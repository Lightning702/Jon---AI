#pragma once

#include "../core/Math.h"
#include "../render/Renderer.h"

namespace echo {

class Flashlight {
public:
    void reset();
    void toggle();
    void setOn(bool v);
    bool isOn() const { return on; }
    bool hasBattery() const { return battery > 0.001f; }

    void update(const em::Vec3& eyePos, const em::Vec3& viewDir, const em::Vec3& rightDir, float dt, float time, float playerSpeed);
    RenderLight buildLight() const;

    float batteryLevel() const { return battery; }
    void setBattery(float v) { battery = em::clampf(v, 0.0f, 1.0f); }
    void addBattery(float v) { battery = em::clampf(battery + v, 0.0f, 1.0f); }
    int spareBatteries() const { return spares; }
    void addSpare(int n) { spares += n; }
    bool swapBattery();

    void disturb(float amount);
    void forceFlicker(float duration, float strength);

    float glowIntensity() const { return currentIntensity; }
    em::Vec3 beamOrigin() const { return smoothPos; }
    em::Vec3 beamDirection() const { return smoothDir; }

    float baseIntensity = 7.2f;
    float baseRange = 17.0f;
    float innerAngle = 0.30f;
    float outerAngle = 0.62f;
    em::Vec3 warmColor = em::Vec3(1.0f, 0.93f, 0.80f);
    em::Vec3 coldColor = em::Vec3(0.72f, 0.80f, 1.0f);

private:
    bool on = false;
    float battery = 1.0f;
    int spares = 0;
    float currentIntensity = 0.0f;
    float flickerTimer = 0.0f;
    float flickerStrength = 0.0f;
    float disturbance = 0.0f;
    float noisePhase = 0.0f;
    float swayPhase = 0.0f;
    em::Vec3 smoothPos;
    em::Vec3 smoothDir = em::Vec3(0, 0, -1);
};

}
