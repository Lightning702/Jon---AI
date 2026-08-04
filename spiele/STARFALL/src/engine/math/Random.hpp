#pragma once

#include "DVec3.hpp"
#include "Vec3.hpp"

namespace sf {

u64 splitMix64(u64 state);
u64 hashCombine(u64 seed, u64 value);
u64 hashCoordinate(u64 seed, i64 x, i64 y, i64 z);

class Random {
public:
    explicit Random(u64 seed = 0x9E3779B97F4A7C15ull) { reseed(seed); }

    void reseed(u64 seed);

    u64 nextUnsigned64();
    u32 nextUnsigned32();
    f32 nextFloat();
    f64 nextDouble();
    f32 range(f32 low, f32 high);
    f64 rangeDouble(f64 low, f64 high);
    i32 rangeInt(i32 low, i32 high);
    bool chance(f32 probability);
    f32 gaussian(f32 mean, f32 standardDeviation);
    Vec3 unitVector();
    Vec3 insideUnitSphere();
    DVec3 unitVectorDouble();

    u64 state() const { return stateValue; }

private:
    u64 stateValue = 0;
    u64 streamValue = 0;
};

}
