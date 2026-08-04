#pragma once

#include "DVec3.hpp"
#include "Vec2.hpp"
#include "Vec3.hpp"

namespace sf {

struct FractalSettings {
    u32 octaves = 6;
    f64 frequency = 1.0;
    f64 amplitude = 1.0;
    f64 lacunarity = 2.02;
    f64 gain = 0.5;
};

f64 valueNoise3(u64 seed, const DVec3& position);
f64 gradientNoise3(u64 seed, const DVec3& position);
f64 simplexNoise3(u64 seed, const DVec3& position);
f64 fractalNoise3(u64 seed, const DVec3& position, const FractalSettings& settings);
f64 ridgedMultifractal3(u64 seed, const DVec3& position, const FractalSettings& settings);
f64 billowNoise3(u64 seed, const DVec3& position, const FractalSettings& settings);
DVec3 domainWarp3(u64 seed, const DVec3& position, f64 strength, f64 frequency);

struct WorleyResult {
    f64 nearestDistance = 0.0;
    f64 secondDistance = 0.0;
    u64 cellHash = 0;
    DVec3 featurePoint = DVec3::zero();
};

WorleyResult worleyNoise3(u64 seed, const DVec3& position);
f64 worleyNearestDistance(u64 seed, const DVec3& position);
f64 craterField(u64 seed, const DVec3& unitDirection, f64 density, f64 depth, u32 layers);

}
