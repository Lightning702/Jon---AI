#include "Props.h"
#include "../core/Random.h"
#include "../core/Log.h"
#include "../core/Time.h"

using namespace em;

namespace echo {

namespace {

void frame(MeshBuilder& mb, const Vec3& c, const Vec3& half, float thickness) {
    mb.addBox(Vec3(c.x, c.y + half.y - thickness, c.z), Vec3(half.x, thickness, half.z));
    mb.addBox(Vec3(c.x, c.y - half.y + thickness, c.z), Vec3(half.x, thickness, half.z));
    mb.addBox(Vec3(c.x - half.x + thickness, c.y, c.z), Vec3(thickness, half.y - thickness * 2, half.z));
    mb.addBox(Vec3(c.x + half.x - thickness, c.y, c.z), Vec3(thickness, half.y - thickness * 2, half.z));
}

void legs(MeshBuilder& mb, const Vec3& c, const Vec3& half, float height, float r) {
    for (int i = 0; i < 4; i++) {
        float sx = (i & 1) ? 1.0f : -1.0f;
        float sz = (i & 2) ? 1.0f : -1.0f;
        mb.addBox(Vec3(c.x + sx * (half.x - r), c.y + height * 0.5f, c.z + sz * (half.z - r)), Vec3(r, height * 0.5f, r));
    }
}

void castors(MeshBuilder& mb, const Vec3& c, const Vec3& half, float y) {
    for (int i = 0; i < 4; i++) {
        float sx = (i & 1) ? 1.0f : -1.0f;
        float sz = (i & 2) ? 1.0f : -1.0f;
        Vec3 p(c.x + sx * (half.x - 0.06f), y, c.z + sz * (half.z - 0.06f));
        mb.pushTransform(Mat4::translate(p) * Mat4::rotateZ(HALF_PI));
        mb.addCylinder(Vec3(0, -0.02f, 0), 0.045f, 0.04f, 10);
        mb.popTransform();
    }
}

void buildBed(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0.52f, 0), Vec3(0.46f, 0.035f, 1.00f));
    legs(mb, Vec3(0, 0, 0), Vec3(0.42f, 0, 0.94f), 0.50f, 0.022f);
    mb.addBox(Vec3(0, 0.36f, 0), Vec3(0.38f, 0.02f, 0.88f));
    frame(mb, Vec3(0, 0.86f, -1.02f), Vec3(0.44f, 0.30f, 0.02f), 0.026f);
    for (int i = 0; i < 5; i++) {
        float t = -0.30f + i * 0.15f;
        mb.addBox(Vec3(t, 0.86f, -1.02f), Vec3(0.012f, 0.26f, 0.018f));
    }
    frame(mb, Vec3(0, 0.75f, 1.02f), Vec3(0.44f, 0.20f, 0.02f), 0.024f);
    mb.addBox(Vec3(-0.47f, 0.70f, -0.35f), Vec3(0.018f, 0.16f, 0.42f));
    mb.addBox(Vec3(0.47f, 0.70f, 0.30f), Vec3(0.018f, 0.16f, 0.42f));
    castors(mb, Vec3(0, 0, 0), Vec3(0.42f, 0, 0.94f), 0.05f);
    mb.finishSubMesh();

    mb.setMaterial(MAT_MATTRESS);
    mb.addBox(Vec3(0, 0.60f, -0.05f), Vec3(0.43f, 0.055f, 0.92f));
    mb.addBox(Vec3(0, 0.68f, -0.72f), Vec3(0.26f, 0.035f, 0.18f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_FABRIC);
    mb.addBox(Vec3(0, 0.665f, 0.15f), Vec3(0.44f, 0.012f, 0.70f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.48f, 0.45f, 1.05f);
    out.colliderOffset = Vec3(0, 0.45f, 0);
}

void buildGurney(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0.74f, 0), Vec3(0.36f, 0.03f, 0.95f));
    mb.addBox(Vec3(0, 0.30f, 0), Vec3(0.30f, 0.02f, 0.80f));
    for (int i = 0; i < 4; i++) {
        float sx = (i & 1) ? 1.0f : -1.0f;
        float sz = (i & 2) ? 1.0f : -1.0f;
        mb.addBox(Vec3(sx * 0.30f, 0.40f, sz * 0.82f), Vec3(0.02f, 0.34f, 0.02f));
    }
    mb.addBox(Vec3(0, 0.98f, -0.96f), Vec3(0.34f, 0.02f, 0.02f));
    mb.addBox(Vec3(-0.34f, 0.86f, -0.96f), Vec3(0.02f, 0.14f, 0.02f));
    mb.addBox(Vec3(0.34f, 0.86f, -0.96f), Vec3(0.02f, 0.14f, 0.02f));
    castors(mb, Vec3(0, 0, 0), Vec3(0.32f, 0, 0.84f), 0.06f);
    mb.finishSubMesh();

