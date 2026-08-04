#include "ArenaAllocator.hpp"

#include "../core/Assert.hpp"

#include <cstdlib>
#include <cstring>

namespace sf {

ArenaAllocator::ArenaAllocator(usize capacityBytesValue, MemoryCategory category) {
    initialize(capacityBytesValue, category);
}

ArenaAllocator::~ArenaAllocator() {
    release();
}

ArenaAllocator::ArenaAllocator(ArenaAllocator&& other) noexcept
    : base(other.base), capacity(other.capacity), offset(other.offset), trackedCategory(other.trackedCategory) {
    other.base = nullptr;
    other.capacity = 0;
    other.offset = 0;
}

ArenaAllocator& ArenaAllocator::operator=(ArenaAllocator&& other) noexcept {
    if (this != &other) {
        release();
        base = other.base;
        capacity = other.capacity;
        offset = other.offset;
        trackedCategory = other.trackedCategory;
        other.base = nullptr;
        other.capacity = 0;
        other.offset = 0;
    }
    return *this;
}

void ArenaAllocator::initialize(usize capacityBytesValue, MemoryCategory category) {
    release();
    trackedCategory = category;
    capacity = capacityBytesValue;
    offset = 0;
    if (capacity == 0) return;
    base = static_cast<u8*>(std::malloc(capacity));
    SF_ASSERT_MSG(base != nullptr, "Arena konnte nicht reserviert werden");
    MemoryTracker::instance().recordAllocation(trackedCategory, capacity);
}

void ArenaAllocator::release() {
    if (!base) {
        capacity = 0;
        offset = 0;
        return;
    }
    MemoryTracker::instance().recordDeallocation(trackedCategory, capacity);
    std::free(base);
    base = nullptr;
    capacity = 0;
    offset = 0;
}

void ArenaAllocator::reset() {
    offset = 0;
}

void* ArenaAllocator::allocate(usize size, usize alignment) {
    if (size == 0 || !base) return nullptr;
    const usize alignmentValue = alignment == 0 ? alignof(std::max_align_t) : alignment;
    const usize baseAddress = reinterpret_cast<usize>(base);
    const usize alignedAddress = alignUp(baseAddress + offset, alignmentValue);
    const usize aligned = alignedAddress - baseAddress;
    if (aligned + size > capacity) return nullptr;
    offset = aligned + size;
    return base + aligned;
}

void ArenaAllocator::deallocate(void*, usize) {
}

void ArenaAllocator::rewindTo(usize savedMarker) {
    if (savedMarker <= offset) offset = savedMarker;
}

}
