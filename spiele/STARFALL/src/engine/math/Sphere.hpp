#pragma once

#include "AABB.hpp"

namespace sf {

struct Sphere {
    Vec3 center = Vec3::zero();
    f32 radius = 0.0f;

    constexpr Sphere() = default;
    constexpr Sphere(const Vec3& centerValue, f32 radiusValue) : center(centerValue), radius(radiusValue) {}

    bool contains(const Vec3& point) const { return lengthSquared(point - center) <= radius * radius; }

    bool intersects(const Sphere& other) const {
        const f32 combined = radius + other.radius;
        return lengthSquared(other.center - center) <= combined * combined;
    }

    AABB bounds() const {
        AABB box;
        box.minimum = center - Vec3(radius);
        box.maximum = center + Vec3(radius);
        return box;
    }
};

}