    mb.setMaterial(MAT_MATTRESS);
    mb.addBox(Vec3(0, 0.80f, 0), Vec3(0.34f, 0.04f, 0.92f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.38f, 0.45f, 0.98f);
    out.colliderOffset = Vec3(0, 0.45f, 0);
}

void buildCrib(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0.44f, 0), Vec3(0.34f, 0.025f, 0.62f));
    legs(mb, Vec3(0, 0, 0), Vec3(0.32f, 0, 0.60f), 0.42f, 0.018f);
    for (int side = 0; side < 2; side++) {
        float sz = side ? 1.0f : -1.0f;
        mb.addBox(Vec3(0, 0.74f, sz * 0.62f), Vec3(0.34f, 0.02f, 0.02f));
        for (int i = 0; i < 9; i++) {
            float x = -0.30f + i * 0.075f;
            mb.addBox(Vec3(x, 0.60f, sz * 0.62f), Vec3(0.009f, 0.16f, 0.012f));
        }
    }
    for (int side = 0; side < 2; side++) {
        float sx = side ? 1.0f : -1.0f;
        mb.addBox(Vec3(sx * 0.34f, 0.74f, 0), Vec3(0.02f, 0.02f, 0.62f));
        for (int i = 0; i < 15; i++) {
            float z = -0.56f + i * 0.08f;
            mb.addBox(Vec3(sx * 0.34f, 0.60f, z), Vec3(0.012f, 0.16f, 0.009f));
        }
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_MATTRESS);
    mb.addBox(Vec3(0, 0.50f, 0), Vec3(0.32f, 0.035f, 0.60f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.36f, 0.40f, 0.65f);
    out.colliderOffset = Vec3(0, 0.40f, 0);
}

void buildWheelchair(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.pushTransform(Mat4::translate(Vec3(-0.26f, 0.30f, 0.05f)) * Mat4::rotateZ(HALF_PI));
    mb.addCylinder(Vec3(0, -0.015f, 0), 0.29f, 0.03f, 20);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0.26f, 0.30f, 0.05f)) * Mat4::rotateZ(HALF_PI));
    mb.addCylinder(Vec3(0, -0.015f, 0), 0.29f, 0.03f, 20);
    mb.popTransform();
    for (int w = 0; w < 2; w++) {
        float sx = w ? 1.0f : -1.0f;
        for (int s = 0; s < 8; s++) {
            float a = TAU * s / 8.0f;
            mb.pushTransform(Mat4::translate(Vec3(sx * 0.26f, 0.30f, 0.05f)) * Mat4::rotateX(a));
            mb.addBox(Vec3(0, 0.145f, 0), Vec3(0.006f, 0.145f, 0.006f));
            mb.popTransform();
        }
    }
    mb.pushTransform(Mat4::translate(Vec3(-0.22f, 0.08f, -0.34f)) * Mat4::rotateZ(HALF_PI));
    mb.addCylinder(Vec3(0, -0.012f, 0), 0.075f, 0.024f, 12);
    mb.popTransform();
    mb.pushTransform(Mat4::translate(Vec3(0.22f, 0.08f, -0.34f)) * Mat4::rotateZ(HALF_PI));
    mb.addCylinder(Vec3(0, -0.012f, 0), 0.075f, 0.024f, 12);
    mb.popTransform();

    mb.addBox(Vec3(-0.24f, 0.52f, 0.05f), Vec3(0.018f, 0.30f, 0.018f));
    mb.addBox(Vec3(0.24f, 0.52f, 0.05f), Vec3(0.018f, 0.30f, 0.018f));
    mb.addBox(Vec3(-0.24f, 0.84f, -0.02f), Vec3(0.016f, 0.016f, 0.14f));
    mb.addBox(Vec3(0.24f, 0.84f, -0.02f), Vec3(0.016f, 0.016f, 0.14f));
    mb.addBox(Vec3(-0.24f, 0.62f, -0.22f), Vec3(0.03f, 0.02f, 0.14f));
    mb.addBox(Vec3(0.24f, 0.62f, -0.22f), Vec3(0.03f, 0.02f, 0.14f));
    mb.addBox(Vec3(-0.16f, 0.16f, -0.42f), Vec3(0.06f, 0.014f, 0.09f));
    mb.addBox(Vec3(0.16f, 0.16f, -0.42f), Vec3(0.06f, 0.014f, 0.09f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_FABRIC);
    mb.addBox(Vec3(0, 0.46f, -0.05f), Vec3(0.22f, 0.02f, 0.22f));
    mb.addBox(Vec3(0, 0.66f, 0.16f), Vec3(0.22f, 0.20f, 0.02f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.30f, 0.45f, 0.42f);
    out.colliderOffset = Vec3(0, 0.45f, 0);
}

void buildIVStand(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    for (int i = 0; i < 5; i++) {
        float a = TAU * i / 5.0f;
        mb.pushTransform(Mat4::rotateY(a));
        mb.addBox(Vec3(0, 0.02f, 0.14f), Vec3(0.012f, 0.012f, 0.14f));
        mb.popTransform();
    }
    mb.addCylinder(Vec3(0, 0.02f, 0), 0.016f, 1.55f, 10);
    mb.addBox(Vec3(0, 1.56f, 0), Vec3(0.10f, 0.010f, 0.010f));
    mb.addBox(Vec3(-0.10f, 1.53f, 0), Vec3(0.008f, 0.03f, 0.008f));
    mb.addBox(Vec3(0.10f, 1.53f, 0), Vec3(0.008f, 0.03f, 0.008f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(-0.10f, 1.40f, 0), Vec3(0.045f, 0.09f, 0.02f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.18f, 0.80f, 0.18f);
    out.colliderOffset = Vec3(0, 0.80f, 0);
}

void buildMonitorCart(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0.72f, 0), Vec3(0.24f, 0.02f, 0.20f));
    mb.addCylinder(Vec3(0, 0.06f, 0), 0.022f, 0.66f, 10);
    mb.addBox(Vec3(0, 0.06f, 0), Vec3(0.20f, 0.02f, 0.20f));
    castors(mb, Vec3(0, 0, 0), Vec3(0.18f, 0, 0.18f), 0.04f);
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0.90f, 0), Vec3(0.20f, 0.16f, 0.13f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_SERVER_RACK);
    mb.addBox(Vec3(0, 0.92f, -0.135f), Vec3(0.17f, 0.12f, 0.006f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.24f, 0.55f, 0.22f);
    out.colliderOffset = Vec3(0, 0.55f, 0);
}

void buildDefibrillator(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0.14f, 0), Vec3(0.22f, 0.14f, 0.17f));
    mb.addBox(Vec3(0, 0.30f, 0.05f), Vec3(0.18f, 0.03f, 0.10f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_RUBBER);
    mb.addBox(Vec3(-0.10f, 0.31f, -0.06f), Vec3(0.06f, 0.03f, 0.06f));
    mb.addBox(Vec3(0.10f, 0.31f, -0.06f), Vec3(0.06f, 0.03f, 0.06f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.23f, 0.17f, 0.18f);
    out.colliderOffset = Vec3(0, 0.17f, 0);
}

void buildCabinet(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0.90f, 0), Vec3(0.44f, 0.90f, 0.22f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    for (int i = 0; i < 3; i++) {
        float y = 0.36f + i * 0.55f;
        mb.addBox(Vec3(-0.22f, y, -0.225f), Vec3(0.20f, 0.24f, 0.008f));
        mb.addBox(Vec3(0.22f, y, -0.225f), Vec3(0.20f, 0.24f, 0.008f));
        mb.addBox(Vec3(-0.03f, y, -0.245f), Vec3(0.012f, 0.05f, 0.014f));
        mb.addBox(Vec3(0.03f, y, -0.245f), Vec3(0.012f, 0.05f, 0.014f));
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.45f, 0.90f, 0.24f);
    out.colliderOffset = Vec3(0, 0.90f, 0);
}

void buildFileCabinet(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0.66f, 0), Vec3(0.26f, 0.66f, 0.30f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    for (int i = 0; i < 4; i++) {
        float y = 0.20f + i * 0.31f;
        mb.addBox(Vec3(0, y, -0.305f), Vec3(0.24f, 0.135f, 0.008f));
        mb.addBox(Vec3(0, y, -0.325f), Vec3(0.07f, 0.018f, 0.016f));
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.27f, 0.66f, 0.32f);
    out.colliderOffset = Vec3(0, 0.66f, 0);
}

void buildLocker(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0.95f, 0), Vec3(0.45f, 0.95f, 0.24f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    for (int i = 0; i < 3; i++) {
        float x = -0.30f + i * 0.30f;
        mb.addBox(Vec3(x, 0.95f, -0.245f), Vec3(0.135f, 0.90f, 0.008f));
        mb.addBox(Vec3(x + 0.10f, 1.05f, -0.262f), Vec3(0.014f, 0.06f, 0.012f));
        for (int s = 0; s < 4; s++)
            mb.addBox(Vec3(x, 1.60f + s * 0.035f, -0.256f), Vec3(0.10f, 0.006f, 0.004f));
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.46f, 0.95f, 0.26f);
    out.colliderOffset = Vec3(0, 0.95f, 0);
}

void buildShelf(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_RUST);
    mb.addBox(Vec3(-0.48f, 1.00f, -0.20f), Vec3(0.025f, 1.00f, 0.025f));
    mb.addBox(Vec3(0.48f, 1.00f, -0.20f), Vec3(0.025f, 1.00f, 0.025f));
    mb.addBox(Vec3(-0.48f, 1.00f, 0.20f), Vec3(0.025f, 1.00f, 0.025f));
    mb.addBox(Vec3(0.48f, 1.00f, 0.20f), Vec3(0.025f, 1.00f, 0.025f));
    for (int i = 0; i < 4; i++) {
        float y = 0.30f + i * 0.55f;
        mb.addBox(Vec3(0, y, 0), Vec3(0.50f, 0.014f, 0.23f));
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.51f, 1.00f, 0.25f);
    out.colliderOffset = Vec3(0, 1.00f, 0);
}

