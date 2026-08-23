#include "Human.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

namespace {

void capsuleSegment(MeshBuilder& mb, float radiusTop, float radiusBottom, float length, int segments) {
    mb.addCone(Vec3(0, -length, 0), radiusBottom, radiusTop, length, segments, false);
    mb.addSphere(Vec3(0, 0, 0), radiusTop, 6, segments);
    mb.addSphere(Vec3(0, -length, 0), radiusBottom, 6, segments);
}

void buildHead(MeshBuilder& mb) {
    mb.setMaterial(MAT_SKIN);
    mb.pushTransform(Mat4::scale(Vec3(0.088f, 0.112f, 0.098f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 12, 16);
    mb.popTransform();

    mb.pushTransform(Mat4::translate(Vec3(0, -0.060f, 0.012f)) * Mat4::scale(Vec3(0.072f, 0.062f, 0.084f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 8, 12);
    mb.popTransform();

    mb.pushTransform(Mat4::translate(Vec3(0, -0.012f, -0.086f)) * Mat4::scale(Vec3(0.016f, 0.030f, 0.020f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 8);
    mb.popTransform();

    mb.addBox(Vec3(-0.038f, 0.020f, -0.078f), Vec3(0.024f, 0.005f, 0.010f));
    mb.addBox(Vec3(0.038f, 0.020f, -0.078f), Vec3(0.024f, 0.005f, 0.010f));

    mb.pushTransform(Mat4::translate(Vec3(-0.084f, -0.008f, 0.006f)) * Mat4::scale(Vec3(0.012f, 0.028f, 0.018f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 5, 6);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0.084f, -0.008f, 0.006f)) * Mat4::scale(Vec3(0.012f, 0.028f, 0.018f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 5, 6);
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_SERVER_RACK);
    mb.pushTransform(Mat4::translate(Vec3(-0.036f, 0.012f, -0.074f)) * Mat4::scale(Vec3(0.016f, 0.009f, 0.006f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 5, 7);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0.036f, 0.012f, -0.074f)) * Mat4::scale(Vec3(0.016f, 0.009f, 0.006f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 5, 7);
    mb.popTransform();
    mb.addBox(Vec3(0, -0.052f, -0.070f), Vec3(0.022f, 0.003f, 0.008f));
    mb.finishSubMesh();
}

void buildHair(MeshBuilder& mb) {
    mb.setMaterial(MAT_HAIR);
    mb.pushTransform(Mat4::translate(Vec3(0, 0.012f, 0.010f)) * Mat4::scale(Vec3(0.098f, 0.118f, 0.104f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 10, 14);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0, -0.045f, 0.055f)) * Mat4::scale(Vec3(0.084f, 0.090f, 0.060f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 8, 12);
    mb.popTransform();
    mb.finishSubMesh();
}

void buildTorso(MeshBuilder& mb, int material, float w, float d, float h, bool collar) {
    mb.setMaterial(material);
    mb.pushTransform(Mat4::scale(Vec3(w, h, d)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 10, 14);
    mb.popTransform();
    if (collar) {
        mb.pushTransform(Mat4::translate(Vec3(0, h * 0.82f, 0)) * Mat4::scale(Vec3(w * 0.52f, h * 0.16f, d * 0.62f)));
        mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 10);
        mb.popTransform();
    }
    mb.finishSubMesh();
}

void buildLimb(MeshBuilder& mb, int material, float rTop, float rBot, float len) {
    mb.setMaterial(material);
    capsuleSegment(mb, rTop, rBot, len, 10);
    mb.finishSubMesh();
}

void buildHand(MeshBuilder& mb) {
    mb.setMaterial(MAT_SKIN);
    mb.pushTransform(Mat4::translate(Vec3(0, -0.045f, 0)) * Mat4::scale(Vec3(0.030f, 0.052f, 0.017f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 8);
    mb.popTransform();
    for (int i = 0; i < 4; i++) {
        float x = -0.020f + i * 0.0135f;
        mb.pushTransform(Mat4::translate(Vec3(x, -0.098f, 0)) * Mat4::scale(Vec3(0.006f, 0.026f, 0.006f)));
        mb.addSphere(Vec3(0, 0, 0), 1.0f, 4, 6);
        mb.popTransform();
    }
    mb.pushTransform(Mat4::translate(Vec3(-0.028f, -0.062f, 0.004f)) * Mat4::scale(Vec3(0.007f, 0.020f, 0.007f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 4, 6);
    mb.popTransform();
    mb.finishSubMesh();
}

void buildFoot(MeshBuilder& mb) {
    mb.setMaterial(MAT_RUBBER);
    mb.pushTransform(Mat4::translate(Vec3(0, -0.030f, -0.048f)) * Mat4::scale(Vec3(0.042f, 0.030f, 0.098f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 10);
    mb.popTransform();
    mb.finishSubMesh();
}

}

void HumanRig::build() {
    MeshBuilder mb;

    mb.clear(); buildTorso(mb, MAT_CLOTH_WHITE, 0.135f, 0.098f, 0.098f, false); mb.build(parts[PART_PELVIS]);
    mb.clear(); buildTorso(mb, MAT_CLOTH_WHITE, 0.125f, 0.092f, 0.105f, false); mb.build(parts[PART_ABDOMEN]);
    mb.clear(); buildTorso(mb, MAT_CLOTH_WHITE, 0.160f, 0.110f, 0.170f, true); mb.build(parts[PART_CHEST]);
    mb.clear(); buildLimb(mb, MAT_SKIN, 0.042f, 0.046f, 0.070f); mb.build(parts[PART_NECK]);
    mb.clear(); buildHead(mb); mb.build(parts[PART_HEAD]);
    mb.clear(); buildHair(mb); mb.build(parts[PART_HAIR]);

    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.052f, 0.042f, 0.270f); mb.build(parts[PART_UPPER_ARM_L]);
    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.042f, 0.033f, 0.250f); mb.build(parts[PART_FOREARM_L]);
    mb.clear(); buildHand(mb); mb.build(parts[PART_HAND_L]);
    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.052f, 0.042f, 0.270f); mb.build(parts[PART_UPPER_ARM_R]);
    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.042f, 0.033f, 0.250f); mb.build(parts[PART_FOREARM_R]);
    mb.clear(); buildHand(mb); mb.build(parts[PART_HAND_R]);

    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.078f, 0.058f, 0.400f); mb.build(parts[PART_THIGH_L]);
    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.055f, 0.038f, 0.395f); mb.build(parts[PART_SHIN_L]);
    mb.clear(); buildFoot(mb); mb.build(parts[PART_FOOT_L]);
    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.078f, 0.058f, 0.400f); mb.build(parts[PART_THIGH_R]);
    mb.clear(); buildLimb(mb, MAT_CLOTH_WHITE, 0.055f, 0.038f, 0.395f); mb.build(parts[PART_SHIN_R]);
    mb.clear(); buildFoot(mb); mb.build(parts[PART_FOOT_R]);

    for (int i = 0; i < PART_COUNT; i++) bounds[i] = parts[i].bounds();
    LOG_INFO("Human rig built (%d parts)", (int)PART_COUNT);
}

void HumanRig::destroy() {
    for (int i = 0; i < PART_COUNT; i++) parts[i].destroy();
}

void HumanInstance::configure(int type, u64 seed) {
    Rng rng(seed ? seed : 12345);
    seedValue = seed;
    look.type = clampi(type, 0, HUMAN_TYPE_COUNT - 1);
    look.female = rng.chance(0.5f);
    look.height = rng.range(0.94f, 1.06f);
    look.build = rng.range(0.92f, 1.10f);
    look.hasHair = rng.chance(look.female ? 0.96f : 0.72f);

    float tone = rng.range(0.72f, 1.18f);
    look.skinTint = Vec3(tone, tone * rng.range(0.94f, 1.02f), tone * rng.range(0.90f, 1.0f)) * rng.range(0.82f, 1.0f);
    float hairShade = rng.range(0.55f, 1.5f);
    look.hairTint = Vec3(hairShade, hairShade * 0.95f, hairShade * 0.9f);

    switch (look.type) {
    case HUMAN_DOCTOR:
        look.clothMaterial = MAT_CLOTH_WHITE;
        look.clothTint = Vec3(rng.range(0.88f, 1.02f));
        break;
    case HUMAN_NURSE:
        look.clothMaterial = MAT_CLOTH_SCRUB;
        look.clothTint = Vec3(rng.range(0.85f, 1.15f), rng.range(0.95f, 1.1f), rng.range(0.95f, 1.1f));
        break;
    case HUMAN_PATIENT:
        look.clothMaterial = MAT_CLOTH_WHITE;
        look.clothTint = Vec3(0.82f, 0.84f, 0.80f) * rng.range(0.85f, 1.0f);
        look.hasHair = rng.chance(0.5f);
        break;
    case HUMAN_CLEANER:
        look.clothMaterial = MAT_CLOTH_SCRUB;
        look.clothTint = Vec3(rng.range(1.4f, 1.8f), rng.range(1.1f, 1.3f), 0.55f);
        break;
    default:
        look.clothMaterial = MAT_CLOTH_SCRUB;
        look.clothTint = Vec3(0.55f, 0.60f, 0.75f);
        break;
    }

    currentPose = previousPose = POSE_STAND_STILL;
    poseBlend = 1.0f;
    phase = rng.range(0.0f, 100.0f);
    breathPhase = rng.range(0.0f, TAU);
    swayPhase = rng.range(0.0f, TAU);
    active = true;
}

void HumanInstance::setPose(int pose, float blendTime) {
    if (pose == currentPose) return;
    previousPose = currentPose;
    currentPose = clampi(pose, 0, POSE_COUNT - 1);
    poseBlend = 0.0f;
    blendSpeed = 1.0f / std::max(blendTime, 0.05f);
}

void HumanInstance::setLook(float yawOffset, float pitch) {
    lookForced = true;
    targetHeadYaw = clampf(wrapAngle(yawOffset), -1.05f, 1.05f);
    targetHeadPitch = clampf(pitch, -0.62f, 0.62f);
}

void HumanInstance::clearLook() {
    lookForced = false;
}

void HumanInstance::update(float dt, float time, const Vec3& lookTarget, bool hasLookTarget) {
    if (!active) return;
    if (poseBlend < 1.0f) poseBlend = std::min(1.0f, poseBlend + dt * blendSpeed);

    breathPhase += dt * (0.55f + (currentPose == POSE_SLOW_WALK ? 0.35f : 0.0f));
    swayPhase += dt * 0.28f;
    idleTimer += dt;

    if (currentPose == POSE_SLOW_WALK) phase += dt * walkSpeed * 1.85f;

    if (lookForced) {
    } else if (hasLookTarget) {
        Vec3 d = lookTarget - headPosition();
        float len = length(d);
        if (len > 1e-3f) {
            d /= len;
            float wantYaw = wrapAngle(std::atan2(d.x, -d.z) - yaw);
            targetHeadYaw = clampf(wantYaw, -1.05f, 1.05f);
            targetHeadPitch = clampf(std::asin(clampf(d.y, -1.0f, 1.0f)), -0.5f, 0.5f);
        }
    } else if (idleTimer > 6.0f) {
        idleTimer = 0.0f;
        float r = hash11((float)(seedValue & 0xFFFF) + time * 0.13f);
        targetHeadYaw = (r - 0.5f) * 0.7f;
        targetHeadPitch = (hash11(r * 91.7f) - 0.5f) * 0.25f;
    }

    float lookRate = lookForced ? 6.5f
                                : (currentPose == POSE_STAND_STILL ? 0.55f : 1.1f);
    headYaw = lerpf(headYaw, targetHeadYaw, 1.0f - std::exp(-lookRate * dt));
    headPitch = lerpf(headPitch, targetHeadPitch, 1.0f - std::exp(-lookRate * dt));

    computePose(time);
}

void HumanInstance::computePose(float t) {
    const float s = look.height;
    const float b = look.build;

    float breath = std::sin(breathPhase * TAU * 0.24f) * 0.5f + 0.5f;
    float breathScale = 1.0f + breath * 0.012f * breathAmount;
    float sway = std::sin(swayPhase * TAU * 0.13f) * 0.010f + std::sin(swayPhase * TAU * 0.071f) * 0.006f;

    float walk = 0.0f, armSwing = 0.0f, hipDrop = 0.0f, bobY = 0.0f;
    float leanForward = 0.0f;
    float spineTwist = 0.0f;
    float armDown = 0.0f;
    float kneeBend = 0.0f;
    float sitAmount = 0.0f;

    int poses[2] = { previousPose, currentPose };
    float weights[2] = { 1.0f - poseBlend, poseBlend };

    for (int i = 0; i < 2; i++) {
        float w = weights[i];
        if (w <= 0.0001f) continue;
        switch (poses[i]) {
        case POSE_STAND_STILL:
            armDown += w * 1.0f;
            break;
        case POSE_IDLE:
            armDown += w * 0.94f;
            leanForward += w * 0.03f;
            break;
        case POSE_SLOW_WALK:
            walk += w;
            armSwing += w;
            leanForward += w * 0.06f;
            armDown += w * 0.88f;
            break;
        case POSE_TURN_AWAY:
            spineTwist += w * 0.55f;
            armDown += w * 1.0f;
            break;
        case POSE_FACE_WALL:
            armDown += w * 1.0f;
            leanForward += w * 0.10f;
            break;
        case POSE_SIT:
            sitAmount += w;
            armDown += w * 0.7f;
            kneeBend += w * 1.55f;
            break;
        case POSE_LEAN:
            leanForward += w * 0.22f;
            armDown += w * 0.85f;
            spineTwist += w * 0.18f;
            break;
        case POSE_LOOK_UP:
            armDown += w * 1.0f;
            leanForward -= w * 0.14f;
            break;
        }
    }

    float legPhase = phase * TAU;
    float legL = std::sin(legPhase) * walk;
    float legR = std::sin(legPhase + PI) * walk;
    bobY = -std::fabs(std::sin(legPhase)) * 0.022f * walk;
    hipDrop = std::sin(legPhase) * 0.018f * walk;

    Mat4 root = Mat4::translate(position + Vec3(sway, bobY - sitAmount * 0.34f, 0)) * Mat4::rotateY(yaw);

    float pelvisY = 0.96f * s - sitAmount * 0.06f;
    Mat4 pelvis = root * Mat4::translate(Vec3(0, pelvisY, 0)) * Mat4::rotateZ(hipDrop) * Mat4::rotateY(spineTwist * 0.25f) * Mat4::scale(Vec3(b, 1, b));
    partTransforms[PART_PELVIS] = pelvis;

    Mat4 abdomen = pelvis * Mat4::translate(Vec3(0, 0.115f * s, 0)) * Mat4::rotateX(leanForward * 0.4f) * Mat4::rotateY(spineTwist * 0.3f);
    partTransforms[PART_ABDOMEN] = abdomen * Mat4::scale(Vec3(1, breathScale, 1));

    Mat4 chest = abdomen * Mat4::translate(Vec3(0, 0.165f * s, 0)) * Mat4::rotateX(leanForward * 0.6f) * Mat4::rotateY(spineTwist * 0.45f);
    partTransforms[PART_CHEST] = chest * Mat4::scale(Vec3(breathScale, breathScale, breathScale * 1.02f));

    Mat4 neck = chest * Mat4::translate(Vec3(0, 0.175f * s, 0.006f)) * Mat4::rotateX(-leanForward * 0.35f);
    partTransforms[PART_NECK] = neck;

    Mat4 head = neck * Mat4::translate(Vec3(0, 0.085f * s, 0)) * Mat4::rotateY(headYaw) * Mat4::rotateX(-headPitch);
    partTransforms[PART_HEAD] = head;
    partTransforms[PART_HAIR] = head;

    float shoulderX = 0.175f * b;
    float shoulderY = 0.145f * s;

    for (int side = 0; side < 2; side++) {
        float sx = side == 0 ? -1.0f : 1.0f;
        float swing = (side == 0 ? std::sin(legPhase + PI) : std::sin(legPhase)) * armSwing * 0.42f;
        float spread = 0.16f * armDown;

        Mat4 shoulder = chest * Mat4::translate(Vec3(sx * shoulderX, shoulderY, 0));
        Mat4 upper = shoulder * Mat4::rotateZ(-sx * spread) * Mat4::rotateX(swing) * Mat4::rotateY(sx * 0.06f);
        Mat4 elbow = upper * Mat4::translate(Vec3(0, -0.270f * s, 0));
        Mat4 fore = elbow * Mat4::rotateX(0.12f + std::fabs(swing) * 0.55f + sitAmount * 0.9f);
        Mat4 wrist = fore * Mat4::translate(Vec3(0, -0.250f * s, 0));

        partTransforms[side == 0 ? PART_UPPER_ARM_L : PART_UPPER_ARM_R] = upper;
        partTransforms[side == 0 ? PART_FOREARM_L : PART_FOREARM_R] = fore;
        partTransforms[side == 0 ? PART_HAND_L : PART_HAND_R] = wrist;
    }

    for (int side = 0; side < 2; side++) {
        float sx = side == 0 ? -1.0f : 1.0f;
        float step = side == 0 ? legL : legR;
        float hipAngle = step * 0.34f - sitAmount * 1.42f;
        float knee = std::max(0.0f, -step * 0.5f) + kneeBend + (walk > 0.01f ? 0.10f : 0.045f);

        Mat4 hip = pelvis * Mat4::translate(Vec3(sx * 0.082f * b, -0.055f * s, 0));
        Mat4 thigh = hip * Mat4::rotateX(hipAngle);
        Mat4 kneeJoint = thigh * Mat4::translate(Vec3(0, -0.400f * s, 0));
        Mat4 shin = kneeJoint * Mat4::rotateX(knee);
        Mat4 ankle = shin * Mat4::translate(Vec3(0, -0.395f * s, 0));
        Mat4 foot = ankle * Mat4::rotateX(-hipAngle * 0.4f - knee * 0.5f + sitAmount * 0.7f);

        partTransforms[side == 0 ? PART_THIGH_L : PART_THIGH_R] = thigh;
        partTransforms[side == 0 ? PART_SHIN_L : PART_SHIN_R] = shin;
        partTransforms[side == 0 ? PART_FOOT_L : PART_FOOT_R] = foot;
    }
}

Vec3 HumanInstance::headPosition() const {
    return position + Vec3(0, 1.56f * look.height, 0);
}

AABB HumanInstance::worldBounds() const {
    AABB b;
    b.expand(position + Vec3(-0.45f, -0.1f, -0.45f));
    b.expand(position + Vec3(0.45f, 1.95f * look.height, 0.45f));
    return b;
}

void HumanInstance::submit(Renderer& renderer, const HumanRig& rig) const {
    if (!active || visibility <= 0.01f) return;

    for (int i = 0; i < PART_COUNT; i++) {
        if (i == PART_HAIR && !look.hasHair) continue;
        const Mesh& mesh = rig.part(i);
        if (!mesh.valid()) continue;

        DrawCall dc;
        dc.mesh = &mesh;
        dc.transform = partTransforms[i];
        dc.castShadow = true;

        for (int sub = 0; sub < (int)mesh.subMeshes().size(); sub++) {
            const SubMesh& sm = mesh.subMeshes()[(size_t)sub];
            int mat = sm.material;
            Vec4 tint(1, 1, 1, 1);

            if (mat == MAT_SKIN) tint = Vec4(look.skinTint, 1.0f);
            else if (mat == MAT_HAIR) tint = Vec4(look.hairTint, 1.0f);
            else if (mat == MAT_CLOTH_WHITE) {
                mat = look.clothMaterial;
                tint = Vec4(look.clothTint, 1.0f);
            }

            dc.subIndex = sub;
            dc.material = mat;
            dc.tint = Vec4(tint.x, tint.y, tint.z, visibility);
            dc.bounds = sm.bounds.transformed(partTransforms[i]);
            renderer.submit(dc);
        }
    }
}

}
