#pragma once

#include "../engine/math/DVec3.hpp"
#include "../engine/math/Quat.hpp"
#include "../engine/platform/Input.hpp"

namespace sf {

enum class ObserverMode : u32 {
    Orbit = 0,
    Free,
    Cinematic,
    Count
};

class ObserverController {
public:
    void reset(f64 radiusInGravitationalRadii, f64 inclinationDegrees);
    void update(const Input& input, f64 stepSeconds, bool interactionEnabled);

    void setMode(ObserverMode value) { mode = value; }
    void cycleMode();
    ObserverMode currentMode() const { return mode; }

    void setRadius(f64 radiusInGravitationalRadii);
    f64 radius() const { return orbitRadius; }
    f64 inclinationDegrees() const { return polarAngle * (180.0 / kPiDouble); }

    DVec3 positionInRadii() const;
    Quat orientation() const;
    f64 fieldOfViewDegrees() const { return fieldOfView; }
    f64 cinematicPhase() const { return cinematicTime; }

    static const char* modeName(ObserverMode value);

private:
    void updateOrbit(const Input& input, f64 stepSeconds, bool interactionEnabled);
    void updateFree(const Input& input, f64 stepSeconds, bool interactionEnabled);
    void updateCinematic(f64 stepSeconds);

    DVec3 freePosition = DVec3(0.0, 6.0, 42.0);
    f64 orbitRadius = 42.0;
    f64 targetRadius = 42.0;
    f64 azimuthAngle = 0.0;
    f64 polarAngle = 1.4661;
    f64 fieldOfView = 60.0;
    f64 cinematicTime = 0.0;
    f32 freeYaw = 0.0f;
    f32 freePitch = 0.0f;
    ObserverMode mode = ObserverMode::Orbit;
};

}
