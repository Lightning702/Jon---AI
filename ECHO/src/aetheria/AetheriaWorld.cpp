#include "AetheriaWorld.h"
#include "../core/Log.h"
#include "../core/Time.h"

using namespace em;
using namespace echo;

namespace aeth {

namespace {

const char* kVillageNames[] = {
    "Ahrenfels", "Silberbach", "Morgentau", "Lindenhain", "Steinquell",
    "Nebelgrund", "Goldbruch", "Weidenau", "Hallenstein", "Rabenfurt"
};

const char* kGiverNames[] = {
    "Alwin Rothbart", "Mira Talwind", "Bosco Steinhand", "Elva Morgentau", "Hagen Ulf",
    "Selma Kranich", "Tobias Rauk", "Nara Silberblatt", "Gorm Eisfaust", "Liana Hain"
};

const char* kShrineNames[] = { "Schrein der Stille", "Schrein des Morgenlichts", "Schrein der Tiefe" };
const char* kRuinNames[] = { "Bogen von Ealdor", "Torhalle im Moos", "Bruch der Alten" };
const char* kCircleNames[] = { "Steinkreis Hall", "Ring der Wache", "Sieben Steine" };

const char* kHarvestNames[FLORA_COUNT] = {
    "Kiefernharz", "Laub", "Goldlaub", "Trockenholz", "Beerenranke", "Silberfarn",
    "Gras", "Sonnenbluete", "Stein", "Fels", "Leuchtpilz", "Klangkristall"
};

bool harvestable(int type) {
    return type == FLORA_MUSHROOM || type == FLORA_FLOWER || type == FLORA_CRYSTAL ||
           type == FLORA_FERN || type == FLORA_BUSH;
}

const em::Vec3 kSpeciesTint[5] = {
    em::Vec3(0.62f, 0.92f, 0.58f),
    em::Vec3(0.48f, 0.80f, 0.95f),
    em::Vec3(0.90f, 0.72f, 0.38f),
    em::Vec3(0.78f, 0.56f, 0.95f),
    em::Vec3(0.95f, 0.88f, 0.72f)
};

void buildConifer(FloraMesh& out, Rng& rng) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.62f, 0.46f, 0.34f, 1.0f));
    mb.addCone(Vec3(0, 0, 0), 0.22f, 0.10f, 7.4f, 7, false);
    mb.finishSubMesh();

    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(0.30f, 0.62f, 0.32f, 1.0f));
    for (int i = 0; i < 7; i++) {
        float t = (float)i / 6.0f;
        float y = 1.7f + t * 5.4f;
        float r = lerpf(1.95f, 0.30f, t) * rng.range(0.92f, 1.08f);
        mb.addCone(Vec3(0, y, 0), r, r * 0.18f, 1.5f, 9, true);
    }
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.30f;
}

void buildBroadleaf(FloraMesh& out, Rng& rng, const Vec3& leafTint) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.52f, 0.40f, 0.30f, 1.0f));
    mb.addCone(Vec3(0, 0, 0), 0.30f, 0.16f, 3.6f, 8, false);
    for (int i = 0; i < 4; i++) {
        float a = TAU * i / 4.0f + rng.range(-0.3f, 0.3f);
        mb.pushTransform(Mat4::translate(Vec3(0, 3.1f, 0)) * Mat4::rotateY(a) * Mat4::rotateZ(0.75f));
        mb.addCone(Vec3(0, 0, 0), 0.12f, 0.06f, 1.9f, 6, false);
        mb.popTransform();
    }
    mb.finishSubMesh();

    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(leafTint, 1.0f));
    for (int i = 0; i < 6; i++) {
        Vec3 c(rng.range(-1.5f, 1.5f), 4.4f + rng.range(-0.5f, 1.2f), rng.range(-1.5f, 1.5f));
        float r = rng.range(1.35f, 2.15f);
        mb.pushTransform(Mat4::translate(c) * Mat4::scale(Vec3(1.0f, 0.78f, 1.0f)));
        mb.addSphere(Vec3(0, 0, 0), r, 6, 9);
        mb.popTransform();
    }
    mb.finishSubMesh();

    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.34f;
}

void buildDeadTree(FloraMesh& out, Rng& rng) {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.38f, 0.32f, 0.28f, 1.0f));
    mb.addCone(Vec3(0, 0, 0), 0.26f, 0.10f, 4.6f, 7, false);
    for (int i = 0; i < 6; i++) {
        float a = TAU * i / 6.0f + rng.range(-0.4f, 0.4f);
        mb.pushTransform(Mat4::translate(Vec3(0, rng.range(2.4f, 4.2f), 0)) * Mat4::rotateY(a) * Mat4::rotateZ(rng.range(0.7f, 1.25f)));
        mb.addCone(Vec3(0, 0, 0), 0.09f, 0.02f, rng.range(1.2f, 2.4f), 5, false);
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.24f;
}

void buildBush(FloraMesh& out, Rng& rng, const Vec3& tint, float size) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(tint, 1.0f));
    for (int i = 0; i < 5; i++) {
        Vec3 c(rng.range(-0.35f, 0.35f), size * rng.range(0.35f, 0.65f), rng.range(-0.35f, 0.35f));
        mb.pushTransform(Mat4::translate(c) * Mat4::scale(Vec3(1.0f, 0.8f, 1.0f)));
        mb.addSphere(Vec3(0, 0, 0), size * rng.range(0.35f, 0.55f), 5, 7);
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.0f;
}

void buildGrassTuft(FloraMesh& out, Rng& rng) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(0.44f, 0.68f, 0.30f, 1.0f));
    for (int i = 0; i < 9; i++) {
        float a = rng.range(0.0f, TAU);
        float lean = rng.range(0.12f, 0.42f);
        float h = rng.range(0.32f, 0.62f);
        mb.pushTransform(Mat4::translate(Vec3(rng.range(-0.16f, 0.16f), 0, rng.range(-0.16f, 0.16f))) *
                         Mat4::rotateY(a) * Mat4::rotateZ(lean));
        mb.addCone(Vec3(0, 0, 0), 0.035f, 0.004f, h, 3, false);
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.0f;
    out.castShadow = false;
}

void buildFlower(FloraMesh& out, Rng& rng) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(0.36f, 0.60f, 0.28f, 1.0f));
    mb.addCone(Vec3(0, 0, 0), 0.016f, 0.010f, 0.34f, 4, false);
    mb.finishSubMesh();

    mb.setMaterial(MAT_PLASTIC_WHITE);
    Vec3 petal(rng.range(0.7f, 1.6f), rng.range(0.35f, 1.1f), rng.range(0.5f, 1.5f));
    mb.setColor(Vec4(petal, 1.0f));
    for (int i = 0; i < 5; i++) {
        float a = TAU * i / 5.0f;
        mb.pushTransform(Mat4::translate(Vec3(std::cos(a) * 0.055f, 0.35f, std::sin(a) * 0.055f)) * Mat4::scale(Vec3(1, 0.4f, 1)));
        mb.addSphere(Vec3(0, 0, 0), 0.05f, 4, 6);
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.0f;
    out.castShadow = false;
}

