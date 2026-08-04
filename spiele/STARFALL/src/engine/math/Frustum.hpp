#pragma once

#include "Mat4.hpp"
#include "Plane.hpp"
#include "Sphere.hpp"

namespace sf {

class Frustum {
public:
    void fromViewProjection(const Mat4& viewProjection) {
        const Mat4& p = viewProjection;
        planes[0] = Plane(Vec3(p.at(3, 0) + p.at(0, 0), p.at(3, 1) + p.at(0, 1), p.at(3, 2) + p.at(0, 2)),
                          p.at(3, 3) + p.at(0, 3));
        planes[1] = Plane(Vec3(p.at(3, 0) - p.at(0, 0), p.at(3, 1) - p.at(0, 1), p.at(3, 2) - p.at(0, 2)),
                          p.at(3, 3) - p.at(0, 3));
        planes[2] = Plane(Vec3(p.at(3, 0) + p.at(1, 0), p.at(3, 1) + p.at(1, 1), p.at(3, 2) + p.at(1, 2)),
                          p.at(3, 3) + p.at(1, 3));
        planes[3] = Plane(Vec3(p.at(3, 0) - p.at(1, 0), p.at(3, 1) - p.at(1, 1), p.at(3, 2) - p.at(1, 2)),
                          p.at(3, 3) - p.at(1, 3));
        planes[4] = Plane(Vec3(p.at(3, 0) + p.at(2, 0), p.at(3, 1) + p.at(2, 1), p.at(3, 2) + p.at(2, 2)),
                          p.at(3, 3) + p.at(2, 3));
        planes[5] = Plane(Vec3(p.at(3, 0) - p.at(2, 0), p.at(3, 1) - p.at(2, 1), p.at(3, 2) - p.at(2, 2)),
                          p.at(3, 3) - p.at(2, 3));
        for (Plane& plane : planes) plane.normalizePlane();
    }

    bool containsSphere(const Sphere& sphere) const {
        for (const Plane& plane : planes) {
            if (plane.signedDistance(sphere.center) < -sphere.radius) return false;
        }
        return true;
    }

    bool containsBox(const AABB& box) const {
        for (const Plane& plane : planes) {
            const Vec3 positive(plane.normalVector.x >= 0.0f ? box.maximum.x : box.minimum.x,
                                plane.normalVector.y >= 0.0f ? box.maximum.y : box.minimum.y,
                                plane.normalVector.z >= 0.0f ? box.maximum.z : box.minimum.z);
            if (plane.signedDistance(positive) < 0.0f) return false;
        }
        return true;
    }

    const Plane& plane(u32 index) const { return planes[index]; }

private:
    Plane planes[6];
};

}
