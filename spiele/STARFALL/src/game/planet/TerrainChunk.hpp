#pragma once

#include "../../engine/render/GLApi.hpp"
#include "PlanetBody.hpp"

#include <vector>

namespace sf {

constexpr u32 kTerrainGridResolution = 25;

struct TerrainVertex {
    Vec3 position;
    Vec3 normalVector;
    Vec3 albedo;
    f32 elevationFraction = 0.0f;
    f32 slope = 0.0f;
    f32 water = 0.0f;
};

struct TerrainGeometry {
    std::vector<TerrainVertex> vertices;
    std::vector<u32> indices;
    DVec3 originLocalPosition = DVec3::zero();
    f64 boundingRadius = 0.0;
    bool underWater = false;
};

void generateTerrainGeometry(const PlanetBody& body, u32 face, f64 originU, f64 originV, f64 size, f64 dayPhase,
                             TerrainGeometry& out);

class TerrainChunk {
public:
    TerrainChunk() = default;
    ~TerrainChunk();

    TerrainChunk(const TerrainChunk&) = delete;
    TerrainChunk& operator=(const TerrainChunk&) = delete;
    TerrainChunk(TerrainChunk&& other) noexcept;
    TerrainChunk& operator=(TerrainChunk&& other) noexcept;

    void upload(const TerrainGeometry& geometry);
    void release();
    void draw() const;

    const DVec3& originLocalPosition() const { return origin; }
    f64 boundingRadius() const { return radius; }
    bool valid() const { return vertexArray != 0; }
    u32 triangleCount() const { return indexCount / 3; }

private:
    GLuint vertexArray = 0;
    GLuint vertexBuffer = 0;
    GLuint indexBuffer = 0;
    u32 indexCount = 0;
    DVec3 origin = DVec3::zero();
    f64 radius = 0.0;
};

}