void buildRock(FloraMesh& out, Rng& rng, float size, float radius) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CONCRETE_WALL);
    mb.setColor(Vec4(0.60f, 0.60f, 0.58f, 1.0f));
    int lumps = size > 1.4f ? 5 : 3;
    for (int i = 0; i < lumps; i++) {
        Vec3 c(rng.range(-size * 0.35f, size * 0.35f), rng.range(0.0f, size * 0.30f), rng.range(-size * 0.35f, size * 0.35f));
        mb.pushTransform(Mat4::translate(c) * Mat4::rotateY(rng.range(0, TAU)) *
                         Mat4::scale(Vec3(rng.range(0.7f, 1.3f), rng.range(0.55f, 0.95f), rng.range(0.7f, 1.3f))));
        mb.addSphere(Vec3(0, 0, 0), size * rng.range(0.4f, 0.62f), 4, 6);
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = radius;
}

void buildMushroom(FloraMesh& out, Rng& rng) {
    MeshBuilder mb;
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.setColor(Vec4(0.82f, 0.78f, 0.70f, 1.0f));
    mb.addCone(Vec3(0, 0, 0), 0.09f, 0.07f, 0.55f, 7, false);
    mb.finishSubMesh();
    mb.setMaterial(MAT_PLASTIC_WHITE);
    mb.setColor(Vec4(rng.range(0.9f, 1.7f), rng.range(0.25f, 0.5f), rng.range(0.3f, 0.6f), 1.0f));
    mb.pushTransform(Mat4::translate(Vec3(0, 0.55f, 0)) * Mat4::scale(Vec3(1.0f, 0.55f, 1.0f)));
    mb.addSphere(Vec3(0, 0, 0), 0.34f, 5, 9);
    mb.popTransform();
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.0f;
}

void buildCrystal(FloraMesh& out, Rng& rng) {
    MeshBuilder mb;
    mb.setMaterial(MAT_GLASS);
    mb.setColor(Vec4(0.55f, 0.85f, 1.0f, 1.0f));
    for (int i = 0; i < 4; i++) {
        float a = TAU * i / 4.0f + rng.range(-0.4f, 0.4f);
        mb.pushTransform(Mat4::translate(Vec3(std::cos(a) * 0.22f, 0, std::sin(a) * 0.22f)) *
                         Mat4::rotateY(a) * Mat4::rotateZ(rng.range(-0.25f, 0.25f)));
        mb.addCone(Vec3(0, 0, 0), 0.16f, 0.02f, rng.range(0.9f, 1.9f), 5, true);
        mb.popTransform();
    }
    mb.finishSubMesh();
    mb.build(out.mesh);
    out.bounds = out.mesh.bounds();
    out.collisionRadius = 0.0f;
}

void buildCreature(Ref<Mesh>& out) {
    MeshBuilder mb;
    mb.setMaterial(MAT_CURTAIN);
    mb.setColor(Vec4(0.45f, 0.85f, 0.55f, 1.0f));
    mb.pushTransform(Mat4::scale(Vec3(1.0f, 0.78f, 1.0f)));
    mb.addSphere(Vec3(0, 0.34f, 0), 0.34f, 8, 12);
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_SERVER_RACK);
    mb.setColor(Vec4(1, 1, 1, 1));
    mb.addSphere(Vec3(-0.13f, 0.42f, -0.26f), 0.045f, 4, 6);
    mb.addSphere(Vec3(0.13f, 0.42f, -0.26f), 0.045f, 4, 6);
    mb.finishSubMesh();

    out = std::make_shared<Mesh>();
    mb.build(*out);
}

}

void DayNight::advance(float dt) {
    timeOfDay = fractf(timeOfDay + dt * daySpeed);

    float angle = (timeOfDay - 0.25f) * TAU;
    sunAltitude = std::sin(angle);
    sunDirection = normalize(Vec3(std::cos(angle) * 0.55f, -sunAltitude, 0.34f));

    float day = clampf(sunAltitude * 2.4f, 0.0f, 1.0f);
    float dusk = clampf(1.0f - std::fabs(sunAltitude) * 5.0f, 0.0f, 1.0f);
    float night = clampf(-sunAltitude * 2.6f, 0.0f, 1.0f);

    Vec3 dayColor(1.00f, 0.96f, 0.88f);
    Vec3 duskColor(1.00f, 0.55f, 0.28f);
    Vec3 nightColor(0.32f, 0.42f, 0.72f);
    sunColor = lerp(lerp(nightColor, duskColor, dusk), dayColor, day);

    skyZenith = lerp(Vec3(0.020f, 0.030f, 0.075f), Vec3(0.085f, 0.185f, 0.400f), day);
    skyZenith = lerp(skyZenith, Vec3(0.130f, 0.080f, 0.150f), dusk * 0.55f);
    skyHorizon = lerp(Vec3(0.045f, 0.055f, 0.100f), Vec3(0.560f, 0.660f, 0.780f), day);
    skyHorizon = lerp(skyHorizon, Vec3(0.920f, 0.470f, 0.230f), dusk * 0.75f);
    ground = lerp(Vec3(0.020f, 0.022f, 0.026f), Vec3(0.090f, 0.095f, 0.085f), day);

    starAmount = night;
    ambientScale = lerpf(0.30f, 1.0f, day);
}

void AetheriaWorld::buildFloraMeshes() {
    Rng rng(worldSeed ^ 0xF10A5EEDULL);
    buildConifer(flora[FLORA_PINE], rng);
    buildBroadleaf(flora[FLORA_BROADLEAF], rng, Vec3(0.34f, 0.58f, 0.28f));
    buildBroadleaf(flora[FLORA_GOLDEN_TREE], rng, Vec3(1.05f, 0.66f, 0.20f));
    buildDeadTree(flora[FLORA_DEAD_TREE], rng);
    buildBush(flora[FLORA_BUSH], rng, Vec3(0.32f, 0.54f, 0.26f), 1.30f);
    buildBush(flora[FLORA_FERN], rng, Vec3(0.28f, 0.62f, 0.34f), 0.85f);
    buildGrassTuft(flora[FLORA_GRASS], rng);
    buildFlower(flora[FLORA_FLOWER], rng);
    buildRock(flora[FLORA_ROCK], rng, 0.85f, 0.0f);
    buildRock(flora[FLORA_BOULDER], rng, 2.6f, 0.85f);
    buildMushroom(flora[FLORA_MUSHROOM], rng);
    buildCrystal(flora[FLORA_CRYSTAL], rng);
    buildCreature(creatureMesh);
}