void buildDesk(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.addBox(Vec3(0, 0.73f, 0), Vec3(0.70f, 0.025f, 0.34f));
    mb.addBox(Vec3(-0.62f, 0.37f, 0), Vec3(0.03f, 0.37f, 0.32f));
    mb.addBox(Vec3(0.42f, 0.42f, 0), Vec3(0.26f, 0.32f, 0.32f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    for (int i = 0; i < 3; i++) {
        float y = 0.24f + i * 0.20f;
        mb.addBox(Vec3(0.42f, y, -0.325f), Vec3(0.24f, 0.085f, 0.008f));
        mb.addBox(Vec3(0.42f, y, -0.342f), Vec3(0.06f, 0.014f, 0.012f));
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.71f, 0.38f, 0.35f);
    out.colliderOffset = Vec3(0, 0.38f, 0);
}

void buildTable(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0.74f, 0), Vec3(0.55f, 0.02f, 0.38f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    legs(mb, Vec3(0, 0, 0), Vec3(0.52f, 0, 0.35f), 0.73f, 0.018f);
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.56f, 0.38f, 0.39f);
    out.colliderOffset = Vec3(0, 0.38f, 0);
}

void buildChair(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    legs(mb, Vec3(0, 0, 0), Vec3(0.21f, 0, 0.21f), 0.44f, 0.014f);
    mb.addBox(Vec3(0, 0.66f, 0.20f), Vec3(0.015f, 0.22f, 0.015f));
    mb.addBox(Vec3(-0.19f, 0.66f, 0.20f), Vec3(0.015f, 0.22f, 0.015f));
    mb.addBox(Vec3(0.19f, 0.66f, 0.20f), Vec3(0.015f, 0.22f, 0.015f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0.45f, 0), Vec3(0.22f, 0.018f, 0.22f));
    mb.addBox(Vec3(0, 0.72f, 0.205f), Vec3(0.21f, 0.16f, 0.018f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.23f, 0.30f, 0.23f);
    out.colliderOffset = Vec3(0, 0.30f, 0);
}

void buildStool(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addCylinder(Vec3(0, 0.02f, 0), 0.028f, 0.50f, 10);
    for (int i = 0; i < 5; i++) {
        mb.pushTransform(Mat4::rotateY(TAU * i / 5.0f));
        mb.addBox(Vec3(0, 0.03f, 0.13f), Vec3(0.014f, 0.014f, 0.13f));
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.setMaterial(MAT_RUBBER);
    mb.addCylinder(Vec3(0, 0.52f, 0), 0.17f, 0.05f, 16);
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.18f, 0.30f, 0.18f);
    out.colliderOffset = Vec3(0, 0.30f, 0);
}

void buildBench(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.addBox(Vec3(0, 0.44f, 0), Vec3(0.90f, 0.025f, 0.20f));
    mb.addBox(Vec3(0, 0.72f, 0.18f), Vec3(0.90f, 0.16f, 0.022f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(-0.78f, 0.22f, 0), Vec3(0.02f, 0.22f, 0.18f));
    mb.addBox(Vec3(0.78f, 0.22f, 0), Vec3(0.02f, 0.22f, 0.18f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.92f, 0.30f, 0.22f);
    out.colliderOffset = Vec3(0, 0.30f, 0);
}

void buildTrolley(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0.86f, 0), Vec3(0.30f, 0.02f, 0.22f));
    mb.addBox(Vec3(0, 0.52f, 0), Vec3(0.28f, 0.018f, 0.21f));
    mb.addBox(Vec3(0, 0.20f, 0), Vec3(0.28f, 0.018f, 0.21f));
    for (int i = 0; i < 4; i++) {
        float sx = (i & 1) ? 1.0f : -1.0f;
        float sz = (i & 2) ? 1.0f : -1.0f;
        mb.addBox(Vec3(sx * 0.28f, 0.46f, sz * 0.19f), Vec3(0.016f, 0.42f, 0.016f));
    }
    mb.addBox(Vec3(0, 0.98f, 0.24f), Vec3(0.28f, 0.014f, 0.014f));
    castors(mb, Vec3(0, 0, 0), Vec3(0.26f, 0, 0.18f), 0.04f);
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.31f, 0.50f, 0.24f);
    out.colliderOffset = Vec3(0, 0.50f, 0);
}

void buildBin(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_RUST);
    mb.addCone(Vec3(0, 0, 0), 0.16f, 0.20f, 0.56f, 14, true);
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.20f, 0.28f, 0.20f);
    out.colliderOffset = Vec3(0, 0.28f, 0);
}

