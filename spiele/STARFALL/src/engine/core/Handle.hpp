#pragma once

#include "Types.hpp"

namespace sf {

template <typename Tag>
struct Handle {
    u32 index = kInvalidIndex32;
    u32 generation = 0;

    bool valid() const { return index != kInvalidIndex32; }
    bool operator==(const Handle& other) const {
        return index == other.index && generation == other.generation;
    }
    bool operator!=(const Handle& other) const { return !(*this == other); }

    u64 packed() const { return (static_cast<u64>(generation) << 32) | static_cast<u64>(index); }

    static Handle fromPacked(u64 value) {
        Handle handle;
        handle.index = static_cast<u32>(value & 0xFFFFFFFFull);
        handle.generation = static_cast<u32>(value >> 32);
        return handle;
    }

    static Handle invalid() { return Handle{}; }
};

struct HandleHash {
    template <typename Tag>
    usize operator()(const Handle<Tag>& handle) const {
        u64 value = handle.packed();
        value ^= value >> 33;
        value *= 0xFF51AFD7ED558CCDull;
        value ^= value >> 33;
        return static_cast<usize>(value);
    }
};

}
