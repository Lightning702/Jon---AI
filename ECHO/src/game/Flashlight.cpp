#include "Flashlight.h"

using namespace em;

namespace echo {

void Flashlight::reset() {
    on = false;
    battery = 1.0f;
    spares = 1;
    currentIntensity = 0.0f;
    flickerTimer = 0.0f;
    flickerStrength = 0.0f;
    disturbance = 0.0f;
    noisePhase = 0.0f;
    swayPhase = 0.0f;
}

void Flashlight::toggle() {
    setOn(!on);
}

void Flashlight::setOn(bool v) {
    if (v && battery <= 0.001f) {
        on = false;
        return;
    }
    on = v;
}

bool Flashlight::swapBattery() {
    if (spares <= 0) return false;
    spares--;
    battery = 1.0f;
    return true;
}

void Flashlight::disturb(float amount) {
    disturbance = clampf(disturbance + amount, 0.0f, 1.0f);
}

void Flashlight::forceFlicker(float duration, float strength) {
    flickerTimer = std::max(flickerTimer, duration);
    flickerStrength = std::max(flickerStrength, strength);
}

void Flashlight::update(const Vec3& eyePos, const Vec3& viewDir, const Vec3& rightDir, float dt, float time, float playerSpeed) {
    if (dt <= 0.0f) return;

    if (on) {
        battery = std::max(0.0f, battery - dt * 0.0058f);
        if (battery <= 0.0f) on = false;
    }

    swayPhase += dt * (1.4f + playerSpeed * 0.6f);
    noisePhase += dt * 7.0f;

    Vec3 handOffset = rightDir * 0.16f + Vec3(0, -0.14f, 0);
    Vec3 targetPos = eyePos + handOffset + viewDir * 0.10f;
    smoothPos = expDampV(smoothPos, targetPos, 26.0f, dt);

    float swayX = std::sin(swayPhase * 1.7f) * 0.012f + std::sin(swayPhase * 0.63f) * 0.006f;
    float swayY = std::sin(swayPhase * 1.1f + 1.7f) * 0.009f;
    Vec3 targetDir = normalize(viewDir + rightDir * swayX + Vec3(0, swayY, 0));
    smoothDir = normalize(expDampV(smoothDir, targetDir, 14.0f, dt));

    float target = 0.0f;
    if (on) {
        float low = smoothstepf(0.32f, 0.06f, battery);
        float flicker = 1.0f;

        if (flickerTimer > 0.0f) {
            flickerTimer -= dt;
            float n = hash11(std::floor(noisePhase * 3.4f) * 1.37f);
            flicker *= lerpf(1.0f, n > 0.45f ? 1.0f : 0.12f, flickerStrength);
        } else {
            flickerStrength = lerpf(flickerStrength, 0.0f, 1.0f - std::exp(-3.0f * dt));
        }

        if (low > 0.001f) {
            float n = hash11(std::floor(noisePhase * 2.2f) * 3.11f);
            float dip = n > (0.72f - low * 0.35f) ? 0.25f : 1.0f;
            flicker *= lerpf(1.0f, dip, low);
        }

        if (disturbance > 0.001f) {
            float n = hash11(std::floor(noisePhase * 5.0f) * 7.77f);
            flicker *= lerpf(1.0f, n > 0.6f ? 0.18f : 1.0f, disturbance);
        }

        float dim = lerpf(0.42f, 1.0f, smoothstepf(0.0f, 0.55f, battery));
        target = baseIntensity * dim * flicker;
    }

    float rate = target < currentIntensity ? 26.0f : 16.0f;
    currentIntensity = lerpf(currentIntensity, target, 1.0f - std::exp(-rate * dt));
    disturbance = lerpf(disturbance, 0.0f, 1.0f - std::exp(-0.75f * dt));
}

RenderLight Flashlight::buildLight() const {
    RenderLight l;
    l.position = smoothPos;
    l.direction = smoothDir;
    float warmth = smoothstepf(0.55f, 0.06f, battery);
    l.color = lerp(coldColor, warmColor, 0.55f + warmth * 0.45f);
    l.intensity = currentIntensity;
    l.range = baseRange * lerpf(0.62f, 1.0f, smoothstepf(0.0f, 0.5f, battery));
    l.spot = true;
    l.innerAngle = innerAngle;
    l.outerAngle = outerAngle;
    l.castShadows = true;
    l.priority = 1000.0f;
    l.volumetric = 0.45f;
    return l;
}

}
