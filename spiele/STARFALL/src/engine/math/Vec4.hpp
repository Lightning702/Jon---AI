#pragma once

#include "Vec3.hpp"

namespace sf {

struct Vec4 {
    f32 x = 0.0f;
    f32 y = 0.0f;
    f32 z = 0.0f;
    f32 w = 0.0f;

    constexpr Vec4() = default;
    constexpr Vec4(f32 xValue, f32 yValue, f32 zValue, f32 wValue) : x(xValue), y(yValue), z(zValue), w(wValue) {}
    constexpr Vec4(const Vec3& v, f32 wValue) : x(v.x), y(v.y), z(v.z), w(wValue) {}
    explicit constexpr Vec4(f32 scalar) : x(scalar), y(scalar), z(scalar), w(scalar) {}

    constexpr Vec4 operator+(const Vec4& other) const { return Vec4(x + other.x, y + other.y, z + other.z, w + other.w); }
    constexpr Vec4 operator-(const Vec4& other) const { return Vec4(x - other.x, y - other.y, z - other.z, w - other.w); }
    constexpr Vec4 operator*(f32 scalar) const { return Vec4(x * scalar, y * scalar, z * scalar, w * scalar); }
    constexpr Vec4 operator/(f32 scalar) const { return Vec4(x / scalar, y / scalar, z / scalar, w / scalar); }

    Vec4& operator+=(const Vec4& other) { x += other.x; y += other.y; z += other.z; w += other.w; return *this; }

    constexpr Vec3 xyz() const { return Vec3(x, y, z); }
};

inline constexpr f32 dot(const Vec4& a, const Vec4& b) { return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w; }
inline f32 length(const Vec4& v) { return std::sqrt(dot(v, v)); }
inline Vec4 normalize(const Vec4& v) {
    const f32 magnitude = length(v);
    return magnitude > 0.0f ? v / magnitude : Vec4();
}
inline constexpr Vec4 lerp(const Vec4& a, const Vec4& b, f32 t) { return a + (b - a) * t; }

}
