#pragma once

#include "../core/Types.hpp"

#include <cmath>

namespace sf {

struct Vec2 {
    f32 x = 0.0f;
    f32 y = 0.0f;

    constexpr Vec2() = default;
    constexpr Vec2(f32 xValue, f32 yValue) : x(xValue), y(yValue) {}
    explicit constexpr Vec2(f32 scalar) : x(scalar), y(scalar) {}

    constexpr Vec2 operator+(const Vec2& other) const { return Vec2(x + other.x, y + other.y); }
    constexpr Vec2 operator-(const Vec2& other) const { return Vec2(x - other.x, y - other.y); }
    constexpr Vec2 operator*(f32 scalar) const { return Vec2(x * scalar, y * scalar); }
    constexpr Vec2 operator/(f32 scalar) const { return Vec2(x / scalar, y / scalar); }
    constexpr Vec2 operator*(const Vec2& other) const { return Vec2(x * other.x, y * other.y); }
    constexpr Vec2 operator-() const { return Vec2(-x, -y); }

    Vec2& operator+=(const Vec2& other) { x += other.x; y += other.y; return *this; }
    Vec2& operator-=(const Vec2& other) { x -= other.x; y -= other.y; return *this; }
    Vec2& operator*=(f32 scalar) { x *= scalar; y *= scalar; return *this; }

    bool operator==(const Vec2& other) const { return x == other.x && y == other.y; }
    bool operator!=(const Vec2& other) const { return !(*this == other); }
};

inline constexpr f32 dot(const Vec2& a, const Vec2& b) { return a.x * b.x + a.y * b.y; }
inline f32 length(const Vec2& v) { return std::sqrt(dot(v, v)); }
inline constexpr f32 lengthSquared(const Vec2& v) { return dot(v, v); }
inline Vec2 normalize(const Vec2& v) {
    const f32 magnitude = length(v);
    return magnitude > 0.0f ? v / magnitude : Vec2(0.0f, 0.0f);
}
inline constexpr Vec2 lerp(const Vec2& a, const Vec2& b, f32 t) { return a + (b - a) * t; }
inline f32 crossZ(const Vec2& a, const Vec2& b) { return a.x * b.y - a.y * b.x; }

}
