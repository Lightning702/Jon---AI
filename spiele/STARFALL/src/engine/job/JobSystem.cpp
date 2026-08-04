#include "JobSystem.hpp"

#include "../core/Log.hpp"

#include <chrono>

namespace sf {
namespace {

thread_local u32 tlsWorkerIndex = 0xFFFFFFFFu;

}

JobSystem& JobSystem::instance() {
    static JobSystem system;
    return system;
}

void JobSystem::initialize(u32 workerCountValue) {
    if (active.load(std::memory_order_acquire)) return;
    u32 hardware = std::thread::hardware_concurrency();
    if (hardware == 0) hardware = 4;
    u32 desired = workerCountValue == 0 ? (hardware > 1 ? hardware - 1 : 1) : workerCountValue;
    if (desired > 32) desired = 32;

    queues.clear();
    for (u32 index = 0; index <= desired; ++index) {
        queues.push_back(std::make_unique<WorkStealingQueue>());
    }
    active.store(true, std::memory_order_release);
    for (u32 index = 0; index < desired; ++index) {
        workers.emplace_back([this, index]() { workerMain(index + 1); });
    }
    logInfo("job", "Job-System gestartet mit %u Arbeitern", desired);
}

void JobSystem::shutdown() {
    if (!active.exchange(false, std::memory_order_acq_rel)) return;
    notifyAll();
    for (std::thread& worker : workers) {
        if (worker.joinable()) worker.join();
    }
    workers.clear();
    queues.clear();
}

void JobSystem::notifyAll() {
    std::lock_guard<std::mutex> lock(sleepMutex);
    sleepSignal.notify_all();
}

JobHandle JobSystem::schedule(std::function<void()> work) {
    auto counter = std::make_shared<JobCounter>();
    counter->pending.store(1, std::memory_order_release);
    JobTask task;
    task.work = std::move(work);
    task.counter = counter.get();

    if (queues.empty()) {
        runTask(task);
        return JobHandle(counter);
    }
    const u32 target = roundRobin.fetch_add(1, std::memory_order_relaxed) % static_cast<u32>(queues.size());
    queues[target]->pushBottom(std::move(task));
    notifyAll();
    return JobHandle(counter);
}

JobHandle JobSystem::scheduleBatch(const std::vector<std::function<void()>>& batch) {
    auto counter = std::make_shared<JobCounter>();
    counter->pending.store(static_cast<i32>(batch.size()), std::memory_order_release);
    if (batch.empty()) return JobHandle(counter);

    if (queues.empty()) {
        for (const std::function<void()>& work : batch) {
            JobTask task;
            task.work = work;
            task.counter = counter.get();
            runTask(task);
        }
        return JobHandle(counter);
    }

    for (usize index = 0; index < batch.size(); ++index) {
        JobTask task;
        task.work = batch[index];
        task.counter = counter.get();
        queues[index % queues.size()]->pushBottom(std::move(task));
    }
    notifyAll();
    return JobHandle(counter);
}

void JobSystem::runTask(JobTask& task) {
    if (task.work) task.work();
    if (task.counter) {
        static_cast<JobCounter*>(task.counter)->pending.fetch_sub(1, std::memory_order_acq_rel);
    }
    executed.fetch_add(1, std::memory_order_relaxed);
}

bool JobSystem::acquireTask(u32 workerIndex, JobTask& out) {
    if (queues.empty()) return false;
    if (workerIndex < queues.size() && queues[workerIndex]->popBottom(out)) return true;
    for (usize offset = 1; offset <= queues.size(); ++offset) {
        const usize victim = (workerIndex + offset) % queues.size();
        if (queues[victim]->stealTop(out)) return true;
    }
    return false;
}

void JobSystem::workerMain(u32 workerIndex) {
    tlsWorkerIndex = workerIndex;
    while (active.load(std::memory_order_acquire)) {
        JobTask task;
        if (acquireTask(workerIndex, task)) {
            runTask(task);
            continue;
        }
        std::unique_lock<std::mutex> lock(sleepMutex);
        sleepSignal.wait_for(lock, std::chrono::milliseconds(2));
    }
    JobTask remaining;
    while (acquireTask(workerIndex, remaining)) runTask(remaining);
}

bool JobSystem::helpUntilIdle() {
    const u32 index = tlsWorkerIndex == 0xFFFFFFFFu ? 0 : tlsWorkerIndex;
    JobTask task;
    bool didWork = false;
    while (acquireTask(index, task)) {
        runTask(task);
        didWork = true;
    }
    return didWork;
}

void JobSystem::wait(const JobHandle& handle) {
    if (!handle.valid()) return;
    const u32 index = tlsWorkerIndex == 0xFFFFFFFFu ? 0 : tlsWorkerIndex;
    while (!handle.finished()) {
        JobTask task;
        if (acquireTask(index, task)) {
            runTask(task);
            continue;
        }
        std::this_thread::yield();
    }
}

}
