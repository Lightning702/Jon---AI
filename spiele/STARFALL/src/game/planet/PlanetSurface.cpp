#include "PlanetSurface.hpp"

#include "../../engine/math/Random.hpp"
#include "../../engine/math/Scalar.hpp"
#include "../../engine/math/SphericalCoords.hpp"

namespace sf {
namespace {

constexpr f64 kFeatureRadius = 900.0;
constexpr f64 kFeatureRefreshDistance = 380.0;

}

void PlanetSurface::configure(const PlanetBody& body, u32 maximumLevel, f32 splitFactor) {
    release();
    planetBody = body;
    maximumSubdivision = clampValue(maximumLevel, 3u, 20u);
    splitDistanceFactor = clampValue(splitFactor, 0.8f, 6.0f);

    for (u32 face = 0; face < 6; ++face) {
        roots[face] = createNode(face, 0, 0.0, 0.0, 1.0);
    }
    featuresValid = false;
}

void PlanetSurface::prime(const DVec3& viewerLocalPosition, f64 dayPhase, u32 chunkLimit) {
    u32 budget = chunkLimit;
    while (budget > 0) {
        const u32 before = budget;
        for (u32 face = 0; face < 6; ++face) {
            refine(roots[face], viewerLocalPosition, dayPhase, budget, 1.0f);
        }
        if (budget == before) break;
    }
}

void PlanetSurface::release() {
    nodes.clear();
    scatterInstances.clear();
    resourceNodes.clear();
    creatureInstances.clear();
    featuresValid = false;
}

u32 PlanetSurface::createNode(u32 face, u32 level, f64 originU, f64 originV, f64 size) {
    auto node = std::make_unique<Node>();
    node->face = face;
    node->level = level;
    node->originU = originU;
    node->originV = originV;
    node->size = size;
    node->centerDirection = cubeFaceDirection(face, originU + size * 0.5, originV + size * 0.5);
    node->centerLocalPosition = planetBody.center() + node->centerDirection * planetBody.radiusAt(node->centerDirection);
    node->worldSize = size * planetBody.seaLevelRadius() * 1.7;
    nodes.push_back(std::move(node));
    return static_cast<u32>(nodes.size() - 1);
}

void PlanetSurface::collapse(u32 nodeIndex) {
    Node& node = *nodes[nodeIndex];
    if (!node.hasChildren) return;
    for (u32 child : node.children) {
        if (child == kInvalidIndex32) continue;
        collapse(child);
        nodes[child]->chunk.release();
    }
    node.hasChildren = false;
}

void PlanetSurface::refine(u32 nodeIndex, const DVec3& viewerLocalPosition, f64 dayPhase, u32& budget,
                           f32 detailScale) {
    Node& node = *nodes[nodeIndex];
    const f64 distance = maxValue(length(viewerLocalPosition - node.centerLocalPosition) - node.worldSize * 0.5, 1.0);
    const bool wantsSplit = node.level < maximumSubdivision &&
                            distance < node.worldSize * static_cast<f64>(splitDistanceFactor * detailScale);

    if (wantsSplit) {
        if (!node.hasChildren) {
            if (budget == 0) return;
            const f64 half = node.size * 0.5;
            node.children[0] = createNode(node.face, node.level + 1, node.originU, node.originV, half);
            node.children[1] = createNode(node.face, node.level + 1, node.originU + half, node.originV, half);
            node.children[2] = createNode(node.face, node.level + 1, node.originU, node.originV + half, half);
            node.children[3] = createNode(node.face, node.level + 1, node.originU + half, node.originV + half, half);
            nodes[nodeIndex]->hasChildren = true;
        }
        for (u32 index = 0; index < 4; ++index) {
            const u32 child = nodes[nodeIndex]->children[index];
            if (child != kInvalidIndex32) refine(child, viewerLocalPosition, dayPhase, budget, detailScale);
        }
        return;
    }

    if (node.hasChildren) collapse(nodeIndex);

    Node& leaf = *nodes[nodeIndex];
    if (leaf.chunk.valid() || budget == 0) return;
    generateTerrainGeometry(planetBody, leaf.face, leaf.originU, leaf.originV, leaf.size, dayPhase, leaf.pending);
    leaf.chunk.upload(leaf.pending);
    leaf.pending.vertices.clear();
    leaf.pending.indices.clear();
    --budget;
}

void PlanetSurface::update(const DVec3& viewerLocalPosition, f64 dayPhase, u32 chunkBudgetPerFrame,
                           f32 detailScale) {
    u32 budget = chunkBudgetPerFrame;
    for (u32 face = 0; face < 6; ++face) {
        refine(roots[face], viewerLocalPosition, dayPhase, budget, detailScale);
    }

    const f64 altitude = planetBody.altitudeAt(viewerLocalPosition);
    if (altitude < 2500.0) {
        if (!featuresValid || length(viewerLocalPosition - featureAnchor) > kFeatureRefreshDistance) {
            featureAnchor = viewerLocalPosition;
            populateSurfaceFeatures();
            featuresValid = true;
        }
    } else if (featuresValid) {
        scatterInstances.clear();
        resourceNodes.clear();
        creatureInstances.clear();
        featuresValid = false;
    }
}

void PlanetSurface::populateSurfaceFeatures() {
    scatterInstances.clear();
    resourceNodes.clear();
    creatureInstances.clear();

    const DVec3 anchorDirection = normalize(featureAnchor - planetBody.center());
    const u64 cellSeed = hashCoordinate(planetBody.profile().seed,
                                        static_cast<i64>(featureAnchor.x / kFeatureRefreshDistance),
                                        static_cast<i64>(featureAnchor.y / kFeatureRefreshDistance),
                                        static_cast<i64>(featureAnchor.z / kFeatureRefreshDistance));
    Random random(cellSeed);

    const DVec3 reference = std::fabs(anchorDirection.y) < 0.9 ? DVec3::unitY() : DVec3::unitX();
    const DVec3 tangent = normalize(cross(reference, anchorDirection));
    const DVec3 bitangent = cross(anchorDirection, tangent);

    const PlanetProfile& profile = planetBody.profile();
    const u32 vegetationCount = static_cast<u32>(profile.vegetationDensity * 260.0);
    const u32 resourceCount = 26;
    const u32 creatureCount = static_cast<u32>(profile.faunaDiversity * 14.0);

    for (u32 index = 0; index < vegetationCount; ++index) {
        const f64 angle = random.rangeDouble(0.0, kTwoPiDouble);
        const f64 distance = std::sqrt(random.nextDouble()) * kFeatureRadius;
        const DVec3 offset = tangent * (std::cos(angle) * distance) + bitangent * (std::sin(angle) * distance);
        const DVec3 direction = normalize(anchorDirection + offset / planetBody.seaLevelRadius());
        const SurfaceSample sample = planetBody.sampleSurface(direction, 0.5);
        if (sample.underWater || sample.slope > 1.6) continue;

        ScatterInstance instance;
        instance.localPosition = planetBody.center() + direction * planetBody.radiusAt(direction);
        instance.upDirection = direction;
        instance.scale = static_cast<f32>(random.rangeDouble(0.6, 3.4) * (0.5 + profile.vegetationDensity));
        instance.rotation = static_cast<f32>(random.rangeDouble(0.0, kTwoPiDouble));
        instance.tint = lerp(profile.vegetationColor, sample.albedo, static_cast<f32>(random.rangeDouble(0.0, 0.5)));
        instance.kind = static_cast<u32>(random.rangeInt(0, 3));
        scatterInstances.push_back(instance);
    }

    for (u32 index = 0; index < resourceCount; ++index) {
        const f64 angle = random.rangeDouble(0.0, kTwoPiDouble);
        const f64 distance = std::sqrt(random.nextDouble()) * kFeatureRadius;
        const DVec3 offset = tangent * (std::cos(angle) * distance) + bitangent * (std::sin(angle) * distance);
        const DVec3 direction = normalize(anchorDirection + offset / planetBody.seaLevelRadius());
        const SurfaceSample sample = planetBody.sampleSurface(direction, 0.5);
        if (sample.underWater) continue;

        ResourceNode node;
        node.localPosition = planetBody.center() + direction * planetBody.radiusAt(direction);
        node.upDirection = direction;
        node.resource = planetBody.dominantResource(direction);
        node.radiusMeters = static_cast<f32>(random.rangeDouble(1.6, 4.2));
        node.remainingUnits = static_cast<u32>(random.rangeInt(120, 420));
        resourceNodes.push_back(node);
    }

    for (u32 index = 0; index < creatureCount; ++index) {
        const f64 angle = random.rangeDouble(0.0, kTwoPiDouble);
        const f64 distance = std::sqrt(random.nextDouble()) * kFeatureRadius;
        const DVec3 offset = tangent * (std::cos(angle) * distance) + bitangent * (std::sin(angle) * distance);
        const DVec3 direction = normalize(anchorDirection + offset / planetBody.seaLevelRadius());
        const SurfaceSample sample = planetBody.sampleSurface(direction, 0.5);
        if (sample.underWater) continue;

        CreatureInstance creature;
        creature.localPosition = planetBody.center() + direction * (planetBody.radiusAt(direction) + 1.0);
        creature.heading = normalize(tangent * std::cos(angle) + bitangent * std::sin(angle));
        creature.scale = static_cast<f32>(random.rangeDouble(0.5, 3.0));
        creature.speed = static_cast<f32>(random.rangeDouble(0.8, 4.5));
        creature.wanderTimer = static_cast<f32>(random.rangeDouble(0.0, 5.0));
        creature.speciesIndex = static_cast<u32>(random.rangeInt(0, 6));
        creatureInstances.push_back(creature);
    }
}

void PlanetSurface::updateLife(f64 stepSeconds, const DVec3& viewerLocalPosition) {
    for (usize index = 0; index < creatureInstances.size(); ++index) {
        CreatureInstance& creature = creatureInstances[index];
        creature.wanderTimer -= static_cast<f32>(stepSeconds);
        const DVec3 up = normalize(creature.localPosition - planetBody.center());

        if (creature.wanderTimer <= 0.0f) {
            Random random(hashCombine(planetBody.profile().seed,
                                      static_cast<u64>(index) * 977ull + static_cast<u64>(creature.wanderTimer * 13.0f)));
            creature.wanderTimer = static_cast<f32>(random.rangeDouble(2.0, 7.0));
            const DVec3 reference = std::fabs(up.y) < 0.9 ? DVec3::unitY() : DVec3::unitX();
            const DVec3 tangent = normalize(cross(reference, up));
            const DVec3 bitangent = cross(up, tangent);
            const f64 angle = random.rangeDouble(0.0, kTwoPiDouble);
            creature.heading = normalize(tangent * std::cos(angle) + bitangent * std::sin(angle));
        }

        const f64 viewerDistance = length(viewerLocalPosition - creature.localPosition);
        f64 speed = static_cast<f64>(creature.speed);
        if (viewerDistance < 26.0) {
            const DVec3 away = normalize(creature.localPosition - viewerLocalPosition);
            const DVec3 projected = away - up * dot(away, up);
            if (lengthSquared(projected) > 1.0e-6) creature.heading = normalize(projected);
            speed *= 2.4;
        }

        creature.localPosition += creature.heading * (speed * stepSeconds);
        const DVec3 direction = normalize(creature.localPosition - planetBody.center());
        creature.localPosition = planetBody.center() + direction * (planetBody.radiusAt(direction) + 1.0);
        const DVec3 newUp = direction;
        const DVec3 projectedHeading = creature.heading - newUp * dot(creature.heading, newUp);
        if (lengthSquared(projectedHeading) > 1.0e-6) creature.heading = normalize(projectedHeading);
    }
}

void PlanetSurface::gatherLeaves(u32 nodeIndex, std::vector<u32>& out) const {
    const Node& node = *nodes[nodeIndex];
    if (!node.hasChildren) {
        if (node.chunk.valid()) out.push_back(nodeIndex);
        return;
    }
    for (u32 child : node.children) {
        if (child != kInvalidIndex32) gatherLeaves(child, out);
    }
}

void PlanetSurface::collectVisible(const DVec3& renderOrigin, const Frustum& frustum,
                                   std::vector<const TerrainChunk*>& out) const {
    out.clear();
    lastDrawnTriangles = 0;
    std::vector<u32> leaves;
    for (u32 face = 0; face < 6; ++face) gatherLeaves(roots[face], leaves);

    for (u32 leafIndex : leaves) {
        const Node& node = *nodes[leafIndex];
        Sphere bounds;
        bounds.center = (node.chunk.originLocalPosition() - renderOrigin).toFloat();
        bounds.radius = static_cast<f32>(node.chunk.boundingRadius());
        if (!frustum.containsSphere(bounds)) continue;
        out.push_back(&node.chunk);
        lastDrawnTriangles += node.chunk.triangleCount();
    }
}

u32 PlanetSurface::deepestLevel() const {
    u32 deepest = 0;
    for (const std::unique_ptr<Node>& node : nodes) {
        if (node->hasChildren || !node->chunk.valid()) continue;
        deepest = maxValue(deepest, node->level);
    }
    return deepest;
}

u32 PlanetSurface::leafCount() const {
    u32 total = 0;
    for (const std::unique_ptr<Node>& node : nodes) {
        if (!node->hasChildren && node->chunk.valid()) ++total;
    }
    return total;
}

f64 PlanetSurface::finestChunkMeters() const {
    f64 finest = 1.0e30;
    for (const std::unique_ptr<Node>& node : nodes) {
        if (node->hasChildren || !node->chunk.valid()) continue;
        finest = minValue(finest, node->worldSize);
    }
    return finest;
}

ResourceNode* PlanetSurface::nearestResource(const DVec3& localPosition, f64 maximumDistance) {
    ResourceNode* best = nullptr;
    f64 bestDistance = maximumDistance;
    for (ResourceNode& node : resourceNodes) {
        if (node.depleted) continue;
        const f64 distance = length(node.localPosition - localPosition);
        if (distance >= bestDistance) continue;
        bestDistance = distance;
        best = &node;
    }
    return best;
}

CreatureInstance* PlanetSurface::nearestCreature(const DVec3& localPosition, f64 maximumDistance) {
    CreatureInstance* best = nullptr;
    f64 bestDistance = maximumDistance;
    for (CreatureInstance& creature : creatureInstances) {
        const f64 distance = length(creature.localPosition - localPosition);
        if (distance >= bestDistance) continue;
        bestDistance = distance;
        best = &creature;
    }
    return best;
}

}
