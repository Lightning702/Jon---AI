#pragma once

#include "../../engine/core/Types.hpp"
#include "../../engine/math/Random.hpp"

namespace sf {

struct GalaxyCoord {
    i64 x = 0;
    i64 y = 0;
    i64 z = 0;

    bool operator==(const GalaxyCoord& other) const { return x == other.x && y == other.y && z == other.z; }
    bool operator!=(const GalaxyCoord& other) const { return !(*this == other); }
};

struct SystemCoord {
    i64 x = 0;
    i64 y = 0;
    i64 z = 0;

    bool operator==(const SystemCoord& other) const { return x == other.x && y == other.y && z == other.z; }
    bool operator!=(const SystemCoord& other) const { return !(*this == other); }
    u64 key() const {
        return hashCoordinate(0x5EED0BADC0FFEEull, x, y, z);
    }
};

class UniverseSeed {
public:
    explicit UniverseSeed(u64 rootSeed = 0x5741524653414C4Cull) : root(rootSeed) {}

    u64 value() const { return root; }
    void setValue(u64 rootSeed) { root = rootSeed; }

    u64 galaxySeed(u32 galaxyIndex) const { return hashCombine(root, static_cast<u64>(galaxyIndex) + 0x9E37u); }
    u64 systemSeed(u64 galaxy, const SystemCoord& coordinate) const {
        return hashCoordinate(galaxy, coordinate.x, coordinate.y, coordinate.z);
    }
    u64 planetSeed(u64 system, u32 planetIndex) const {
        return hashCombine(system, static_cast<u64>(planetIndex) + 0x1F1Fu);
    }
    u64 moonSeed(u64 planet, u32 moonIndex) const {
        return hashCombine(planet, static_cast<u64>(moonIndex) + 0x7A2Bu);
    }
    u64 chunkSeed(u64 planet, u32 face, u32 level, i64 tileX, i64 tileY) const {
        u64 hash = hashCombine(planet, static_cast<u64>(face) * 131u + level);
        return hashCoordinate(hash, tileX, tileY, static_cast<i64>(level));
    }
    u64 featureSeed(u64 parent, const char* label) const {
        u64 hash = parent;
        for (const char* cursor = label; *cursor; ++cursor) {
            hash = hashCombine(hash, static_cast<u64>(static_cast<u8>(*cursor)));
        }
        return hash;
    }

private:
    u64 root;
};

}
