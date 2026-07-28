#include "Material.h"
#include "Shader.h"
#include "../core/Log.h"
#include "../core/Random.h"
#include "../core/Parallel.h"
#include "../core/Time.h"

using namespace em;

namespace echo {

namespace {

struct Sample {
    Vec3 albedo = Vec3(0.5f);
    float rough = 0.7f;
    float metal = 0.0f;
    float ao = 1.0f;
    float height = 0.5f;
};

struct MatMaps {
    Image albedo, normal, orm;
};

inline Vec2 uvAt(int x, int y, int res) {
    return Vec2((float)x / res, (float)y / res);
}

inline float linToSrgb1(float c) {
    c = saturate(c);
    return c <= 0.0031308f ? c * 12.92f : 1.055f * std::pow(c, 1.0f / 2.4f) - 0.055f;
}

inline Vec3 linToSrgb(const Vec3& c) {
    return Vec3(linToSrgb1(c.x), linToSrgb1(c.y), linToSrgb1(c.z));
}

inline float grunge(const Vec2& uv, float scale, float off) {
    return fbm2(Vec2(uv.x * scale + off, uv.y * scale + off * 1.7f), 5);
}

inline float streaks(const Vec2& uv, float density, float off) {
    float n = fbm2(Vec2(uv.x * density + off, uv.y * density * 0.08f + off), 4);
    float m = fbm2(Vec2(uv.x * density * 3.0f + off * 2.0f, uv.y * density * 0.2f), 3);
    return saturate(n * 0.7f + m * 0.4f);
}

inline float cracks(const Vec2& uv, float scale, float off) {
    float f2;
    float f1 = worley2(Vec2(uv.x * scale + off, uv.y * scale + off), f2);
    float edge = f2 - f1;
    return 1.0f - smoothstepf(0.0f, 0.022f, edge);
}

inline float tilePattern(const Vec2& uv, float tilesX, float tilesY, float grout, Vec2& local, Vec2& cell, float& edge) {
    Vec2 t(uv.x * tilesX, uv.y * tilesY);
    cell = Vec2(std::floor(t.x), std::floor(t.y));
    local = Vec2(t.x - cell.x, t.y - cell.y);
    float dx = std::min(local.x, 1.0f - local.x);
    float dy = std::min(local.y, 1.0f - local.y);
    edge = std::min(dx, dy);
    return edge < grout ? 0.0f : 1.0f;
}

inline Vec3 tintVary(const Vec3& base, float v, float amount) {
    return base * (1.0f + (v - 0.5f) * amount);
}

inline float spotStain(const Vec2& uv, float scale, float off, float threshold) {
    float n = fbm2(Vec2(uv.x * scale + off * 3.1f, uv.y * scale + off * 7.3f), 4);
    return smoothstepf(threshold, threshold + 0.18f, n);
}

template <typename F>
void generateMaps(int res, MatMaps& m, F fn, float normalStrength) {
    m.albedo.allocate(res, res, 4);
    m.orm.allocate(res, res, 3);
    Image height;
    height.allocate(res, res, 1);

    for (int y = 0; y < res; y++) {
        for (int x = 0; x < res; x++) {
            Vec2 uv = uvAt(x, y, res);
            Sample s = fn(uv, x, y);
            Vec3 enc = linToSrgb(s.albedo);
            m.albedo.set(x, y, Vec4(enc.x, enc.y, enc.z, 1.0f));
            m.orm.set(x, y, Vec3(saturate(s.ao), saturate(s.rough), saturate(s.metal)));
            height.data[(size_t)y * res + x] = (u8)(saturate(s.height) * 255.0f);
        }
    }

    imageToNormalMap(height, m.normal, normalStrength);
}

void genTileWall(int res, MatMaps& m, const Vec3& tileColor, float dirtAmount, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        Vec2 local, cell;
        float edge;
        float inTile = tilePattern(uv, 8.0f, 8.0f, 0.035f, local, cell, edge);
        float cellRand = hash21(cell + Vec2(seed, seed * 2.0f));
        float cellRand2 = hash21(cell + Vec2(seed * 3.0f, seed * 5.0f));

        Vec3 grout(0.30f, 0.30f, 0.29f);
        grout = grout * (0.55f + 0.6f * grunge(uv, 40.0f, seed));

        Vec3 tile = tintVary(tileColor, cellRand, 0.22f);
        float gloss = fbm2(Vec2(uv.x * 90.0f + seed, uv.y * 90.0f), 3);
        tile = tile * (0.9f + 0.16f * gloss);

        float dirt = streaks(uv, 14.0f, seed) * dirtAmount;
        float stain = spotStain(uv, 5.0f, seed, 0.58f) * dirtAmount;
        float mold = spotStain(uv, 11.0f, seed + 4.0f, 0.66f) * dirtAmount;

        bool missing = cellRand2 > 0.955f;
        bool cracked = cellRand2 > 0.90f && !missing;

        if (missing) {
            s.albedo = lerp(Vec3(0.19f, 0.17f, 0.16f), Vec3(0.11f, 0.10f, 0.10f), grunge(uv, 60.0f, seed));
            s.rough = 0.94f;
            s.height = 0.25f;
            s.ao = 0.5f;
        } else if (inTile > 0.5f) {
            s.albedo = tile;
            s.rough = 0.18f + 0.35f * gloss;
            s.height = 0.78f;
            s.ao = 1.0f;
            if (cracked) {
                float cr = cracks(Vec2(uv.x * 1.0f, uv.y * 1.0f), 60.0f, seed + cellRand);
                s.albedo = lerp(s.albedo, Vec3(0.14f, 0.13f, 0.13f), cr * 0.85f);
                s.rough = lerpf(s.rough, 0.9f, cr);
                s.height -= cr * 0.2f;
            }
        } else {
            s.albedo = grout;
            s.rough = 0.88f;
            s.height = 0.32f + 0.1f * grunge(uv, 80.0f, seed);
            s.ao = 0.42f + 0.3f * smoothstepf(0.0f, 0.035f, edge);
        }

        Vec3 dirtColor(0.16f, 0.14f, 0.11f);
        Vec3 moldColor(0.11f, 0.13f, 0.09f);
        s.albedo = lerp(s.albedo, dirtColor, saturate(dirt * 0.55f + stain * 0.35f));
        s.albedo = lerp(s.albedo, moldColor, mold * 0.5f);
        s.rough = saturate(s.rough + dirt * 0.35f + mold * 0.25f);
        s.ao = saturate(s.ao * (1.0f - dirt * 0.28f - stain * 0.15f));
        s.metal = 0.0f;
        return s;
    }, 3.0f);
}

