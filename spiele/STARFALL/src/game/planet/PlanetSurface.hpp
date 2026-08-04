#pragma once

#include "../../engine/math/Frustum.hpp"
#include "TerrainChunk.hpp"

#include <memory>
#include <string>
#include <vector>

namespace sf {

struct ScatterInstance {
    DVec3 localPosition = DVec3::zero();
    DVec3 upDirection = DVec3::unitY();
    f32 scale = 1.0f;
    f32 rotation = 0.0f;
    Vec3 tint = Vec3(0.3f, 0.5f, 0.2f);
    u32 kind = 0;
};

struct ResourceNode {
    DVec3 localPosition = DVec3::zero();
    DVec3 upDirection = DVec3::unitY();
    ItemId resource = ItemId::Ferrite;
    f32 radiusMeters = 2.4f;
    u32 remainingUnits = 240;
    bool depleted = false;
};

struct CreatureInstance {
    DVec3 localPosition = DVec3::zero();
    DVec3 heading = DVec3::unitX();
    f32 scale = 1.0f;
    f32 speed = 2.0f;
    f32 wanderTimer = 0.0f;
    u32 speciesIndex = 0;
    bool scanned = false;
};

class PlanetSurface {
public:
    void configure(const PlanetBody& body, u32 maximumLevel, f32 splitFactor);
    void release();

    void prime(const DVec3& viewerLocalPosition, f64 dayPhase, u32 chunkLimit);
    void update(const DVec3& viewerLocalPosition, f64 dayPhase, u32 chunkBudgetPerFrame, f32 detailScale);
    void updateLife(f64 stepSeconds, const DVec3& viewerLocalPosition);

    void collectVisible(const DVec3& renderOrigin, const Frustum& frustum,
                        std::vector<const TerrainChunk*>& out) const;

    const std::vector<ScatterInstance>& scatter() const { return scatterInstances; }
    const std::vector<ResourceNode>& resources() const { return resourceNodes; }
    std::vector<ResourceNode>& mutableResources() { return resourceNodes; }
    const std::vector<CreatureInstance>& creatures() const { return creatureInstances; }
    std::vector<CreatureInstance>& mutableCreatures() { return creatureInstances; }

    ResourceNode* nearestResource(const DVec3& localPosition, f64 maximumDistance);
    CreatureInstance* nearestCreature(const DVec3& localPosition, f64 maximumDistance);

    u32 loadedChunks() const { return static_cast<u32>(nodes.size()); }
    u32 drawnTriangles() const { return lastDrawnTriangles; }
    u32 deepestLevel() const;
    u32 leafCount() const;
    f64 finestChunkMeters() const;
    const PlanetBody& body() const { return planetBody; }

private:
    struct Node {
        u32 face = 0;
        u32 level = 0;
        f64 originU = 0.0;
        f64 originV = 0.0;
        f64 size = 1.0;
        DVec3 centerDirection = DVec3::unitY();
        DVec3 centerLocalPosition = DVec3::zero();
        f64 worldSize = 0.0;
        TerrainChunk chunk;
        bool hasChildren = false;
        u32 children[4] = {kInvalidIndex32, kInvalidIndex32, kInvalidIndex32, kInvalidIndex32};
        bool needsUpload = false;
        TerrainGeometry pending;
    };

    u32 createNode(u32 face, u32 level, f64 originU, f64 originV, f64 size);
    void refine(u32 nodeIndex, const DVec3& viewerLocalPosition, f64 dayPhase, u32& budget, f32 detailScale);
    void collapse(u32 nodeIndex);
    void gatherLeaves(u32 nodeIndex, std::vector<u32>& out) const;
    void populateSurfaceFeatures();

    PlanetBody planetBody;
    std::vector<std::unique_ptr<Node>> nodes;
    u32 roots[6] = {};
    std::vector<ScatterInstance> scatterInstances;
    std::vector<ResourceNode> resourceNodes;
    std::vector<CreatureInstance> creatureInstances;
    DVec3 featureAnchor = DVec3::zero();
    u32 maximumSubdivision = 14;
    f32 splitDistanceFactor = 2.6f;
    mutable u32 lastDrawnTriangles = 0;
    bool featuresValid = false;
};

}
