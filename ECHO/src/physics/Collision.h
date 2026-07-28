#pragma once

#include "../core/Math.h"

namespace echo {

enum ColliderFlags {
    COL_STATIC = 1 << 0,
    COL_DOOR = 1 << 1,
    COL_PROP = 1 << 2,
    COL_INTERACTABLE = 1 << 3,
    COL_BLOCKS_SIGHT = 1 << 4,
    COL_TRIGGER = 1 << 5,
    COL_CHARACTER = 1 << 6
};

struct Collider {
    em::Vec3 center;
    em::Vec3 half;
    float yaw = 0.0f;
    u32 owner = 0;
    u32 flags = COL_STATIC;
    bool enabled = true;

    em::AABB worldBounds() const;
    em::Vec3 toLocal(const em::Vec3& p) const;
    em::Vec3 toWorld(const em::Vec3& p) const;
    em::Vec3 closestPoint(const em::Vec3& p) const;
    bool containsPoint(const em::Vec3& p) const;
};

struct RayHit {
    bool hit = false;
    float distance = 0.0f;
    em::Vec3 point;
    em::Vec3 normal;
    u32 owner = 0;
    u32 flags = 0;
    int colliderIndex = -1;
};

struct SweepHit {
    bool hit = false;
    float t = 1.0f;
    em::Vec3 normal;
    int colliderIndex = -1;
};

bool rayAABB(const em::Vec3& origin, const em::Vec3& dir, const em::AABB& box, float maxDist, float& tOut, em::Vec3& nOut);
bool rayCollider(const em::Vec3& origin, const em::Vec3& dir, const Collider& c, float maxDist, float& tOut, em::Vec3& nOut);
bool sphereCollider(const em::Vec3& center, float radius, const Collider& c, em::Vec3& normalOut, float& depthOut);
bool capsuleCollider(const em::Vec3& base, const em::Vec3& top, float radius, const Collider& c, em::Vec3& normalOut, float& depthOut);
bool segmentCollider(const em::Vec3& a, const em::Vec3& b, const Collider& c);

}