void genPlaster(int res, MatMaps& m, const Vec3& base, float damage, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float coarse = fbm2(Vec2(uv.x * 6.0f + seed, uv.y * 6.0f + seed), 6);
        float fine = fbm2(Vec2(uv.x * 60.0f + seed, uv.y * 60.0f), 4);
        float peel = spotStain(uv, 4.0f, seed + 2.0f, 0.52f) * damage;
        float water = streaks(uv, 8.0f, seed + 9.0f) * damage;
        float crk = cracks(uv, 26.0f, seed) * damage * 0.45f;

        Vec3 paint = base * (0.86f + 0.28f * coarse) * (0.95f + 0.1f * fine);
        Vec3 under(0.42f, 0.38f, 0.34f);
        under = under * (0.8f + 0.4f * fine);

        s.albedo = lerp(paint, under, peel);
        s.albedo = lerp(s.albedo, Vec3(0.20f, 0.18f, 0.14f), saturate(water * 0.5f));
        s.albedo = lerp(s.albedo, Vec3(0.17f, 0.16f, 0.14f), crk * 0.55f);
        s.rough = saturate(0.72f + 0.2f * fine + peel * 0.18f + water * 0.1f);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - peel * 0.25f - crk * 0.28f - water * 0.12f);
        s.height = 0.6f + 0.20f * coarse + 0.1f * fine - peel * 0.22f - crk * 0.16f;
        return s;
    }, 2.4f);
}

void genConcrete(int res, MatMaps& m, const Vec3& base, float wet, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float coarse = fbm2(Vec2(uv.x * 5.0f + seed, uv.y * 5.0f + seed), 6);
        float mid = fbm2(Vec2(uv.x * 22.0f + seed, uv.y * 22.0f), 5);
        float fine = fbm2(Vec2(uv.x * 110.0f, uv.y * 110.0f + seed), 3);
        float f2;
        float pores = worley2(Vec2(uv.x * 45.0f + seed, uv.y * 45.0f), f2);
        float pore = smoothstepf(0.06f, 0.0f, pores);
        float crk = cracks(uv, 9.0f, seed + 3.0f);
        float dark = spotStain(uv, 3.0f, seed + 6.0f, 0.5f);

        Vec3 c = base * (0.82f + 0.3f * coarse) * (0.92f + 0.16f * mid);
        c = lerp(c, base * 0.55f, dark * 0.45f);
        c = lerp(c, Vec3(0.07f, 0.065f, 0.06f), crk * 0.9f);
        c = lerp(c, c * 0.4f, pore * 0.7f);

        s.albedo = c;
        s.rough = saturate(0.88f - 0.16f * mid + 0.08f * fine);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - pore * 0.55f - crk * 0.6f - dark * 0.12f);
        s.height = 0.55f + 0.18f * coarse + 0.12f * mid + 0.05f * fine - pore * 0.3f - crk * 0.4f;

        if (wet > 0.0f) {
            float puddle = smoothstepf(0.48f, 0.62f, fbm2(Vec2(uv.x * 3.0f + seed * 2.0f, uv.y * 3.0f), 5));
            puddle *= wet;
            s.rough = lerpf(s.rough, 0.09f, puddle);
            s.albedo = lerp(s.albedo, s.albedo * 0.45f, puddle);
            s.height = lerpf(s.height, 0.35f, puddle * 0.6f);
        }
        return s;
    }, 2.6f);
}

void genCheckerFloor(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        Vec2 local, cell;
        float edge;
        float inTile = tilePattern(uv, 8.0f, 8.0f, 0.014f, local, cell, edge);
        int parity = ((int)cell.x + (int)cell.y) & 1;
        float cr = hash21(cell + Vec2(seed, seed * 1.3f));
        float cr2 = hash21(cell + Vec2(seed * 4.0f, seed * 7.0f));

        Vec3 dark(0.045f, 0.048f, 0.050f);
        Vec3 light(0.62f, 0.615f, 0.595f);
        Vec3 tile = parity ? dark : light;
        tile = tintVary(tile, cr, parity ? 0.5f : 0.16f);

        float speckle = fbm2(Vec2(uv.x * 200.0f + seed, uv.y * 200.0f), 3);
        tile = tile * (0.92f + 0.16f * speckle);

        float wear = streaks(uv, 6.0f, seed + 1.0f);
        float grime = fbm2(Vec2(uv.x * 3.0f + seed * 2.0f, uv.y * 3.0f), 6);
        float scuff = smoothstepf(0.55f, 0.8f, fbm2(Vec2(uv.x * 26.0f + seed, uv.y * 26.0f), 4));

        if (inTile < 0.5f) {
            s.albedo = Vec3(0.14f, 0.14f, 0.135f) * (0.6f + 0.6f * grime);
            s.rough = 0.9f;
            s.height = 0.34f;
            s.ao = 0.55f;
        } else {
            s.albedo = tile;
            s.rough = lerpf(0.16f, 0.55f, saturate(wear * 0.8f + scuff * 0.5f));
            s.height = 0.8f - 0.05f * speckle;
            s.ao = 1.0f;
            if (cr2 > 0.965f) {
                float chip = cracks(uv, 70.0f, seed + cr);
                s.albedo = lerp(s.albedo, Vec3(0.12f, 0.11f, 0.10f), chip * 0.9f);
                s.rough = lerpf(s.rough, 0.92f, chip);
                s.height -= chip * 0.25f;
            }
        }

        s.albedo = lerp(s.albedo, Vec3(0.10f, 0.09f, 0.075f), saturate(grime * 0.55f - 0.12f));
        s.albedo = lerp(s.albedo, Vec3(0.055f, 0.05f, 0.045f), saturate(wear * 0.4f));
        s.ao = saturate(s.ao * (1.0f - grime * 0.22f));
        s.metal = 0.0f;

        float puddle = smoothstepf(0.52f, 0.68f, fbm2(Vec2(uv.x * 2.2f + seed * 3.0f, uv.y * 2.2f), 5));
        s.rough = lerpf(s.rough, 0.06f, puddle * 0.85f);
        s.albedo = lerp(s.albedo, s.albedo * 0.55f, puddle * 0.7f);
        return s;
    }, 2.2f);
}

