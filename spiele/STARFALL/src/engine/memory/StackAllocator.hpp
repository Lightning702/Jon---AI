#pragma once

#include "Allocator.hpp"
#include "MemoryTracker.hpp"

namespace sf {

class StackAllocator final : public Allocator {
public:
    StackAllocator() = default;
    StackAllocator(usize capacity, MemoryCategory category);
    ~StackAllocator() override;

    StackAllocator(const StackAllocator&) = delete;
    StackAllocator& operator=(const StackAllocator&) = delete;

    void initialize(usize capacity, MemoryCategory category);
    void release();
    void reset();

    void* allocate(usize size, usize alignment) override;
    void deallocate(void* pointer, usize size) override;
    usize bytesInUse() const override { return top; }
    usize capacityBytes() const override { return capacity; }

private:
    struct BlockHeader {
        usize previousTop;
    };

    u8* base = nullptr;
    usize capacity = 0;
    usize top = 0;
    MemoryCategory trackedCategory = MemoryCategory::Core;
};

}
