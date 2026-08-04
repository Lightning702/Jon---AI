#pragma once

#include "../core/Types.hpp"

#include <atomic>
#include <memory>

namespace sf {

struct JobCounter {
    std::atomic<i32> pending{0};
};

class JobHandle {
public:
    JobHandle() = default;
    explicit JobHandle(std::shared_ptr<JobCounter> counterValue) : counter(std::move(counterValue)) {}

    bool valid() const { return static_cast<bool>(counter); }
    bool finished() const { return !counter || counter->pending.load(std::memory_order_acquire) <= 0; }
    JobCounter* raw() const { return counter.get(); }

private:
    std::shared_ptr<JobCounter> counter;
};

}
