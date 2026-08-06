#include "ObserverController.hpp"

#include "../engine/math/Scalar.hpp"

namespace sf {
namespace {

constexpr f64 kMinimumRadius = 1.45;
constexpr f64 kMaximumRadius = 4000.0;
constexpr f64 kCinematicCycle = 90.0;

f64 smoothBlend(f64 value) {
    const f64 clamped = clampValue(value, 0.0, 1.0);
    return clamped * clamped * (3.0 - 2.0 * clamped);
}

}

void ObserverController::reset(f64 radiusInGravitationalRadii, f64 inclinationDegrees) {
    orbitRadius = clampValue(radiusInGravitationalRadii, kMinimumRadius, kMaximumRadius);
    targetRadius = orbitRadius;
    polarAngle = clampValue(inclinationDegrees * (kPiDouble / 180.0), 0.04, kPiDouble - 0.04);
    azimuthAngle = 0.0;
    fieldOfView = 60.0;
    cinematicTime = 0.0;
    freePosition = positionInRadii();
    freeYaw = 0.0f;
    freePitch = 0.0f;
}

void ObserverController::setRadius(f64 radiusInGravitationalRadii) {
    targetRadius = clampValue(radiusInGravitationalRadii, kMinimumRadius, kMaximumRadius);
    orbitRadius = targetRadius;
}

void ObserverController::cycleMode() {
    mode = static_cast<ObserverMode>((static_cast<u32>(mode) + 1) % static_cast<u32>(ObserverMode::Count));
    if (mode == ObserverMode::Free) {
        freePosition = positionInRadii();
        const DVec3 forward = normalize(DVec3::zero() - freePosition);
        freePitch = static_cast<f32>(std::asin(clampValue(forward.y, -1.0, 1.0)));
        freeYaw = static_cast<f32>(std::atan2(forward.x, -forward.z));
    }
}

DVec3 ObserverController::positionInRadii() const {
    if (mode == ObserverMode::Free) return freePosition;
    const f64 sinePolar = std::sin(polarAngle);
    return DVec3(sinePolar * std::cos(azimuthAngle) * orbitRadius, std::cos(polarAngle) * orbitRadius,
                 sinePolar * std::sin(azimuthAngle) * orbitRadius);
}

Quat ObserverController::orientation() const {
    DVec3 forward;
    if (mode == ObserverMode::Free) {
        const f64 cosinePitch = std::cos(static_cast<f64>(freePitch));
        forward = DVec3(std::sin(static_cast<f64>(freeYaw)) * cosinePitch, std::sin(static_cast<f64>(freePitch)),
                        -std::cos(static_cast<f64>(freeYaw)) * cosinePitch);
    } else {
        const DVec3 position = positionInRadii();
        const f64 distance = length(position);
        forward = distance > 0.0 ? position / distance * -1.0 : DVec3(0.0, 0.0, -1.0);
    }

    const Vec3 forwardFloat = normalize(forward.toFloat());
    const Vec3 worldUp(0.0f, 1.0f, 0.0f);
    Vec3 right = cross(forwardFloat, worldUp);
    if (lengthSquared(right) < 1.0e-8f) right = Vec3::unitX();
    right = normalize(right);
    const Vec3 up = cross(right, forwardFloat);
    return Quat::fromBasis(right, up, forwardFloat);
}

void ObserverController::updateOrbit(const Input& input, f64 stepSeconds, bool interactionEnabled) {
    if (interactionEnabled) {
        if (input.mouseDown(MouseButton::Left)) {
            const Vec2 delta = input.mouseDelta();
            azimuthAngle -= static_cast<f64>(delta.x) * 0.0062;
            polarAngle = clampValue(polarAngle - static_cast<f64>(delta.y) * 0.0062, 0.04, kPiDouble - 0.04);
        }
        const f32 wheel = input.wheelDelta();
        if (std::fabs(wheel) > 0.0f) {
            targetRadius = clampValue(targetRadius * std::pow(0.86, static_cast<f64>(wheel)), kMinimumRadius,
                                      kMaximumRadius);
        }
        const f64 keyboardZoom = static_cast<f64>(input.axis(Key::W, Key::S));
        if (std::fabs(keyboardZoom) > 0.0) {
            targetRadius = clampValue(targetRadius * std::exp(-keyboardZoom * stepSeconds * 0.9), kMinimumRadius,
                                      kMaximumRadius);
        }
        azimuthAngle -= static_cast<f64>(input.axis(Key::D, Key::A)) * stepSeconds * 0.6;
        polarAngle = clampValue(polarAngle - static_cast<f64>(input.axis(Key::E, Key::Q)) * stepSeconds * 0.5, 0.04,
                                kPiDouble - 0.04);
    }
    orbitRadius = exponentialApproach(orbitRadius, targetRadius, 6.0, stepSeconds);
}

void ObserverController::updateFree(const Input& input, f64 stepSeconds, bool interactionEnabled) {
    if (!interactionEnabled) return;

    if (input.mouseDown(MouseButton::Left)) {
        const Vec2 delta = input.mouseDelta();
        freeYaw = wrapAngle(freeYaw - delta.x * 0.0042f);
        freePitch = clampValue(freePitch - delta.y * 0.0042f, -1.52f, 1.52f);
    }

    const f64 cosinePitch = std::cos(static_cast<f64>(freePitch));
    const DVec3 forward(std::sin(static_cast<f64>(freeYaw)) * cosinePitch, std::sin(static_cast<f64>(freePitch)),
                        -std::cos(static_cast<f64>(freeYaw)) * cosinePitch);
    const DVec3 right = normalize(cross(forward, DVec3::unitY()));
    const DVec3 up = cross(right, forward);

    const f64 distance = maxValue(length(freePosition), kMinimumRadius);
    f64 speed = distance * 0.55;
    if (input.keyDown(Key::LeftShift)) speed *= 4.0;
    if (input.keyDown(Key::LeftControl)) speed *= 0.22;

    DVec3 motion = forward * static_cast<f64>(input.axis(Key::W, Key::S));
    motion += right * static_cast<f64>(input.axis(Key::D, Key::A));
    motion += up * static_cast<f64>(input.axis(Key::E, Key::Q));
    if (lengthSquared(motion) > 1.0e-9) freePosition += normalize(motion) * (speed * stepSeconds);

    const f64 newDistance = length(freePosition);
    if (newDistance < kMinimumRadius) freePosition = normalize(freePosition) * kMinimumRadius;
    if (newDistance > kMaximumRadius) freePosition = normalize(freePosition) * kMaximumRadius;
    orbitRadius = length(freePosition);
    targetRadius = orbitRadius;
}

void ObserverController::updateCinematic(f64 stepSeconds) {
    cinematicTime += stepSeconds;
    while (cinematicTime >= kCinematicCycle) cinematicTime -= kCinematicCycle;

    struct Key {
        f64 time;
        f64 radius;
        f64 polar;
        f64 fieldOfView;
    };
    static const Key keys[] = {{0.0, 120.0, 1.30, 46.0},  {18.0, 74.0, 1.42, 50.0}, {40.0, 34.0, 1.20, 58.0},
                               {65.0, 11.0, 1.48, 70.0},  {82.0, 7.4, 1.52, 80.0},  {kCinematicCycle, 120.0, 1.30, 46.0}};

    for (u32 index = 0; index + 1 < 6; ++index) {
        if (cinematicTime < keys[index].time || cinematicTime > keys[index + 1].time) continue;
        const f64 span = maxValue(keys[index + 1].time - keys[index].time, 1.0e-4);
        const f64 alpha = smoothBlend((cinematicTime - keys[index].time) / span);
        orbitRadius = mixValue(keys[index].radius, keys[index + 1].radius, alpha);
        polarAngle = mixValue(keys[index].polar, keys[index + 1].polar, alpha);
        fieldOfView = mixValue(keys[index].fieldOfView, keys[index + 1].fieldOfView, alpha);
        break;
    }
    targetRadius = orbitRadius;
    azimuthAngle += stepSeconds * 0.055;
}

void ObserverController::update(const Input& input, f64 stepSeconds, bool interactionEnabled) {
    switch (mode) {
        case ObserverMode::Orbit: updateOrbit(input, stepSeconds, interactionEnabled); break;
        case ObserverMode::Free: updateFree(input, stepSeconds, interactionEnabled); break;
        default: updateCinematic(stepSeconds); break;
    }
    if (mode != ObserverMode::Cinematic && interactionEnabled) {
        const f64 zoomKeys = static_cast<f64>(input.axis(Key::Period, Key::Comma));
        fieldOfView = clampValue(fieldOfView - zoomKeys * stepSeconds * 22.0, 14.0, 110.0);
    }
}

const char* ObserverController::modeName(ObserverMode value) {
    switch (value) {
        case ObserverMode::Orbit: return "ORBIT";
        case ObserverMode::Free: return "FREIFLUG";
        case ObserverMode::Cinematic: return "KAMERAFAHRT";
        default: return "";
    }
}

}
