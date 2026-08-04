#pragma once

#include "../core/Types.hpp"

#include <new>

namespace sf {

enum class MemoryCategory : u32 {
    Core = 0,
    Render,
    Terrain,
    Universe,
    Physics,
    Audio,
    Network,
    Gameplay,
    Interface,
    Scratch,
    Count
};

class Allocator {
public:
    virtual ~Allocator() = default;
    virtual void* allocate(usize size, usize alignment) = 0;
    virtual void deallocate(void* pointer, usize size) = 0;
    virtual usize bytesInUse() const = 0;
    virtual usize capacityBytes() const = 0;
};

template <typename T, typename... Args>
T* construct(Allocator& allocator, Args&&... args) {
    void* memory = allocator.allocate(sizeof(T), alignof(T));
    return memory ? new (memory) T(static_cast<Args&&>(args)...) : nullptr;
}

template <typename T>
void destroy(Allocator& allocator, T* pointer) {
    if (!pointer) return;
    pointer->~T();
    allocator.deallocate(pointer, sizeof(T));
}

}