void AetheriaWorld::scatterFlora(Rng& rng) {
    float size = land.worldSize();
    gridCell = 32.0f;
    gridDim = std::max(1, (int)std::ceil(size / gridCell));
    floraGrid.assign((size_t)gridDim * gridDim, {});
    instances.clear();
    instances.reserve(90000);

    const int samples = 260000;
    for (int i = 0; i < samples; i++) {
        float x = rng.range(1.0f, size - 1.0f);
        float z = rng.range(1.0f, size - 1.0f);
        float h = land.heightAt(x, z);
        if (h < land.waterLevel() + 0.25f) continue;

        float slope = land.slopeAt(x, z);
        int biome = land.biomeAt(x, z);
        float roll = rng.nextFloat();

        int type = -1;
        float scale = 1.0f;

        switch (biome) {
        case BIOME_FOREST:
            if (slope > 0.55f) { if (roll < 0.30f) type = FLORA_ROCK; }
            else if (roll < 0.22f) type = FLORA_PINE;
            else if (roll < 0.34f) type = FLORA_BROADLEAF;
            else if (roll < 0.48f) type = FLORA_FERN;
            else if (roll < 0.58f) type = FLORA_BUSH;
            else if (roll < 0.64f) type = FLORA_MUSHROOM;
            else type = FLORA_GRASS;
            break;
        case BIOME_GOLDEN_WOOD:
            if (slope > 0.55f) { if (roll < 0.25f) type = FLORA_ROCK; }
            else if (roll < 0.26f) type = FLORA_GOLDEN_TREE;
            else if (roll < 0.34f) type = FLORA_BROADLEAF;
            else if (roll < 0.48f) type = FLORA_BUSH;
            else if (roll < 0.58f) type = FLORA_FLOWER;
            else type = FLORA_GRASS;
            break;
        case BIOME_MEADOW:
            if (slope > 0.62f) { if (roll < 0.20f) type = FLORA_ROCK; }
            else if (roll < 0.05f) type = FLORA_BROADLEAF;
            else if (roll < 0.12f) type = FLORA_BUSH;
            else if (roll < 0.30f) type = FLORA_FLOWER;
            else type = FLORA_GRASS;
            break;
        case BIOME_HIGHLAND:
            if (roll < 0.16f) type = FLORA_ROCK;
            else if (roll < 0.21f) type = FLORA_BOULDER;
            else if (roll < 0.27f) type = FLORA_PINE;
            else if (roll < 0.36f) type = FLORA_DEAD_TREE;
            else if (roll < 0.72f) type = FLORA_GRASS;
            break;
        case BIOME_SNOW:
            if (roll < 0.10f) type = FLORA_ROCK;
            else if (roll < 0.14f) type = FLORA_BOULDER;
            else if (roll < 0.19f) type = FLORA_PINE;
            else if (roll < 0.23f) type = FLORA_CRYSTAL;
            break;
        case BIOME_MARSH:
            if (roll < 0.14f) type = FLORA_DEAD_TREE;
            else if (roll < 0.28f) type = FLORA_FERN;
            else if (roll < 0.38f) type = FLORA_MUSHROOM;
            else type = FLORA_GRASS;
            break;
        default:
            if (roll < 0.08f) type = FLORA_ROCK;
            else if (roll < 0.14f) type = FLORA_BUSH;
            else if (roll < 0.40f) type = FLORA_GRASS;
            break;
        }

        if (type < 0) continue;
        if (slope > 0.72f && type != FLORA_ROCK) continue;

        switch (type) {
        case FLORA_PINE: scale = rng.range(0.72f, 1.45f); break;
        case FLORA_BROADLEAF:
        case FLORA_GOLDEN_TREE: scale = rng.range(0.78f, 1.35f); break;
        case FLORA_DEAD_TREE: scale = rng.range(0.70f, 1.25f); break;
        case FLORA_GRASS: scale = rng.range(0.75f, 1.55f); break;
        case FLORA_BOULDER: scale = rng.range(0.70f, 1.60f); break;
        default: scale = rng.range(0.80f, 1.30f); break;
        }

        FloraInstance inst;
        inst.type = (u16)type;
        inst.x = x;
        inst.z = z;
        inst.y = h;
        inst.yaw = rng.range(0.0f, TAU);
        inst.scale = scale;
        inst.tint = rng.range(0.82f, 1.18f);

        int gx = clampi((int)(x / gridCell), 0, gridDim - 1);
        int gz = clampi((int)(z / gridCell), 0, gridDim - 1);
        floraGrid[(size_t)(gz * gridDim + gx)].push_back((int)instances.size());
        instances.push_back(inst);
    }

    LOG_INFO("Aetheria flora: %d instances across %d cells", (int)instances.size(), gridDim * gridDim);
}

void AetheriaWorld::buildWater() {
    MeshBuilder mb;
    mb.setMaterial(MAT_GLASS);
    mb.setColor(Vec4(0.28f, 0.52f, 0.62f, 1.0f));
    float s = land.worldSize();
    mb.addPlane(Vec3(s * 0.5f, land.waterLevel(), s * 0.5f), Vec2(s * 1.6f, s * 1.6f), Vec3(0, 1, 0), 24);
    mb.finishSubMesh();
    waterMesh = std::make_shared<Mesh>();
    mb.build(*waterMesh);
}

void AetheriaWorld::addBuilding(int type, const Vec3& pos, float yaw, float scale, float tint) {
    BuildingInstance b;
    b.type = (u16)type;
    b.position = pos;
    b.yaw = yaw;
    b.scale = scale;
    b.tint = tint;
    structures.push_back(b);

    const BuildingMesh& bm = buildLib.get(type);
    if (bm.blockHalf.x > 0.01f && bm.blockHalf.y > 0.01f) {
        BoxCollider box;
        box.center = Vec2(pos.x, pos.z);
        box.half = bm.blockHalf * scale;
        box.sinYaw = std::sin(yaw);
        box.cosYaw = std::cos(yaw);
        boxes.push_back(box);
    }
    clearFloraAround(Vec2(pos.x, pos.z), std::max(bm.blockHalf.x, bm.blockHalf.y) * scale + 2.6f, 0.0f);
}

void AetheriaWorld::clearFloraAround(const Vec2& center, float radius, float minCollision) {
    if (gridDim <= 0) return;
    int span = (int)(radius / gridCell) + 1;
    int gx = clampi((int)(center.x / gridCell), 0, gridDim - 1);
    int gz = clampi((int)(center.y / gridCell), 0, gridDim - 1);
    float r2 = radius * radius;

    for (int dz = -span; dz <= span; dz++) {
        for (int dx = -span; dx <= span; dx++) {
            int cx = gx + dx, cz = gz + dz;
            if (cx < 0 || cz < 0 || cx >= gridDim || cz >= gridDim) continue;
            for (int idx : floraGrid[(size_t)(cz * gridDim + cx)]) {
                FloraInstance& f = instances[(size_t)idx];
                if (f.harvested) continue;
                if (flora[f.type].collisionRadius < minCollision) continue;
                float ddx = f.x - center.x;
                float ddz = f.z - center.y;
                if (ddx * ddx + ddz * ddz <= r2) f.harvested = true;
            }
        }
    }
}

