#pragma once

#include "JobSystem.hpp"

namespace sf {

template <typename Body>
void parallelFor(usize itemCount, usize minimumChunk, Body body) {
    if (itemCount == 0) return;
    JobSystem& jobs = JobSystem::instance();
    const usize workers = jobs.workerCount() + 1;
    if (workers <= 1 || itemCount <= minimumChunk) {
        for (usize index = 0; index < itemCount; ++index) body(index);
        return;
    }

    usize chunk = (itemCount + workers - 1) / workers;
    if (chunk < minimumChunk) chunk = minimumChunk;

    std::vector<std::function<void()>> batch;
    for (usize start = 0; start < itemCount; start += chunk) {
        const usize end = start + chunk > itemCount ? itemCount : start + chunk;
        batch.push_back([start, end, &body]() {
            for (usize index = start; index < end; ++index) body(index);
        });
    }
    JobHandle handle = jobs.scheduleBatch(batch);
    jobs.wait(handle);
}

template <typename Body>
void parallelForRange(usize itemCount, usize minimumChunk, Body body) {
    if (itemCount == 0) return;
    JobSystem& jobs = JobSystem::instance();
    const usize workers = jobs.workerCount() + 1;
    if (workers <= 1 || itemCount <= minimumChunk) {
        body(0, itemCount);
        return;
    }

    usize chunk = (itemCount + workers - 1) / workers;
    if (chunk < minimumChunk) chunk = minimumChunk;

    std::vector<std::function<void()>> batch;
    for (usize start = 0; start < itemCount; start += chunk) {
        const usize end = start + chunk > itemCount ? itemCount : start + chunk;
        batch.push_back([start, end, &body]() { body(start, end); });
    }
    JobHandle handle = jobs.scheduleBatch(batch);
    jobs.wait(handle);
}

}
