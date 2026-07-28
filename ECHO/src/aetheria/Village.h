#pragma once

#include "Terrain.h"

namespace aeth {

enum BuildingType {
    BUILD_COTTAGE = 0,
    BUILD_LONGHOUSE,
    BUILD_TOWER,
    BUILD_WELL,
    BUILD_STALL,
    BUILD_FENCE,
    BUILD_BANNER,
    BUILD_CAMPFIRE,
    BUILD_SHRINE,
    BUILD_RUIN_ARCH,
    BUILD_STANDING_STONE,
    BUILD_SIGNPOST,
    BUILD_COUNT
};

struct BuildingMesh {
    echo::Mesh mesh;
    em::AABB bounds;
    em::Vec2 blockHalf = em::Vec2(0, 0);
    float blockHeight = 0.0f;
    bool lit = false;
    em::Vec3 lightOffset;
    em::Vec3 lightColor = em::Vec3(1.0f, 0.72f, 0.42f);
    float lightRange = 9.0f;
};

struct BuildingInstance {
    u16 type = 0;
    em::Vec3 position;
    float yaw = 0.0f;
    float scale = 1.0f;
    float tint = 1.0f;
};

struct BoxCollider {
    em::Vec2 center;
    em::Vec2 half;
    float sinYaw = 0.0f;
    float cosYaw = 1.0f;
};

class BuildingLibrary {
public:
    void build();
    void destroy();
    const BuildingMesh& get(int type) const { return meshes[type < 0 || type >= BUILD_COUNT ? 0 : type]; }

private:
    BuildingMesh meshes[BUILD_COUNT];
};

em::Vec2 resolveBoxes(const std::vector<BoxCollider>& boxes, const em::Vec2& point, float radius);

}
