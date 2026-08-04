#pragma once

#include "../core/Types.hpp"

#include <cmath>

namespace sf {

struct Vec3 {
    f32 x = 0.0f;
    f32 y = 0.0f;
    f32 z = 0.0f;

    constexpr Vec3() = default;
    constexpr Vec3(f32 xValue, f32 yValue, f32 zValue) : x(xValue), y(yValue), z(zValue) {}
    explicit constexpr Vec3(f32 scalar) : x(scalar), y(scalar), z(scalar) {}

    constexpr Vec3 operator+(const Vec3& other) const { return Vec3(x + other.x, y + other.y, z + other.z); }
    constexpr Vec3 operator-(const Vec3& other) const { return Vec3(x - other.x, y - other.y, z - other.z); }
    constexpr Vec3 operator*(f32 scalar) const { return Vec3(x * scalar, y * scalar, z * scalar); }
    constexpr Vec3 operator/(f32 scalar) const { return Vec3(x / scalar, y / scalar, z / scalar); }
    constexpr Vec3 operator*(const Vec3& other) const { return Vec3(x * other.x, y * other.y, z * other.z); }
    constexpr Vec3 operator-() const { return Vec3(-x, -y, -z); }

    Vec3& operator+=(const Vec3& other) { x += other.x; y += other.y; z += other.z; return *this; }
    Vec3& operator-=(const Vec3& other) { x -= other.x; y -= other.y; z -= other.z; return *this; }
    Vec3& operator*=(f32 scalar) { x *= scalar; y *= scalar; z *= scalar; return *this; }
    Vec3& operator/=(f32 scalar) { x /= scalar; y /= scalar; z /= scalar; return *this; }

    bool operator==(const Vec3& other) const { return x == other.x && y == other.y && z == other.z; }
    bool operator!=(const Vec3& other) const { return !(*this == other); }

    f32 component(u32 index) const { return index == 0 ? x : (index == 1 ? y : z); }
    void setComponent(u32 index, f32 value) {
        if (index == 0) x = value;
        else if (index == 1) y = value;
        else z = value;
    }

    static constexpr Vec3 zero() { return Vec3(0.0f, 0.0f, 0.0f); }
    static constexpr Vec3 one() { return Vec3(1.0f, 1.0f, 1.0f); }
    static constexpr Vec3 unitX() { return Vec3(1.0f, 0.0f, 0.0f); }
    static constexpr Vec3 unitY() { return Vec3(0.0f, 1.0f, 0.0f); }
    static constexpr Vec3 unitZ() { return Vec3(0.0f, 0.0f, 1.0f); }
};

inline constexpr Vec3 operator*(f32 scalar, const Vec3& v) { return v * scalar; }
inline constexpr f32 dot(const Vec3& a, const Vec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline constexpr Vec3 cross(const Vec3& a, const Vec3& b) {
    return Vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
}
inline constexpr f32 lengthSquared(const Vec3& v) { return dot(v, v); }
inline f32 length(const Vec3& v) { return std::sqrt(dot(v, v)); }
inline Vec3 normalize(const Vec3& v) {
    const f32 magnitude = length(v);
    return magnitude > 0.0f ? v / magnitude : Vec3::zero();
}
inline constexpr Vec3 lerp(const Vec3& a, const Vec3& b, f32 t) { return a + (b - a) * t; }
inline constexpr Vec3 minComponents(const Vec3& a, const Vec3& b) {
    return Vec3(a.x < b.x ? a.x : b.x, a.y < b.y ? a.y : b.y, a.z < b.z ? a.z : b.z);
}
inline constexpr Vec3 maxComponents(const Vec3& a, const Vec3& b) {
    return Vec3(a.x > b.x ? a.x : b.x, a.y > b.y ? a.y : b.y, a.z > b.z ? a.z : b.z);
}
inline Vec3 reflect(const Vec3& incident, const Vec3& normalVector) {
    return incident - normalVector * (2.0f * dot(incident, normalVector));
}
inline Vec3 perpendicular(const Vec3& v) {
    const Vec3 reference = std::fabs(v.x) < 0.9f ? Vec3::unitX() : Vec3::unitY();
    return normalize(cross(v, reference));
}
inline f32 distance(const Vec3& a, const Vec3& b) { return length(b - a); }

}
