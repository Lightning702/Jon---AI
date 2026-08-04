#pragma once

#include "Vec3.hpp"

namespace sf {

struct AABB {
    Vec3 minimum = Vec3(1.0e30f);
    Vec3 maximum = Vec3(-1.0e30f);

    void reset() {
        minimum = Vec3(1.0e30f);
        maximum = Vec3(-1.0e30f);
    }

    void expand(const Vec3& point) {
        minimum = minComponents(minimum, point);
        maximum = maxComponents(maximum, point);
    }

    void expand(const AABB& other) {
        minimum = minComponents(minimum, other.minimum);
        maximum = maxComponents(maximum, other.maximum);
    }

    bool valid() const { return minimum.x <= maximum.x && minimum.y <= maximum.y && minimum.z <= maximum.z; }
    Vec3 center() const { return (minimum + maximum) * 0.5f; }
    Vec3 extent() const { return (maximum - minimum) * 0.5f; }
    Vec3 size() const { return maximum - minimum; }

    bool contains(const Vec3& point) const {
        return point.x >= minimum.x && point.x <= maximum.x && point.y >= minimum.y && point.y <= maximum.y &&
               point.z >= minimum.z && point.z <= maximum.z;
    }

    bool intersects(const AABB& other) const {
        return minimum.x <= other.maximum.x && maximum.x >= other.minimum.x &&
               minimum.y <= other.maximum.y && maximum.y >= other.minimum.y &&
               minimum.z <= other.maximum.z && maximum.z >= other.minimum.z;
    }

    f32 surfaceArea() const {
        const Vec3 dimensions = size();
        return 2.0f * (dimensions.x * dimensions.y + dimensions.y * dimensions.z + dimensions.z * dimensions.x);
    }
};

}