void genLinoleum(int res, MatMaps& m, const Vec3& base, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float speck = fbm2(Vec2(uv.x * 260.0f + seed, uv.y * 260.0f), 3);
        float speck2 = fbm2(Vec2(uv.x * 90.0f, uv.y * 90.0f + seed), 4);
        float seam = 1.0f - smoothstepf(0.0f, 0.006f, std::fabs(fractf(uv.y * 2.0f + seed * 0.1f) - 0.5f));
        float wear = streaks(uv, 7.0f, seed + 5.0f);
        float grime = fbm2(Vec2(uv.x * 3.5f + seed, uv.y * 3.5f), 6);
        float scratch = smoothstepf(0.72f, 0.88f, fbm2(Vec2(uv.x * 160.0f + seed, uv.y * 12.0f), 3));

        Vec3 c = base * (0.9f + 0.2f * speck) * (0.94f + 0.12f * speck2);
        c = lerp(c, base * 0.4f, seam * 0.6f);
        c = lerp(c, Vec3(0.11f, 0.10f, 0.085f), saturate(grime * 0.6f - 0.1f));
        c = lerp(c, Vec3(0.16f, 0.15f, 0.14f), wear * 0.35f);
        c = lerp(c, c * 1.35f, scratch * 0.4f);

        s.albedo = c;
        s.rough = saturate(0.28f + wear * 0.4f + grime * 0.2f + scratch * 0.25f);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - seam * 0.35f - grime * 0.2f);
        s.height = 0.7f - seam * 0.3f + 0.05f * speck2;
        return s;
    }, 1.6f);
}

void genCeilingTile(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        Vec2 local, cell;
        float edge;
        float inTile = tilePattern(uv, 2.0f, 2.0f, 0.02f, local, cell, edge);
        float cr = hash21(cell + Vec2(seed, seed * 2.0f));

        float f2;
        float perf = worley2(Vec2(local.x * 26.0f + cell.x * 26.0f, local.y * 26.0f + cell.y * 26.0f), f2);
        float holes = smoothstepf(0.16f, 0.06f, perf);
        float fibre = fbm2(Vec2(uv.x * 120.0f + seed, uv.y * 120.0f), 4);

        Vec3 white(0.60f, 0.585f, 0.545f);
        white = tintVary(white, cr, 0.18f);
        float stain = spotStain(uv, 4.0f, seed + 3.0f, 0.5f);
        float heavyStain = spotStain(uv, 2.5f, seed + 8.0f, 0.62f);

        bool sagging = cr > 0.86f;
        bool gone = cr > 0.955f;

        if (gone) {
            s.albedo = Vec3(0.03f, 0.03f, 0.032f);
            s.rough = 0.95f;
            s.ao = 0.15f;
            s.height = 0.05f;
        } else if (inTile < 0.5f) {
            s.albedo = Vec3(0.20f, 0.20f, 0.19f);
            s.rough = 0.6f;
            s.metal = 0.35f;
            s.ao = 0.45f;
            s.height = 0.85f;
        } else {
            s.albedo = white * (0.9f + 0.16f * fibre);
            s.albedo = lerp(s.albedo, Vec3(0.42f, 0.34f, 0.22f), stain * 0.55f);
            s.albedo = lerp(s.albedo, Vec3(0.22f, 0.17f, 0.11f), heavyStain * 0.7f);
            s.albedo = lerp(s.albedo, s.albedo * 0.35f, holes * 0.8f);
            s.rough = saturate(0.9f + 0.08f * fibre);
            s.ao = saturate(1.0f - holes * 0.6f - stain * 0.2f);
            s.height = 0.62f - holes * 0.3f + 0.06f * fibre - (sagging ? 0.12f : 0.0f);
        }
        return s;
    }, 2.0f);
}

void genPaintedMetal(int res, MatMaps& m, const Vec3& base, float rust, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float brush = fbm2(Vec2(uv.x * 300.0f + seed, uv.y * 8.0f), 3);
        float coarse = fbm2(Vec2(uv.x * 7.0f + seed, uv.y * 7.0f), 5);
        float rustMask = smoothstepf(0.5f - rust * 0.28f, 0.72f - rust * 0.2f, fbm2(Vec2(uv.x * 5.0f + seed * 3.0f, uv.y * 5.0f), 6));
        float rustEdge = smoothstepf(0.42f, 0.6f, fbm2(Vec2(uv.x * 12.0f + seed * 3.0f, uv.y * 12.0f), 5));
        float scratch = smoothstepf(0.74f, 0.9f, fbm2(Vec2(uv.x * 200.0f + seed, uv.y * 20.0f), 3));
        float dents = fbm2(Vec2(uv.x * 16.0f + seed * 5.0f, uv.y * 16.0f), 4);

        Vec3 paint = base * (0.9f + 0.16f * coarse) * (0.96f + 0.08f * brush);
        Vec3 rustCol(0.30f, 0.13f, 0.055f);
        rustCol = rustCol * (0.6f + 0.9f * fbm2(Vec2(uv.x * 40.0f + seed, uv.y * 40.0f), 4));
        Vec3 bare(0.42f, 0.42f, 0.44f);

        float rm = rustMask * rust;
        s.albedo = lerp(paint, rustCol, rm);
        s.albedo = lerp(s.albedo, rustCol * 0.7f, rustEdge * rm * 0.5f);
        s.albedo = lerp(s.albedo, bare, scratch * 0.5f * (1.0f - rm));

        s.rough = lerpf(0.36f + 0.2f * brush, 0.92f, rm);
        s.rough = lerpf(s.rough, 0.24f, scratch * 0.4f * (1.0f - rm));
        s.metal = lerpf(0.85f, 0.05f, rm);
        s.metal = lerpf(s.metal, 1.0f, scratch * 0.5f * (1.0f - rm));
        s.ao = saturate(1.0f - rm * 0.25f);
        s.height = 0.6f + 0.1f * dents - rm * 0.22f + scratch * 0.05f;
        return s;
    }, 2.0f);
}

