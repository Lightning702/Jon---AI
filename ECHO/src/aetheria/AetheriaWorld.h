#pragma once

#include "Terrain.h"
#include "Village.h"
#include "../render/Renderer.h"
#include "../world/Human.h"

namespace aeth {

enum FloraType {
    FLORA_PINE = 0,
    FLORA_BROADLEAF,
    FLORA_GOLDEN_TREE,
    FLORA_DEAD_TREE,
    FLORA_BUSH,
    FLORA_FERN,
    FLORA_GRASS,
    FLORA_FLOWER,
    FLORA_ROCK,
    FLORA_BOULDER,
    FLORA_MUSHROOM,
    FLORA_CRYSTAL,
    FLORA_COUNT
};

struct FloraMesh {
    echo::Mesh mesh;
    em::AABB bounds;
    float collisionRadius = 0.0f;
    bool castShadow = true;
};

struct FloraInstance {
    u16 type = 0;
    float x = 0, z = 0, y = 0;
    float yaw = 0.0f;
    float scale = 1.0f;
    float tint = 1.0f;
    bool harvested = false;
};

struct WildlifeAgent {
    int species = 0;
    em::Vec3 position;
    em::Vec3 velocity;
    float yaw = 0.0f;
    float phase = 0.0f;
    float timer = 0.0f;
    int state = 0;
    float scale = 1.0f;
    float health = 30.0f;
    float hitFlash = 0.0f;
    float respawn = 0.0f;
    float attackCooldown = 0.0f;
    bool alive = true;
};

struct Settlement {
    em::Vec3 center;
    float radius = 18.0f;
    std::string name;
    int biome = 0;
    std::string giverName;
    em::Vec3 giverPos;
    float giverYaw = 0.0f;
    bool visited = false;
};

struct Landmark {
    em::Vec3 position;
    std::string name;
    int kind = 0;
    bool found = false;
};

struct StrikeResult {
    bool hit = false;
    bool killed = false;
    int species = 0;
    em::Vec3 point;
};

struct DayNight {
    float timeOfDay = 0.30f;
    float daySpeed = 1.0f / 900.0f;
    float sunAltitude = 0.0f;
    em::Vec3 sunDirection;
    em::Vec3 sunColor;
    em::Vec3 skyZenith, skyHorizon, ground;
    float starAmount = 0.0f;
    float ambientScale = 1.0f;
    void advance(float dt);
};

class AetheriaWorld {
public:
    void generate(u64 seed);
    void destroy();

    void update(float dt, float time, const em::Vec3& viewPos);
    void collectRender(echo::Renderer& renderer, const echo::CameraData& cam, float viewDistance);
    void applySky(echo::Renderer& renderer);

    Terrain& terrain() { return land; }
    const Terrain& terrain() const { return land; }
    DayNight& clock() { return sky; }

    em::Vec3 spawnPoint() const { return spawn; }
    float groundHeight(float x, float z) const { return land.heightAt(x, z); }
    bool blocked(const em::Vec3& p, float radius) const;
    em::Vec3 resolveMovement(const em::Vec3& from, const em::Vec3& to, float radius) const;

    const std::vector<Settlement>& settlements() const { return villages; }
    std::vector<Settlement>& settlements() { return villages; }
    const std::vector<Landmark>& landmarks() const { return marks; }
    std::vector<Landmark>& landmarks() { return marks; }
    int floraCount() const { return (int)instances.size(); }
    int wildlifeCount() const { return (int)wildlife.size(); }
    std::string regionName(const em::Vec3& p) const;

    int villageAt(const em::Vec3& p, float extra) const;
    int landmarkAt(const em::Vec3& p, float extra) const;
    int harvestableNear(const em::Vec3& p, float radius) const;
    int nearestOfType(const em::Vec3& p, int floraType, float maxDistance) const;
    int floraTypeOf(int index) const;
    const char* harvestName(int floraType) const;
    em::Vec3 floraPosition(int index) const;
    void harvest(int index);
    StrikeResult strike(const em::Vec3& origin, const em::Vec3& forward, float range, float damage);
    float consumeDamage();

private:
    void buildFloraMeshes();
    void scatterFlora(em::Rng& rng);
    void buildWater();
    void placeSettlements(em::Rng& rng);
    void placeLandmarks(em::Rng& rng);
    void addBuilding(int type, const em::Vec3& pos, float yaw, float scale, float tint);
    void clearFloraAround(const em::Vec2& center, float radius, float minCollision);
    void spawnWildlife(em::Rng& rng);
    void updateWildlife(float dt, float time, const em::Vec3& viewPos);
    void respawnAgent(WildlifeAgent& a);

    Terrain land;
    FloraMesh flora[FLORA_COUNT];
    std::vector<FloraInstance> instances;
    std::vector<std::vector<int>> floraGrid;
    std::vector<WildlifeAgent> wildlife;
    std::vector<Settlement> villages;
    std::vector<Landmark> marks;
    BuildingLibrary buildLib;
    std::vector<BuildingInstance> structures;
    std::vector<BoxCollider> boxes;
    echo::HumanRig villagerRig;
    std::vector<echo::HumanInstance> villagers;
    em::Rng worldRng;

    Ref<echo::Mesh> waterMesh;
    Ref<echo::Mesh> creatureMesh;
    DayNight sky;

    em::Vec3 spawn;
    int gridDim = 0;
    float gridCell = 32.0f;
    u64 worldSeed = 0;
    float windPhase = 0.0f;
    float pendingDamage = 0.0f;
};

}
