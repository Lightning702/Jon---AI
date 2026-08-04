#pragma once

#include "Array.hpp"

namespace sf {

template <typename T>
class RingBuffer {
public:
    RingBuffer() = default;
    explicit RingBuffer(usize capacityValue) { initialize(capacityValue); }

    void initialize(usize capacityValue) {
        slots.resize(capacityValue == 0 ? 1 : capacityValue);
        head = 0;
        tail = 0;
        count = 0;
    }

    bool push(const T& value) {
        if (count == slots.size()) return false;
        slots[head] = value;
        head = (head + 1) % slots.size();
        ++count;
        return true;
    }

    void pushOverwrite(const T& value) {
        if (count == slots.size()) {
            tail = (tail + 1) % slots.size();
            --count;
        }
        slots[head] = value;
        head = (head + 1) % slots.size();
        ++count;
    }

    bool pop(T& out) {
        if (count == 0) return false;
        out = slots[tail];
        tail = (tail + 1) % slots.size();
        --count;
        return true;
    }

    const T& peekFromNewest(usize offsetFromNewest) const {
        const usize index = (head + slots.size() - 1 - (offsetFromNewest % slots.size())) % slots.size();
        return slots[index];
    }

    const T& peekFromOldest(usize offsetFromOldest) const {
        return slots[(tail + offsetFromOldest) % slots.size()];
    }

    void clear() {
        head = 0;
        tail = 0;
        count = 0;
    }

    usize size() const { return count; }
    usize capacity() const { return slots.size(); }
    bool empty() const { return count == 0; }
    bool full() const { return count == slots.size(); }

private:
    Array<T> slots;
    usize head = 0;
    usize tail = 0;
    usize count = 0;
};

}
