#include "Horror.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

namespace {

void bone(MeshBuilder& mb, float rTop, float rBot, float len, int seg) {
    mb.addCone(Vec3(0, -len, 0), rBot, rTop, len, seg, false);
    mb.addSphere(Vec3(0, 0, 0), rTop, 6, seg);
    mb.addSphere(Vec3(0, -len, 0), rBot * 1.12f, 6, seg);
}

void buildLimb(MeshBuilder& mb, float rTop, float rBot, float len, bool knobs) {
    mb.setMaterial(MAT_SKIN);
    bone(mb, rTop, rBot, len, 9);
    if (knobs) {
        mb.pushTransform(Mat4::translate(Vec3(0, -len * 0.5f, -rTop * 0.7f)) *
                         Mat4::scale(Vec3(rTop * 0.5f, len * 0.22f, rTop * 0.4f)));
        mb.addSphere(Vec3(0, 0, 0), 1.0f, 5, 7);
        mb.popTransform();
    }
    mb.finishSubMesh();
}

void buildSkull(MeshBuilder& mb) {
    mb.setMaterial(MAT_SKIN);
    mb.pushTransform(Mat4::scale(Vec3(0.082f, 0.120f, 0.104f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 12, 16);
    mb.popTransform();

    mb.pushTransform(Mat4::translate(Vec3(0, -0.052f, -0.030f)) * Mat4::scale(Vec3(0.062f, 0.056f, 0.070f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 8, 12);
    mb.popTransform();

    mb.pushTransform(Mat4::translate(Vec3(-0.036f, 0.018f, -0.062f)) * Mat4::scale(Vec3(0.022f, 0.020f, 0.020f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 8);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0.036f, 0.018f, -0.062f)) * Mat4::scale(Vec3(0.022f, 0.020f, 0.020f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 8);
    mb.popTransform();

    mb.pushTransform(Mat4::translate(Vec3(0, 0.058f, 0.020f)) * Mat4::scale(Vec3(0.070f, 0.040f, 0.090f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 7, 10);
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_SERVER_RACK);
    mb.pushTransform(Mat4::translate(Vec3(-0.036f, 0.016f, -0.070f)) * Mat4::scale(Vec3(0.026f, 0.026f, 0.020f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 7, 9);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0.036f, 0.016f, -0.070f)) * Mat4::scale(Vec3(0.026f, 0.026f, 0.020f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 7, 9);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0, -0.030f, -0.082f)) * Mat4::scale(Vec3(0.014f, 0.020f, 0.014f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 5, 7);
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    for (int i = 0; i < 7; i++) {
        float x = -0.030f + i * 0.010f;
        mb.addBox(Vec3(x, -0.062f, -0.056f), Vec3(0.0038f, 0.0085f, 0.0038f));
    }
    mb.finishSubMesh();
}

void buildJaw(MeshBuilder& mb) {
    mb.setMaterial(MAT_SKIN);
    mb.pushTransform(Mat4::translate(Vec3(0, -0.034f, -0.020f)) * Mat4::scale(Vec3(0.052f, 0.038f, 0.062f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 7, 10);
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    for (int i = 0; i < 7; i++) {
        float x = -0.028f + i * 0.0094f;
        mb.addBox(Vec3(x, -0.012f, -0.052f), Vec3(0.0035f, 0.0090f, 0.0035f));
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_SERVER_RACK);
    mb.pushTransform(Mat4::translate(Vec3(0, -0.040f, -0.026f)) * Mat4::scale(Vec3(0.034f, 0.020f, 0.030f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 5, 8);
    mb.popTransform();
    mb.finishSubMesh();
}

void buildRibs(MeshBuilder& mb) {
    mb.setMaterial(MAT_SKIN);
    mb.pushTransform(Mat4::scale(Vec3(0.120f, 0.175f, 0.082f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 10, 14);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0, 0.150f, 0)) * Mat4::scale(Vec3(0.150f, 0.038f, 0.062f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 10);
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    for (int i = 0; i < 5; i++) {
        float y = 0.095f - i * 0.046f;
        float w = 0.116f - std::fabs(i - 1) * 0.006f;
        mb.addTorusArc(Vec3(0, y, 0.006f), w, 0.0095f, -1.15f, 2.30f, 9, 5);
    }
    mb.addBox(Vec3(0, 0.020f, -0.070f), Vec3(0.012f, 0.090f, 0.008f));
    mb.finishSubMesh();
}

void buildClaw(MeshBuilder& mb) {
    mb.setMaterial(MAT_SKIN);
    mb.pushTransform(Mat4::translate(Vec3(0, -0.048f, 0)) * Mat4::scale(Vec3(0.028f, 0.056f, 0.016f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 8);
    mb.popTransform();
    for (int i = 0; i < 4; i++) {
        float x = -0.021f + i * 0.014f;
        float len = 0.052f + (i == 1 || i == 2 ? 0.016f : 0.0f);
        mb.pushTransform(Mat4::translate(Vec3(x, -0.100f, 0)) * Mat4::rotateZ((x) * 2.2f));
        bone(mb, 0.0062f, 0.0016f, len, 5);
        mb.popTransform();
    }
    mb.pushTransform(Mat4::translate(Vec3(-0.030f, -0.066f, 0.008f)) * Mat4::rotateZ(0.7f));
    bone(mb, 0.0068f, 0.0018f, 0.044f, 5);
    mb.popTransform();
    mb.finishSubMesh();
}

void buildFoot(MeshBuilder& mb) {
    mb.setMaterial(MAT_SKIN);
    mb.pushTransform(Mat4::translate(Vec3(0, -0.026f, -0.040f)) * Mat4::scale(Vec3(0.034f, 0.024f, 0.088f)));
    mb.addSphere(Vec3(0, 0, 0), 1.0f, 6, 9);
    mb.popTransform();
    for (int i = 0; i < 3; i++) {
        mb.pushTransform(Mat4::translate(Vec3(-0.016f + i * 0.016f, -0.030f, -0.118f)) * Mat4::rotateX(1.35f));
        bone(mb, 0.0060f, 0.0018f, 0.032f, 5);
        mb.popTransform();
    }
    mb.finishSubMesh();
}

void buildHair(MeshBuilder& mb) {
    mb.setMaterial(MAT_HAIR);
    Rng rng(0x51A1E);
    for (int i = 0; i < 26; i++) {
        float a = rng.range(0.0f, TAU);
        float r = rng.range(0.0f, 0.062f);
        float len = rng.range(0.16f, 0.42f);
        mb.pushTransform(Mat4::translate(Vec3(std::cos(a) * r, 0.058f, std::sin(a) * r)) *
                         Mat4::rotateZ(rng.range(-0.22f, 0.22f)) *
                         Mat4::rotateX(rng.range(-0.22f, 0.22f)));
        bone(mb, 0.0055f, 0.0012f, len, 4);
        mb.popTransform();
    }
    mb.finishSubMesh();
}

}

void HorrorRig::build() {
    if (built) return;
    MeshBuilder mb;

    mb.clear(); buildLimb(mb, 0.098f, 0.086f, 0.070f, false); mb.build(parts[HPART_PELVIS]);
    mb.clear(); buildLimb(mb, 0.070f, 0.084f, 0.190f, true); mb.build(parts[HPART_SPINE]);
    mb.clear(); buildRibs(mb); mb.build(parts[HPART_RIBS]);
    mb.clear(); buildLimb(mb, 0.030f, 0.034f, 0.130f, false); mb.build(parts[HPART_NECK]);
    mb.clear(); buildSkull(mb); mb.build(parts[HPART_SKULL]);
    mb.clear(); buildJaw(mb); mb.build(parts[HPART_JAW]);

    mb.clear(); buildLimb(mb, 0.036f, 0.028f, 0.360f, true); mb.build(parts[HPART_ARM_L]);
    mb.clear(); buildLimb(mb, 0.028f, 0.021f, 0.365f, true); mb.build(parts[HPART_FORE_L]);
    mb.clear(); buildClaw(mb); mb.build(parts[HPART_CLAW_L]);
    mb.clear(); buildLimb(mb, 0.036f, 0.028f, 0.360f, true); mb.build(parts[HPART_ARM_R]);
    mb.clear(); buildLimb(mb, 0.028f, 0.021f, 0.365f, true); mb.build(parts[HPART_FORE_R]);
    mb.clear(); buildClaw(mb); mb.build(parts[HPART_CLAW_R]);

    mb.clear(); buildLimb(mb, 0.062f, 0.044f, 0.440f, true); mb.build(parts[HPART_THIGH_L]);
    mb.clear(); buildLimb(mb, 0.042f, 0.028f, 0.430f, true); mb.build(parts[HPART_SHIN_L]);
    mb.clear(); buildFoot(mb); mb.build(parts[HPART_FOOT_L]);
    mb.clear(); buildLimb(mb, 0.062f, 0.044f, 0.440f, true); mb.build(parts[HPART_THIGH_R]);
    mb.clear(); buildLimb(mb, 0.042f, 0.028f, 0.430f, true); mb.build(parts[HPART_SHIN_R]);
    mb.clear(); buildFoot(mb); mb.build(parts[HPART_FOOT_R]);

    mb.clear(); buildHair(mb); mb.build(parts[HPART_HAIR]);

    built = true;
    LOG_INFO("Horror rig built (%d parts)", (int)HPART_COUNT);
}

void HorrorRig::destroy() {
    for (int i = 0; i < HPART_COUNT; i++) parts[i].destroy();
    built = false;
}

void HorrorInstance::configure(int kind, u64 seed) {
    Rng rng(seed ? seed : 0xBADFACE);
    seedValue = seed;
    appearance.kind = clampi(kind, 0, HORROR_KIND_COUNT - 1);
    appearance.height = rng.range(0.98f, 1.14f);
    appearance.gaunt = rng.range(0.86f, 1.04f);
    appearance.armStretch = rng.range(1.02f, 1.18f);
    appearance.neckStretch = rng.range(1.0f, 1.28f);
    appearance.jawDrop = rng.range(0.85f, 1.15f);
    appearance.hasHair = rng.chance(0.7f);

    float pale = rng.range(0.58f, 0.86f);
    appearance.fleshTint = Vec3(pale * 1.02f, pale * 0.94f, pale * 0.90f);
    appearance.darkTint = Vec3(0.06f, 0.05f, 0.06f);

    switch (appearance.kind) {
    case HORROR_CRAWLER:
        appearance.height = rng.range(0.90f, 1.0f);
        appearance.armStretch = rng.range(1.16f, 1.34f);
        appearance.fleshTint = Vec3(pale * 0.80f, pale * 0.74f, pale * 0.70f);
        appearance.hasHair = true;
        break;
    case HORROR_BANDAGED:
        appearance.fleshTint = Vec3(0.94f, 0.90f, 0.82f);
        appearance.hasHair = false;
        appearance.neckStretch = rng.range(0.94f, 1.06f);
        break;
    case HORROR_LONGARM:
        appearance.armStretch = rng.range(1.42f, 1.70f);
        appearance.height = rng.range(1.10f, 1.24f);
        appearance.neckStretch = rng.range(1.24f, 1.48f);
        break;
    default:
        break;
    }

    currentMode = HMODE_STARE;
    modeTime = 0.0f;
    phase = rng.range(0.0f, 10.0f);
    twitch = 0.0f;
    twitchTimer = rng.range(0.4f, 1.6f);
    lunge = 0.0f;
    jawOpen = appearance.kind == HORROR_BANDAGED ? 0.15f : 0.35f;
    breathe = rng.range(0.0f, TAU);
    visibility = 1.0f;
    scale = 1.0f;
    active = true;
}

void HorrorInstance::setMode(int mode) {
    if (mode == currentMode) return;
    currentMode = clampi(mode, 0, HMODE_HANG);
    modeTime = 0.0f;
    if (currentMode == HMODE_LUNGE || currentMode == HMODE_SCREAM) jawOpen = 1.0f;
}

void HorrorInstance::faceTowards(const Vec3& p) {
    Vec3 d = p - position;
    if (lengthSq(Vec2(d.x, d.z)) < 1e-5f) return;
    yaw = std::atan2(d.x, -d.z);
}

Vec3 HorrorInstance::headPosition() const {
    float base = appearance.kind == HORROR_CRAWLER ? 0.72f : 1.62f;
    return position + Vec3(0, base * appearance.height * scale, 0);
}

void HorrorInstance::update(float dt, float time, const Vec3& target) {
    if (!active) return;
    modeTime += dt;
    breathe += dt * (currentMode == HMODE_LUNGE ? 5.4f : 1.35f);

    twitchTimer -= dt;
    if (twitchTimer <= 0.0f) {
        twitchTimer = currentMode == HMODE_TWITCH ? 0.10f + hash11(time * 7.1f) * 0.22f
                                                  : 0.7f + hash11(time * 3.3f) * 2.1f;
        twitch = (hash11(time * 13.7f) - 0.5f) * (currentMode == HMODE_TWITCH ? 2.4f : 0.9f);
    }
    twitch *= std::exp(-dt * 6.0f);

    float lungeTarget = (currentMode == HMODE_LUNGE) ? 1.0f : 0.0f;
    lunge += (lungeTarget - lunge) * std::min(1.0f, dt * 11.0f);

    float jawTarget = 0.2f;
    if (currentMode == HMODE_SCREAM || currentMode == HMODE_LUNGE) jawTarget = 1.0f;
    else if (currentMode == HMODE_CRAWL) jawTarget = 0.65f;
    else if (currentMode == HMODE_TWITCH) jawTarget = 0.45f;
    jawOpen += (jawTarget - jawOpen) * std::min(1.0f, dt * 14.0f);

    if (currentMode == HMODE_CRAWL) phase += dt * 5.4f;
    else if (currentMode == HMODE_LUNGE) phase += dt * 7.2f;
    else phase += dt * 0.55f;

    Vec3 d = target - headPosition();
    float len = length(d);
    if (len > 1e-3f) {
        d /= len;
        float wantYaw = wrapAngle(std::atan2(d.x, -d.z) - yaw);
        float rate = currentMode == HMODE_STARE ? 3.0f : 9.0f;
        headYaw += (clampf(wantYaw, -1.45f, 1.45f) - headYaw) * std::min(1.0f, dt * rate);
        headPitch += (clampf(std::asin(clampf(d.y, -1.0f, 1.0f)), -0.8f, 0.8f) - headPitch) *
                     std::min(1.0f, dt * rate);
    }

    computePose(time);
}

void HorrorInstance::computePose(float time) {
    const HorrorLook& L = appearance;
    const float s = L.height * scale;
    const float g = L.gaunt;
    const bool crawling = currentMode == HMODE_CRAWL;

    float breath = std::sin(breathe) * 0.5f + 0.5f;
    float sway = std::sin(phase * 0.9f) * 0.018f + std::sin(phase * 0.37f) * 0.010f;
    float step = std::sin(phase * TAU);
    float jitter = twitch * 0.12f;

    float pelvisY = (crawling ? 0.44f : 0.95f) * s;
    float leanForward = crawling ? 1.32f : (0.10f + lunge * 0.46f);

    Mat4 root = Mat4::translate(position + Vec3(sway, crawling ? 0.0f : -std::fabs(step) * 0.012f, 0)) *
                Mat4::rotateY(yaw + jitter * 0.5f);

    Mat4 pelvis = root * Mat4::translate(Vec3(0, pelvisY, 0)) *
                  Mat4::rotateX(leanForward * 0.45f) *
                  Mat4::rotateZ(std::sin(phase * TAU) * 0.05f) *
                  Mat4::scale(Vec3(g, 1, g));
    partTransforms[HPART_PELVIS] = pelvis;

    Mat4 spine = pelvis * Mat4::translate(Vec3(0, 0.06f * s, 0)) *
                 Mat4::rotateX(leanForward * 0.28f + jitter * 0.4f) *
                 Mat4::rotateZ(twitch * 0.10f);
    partTransforms[HPART_SPINE] = spine;

    Mat4 ribs = spine * Mat4::translate(Vec3(0, 0.20f * s, 0)) *
                Mat4::rotateX(-leanForward * 0.16f + lunge * 0.22f) *
                Mat4::rotateZ(twitch * 0.14f) *
                Mat4::scale(Vec3(g * (1.0f + breath * 0.05f), 1.0f + breath * 0.03f, g * (1.0f - breath * 0.03f)));
    partTransforms[HPART_RIBS] = ribs;

    Mat4 neck = ribs * Mat4::translate(Vec3(0, 0.175f * s, 0.006f)) *
                Mat4::rotateX(-0.16f + lunge * 0.42f + jitter) *
                Mat4::scale(Vec3(1, L.neckStretch, 1));
    partTransforms[HPART_NECK] = neck;

    Mat4 skull = neck * Mat4::translate(Vec3(0, 0.132f * s * L.neckStretch, 0)) *
                 Mat4::rotateY(headYaw + twitch * 0.5f) *
                 Mat4::rotateX(-headPitch + twitch * 0.3f) *
                 Mat4::rotateZ(twitch * 0.45f);
    partTransforms[HPART_SKULL] = skull;

    partTransforms[HPART_JAW] = skull * Mat4::translate(Vec3(0, -0.020f, -0.010f)) *
                                Mat4::rotateX(jawOpen * L.jawDrop * 0.85f);
    partTransforms[HPART_HAIR] = skull;

    float armSpread = crawling ? 0.55f : (0.16f + lunge * 0.30f);
    float armRaise = crawling ? 1.62f : (lunge > 0.02f ? -1.05f - lunge * 0.85f : 0.06f);
    float armSwing = (crawling ? step * 0.75f : step * 0.20f);

    for (int side = 0; side < 2; side++) {
        float sign = side == 0 ? -1.0f : 1.0f;
        int upper = side == 0 ? HPART_ARM_L : HPART_ARM_R;
        int fore = side == 0 ? HPART_FORE_L : HPART_FORE_R;
        int claw = side == 0 ? HPART_CLAW_L : HPART_CLAW_R;
        float swing = armSwing * sign;

        Mat4 shoulder = ribs * Mat4::translate(Vec3(sign * 0.148f * g, 0.140f * s, 0)) *
                        Mat4::rotateZ(sign * armSpread + twitch * 0.20f * sign) *
                        Mat4::rotateX(armRaise + swing) *
                        Mat4::scale(Vec3(1, L.armStretch, 1));
        partTransforms[upper] = shoulder;

        float elbow = crawling ? -1.15f : (-0.28f - lunge * 0.55f + std::fabs(swing) * 0.5f);
        Mat4 forearm = shoulder * Mat4::translate(Vec3(0, -0.360f * s * L.armStretch, 0)) *
                       Mat4::rotateX(elbow) * Mat4::rotateZ(twitch * 0.12f * sign);
        partTransforms[fore] = forearm;

        partTransforms[claw] = forearm * Mat4::translate(Vec3(0, -0.365f * s * L.armStretch, 0)) *
                               Mat4::rotateX(0.24f + lunge * 0.6f) *
                               Mat4::rotateZ(sign * (0.18f + lunge * 0.4f));
    }

    float hipSpread = 0.075f * g;
    for (int side = 0; side < 2; side++) {
        float sign = side == 0 ? -1.0f : 1.0f;
        int thigh = side == 0 ? HPART_THIGH_L : HPART_THIGH_R;
        int shin = side == 0 ? HPART_SHIN_L : HPART_SHIN_R;
        int foot = side == 0 ? HPART_FOOT_L : HPART_FOOT_R;
        float legPhase = std::sin(phase * TAU + (side == 0 ? 0.0f : PI));
        float hipAngle = crawling ? 1.42f + legPhase * 0.45f
                                  : (currentMode == HMODE_LUNGE ? legPhase * 0.95f : legPhase * 0.16f);
        float kneeAngle = crawling ? -1.75f : (-0.20f - std::max(0.0f, -legPhase) * 0.85f);

        Mat4 hip = pelvis * Mat4::translate(Vec3(sign * hipSpread, -0.020f * s, 0)) *
                   Mat4::rotateX(hipAngle) * Mat4::rotateZ(sign * 0.05f);
        partTransforms[thigh] = hip;

        Mat4 knee = hip * Mat4::translate(Vec3(0, -0.440f * s, 0)) * Mat4::rotateX(kneeAngle);
        partTransforms[shin] = knee;

        partTransforms[foot] = knee * Mat4::translate(Vec3(0, -0.430f * s, 0)) *
                               Mat4::rotateX(crawling ? 0.9f : -hipAngle * 0.4f);
    }
}

void HorrorInstance::submit(Renderer& renderer, const HorrorRig& rig) const {
    if (!active || visibility <= 0.01f) return;

    for (int i = 0; i < HPART_COUNT; i++) {
        if (i == HPART_HAIR && !appearance.hasHair) continue;
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

            if (mat == MAT_SKIN) {
                mat = appearance.kind == HORROR_BANDAGED ? MAT_FABRIC : MAT_SKIN;
                tint = Vec4(appearance.fleshTint, 1.0f);
            } else if (mat == MAT_SERVER_RACK) {
                tint = Vec4(appearance.darkTint, 1.0f);
            } else if (mat == MAT_HAIR) {
                tint = Vec4(0.16f, 0.14f, 0.14f, 1.0f);
            } else if (mat == MAT_PLASTIC_WHITE) {
                tint = Vec4(0.92f, 0.88f, 0.80f, 1.0f);
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
