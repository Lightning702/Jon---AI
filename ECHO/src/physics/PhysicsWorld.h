#pragma once

#include "Collision.h"

namespace echo {

class PhysicsWorld {
public:
    void clear();
    int addCollider(const Collider& c);
    void updateCollider(int index, const Collider& c);
    void setEnabled(int index, bool enabled);
    Collider* collider(int index);
    const Collider* collider(int index) const;
    int colliderCount() const { return (int)colliders.size(); }

    void rebuildGrid();

    RayHit raycast(const em::Vec3& origin, const em::Vec3& dir, float maxDist, u32 ignoreFlags = 0) const;
    bool lineOfSight(const em::Vec3& a, const em::Vec3& b) const;
    bool overlapCapsule(const em::Vec3& base, const em::Vec3& top, float radius, u32 mask = 0xFFFFFFFF) const;

    em::Vec3 resolveCapsule(const em::Vec3& position, float radius, float height, int iterations, em::Vec3& groundNormalOut, bool& groundedOut) const;
    void queryRegion(const em::AABB& region, std::vector<int>& out) const;

    float floorHeightAt(const em::Vec3& position, float searchUp, float searchDown, bool& found) const;

private:
    struct Cell {
        std::vector<int> items;
    };
    int cellIndex(int cx, int cz) const;
    void cellRange(const em::AABB& b, int& x0, int& z0, int& x1, int& z1) const;

    std::vector<Collider> colliders;
    std::vector<Cell> grid;
    em::AABB worldBounds;
    float cellSize = 4.0f;
    int gridW = 0, gridH = 0;
    bool dirty = true;
};

}
