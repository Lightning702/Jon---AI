#pragma once

#include "Mat3.hpp"
#include "Scalar.hpp"

namespace sf {

struct Quat {
    f32 x = 0.0f;
    f32 y = 0.0f;
    f32 z = 0.0f;
    f32 w = 1.0f;

    constexpr Quat() = default;
    constexpr Quat(f32 xValue, f32 yValue, f32 zValue, f32 wValue) : x(xValue), y(yValue), z(zValue), w(wValue) {}

    static Quat identity() { return Quat(); }

    static Quat fromAxisAngle(const Vec3& axis, f32 angleRadians) {
        const Vec3 unit = normalize(axis);
        const f32 half = angleRadians * 0.5f;
        const f32 sine = std::sin(half);
        return Quat(unit.x * sine, unit.y * sine, unit.z * sine, std::cos(half));
    }

    static Quat fromEuler(f32 pitchRadians, f32 yawRadians, f32 rollRadians) {
        const f32 cosPitch = std::cos(pitchRadians * 0.5f);
        const f32 sinPitch = std::sin(pitchRadians * 0.5f);
        const f32 cosYaw = std::cos(yawRadians * 0.5f);
        const f32 sinYaw = std::sin(yawRadians * 0.5f);
        const f32 cosRoll = std::cos(rollRadians * 0.5f);
        const f32 sinRoll = std::sin(rollRadians * 0.5f);
        return Quat(sinPitch * cosYaw * cosRoll - cosPitch * sinYaw * sinRoll,
                    cosPitch * sinYaw * cosRoll + sinPitch * cosYaw * sinRoll,
                    cosPitch * cosYaw * sinRoll - sinPitch * sinYaw * cosRoll,
                    cosPitch * cosYaw * cosRoll + sinPitch * sinYaw * sinRoll);
    }

    static Quat fromBasis(const Vec3& right, const Vec3& upDirection, const Vec3& forward) {
        Mat3 rotation = Mat3::fromColumns(right, upDirection, forward * -1.0f);
        const f32 trace = rotation.at(0, 0) + rotation.at(1, 1) + rotation.at(2, 2);
        Quat result;
        if (trace > 0.0f) {
            const f32 scale = std::sqrt(trace + 1.0f) * 2.0f;
            result.w = 0.25f * scale;
            result.x = (rotation.at(2, 1) - rotation.at(1, 2)) / scale;
            result.y = (rotation.at(0, 2) - rotation.at(2, 0)) / scale;
            result.z = (rotation.at(1, 0) - rotation.at(0, 1)) / scale;
        } else if (rotation.at(0, 0) > rotation.at(1, 1) && rotation.at(0, 0) > rotation.at(2, 2)) {
            const f32 scale = std::sqrt(1.0f + rotation.at(0, 0) - rotation.at(1, 1) - rotation.at(2, 2)) * 2.0f;
            result.w = (rotation.at(2, 1) - rotation.at(1, 2)) / scale;
            result.x = 0.25f * scale;
            result.y = (rotation.at(0, 1) + rotation.at(1, 0)) / scale;
            result.z = (rotation.at(0, 2) + rotation.at(2, 0)) / scale;
        } else if (rotation.at(1, 1) > rotation.at(2, 2)) {
            const f32 scale = std::sqrt(1.0f + rotation.at(1, 1) - rotation.at(0, 0) - rotation.at(2, 2)) * 2.0f;
            result.w = (rotation.at(0, 2) - rotation.at(2, 0)) / scale;
            result.x = (rotation.at(0, 1) + rotation.at(1, 0)) / scale;
            result.y = 0.25f * scale;
            result.z = (rotation.at(1, 2) + rotation.at(2, 1)) / scale;
        } else {
            const f32 scale = std::sqrt(1.0f + rotation.at(2, 2) - rotation.at(0, 0) - rotation.at(1, 1)) * 2.0f;
            result.w = (rotation.at(1, 0) - rotation.at(0, 1)) / scale;
            result.x = (rotation.at(0, 2) + rotation.at(2, 0)) / scale;
            result.y = (rotation.at(1, 2) + rotation.at(2, 1)) / scale;
            result.z = 0.25f * scale;
        }
        return result;
    }

    Quat operator*(const Quat& other) const {
        return Quat(w * other.x + x * other.w + y * other.z - z * other.y,
                    w * other.y - x * other.z + y * other.w + z * other.x,
                    w * other.z + x * other.y - y * other.x + z * other.w,
                    w * other.w - x * other.x - y * other.y - z * other.z);
    }

    Vec3 operator*(const Vec3& v) const {
        const Vec3 quaternionVector(x, y, z);
        const Vec3 firstCross = cross(quaternionVector, v);
        const Vec3 secondCross = cross(quaternionVector, firstCross);
        return v + ((firstCross * w) + secondCross) * 2.0f;
    }

    Quat conjugate() const { return Quat(-x, -y, -z, w); }

    Vec3 right() const { return (*this) * Vec3::unitX(); }
    Vec3 up() const { return (*this) * Vec3::unitY(); }
    Vec3 forward() const { return (*this) * Vec3(0.0f, 0.0f, -1.0f); }

    Mat3 toMat3() const {
        return Mat3::fromColumns(right(), up(), (*this) * Vec3::unitZ());
    }
};

inline f32 dot(const Quat& a, const Quat& b) { return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w; }

inline Quat normalize(const Quat& q) {
    const f32 magnitude = std::sqrt(dot(q, q));
    if (magnitude <= 0.0f) return Quat::identity();
    const f32 inverse = 1.0f / magnitude;
    return Quat(q.x * inverse, q.y * inverse, q.z * inverse, q.w * inverse);
}

inline Quat slerp(const Quat& a, const Quat& b, f32 t) {
    f32 cosine = dot(a, b);
    Quat target = b;
    if (cosine < 0.0f) {
        cosine = -cosine;
        target = Quat(-b.x, -b.y, -b.z, -b.w);
    }
    if (cosine > 0.9995f) {
        return normalize(Quat(a.x + (target.x - a.x) * t, a.y + (target.y - a.y) * t,
                              a.z + (target.z - a.z) * t, a.w + (target.w - a.w) * t));
    }
    const f32 angle = std::acos(clampValue(cosine, -1.0f, 1.0f));
    const f32 sine = std::sin(angle);
    const f32 weightA = std::sin((1.0f - t) * angle) / sine;
    const f32 weightB = std::sin(t * angle) / sine;
    return Quat(a.x * weightA + target.x * weightB, a.y * weightA + target.y * weightB,
                a.z * weightA + target.z * weightB, a.w * weightA + target.w * weightB);
}

inline Quat integrateAngularVelocity(const Quat& orientation, const Vec3& angularVelocity, f32 deltaSeconds) {
    const Quat spin(angularVelocity.x * 0.5f * deltaSeconds, angularVelocity.y * 0.5f * deltaSeconds,
                    angularVelocity.z * 0.5f * deltaSeconds, 0.0f);
    const Quat delta = spin * orientation;
    return normalize(Quat(orientation.x + delta.x, orientation.y + delta.y, orientation.z + delta.z,
                          orientation.w + delta.w));
}

}
