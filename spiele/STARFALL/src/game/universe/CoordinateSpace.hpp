#pragma once

#include "../../engine/math/DVec3.hpp"
#include "UniverseSeed.hpp"

namespace sf {

struct UniversePosition {
    GalaxyCoord galaxy;
    SystemCoord system;
    DVec3 local = DVec3::zero();

    DVec3 systemMetersFromGalaxyOrigin() const {
        return DVec3(static_cast<f64>(system.x), static_cast<f64>(system.y), static_cast<f64>(system.z)) *
               kLightYear;
    }

    bool sameSystem(const UniversePosition& other) const {
        return galaxy == other.galaxy && system == other.system;
    }

    DVec3 differenceWithin(const UniversePosition& other) const {
        const DVec3 systemOffset = systemMetersFromGalaxyOrigin() - other.systemMetersFromGalaxyOrigin();
        return systemOffset + local - other.local;
    }
};

class FloatingOrigin {
public:
    explicit FloatingOrigin(f64 rebaseDistance = 4096.0) : threshold(rebaseDistance) {}

    bool update(const DVec3& cameraWorldPosition) {
        const DVec3 offset = cameraWorldPosition - originValue;
        if (length(offset) < threshold) return false;
        originValue = cameraWorldPosition;
        ++rebaseCount;
        return true;
    }

    void forceOrigin(const DVec3& value) {
        originValue = value;
        ++rebaseCount;
    }

    const DVec3& origin() const { return originValue; }
    Vec3 toRenderSpace(const DVec3& worldPosition) const { return (worldPosition - originValue).toFloat(); }
    DVec3 toWorldSpace(const Vec3& renderPosition) const { return originValue + fromFloat(renderPosition); }
    u64 rebases() const { return rebaseCount; }
    f64 rebaseThreshold() const { return threshold; }

private:
    DVec3 originValue = DVec3::zero();
    f64 threshold;
    u64 rebaseCount = 0;
};

}