void genSteel(int res, MatMaps& m, float polish, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float brush = fbm2(Vec2(uv.x * 900.0f + seed, uv.y * 4.0f), 3);
        float brush2 = fbm2(Vec2(uv.x * 260.0f, uv.y * 6.0f + seed), 3);
        float smudge = fbm2(Vec2(uv.x * 9.0f + seed, uv.y * 9.0f), 5);
        float scratch = smoothstepf(0.78f, 0.94f, fbm2(Vec2(uv.x * 400.0f + seed, uv.y * 26.0f), 3));

        Vec3 c(0.55f, 0.56f, 0.575f);
        c = c * (0.9f + 0.16f * brush) * (0.95f + 0.1f * brush2);
        c = lerp(c, c * 0.72f, smudge * 0.4f);

        s.albedo = c;
        s.rough = saturate(lerpf(0.42f, 0.12f, polish) + smudge * 0.22f + scratch * 0.2f - brush * 0.05f);
        s.metal = 1.0f;
        s.ao = saturate(1.0f - smudge * 0.12f);
        s.height = 0.6f + 0.03f * brush + scratch * 0.04f;
        return s;
    }, 0.8f);
}

void genVentGrate(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float slat = fractf(uv.y * 16.0f);
        float open = smoothstepf(0.18f, 0.28f, slat) * (1.0f - smoothstepf(0.72f, 0.82f, slat));
        float dust = fbm2(Vec2(uv.x * 30.0f + seed, uv.y * 30.0f), 4);
        float rust = smoothstepf(0.55f, 0.75f, fbm2(Vec2(uv.x * 6.0f + seed * 2.0f, uv.y * 6.0f), 5));

        Vec3 metal(0.34f, 0.345f, 0.35f);
        Vec3 dark(0.012f, 0.012f, 0.014f);
        s.albedo = lerp(metal, dark, open);
        s.albedo = lerp(s.albedo, Vec3(0.26f, 0.12f, 0.05f), rust * 0.55f * (1.0f - open));
        s.albedo = lerp(s.albedo, Vec3(0.28f, 0.27f, 0.25f), dust * 0.25f * (1.0f - open));
        s.rough = lerpf(0.5f + rust * 0.4f, 0.98f, open);
        s.metal = lerpf(0.9f, 0.0f, open + rust * 0.5f);
        s.ao = lerpf(1.0f, 0.12f, open);
        s.height = lerpf(0.8f, 0.15f, open);
        return s;
    }, 3.5f);
}

void genWood(int res, MatMaps& m, const Vec3& base, float wear, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float ring = fractf((uv.x * 3.0f + fbm2(Vec2(uv.x * 2.0f + seed, uv.y * 0.6f), 4) * 1.2f) * 7.0f);
        float grain = fbm2(Vec2(uv.x * 400.0f + seed, uv.y * 12.0f), 4);
        float plank = std::floor(uv.y * 4.0f);
        float plankRand = hash21(Vec2(plank, seed));
        float seam = 1.0f - smoothstepf(0.0f, 0.012f, std::fabs(fractf(uv.y * 4.0f) - 0.5f) - 0.485f);

        Vec3 c = base * (0.72f + 0.5f * ring) * (0.9f + 0.2f * grain);
        c = tintVary(c, plankRand, 0.24f);
        float scuff = smoothstepf(0.6f, 0.85f, fbm2(Vec2(uv.x * 20.0f + seed, uv.y * 20.0f), 4)) * wear;
        c = lerp(c, Vec3(0.14f, 0.11f, 0.08f), scuff * 0.5f);
        c = lerp(c, Vec3(0.05f, 0.04f, 0.03f), seam * 0.85f);

        s.albedo = c;
        s.rough = saturate(0.55f + 0.2f * grain + scuff * 0.3f);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - seam * 0.6f - scuff * 0.2f);
        s.height = 0.65f + 0.12f * ring + 0.06f * grain - seam * 0.5f - scuff * 0.08f;
        return s;
    }, 1.8f);
}

void genFabric(int res, MatMaps& m, const Vec3& base, float weaveScale, float dirt, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float wx = std::sin(uv.x * weaveScale * TAU) * 0.5f + 0.5f;
        float wy = std::sin(uv.y * weaveScale * TAU) * 0.5f + 0.5f;
        float weave = std::max(wx, wy);
        float fuzz = fbm2(Vec2(uv.x * 300.0f + seed, uv.y * 300.0f), 3);
        float stain = spotStain(uv, 4.0f, seed + 2.0f, 0.52f) * dirt;
        float blood = spotStain(uv, 7.0f, seed + 11.0f, 0.74f) * dirt;
        float fold = fbm2(Vec2(uv.x * 5.0f + seed, uv.y * 5.0f), 5);

        Vec3 c = base * (0.78f + 0.3f * weave) * (0.92f + 0.16f * fuzz);
        c = c * (0.85f + 0.3f * fold);
        c = lerp(c, Vec3(0.26f, 0.22f, 0.15f), stain * 0.55f);
        c = lerp(c, Vec3(0.16f, 0.03f, 0.02f), blood * 0.75f);

        s.albedo = c;
        s.rough = saturate(0.92f - 0.06f * weave + stain * 0.05f);
        s.metal = 0.0f;
        s.ao = saturate(0.82f + 0.18f * weave - stain * 0.2f);
        s.height = 0.5f + 0.22f * weave + 0.08f * fuzz + 0.14f * fold;
        return s;
    }, 2.2f);
}

void genRubber(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float f2;
        float bumps = worley2(Vec2(uv.x * 60.0f + seed, uv.y * 60.0f), f2);
        float dot = smoothstepf(0.14f, 0.05f, bumps);
        float grime = fbm2(Vec2(uv.x * 5.0f + seed, uv.y * 5.0f), 5);
        Vec3 c(0.045f, 0.045f, 0.048f);
        c = c * (0.7f + 0.6f * grime) * (1.0f + dot * 0.4f);
        s.albedo = c;
        s.rough = saturate(0.86f - dot * 0.12f + grime * 0.1f);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - (1.0f - dot) * 0.2f);
        s.height = 0.45f + dot * 0.35f;
        return s;
    }, 2.4f);
}

