#pragma once

#include "Common.h"
#include <thread>
#include <atomic>
#include <functional>

namespace echo {

inline int hardwareThreads() {
    unsigned n = std::thread::hardware_concurrency();
    if (n == 0) n = 4;
    return (int)std::min(n, 32u);
}

inline void parallelFor(int count, const std::function<void(int)>& fn) {
    if (count <= 0) return;
    int workers = std::min(hardwareThreads(), count);
    if (workers <= 1) {
        for (int i = 0; i < count; i++) fn(i);
        return;
    }
    std::atomic<int> next(0);
    std::vector<std::thread> pool;
    pool.reserve((size_t)workers);
    for (int t = 0; t < workers; t++) {
        pool.emplace_back([&]() {
            for (;;) {
                int i = next.fetch_add(1);
                if (i >= count) break;
                fn(i);
            }
        });
    }
    for (auto& th : pool) th.join();
}

}
