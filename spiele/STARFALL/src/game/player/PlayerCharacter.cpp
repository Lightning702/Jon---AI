#include "PlayerCharacter.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {
namespace {

constexpr f64 kWalkSpeed = 5.4;
constexpr f64 kSprintSpeed = 11.2;
constexpr f64 kCrouchSpeed = 2.4;
constexpr f64 kJetpackAcceleration = 16.0;
constexpr f64 kGroundAcceleration = 46.0;
constexpr f64 kAirAcceleration = 8.0;

}

void PlayerCharacter::configureInventory(u32 slotCount) {
    suitInventory.configure(InventoryKind::Suit, slotCount, "ANZUG");
}

void PlayerCharacter::spawnOn(const PlanetBody& body, const DVec3& unitDirection) {
    const DVec3 direction = normalize(unitDirection);
    position = body.center() + direction * (body.radiusAt(direction) + 2.0);
    upDirection = direction;
    linearVelocity = DVec3::zero();
    onGround = true;
    attached = true;
    beamHeat = 0.0f;
    survivalStats.reset();
}

void PlayerCharacter::detachFromSurface() {
    attached = false;
    onGround = false;
}

DVec3 PlayerCharacter::lookDirection() const {
    const DVec3 reference = std::fabs(upDirection.y) < 0.9 ? DVec3::unitY() : DVec3::unitX();
    const DVec3 east = normalize(cross(reference, upDirection));
    const DVec3 north = cross(upDirection, east);

    const f64 cosinePitch = std::cos(static_cast<f64>(pitch));
    const f64 sinePitch = std::sin(static_cast<f64>(pitch));
    const f64 cosineYaw = std::cos(static_cast<f64>(yaw));
    const f64 sineYaw = std::sin(static_cast<f64>(yaw));

    const DVec3 horizontal = north * cosineYaw + east * sineYaw;
    return normalize(horizontal * cosinePitch + upDirection * sinePitch);
}

Quat PlayerCharacter::orientation() const {
    const DVec3 forward = lookDirection();
    const DVec3 right = normalize(cross(forward, upDirection));
    const DVec3 realUp = cross(right, forward);
    return Quat::fromBasis(right.toFloat(), realUp.toFloat(), forward.toFloat());
}

void PlayerCharacter::cycleTool() {
    activeTool = static_cast<ToolMode>((static_cast<u32>(activeTool) + 1) % static_cast<u32>(ToolMode::Count));
}

void PlayerCharacter::step(const PlanetBody& body, const FootInput& input, f64 stepSeconds) {
    if (stepSeconds <= 0.0) return;

    yaw = wrapAngle(yaw + input.lookYaw);
    pitch = clampValue(pitch + input.lookPitch, -1.52f, 1.52f);

    const DVec3 newUp = body.upAt(position);
    upDirection = newUp;

    const DVec3 reference = std::fabs(upDirection.y) < 0.9 ? DVec3::unitY() : DVec3::unitX();
    const DVec3 east = normalize(cross(reference, upDirection));
    const DVec3 north = cross(upDirection, east);

    const f64 surfaceRadius = body.radiusAt(upDirection);
    const f64 groundDistance = length(position - body.center()) - surfaceRadius;

    f64 targetSpeed = kWalkSpeed;
    if (input.crouch) targetSpeed = kCrouchSpeed;
    else if (input.sprint && survivalStats.stamina() > 0.05) targetSpeed = kSprintSpeed;

    const f64 gravityScale = clampValue(body.profile().surfaceGravity / 9.81, 0.05, 4.0);
    targetSpeed *= clampValue(1.28 - gravityScale * 0.24, 0.55, 1.35);

    const DVec3 wishDirection = north * static_cast<f64>(input.forward) + east * static_cast<f64>(input.strafe);
    const f64 wishLength = length(wishDirection);
    const DVec3 wish = wishLength > 1.0e-6 ? wishDirection / wishLength : DVec3::zero();

    const DVec3 gravity = body.gravityAt(position);
    linearVelocity += gravity * stepSeconds;

    const f64 verticalSpeed = dot(linearVelocity, upDirection);
    DVec3 horizontalVelocity = linearVelocity - upDirection * verticalSpeed;

    const f64 acceleration = onGround ? kGroundAcceleration : kAirAcceleration;
    if (wishLength > 1.0e-6) {
        const DVec3 target = wish * (targetSpeed * minValue(wishLength, 1.0));
        const DVec3 difference = target - horizontalVelocity;
        const f64 magnitude = length(difference);
        const f64 change = minValue(magnitude, acceleration * stepSeconds);
        if (magnitude > 1.0e-6) horizontalVelocity += difference / magnitude * change;
    } else if (onGround) {
        const f64 speed = length(horizontalVelocity);
        const f64 drop = minValue(speed, 24.0 * stepSeconds);
        if (speed > 1.0e-6) horizontalVelocity -= horizontalVelocity / speed * drop;
    }

    f64 newVerticalSpeed = verticalSpeed;
    const bool jetpackWanted = input.jetpack && survivalStats.jetpackFuel() > 0.0;
    if (jetpackWanted) {
        newVerticalSpeed += kJetpackAcceleration * stepSeconds;
        onGround = false;
    } else if (input.jump && onGround) {
        const f64 jumpSpeed = std::sqrt(2.0 * maxValue(length(gravity), 0.5) * 1.55);
        newVerticalSpeed = jumpSpeed;
        onGround = false;
    }

    linearVelocity = horizontalVelocity + upDirection * newVerticalSpeed;

    const f64 terminalSpeed = 180.0;
    const f64 speed = length(linearVelocity);
    if (speed > terminalSpeed) linearVelocity *= terminalSpeed / speed;

    position += linearVelocity * stepSeconds;

    const DVec3 updatedUp = body.upAt(position);
    const f64 updatedRadius = body.radiusAt(updatedUp);
    const f64 distanceFromCenter = length(position - body.center());
    const f64 footHeight = input.crouch ? crouchHeight : standHeight;
    const f64 minimumDistance = updatedRadius;

    if (distanceFromCenter <= minimumDistance) {
        const f64 impactSpeed = -dot(linearVelocity, updatedUp);
        position = body.center() + updatedUp * minimumDistance;
        const f64 vertical = dot(linearVelocity, updatedUp);
        if (vertical < 0.0) linearVelocity -= updatedUp * vertical;
        if (!onGround && impactSpeed > 14.0) {
            survivalStats.applyDamage(clampValue((impactSpeed - 14.0) * 0.035, 0.0, 1.0));
        }
        onGround = true;
    } else if (distanceFromCenter > minimumDistance + 0.25) {
        onGround = false;
    }

    eyeHeight = static_cast<f32>(mixValue(static_cast<f64>(eyeHeight), footHeight * 0.93, minValue(1.0, stepSeconds * 12.0)));
    (void)groundDistance;
    (void)attached;

    beamHeat = static_cast<f32>(maxValue(static_cast<f64>(beamHeat) - stepSeconds * 0.42, 0.0));
}

}