void AetheriaWorld::placeSettlements(Rng& rng) {
    villages.clear();
    villagers.clear();
    villagerRig.build();

    int wanted = 7;
    int nameCount = (int)(sizeof(kVillageNames) / sizeof(kVillageNames[0]));

    auto dryArea = [&](const Vec3& c, float radius, float clearance) {
        for (int i = 0; i < 16; i++) {
            float a = TAU * i / 16.0f;
            for (int step = 1; step <= 3; step++) {
                float r = radius * step / 3.0f;
                float x = c.x + std::cos(a) * r;
                float z = c.z + std::sin(a) * r;
                if (!land.inBounds(x, z)) return false;
                if (land.heightAt(x, z) < land.waterLevel() + clearance) return false;
                if (land.slopeAt(x, z) > 0.62f) return false;
            }
        }
        return true;
    };

    for (int attempt = 0; attempt < 420 && (int)villages.size() < wanted; attempt++) {
        int wish = attempt % 3 == 0 ? BIOME_GOLDEN_WOOD : (attempt % 3 == 1 ? BIOME_MEADOW : BIOME_FOREST);
        Vec3 site = land.findSpawn(rng, wish);
        site = land.findFlatGround(Vec2(site.x, site.z), 24.0f, rng);
        if (!land.inBounds(site.x, site.z)) continue;
        if (land.heightAt(site.x, site.z) < land.waterLevel() + 2.4f) continue;
        if (!dryArea(site, 30.0f, 1.4f)) continue;

        bool tooClose = false;
        for (const auto& v : villages) {
            if (distance(Vec2(v.center.x, v.center.z), Vec2(site.x, site.z)) < 96.0f) tooClose = true;
        }
        if (tooClose) continue;

        int index = (int)villages.size();
        Settlement s;
        s.center = site;
        s.center.y = land.heightAt(site.x, site.z);
        s.radius = rng.range(19.0f, 26.0f);
        s.name = kVillageNames[index % nameCount];
        s.biome = land.biomeAt(site.x, site.z);
        s.giverName = kGiverNames[index % nameCount];

        clearFloraAround(Vec2(s.center.x, s.center.z), s.radius + 5.0f, 0.05f);

        auto ground = [&](float x, float z) { return Vec3(x, land.heightAt(x, z), z); };
        auto facing = [&](const Vec3& p) {
            Vec2 d(s.center.x - p.x, s.center.z - p.z);
            if (lengthSq(d) < 1e-4f) return 0.0f;
            d = normalize(d);
            return std::atan2(d.x, d.y);
        };

        addBuilding(BUILD_WELL, ground(s.center.x, s.center.z), rng.range(0.0f, TAU), 1.0f, 1.0f);

        int houses = rng.rangeInt(5, 9);
        float baseAngle = rng.range(0.0f, TAU);
        for (int i = 0; i < houses; i++) {
            float a = baseAngle + TAU * i / houses + rng.range(-0.16f, 0.16f);
            float dist = rng.range(9.5f, s.radius * 0.86f);
            Vec3 p = ground(s.center.x + std::cos(a) * dist, s.center.z + std::sin(a) * dist);
            int type = (i == 0) ? BUILD_LONGHOUSE : BUILD_COTTAGE;
            addBuilding(type, p, facing(p), rng.range(0.94f, 1.12f), rng.range(0.88f, 1.10f));
        }

        for (int i = 0; i < 2; i++) {
            float a = baseAngle + rng.range(0.0f, TAU);
            float dist = rng.range(4.6f, 7.4f);
            Vec3 p = ground(s.center.x + std::cos(a) * dist, s.center.z + std::sin(a) * dist);
            addBuilding(BUILD_STALL, p, facing(p) + PI, 1.0f, 1.0f);
        }

        {
            float a = baseAngle + 2.1f;
            Vec3 p = ground(s.center.x + std::cos(a) * 6.2f, s.center.z + std::sin(a) * 6.2f);
            addBuilding(BUILD_CAMPFIRE, p, 0.0f, 1.0f, 1.0f);
        }
        {
            float a = baseAngle - 1.2f;
            Vec3 p = ground(s.center.x + std::cos(a) * 3.6f, s.center.z + std::sin(a) * 3.6f);
            addBuilding(BUILD_BANNER, p, rng.range(0.0f, TAU), 1.0f, 1.0f);
        }

        if (index % 2 == 0) {
            float a = baseAngle + 3.7f;
            Vec3 p = ground(s.center.x + std::cos(a) * (s.radius * 0.94f), s.center.z + std::sin(a) * (s.radius * 0.94f));
            addBuilding(BUILD_TOWER, p, rng.range(0.0f, TAU), 1.0f, 1.0f);
        }

        int posts = 4;
        for (int i = 0; i < posts; i++) {
            float a = baseAngle + TAU * i / posts + 0.4f;
            float dist = s.radius + 5.5f;
            Vec3 p = ground(s.center.x + std::cos(a) * dist, s.center.z + std::sin(a) * dist);
            addBuilding(BUILD_SIGNPOST, p, facing(p), 1.0f, 1.0f);
        }

        int fences = rng.rangeInt(6, 11);
        for (int i = 0; i < fences; i++) {
            float a = baseAngle + TAU * i / fences + rng.range(-0.08f, 0.08f);
            float dist = s.radius * rng.range(0.94f, 1.02f);
            Vec3 p = ground(s.center.x + std::cos(a) * dist, s.center.z + std::sin(a) * dist);
            addBuilding(BUILD_FENCE, p, a + HALF_PI, 1.0f, 1.0f);
        }

        s.giverPos = ground(s.center.x + 2.4f, s.center.z + 2.4f);
        s.giverYaw = facing(s.giverPos);

        HumanInstance giver;
        giver.configure(HUMAN_DOCTOR, hashCombine(worldSeed, (u64)(index * 104729 + 17)));
        giver.position = s.giverPos;
        giver.yaw = s.giverYaw;
        giver.setPose(POSE_IDLE, 0.01f);
        giver.snapPose();
        giver.visibility = 1.0f;
        villagers.push_back(giver);

        int count = rng.rangeInt(4, 9);
        for (int i = 0; i < count; i++) {
            HumanInstance h;
            h.configure(rng.rangeInt(0, HUMAN_TYPE_COUNT), hashCombine(worldSeed, (u64)(index * 7919 + i * 131)));
            Vec2 off = rng.unitDisk() * s.radius * 0.72f;
            Vec3 p = ground(s.center.x + off.x, s.center.z + off.y);
            h.position = p;
            h.yaw = rng.range(0.0f, TAU);
            h.setPose(rng.chance(0.45f) ? POSE_IDLE : POSE_STAND_STILL, 0.01f);
            h.snapPose();
            h.visibility = 1.0f;
            villagers.push_back(h);
        }

        villages.push_back(s);
    }

    LOG_INFO("Aetheria settlements: %d villages, %d inhabitants, %d structures",
             (int)villages.size(), (int)villagers.size(), (int)structures.size());
}

