#pragma once

#include "../core/Types.hpp"

#include <cmath>

namespace sf {

constexpr f32 kPi = 3.14159265358979323846f;
constexpr f32 kTwoPi = 6.28318530717958647692f;
constexpr f32 kHalfPi = 1.57079632679489661923f;
constexpr f64 kPiDouble = 3.14159265358979323846;
constexpr f64 kTwoPiDouble = 6.28318530717958647692;
constexpr f32 kEpsilon = 1.0e-6f;
constexpr f64 kEpsilonDouble = 1.0e-12;

template <typename T>
constexpr T clampValue(T value, T low, T high) {
    return value < low ? low : (value > high ? high : value);
}

template <typename T>
constexpr T minValue(T a, T b) { return a < b ? a : b; }

template <typename T>
constexpr T maxValue(T a, T b) { return a > b ? a : b; }

inline constexpr f32 saturate(f32 value) { return clampValue(value, 0.0f, 1.0f); }
inline constexpr f64 saturate(f64 value) { return clampValue(value, 0.0, 1.0); }

inline constexpr f32 radians(f32 degrees) { return degrees * (kPi / 180.0f); }
inline constexpr f32 degrees(f32 radiansValue) { return radiansValue * (180.0f / kPi); }
inline constexpr f64 radiansDouble(f64 degreesValue) { return degreesValue * (kPiDouble / 180.0); }

inline constexpr f32 mixValue(f32 a, f32 b, f32 t) { return a + (b - a) * t; }
inline constexpr f64 mixValue(f64 a, f64 b, f64 t) { return a + (b - a) * t; }

inline f32 smoothStep(f32 edge0, f32 edge1, f32 value) {
    if (edge1 == edge0) return value < edge0 ? 0.0f : 1.0f;
    const f32 t = saturate((value - edge0) / (edge1 - edge0));
    return t * t * (3.0f - 2.0f * t);
}

inline f64 smoothStep(f64 edge0, f64 edge1, f64 value) {
    if (edge1 == edge0) return value < edge0 ? 0.0 : 1.0;
    const f64 t = saturate((value - edge0) / (edge1 - edge0));
    return t * t * (3.0 - 2.0 * t);
}

inline f32 wrapAngle(f32 angle) {
    while (angle > kPi) angle -= kTwoPi;
    while (angle < -kPi) angle += kTwoPi;
    return angle;
}

inline f64 wrapAngleDouble(f64 angle) {
    while (angle > kPiDouble) angle -= kTwoPiDouble;
    while (angle < -kPiDouble) angle += kTwoPiDouble;
    return angle;
}

inline f32 moveTowards(f32 current, f32 target, f32 maximumDelta) {
    const f32 difference = target - current;
    if (std::fabs(difference) <= maximumDelta) return target;
    return current + (difference > 0.0f ? maximumDelta : -maximumDelta);
}

inline f32 exponentialApproach(f32 current, f32 target, f32 rate, f32 deltaSeconds) {
    const f32 factor = 1.0f - std::exp(-rate * deltaSeconds);
    return current + (target - current) * factor;
}

inline f64 exponentialApproach(f64 current, f64 target, f64 rate, f64 deltaSeconds) {
    const f64 factor = 1.0 - std::exp(-rate * deltaSeconds);
    return current + (target - current) * factor;
}

}