void genPlastic(int res, MatMaps& m, const Vec3& base, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float micro = fbm2(Vec2(uv.x * 400.0f + seed, uv.y * 400.0f), 3);
        float yellowing = fbm2(Vec2(uv.x * 3.0f + seed, uv.y * 3.0f), 5);
        float scratch = smoothstepf(0.8f, 0.94f, fbm2(Vec2(uv.x * 260.0f + seed, uv.y * 30.0f), 3));
        Vec3 c = lerp(base, Vec3(0.52f, 0.46f, 0.32f), yellowing * 0.45f);
        c = c * (0.95f + 0.08f * micro);
        s.albedo = c;
        s.rough = saturate(0.32f + 0.14f * micro + scratch * 0.3f + yellowing * 0.15f);
        s.metal = 0.0f;
        s.ao = 1.0f;
        s.height = 0.6f + 0.03f * micro;
        return s;
    }, 0.9f);
}

void genGlass(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float dust = fbm2(Vec2(uv.x * 18.0f + seed, uv.y * 18.0f), 5);
        float streak = streaks(uv, 10.0f, seed);
        float crackL = cracks(uv, 7.0f, seed + 3.0f);
        s.albedo = Vec3(0.78f, 0.82f, 0.80f) * (0.9f + 0.2f * dust);
        s.albedo = lerp(s.albedo, Vec3(0.95f), crackL * 0.8f);
        s.rough = saturate(0.04f + dust * 0.35f + streak * 0.2f + crackL * 0.4f);
        s.metal = 0.0f;
        s.ao = 1.0f;
        s.height = 0.6f - crackL * 0.15f;
        return s;
    }, 1.2f);
}

void genPaper(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float fibre = fbm2(Vec2(uv.x * 220.0f + seed, uv.y * 220.0f), 4);
        float age = fbm2(Vec2(uv.x * 4.0f + seed, uv.y * 4.0f), 5);
        float edgeBurn = smoothstepf(0.35f, 0.02f, std::min(std::min(uv.x, 1.0f - uv.x), std::min(uv.y, 1.0f - uv.y)));
        Vec3 c(0.68f, 0.64f, 0.55f);
        c = c * (0.9f + 0.16f * fibre);
        c = lerp(c, Vec3(0.44f, 0.36f, 0.24f), age * 0.5f + edgeBurn * 0.55f);
        s.albedo = c;
        s.rough = saturate(0.9f + 0.08f * fibre);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - edgeBurn * 0.2f);
        s.height = 0.6f + 0.05f * fibre;
        return s;
    }, 1.0f);
}

void genLightPanel(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float ribs = std::sin(uv.x * TAU * 40.0f) * 0.5f + 0.5f;
        float dust = fbm2(Vec2(uv.x * 16.0f + seed, uv.y * 16.0f), 5);
        float bugs = smoothstepf(0.72f, 0.86f, fbm2(Vec2(uv.x * 30.0f + seed * 3.0f, uv.y * 30.0f), 4));
        Vec3 c(0.86f, 0.87f, 0.85f);
        c = c * (0.9f + 0.14f * ribs);
        c = lerp(c, Vec3(0.36f, 0.33f, 0.26f), dust * 0.45f);
        c = lerp(c, Vec3(0.10f, 0.08f, 0.06f), bugs * 0.7f);
        s.albedo = c;
        s.rough = saturate(0.3f + dust * 0.4f);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - bugs * 0.4f);
        s.height = 0.6f + 0.06f * ribs;
        return s;
    }, 1.4f);
}

void genServerRack(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float unit = fractf(uv.y * 14.0f);
        float gap = 1.0f - smoothstepf(0.0f, 0.06f, std::fabs(unit - 0.5f) - 0.42f);
        float vents = fractf(uv.x * 48.0f) < 0.55f ? 1.0f : 0.0f;
        float ventBand = smoothstepf(0.15f, 0.25f, unit) * (1.0f - smoothstepf(0.62f, 0.72f, unit));
        float dust = fbm2(Vec2(uv.x * 20.0f + seed, uv.y * 20.0f), 4);

        Vec3 body(0.045f, 0.047f, 0.05f);
        Vec3 dark(0.008f, 0.008f, 0.01f);
        s.albedo = lerp(body, dark, vents * ventBand * 0.85f);
        s.albedo = lerp(s.albedo, Vec3(0.15f, 0.15f, 0.14f), dust * 0.2f);
        s.albedo = lerp(s.albedo, Vec3(0.02f), gap * 0.8f);
        s.rough = saturate(0.55f + dust * 0.2f + vents * ventBand * 0.3f);
        s.metal = lerpf(0.6f, 0.0f, vents * ventBand);
        s.ao = saturate(1.0f - vents * ventBand * 0.5f - gap * 0.5f);
        s.height = 0.7f - vents * ventBand * 0.25f - gap * 0.4f;
        return s;
    }, 2.6f);
}

void genMorgueSteel(int res, MatMaps& m, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        Vec2 local, cell;
        float edge;
        tilePattern(uv, 3.0f, 4.0f, 0.03f, local, cell, edge);
        float seam = 1.0f - smoothstepf(0.0f, 0.03f, edge);
        float brush = fbm2(Vec2(uv.x * 600.0f + seed, uv.y * 5.0f), 3);
        float smudge = fbm2(Vec2(uv.x * 8.0f + seed, uv.y * 8.0f), 5);
        float handleBand = smoothstepf(0.42f, 0.46f, local.y) * (1.0f - smoothstepf(0.54f, 0.58f, local.y));
        float handle = handleBand * smoothstepf(0.3f, 0.36f, local.x) * (1.0f - smoothstepf(0.64f, 0.7f, local.x));

        Vec3 c(0.52f, 0.53f, 0.545f);
        c = c * (0.92f + 0.12f * brush);
        c = lerp(c, c * 0.7f, smudge * 0.35f);
        c = lerp(c, Vec3(0.14f), seam * 0.85f);
        c = lerp(c, Vec3(0.30f, 0.30f, 0.32f), handle * 0.8f);

        s.albedo = c;
        s.rough = saturate(0.24f + smudge * 0.28f + seam * 0.5f);
        s.metal = lerpf(1.0f, 0.4f, seam);
        s.ao = saturate(1.0f - seam * 0.6f - handle * 0.2f);
        s.height = 0.72f - seam * 0.45f + handle * 0.12f;
        return s;
    }, 2.0f);
}

