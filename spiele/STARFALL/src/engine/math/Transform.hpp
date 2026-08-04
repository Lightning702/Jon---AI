#pragma once

#include "DVec3.hpp"
#include "Mat4.hpp"
#include "Quat.hpp"

namespace sf {

struct Transform {
    Vec3 position = Vec3::zero();
    Quat rotation = Quat::identity();
    Vec3 scale = Vec3::one();

    Mat4 toMatrix() const {
        const Mat3 basis = rotation.toMat3();
        Mat4 result = Mat4::fromMat3(basis);
        result.at(0, 0) *= scale.x; result.at(1, 0) *= scale.x; result.at(2, 0) *= scale.x;
        result.at(0, 1) *= scale.y; result.at(1, 1) *= scale.y; result.at(2, 1) *= scale.y;
        result.at(0, 2) *= scale.z; result.at(1, 2) *= scale.z; result.at(2, 2) *= scale.z;
        result.m[12] = position.x;
        result.m[13] = position.y;
        result.m[14] = position.z;
        return result;
    }

    Vec3 transformPoint(const Vec3& point) const { return position + rotation * (point * scale); }
    Vec3 transformDirection(const Vec3& direction) const { return rotation * direction; }

    Transform combined(const Transform& child) const {
        Transform result;
        result.position = transformPoint(child.position);
        result.rotation = rotation * child.rotation;
        result.scale = scale * child.scale;
        return result;
    }
};

struct WorldTransform {
    DVec3 position = DVec3::zero();
    Quat rotation = Quat::identity();
    f64 scale = 1.0;

    Transform relativeTo(const DVec3& origin) const {
        Transform result;
        result.position = (position - origin).toFloat();
        result.rotation = rotation;
        result.scale = Vec3(static_cast<f32>(scale));
        return result;
    }
};

}
