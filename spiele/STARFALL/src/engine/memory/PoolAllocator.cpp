#include "PoolAllocator.hpp"

#include "../core/Assert.hpp"

#include <cstdlib>

namespace sf {

PoolAllocator::PoolAllocator(usize elementSize, usize elementAlignment, usize elementCount, MemoryCategory category) {
    initialize(elementSize, elementAlignment, elementCount, category);
}

PoolAllocator::~PoolAllocator() {
    release();
}

void PoolAllocator::initialize(usize elementSize, usize elementAlignment, usize elementCount, MemoryCategory category) {
    release();
    trackedCategory = category;
    const usize alignment = elementAlignment < sizeof(void*) ? sizeof(void*) : elementAlignment;
    const usize size = elementSize < sizeof(void*) ? sizeof(void*) : elementSize;
    strideBytes = alignUp(size, alignment);
    totalElements = elementCount;
    usedElements = 0;
    if (totalElements == 0) return;
    base = static_cast<u8*>(std::malloc(strideBytes * totalElements));
    SF_ASSERT_MSG(base != nullptr, "Pool konnte nicht reserviert werden");
    MemoryTracker::instance().recordAllocation(trackedCategory, strideBytes * totalElements);
    reset();
}

void PoolAllocator::release() {
    if (!base) {
        strideBytes = 0;
        totalElements = 0;
        usedElements = 0;
        freeHead = nullptr;
        return;
    }
    MemoryTracker::instance().recordDeallocation(trackedCategory, strideBytes * totalElements);
    std::free(base);
    base = nullptr;
    freeHead = nullptr;
    strideBytes = 0;
    totalElements = 0;
    usedElements = 0;
}

void PoolAllocator::reset() {
    usedElements = 0;
    freeHead = nullptr;
    if (!base || totalElements == 0) return;
    for (usize index = totalElements; index > 0; --index) {
        u8* slot = base + (index - 1) * strideBytes;
        *reinterpret_cast<void**>(slot) = freeHead;
        freeHead = slot;
    }
}

void* PoolAllocator::allocate(usize size, usize) {
    return size <= strideBytes ? acquire() : nullptr;
}

void PoolAllocator::deallocate(void* pointer, usize) {
    recycle(pointer);
}

void* PoolAllocator::acquire() {
    if (!freeHead) return nullptr;
    void* slot = freeHead;
    freeHead = *reinterpret_cast<void**>(slot);
    ++usedElements;
    return slot;
}

void PoolAllocator::recycle(void* pointer) {
    if (!pointer || !owns(pointer)) return;
    *reinterpret_cast<void**>(pointer) = freeHead;
    freeHead = pointer;
    if (usedElements > 0) --usedElements;
}

bool PoolAllocator::owns(const void* pointer) const {
    if (!base || !pointer) return false;
    const u8* target = static_cast<const u8*>(pointer);
    return target >= base && target < base + strideBytes * totalElements;
}

}