void AetheriaWorld::placeLandmarks(Rng& rng) {
    marks.clear();
    int wanted = 10;

    auto dryArea = [&](const Vec3& c, float radius) {
        for (int i = 0; i < 10; i++) {
            float a = TAU * i / 10.0f;
            float x = c.x + std::cos(a) * radius;
            float z = c.z + std::sin(a) * radius;
            if (!land.inBounds(x, z)) return false;
            if (land.heightAt(x, z) < land.waterLevel() + 1.2f) return false;
        }
        return true;
    };

    for (int attempt = 0; attempt < 520 && (int)marks.size() < wanted; attempt++) {
        Vec3 site = land.findSpawn(rng, -1);
        site = land.findFlatGround(Vec2(site.x, site.z), 14.0f, rng);
        if (!land.inBounds(site.x, site.z)) continue;
        if (land.heightAt(site.x, site.z) < land.waterLevel() + 2.0f) continue;
        if (!dryArea(site, 11.0f)) continue;

        bool tooClose = false;
        for (const auto& v : villages) {
            if (distance(Vec2(v.center.x, v.center.z), Vec2(site.x, site.z)) < 52.0f) tooClose = true;
        }
        for (const auto& m : marks) {
            if (distance(Vec2(m.position.x, m.position.z), Vec2(site.x, site.z)) < 55.0f) tooClose = true;
        }
        if (tooClose) continue;

        int index = (int)marks.size();
        int kind = index % 3;
        Landmark lm;
        lm.position = Vec3(site.x, land.heightAt(site.x, site.z), site.z);
        lm.kind = kind;

        clearFloraAround(Vec2(lm.position.x, lm.position.z), 13.0f, 0.05f);

        if (kind == 0) {
            lm.name = kShrineNames[(index / 3) % 3];
            addBuilding(BUILD_SHRINE, lm.position, rng.range(0.0f, TAU), 1.0f, 1.0f);
            for (int i = 0; i < 4; i++) {
                float a = TAU * i / 4.0f + 0.6f;
                Vec3 p(lm.position.x + std::cos(a) * 6.0f, 0, lm.position.z + std::sin(a) * 6.0f);
                p.y = land.heightAt(p.x, p.z);
                addBuilding(BUILD_STANDING_STONE, p, a, 0.7f, 1.0f);
            }
        } else if (kind == 1) {
            lm.name = kRuinNames[(index / 3) % 3];
            addBuilding(BUILD_RUIN_ARCH, lm.position, rng.range(0.0f, TAU), 1.0f, 1.0f);
            for (int i = 0; i < 3; i++) {
                float a = rng.range(0.0f, TAU);
                float d = rng.range(5.0f, 9.5f);
                Vec3 p(lm.position.x + std::cos(a) * d, 0, lm.position.z + std::sin(a) * d);
                p.y = land.heightAt(p.x, p.z);
                addBuilding(BUILD_STANDING_STONE, p, rng.range(0.0f, TAU), rng.range(0.7f, 1.0f), 1.0f);
            }
        } else {
            lm.name = kCircleNames[(index / 3) % 3];
            int stones = 7;
            for (int i = 0; i < stones; i++) {
                float a = TAU * i / stones;
                Vec3 p(lm.position.x + std::cos(a) * 7.0f, 0, lm.position.z + std::sin(a) * 7.0f);
                p.y = land.heightAt(p.x, p.z);
                addBuilding(BUILD_STANDING_STONE, p, a + HALF_PI, 1.0f, 1.0f);
            }
            addBuilding(BUILD_CAMPFIRE, lm.position, 0.0f, 1.2f, 1.0f);
        }

        marks.push_back(lm);
    }

    LOG_INFO("Aetheria landmarks: %d", (int)marks.size());
}

void AetheriaWorld::respawnAgent(WildlifeAgent& a) {
    Vec3 p = land.findSpawn(worldRng, -1);
    a.position = p;
    a.yaw = worldRng.range(0.0f, TAU);
    a.phase = worldRng.range(0.0f, TAU);
    a.timer = worldRng.range(0.0f, 5.0f);
    a.state = 0;
    a.health = 26.0f + a.species * 9.0f;
    a.hitFlash = 0.0f;
    a.respawn = 0.0f;
    a.alive = true;
}

void AetheriaWorld::spawnWildlife(Rng& rng) {
    wildlife.clear();
    for (int i = 0; i < 260; i++) {
        Vec3 p = land.findSpawn(rng, -1);
        WildlifeAgent a;
        a.species = rng.rangeInt(0, 4);
        a.position = p;
        a.yaw = rng.range(0.0f, TAU);
        a.phase = rng.range(0.0f, TAU);
        a.timer = rng.range(0.0f, 6.0f);
        a.scale = rng.range(0.78f, 1.30f);
        a.health = 26.0f + a.species * 9.0f;
        wildlife.push_back(a);
    }
}

void AetheriaWorld::generate(u64 seed) {
    Clock clock;
    worldSeed = seed;
    worldRng.setSeed(seed ^ 0xA57E21ULL);
    Rng rng(seed);

    TerrainConfig tc;
    tc.seed = seed;
    land.generate(tc);

    buildFloraMeshes();
    buildLib.build();
    structures.clear();
    boxes.clear();
    scatterFlora(rng);
    buildWater();
    placeSettlements(rng);
    placeLandmarks(rng);
    spawnWildlife(rng);

    if (villages.empty()) {
        spawn = land.findSpawn(rng, BIOME_MEADOW);
    } else {
        const Settlement& home = villages[0];
        spawn = home.center;
        for (int i = 0; i < 48; i++) {
            float a = TAU * (i % 24) / 24.0f;
            float r = 5.5f + (i / 24) * 2.5f;
            Vec3 p(home.center.x + std::cos(a) * r, 0, home.center.z + std::sin(a) * r);
            p.y = land.heightAt(p.x, p.z);
            if (p.y <= land.waterLevel() + 1.0f || blocked(p, 0.7f)) continue;
            bool crowded = false;
            for (const auto& h : villagers) {
                if (distanceSq(h.position, p) < 9.0f) crowded = true;
            }
            if (crowded) continue;
            spawn = p;
            break;
        }
    }
    spawn.y = land.heightAt(spawn.x, spawn.z);

    sky.timeOfDay = 0.40f;
    sky.advance(0.0f);

    LOG_INFO("AETHERIA generated in %.2fs", clock.elapsed());
}

void AetheriaWorld::destroy() {
    for (int i = 0; i < FLORA_COUNT; i++) flora[i].mesh.destroy();
    instances.clear();
    floraGrid.clear();
    wildlife.clear();
    villages.clear();
    marks.clear();
    structures.clear();
    boxes.clear();
    buildLib.destroy();
    villagers.clear();
    villagerRig.destroy();
    waterMesh.reset();
    creatureMesh.reset();
    land.destroy();
}

int AetheriaWorld::villageAt(const Vec3& p, float extra) const {
    for (int i = 0; i < (int)villages.size(); i++) {
        const Settlement& v = villages[(size_t)i];
        if (distance(Vec2(v.center.x, v.center.z), Vec2(p.x, p.z)) < v.radius + extra) return i;
    }
    return -1;
}

