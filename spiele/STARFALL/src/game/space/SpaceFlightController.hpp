#pragma once

#include "../../engine/math/DVec3.hpp"
#include "../../engine/math/Quat.hpp"
#include "../../engine/platform/Input.hpp"

namespace sf {

enum class FlightMode : u32 {
    Newtonian = 0,
    Assisted,
    Atmospheric,
    Docking,
    Count
};

struct FlightInput {
    f32 throttle = 0.0f;
    f32 strafeHorizontal = 0.0f;
    f32 strafeVertical = 0.0f;
    f32 pitch = 0.0f;
    f32 yaw = 0.0f;
    f32 roll = 0.0f;
    bool afterburner = false;
    bool brake = false;
    bool holdThrust = false;
    bool zeroThrust = false;
};

struct FlightVehicleSpecification {
    f64 dryMassKilograms = 42000.0;
    f64 cargoMassKilograms = 0.0;
    f64 mainThrustNewtons = 2.6e6;
    f64 afterburnerMultiplier = 3.2;
    f64 manoeuvringThrustNewtons = 4.4e5;
    f64 angularThrustNewtonMetres = 9.0e5;
    f64 momentOfInertia = 5.6e6;
    f64 referenceAreaSquareMetres = 84.0;
    f64 dragCoefficient = 0.62;
    f64 liftCoefficientSlope = 3.4;
    f64 controlSurfaceEffectiveness = 1.0;
    f64 maximumManoeuvreSpeed = 1500.0;
    f64 impulseSpeedLimit = 0.1 * kSpeedOfLight;
};

struct FlightState {
    DVec3 position = DVec3::zero();
    DVec3 velocity = DVec3::zero();
    Quat orientation = Quat::identity();
    Vec3 angularVelocity = Vec3::zero();
    f64 throttleLevel = 0.0;
    f64 heatLevel = 0.0;
    f64 fuelKilograms = 4000.0;
    f64 hullStress = 0.0;
    f64 atmosphericDensity = 0.0;
    f64 dynamicPressure = 0.0;
    f64 angleOfAttackRadians = 0.0;
    f64 machNumber = 0.0;
    bool plasmaSheath = false;
    bool communicationBlackout = false;
};

class SpaceFlightController {
public:
    void setSpecification(const FlightVehicleSpecification& value) { specification = value; }
    const FlightVehicleSpecification& specification_() const { return specification; }

    void setMode(FlightMode value) { mode = value; }
    FlightMode currentMode() const { return mode; }
    void cycleMode();

    void applyInput(const FlightInput& value) { input = value; }
    FlightInput& mutableInput() { return input; }

    void step(FlightState& state, const DVec3& gravitationalAcceleration, f64 stepSeconds);

    f64 currentMassKilograms() const { return specification.dryMassKilograms + specification.cargoMassKilograms; }
    f64 lastThrustNewtons() const { return lastThrust; }
    f64 lastAccelerationMetresPerSecondSquared() const { return lastAcceleration; }

    static f64 atmosphericDensityAt(f64 altitudeMeters, f64 surfaceDensity, f64 scaleHeightMeters);
    static const char* modeName(FlightMode value);

private:
    void applyRotation(FlightState& state, f64 stepSeconds);
    void applyTranslation(FlightState& state, f64 stepSeconds);
    void applyAerodynamics(FlightState& state, f64 stepSeconds);

    FlightVehicleSpecification specification;
    FlightInput input;
    FlightMode mode = FlightMode::Assisted;
    f64 lastThrust = 0.0;
    f64 lastAcceleration = 0.0;
};

}
