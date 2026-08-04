#pragma once

#include "../math/DVec3.hpp"
#include "../math/Frustum.hpp"
#include "../math/Mat4.hpp"
#include "../math/Quat.hpp"
#include "../math/Scalar.hpp"

namespace sf {

class Camera {
public:
    void setPerspective(f32 verticalFieldOfViewRadians, f32 aspectRatioValue, f32 nearPlaneValue, f32 farPlaneValue) {
        fieldOfView = verticalFieldOfViewRadians;
        aspect = aspectRatioValue;
        nearPlane = nearPlaneValue;
        farPlane = farPlaneValue;
        dirty = true;
    }

    void setAspectRatio(f32 value) {
        aspect = value;
        dirty = true;
    }

    void setWorldPosition(const DVec3& value) {
        worldPosition = value;
        dirty = true;
    }

    void setOrientation(const Quat& value) {
        orientation = normalize(value);
        dirty = true;
    }

    void setRenderOrigin(const DVec3& value) {
        renderOrigin = value;
        dirty = true;
    }

    const DVec3& position() const { return worldPosition; }
    const DVec3& origin() const { return renderOrigin; }
    const Quat& rotation() const { return orientation; }
    Vec3 forward() const { return orientation.forward(); }
    Vec3 up() const { return orientation.up(); }
    Vec3 right() const { return orientation.right(); }
    Vec3 relativePosition() const { return (worldPosition - renderOrigin).toFloat(); }

    f32 verticalFieldOfView() const { return fieldOfView; }
    f32 aspectRatio() const { return aspect; }
    f32 nearDistance() const { return nearPlane; }
    f32 farDistance() const { return farPlane; }

    const Mat4& viewMatrix() const {
        refresh();
        return view;
    }

    const Mat4& projectionMatrix() const {
        refresh();
        return projection;
    }

    const Mat4& viewProjectionMatrix() const {
        refresh();
        return viewProjection;
    }

    const Mat4& inverseViewProjectionMatrix() const {
        refresh();
        return inverseViewProjection;
    }

    const Frustum& frustum() const {
        refresh();
        return cachedFrustum;
    }

private:
    void refresh() const {
        if (!dirty) return;
        const Vec3 eye = relativePosition();
        view = Mat4::lookAt(eye, eye + orientation.forward(), orientation.up());
        projection = Mat4::perspective(fieldOfView, aspect, nearPlane, farPlane);
        viewProjection = projection * view;
        inverseViewProjection = viewProjection.inverted();
        cachedFrustum.fromViewProjection(viewProjection);
        dirty = false;
    }

    DVec3 worldPosition = DVec3::zero();
    DVec3 renderOrigin = DVec3::zero();
    Quat orientation = Quat::identity();
    f32 fieldOfView = radians(65.0f);
    f32 aspect = 16.0f / 9.0f;
    f32 nearPlane = 0.1f;
    f32 farPlane = 5.0e7f;

    mutable Mat4 view;
    mutable Mat4 projection;
    mutable Mat4 viewProjection;
    mutable Mat4 inverseViewProjection;
    mutable Frustum cachedFrustum;
    mutable bool dirty = true;
};

}
