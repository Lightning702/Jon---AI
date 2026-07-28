#pragma once

#include "../render/Mesh.h"
#include "../render/Renderer.h"
#include "../physics/PhysicsWorld.h"
#include "../core/Random.h"

namespace aeth {

using namespace echo;

enum Biome {
    BIOME_MEADOW = 0,
    BIOME_FOREST,
    BIOME_GOLDEN_WOOD,
    BIOME_HIGHLAND,
    BIOME_SNOW,
    BIOME_MARSH,
    BIOME_SHORE,
    BIOME_COUNT
};

const char* biomeName(int biome);

struct TerrainConfig {
    u64 seed = 7777;
    float worldSize = 512.0f;
    int chunkCount = 16;
    int chunkResolution = 33;
    float maxHeight = 92.0f;
    float waterLevel = 8.5f;
};

struct TerrainChunk {
    Ref<Mesh> mesh;
    em::AABB bounds;
    int cx = 0, cz = 0;
    int dominantBiome = BIOME_MEADOW;
};

class Terrain {
public:
    void generate(const TerrainConfig& cfg);
    void destroy();

    float heightAt(float x, float z) const;
    em::Vec3 normalAt(float x, float z) const;
    int biomeAt(float x, float z) const;
    float slopeAt(float x, float z) const;
    bool underwater(float x, float z) const;

    const std::vector<TerrainChunk>& chunks() const { return chunkList; }
    const TerrainConfig& config() const { return cfg_; }
    float waterLevel() const { return cfg_.waterLevel; }
    float worldSize() const { return cfg_.worldSize; }
    em::Vec2 center() const { return em::Vec2(cfg_.worldSize * 0.5f, cfg_.worldSize * 0.5f); }
    bool inBounds(float x, float z) const { return x > 2.0f && z > 2.0f && x < cfg_.worldSize - 2.0f && z < cfg_.worldSize - 2.0f; }

    em::Vec3 findSpawn(em::Rng& rng, int preferredBiome) const;
    em::Vec3 findFlatGround(const em::Vec2& near, float radius, em::Rng& rng) const;

private:
    void buildHeightField();
    void buildChunks();
    float sampleRaw(float x, float z) const;
    int heightIndex(int x, int z) const;

    TerrainConfig cfg_;
    std::vector<float> heights;
    std::vector<u8> biomes;
    std::vector<TerrainChunk> chunkList;
    int fieldSize = 0;
    float cellSize = 1.0f;
};

}
