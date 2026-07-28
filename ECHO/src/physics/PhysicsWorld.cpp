#include "PhysicsWorld.h"

using namespace em;

namespace echo {

void PhysicsWorld::clear() {
    colliders.clear();
    grid.clear();
    worldBounds = AABB();
    gridW = gridH = 0;
    dirty = true;
}

int PhysicsWorld::addCollider(const Collider& c) {
    colliders.push_back(c);
    dirty = true;
    return (int)colliders.size() - 1;
}

void PhysicsWorld::updateCollider(int index, const Collider& c) {
    if (index < 0 || index >= (int)colliders.size()) return;
    colliders[(size_t)index] = c;
    dirty = true;
}

void PhysicsWorld::setEnabled(int index, bool enabled) {
    if (index < 0 || index >= (int)colliders.size()) return;
    colliders[(size_t)index].enabled = enabled;
}

Collider* PhysicsWorld::collider(int index) {
    if (index < 0 || index >= (int)colliders.size()) return nullptr;
    return &colliders[(size_t)index];
}

const Collider* PhysicsWorld::collider(int index) const {
    if (index < 0 || index >= (int)colliders.size()) return nullptr;
    return &colliders[(size_t)index];
}

int PhysicsWorld::cellIndex(int cx, int cz) const {
    return cz * gridW + cx;
}

void PhysicsWorld::cellRange(const AABB& b, int& x0, int& z0, int& x1, int& z1) const {
    x0 = clampi((int)std::floor((b.mn.x - worldBounds.mn.x) / cellSize), 0, gridW - 1);
    x1 = clampi((int)std::floor((b.mx.x - worldBounds.mn.x) / cellSize), 0, gridW - 1);
    z0 = clampi((int)std::floor((b.mn.z - worldBounds.mn.z) / cellSize), 0, gridH - 1);
    z1 = clampi((int)std::floor((b.mx.z - worldBounds.mn.z) / cellSize), 0, gridH - 1);
}

void PhysicsWorld::rebuildGrid() {
    worldBounds = AABB();
    for (const auto& c : colliders) worldBounds.expand(c.worldBounds());
    if (!worldBounds.valid()) {
        grid.clear();
        gridW = gridH = 0;
        dirty = false;
        return;
    }
    worldBounds.grow(2.0f);

    gridW = clampi((int)std::ceil(worldBounds.size().x / cellSize), 1, 512);
    gridH = clampi((int)std::ceil(worldBounds.size().z / cellSize), 1, 512);
    cellSize = std::max(worldBounds.size().x / gridW, worldBounds.size().z / gridH);
    cellSize = std::max(cellSize, 1.0f);
    gridW = clampi((int)std::ceil(worldBounds.size().x / cellSize) + 1, 1, 512);
    gridH = clampi((int)std::ceil(worldBounds.size().z / cellSize) + 1, 1, 512);

    grid.assign((size_t)gridW * gridH, Cell());
    for (int i = 0; i < (int)colliders.size(); i++) {
        AABB b = colliders[(size_t)i].worldBounds();
        int x0, z0, x1, z1;
        cellRange(b, x0, z0, x1, z1);
        for (int z = z0; z <= z1; z++)
            for (int x = x0; x <= x1; x++)
                grid[(size_t)cellIndex(x, z)].items.push_back(i);
    }
    dirty = false;
}

void PhysicsWorld::queryRegion(const AABB& region, std::vector<int>& out) const {
    out.clear();
    if (grid.empty()) {
        for (int i = 0; i < (int)colliders.size(); i++) out.push_back(i);
        return;
    }
    int x0, z0, x1, z1;
    cellRange(region, x0, z0, x1, z1);
    static thread_local std::vector<u8> seen;
    seen.assign(colliders.size(), 0);
    for (int z = z0; z <= z1; z++) {
        for (int x = x0; x <= x1; x++) {
            for (int idx : grid[(size_t)cellIndex(x, z)].items) {
                if (seen[(size_t)idx]) continue;
                seen[(size_t)idx] = 1;
                out.push_back(idx);
            }
        }
    }
}

RayHit PhysicsWorld::raycast(const Vec3& origin, const Vec3& dir, float maxDist, u32 ignoreFlags) const {
    RayHit hit;
    hit.distance = maxDist;

    Vec3 d = normalize(dir);
    AABB region;
    region.expand(origin);
    region.expand(origin + d * maxDist);
    region.grow(0.2f);

    std::vector<int> candidates;
    queryRegion(region, candidates);

    for (int idx : candidates) {
        const Collider& c = colliders[(size_t)idx];
        if (!c.enabled) continue;
        if (ignoreFlags && (c.flags & ignoreFlags)) continue;
        float t;
        Vec3 n;
        if (rayCollider(origin, d, c, hit.distance, t, n)) {
            if (t >= 0.0f && t < hit.distance) {
                hit.hit = true;
                hit.distance = t;
                hit.normal = n;
                hit.point = origin + d * t;
                hit.owner = c.owner;
                hit.flags = c.flags;
                hit.colliderIndex = idx;
            }
        }
    }
    return hit;
}

bool PhysicsWorld::lineOfSight(const Vec3& a, const Vec3& b) const {
    Vec3 d = b - a;
    float len = length(d);
    if (len < 1e-4f) return true;
    RayHit h = raycast(a, d / len, len, COL_TRIGGER | COL_CHARACTER);
    return !h.hit;
}

bool PhysicsWorld::overlapCapsule(const Vec3& base, const Vec3& top, float radius, u32 mask) const {
    AABB region(minv(base, top) - Vec3(radius), maxv(base, top) + Vec3(radius));
    std::vector<int> candidates;
    queryRegion(region, candidates);
    for (int idx : candidates) {
        const Collider& c = colliders[(size_t)idx];
        if (!c.enabled || !(c.flags & mask)) continue;
        if (c.flags & COL_TRIGGER) continue;
        Vec3 n;
        float depth;
        if (capsuleCollider(base, top, radius, c, n, depth)) return true;
    }
    return false;
}

Vec3 PhysicsWorld::resolveCapsule(const Vec3& position, float radius, float height, int iterations, Vec3& groundNormalOut, bool& groundedOut) const {
    Vec3 pos = position;
    groundedOut = false;
    groundNormalOut = Vec3(0, 1, 0);

    float cylHeight = std::max(height - radius * 2.0f, 0.01f);

    for (int it = 0; it < iterations; it++) {
        Vec3 base = pos + Vec3(0, radius, 0);
        Vec3 top = pos + Vec3(0, radius + cylHeight, 0);

        AABB region(minv(base, top) - Vec3(radius + 0.1f), maxv(base, top) + Vec3(radius + 0.1f));
        std::vector<int> candidates;
        queryRegion(region, candidates);

        bool any = false;
        for (int idx : candidates) {
            const Collider& c = colliders[(size_t)idx];
            if (!c.enabled) continue;
            if (c.flags & COL_TRIGGER) continue;

            Vec3 lb = pos + Vec3(0, radius, 0);
            Vec3 lt = pos + Vec3(0, radius + cylHeight, 0);
            Vec3 n;
            float depth;
            if (!capsuleCollider(lb, lt, radius, c, n, depth)) continue;
            if (depth <= 1e-5f) continue;

            pos += n * (depth + 0.0008f);
            any = true;

            if (n.y > 0.55f) {
                groundedOut = true;
                groundNormalOut = n;
            }
        }
        if (!any) break;
    }
    return pos;
}

float PhysicsWorld::floorHeightAt(const Vec3& position, float searchUp, float searchDown, bool& found) const {
    Vec3 origin = position + Vec3(0, searchUp, 0);
    RayHit h = raycast(origin, Vec3(0, -1, 0), searchUp + searchDown, COL_TRIGGER);
    found = h.hit;
    return h.hit ? h.point.y : position.y;
}

}
