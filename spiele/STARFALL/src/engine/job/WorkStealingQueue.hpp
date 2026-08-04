#pragma once

#include "../core/Types.hpp"

#include <functional>
#include <mutex>
#include <vector>

namespace sf {

struct JobTask {
    std::function<void()> work;
    void* counter = nullptr;
};

class WorkStealingQueue {
public:
    void pushBottom(JobTask task) {
        std::lock_guard<std::mutex> lock(mutex);
        tasks.push_back(std::move(task));
    }

    bool popBottom(JobTask& out) {
        std::lock_guard<std::mutex> lock(mutex);
        if (tasks.empty()) return false;
        out = std::move(tasks.back());
        tasks.pop_back();
        return true;
    }

    bool stealTop(JobTask& out) {
        std::lock_guard<std::mutex> lock(mutex);
        if (tasks.empty()) return false;
        out = std::move(tasks.front());
        tasks.erase(tasks.begin());
        return true;
    }

    usize size() const {
        std::lock_guard<std::mutex> lock(mutex);
        return tasks.size();
    }

private:
    mutable std::mutex mutex;
    std::vector<JobTask> tasks;
};

}
