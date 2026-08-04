#include "Random.hpp"

#include "Scalar.hpp"

namespace sf {

u64 splitMix64(u64 state) {
    u64 value = state + 0x9E3779B97F4A7C15ull;
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9ull;
    value = (value ^ (value >> 27)) * 0x94D049BB133111EBull;
    return value ^ (value >> 31);
}

u64 hashCombine(u64 seed, u64 value) {
    return splitMix64(seed ^ (value + 0x9E3779B97F4A7C15ull + (seed << 6) + (seed >> 2)));
}

u64 hashCoordinate(u64 seed, i64 x, i64 y, i64 z) {
    u64 hash = hashCombine(seed, static_cast<u64>(x));
    hash = hashCombine(hash, static_cast<u64>(y));
    hash = hashCombine(hash, static_cast<u64>(z));
    return hash;
}

void Random::reseed(u64 seed) {
    stateValue = splitMix64(seed);
    streamValue = splitMix64(stateValue) | 1ull;
}

u64 Random::nextUnsigned64() {
    stateValue = stateValue * 6364136223846793005ull + streamValue;
    u64 value = stateValue;
    value ^= value >> 33;
    value *= 0xFF51AFD7ED558CCDull;
    value ^= value >> 33;
    value *= 0xC4CEB9FE1A85EC53ull;
    value ^= value >> 33;
    return value;
}

u32 Random::nextUnsigned32() {
    return static_cast<u32>(nextUnsigned64() >> 32);
}

f32 Random::nextFloat() {
    return static_cast<f32>(nextUnsigned32() >> 8) * (1.0f / 16777216.0f);
}

f64 Random::nextDouble() {
    return static_cast<f64>(nextUnsigned64() >> 11) * (1.0 / 9007199254740992.0);
}

f32 Random::range(f32 low, f32 high) {
    return low + (high - low) * nextFloat();
}

f64 Random::rangeDouble(f64 low, f64 high) {
    return low + (high - low) * nextDouble();
}

i32 Random::rangeInt(i32 low, i32 high) {
    if (high <= low) return low;
    const u32 span = static_cast<u32>(high - low);
    return low + static_cast<i32>(nextUnsigned32() % span);
}

bool Random::chance(f32 probability) {
    return nextFloat() < probability;
}

f32 Random::gaussian(f32 mean, f32 standardDeviation) {
    f32 u1 = nextFloat();
    if (u1 < 1.0e-7f) u1 = 1.0e-7f;
    const f32 u2 = nextFloat();
    const f32 magnitude = std::sqrt(-2.0f * std::log(u1));
    return mean + standardDeviation * magnitude * std::cos(kTwoPi * u2);
}

Vec3 Random::unitVector() {
    const f32 z = range(-1.0f, 1.0f);
    const f32 angle = range(0.0f, kTwoPi);
    const f32 planar = std::sqrt(maxValue(0.0f, 1.0f - z * z));
    return Vec3(planar * std::cos(angle), planar * std::sin(angle), z);
}

Vec3 Random::insideUnitSphere() {
    return unitVector() * std::cbrt(nextFloat());
}

DVec3 Random::unitVectorDouble() {
    const f64 z = rangeDouble(-1.0, 1.0);
    const f64 angle = rangeDouble(0.0, kTwoPiDouble);
    const f64 planar = std::sqrt(maxValue(0.0, 1.0 - z * z));
    return DVec3(planar * std::cos(angle), planar * std::sin(angle), z);
}

}
