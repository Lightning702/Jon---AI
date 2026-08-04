#include "SpaceFlightController.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {

void SpaceFlightController::cycleMode() {
    const u32 next = (static_cast<u32>(mode) + 1) % static_cast<u32>(FlightMode::Count);
    mode = static_cast<FlightMode>(next);
}

f64 SpaceFlightController::atmosphericDensityAt(f64 altitudeMeters, f64 surfaceDensity, f64 scaleHeightMeters) {
    if (altitudeMeters < 0.0) altitudeMeters = 0.0;
    if (scaleHeightMeters <= 0.0) return 0.0;
    return surfaceDensity * std::exp(-altitudeMeters / scaleHeightMeters);
}

const char* SpaceFlightController::modeName(FlightMode value) {
    switch (value) {
        case FlightMode::Newtonian: return "NEWTONISCH";
        case FlightMode::Assisted: return "ASSISTIERT";
        case FlightMode::Atmospheric: return "ATMOSPHAERISCH";
        case FlightMode::Docking: return "ANDOCKEN";
        default: return "UNBEKANNT";
    }
}

void SpaceFlightController::applyRotation(FlightState& state, f64 stepSeconds) {
    const f64 authority = mode == FlightMode::Atmospheric
                              ? specification.controlSurfaceEffectiveness *
                                    clampValue(state.atmosphericDensity / 1.225, 0.12, 1.4)
                              : 1.0;
    const f64 angularAcceleration = specification.angularThrustNewtonMetres * authority /
                                    maxValue(specification.momentOfInertia, 1.0);

    const Vec3 localTorque(static_cast<f32>(input.pitch * angularAcceleration * stepSeconds),
                           static_cast<f32>(input.yaw * angularAcceleration * stepSeconds),
                           static_cast<f32>(input.roll * angularAcceleration * stepSeconds));

    state.angularVelocity += state.orientation * localTorque;

    f64 dampingRate = 0.0;
    switch (mode) {
        case FlightMode::Newtonian: dampingRate = 0.05; break;
        case FlightMode::Assisted: dampingRate = 3.4; break;
        case FlightMode::Atmospheric: dampingRate = 2.2; break;
        case FlightMode::Docking: dampingRate = 6.0; break;
        default: dampingRate = 1.0; break;
    }
    const f32 damping = static_cast<f32>(std::exp(-dampingRate * stepSeconds));
    state.angularVelocity *= damping;

    const f32 maximumRate = mode == FlightMode::Docking ? 0.45f : 2.6f;
    const f32 rate = length(state.angularVelocity);
    if (rate > maximumRate) state.angularVelocity *= maximumRate / rate;

    state.orientation = integrateAngularVelocity(state.orientation, state.angularVelocity,
                                                 static_cast<f32>(stepSeconds));
}

void SpaceFlightController::applyTranslation(FlightState& state, f64 stepSeconds) {
    const f64 mass = maxValue(currentMassKilograms(), 1.0);

    f64 commandedThrottle = static_cast<f64>(input.throttle);
    if (input.zeroThrust) commandedThrottle = 0.0;
    if (input.holdThrust) commandedThrottle = state.throttleLevel;
    if (mode == FlightMode::Docking) commandedThrottle = clampValue(commandedThrottle, -0.25, 0.25);

    const f64 responseRate = mode == FlightMode::Docking ? 6.0 : 3.0;
    state.throttleLevel = exponentialApproach(state.throttleLevel, clampValue(commandedThrottle, -1.0, 1.0),
                                              responseRate, stepSeconds);

    f64 thrust = specification.mainThrustNewtons * state.throttleLevel;
    const bool burnerActive = input.afterburner && state.fuelKilograms > 0.0 && mode != FlightMode::Docking;
    if (burnerActive) thrust *= specification.afterburnerMultiplier;
    lastThrust = thrust;

    const Vec3 forwardAxis = state.orientation.forward();
    const Vec3 rightAxis = state.orientation.right();
    const Vec3 upAxis = state.orientation.up();

    DVec3 acceleration = DVec3(fromFloat(forwardAxis)) * (thrust / mass);
    acceleration += DVec3(fromFloat(rightAxis)) *
                    (specification.manoeuvringThrustNewtons * static_cast<f64>(input.strafeHorizontal) / mass);
    acceleration += DVec3(fromFloat(upAxis)) *
                    (specification.manoeuvringThrustNewtons * static_cast<f64>(input.strafeVertical) / mass);

    state.velocity += acceleration * stepSeconds;
    lastAcceleration = length(acceleration);

    const f64 fuelBurnRate = (std::fabs(state.throttleLevel) * (burnerActive ? 2.4 : 1.0) * 0.42) +
                             (std::fabs(static_cast<f64>(input.strafeHorizontal)) +
                              std::fabs(static_cast<f64>(input.strafeVertical))) * 0.12;
    state.fuelKilograms = maxValue(state.fuelKilograms - fuelBurnRate * stepSeconds, 0.0);

    const f64 heatGeneration = std::fabs(state.throttleLevel) * (burnerActive ? 2.8 : 1.0) * 0.16;
    const f64 heatDissipation = 0.22 * (1.0 + state.atmosphericDensity * 2.0);
    state.heatLevel = clampValue(state.heatLevel + (heatGeneration - heatDissipation * state.heatLevel) * stepSeconds,
                                 0.0, 1.6);

    if (input.brake || mode == FlightMode::Assisted) {
        const f64 brakeRate = input.brake ? 1.6 : (std::fabs(state.throttleLevel) < 0.02 ? 0.22 : 0.0);
        if (brakeRate > 0.0) {
            const f64 factor = std::exp(-brakeRate * stepSeconds);
            state.velocity *= factor;
        }
    }

    const f64 speed = length(state.velocity);
    const f64 limit = mode == FlightMode::Docking ? 120.0 : specification.impulseSpeedLimit;
    if (speed > limit) state.velocity *= limit / speed;
}

