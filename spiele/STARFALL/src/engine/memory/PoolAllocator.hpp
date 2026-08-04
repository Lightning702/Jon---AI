#pragma once

#include "Allocator.hpp"
#include "MemoryTracker.hpp"

namespace sf {

class PoolAllocator final : public Allocator {
public:
    PoolAllocator() = default;
    PoolAllocator(usize elementSize, usize elementAlignment, usize elementCount, MemoryCategory category);
    ~PoolAllocator() override;

    PoolAllocator(const PoolAllocator&) = delete;
    PoolAllocator& operator=(const PoolAllocator&) = delete;

    void initialize(usize elementSize, usize elementAlignment, usize elementCount, MemoryCategory category);
    void release();
    void reset();

    void* allocate(usize size, usize alignment) override;
    void deallocate(void* pointer, usize size) override;
    usize bytesInUse() const override { return usedElements * strideBytes; }
    usize capacityBytes() const override { return totalElements * strideBytes; }

    void* acquire();
    void recycle(void* pointer);

    usize used() const { return usedElements; }
    usize total() const { return totalElements; }
    usize stride() const { return strideBytes; }
    bool owns(const void* pointer) const;

private:
    u8* base = nullptr;
    void* freeHead = nullptr;
    usize strideBytes = 0;
    usize totalElements = 0;
    usize usedElements = 0;
    MemoryCategory trackedCategory = MemoryCategory::Core;
};

}
