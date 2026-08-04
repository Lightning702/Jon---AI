#pragma once

#include "ArenaAllocator.hpp"

namespace sf {

class FrameAllocator final : public Allocator {
public:
    FrameAllocator() = default;

    void initialize(usize capacityPerFrame, u32 frameCount, MemoryCategory category);
    void release();
    void beginFrame();

    void* allocate(usize size, usize alignment) override;
    void deallocate(void* pointer, usize size) override;
    usize bytesInUse() const override;
    usize capacityBytes() const override;

    u32 activeFrame() const { return current; }
    usize highWaterMark() const { return highWater; }

private:
    static constexpr u32 kMaximumFrames = 4;
    ArenaAllocator arenas[kMaximumFrames];
    u32 frames = 0;
    u32 current = 0;
    usize highWater = 0;
};

FrameAllocator& globalFrameAllocator();

}