int AetheriaWorld::landmarkAt(const Vec3& p, float extra) const {
    for (int i = 0; i < (int)marks.size(); i++) {
        const Landmark& m = marks[(size_t)i];
        if (distance(Vec2(m.position.x, m.position.z), Vec2(p.x, p.z)) < 14.0f + extra) return i;
    }
    return -1;
}

int AetheriaWorld::harvestableNear(const Vec3& p, float radius) const {
    if (gridDim <= 0) return -1;
    int gx = clampi((int)(p.x / gridCell), 0, gridDim - 1);
    int gz = clampi((int)(p.z / gridCell), 0, gridDim - 1);
    int best = -1;
    float bestD = radius * radius;

    for (int dz = -1; dz <= 1; dz++) {
        for (int dx = -1; dx <= 1; dx++) {
            int cx = gx + dx, cz = gz + dz;
            if (cx < 0 || cz < 0 || cx >= gridDim || cz >= gridDim) continue;
            for (int idx : floraGrid[(size_t)(cz * gridDim + cx)]) {
                const FloraInstance& f = instances[(size_t)idx];
                if (f.harvested || !harvestable(f.type)) continue;
                float ddx = f.x - p.x;
                float ddz = f.z - p.z;
                float d2 = ddx * ddx + ddz * ddz;
                if (d2 < bestD) { bestD = d2; best = idx; }
            }
        }
    }
    return best;
}

int AetheriaWorld::nearestOfType(const Vec3& p, int floraType, float maxDistance) const {
    if (gridDim <= 0 || floraType < 0 || floraType >= FLORA_COUNT) return -1;
    int gx = clampi((int)(p.x / gridCell), 0, gridDim - 1);
    int gz = clampi((int)(p.z / gridCell), 0, gridDim - 1);
    int span = clampi((int)(maxDistance / gridCell) + 1, 1, gridDim);

    int best = -1;
    float bestD = maxDistance * maxDistance;

    for (int ring = 0; ring <= span; ring++) {
        bool any = false;
        for (int dz = -ring; dz <= ring; dz++) {
            for (int dx = -ring; dx <= ring; dx++) {
                if (std::max(std::abs(dx), std::abs(dz)) != ring) continue;
                int cx = gx + dx, cz = gz + dz;
                if (cx < 0 || cz < 0 || cx >= gridDim || cz >= gridDim) continue;
                any = true;
                for (int idx : floraGrid[(size_t)(cz * gridDim + cx)]) {
                    const FloraInstance& f = instances[(size_t)idx];
                    if (f.harvested || f.type != (u16)floraType) continue;
                    float ddx = f.x - p.x;
                    float ddz = f.z - p.z;
                    float d2 = ddx * ddx + ddz * ddz;
                    if (d2 < bestD) { bestD = d2; best = idx; }
                }
            }
        }
        if (best >= 0 && (float)ring * gridCell > std::sqrt(bestD)) break;
        if (!any && ring > 0) break;
    }
    return best;
}

int AetheriaWorld::floraTypeOf(int index) const {
    if (index < 0 || index >= (int)instances.size()) return -1;
    return instances[(size_t)index].type;
}

const char* AetheriaWorld::harvestName(int floraType) const {
    if (floraType < 0 || floraType >= FLORA_COUNT) return "Pflanze";
    return kHarvestNames[floraType];
}

Vec3 AetheriaWorld::floraPosition(int index) const {
    if (index < 0 || index >= (int)instances.size()) return Vec3(0, 0, 0);
    const FloraInstance& f = instances[(size_t)index];
    return Vec3(f.x, f.y, f.z);
}

void AetheriaWorld::harvest(int index) {
    if (index < 0 || index >= (int)instances.size()) return;
    instances[(size_t)index].harvested = true;
}

float AetheriaWorld::consumeDamage() {
    float d = pendingDamage;
    pendingDamage = 0.0f;
    return d;
}

StrikeResult AetheriaWorld::strike(const Vec3& origin, const Vec3& forward, float range, float damage) {
    StrikeResult result;
    float best = range * range;
    int bestIndex = -1;

    for (int i = 0; i < (int)wildlife.size(); i++) {
        WildlifeAgent& a = wildlife[(size_t)i];
        if (!a.alive) continue;
        Vec3 to = a.position + Vec3(0, 0.35f, 0) - origin;
        float d2 = lengthSq(to);
        if (d2 > best) continue;
        if (d2 > 0.04f && dot(normalize(to), forward) < 0.55f) continue;
        best = d2;
        bestIndex = i;
    }

    if (bestIndex < 0) return result;

    WildlifeAgent& a = wildlife[(size_t)bestIndex];
    a.health -= damage;
    a.hitFlash = 0.35f;
    a.state = 2;
    a.timer = 3.5f;
    Vec3 away = a.position - origin;
    away.y = 0.0f;
    if (lengthSq(away) > 1e-4f) a.yaw = std::atan2(away.x, -away.z);

    result.hit = true;
    result.species = a.species;
    result.point = a.position + Vec3(0, 0.35f, 0);
    if (a.health <= 0.0f) {
        a.alive = false;
        a.respawn = 55.0f;
        result.killed = true;
    }
    return result;
}

bool AetheriaWorld::blocked(const Vec3& p, float radius) const {
    for (const BoxCollider& b : boxes) {
        Vec2 d(p.x - b.center.x, p.z - b.center.y);
        Vec2 local(d.x * b.cosYaw + d.y * b.sinYaw, -d.x * b.sinYaw + d.y * b.cosYaw);
        if (std::fabs(local.x) < b.half.x + radius && std::fabs(local.y) < b.half.y + radius) return true;
    }
    if (gridDim <= 0) return false;
    int gx = clampi((int)(p.x / gridCell), 0, gridDim - 1);
    int gz = clampi((int)(p.z / gridCell), 0, gridDim - 1);

    for (int dz = -1; dz <= 1; dz++) {
        for (int dx = -1; dx <= 1; dx++) {
            int cx = gx + dx, cz = gz + dz;
            if (cx < 0 || cz < 0 || cx >= gridDim || cz >= gridDim) continue;
            for (int idx : floraGrid[(size_t)(cz * gridDim + cx)]) {
                const FloraInstance& f = instances[(size_t)idx];
                if (f.harvested) continue;
                float r = flora[f.type].collisionRadius * f.scale;
                if (r <= 0.01f) continue;
                float dxp = p.x - f.x;
                float dzp = p.z - f.z;
                float rr = r + radius;
                if (dxp * dxp + dzp * dzp < rr * rr) return true;
            }
        }
    }
    return false;
}

