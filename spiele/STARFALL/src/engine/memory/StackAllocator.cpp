#include "StackAllocator.hpp"

#include "../core/Assert.hpp"

#include <cstdlib>

namespace sf {

StackAllocator::StackAllocator(usize capacityBytesValue, MemoryCategory category) {
    initialize(capacityBytesValue, category);
}

StackAllocator::~StackAllocator() {
    release();
}

void StackAllocator::initialize(usize capacityBytesValue, MemoryCategory category) {
    release();
    trackedCategory = category;
    capacity = capacityBytesValue;
    top = 0;
    if (capacity == 0) return;
    base = static_cast<u8*>(std::malloc(capacity));
    SF_ASSERT_MSG(base != nullptr, "Stack-Allokator konnte nicht reserviert werden");
    MemoryTracker::instance().recordAllocation(trackedCategory, capacity);
}

void StackAllocator::release() {
    if (!base) {
        capacity = 0;
        top = 0;
        return;
    }
    MemoryTracker::instance().recordDeallocation(trackedCategory, capacity);
    std::free(base);
    base = nullptr;
    capacity = 0;
    top = 0;
}

void StackAllocator::reset() {
    top = 0;
}

void* StackAllocator::allocate(usize size, usize alignment) {
    if (size == 0 || !base) return nullptr;
    const usize alignmentValue = alignment < alignof(BlockHeader) ? alignof(BlockHeader) : alignment;
    const usize headerOffset = alignUp(top + sizeof(BlockHeader), alignmentValue);
    if (headerOffset + size > capacity) return nullptr;
    BlockHeader* header = reinterpret_cast<BlockHeader*>(base + headerOffset - sizeof(BlockHeader));
    header->previousTop = top;
    top = headerOffset + size;
    return base + headerOffset;
}

void StackAllocator::deallocate(void* pointer, usize) {
    if (!pointer || !base) return;
    u8* target = static_cast<u8*>(pointer);
    if (target < base || target >= base + capacity) return;
    const BlockHeader* header = reinterpret_cast<const BlockHeader*>(target - sizeof(BlockHeader));
    top = header->previousTop;
}

}
