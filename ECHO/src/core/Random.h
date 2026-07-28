#pragma once

#include "Math.h"

namespace em {

class Rng {
public:
    Rng() : s(0x853c49e6748fea9bULL) {}
    explicit Rng(u64 seed) { setSeed(seed); }

    void setSeed(u64 seed) {
        s = seed ? seed : 0x9E3779B97F4A7C15ULL;
        for (int i = 0; i < 4; i++) nextU32();
    }
    u64 state() const { return s; }
    void setState(u64 v) { s = v; }

    u32 nextU32() {
        s ^= s << 13;
        s ^= s >> 7;
        s ^= s << 17;
        return (u32)(s >> 16);
    }
    float nextFloat() { return (float)(nextU32() & 0x00FFFFFF) / 16777216.0f; }
    float range(float a, float b) { return a + (b - a) * nextFloat(); }
    int rangeInt(int a, int b) { if (b <= a) return a; return a + (int)(nextU32() % (u32)(b - a)); }
    bool chance(float p) { return nextFloat() < p; }
    Vec3 unitSphere() {
        for (int i = 0; i < 24; i++) {
            Vec3 v(range(-1, 1), range(-1, 1), range(-1, 1));
            float l = lengthSq(v);
            if (l > 0.0001f && l <= 1.0f) return v / std::sqrt(l);
        }
        return Vec3(0, 1, 0);
    }
    Vec3 hemisphere(const Vec3& n) {
        Vec3 v = unitSphere();
        return dot(v, n) < 0 ? -v : v;
    }
    Vec2 unitDisk() {
        for (int i = 0; i < 24; i++) {
            Vec2 v(range(-1, 1), range(-1, 1));
            if (lengthSq(v) <= 1.0f) return v;
        }
        return Vec2(0, 0);
    }
    template <typename T>
    const T& pick(const std::vector<T>& v) { return v[(size_t)rangeInt(0, (int)v.size())]; }
    template <typename T>
    void shuffle(std::vector<T>& v) {
        for (int i = (int)v.size() - 1; i > 0; i--) std::swap(v[i], v[rangeInt(0, i + 1)]);
    }

private:
    u64 s;
};

inline u64 hashCombine(u64 a, u64 b) {
    a ^= b + 0x9E3779B97F4A7C15ULL + (a << 6) + (a >> 2);
    return a;
}

inline u64 hashString(const std::string& v) {
    u64 h = 1469598103934665603ULL;
    for (char c : v) { h ^= (u8)c; h *= 1099511628211ULL; }
    return h;
}

}
