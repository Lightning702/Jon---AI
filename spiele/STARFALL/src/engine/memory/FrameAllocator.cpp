#include "FrameAllocator.hpp"

namespace sf {

void FrameAllocator::initialize(usize capacityPerFrame, u32 frameCount, MemoryCategory category) {
    release();
    frames = frameCount == 0 ? 1 : (frameCount > kMaximumFrames ? kMaximumFrames : frameCount);
    for (u32 index = 0; index < frames; ++index) {
        arenas[index].initialize(capacityPerFrame, category);
    }
    current = 0;
    highWater = 0;
}

void FrameAllocator::release() {
    for (u32 index = 0; index < kMaximumFrames; ++index) {
        arenas[index].release();
    }
    frames = 0;
    current = 0;
    highWater = 0;
}

void FrameAllocator::beginFrame() {
    if (frames == 0) return;
    const usize used = arenas[current].bytesInUse();
    if (used > highWater) highWater = used;
    current = (current + 1) % frames;
    arenas[current].reset();
}

void* FrameAllocator::allocate(usize size, usize alignment) {
    if (frames == 0) return nullptr;
    return arenas[current].allocate(size, alignment);
}

void FrameAllocator::deallocate(void*, usize) {
}

usize FrameAllocator::bytesInUse() const {
    return frames == 0 ? 0 : arenas[current].bytesInUse();
}

usize FrameAllocator::capacityBytes() const {
    usize total = 0;
    for (u32 index = 0; index < frames; ++index) total += arenas[index].capacityBytes();
    return total;
}

FrameAllocator& globalFrameAllocator() {
    static FrameAllocator instance;
    return instance;
}

}