void genSkin(int res, MatMaps& m, const Vec3& base, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float pores = fbm2(Vec2(uv.x * 420.0f + seed, uv.y * 420.0f), 3);
        float blotch = fbm2(Vec2(uv.x * 9.0f + seed, uv.y * 9.0f), 5);
        float vein = fbm2(Vec2(uv.x * 22.0f + seed * 2.0f, uv.y * 22.0f), 4);
        float pale = smoothstepf(0.42f, 0.72f, blotch);
        Vec3 c = base * (0.90f + 0.16f * pores);
        c = lerp(c, base * Vec3(0.86f, 0.92f, 0.98f), pale * 0.55f);
        c = lerp(c, base * Vec3(0.78f, 0.70f, 0.76f), smoothstepf(0.55f, 0.85f, vein) * 0.30f);
        s.albedo = c;
        s.rough = saturate(0.46f + 0.22f * pores + pale * 0.12f);
        s.metal = 0.0f;
        s.ao = saturate(1.0f - blotch * 0.10f);
        s.height = 0.6f + 0.05f * pores + 0.03f * blotch;
        return s;
    }, 1.1f);
}

void genHair(int res, MatMaps& m, const Vec3& base, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float strand = fbm2(Vec2(uv.x * 620.0f + seed, uv.y * 14.0f), 4);
        float clump = fbm2(Vec2(uv.x * 60.0f + seed, uv.y * 8.0f), 4);
        float grey = smoothstepf(0.62f, 0.88f, clump);
        Vec3 c = base * (0.6f + 0.9f * strand);
        c = lerp(c, Vec3(0.26f, 0.25f, 0.24f), grey * 0.5f);
        s.albedo = c;
        s.rough = saturate(0.34f + 0.3f * strand);
        s.metal = 0.0f;
        s.ao = saturate(0.72f + 0.28f * strand);
        s.height = 0.5f + 0.4f * strand;
        return s;
    }, 2.4f);
}

void genCloth(int res, MatMaps& m, const Vec3& base, float seed) {
    generateMaps(res, m, [&](const Vec2& uv, int x, int y) -> Sample {
        Sample s;
        float weave = std::max(std::sin(uv.x * 220.0f * TAU) * 0.5f + 0.5f, std::sin(uv.y * 220.0f * TAU) * 0.5f + 0.5f);
        float fold = fbm2(Vec2(uv.x * 7.0f + seed, uv.y * 7.0f), 5);
        float wear = fbm2(Vec2(uv.x * 3.0f + seed * 2.0f, uv.y * 3.0f), 5);
        float stain = smoothstepf(0.60f, 0.86f, fbm2(Vec2(uv.x * 5.0f + seed * 3.0f, uv.y * 5.0f), 4));
        float blood = smoothstepf(0.78f, 0.94f, fbm2(Vec2(uv.x * 8.0f + seed * 5.0f, uv.y * 8.0f), 4));
        Vec3 c = base * (0.86f + 0.24f * fold) * (0.94f + 0.10f * weave);
        c = lerp(c, Vec3(0.24f, 0.21f, 0.16f), stain * 0.55f * wear);
        c = lerp(c, Vec3(0.14f, 0.032f, 0.026f), blood * 0.45f);
        s.albedo = c;
        s.rough = saturate(0.86f - 0.06f * weave + stain * 0.06f);
        s.metal = 0.0f;
        s.ao = saturate(0.86f + 0.14f * weave - fold * 0.12f);
        s.height = 0.5f + 0.24f * fold + 0.10f * weave;
        return s;
    }, 1.8f);
}

void buildBlueNoise(Image& img, int size) {
    img.allocate(size, size, 1);
    Rng rng(0xB10E0F51);
    std::vector<float> v((size_t)size * size);
    for (auto& x : v) x = rng.nextFloat();

    auto energy = [&](int cx, int cy) {
        float e = 0.0f;
        const int R = 4;
        float center = v[(size_t)cy * size + cx];
        for (int dy = -R; dy <= R; dy++) {
            for (int dx = -R; dx <= R; dx++) {
                if (dx == 0 && dy == 0) continue;
                int nx = ((cx + dx) % size + size) % size;
                int ny = ((cy + dy) % size + size) % size;
                float d2 = (float)(dx * dx + dy * dy);
                float diff = center - v[(size_t)ny * size + nx];
                e += std::exp(-d2 / 4.5f) * std::exp(-std::fabs(diff) * 2.0f);
            }
        }
        return e;
    };

    int iterations = size * size * 12;
    for (int i = 0; i < iterations; i++) {
        int ax = rng.rangeInt(0, size), ay = rng.rangeInt(0, size);
        int bx = rng.rangeInt(0, size), by = rng.rangeInt(0, size);
        if (ax == bx && ay == by) continue;
        float before = energy(ax, ay) + energy(bx, by);
        std::swap(v[(size_t)ay * size + ax], v[(size_t)by * size + bx]);
        float after = energy(ax, ay) + energy(bx, by);
        if (after > before) std::swap(v[(size_t)ay * size + ax], v[(size_t)by * size + bx]);
    }
    for (int i = 0; i < size * size; i++) img.data[i] = (u8)(saturate(v[i]) * 255.0f);
}

void buildDetailNoise(Image& img, int size) {
    img.allocate(size, size, 4);
    parallelFor(size, [&](int y) {
        for (int x = 0; x < size; x++) {
            Vec2 uv((float)x / size, (float)y / size);
            float a = fbm2(uv * 8.0f, 6);
            float b = fbm2(uv * 24.0f + Vec2(31.0f, 17.0f), 5);
            float f2;
            float c = 1.0f - worley2(uv * 12.0f + Vec2(7.0f, 3.0f), f2);
            float d = hash21(Vec2((float)x, (float)y) * 1.37f);
            img.set(x, y, Vec4(a, b, saturate(c), d));
        }
    });
}

}