void SpaceFlightController::applyAerodynamics(FlightState& state, f64 stepSeconds) {
    if (state.atmosphericDensity <= 1.0e-8) {
        state.dynamicPressure = 0.0;
        state.angleOfAttackRadians = 0.0;
        state.machNumber = 0.0;
        state.plasmaSheath = false;
        state.communicationBlackout = false;
        return;
    }

    const f64 speed = length(state.velocity);
    if (speed < 0.5) {
        state.dynamicPressure = 0.0;
        return;
    }

    const DVec3 flowDirection = state.velocity / speed;
    const Vec3 forwardAxis = state.orientation.forward();
    const f64 alignment = clampValue(dot(flowDirection, DVec3(fromFloat(forwardAxis))), -1.0, 1.0);
    state.angleOfAttackRadians = std::acos(alignment);

    state.dynamicPressure = 0.5 * state.atmosphericDensity * speed * speed;
    const f64 speedOfSound = 340.0 * std::sqrt(maxValue(state.atmosphericDensity / 1.225, 0.05));
    state.machNumber = speed / maxValue(speedOfSound, 1.0);

    const f64 mass = maxValue(currentMassKilograms(), 1.0);
    const f64 dragMagnitude = state.dynamicPressure * specification.dragCoefficient *
                              specification.referenceAreaSquareMetres *
                              (1.0 + std::sin(state.angleOfAttackRadians) * 2.4);
    state.velocity -= flowDirection * (dragMagnitude / mass * stepSeconds);

    const f64 liftCoefficient = specification.liftCoefficientSlope * std::sin(state.angleOfAttackRadians) *
                                std::cos(state.angleOfAttackRadians);
    const f64 liftMagnitude = state.dynamicPressure * liftCoefficient * specification.referenceAreaSquareMetres;
    const Vec3 upAxis = state.orientation.up();
    state.velocity += DVec3(fromFloat(upAxis)) * (liftMagnitude / mass * stepSeconds);

    const f64 heatFlux = state.dynamicPressure * speed * 1.0e-9;
    state.heatLevel = clampValue(state.heatLevel + heatFlux * stepSeconds, 0.0, 3.0);
    state.plasmaSheath = state.machNumber > 6.0 && state.dynamicPressure > 4000.0;
    state.communicationBlackout = state.plasmaSheath && state.machNumber > 9.0;

    if (state.heatLevel > 1.4) {
        state.hullStress = clampValue(state.hullStress + (state.heatLevel - 1.4) * 0.14 * stepSeconds, 0.0, 1.0);
    }
}

void SpaceFlightController::step(FlightState& state, const DVec3& gravitationalAcceleration, f64 stepSeconds) {
    if (stepSeconds <= 0.0) return;
    applyRotation(state, stepSeconds);
    applyTranslation(state, stepSeconds);
    applyAerodynamics(state, stepSeconds);
    state.velocity += gravitationalAcceleration * stepSeconds;
    state.position += state.velocity * stepSeconds;
}

}
