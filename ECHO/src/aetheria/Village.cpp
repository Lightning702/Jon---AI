#include "Village.h"

using namespace em;
using namespace echo;

namespace aeth {

namespace {

const Vec4 kWall(0.86f, 0.80f, 0.68f, 1.0f);
const Vec4 kBeam(0.34f, 0.24f, 0.17f, 1.0f);
const Vec4 kThatch(0.62f, 0.48f, 0.24f, 1.0f);
const Vec4 kTileRoof(0.52f, 0.24f, 0.19f, 1.0f);
const Vec4 kStone(0.58f, 0.57f, 0.54f, 1.0f);
const Vec4 kGlow(1.00f, 0.74f, 0.38f, 1.0f);

void addTimberFrame(MeshBuilder& mb, float hw, float hd, float h) {
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(kBeam);
    float t = 0.09f;
    mb.addBox(Vec3(-hw, h * 0.5f, -hd), Vec3(t, h * 0.5f, t));
    mb.addBox(Vec3(hw, h * 0.5f, -hd), Vec3(t, h * 0.5f, t));
    mb.addBox(Vec3(-hw, h * 0.5f, hd), Vec3(t, h * 0.5f, t));
    mb.addBox(Vec3(hw, h * 0.5f, hd), Vec3(t, h * 0.5f, t));
    mb.addBox(Vec3(0, h, 0), Vec3(hw + t, t, hd + t));
    mb.addBox(Vec3(0, h * 0.55f, -hd), Vec3(hw, t * 0.7f, t * 0.7f));
    mb.addBox(Vec3(0, h * 0.55f, hd), Vec3(hw, t * 0.7f, t * 0.7f));
}

void addGableRoof(MeshBuilder& mb, float hw, float hd, float base, float peak, const Vec4& color) {
    mb.setMaterial(MAT_FABRIC);
    mb.setColor(color);
    float ow = hw + 0.30f;
    float od = hd + 0.30f;
    float rise = peak - base;

    Vec3 fl(-ow, base, od), fr(ow, base, od);
    Vec3 bl(-ow, base, -od), br(ow, base, -od);
    Vec3 rl(-ow, peak, 0), rr(ow, peak, 0);

    mb.addQuad(fl, fr, rr, rl, normalize(Vec3(0, od, rise)));
    mb.addQuad(br, bl, rl, rr, normalize(Vec3(0, od, -rise)));
    mb.addQuad(bl, fl, rl, rl, Vec3(-1, 0, 0));
    mb.addQuad(fr, br, rr, rr, Vec3(1, 0, 0));
    mb.addQuad(bl, br, fr, fl, Vec3(0, -1, 0));
}

void addWindowPane(MeshBuilder& mb, const Vec3& center, float w, float h, float depth) {
    mb.addBox(center, Vec3(w, h, depth));
}

void addWindowFrame(MeshBuilder& mb, const Vec3& center, float w, float h, float depth) {
    mb.addBox(center + Vec3(0, h, 0), Vec3(w + 0.06f, 0.05f, depth * 1.3f));
    mb.addBox(center - Vec3(0, h, 0), Vec3(w + 0.06f, 0.05f, depth * 1.3f));
}

void buildCottage(BuildingMesh& out) {
    MeshBuilder mb;
    float hw = 2.4f, hd = 2.0f, h = 2.5f;

    mb.setMaterial(MAT_PLASTER);
    mb.setColor(kWall);
    mb.addBox(Vec3(0, h * 0.5f, 0), Vec3(hw, h * 0.5f, hd));
    mb.finishSubMesh();

    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(kStone);
    mb.addBox(Vec3(0, 0.22f, 0), Vec3(hw + 0.14f, 0.22f, hd + 0.14f));
    mb.addBox(Vec3(hw * 0.55f, h + 0.9f, -hd * 0.5f), Vec3(0.28f, 1.5f, 0.28f));
    mb.finishSubMesh();

    addTimberFrame(mb, hw, hd, h);
    addWindowFrame(mb, Vec3(hw * 0.45f, 1.55f, hd + 0.04f), 0.42f, 0.40f, 0.05f);
    addWindowFrame(mb, Vec3(-hw - 0.04f, 1.55f, 0.0f), 0.05f, 0.40f, 0.42f);
    mb.finishSubMesh();

    mb.setMaterial(MAT_WOOD_DOOR);
    mb.setColor(Vec4(0.46f, 0.31f, 0.20f, 1.0f));
    mb.addBox(Vec3(-hw * 0.35f, 1.02f, hd + 0.03f), Vec3(0.48f, 1.02f, 0.07f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(kGlow);
    addWindowPane(mb, Vec3(hw * 0.45f, 1.55f, hd + 0.04f), 0.42f, 0.40f, 0.05f);
    addWindowPane(mb, Vec3(-hw - 0.04f, 1.55f, 0.0f), 0.05f, 0.40f, 0.42f);
    mb.finishSubMesh();

    addGableRoof(mb, hw, hd, h, h + 1.55f, kThatch);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(hw + 0.2f, hd + 0.2f);
    out.blockHeight = h;
    out.lit = true;
    out.lightOffset = Vec3(0, 2.1f, hd + 0.9f);
    out.lightRange = 10.0f;
}

void buildLonghouse(BuildingMesh& out) {
    MeshBuilder mb;
    float hw = 4.6f, hd = 2.6f, h = 3.0f;

    mb.setMaterial(MAT_PLASTER);
    mb.setColor(Vec4(0.80f, 0.75f, 0.64f, 1.0f));
    mb.addBox(Vec3(0, h * 0.5f, 0), Vec3(hw, h * 0.5f, hd));
    mb.finishSubMesh();

    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(kStone);
    mb.addBox(Vec3(0, 0.26f, 0), Vec3(hw + 0.18f, 0.26f, hd + 0.18f));
    mb.finishSubMesh();

    addTimberFrame(mb, hw, hd, h);
    for (int i = -1; i <= 1; i += 2) {
        addWindowFrame(mb, Vec3(i * hw * 0.55f, 1.85f, hd + 0.05f), 0.55f, 0.42f, 0.05f);
        addWindowFrame(mb, Vec3(i * hw * 0.55f, 1.85f, -hd - 0.05f), 0.55f, 0.42f, 0.05f);
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_WOOD_DOOR);
    mb.setColor(Vec4(0.44f, 0.29f, 0.19f, 1.0f));
    mb.addBox(Vec3(0, 1.15f, hd + 0.04f), Vec3(0.72f, 1.15f, 0.08f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(kGlow);
    for (int i = -1; i <= 1; i += 2) {
        addWindowPane(mb, Vec3(i * hw * 0.55f, 1.85f, hd + 0.05f), 0.55f, 0.42f, 0.05f);
        addWindowPane(mb, Vec3(i * hw * 0.55f, 1.85f, -hd - 0.05f), 0.55f, 0.42f, 0.05f);
    }
    mb.finishSubMesh();

    addGableRoof(mb, hw, hd, h, h + 2.0f, kTileRoof);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(hw + 0.24f, hd + 0.24f);
    out.blockHeight = h;
    out.lit = true;
    out.lightOffset = Vec3(0, 2.4f, hd + 1.1f);
    out.lightRange = 12.0f;
}

void buildTower(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(kStone);
    mb.addCylinder(Vec3(0, 0, 0), 1.85f, 8.4f, 12, true);
    mb.addCylinder(Vec3(0, 8.4f, 0), 2.15f, 0.5f, 12, true);
    mb.finishSubMesh();

    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(Vec4(0.50f, 0.49f, 0.47f, 1.0f));
    for (int i = 0; i < 8; i++) {
        float a = TAU * i / 8.0f;
        mb.addBox(Vec3(std::cos(a) * 1.95f, 9.15f, std::sin(a) * 1.95f), Vec3(0.30f, 0.32f, 0.30f));
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(kGlow);
    for (int i = 0; i < 3; i++) {
        float a = TAU * i / 3.0f;
        mb.addBox(Vec3(std::cos(a) * 1.86f, 3.2f + i * 1.9f, std::sin(a) * 1.86f), Vec3(0.22f, 0.42f, 0.22f));
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_FABRIC);
    mb.setColor(kTileRoof);
    mb.addCone(Vec3(0, 8.9f, 0), 2.35f, 0.06f, 2.3f, 12, false);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(1.95f, 1.95f);
    out.blockHeight = 8.4f;
    out.lit = true;
    out.lightOffset = Vec3(0, 9.4f, 0);
    out.lightColor = Vec3(1.0f, 0.85f, 0.55f);
    out.lightRange = 26.0f;
}

void buildWell(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(kStone);
    mb.addCylinder(Vec3(0, 0, 0), 1.15f, 0.92f, 14, false);
    mb.addCylinder(Vec3(0, 0.92f, 0), 1.22f, 0.16f, 14, true);
    mb.finishSubMesh();

    mb.setMaterial(MAT_GLASS);
    mb.setColor(Vec4(0.24f, 0.42f, 0.50f, 1.0f));
    mb.addPlane(Vec3(0, 0.62f, 0), Vec2(2.0f, 2.0f), Vec3(0, 1, 0), 2);
    mb.finishSubMesh();

    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(kBeam);
    mb.addBox(Vec3(-1.0f, 1.6f, 0), Vec3(0.10f, 0.75f, 0.10f));
    mb.addBox(Vec3(1.0f, 1.6f, 0), Vec3(0.10f, 0.75f, 0.10f));
    mb.pushTransform(Mat4::translate(Vec3(1.0f, 2.28f, 0)) * Mat4::rotateZ(HALF_PI));
    mb.addCylinder(Vec3(0, 0, 0), 0.11f, 2.0f, 8, true);
    mb.popTransform();
    mb.addBox(Vec3(0, 2.7f, 0), Vec3(1.35f, 0.09f, 0.62f));
    mb.addBox(Vec3(0.35f, 1.85f, 0), Vec3(0.28f, 0.26f, 0.28f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_FABRIC);
    mb.setColor(kThatch);
    mb.addCone(Vec3(0, 2.72f, 0), 1.55f, 0.05f, 0.85f, 4, false);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(1.2f, 1.2f);
    out.blockHeight = 1.1f;
}

void buildStall(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.48f, 0.35f, 0.22f, 1.0f));
    mb.addBox(Vec3(0, 0.92f, 0), Vec3(1.5f, 0.08f, 0.72f));
    for (int i = -1; i <= 1; i += 2) {
        for (int j = -1; j <= 1; j += 2) {
            mb.addBox(Vec3(i * 1.35f, 0.45f, j * 0.60f), Vec3(0.07f, 0.45f, 0.07f));
            mb.addBox(Vec3(i * 1.35f, 1.55f, j * 0.60f), Vec3(0.06f, 0.62f, 0.06f));
        }
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(0.72f, 0.26f, 0.24f, 1.0f));
    mb.addBox(Vec3(0, 2.22f, 0), Vec3(1.62f, 0.06f, 0.86f));
    mb.addBox(Vec3(0, 1.98f, 0.86f), Vec3(1.62f, 0.24f, 0.05f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.setColor(Vec4(0.86f, 0.52f, 0.24f, 1.0f));
    for (int i = 0; i < 6; i++) {
        float fx = -1.1f + (i % 3) * 0.75f;
        float fz = (i / 3) * 0.42f - 0.21f;
        mb.addSphere(Vec3(fx, 1.10f, fz), 0.14f, 5, 7);
    }
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(1.5f, 0.75f);
    out.blockHeight = 1.0f;
}

void buildFence(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.44f, 0.34f, 0.24f, 1.0f));
    for (int i = 0; i < 4; i++) {
        mb.addBox(Vec3(-1.35f + i * 0.9f, 0.55f, 0), Vec3(0.07f, 0.55f, 0.07f));
    }
    mb.addBox(Vec3(0, 0.92f, 0), Vec3(1.5f, 0.055f, 0.05f));
    mb.addBox(Vec3(0, 0.55f, 0), Vec3(1.5f, 0.055f, 0.05f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(0, 0);
    out.blockHeight = 0.0f;
}

void buildBanner(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(kBeam);
    mb.addCylinder(Vec3(0, 0, 0), 0.09f, 4.2f, 8, true);
    mb.addBox(Vec3(0.42f, 4.05f, 0), Vec3(0.45f, 0.05f, 0.05f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(0.30f, 0.42f, 0.72f, 1.0f));
    mb.addBox(Vec3(0.62f, 3.25f, 0), Vec3(0.32f, 0.72f, 0.02f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(Vec4(1.0f, 0.80f, 0.45f, 1.0f));
    mb.addSphere(Vec3(0, 4.34f, 0), 0.14f, 6, 8);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(0, 0);
    out.blockHeight = 0.0f;
    out.lit = true;
    out.lightOffset = Vec3(0, 4.34f, 0);
    out.lightColor = Vec3(1.0f, 0.78f, 0.44f);
    out.lightRange = 14.0f;
}

void buildCampfire(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(kStone);
    for (int i = 0; i < 9; i++) {
        float a = TAU * i / 9.0f;
        mb.addSphere(Vec3(std::cos(a) * 0.82f, 0.10f, std::sin(a) * 0.82f), 0.20f, 4, 6);
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.30f, 0.22f, 0.16f, 1.0f));
    for (int i = 0; i < 5; i++) {
        float a = TAU * i / 5.0f;
        mb.pushTransform(Mat4::translate(Vec3(std::cos(a) * 0.34f, 0.05f, std::sin(a) * 0.34f)) *
                         Mat4::rotateY(a) * Mat4::rotateZ(-0.62f));
        mb.addCone(Vec3(0, 0, 0), 0.08f, 0.05f, 0.95f, 5, false);
        mb.popTransform();
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(Vec4(1.0f, 0.55f, 0.20f, 1.0f));
    mb.addSphere(Vec3(0, 0.34f, 0), 0.30f, 5, 8);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(0.55f, 0.55f);
    out.blockHeight = 0.5f;
    out.lit = true;
    out.lightOffset = Vec3(0, 0.65f, 0);
    out.lightColor = Vec3(1.0f, 0.56f, 0.24f);
    out.lightRange = 13.0f;
}

void buildShrine(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(Vec4(0.62f, 0.61f, 0.58f, 1.0f));
    mb.addCylinder(Vec3(0, 0, 0), 2.05f, 0.32f, 12, true);
    mb.addCylinder(Vec3(0, 0.32f, 0), 1.70f, 0.26f, 12, true);
    for (int i = 0; i < 4; i++) {
        float a = TAU * i / 4.0f + PI * 0.25f;
        mb.addCylinder(Vec3(std::cos(a) * 1.32f, 0.58f, std::sin(a) * 1.32f), 0.20f, 2.9f, 8, true);
    }
    mb.addBox(Vec3(0, 3.62f, 0), Vec3(1.62f, 0.16f, 1.62f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_FABRIC);
    mb.setColor(Vec4(0.44f, 0.30f, 0.24f, 1.0f));
    mb.addCone(Vec3(0, 3.78f, 0), 1.85f, 0.10f, 1.05f, 4, false);
    mb.finishSubMesh();

    mb.setMaterial(MAT_GLASS);
    mb.setColor(Vec4(0.55f, 0.88f, 1.0f, 1.0f));
    mb.addCone(Vec3(0, 0.58f, 0), 0.34f, 0.03f, 1.35f, 6, true);
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(Vec4(0.50f, 0.86f, 1.0f, 1.0f));
    mb.addSphere(Vec3(0, 2.30f, 0), 0.26f, 6, 9);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(0, 0);
    out.blockHeight = 0.0f;
    out.lit = true;
    out.lightOffset = Vec3(0, 2.30f, 0);
    out.lightColor = Vec3(0.46f, 0.80f, 1.0f);
    out.lightRange = 18.0f;
}

void buildRuinArch(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(Vec4(0.55f, 0.55f, 0.51f, 1.0f));
    mb.addBox(Vec3(-2.2f, 2.3f, 0), Vec3(0.52f, 2.3f, 0.52f));
    mb.addBox(Vec3(2.2f, 2.3f, 0), Vec3(0.52f, 2.3f, 0.52f));
    mb.pushTransform(Mat4::translate(Vec3(0, 4.6f, 0)) * Mat4::rotateX(-HALF_PI));
    mb.addTorusArc(Vec3(0, 0, 0), 2.2f, 0.44f, 0.0f, PI * 0.70f, 12, 7);
    mb.popTransform();
    mb.addBox(Vec3(0, 0.22f, 0), Vec3(3.4f, 0.22f, 1.3f));
    mb.addBox(Vec3(-3.9f, 0.45f, 1.1f), Vec3(0.60f, 0.45f, 0.55f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(0.32f, 0.52f, 0.28f, 1.0f));
    mb.addSphere(Vec3(-2.2f, 4.8f, 0.2f), 0.62f, 5, 7);
    mb.addSphere(Vec3(2.3f, 4.7f, -0.2f), 0.52f, 5, 7);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(0, 0);
    out.blockHeight = 0.0f;
}

void buildStandingStone(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(Vec4(0.46f, 0.47f, 0.50f, 1.0f));
    mb.pushTransform(Mat4::rotateZ(0.06f));
    mb.addBox(Vec3(0, 1.9f, 0), Vec3(0.52f, 1.9f, 0.36f));
    mb.popTransform();
    mb.addBox(Vec3(0, 0.18f, 0), Vec3(0.90f, 0.18f, 0.75f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(Vec4(0.42f, 0.78f, 1.0f, 1.0f));
    mb.addBox(Vec3(0, 2.55f, 0.37f), Vec3(0.20f, 0.42f, 0.03f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(0.55f, 0.40f);
    out.blockHeight = 3.6f;
    out.lit = true;
    out.lightOffset = Vec3(0, 2.55f, 0.6f);
    out.lightColor = Vec3(0.40f, 0.74f, 1.0f);
    out.lightRange = 9.0f;
}

void buildSignpost(BuildingMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.46f, 0.34f, 0.22f, 1.0f));
    mb.addCylinder(Vec3(0, 0, 0), 0.10f, 2.35f, 8, true);
    mb.pushTransform(Mat4::translate(Vec3(0.55f, 1.95f, 0)));
    mb.addBox(Vec3(0, 0, 0), Vec3(0.55f, 0.16f, 0.04f));
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(-0.5f, 1.55f, 0)) * Mat4::rotateY(PI));
    mb.addBox(Vec3(0, 0, 0), Vec3(0.50f, 0.15f, 0.04f));
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(Vec4(1.0f, 0.76f, 0.40f, 1.0f));
    mb.addSphere(Vec3(0, 2.46f, 0), 0.11f, 5, 7);
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.blockHalf = Vec2(0, 0);
    out.blockHeight = 0.0f;
    out.lit = true;
    out.lightOffset = Vec3(0, 2.46f, 0);
    out.lightColor = Vec3(1.0f, 0.74f, 0.42f);
    out.lightRange = 8.0f;
}

}

void BuildingLibrary::build() {
    buildCottage(meshes[BUILD_COTTAGE]);
    buildLonghouse(meshes[BUILD_LONGHOUSE]);
    buildTower(meshes[BUILD_TOWER]);
    buildWell(meshes[BUILD_WELL]);
    buildStall(meshes[BUILD_STALL]);
    buildFence(meshes[BUILD_FENCE]);
    buildBanner(meshes[BUILD_BANNER]);
    buildCampfire(meshes[BUILD_CAMPFIRE]);
    buildShrine(meshes[BUILD_SHRINE]);
    buildRuinArch(meshes[BUILD_RUIN_ARCH]);
    buildStandingStone(meshes[BUILD_STANDING_STONE]);
    buildSignpost(meshes[BUILD_SIGNPOST]);
}

void BuildingLibrary::destroy() {
    for (int i = 0; i < BUILD_COUNT; i++) meshes[i].mesh.destroy();
}

Vec2 resolveBoxes(const std::vector<BoxCollider>& boxes, const Vec2& point, float radius) {
    Vec2 p = point;
    for (int pass = 0; pass < 4; pass++) {
        bool moved = false;
        for (const BoxCollider& b : boxes) {
            Vec2 d = p - b.center;
            Vec2 local(d.x * b.cosYaw + d.y * b.sinYaw, -d.x * b.sinYaw + d.y * b.cosYaw);
            float ex = b.half.x + radius;
            float ez = b.half.y + radius;
            if (std::fabs(local.x) >= ex || std::fabs(local.y) >= ez) continue;

            float px = ex - std::fabs(local.x);
            float pz = ez - std::fabs(local.y);
            if (px < pz) local.x += local.x < 0.0f ? -px : px;
            else local.y += local.y < 0.0f ? -pz : pz;

            p = b.center + Vec2(local.x * b.cosYaw - local.y * b.sinYaw, local.x * b.sinYaw + local.y * b.cosYaw);
            moved = true;
        }
        if (!moved) break;
    }
    return p;
}

}
