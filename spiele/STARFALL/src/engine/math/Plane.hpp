#pragma once

#include "Vec3.hpp"

namespace sf {

struct Plane {
    Vec3 normalVector = Vec3::unitY();
    f32 distanceToOrigin = 0.0f;

    constexpr Plane() = default;
    Plane(const Vec3& normalValue, f32 distanceValue)
        : normalVector(normalValue), distanceToOrigin(distanceValue) {}

    static Plane fromPointAndNormal(const Vec3& point, const Vec3& normalValue) {
        const Vec3 unit = normalize(normalValue);
        return Plane(unit, -dot(unit, point));
    }

    void normalizePlane() {
        const f32 magnitude = length(normalVector);
        if (magnitude <= 0.0f) return;
        normalVector = normalVector / magnitude;
        distanceToOrigin /= magnitude;
    }

    f32 signedDistance(const Vec3& point) const { return dot(normalVector, point) + distanceToOrigin; }
};

}
