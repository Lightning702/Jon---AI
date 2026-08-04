#pragma once

#include "Types.hpp"

#include <string>

namespace sf {

constexpr u64 kFnvOffsetBasis = 1469598103934665603ull;
constexpr u64 kFnvPrime = 1099511628211ull;

constexpr u64 hashString(const char* text, u64 seed = kFnvOffsetBasis) {
    u64 hash = seed;
    while (*text) {
        hash ^= static_cast<u64>(static_cast<u8>(*text++));
        hash *= kFnvPrime;
    }
    return hash;
}

inline u64 hashBytes(const void* data, usize size, u64 seed = kFnvOffsetBasis) {
    const u8* bytes = static_cast<const u8*>(data);
    u64 hash = seed;
    for (usize i = 0; i < size; ++i) {
        hash ^= static_cast<u64>(bytes[i]);
        hash *= kFnvPrime;
    }
    return hash;
}

class StringId {
public:
    constexpr StringId() : hashValue(0) {}
    constexpr explicit StringId(u64 value) : hashValue(value) {}
    explicit StringId(const char* text) : hashValue(hashString(text)) { registerText(text); }
    explicit StringId(const std::string& text) : hashValue(hashString(text.c_str())) { registerText(text.c_str()); }

    constexpr u64 value() const { return hashValue; }
    constexpr bool valid() const { return hashValue != 0; }
    bool operator==(const StringId& other) const { return hashValue == other.hashValue; }
    bool operator!=(const StringId& other) const { return hashValue != other.hashValue; }
    bool operator<(const StringId& other) const { return hashValue < other.hashValue; }

    const char* text() const;

private:
    static void registerText(const char* text);
    u64 hashValue;
};

constexpr StringId operator""_sid(const char* text, usize) {
    return StringId(hashString(text));
}

struct StringIdHash {
    usize operator()(const StringId& id) const { return static_cast<usize>(id.value()); }
};

}
