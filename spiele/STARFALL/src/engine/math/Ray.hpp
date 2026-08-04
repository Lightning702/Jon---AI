#pragma once

#include "AABB.hpp"
#include "Plane.hpp"
#include "Sphere.hpp"

namespace sf {

struct Ray {
    Vec3 origin = Vec3::zero();
    Vec3 direction = Vec3(0.0f, 0.0f, -1.0f);

    constexpr Ray() = default;
    Ray(const Vec3& originValue, const Vec3& directionValue) : origin(originValue), direction(directionValue) {}

    Vec3 at(f32 distanceAlongRay) const { return origin + direction * distanceAlongRay; }
};

inline bool intersectSphere(const Ray& ray, const Sphere& sphere, f32& nearHit, f32& farHit) {
    const Vec3 toCenter = ray.origin - sphere.center;
    const f32 a = dot(ray.direction, ray.direction);
    const f32 b = 2.0f * dot(toCenter, ray.direction);
    const f32 c = dot(toCenter, toCenter) - sphere.radius * sphere.radius;
    const f32 discriminant = b * b - 4.0f * a * c;
    if (discriminant < 0.0f) return false;
    const f32 root = std::sqrt(discriminant);
    nearHit = (-b - root) / (2.0f * a);
    farHit = (-b + root) / (2.0f * a);
    return farHit >= 0.0f;
}

inline bool intersectPlane(const Ray& ray, const Plane& plane, f32& hitDistance) {
    const f32 denominator = dot(plane.normalVector, ray.direction);
    if (std::fabs(denominator) < 1.0e-8f) return false;
    hitDistance = -(dot(plane.normalVector, ray.origin) + plane.distanceToOrigin) / denominator;
    return hitDistance >= 0.0f;
}

inline bool intersectAABB(const Ray& ray, const AABB& box, f32& nearHit, f32& farHit) {
    f32 tMin = -1.0e30f;
    f32 tMax = 1.0e30f;
    for (u32 axis = 0; axis < 3; ++axis) {
        const f32 originComponent = ray.origin.component(axis);
        const f32 directionComponent = ray.direction.component(axis);
        const f32 minimumComponent = box.minimum.component(axis);
        const f32 maximumComponent = box.maximum.component(axis);
        if (std::fabs(directionComponent) < 1.0e-8f) {
            if (originComponent < minimumComponent || originComponent > maximumComponent) return false;
            continue;
        }
        const f32 inverse = 1.0f / directionComponent;
        f32 entry = (minimumComponent - originComponent) * inverse;
        f32 exit = (maximumComponent - originComponent) * inverse;
        if (entry > exit) {
            const f32 swap = entry;
            entry = exit;
            exit = swap;
        }
        tMin = maxValue(tMin, entry);
        tMax = minValue(tMax, exit);
        if (tMin > tMax) return false;
    }
    nearHit = tMin;
    farHit = tMax;
    return tMax >= 0.0f;
}

}