void MaterialLibrary::generate(int resolution) {
    Clock clock;
    res = resolution;

    std::vector<MatMaps> maps((size_t)MAT_COUNT);

    auto gen = [&](int id) {
        MatMaps& m = maps[(size_t)id];
        switch (id) {
        case MAT_TILE_WALL:       genTileWall(res, m, Vec3(0.145f, 0.205f, 0.195f), 0.75f, 11.0f); break;
        case MAT_TILE_WALL_GREEN: genTileWall(res, m, Vec3(0.105f, 0.185f, 0.150f), 0.85f, 23.0f); break;
        case MAT_TILE_WALL_WHITE: genTileWall(res, m, Vec3(0.395f, 0.400f, 0.380f), 0.80f, 37.0f); break;
        case MAT_PLASTER:         genPlaster(res, m, Vec3(0.400f, 0.395f, 0.360f), 0.80f, 5.0f); break;
        case MAT_PAINT_WALL:      genPlaster(res, m, Vec3(0.230f, 0.290f, 0.270f), 0.65f, 41.0f); break;
        case MAT_CONCRETE_WALL:   genConcrete(res, m, Vec3(0.230f, 0.228f, 0.220f), 0.0f, 13.0f); break;
        case MAT_FLOOR_CHECKER:   genCheckerFloor(res, m, 17.0f); break;
        case MAT_FLOOR_LINO:      genLinoleum(res, m, Vec3(0.240f, 0.245f, 0.225f), 29.0f); break;
        case MAT_CONCRETE_FLOOR:  genConcrete(res, m, Vec3(0.180f, 0.180f, 0.175f), 0.85f, 31.0f); break;
        case MAT_TILE_FLOOR_SMALL:genTileWall(res, m, Vec3(0.300f, 0.300f, 0.285f), 0.90f, 43.0f); break;
        case MAT_CEILING_TILE:    genCeilingTile(res, m, 19.0f); break;
        case MAT_CEILING_CONCRETE:genConcrete(res, m, Vec3(0.200f, 0.198f, 0.192f), 0.0f, 47.0f); break;
        case MAT_METAL_PAINTED:   genPaintedMetal(res, m, Vec3(0.235f, 0.290f, 0.278f), 0.42f, 7.0f); break;
        case MAT_METAL_RUST:      genPaintedMetal(res, m, Vec3(0.200f, 0.195f, 0.185f), 0.95f, 53.0f); break;
        case MAT_STEEL:           genSteel(res, m, 0.55f, 3.0f); break;
        case MAT_VENT_GRATE:      genVentGrate(res, m, 59.0f); break;
        case MAT_WOOD_DOOR:       genWood(res, m, Vec3(0.330f, 0.218f, 0.125f), 0.65f, 61.0f); break;
        case MAT_WOOD_OLD:        genWood(res, m, Vec3(0.160f, 0.115f, 0.070f), 0.95f, 67.0f); break;
        case MAT_DOOR_GREEN:      genPaintedMetal(res, m, Vec3(0.130f, 0.335f, 0.245f), 0.32f, 71.0f); break;
        case MAT_DOOR_METAL:      genPaintedMetal(res, m, Vec3(0.400f, 0.406f, 0.388f), 0.50f, 73.0f); break;
        case MAT_FABRIC:          genFabric(res, m, Vec3(0.180f, 0.200f, 0.215f), 90.0f, 0.75f, 79.0f); break;
        case MAT_MATTRESS:        genFabric(res, m, Vec3(0.248f, 0.240f, 0.218f), 60.0f, 1.0f, 83.0f); break;
        case MAT_CURTAIN:         genFabric(res, m, Vec3(0.220f, 0.290f, 0.280f), 130.0f, 0.55f, 89.0f); break;
        case MAT_RUBBER:          genRubber(res, m, 97.0f); break;
        case MAT_PLASTIC_WHITE:   genPlastic(res, m, Vec3(0.395f, 0.392f, 0.368f), 101.0f); break;
        case MAT_GLASS:           genGlass(res, m, 103.0f); break;
        case MAT_PAPER:           genPaper(res, m, 107.0f); break;
        case MAT_MORGUE_STEEL:    genMorgueSteel(res, m, 109.0f); break;
        case MAT_SERVER_RACK:     genServerRack(res, m, 113.0f); break;
        case MAT_LIGHT_PANEL:     genLightPanel(res, m, 127.0f); break;
        case MAT_SKIN:            genSkin(res, m, Vec3(0.560f, 0.430f, 0.380f), 131.0f); break;
        case MAT_HAIR:            genHair(res, m, Vec3(0.055f, 0.042f, 0.036f), 137.0f); break;
        case MAT_CLOTH_WHITE:     genCloth(res, m, Vec3(0.520f, 0.516f, 0.498f), 139.0f); break;
        case MAT_CLOTH_SCRUB:     genCloth(res, m, Vec3(0.105f, 0.190f, 0.205f), 149.0f); break;
        default:                  genConcrete(res, m, Vec3(0.3f), 0.0f, 1.0f); break;
        }
    };

    parallelFor((int)MAT_COUNT, gen);

    TextureDesc ad;
    ad.target = GL_TEXTURE_2D_ARRAY;
    ad.width = res; ad.height = res; ad.depth = MAT_COUNT;
    ad.internalFormat = GL_SRGB8_ALPHA8;
    ad.format = GL_RGBA;
    ad.type = GL_UNSIGNED_BYTE;
    ad.wrap = GL_REPEAT;
    ad.mipmaps = true;
    albedo = std::make_shared<Texture>();
    albedo->create(ad, nullptr);

    TextureDesc nd = ad;
    nd.internalFormat = GL_RGB8;
    nd.format = GL_RGB;
    normal = std::make_shared<Texture>();
    normal->create(nd, nullptr);

    orm = std::make_shared<Texture>();
    orm->create(nd, nullptr);

    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    for (int i = 0; i < MAT_COUNT; i++) {
        albedo->updateLayer(maps[(size_t)i].albedo.data.data(), i);
        normal->updateLayer(maps[(size_t)i].normal.data.data(), i);
        orm->updateLayer(maps[(size_t)i].orm.data.data(), i);
    }
    glPixelStorei(GL_UNPACK_ALIGNMENT, 4);

    albedo->generateMips();
    normal->generateMips();
    orm->generateMips();

    for (int i = 0; i < MAT_COUNT; i++) {
        defs[i] = MaterialDef();
        defs[i].layer = i;
    }

    defs[MAT_TILE_WALL].uvScale = Vec2(0.85f, 0.85f);
    defs[MAT_TILE_WALL_GREEN].uvScale = Vec2(0.85f, 0.85f);
    defs[MAT_TILE_WALL_WHITE].uvScale = Vec2(0.9f, 0.9f);
    defs[MAT_PLASTER].uvScale = Vec2(0.62f, 0.62f);
    defs[MAT_PAINT_WALL].uvScale = Vec2(0.58f, 0.58f);
    defs[MAT_CONCRETE_WALL].uvScale = Vec2(0.52f, 0.52f);
    defs[MAT_FLOOR_CHECKER].uvScale = Vec2(0.4166f, 0.4166f);
    defs[MAT_FLOOR_LINO].uvScale = Vec2(0.34f, 0.34f);
    defs[MAT_CONCRETE_FLOOR].uvScale = Vec2(0.26f, 0.26f);
    defs[MAT_CONCRETE_FLOOR].wetness = 0.6f;
    defs[MAT_TILE_FLOOR_SMALL].uvScale = Vec2(1.6f, 1.6f);
    defs[MAT_CEILING_TILE].uvScale = Vec2(0.834f, 0.834f);
    defs[MAT_CEILING_CONCRETE].uvScale = Vec2(0.26f, 0.26f);
    defs[MAT_METAL_PAINTED].uvScale = Vec2(0.5f, 0.5f);
    defs[MAT_METAL_RUST].uvScale = Vec2(0.45f, 0.45f);
    defs[MAT_STEEL].uvScale = Vec2(0.7f, 0.7f);
    defs[MAT_VENT_GRATE].uvScale = Vec2(2.0f, 2.0f);
    defs[MAT_WOOD_DOOR].uvScale = Vec2(0.55f, 0.55f);
    defs[MAT_WOOD_OLD].uvScale = Vec2(0.6f, 0.6f);
    defs[MAT_DOOR_GREEN].uvScale = Vec2(0.5f, 0.5f);
    defs[MAT_DOOR_METAL].uvScale = Vec2(0.5f, 0.5f);
    defs[MAT_FABRIC].uvScale = Vec2(1.2f, 1.2f);
    defs[MAT_MATTRESS].uvScale = Vec2(1.4f, 1.4f);
    defs[MAT_CURTAIN].uvScale = Vec2(0.8f, 0.8f);
    defs[MAT_RUBBER].uvScale = Vec2(1.5f, 1.5f);
    defs[MAT_PLASTIC_WHITE].uvScale = Vec2(1.0f, 1.0f);
    defs[MAT_GLASS].uvScale = Vec2(0.4f, 0.4f);
    defs[MAT_GLASS].transparent = true;
    defs[MAT_GLASS].alpha = 0.22f;
    defs[MAT_GLASS].doubleSided = true;
    defs[MAT_PAPER].uvScale = Vec2(2.5f, 2.5f);
    defs[MAT_MORGUE_STEEL].uvScale = Vec2(0.55f, 0.55f);
    defs[MAT_SERVER_RACK].uvScale = Vec2(0.5f, 0.5f);
    defs[MAT_LIGHT_PANEL].uvScale = Vec2(0.8f, 0.8f);
    defs[MAT_LIGHT_PANEL].emissive = Vec3(1.0f, 0.96f, 0.88f);
    defs[MAT_LIGHT_PANEL].emissiveStrength = 0.85f;
    defs[MAT_SKIN].uvScale = Vec2(1.1f, 1.1f);
    defs[MAT_HAIR].uvScale = Vec2(2.2f, 2.2f);
    defs[MAT_CLOTH_WHITE].uvScale = Vec2(1.5f, 1.5f);
    defs[MAT_CLOTH_SCRUB].uvScale = Vec2(1.5f, 1.5f);

    Image bn;
    buildBlueNoise(bn, 64);
    blueNoise = makeTexture2D(bn, false, false, GL_REPEAT);
    glBindTexture(GL_TEXTURE_2D, blueNoise->id());
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glBindTexture(GL_TEXTURE_2D, 0);

    Image dn;
    buildDetailNoise(dn, 256);
    noise = makeTexture2D(dn, false, true, GL_REPEAT);

    LOG_INFO("Generated %d procedural materials at %dpx in %.2fs", (int)MAT_COUNT, res, clock.elapsed());
}

