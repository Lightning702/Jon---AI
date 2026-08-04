#pragma once

#include "Vec3.hpp"

namespace sf {

struct DVec3 {
    f64 x = 0.0;
    f64 y = 0.0;
    f64 z = 0.0;

    constexpr DVec3() = default;
    constexpr DVec3(f64 xValue, f64 yValue, f64 zValue) : x(xValue), y(yValue), z(zValue) {}
    explicit constexpr DVec3(f64 scalar) : x(scalar), y(scalar), z(scalar) {}
    explicit constexpr DVec3(const Vec3& v) : x(v.x), y(v.y), z(v.z) {}

    constexpr DVec3 operator+(const DVec3& other) const { return DVec3(x + other.x, y + other.y, z + other.z); }
    constexpr DVec3 operator-(const DVec3& other) const { return DVec3(x - other.x, y - other.y, z - other.z); }
    constexpr DVec3 operator*(f64 scalar) const { return DVec3(x * scalar, y * scalar, z * scalar); }
    constexpr DVec3 operator/(f64 scalar) const { return DVec3(x / scalar, y / scalar, z / scalar); }
    constexpr DVec3 operator*(const DVec3& other) const { return DVec3(x * other.x, y * other.y, z * other.z); }
    constexpr DVec3 operator-() const { return DVec3(-x, -y, -z); }

    DVec3& operator+=(const DVec3& other) { x += other.x; y += other.y; z += other.z; return *this; }
    DVec3& operator-=(const DVec3& other) { x -= other.x; y -= other.y; z -= other.z; return *this; }
    DVec3& operator*=(f64 scalar) { x *= scalar; y *= scalar; z *= scalar; return *this; }

    bool operator==(const DVec3& other) const { return x == other.x && y == other.y && z == other.z; }
    bool operator!=(const DVec3& other) const { return !(*this == other); }

    Vec3 toFloat() const { return Vec3(static_cast<f32>(x), static_cast<f32>(y), static_cast<f32>(z)); }

    static constexpr DVec3 zero() { return DVec3(0.0, 0.0, 0.0); }
    static constexpr DVec3 unitX() { return DVec3(1.0, 0.0, 0.0); }
    static constexpr DVec3 unitY() { return DVec3(0.0, 1.0, 0.0); }
    static constexpr DVec3 unitZ() { return DVec3(0.0, 0.0, 1.0); }
};

inline constexpr DVec3 operator*(f64 scalar, const DVec3& v) { return v * scalar; }
inline constexpr f64 dot(const DVec3& a, const DVec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline constexpr DVec3 cross(const DVec3& a, const DVec3& b) {
    return DVec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
}
inline constexpr f64 lengthSquared(const DVec3& v) { return dot(v, v); }
inline f64 length(const DVec3& v) { return std::sqrt(dot(v, v)); }
inline DVec3 normalize(const DVec3& v) {
    const f64 magnitude = length(v);
    return magnitude > 0.0 ? v / magnitude : DVec3::zero();
}
inline f64 distance(const DVec3& a, const DVec3& b) { return length(b - a); }
inline constexpr DVec3 lerp(const DVec3& a, const DVec3& b, f64 t) { return a + (b - a) * t; }
inline DVec3 fromFloat(const Vec3& v) { return DVec3(v.x, v.y, v.z); }

}
