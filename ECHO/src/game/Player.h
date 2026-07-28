#pragma once

#include "../core/Math.h"
#include "../physics/PhysicsWorld.h"
#include "../render/Renderer.h"

namespace echo {

struct PlayerInput {
    em::Vec2 move = em::Vec2(0, 0);
    em::Vec2 look = em::Vec2(0, 0);
    bool sprint = false;
    bool crouch = false;
    bool jump = false;
    bool interact = false;
    bool focus = false;
};

enum class FootstepSurface { Tile, Concrete, Linoleum, Metal, Water, Debris };

struct FootstepEvent {
    em::Vec3 position;
    FootstepSurface surface = FootstepSurface::Tile;
    float loudness = 1.0f;
};

class Player {
public:
    void reset(const em::Vec3& spawn, float yaw);
    void update(const PlayerInput& in, const PhysicsWorld& world, float dt);

    CameraData buildCamera(float aspect) const;
    em::Vec3 eyePosition() const;
    em::Vec3 forward() const;
    em::Vec3 right() const;
    em::Vec3 flatForward() const;

    const em::Vec3& position() const { return pos; }
    void setPosition(const em::Vec3& p) { pos = p; velocity = em::Vec3(0); }
    const em::Vec3& velocityVec() const { return velocity; }
    float yawAngle() const { return yaw; }
    float pitchAngle() const { return pitch; }
    void setOrientation(float y, float p) { yaw = y; pitch = p; }

    bool isCrouching() const { return crouching; }
    bool isSprinting() const { return sprinting; }
    bool isGrounded() const { return grounded; }
    bool isMoving() const { return em::length(em::Vec2(velocity.x, velocity.z)) > 0.25f; }
    float speed() const { return em::length(em::Vec2(velocity.x, velocity.z)); }
    float stamina() const { return staminaValue; }
    float breathLevel() const { return breath; }
    float noiseLevel() const { return noise; }
    float eyeHeight() const { return currentEye; }

    bool consumeFootstep(FootstepEvent& out);
    void addShake(float amount, float duration);
    void addRecoilLook(float yawDelta, float pitchDelta);
    void forceLookAt(const em::Vec3& target, float strength);
    void setSurface(FootstepSurface s) { surface = s; }
    void setMovementLock(bool locked) { movementLocked = locked; }
    bool movementLocked_() const { return movementLocked; }
    void setSensitivity(float s) { sensitivity = s; }
    float sensitivity_() const { return sensitivity; }
    void setInvertY(bool v) { invertY = v; }
    bool invertY_() const { return invertY; }
    void setFovBase(float f) { fovBase = f; }
    float fovBase_() const { return fovBase; }

    float headTiltTarget = 0.0f;
    float exhaustion = 0.0f;

private:
    void applyLook(const PlayerInput& in, float dt);
    void applyMovement(const PlayerInput& in, const PhysicsWorld& world, float dt);
    void updateBob(float dt);

    em::Vec3 pos = em::Vec3(0, 0, 0);
    em::Vec3 velocity = em::Vec3(0, 0, 0);
    float yaw = 0.0f, pitch = 0.0f;
    float sensitivity = 0.0022f;
    bool invertY = false;
    float fovBase = 1.204f;

    float radius = 0.30f;
    float standHeight = 1.78f;
    float crouchHeight = 1.10f;
    float currentHeight = 1.78f;
    float standEye = 1.66f;
    float crouchEye = 0.95f;
    float currentEye = 1.66f;

    bool crouching = false;
    bool sprinting = false;
    bool grounded = true;
    bool movementLocked = false;

    float staminaValue = 1.0f;
    float breath = 0.0f;
    float noise = 0.0f;

    float bobTime = 0.0f;
    float bobAmount = 0.0f;
    float stepAccum = 0.0f;
    int stepParity = 0;
    em::Vec3 bobOffset = em::Vec3(0, 0, 0);
    float rollAngle = 0.0f;
    float pitchBob = 0.0f;
    float landImpact = 0.0f;

    float shakeAmount = 0.0f;
    float shakeTime = 0.0f;
    float shakeSeed = 0.0f;

    float fovCurrent = 1.204f;

    FootstepSurface surface = FootstepSurface::Tile;
    bool footstepPending = false;
    FootstepEvent pendingStep;
};

}
