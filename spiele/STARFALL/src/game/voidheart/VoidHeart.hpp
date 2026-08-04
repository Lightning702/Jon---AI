#pragma once

#include "../../engine/math/DVec3.hpp"
#include "../../engine/render/BlackHolePass.hpp"
#include "../universe/CoordinateSpace.hpp"

#include <string>

namespace sf {

enum class VoidZone : u32 {
    FarField = 5,
    GravityDrift = 4,
    Distortion = 3,
    Ergosphere = 2,
    HorizonProximity = 1,
    EventHorizon = 0
};

struct VoidHeartState {
    f64 distanceMeters = 0.0;
    f64 radiusInGravitationalRadii = 1.0e9;
    VoidZone zone = VoidZone::FarField;
    f64 timeDilation = 1.0;
    f64 frameDraggingAngularRate = 0.0;
    f64 tidalStressPerSecond = 0.0;
    f64 shieldDrainPerSecond = 0.0;
    f64 instrumentNoise = 0.0;
    f64 hyperdriveChargeMultiplier = 1.0;
    f64 fuelConsumptionMultiplier = 1.0;
    DVec3 gravitationalAcceleration = DVec3::zero();
    bool voidDriveRequired = false;
    bool escapePossible = true;
};

class VoidHeart {
public:
    VoidHeart();

    void configure(const SystemCoord& hostSystem, const DVec3& localPosition);

    const SystemCoord& systemCoordinate() const { return coordinate; }
    const DVec3& localPosition() const { return position; }

    f64 massKilograms() const { return massValue; }
    f64 massSolar() const { return massValue / kSolarMass; }
    f64 spin() const { return spinValue; }
    f64 gravitationalRadiusMeters() const { return gravitationalRadius; }
    f64 schwarzschildRadiusMeters() const { return gravitationalRadius * 2.0; }
    f64 horizonRadiusMeters() const;
    f64 ergosphereEquatorialRadiusMeters() const;
    f64 photonSphereRadiusMeters() const;
    f64 innermostStableOrbitMeters() const;
    f64 distortionZoneRadiusMeters() const { return gravitationalRadius * 90.0; }
    f64 driftZoneRadiusMeters() const { return gravitationalRadius * 600.0; }
    f64 influenceRadiusMeters() const { return gravitationalRadius * 12000.0; }

    VoidHeartState evaluate(const DVec3& observerLocalPosition) const;
    BlackHoleRenderParameters renderParameters(const DVec3& centerWorldPosition, f32 elapsedSeconds,
                                               f32 qualityScale) const;

    f64 orbitalSpeedAt(f64 radiusMeters) const;
    f64 escapeSpeedAt(f64 radiusMeters) const;
    bool withinInfluence(const DVec3& observerLocalPosition) const;

    static const char* zoneName(VoidZone zone);
    static const char* zoneDescription(VoidZone zone);

private:
    SystemCoord coordinate;
    DVec3 position = DVec3::zero();
    f64 massValue = 4.1e6 * kSolarMass;
    f64 spinValue = 0.94;
    f64 gravitationalRadius = 0.0;
    f64 accretionDiskOuterRadii = 26.0;
};

}
