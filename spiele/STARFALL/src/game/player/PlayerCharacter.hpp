#pragma once

#include "../../engine/platform/Input.hpp"
#include "../planet/PlanetSurface.hpp"
#include "Inventory.hpp"
#include "SurvivalStats.hpp"

namespace sf {

enum class ToolMode : u32 {
    MiningBeam = 0,
    TerrainManipulator,
    Scanner,
    BuildMode,
    Count
};

struct FootInput {
    f32 forward = 0.0f;
    f32 strafe = 0.0f;
    f32 lookYaw = 0.0f;
    f32 lookPitch = 0.0f;
    bool sprint = false;
    bool crouch = false;
    bool jump = false;
    bool jetpack = false;
    bool useTool = false;
    bool interact = false;
};

class PlayerCharacter {
public:
    void spawnOn(const PlanetBody& body, const DVec3& unitDirection);
    void detachFromSurface();

    void step(const PlanetBody& body, const FootInput& input, f64 stepSeconds);

    const DVec3& localPosition() const { return position; }
    void setLocalPosition(const DVec3& value) { position = value; }
    const DVec3& velocity() const { return linearVelocity; }
    DVec3 eyePosition() const { return position + upDirection * static_cast<f64>(eyeHeight); }
    DVec3 lookDirection() const;
    Quat orientation() const;
    const DVec3& up() const { return upDirection; }

    bool grounded() const { return onGround; }
    f32 headingYaw() const { return yaw; }
    f32 headingPitch() const { return pitch; }
    f32 currentSpeed() const { return static_cast<f32>(length(linearVelocity)); }

    ToolMode toolMode() const { return activeTool; }
    void setToolMode(ToolMode mode) { activeTool = mode; }
    void cycleTool();

    SurvivalStats& survival() { return survivalStats; }
    const SurvivalStats& survival() const { return survivalStats; }
    Inventory& inventory() { return suitInventory; }
    const Inventory& inventory() const { return suitInventory; }

    void configureInventory(u32 slotCount);
    f32 beamCharge() const { return beamHeat; }
    void setBeamCharge(f32 value) { beamHeat = clampValue(value, 0.0f, 1.4f); }

private:
    DVec3 position = DVec3::zero();
    DVec3 linearVelocity = DVec3::zero();
    DVec3 upDirection = DVec3::unitY();
    Inventory suitInventory;
    SurvivalStats survivalStats;
    f32 yaw = 0.0f;
    f32 pitch = 0.0f;
    f32 eyeHeight = 1.72f;
    f32 standHeight = 1.85f;
    f32 crouchHeight = 1.05f;
    f32 beamHeat = 0.0f;
    bool onGround = false;
    bool attached = false;
    ToolMode activeTool = ToolMode::MiningBeam;
};

}