void MaterialLibrary::destroy() {
    albedo.reset();
    normal.reset();
    orm.reset();
    noise.reset();
    blueNoise.reset();
}

void MaterialLibrary::bind(int albedoUnit, int normalUnit, int ormUnit) const {
    if (albedo) albedo->bind(albedoUnit);
    if (normal) normal->bind(normalUnit);
    if (orm) orm->bind(ormUnit);
}

void MaterialLibrary::uploadUniforms(Shader& shader) const {
    float a[MAT_COUNT * 4];
    float b[MAT_COUNT * 4];
    float c[MAT_COUNT * 4];
    for (int i = 0; i < MAT_COUNT; i++) {
        a[i * 4 + 0] = defs[i].uvScale.x;
        a[i * 4 + 1] = defs[i].uvScale.y;
        a[i * 4 + 2] = defs[i].wetness;
        a[i * 4 + 3] = (float)defs[i].layer;
        b[i * 4 + 0] = defs[i].tint.x;
        b[i * 4 + 1] = defs[i].tint.y;
        b[i * 4 + 2] = defs[i].tint.z;
        b[i * 4 + 3] = defs[i].emissiveStrength;
        c[i * 4 + 0] = defs[i].roughnessScale;
        c[i * 4 + 1] = defs[i].metallicScale;
        c[i * 4 + 2] = defs[i].normalStrength;
        c[i * 4 + 3] = defs[i].alpha;
    }
    shader.setVec4Array("uMatA", a, MAT_COUNT);
    shader.setVec4Array("uMatB", b, MAT_COUNT);
    shader.setVec4Array("uMatC", c, MAT_COUNT);
}

}
