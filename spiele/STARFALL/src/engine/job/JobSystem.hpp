#pragma once

#include "JobHandle.hpp"
#include "WorkStealingQueue.hpp"

#include <condition_variable>
#include <thread>

namespace sf {

class JobSystem {
public:
    static JobSystem& instance();

    void initialize(u32 workerCount);
    void shutdown();

    JobHandle schedule(std::function<void()> work);
    JobHandle scheduleBatch(const std::vector<std::function<void()>>& batch);
    void wait(const JobHandle& handle);
    bool helpUntilIdle();

    u32 workerCount() const { return static_cast<u32>(workers.size()); }
    u64 executedJobs() const { return executed.load(std::memory_order_relaxed); }
    bool running() const { return active.load(std::memory_order_acquire); }

private:
    void workerMain(u32 workerIndex);
    bool acquireTask(u32 workerIndex, JobTask& out);
    void runTask(JobTask& task);
    void notifyAll();

    std::vector<std::thread> workers;
    std::vector<std::unique_ptr<WorkStealingQueue>> queues;
    std::mutex sleepMutex;
    std::condition_variable sleepSignal;
    std::atomic<bool> active{false};
    std::atomic<u64> executed{0};
    std::atomic<u32> roundRobin{0};
};

}
