#pragma once

#include "../core/Result.hpp"
#include "Camera.hpp"
#include "CelestialBodyPass.hpp"
#include "Mesh.hpp"
#include "Shader.hpp"

#include <vector>

namespace sf {

class TerrainChunk;

struct TerrainRenderParameters {
    DVec3 planetCenter = DVec3::zero();
    f32 planetRadius = 6.0e6f;
    f32 terrainAmplitude = 12000.0f;
    f32 seaLevelOffset = 0.0f;
    Vec3 waterColor = Vec3(0.05f, 0.20f, 0.34f);
    Vec3 fogColor = Vec3(0.42f, 0.52f, 0.62f);
    f32 fogDensity = 0.0f;
    f32 elapsedSeconds = 0.0f;
    f32 detailStrength = 1.0f;
    bool waterEnabled = true;
};

struct ScatterRenderItem {
    Vec3 relativePosition;
    Vec3 upDirection;
    Vec3 tint;
    f32 scale = 1.0f;
    f32 rotation = 0.0f;
    u32 kind = 0;
};

class TerrainPass {
public:
    Status initialize();
    void release();

    void renderChunks(const Camera& camera, const std::vector<const TerrainChunk*>& chunks,
                      const TerrainRenderParameters& parameters, const CelestialLighting& lighting);
    void renderScatter(const Camera& camera, const std::vector<ScatterRenderItem>& items,
                       const TerrainRenderParameters& parameters, const CelestialLighting& lighting);
    bool ready() const { return terrainShader.valid(); }

private:
    Shader terrainShader;
    Shader scatterShader;
    Mesh coneMesh;
    Mesh blockMesh;
};

}