Vec3 AetheriaWorld::resolveMovement(const Vec3& from, const Vec3& to, float radius) const {
    Vec3 result = to;
    if (!land.inBounds(result.x, result.z)) {
        result.x = clampf(result.x, 3.0f, land.worldSize() - 3.0f);
        result.z = clampf(result.z, 3.0f, land.worldSize() - 3.0f);
    }
    if (!boxes.empty()) {
        Vec2 flat = resolveBoxes(boxes, Vec2(result.x, result.z), radius);
        result.x = flat.x;
        result.z = flat.y;
    }

    if (gridDim <= 0) return result;

    for (int pass = 0; pass < 3; pass++) {
        bool moved = false;
        int gx = clampi((int)(result.x / gridCell), 0, gridDim - 1);
        int gz = clampi((int)(result.z / gridCell), 0, gridDim - 1);

        for (int dz = -1; dz <= 1 && !moved; dz++) {
            for (int dx = -1; dx <= 1 && !moved; dx++) {
                int cx = gx + dx, cz = gz + dz;
                if (cx < 0 || cz < 0 || cx >= gridDim || cz >= gridDim) continue;
                for (int idx : floraGrid[(size_t)(cz * gridDim + cx)]) {
                    const FloraInstance& f = instances[(size_t)idx];
                    if (f.harvested) continue;
                    float r = flora[f.type].collisionRadius * f.scale;
                    if (r <= 0.01f) continue;
                    float dxp = result.x - f.x;
                    float dzp = result.z - f.z;
                    float rr = r + radius;
                    float d2 = dxp * dxp + dzp * dzp;
                    if (d2 >= rr * rr) continue;

                    float d = std::sqrt(std::max(d2, 1e-6f));
                    float push = rr - d;
                    if (d < 1e-4f) {
                        result.x += rr;
                    } else {
                        result.x += (dxp / d) * push;
                        result.z += (dzp / d) * push;
                    }
                    moved = true;
                    break;
                }
            }
        }
        if (!moved) break;
    }
    return result;
}

std::string AetheriaWorld::regionName(const Vec3& p) const {
    for (const auto& v : villages) {
        if (distance(Vec2(v.center.x, v.center.z), Vec2(p.x, p.z)) < v.radius * 1.6f) return v.name;
    }
    for (const auto& m : marks) {
        if (distance(Vec2(m.position.x, m.position.z), Vec2(p.x, p.z)) < 22.0f) return m.name;
    }
    return biomeName(land.biomeAt(p.x, p.z));
}

void AetheriaWorld::updateWildlife(float dt, float time, const Vec3& viewPos) {
    for (auto& a : wildlife) {
        if (!a.alive) {
            a.respawn -= dt;
            if (a.respawn <= 0.0f) respawnAgent(a);
            continue;
        }

        if (a.hitFlash > 0.0f) a.hitFlash -= dt;
        if (a.attackCooldown > 0.0f) a.attackCooldown -= dt;

        float dist = distance(a.position, viewPos);
        if (dist > 140.0f) continue;

        bool aggressive = a.species == 2;

        a.timer -= dt;
        if (a.timer <= 0.0f) {
            a.timer = 2.5f + hash11(a.phase + time * 0.1f) * 5.0f;
            a.state = a.state == 0 ? 1 : 0;
            a.yaw += (hash11(a.phase * 3.1f + time) - 0.5f) * 2.4f;
        }

        if (aggressive && dist < 17.0f) {
            a.state = 3;
            a.timer = 1.5f;
            Vec3 to = viewPos - a.position;
            to.y = 0.0f;
            if (lengthSq(to) > 1e-4f) a.yaw = std::atan2(to.x, -to.z);
            if (dist < 1.85f && a.attackCooldown <= 0.0f) {
                a.attackCooldown = 1.35f;
                pendingDamage += 8.0f;
            }
        } else if (!aggressive && dist < 6.5f && a.state != 2) {
            a.state = 2;
            a.timer = 2.6f;
            Vec3 away = a.position - viewPos;
            away.y = 0.0f;
            if (lengthSq(away) > 1e-4f) a.yaw = std::atan2(away.x, -away.z);
        }

        if (a.state != 0 && !(a.state == 3 && dist < 1.5f)) {
            float speed = (a.state == 2 ? 3.6f : (a.state == 3 ? 3.1f : 1.4f)) + a.species * 0.30f;
            Vec3 dir(std::sin(a.yaw), 0, -std::cos(a.yaw));
            Vec3 next = a.position + dir * speed * dt;
            if (land.inBounds(next.x, next.z) && !land.underwater(next.x, next.z)) {
                a.position.x = next.x;
                a.position.z = next.z;
            } else {
                a.yaw += PI * 0.6f;
            }
        }
        a.position.y = land.heightAt(a.position.x, a.position.z);
        a.phase += dt * (2.0f + a.species * 0.4f) * (a.state >= 2 ? 2.1f : 1.0f);
    }
}

void AetheriaWorld::update(float dt, float time, const Vec3& viewPos) {
    sky.advance(dt);
    windPhase += dt * 0.55f;
    updateWildlife(dt, time, viewPos);

    for (auto& h : villagers) {
        if (distanceSq(h.position, viewPos) > 120.0f * 120.0f) continue;
        h.update(dt, time, viewPos, distanceSq(h.position, viewPos) < 20.0f * 20.0f);
    }
}

void AetheriaWorld::applySky(Renderer& renderer) {
    SkyParams& sp = renderer.sky();
    sp.enabled = true;
    sp.sunDirection = sky.sunDirection;
    sp.sunColor = sky.sunColor;
    sp.sunIntensity = clampf(sky.sunAltitude * 3.4f, 0.0f, 3.4f) + 0.10f;
    sp.zenith = sky.skyZenith;
    sp.horizon = sky.skyHorizon;
    sp.ground = sky.ground;
    sp.sunDisc = clampf(sky.sunAltitude * 4.0f, 0.0f, 1.0f);
    sp.starAmount = sky.starAmount * 0.9f;
    sp.cloudAmount = 0.42f;

    TerrainParams& tp = renderer.terrainParams();
    tp.waterLevel = land.waterLevel();
    tp.maxHeight = land.config().maxHeight;
    tp.snowLine = 0.60f;

    sp.aerialDensity = lerpf(0.0016f, 0.0026f, 1.0f - sky.ambientScale);
    sp.aerialHeight = 0.0045f;

    AtmosphereParams& atmos = renderer.atmosphere();
    float amb = sky.ambientScale;
    atmos.ambientTop = lerp(Vec3(0.038f, 0.052f, 0.100f), Vec3(0.340f, 0.395f, 0.470f), amb);
    atmos.ambientBottom = lerp(Vec3(0.016f, 0.018f, 0.028f), Vec3(0.150f, 0.160f, 0.140f), amb);
    atmos.fogColor = lerp(Vec3(0.030f, 0.040f, 0.070f), sky.skyHorizon * 0.85f, amb);
    atmos.fogDensity = 0.0f;
    atmos.dust = 0.0f;
    atmos.decay = 0.0f;
    atmos.globalWetness = 0.0f;
}

