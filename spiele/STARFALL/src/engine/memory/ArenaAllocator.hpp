#pragma once

#include "Allocator.hpp"
#include "MemoryTracker.hpp"

namespace sf {

class ArenaAllocator final : public Allocator {
public:
    ArenaAllocator() = default;
    ArenaAllocator(usize capacity, MemoryCategory category);
    ~ArenaAllocator() override;

    ArenaAllocator(const ArenaAllocator&) = delete;
    ArenaAllocator& operator=(const ArenaAllocator&) = delete;
    ArenaAllocator(ArenaAllocator&& other) noexcept;
    ArenaAllocator& operator=(ArenaAllocator&& other) noexcept;

    void initialize(usize capacity, MemoryCategory category);
    void release();
    void reset();

    void* allocate(usize size, usize alignment) override;
    void deallocate(void* pointer, usize size) override;
    usize bytesInUse() const override { return offset; }
    usize capacityBytes() const override { return capacity; }

    usize marker() const { return offset; }
    void rewindTo(usize savedMarker);

private:
    u8* base = nullptr;
    usize capacity = 0;
    usize offset = 0;
    MemoryCategory trackedCategory = MemoryCategory::Core;
};

class ArenaScope {
public:
    explicit ArenaScope(ArenaAllocator& target) : arena(target), savedMarker(target.marker()) {}
    ~ArenaScope() { arena.rewindTo(savedMarker); }

    ArenaScope(const ArenaScope&) = delete;
    ArenaScope& operator=(const ArenaScope&) = delete;

private:
    ArenaAllocator& arena;
    usize savedMarker;
};

}