void buildSink(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0.82f, 0), Vec3(0.28f, 0.08f, 0.22f));
    mb.addBoxInner(Vec3(0, 0.86f, 0), Vec3(0.22f, 0.06f, 0.16f));
    mb.addBox(Vec3(0, 0.50f, 0.12f), Vec3(0.09f, 0.26f, 0.09f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    mb.addCylinder(Vec3(0, 0.90f, 0.16f), 0.018f, 0.16f, 10);
    mb.addBox(Vec3(0, 1.05f, 0.09f), Vec3(0.016f, 0.016f, 0.08f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.29f, 0.45f, 0.24f);
    out.colliderOffset = Vec3(0, 0.45f, 0);
}

void buildToilet(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0.20f, 0), Vec3(0.17f, 0.20f, 0.24f));
    mb.addCylinder(Vec3(0, 0.38f, -0.04f), 0.19f, 0.06f, 16);
    mb.addBox(Vec3(0, 0.58f, 0.22f), Vec3(0.21f, 0.24f, 0.10f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.22f, 0.42f, 0.30f);
    out.colliderOffset = Vec3(0, 0.42f, 0);
}

void buildMirror(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    frame(mb, Vec3(0, 0, 0), Vec3(0.36f, 0.48f, 0.025f), 0.028f);
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0, 0.008f), Vec3(0.33f, 0.45f, 0.012f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildRadiator(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    for (int i = 0; i < 12; i++) {
        float x = -0.42f + i * 0.077f;
        mb.addBox(Vec3(x, 0.32f, 0), Vec3(0.024f, 0.28f, 0.055f));
    }
    mb.addBox(Vec3(0, 0.60f, 0), Vec3(0.46f, 0.02f, 0.06f));
    mb.addBox(Vec3(0, 0.05f, 0), Vec3(0.46f, 0.02f, 0.06f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_METAL_RUST);
    mb.addCylinder(Vec3(-0.44f, 0.0f, 0.0f), 0.018f, 0.30f, 8);
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.47f, 0.32f, 0.08f);
    out.colliderOffset = Vec3(0, 0.32f, 0);
}

void buildPipes(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_RUST);
    mb.pushTransform(Mat4::rotateX(HALF_PI));
    mb.addCylinder(Vec3(0.0f, 0, 0), 0.055f, 4.0f, 12);
    mb.addCylinder(Vec3(0.16f, 0, 0), 0.038f, 4.0f, 10);
    mb.popTransform();
    for (int i = 0; i < 3; i++) {
        float z = -1.4f + i * 1.4f;
        mb.addBox(Vec3(0.08f, 0.11f, z), Vec3(0.16f, 0.014f, 0.02f));
    }
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    mb.pushTransform(Mat4::translate(Vec3(0, 0, -0.6f)) * Mat4::rotateX(HALF_PI));
    mb.addCylinder(Vec3(0, -0.05f, 0), 0.072f, 0.10f, 12);
    mb.popTransform();
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildDuct(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.30f, 0.22f, 2.0f));
    for (int i = 0; i < 5; i++) {
        float z = -1.6f + i * 0.8f;
        mb.addBox(Vec3(0, 0, z), Vec3(0.32f, 0.24f, 0.03f));
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.32f, 0.24f, 2.0f);
}