void AetheriaWorld::collectRender(Renderer& renderer, const CameraData& cam, float viewDistance) {
    for (const auto& chunk : land.chunks()) {
        if (!chunk.mesh || !chunk.mesh->valid()) continue;
        if (!cam.frustum.testAABB(chunk.bounds)) continue;
        if (chunk.bounds.distSq(cam.position) > viewDistance * viewDistance * 4.0f) continue;

        DrawCall dc;
        dc.mesh = chunk.mesh.get();
        dc.subIndex = 0;
        dc.transform = Mat4();
        dc.bounds = chunk.bounds;
        dc.castShadow = false;
        renderer.submitTerrain(dc);
    }

    if (gridDim > 0) {
        int gx = clampi((int)(cam.position.x / gridCell), 0, gridDim - 1);
        int gz = clampi((int)(cam.position.z / gridCell), 0, gridDim - 1);
        int span = clampi((int)(viewDistance / gridCell) + 1, 1, 8);

        for (int dz = -span; dz <= span; dz++) {
            for (int dx = -span; dx <= span; dx++) {
                int cx = gx + dx, cz = gz + dz;
                if (cx < 0 || cz < 0 || cx >= gridDim || cz >= gridDim) continue;

                for (int idx : floraGrid[(size_t)(cz * gridDim + cx)]) {
                    const FloraInstance& f = instances[(size_t)idx];
                    if (f.harvested) continue;
                    Vec3 pos(f.x, f.y, f.z);
                    float d2 = distanceSq(pos, cam.position);

                    float budget = viewDistance;
                    if (f.type == FLORA_GRASS || f.type == FLORA_FLOWER) budget = std::min(viewDistance, 42.0f);
                    else if (f.type == FLORA_MUSHROOM || f.type == FLORA_FERN) budget = std::min(viewDistance, 70.0f);
                    if (d2 > budget * budget) continue;

                    const FloraMesh& fm = flora[f.type];
                    float sway = 0.0f;
                    if (f.type == FLORA_GRASS || f.type == FLORA_FLOWER || f.type == FLORA_FERN) {
                        sway = std::sin(windPhase * 2.1f + f.x * 0.35f + f.z * 0.21f) * 0.10f;
                    } else if (f.type <= FLORA_DEAD_TREE) {
                        sway = std::sin(windPhase * 0.8f + f.x * 0.11f) * 0.022f;
                    }

                    Mat4 xf = Mat4::translate(pos) * Mat4::rotateY(f.yaw) * Mat4::rotateZ(sway) *
                              Mat4::scale(Vec3(f.scale));
                    AABB wb = fm.bounds.transformed(xf);
                    if (!cam.frustum.testAABB(wb)) continue;

                    DrawCall dc;
                    dc.mesh = &fm.mesh;
                    dc.transform = xf;
                    dc.castShadow = fm.castShadow && d2 < 45.0f * 45.0f;
                    dc.tint = Vec4(f.tint, f.tint, f.tint, 1.0f);

                    for (int sub = 0; sub < (int)fm.mesh.subMeshes().size(); sub++) {
                        const SubMesh& sm = fm.mesh.subMeshes()[(size_t)sub];
                        dc.subIndex = sub;
                        dc.material = sm.material;
                        dc.bounds = sm.bounds.transformed(xf);
                        dc.transparent = false;
                        renderer.submit(dc);
                    }
                }
            }
        }
    }

    float structureRange = std::max(viewDistance, 150.0f);
    for (const auto& b : structures) {
        const BuildingMesh& bm = buildLib.get(b.type);
        if (!bm.mesh.valid()) continue;
        float d2 = distanceSq(b.position, cam.position);
        if (d2 > structureRange * structureRange) continue;

        Mat4 xf = Mat4::translate(b.position) * Mat4::rotateY(b.yaw) * Mat4::scale(Vec3(b.scale));
        AABB wb = bm.bounds.transformed(xf);
        if (!cam.frustum.testAABB(wb)) continue;

        DrawCall dc;
        dc.mesh = &bm.mesh;
        dc.transform = xf;
        dc.castShadow = d2 < 70.0f * 70.0f;
        dc.tint = Vec4(b.tint, b.tint, b.tint, 1.0f);
        for (int sub = 0; sub < (int)bm.mesh.subMeshes().size(); sub++) {
            const SubMesh& sm = bm.mesh.subMeshes()[(size_t)sub];
            dc.subIndex = sub;
            dc.material = sm.material;
            dc.bounds = sm.bounds.transformed(xf);
            renderer.submit(dc);
        }

        if (bm.lit && d2 < 62.0f * 62.0f) {
            float night = clampf(1.25f - sky.ambientScale * 1.35f, 0.0f, 1.0f);
            float flicker = 0.88f + std::sin(windPhase * 5.3f + b.position.x * 0.7f) * 0.12f;
            RenderLight light;
            float s = std::sin(b.yaw), c = std::cos(b.yaw);
            Vec3 o = bm.lightOffset * b.scale;
            light.position = b.position + Vec3(o.x * c + o.z * s, o.y, -o.x * s + o.z * c);
            light.color = bm.lightColor;
            light.intensity = (0.9f + night * 4.2f) * flicker;
            light.range = bm.lightRange * b.scale;
            light.volumetric = 0.35f;
            light.priority = 90.0f - std::sqrt(d2);
            renderer.submitLight(light);
        }
    }

    if (creatureMesh && creatureMesh->valid()) {
        for (const auto& a : wildlife) {
            if (!a.alive) continue;
            float d2 = distanceSq(a.position, cam.position);
            if (d2 > 90.0f * 90.0f) continue;
            float hop = a.state != 0 ? std::fabs(std::sin(a.phase)) * 0.16f : 0.0f;
            Mat4 xf = Mat4::translate(a.position + Vec3(0, hop, 0)) * Mat4::rotateY(a.yaw) * Mat4::scale(Vec3(a.scale));
            AABB wb = creatureMesh->bounds().transformed(xf);
            if (!cam.frustum.testAABB(wb)) continue;

            Vec3 tint = kSpeciesTint[a.species % 5];
            if (a.hitFlash > 0.0f) tint = lerp(tint, Vec3(2.2f, 0.8f, 0.7f), clampf(a.hitFlash * 2.6f, 0.0f, 1.0f));

            DrawCall dc;
            dc.mesh = creatureMesh.get();
            dc.transform = xf;
            dc.castShadow = d2 < 30.0f * 30.0f;
            dc.tint = Vec4(tint, 1.0f);
            for (int sub = 0; sub < (int)creatureMesh->subMeshes().size(); sub++) {
                const SubMesh& sm = creatureMesh->subMeshes()[(size_t)sub];
                dc.subIndex = sub;
                dc.material = sm.material;
                dc.bounds = sm.bounds.transformed(xf);
                renderer.submit(dc);
            }
        }
    }

    for (const auto& h : villagers) {
        if (distanceSq(h.position, cam.position) > 85.0f * 85.0f) continue;
        h.submit(renderer, villagerRig);
    }

    if (waterMesh && waterMesh->valid()) {
        DrawCall dc;
        dc.mesh = waterMesh.get();
        dc.subIndex = 0;
        dc.transform = Mat4();
        dc.material = MAT_GLASS;
        dc.transparent = true;
        dc.castShadow = false;
        dc.tint = Vec4(0.34f, 0.62f, 0.70f, 0.60f);
        dc.bounds = waterMesh->bounds();
        renderer.submit(dc);
    }
}

}
