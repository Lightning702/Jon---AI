#include "Terrain.h"
#include "../core/Log.h"
#include "../core/Time.h"
#include "../core/Parallel.h"

using namespace em;

namespace aeth {

namespace {

const char* kBiomeNames[BIOME_COUNT] = {
    "Wiesengrund", "Tiefwald", "Goldhain", "Hochland", "Firnkamm", "Nebelmoor", "Muschelkueste"
};

float ridged(Vec2 p, int octaves, float seed) {
    float sum = 0.0f, amp = 0.5f, norm = 0.0f;
    for (int i = 0; i < octaves; i++) {
        float n = valueNoise2(p + Vec2(seed, seed * 1.7f));
        n = 1.0f - std::fabs(n * 2.0f - 1.0f);
        sum += n * n * amp;
        norm += amp;
        p *= 2.03f;
        amp *= 0.52f;
    }
    return norm > 0 ? sum / norm : 0.0f;
}

}

const char* biomeName(int biome) {
    return kBiomeNames[clampi(biome, 0, BIOME_COUNT - 1)];
}

int Terrain::heightIndex(int x, int z) const {
    x = clampi(x, 0, fieldSize - 1);
    z = clampi(z, 0, fieldSize - 1);
    return z * fieldSize + x;
}

float Terrain::sampleRaw(float x, float z) const {
    float s = cfg_.worldSize;
    Vec2 uv(x / s, z / s);
    float seed = (float)(cfg_.seed % 4096) * 0.017f;

    float continent = fbm2(uv * 1.6f + Vec2(seed, seed), 5);
    float mountains = ridged(uv * 3.1f, 6, seed + 11.0f);
    float hills = fbm2(uv * 7.4f + Vec2(seed * 2.0f, 0.0f), 5);
    float detail = fbm2(uv * 26.0f, 4);

    Vec2 d = uv - Vec2(0.5f, 0.5f);
    float radial = clampf(1.0f - length(d) * 1.72f, 0.0f, 1.0f);
    float island = smoothstepf(0.02f, 0.55f, radial);

    float mountainMask = smoothstepf(0.45f, 0.85f, continent);
    float h = continent * 0.42f + hills * 0.20f + detail * 0.05f;
    h += mountains * mountainMask * 0.62f;
    h *= island;

    float shoreFlatten = smoothstepf(0.06f, 0.22f, h);
    h = lerpf(h * 0.55f, h, shoreFlatten);

    return h * cfg_.maxHeight;
}

void Terrain::buildHeightField() {
    fieldSize = cfg_.chunkCount * (cfg_.chunkResolution - 1) + 1;
    cellSize = cfg_.worldSize / (float)(fieldSize - 1);
    heights.assign((size_t)fieldSize * fieldSize, 0.0f);
    biomes.assign((size_t)fieldSize * fieldSize, BIOME_MEADOW);

    parallelFor(fieldSize, [&](int z) {
        for (int x = 0; x < fieldSize; x++) {
            float wx = x * cellSize;
            float wz = z * cellSize;
            heights[(size_t)heightIndex(x, z)] = sampleRaw(wx, wz);
        }
    });

    parallelFor(fieldSize, [&](int z) {
        for (int x = 0; x < fieldSize; x++) {
            float h = heights[(size_t)heightIndex(x, z)];
            float wx = x * cellSize;
            float wz = z * cellSize;
            Vec2 uv(wx / cfg_.worldSize, wz / cfg_.worldSize);

            float dhx = heights[(size_t)heightIndex(x + 1, z)] - heights[(size_t)heightIndex(x - 1, z)];
            float dhz = heights[(size_t)heightIndex(x, z + 1)] - heights[(size_t)heightIndex(x, z - 1)];
            float slope = length(Vec2(dhx, dhz)) / (2.0f * cellSize);

            float moisture = fbm2(uv * 4.2f + Vec2(53.0f, 17.0f), 4);
            float warmth = fbm2(uv * 2.6f + Vec2(9.0f, 71.0f), 4);

            int b = BIOME_MEADOW;
            if (h < cfg_.waterLevel + 1.6f) b = BIOME_SHORE;
            else if (h > cfg_.maxHeight * 0.62f) b = BIOME_SNOW;
            else if (h > cfg_.maxHeight * 0.40f || slope > 0.85f) b = BIOME_HIGHLAND;
            else if (moisture > 0.62f && h < cfg_.waterLevel + 9.0f) b = BIOME_MARSH;
            else if (warmth > 0.58f && moisture < 0.52f) b = BIOME_GOLDEN_WOOD;
            else if (moisture > 0.46f) b = BIOME_FOREST;

            biomes[(size_t)heightIndex(x, z)] = (u8)b;
        }
    });
}

void Terrain::buildChunks() {
    int res = cfg_.chunkResolution;
    float chunkWorld = cfg_.worldSize / cfg_.chunkCount;

    chunkList.clear();
    chunkList.reserve((size_t)cfg_.chunkCount * cfg_.chunkCount);

    for (int cz = 0; cz < cfg_.chunkCount; cz++) {
        for (int cx = 0; cx < cfg_.chunkCount; cx++) {
            MeshBuilder mb;
            mb.setMaterial(0);

            std::vector<Vertex>& verts = mb.vertices();
            std::vector<u32>& inds = mb.indices();
            verts.reserve((size_t)res * res);
            inds.reserve((size_t)(res - 1) * (res - 1) * 6);

            int baseX = cx * (res - 1);
            int baseZ = cz * (res - 1);
            int counts[BIOME_COUNT] = {};

            for (int z = 0; z < res; z++) {
                for (int x = 0; x < res; x++) {
                    int gx = baseX + x;
                    int gz = baseZ + z;
                    float wx = gx * cellSize;
                    float wz = gz * cellSize;
                    float h = heights[(size_t)heightIndex(gx, gz)];

                    float hl = heights[(size_t)heightIndex(gx - 1, gz)];
                    float hr = heights[(size_t)heightIndex(gx + 1, gz)];
                    float hd = heights[(size_t)heightIndex(gx, gz - 1)];
                    float hu = heights[(size_t)heightIndex(gx, gz + 1)];
                    Vec3 n = normalize(Vec3(hl - hr, 2.0f * cellSize, hd - hu));

                    int b = biomes[(size_t)heightIndex(gx, gz)];
                    counts[b]++;

                    Vertex v;
                    v.pos = Vec3(wx, h, wz);
                    v.normal = n;
                    v.tangent = Vec4(1, 0, 0, 1);
                    v.uv = Vec2(wx, wz);
                    v.color[0] = (u8)b;
                    v.color[1] = (u8)(clampf(h / cfg_.maxHeight, 0.0f, 1.0f) * 255.0f);
                    v.color[2] = (u8)(clampf(1.0f - n.y, 0.0f, 1.0f) * 255.0f);
                    v.color[3] = 255;
                    verts.push_back(v);
                }
            }

            for (int z = 0; z < res - 1; z++) {
                for (int x = 0; x < res - 1; x++) {
                    u32 i0 = (u32)(z * res + x);
                    u32 i1 = i0 + 1;
                    u32 i2 = i0 + res;
                    u32 i3 = i2 + 1;
                    inds.push_back(i0); inds.push_back(i2); inds.push_back(i1);
                    inds.push_back(i1); inds.push_back(i2); inds.push_back(i3);
                }
            }

            TerrainChunk chunk;
            chunk.cx = cx;
            chunk.cz = cz;
            chunk.mesh = std::make_shared<Mesh>();

            int best = 0;
            for (int i = 1; i < BIOME_COUNT; i++) if (counts[i] > counts[best]) best = i;
            chunk.dominantBiome = best;

            mb.build(*chunk.mesh);
            chunk.bounds = chunk.mesh->bounds();
            chunkList.push_back(chunk);
        }
    }
}

void Terrain::generate(const TerrainConfig& cfg) {
    Clock clock;
    cfg_ = cfg;
    buildHeightField();
    buildChunks();
    LOG_INFO("Aetheria terrain: %.0fm, %d chunks, %dx%d samples in %.2fs",
             cfg_.worldSize, (int)chunkList.size(), fieldSize, fieldSize, clock.elapsed());
}

void Terrain::destroy() {
    chunkList.clear();
    heights.clear();
    biomes.clear();
}

float Terrain::heightAt(float x, float z) const {
    if (heights.empty()) return 0.0f;
    float fx = clampf(x / cellSize, 0.0f, (float)(fieldSize - 1));
    float fz = clampf(z / cellSize, 0.0f, (float)(fieldSize - 1));
    int x0 = (int)fx, z0 = (int)fz;
    int x1 = std::min(x0 + 1, fieldSize - 1);
    int z1 = std::min(z0 + 1, fieldSize - 1);
    float tx = fx - x0, tz = fz - z0;

    float h00 = heights[(size_t)heightIndex(x0, z0)];
    float h10 = heights[(size_t)heightIndex(x1, z0)];
    float h01 = heights[(size_t)heightIndex(x0, z1)];
    float h11 = heights[(size_t)heightIndex(x1, z1)];
    return lerpf(lerpf(h00, h10, tx), lerpf(h01, h11, tx), tz);
}

Vec3 Terrain::normalAt(float x, float z) const {
    float e = cellSize;
    float hl = heightAt(x - e, z);
    float hr = heightAt(x + e, z);
    float hd = heightAt(x, z - e);
    float hu = heightAt(x, z + e);
    return normalize(Vec3(hl - hr, 2.0f * e, hd - hu));
}

float Terrain::slopeAt(float x, float z) const {
    return 1.0f - normalAt(x, z).y;
}

int Terrain::biomeAt(float x, float z) const {
    if (biomes.empty()) return BIOME_MEADOW;
    int gx = clampi((int)std::round(x / cellSize), 0, fieldSize - 1);
    int gz = clampi((int)std::round(z / cellSize), 0, fieldSize - 1);
    return biomes[(size_t)heightIndex(gx, gz)];
}

bool Terrain::underwater(float x, float z) const {
    return heightAt(x, z) < cfg_.waterLevel;
}

Vec3 Terrain::findFlatGround(const Vec2& nearPoint, float radius, Rng& rng) const {
    Vec3 best(nearPoint.x, heightAt(nearPoint.x, nearPoint.y), nearPoint.y);
    float bestScore = -1e30f;

    for (int i = 0; i < 64; i++) {
        Vec2 offset = rng.unitDisk() * radius;
        float x = nearPoint.x + offset.x;
        float z = nearPoint.y + offset.y;
        if (!inBounds(x, z)) continue;
        float h = heightAt(x, z);
        if (h < cfg_.waterLevel + 1.0f) continue;
        float flat = 1.0f - slopeAt(x, z);
        float score = flat * 3.0f - std::fabs(h - cfg_.waterLevel - 12.0f) * 0.02f;
        if (score > bestScore) {
            bestScore = score;
            best = Vec3(x, h, z);
        }
    }
    return best;
}

Vec3 Terrain::findSpawn(Rng& rng, int preferredBiome) const {
    Vec3 fallback(cfg_.worldSize * 0.5f, 0.0f, cfg_.worldSize * 0.5f);
    fallback.y = heightAt(fallback.x, fallback.z);

    for (int attempt = 0; attempt < 900; attempt++) {
        float x = rng.range(cfg_.worldSize * 0.25f, cfg_.worldSize * 0.75f);
        float z = rng.range(cfg_.worldSize * 0.25f, cfg_.worldSize * 0.75f);
        float h = heightAt(x, z);
        if (h < cfg_.waterLevel + 2.5f) continue;
        if (h > cfg_.maxHeight * 0.36f) continue;
        if (slopeAt(x, z) > 0.22f) continue;
        if (preferredBiome >= 0 && biomeAt(x, z) != preferredBiome && attempt < 600) continue;
        return Vec3(x, h, z);
    }
    return fallback;
}

}