void buildCeilingLamp(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, -0.03f, 0), Vec3(0.62f, 0.055f, 0.16f));
    mb.addBox(Vec3(0, 0.02f, 0), Vec3(0.58f, 0.02f, 0.12f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.addBox(Vec3(0, -0.085f, 0), Vec3(0.56f, 0.014f, 0.115f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildWallLamp(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0, 0.04f), Vec3(0.13f, 0.19f, 0.05f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.addBox(Vec3(0, 0, -0.02f), Vec3(0.105f, 0.16f, 0.03f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildORLamp(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addCylinder(Vec3(0, 0.0f, 0), 0.035f, 0.55f, 10);
    mb.addBox(Vec3(0, -0.05f, 0.30f), Vec3(0.025f, 0.025f, 0.30f));
    mb.pushTransform(Mat4::translate(Vec3(0, -0.16f, 0.58f)));
    mb.addCone(Vec3(0, 0, 0), 0.46f, 0.40f, 0.14f, 20, true);
    mb.popTransform();
    mb.finishSubMesh();
    mb.setMaterial(MAT_LIGHT_PANEL);
    for (int i = 0; i < 6; i++) {
        float a = TAU * i / 6.0f;
        mb.addCylinder(Vec3(std::cos(a) * 0.22f, -0.175f, 0.58f + std::sin(a) * 0.22f), 0.075f, 0.012f, 12);
    }
    mb.addCylinder(Vec3(0, -0.175f, 0.58f), 0.085f, 0.012f, 12);
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildORTable(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0.86f, 0), Vec3(0.30f, 0.04f, 1.00f));
    mb.addBox(Vec3(0, 0.45f, 0), Vec3(0.11f, 0.42f, 0.16f));
    mb.addBox(Vec3(0, 0.06f, 0), Vec3(0.26f, 0.06f, 0.50f));
    mb.addBox(Vec3(0, 0.98f, -0.90f), Vec3(0.22f, 0.03f, 0.16f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_RUBBER);
    mb.addBox(Vec3(0, 0.92f, 0), Vec3(0.28f, 0.035f, 0.96f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.32f, 0.50f, 1.02f);
    out.colliderOffset = Vec3(0, 0.50f, 0);
}

void buildXrayMachine(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0.55f, 0), Vec3(0.55f, 0.55f, 0.45f));
    mb.addBox(Vec3(0, 1.30f, 0.0f), Vec3(0.09f, 0.22f, 0.09f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 1.58f, 0.30f), Vec3(0.06f, 0.06f, 0.42f));
    mb.pushTransform(Mat4::translate(Vec3(0, 1.44f, 0.66f)));
    mb.addCone(Vec3(0, 0, 0), 0.20f, 0.13f, 0.24f, 16, true);
    mb.popTransform();
    mb.addBox(Vec3(0, 1.0f, -0.90f), Vec3(0.50f, 0.72f, 0.05f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.56f, 0.80f, 0.48f);
    out.colliderOffset = Vec3(0, 0.80f, 0);
}

void buildMorgueWall(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_MORGUE_STEEL);
    mb.addBox(Vec3(0, 1.05f, 0), Vec3(1.20f, 1.05f, 0.42f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    for (int r = 0; r < 3; r++) {
        for (int c = 0; c < 3; c++) {
            float x = -0.78f + c * 0.78f;
            float y = 0.36f + r * 0.68f;
            mb.addBox(Vec3(x, y, -0.428f), Vec3(0.36f, 0.30f, 0.012f));
            mb.addBox(Vec3(x, y - 0.16f, -0.452f), Vec3(0.12f, 0.022f, 0.022f));
        }
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(1.22f, 1.05f, 0.46f);
    out.colliderOffset = Vec3(0, 1.05f, 0);
}

void buildServerRack(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_SERVER_RACK);
    mb.addBox(Vec3(0, 1.00f, 0), Vec3(0.31f, 1.00f, 0.50f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(-0.315f, 1.00f, 0), Vec3(0.012f, 1.00f, 0.50f));
    mb.addBox(Vec3(0.315f, 1.00f, 0), Vec3(0.012f, 1.00f, 0.50f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.34f, 1.00f, 0.52f);
    out.colliderOffset = Vec3(0, 1.00f, 0);
}

void buildVending(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0.90f, 0), Vec3(0.42f, 0.90f, 0.34f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_GLASS);
    mb.addBox(Vec3(-0.09f, 1.05f, -0.345f), Vec3(0.28f, 0.62f, 0.01f));
    mb.finishSubMesh();
    out.transparentSub = 1;
    out.hasTransparent = true;
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.43f, 0.90f, 0.36f);
    out.colliderOffset = Vec3(0, 0.90f, 0);
}

void buildCurtain(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.pushTransform(Mat4::rotateX(HALF_PI));
    mb.addCylinder(Vec3(0, -1.10f, 0), 0.014f, 2.20f, 8);
    mb.popTransform();
    mb.finishSubMesh();
    mb.setMaterial(MAT_CURTAIN);
    int folds = 14;
    for (int i = 0; i < folds; i++) {
        float z0 = -1.05f + (2.10f * i) / folds;
        float z1 = -1.05f + (2.10f * (i + 1)) / folds;
        float x0 = std::sin(i * 1.7f) * 0.035f;
        float x1 = std::sin((i + 1) * 1.7f) * 0.035f;
        mb.addQuad(Vec3(x0, -1.05f, z0), Vec3(x1, -1.05f, z1), Vec3(x1, 0.0f, z1), Vec3(x0, 0.0f, z0), Vec3(1, 0, 0));
        mb.addQuad(Vec3(x1, -1.05f, z1), Vec3(x0, -1.05f, z0), Vec3(x0, 0.0f, z0), Vec3(x1, 0.0f, z1), Vec3(-1, 0, 0));
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildWindow(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    frame(mb, Vec3(0, 0, 0), Vec3(0.72f, 0.95f, 0.06f), 0.055f);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.03f, 0.90f, 0.045f));
    mb.addBox(Vec3(0, 0, 0), Vec3(0.68f, 0.03f, 0.045f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_GLASS);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.68f, 0.90f, 0.006f));
    mb.finishSubMesh();
    out.transparentSub = 1;
    out.hasTransparent = true;
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildVentCover(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_VENT_GRATE);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.30f, 0.20f, 0.018f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    frame(mb, Vec3(0, 0, 0.006f), Vec3(0.33f, 0.23f, 0.014f), 0.025f);
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildExitSign(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.24f, 0.11f, 0.035f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.addBox(Vec3(0, 0, -0.038f), Vec3(0.21f, 0.085f, 0.008f));
    mb.addBox(Vec3(0, 0, 0.038f), Vec3(0.21f, 0.085f, 0.008f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildLightSwitch(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.045f, 0.062f, 0.014f));
    mb.addBox(Vec3(0, 0.005f, -0.016f), Vec3(0.028f, 0.036f, 0.008f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildKeypad(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.055f, 0.085f, 0.018f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_SERVER_RACK);
    mb.addBox(Vec3(0, 0.045f, -0.019f), Vec3(0.040f, 0.022f, 0.004f));
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 3; c++)
            mb.addBox(Vec3(-0.026f + c * 0.026f, 0.006f - r * 0.025f, -0.020f), Vec3(0.010f, 0.010f, 0.004f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildPaperPile(PropMesh& out) {
    MeshBuilder mb;
    Rng rng(4242);
    mb.setMaterial(MAT_PAPER);
    for (int i = 0; i < 9; i++) {
        mb.pushTransform(Mat4::translate(Vec3(rng.range(-0.05f, 0.05f), i * 0.004f, rng.range(-0.05f, 0.05f))) * Mat4::rotateY(rng.range(-0.5f, 0.5f)));
        mb.addBox(Vec3(0, 0.002f, 0), Vec3(0.105f, 0.002f, 0.148f));
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildBox(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PAPER);
    mb.addBox(Vec3(0, 0.17f, 0), Vec3(0.26f, 0.17f, 0.20f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.27f, 0.17f, 0.21f);
    out.colliderOffset = Vec3(0, 0.17f, 0);
}

void buildDebris(PropMesh& out) {
    MeshBuilder mb;
    Rng rng(777);
    mb.setMaterial(MAT_CONCRETE_FLOOR);
    for (int i = 0; i < 16; i++) {
        Vec3 p(rng.range(-0.55f, 0.55f), 0.0f, rng.range(-0.55f, 0.55f));
        float s = rng.range(0.035f, 0.11f);
        mb.pushTransform(Mat4::translate(p) * Mat4::rotateY(rng.range(0, TAU)));
        mb.addBox(Vec3(0, s * 0.5f, 0), Vec3(s, s * 0.35f, s * 0.7f));
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.setMaterial(MAT_CEILING_TILE);
    for (int i = 0; i < 4; i++) {
        Vec3 p(rng.range(-0.5f, 0.5f), 0.0f, rng.range(-0.5f, 0.5f));
        mb.pushTransform(Mat4::translate(p) * Mat4::rotateY(rng.range(0, TAU)));
        mb.addBox(Vec3(0, 0.012f, 0), Vec3(0.22f, 0.012f, 0.18f));
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildDeadPlant(PropMesh& out) {
    MeshBuilder mb;
    Rng rng(31337);
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addCone(Vec3(0, 0, 0), 0.14f, 0.18f, 0.30f, 14, true);
    mb.finishSubMesh();
    mb.setMaterial(MAT_WOOD_OLD);
    mb.addCylinder(Vec3(0, 0.28f, 0), 0.022f, 0.42f, 6);
    for (int i = 0; i < 7; i++) {
        mb.pushTransform(Mat4::translate(Vec3(0, 0.42f + rng.range(0.0f, 0.24f), 0)) * Mat4::rotateY(rng.range(0, TAU)) * Mat4::rotateZ(rng.range(0.5f, 1.2f)));
        mb.addCylinder(Vec3(0, 0, 0), 0.008f, rng.range(0.12f, 0.26f), 5);
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.18f, 0.20f, 0.18f);
    out.colliderOffset = Vec3(0, 0.20f, 0);
}

void buildTV(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.34f, 0.26f, 0.28f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_SERVER_RACK);
    mb.addBox(Vec3(0, 0.01f, -0.285f), Vec3(0.28f, 0.21f, 0.012f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, -0.10f, 0.32f), Vec3(0.10f, 0.03f, 0.10f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildClock(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.pushTransform(Mat4::rotateX(HALF_PI));
    mb.addCylinder(Vec3(0, -0.03f, 0), 0.16f, 0.05f, 20, true);
    mb.popTransform();
    mb.finishSubMesh();
    mb.setMaterial(MAT_SERVER_RACK);
    mb.addBox(Vec3(0, 0.04f, -0.032f), Vec3(0.008f, 0.05f, 0.004f));
    mb.addBox(Vec3(0.03f, 0, -0.032f), Vec3(0.04f, 0.006f, 0.004f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildNoticeBoard(PropMesh& out) {
    MeshBuilder mb;
    Rng rng(9001);
    mb.setMaterial(MAT_WOOD_OLD);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.60f, 0.42f, 0.025f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_PAPER);
    for (int i = 0; i < 8; i++) {
        mb.pushTransform(Mat4::translate(Vec3(rng.range(-0.44f, 0.44f), rng.range(-0.28f, 0.28f), -0.028f)) * Mat4::rotateZ(rng.range(-0.14f, 0.14f)));
        mb.addBox(Vec3(0, 0, 0), Vec3(0.075f, 0.105f, 0.002f));
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildStretcher(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_STEEL);
    mb.addBox(Vec3(0, 0.14f, 0), Vec3(0.32f, 0.02f, 0.94f));
    mb.addBox(Vec3(-0.33f, 0.14f, 0), Vec3(0.02f, 0.03f, 1.02f));
    mb.addBox(Vec3(0.33f, 0.14f, 0), Vec3(0.02f, 0.03f, 1.02f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_FABRIC);
    mb.addBox(Vec3(0, 0.17f, 0), Vec3(0.30f, 0.02f, 0.90f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.35f, 0.12f, 1.04f);
    out.colliderOffset = Vec3(0, 0.12f, 0);
}

void buildCorpse(PropMesh& out) {
    MeshBuilder mb;

    mb.setMaterial(MAT_SKIN);
    mb.addSphere(Vec3(0, 0.10f, -0.74f), 0.115f, 12, 10);
    mb.addBox(Vec3(-0.13f, 0.045f, 0.34f), Vec3(0.045f, 0.035f, 0.085f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_HAIR);
    mb.addSphere(Vec3(0, 0.145f, -0.78f), 0.10f, 12, 8);
    mb.finishSubMesh();

    mb.setMaterial(MAT_CLOTH_WHITE);
    mb.addBox(Vec3(0, 0.075f, -0.44f), Vec3(0.215f, 0.075f, 0.24f));
    mb.addBox(Vec3(0, 0.085f, -0.12f), Vec3(0.235f, 0.085f, 0.20f));
    mb.addBox(Vec3(0, 0.070f, 0.14f), Vec3(0.205f, 0.070f, 0.18f));
    mb.addBox(Vec3(-0.095f, 0.060f, 0.40f), Vec3(0.085f, 0.060f, 0.16f));
    mb.addBox(Vec3(0.095f, 0.060f, 0.40f), Vec3(0.085f, 0.060f, 0.16f));
    mb.addBox(Vec3(0.135f, 0.075f, -0.20f), Vec3(0.055f, 0.045f, 0.30f));
    mb.addBox(Vec3(-0.135f, 0.075f, -0.20f), Vec3(0.055f, 0.045f, 0.30f));
    mb.addBox(Vec3(0, 0.012f, -0.10f), Vec3(0.275f, 0.012f, 0.72f));
    mb.addBox(Vec3(-0.272f, 0.030f, -0.10f), Vec3(0.014f, 0.030f, 0.70f));
    mb.addBox(Vec3(0.272f, 0.030f, -0.10f), Vec3(0.014f, 0.030f, 0.70f));
    mb.addBox(Vec3(0, 0.030f, 0.60f), Vec3(0.245f, 0.030f, 0.020f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_PAPER);
    mb.addBox(Vec3(-0.13f, 0.012f, 0.435f), Vec3(0.030f, 0.004f, 0.042f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.colliderHalf = Vec3(0.28f, 0.10f, 0.78f);
    out.colliderOffset = Vec3(0, 0.09f, 0);
}

void buildSpeaker(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.addBox(Vec3(0, 0, 0), Vec3(0.13f, 0.13f, 0.05f));
    mb.finishSubMesh();
    mb.setMaterial(MAT_VENT_GRATE);
    mb.addBox(Vec3(0, 0, -0.052f), Vec3(0.11f, 0.11f, 0.006f));
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildKeyring(PropMesh& out) {
    MeshBuilder mb;

    mb.setMaterial(MAT_STEEL);
    mb.pushTransform(Mat4::rotateX(HALF_PI));
    mb.addTorusArc(Vec3(0, 0, 0), 0.030f, 0.0035f, 0.0f, TAU, 18, 6);
    mb.popTransform();

    for (int i = 0; i < 2; i++) {
        float a = i == 0 ? -0.34f : 0.42f;
        mb.pushTransform(Mat4::translate(Vec3(std::cos(a) * 0.030f, 0.0f, std::sin(a) * 0.030f)) *
                         Mat4::rotateY(-a) * Mat4::rotateZ(0.10f + i * 0.06f));
        mb.addBox(Vec3(0.034f, 0.0f, 0.0f), Vec3(0.034f, 0.0035f, 0.007f));
        mb.pushTransform(Mat4::rotateX(HALF_PI));
        mb.addTorusArc(Vec3(0.004f, 0.0f, 0.0f), 0.009f, 0.0028f, 0.0f, TAU, 10, 5);
        mb.popTransform();
        mb.addBox(Vec3(0.062f, 0.006f, 0.0f), Vec3(0.006f, 0.006f, 0.006f));
        mb.addBox(Vec3(0.050f, 0.007f, 0.0f), Vec3(0.005f, 0.005f, 0.006f));
        mb.popTransform();
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.pushTransform(Mat4::translate(Vec3(-0.052f, 0.0f, 0.014f)) * Mat4::rotateY(0.24f));
    mb.addBox(Vec3(0, 0, 0), Vec3(0.026f, 0.0022f, 0.016f));
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.addBox(Vec3(0.0f, 0.004f, 0.0f), Vec3(0.008f, 0.0015f, 0.008f));
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

void buildBattery(PropMesh& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_METAL_PAINTED);
    mb.pushTransform(Mat4::rotateZ(HALF_PI));
    mb.addCylinder(Vec3(0, -0.025f, 0), 0.014f, 0.050f, 10, true);
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_STEEL);
    mb.pushTransform(Mat4::translate(Vec3(0.026f, 0, 0)) * Mat4::rotateZ(HALF_PI));
    mb.addCylinder(Vec3(0, 0, 0), 0.006f, 0.004f, 8, true);
    mb.popTransform();
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.solid = false;
}

}

void PropLibrary::build() {
    Clock clock;
    buildBed(props[PROP_BED]);
    buildGurney(props[PROP_GURNEY]);
    buildCrib(props[PROP_CRIB]);
    buildWheelchair(props[PROP_WHEELCHAIR]);
    buildIVStand(props[PROP_IV_STAND]);
    buildMonitorCart(props[PROP_MONITOR_CART]);
    buildDefibrillator(props[PROP_DEFIBRILLATOR]);
    buildCabinet(props[PROP_CABINET]);
    buildFileCabinet(props[PROP_FILE_CABINET]);
    buildLocker(props[PROP_LOCKER]);
    buildShelf(props[PROP_SHELF]);
    buildDesk(props[PROP_DESK]);
    buildTable(props[PROP_TABLE]);
    buildChair(props[PROP_CHAIR]);
    buildStool(props[PROP_STOOL]);
    buildBench(props[PROP_BENCH]);
    buildTrolley(props[PROP_TROLLEY]);
    buildBin(props[PROP_BIN]);
    buildSink(props[PROP_SINK]);
    buildToilet(props[PROP_TOILET]);
    buildMirror(props[PROP_MIRROR]);
    buildRadiator(props[PROP_RADIATOR]);
    buildPipes(props[PROP_PIPES]);
    buildDuct(props[PROP_DUCT]);
    buildCeilingLamp(props[PROP_CEILING_LAMP]);
    buildWallLamp(props[PROP_WALL_LAMP]);
    buildORLamp(props[PROP_OR_LAMP]);
    buildORTable(props[PROP_OR_TABLE]);
    buildXrayMachine(props[PROP_XRAY_MACHINE]);
    buildMorgueWall(props[PROP_MORGUE_WALL]);
    buildServerRack(props[PROP_SERVER_RACK]);
    buildVending(props[PROP_VENDING]);
    buildCurtain(props[PROP_CURTAIN]);
    buildWindow(props[PROP_WINDOW]);
    buildVentCover(props[PROP_VENT_COVER]);
    buildExitSign(props[PROP_EXIT_SIGN]);
    buildLightSwitch(props[PROP_LIGHT_SWITCH]);
    buildKeypad(props[PROP_KEYPAD]);
    buildPaperPile(props[PROP_PAPER_PILE]);
    buildBox(props[PROP_BOX]);
    buildDebris(props[PROP_DEBRIS]);
    buildDeadPlant(props[PROP_DEAD_PLANT]);
    buildTV(props[PROP_TV]);
    buildClock(props[PROP_CLOCK]);
    buildNoticeBoard(props[PROP_NOTICE_BOARD]);
    buildStretcher(props[PROP_STRETCHER]);
    buildCorpse(props[PROP_CORPSE]);
    buildSpeaker(props[PROP_SPEAKER]);
    buildKeyring(props[PROP_KEYRING]);
    buildBattery(props[PROP_BATTERY]);
    LOG_INFO("Built %d procedural props in %.2fs", (int)PROP_COUNT, clock.elapsed());
}

void PropLibrary::destroy() {
    for (int i = 0; i < PROP_COUNT; i++) props[i].mesh.destroy();
}

}
