#include "Player.h"

using namespace em;

namespace echo {

void Player::reset(const Vec3& spawn, float y) {
    pos = spawn;
    velocity = Vec3(0, 0, 0);
    yaw = y;
    pitch = 0.0f;
    crouching = false;
    sprinting = false;
    grounded = true;
    currentHeight = standHeight;
    currentEye = standEye;
    staminaValue = 1.0f;
    breath = 0.0f;
    noise = 0.0f;
    bobTime = 0.0f;
    bobAmount = 0.0f;
    stepAccum = 0.0f;
    bobOffset = Vec3(0, 0, 0);
    rollAngle = 0.0f;
    pitchBob = 0.0f;
    landImpact = 0.0f;
    shakeAmount = 0.0f;
    shakeTime = 0.0f;
    fovCurrent = fovBase;
    exhaustion = 0.0f;
    footstepPending = false;
}

Vec3 Player::forward() const {
    return sphericalDir(yaw, pitch);
}

Vec3 Player::flatForward() const {
    return normalize(Vec3(std::sin(yaw), 0.0f, -std::cos(yaw)));
}

Vec3 Player::right() const {
    return normalize(cross(flatForward(), Vec3(0, 1, 0)));
}

Vec3 Player::eyePosition() const {
    return pos + Vec3(0, currentEye, 0) + bobOffset;
}

void Player::applyLook(const PlayerInput& in, float dt) {
    if (movementLocked) return;
    float dx = in.look.x * sensitivity;
    float dy = in.look.y * sensitivity * (invertY ? -1.0f : 1.0f);
    float focusScale = in.focus ? 0.45f : 1.0f;
    yaw += dx * focusScale;
    pitch -= dy * focusScale;
    pitch = clampf(pitch, -1.5533f, 1.5533f);
    yaw = wrapAngle(yaw);
}

void Player::applyMovement(const PlayerInput& in, const PhysicsWorld& world, float dt) {
    float targetHeight = crouching ? crouchHeight : standHeight;
    float targetEye = crouching ? crouchEye : standEye;

    bool wantCrouch = in.crouch && !movementLocked;
    if (!wantCrouch && crouching) {
        Vec3 base = pos + Vec3(0, radius, 0);
        Vec3 top = pos + Vec3(0, standHeight - radius, 0);
        if (!world.overlapCapsule(base, top, radius * 0.94f)) crouching = false;
    } else {
        crouching = wantCrouch;
    }

    targetHeight = crouching ? crouchHeight : standHeight;
    targetEye = crouching ? crouchEye : standEye;
    currentHeight = lerpf(currentHeight, targetHeight, 1.0f - std::exp(-14.0f * dt));
    currentEye = lerpf(currentEye, targetEye, 1.0f - std::exp(-13.0f * dt));

    Vec2 mv = in.move;
    float mvLen = length(mv);
    if (mvLen > 1.0f) mv /= mvLen;
    if (movementLocked) mv = Vec2(0, 0);

    bool wantsSprint = in.sprint && !crouching && mv.y > 0.25f && staminaValue > 0.06f;
    sprinting = wantsSprint;

    float baseSpeed = 1.62f;
    if (crouching) baseSpeed = 0.82f;
    else if (sprinting) baseSpeed = 3.35f;
    baseSpeed *= lerpf(1.0f, 0.78f, exhaustion);
    if (in.focus) baseSpeed *= 0.55f;

    Vec3 wishDir = flatForward() * mv.y + right() * mv.x;
    float wishLen = length(wishDir);
    if (wishLen > 1e-4f) wishDir /= wishLen;

    Vec3 targetVel = wishDir * (baseSpeed * std::min(mvLen, 1.0f));
    Vec3 horizontal(velocity.x, 0, velocity.z);

    float accel = grounded ? (sprinting ? 16.0f : 20.0f) : 4.0f;
    float decel = grounded ? 24.0f : 2.0f;
    float rate = lengthSq(targetVel) > lengthSq(horizontal) ? accel : decel;
    horizontal = horizontal + (targetVel - horizontal) * (1.0f - std::exp(-rate * dt));

    velocity.x = horizontal.x;
    velocity.z = horizontal.z;
    velocity.y -= 19.6f * dt;
    if (velocity.y < -35.0f) velocity.y = -35.0f;

    Vec3 prevPos = pos;
    bool wasGrounded = grounded;

    Vec3 delta = velocity * dt;
    Vec3 target = pos + delta;

    Vec3 groundNormal(0, 1, 0);
    bool hitGround = false;
    const float stepHeight = 0.50f;
    Vec3 desiredHoriz(delta.x, 0, delta.z);
    bool useStepOffset = wasGrounded && velocity.y <= 0.02f && !movementLocked;

    Vec3 resolved;
    if (useStepOffset) {
        float liftedHeight = std::max(currentHeight - stepHeight, radius * 2.0f + 0.06f);
        Vec3 lifted = prevPos + Vec3(0, stepHeight, 0) + Vec3(delta.x, 0, delta.z);
        Vec3 ln;
        bool lg = false;
        Vec3 swept = world.resolveCapsule(lifted, radius, liftedHeight, 5, ln, lg);
        Vec3 moved(swept.x - prevPos.x, 0, swept.z - prevPos.z);
        float maxMove = length(desiredHoriz) * 1.6f + 0.06f;
        if (length(moved) > maxMove) {
            Vec3 fn;
            bool fg = false;
            resolved = world.resolveCapsule(target, radius, currentHeight, 5, fn, fg);
            if (fg) { hitGround = true; groundNormal = fn; }
        } else {
            resolved = Vec3(swept.x, prevPos.y, swept.z);
        }
    } else {
        resolved = world.resolveCapsule(target, radius, currentHeight, 5, groundNormal, hitGround);
    }

    if (velocity.y <= 0.02f) {
        float startH = stepHeight + 0.10f;
        RayHit snap = world.raycast(resolved + Vec3(0, startH, 0), Vec3(0, -1, 0),
                                    startH + stepHeight + 0.30f, COL_TRIGGER | COL_CHARACTER);

        if (snap.hit && snap.distance < 0.02f) {
            startH = std::max(currentHeight * 0.92f, stepHeight + 0.60f);
            snap = world.raycast(resolved + Vec3(0, startH, 0), Vec3(0, -1, 0),
                                 startH + stepHeight + 0.30f, COL_TRIGGER | COL_CHARACTER);
        }

        if (snap.hit && snap.normal.y > 0.36f && snap.distance > 0.005f) {
            float drop = resolved.y - snap.point.y;
            if (drop > -stepHeight && drop < stepHeight + 0.10f) {
                resolved.y = snap.point.y;
                hitGround = true;
                groundNormal = snap.normal;
            }
        }
    }

    if (!hitGround) {
        Vec3 fn;
        bool fg = false;
        resolved = world.resolveCapsule(resolved, radius, currentHeight, 4, fn, fg);
        if (fg) {
            hitGround = true;
            groundNormal = fn;
        }
    }

    Vec3 totalMove(resolved.x - prevPos.x, 0, resolved.z - prevPos.z);
    float allowed = length(desiredHoriz) * 2.0f + 0.12f;
    float movedLen = length(totalMove);
    if (movedLen > allowed && movedLen > 1e-5f) {
        Vec3 capped = totalMove * (allowed / movedLen);
        resolved.x = prevPos.x + capped.x;
        resolved.z = prevPos.z + capped.z;
    }
    if (resolved.y - prevPos.y > stepHeight + 0.12f) resolved.y = prevPos.y + stepHeight + 0.12f;

    pos = resolved;

    if (hitGround && velocity.y <= 0.0f) {
        if (!wasGrounded && velocity.y < -3.0f) {
            landImpact = clampf(-velocity.y * 0.035f, 0.0f, 0.5f);
            addShake(clampf(-velocity.y * 0.02f, 0.0f, 0.35f), 0.28f);
        }
        velocity.y = 0.0f;
        grounded = true;
    } else {
        grounded = hitGround;
    }

    if (grounded && in.jump && !movementLocked && !crouching && staminaValue > 0.2f) {
        velocity.y = 4.4f;
        grounded = false;
        staminaValue = std::max(0.0f, staminaValue - 0.12f);
    }

    if (sprinting && isMoving()) {
        staminaValue = std::max(0.0f, staminaValue - dt * 0.145f);
    } else {
        float rec = crouching || !isMoving() ? 0.20f : 0.085f;
        staminaValue = std::min(1.0f, staminaValue + dt * rec);
    }

    float breathTarget = sprinting ? 1.0f : (isMoving() ? 0.35f : 0.1f);
    breathTarget += (1.0f - staminaValue) * 0.6f;
    breath = lerpf(breath, clampf(breathTarget, 0.0f, 1.4f), 1.0f - std::exp(-2.2f * dt));

    float noiseTarget = 0.0f;
    if (isMoving()) noiseTarget = crouching ? 0.18f : (sprinting ? 1.0f : 0.45f);
    noise = lerpf(noise, noiseTarget, 1.0f - std::exp(-8.0f * dt));

    exhaustion = lerpf(exhaustion, clampf(1.0f - staminaValue, 0.0f, 1.0f), 1.0f - std::exp(-1.2f * dt));
}

void Player::updateBob(float dt) {
    float sp = speed();
    float intensity = clampf(sp / 3.2f, 0.0f, 1.2f);
    bobAmount = lerpf(bobAmount, grounded ? intensity : 0.0f, 1.0f - std::exp(-9.0f * dt));

    float freq = crouching ? 5.4f : (sprinting ? 10.4f : 7.6f);
    if (sp > 0.15f && grounded) {
        bobTime += dt * freq;
        stepAccum += sp * dt;
    } else {
        bobTime += dt * 1.4f;
    }

    float strideLength = crouching ? 0.68f : (sprinting ? 1.30f : 0.92f);
    if (stepAccum >= strideLength) {
        stepAccum -= strideLength;
        stepParity ^= 1;
        pendingStep.position = pos;
        pendingStep.surface = surface;
        pendingStep.loudness = crouching ? 0.22f : (sprinting ? 1.0f : 0.52f);
        footstepPending = true;
    }

    float breathe = std::sin((float)bobTime * 0.28f) * 0.004f + std::sin((float)bobTime * 0.17f + 1.3f) * 0.003f;
    float breathAmp = 0.004f + breath * 0.012f;

    float vertical = std::sin(bobTime * 2.0f) * 0.031f * bobAmount;
    float lateral = std::sin(bobTime) * 0.026f * bobAmount;

    if (shakeTime > 0.0f) {
        shakeTime -= dt;
        shakeSeed += dt * 43.0f;
        float decay = clampf(shakeTime * 3.5f, 0.0f, 1.0f);
        vertical += (hash11(shakeSeed) - 0.5f) * shakeAmount * decay * 0.6f;
        lateral += (hash11(shakeSeed + 17.3f) - 0.5f) * shakeAmount * decay * 0.6f;
    }

    landImpact = lerpf(landImpact, 0.0f, 1.0f - std::exp(-9.0f * dt));

    Vec3 targetBob = right() * lateral + Vec3(0, vertical + breathe * (1.0f + breath * 2.0f) - landImpact * 0.25f, 0);
    targetBob.y += std::sin(bobTime * 0.9f) * breathAmp;
    bobOffset = expDampV(bobOffset, targetBob, 22.0f, dt);

    float targetRoll = -lateral * 0.9f + headTiltTarget;
    rollAngle = lerpf(rollAngle, targetRoll, 1.0f - std::exp(-10.0f * dt));
    pitchBob = lerpf(pitchBob, -vertical * 0.5f - landImpact * 0.35f, 1.0f - std::exp(-12.0f * dt));

    float targetFov = fovBase + (sprinting ? 0.085f : 0.0f) * clampf(speed() / 3.2f, 0.0f, 1.0f);
    fovCurrent = lerpf(fovCurrent, targetFov, 1.0f - std::exp(-6.0f * dt));
}

void Player::update(const PlayerInput& in, const PhysicsWorld& world, float dt) {
    if (dt <= 0.0f) return;
    dt = std::min(dt, 0.05f);
    applyLook(in, dt);
    applyMovement(in, world, dt);
    updateBob(dt);
}

CameraData Player::buildCamera(float aspect) const {
    CameraData cam;
    cam.position = eyePosition();
    float p = clampf(pitch + pitchBob, -1.56f, 1.56f);
    cam.forward = sphericalDir(yaw, p);
    cam.fovY = fovCurrent;
    cam.nearPlane = 0.045f;
    cam.farPlane = 240.0f;
    cam.update(aspect);

    if (std::fabs(rollAngle) > 1e-5f) {
        Vec3 f = cam.forward;
        Vec3 r = normalize(cross(f, Vec3(0, 1, 0)));
        Vec3 u = cross(r, f);
        float c = std::cos(rollAngle), s = std::sin(rollAngle);
        Vec3 rr = r * c + u * s;
        Vec3 uu = u * c - r * s;
        cam.view = Mat4::lookAt(cam.position, cam.position + f, uu);
        cam.viewProj = cam.proj * cam.view;
        cam.invViewProj = cam.viewProj.inverted();
        cam.invView = cam.view.inverted();
        cam.frustum.fromMatrix(cam.viewProj);
    }
    return cam;
}

bool Player::consumeFootstep(FootstepEvent& out) {
    if (!footstepPending) return false;
    out = pendingStep;
    footstepPending = false;
    return true;
}

void Player::addShake(float amount, float duration) {
    shakeAmount = std::max(shakeAmount * 0.5f, amount);
    shakeTime = std::max(shakeTime, duration);
}

void Player::addRecoilLook(float yawDelta, float pitchDelta) {
    yaw = wrapAngle(yaw + yawDelta);
    pitch = clampf(pitch + pitchDelta, -1.5533f, 1.5533f);
}

void Player::forceLookAt(const Vec3& target, float strength) {
    Vec3 d = target - eyePosition();
    if (lengthSq(d) < 1e-5f) return;
    d = normalize(d);
    float targetYaw = std::atan2(d.x, -d.z);
    float targetPitch = std::asin(clampf(d.y, -1.0f, 1.0f));
    yaw = wrapAngle(yaw + wrapAngle(targetYaw - yaw) * clampf(strength, 0.0f, 1.0f));
    pitch = clampf(pitch + (targetPitch - pitch) * clampf(strength, 0.0f, 1.0f), -1.5533f, 1.5533f);
}

}
