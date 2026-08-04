#pragma once

#include "../core/Result.hpp"
#include "Camera.hpp"
#include "Mesh.hpp"
#include "Shader.hpp"

#include <vector>

namespace sf {

enum class CelestialSurface : u32 {
    Rock = 0,
    Ocean,
    Ice,
    Desert,
    Lava,
    GasGiant,
    Star,
    Metal,
    Crystal,
    Count
};

struct CelestialBodyDraw {
    DVec3 worldPosition = DVec3::zero();
    f64 radiusMeters = 1.0e6;
    Quat orientation = Quat::identity();
    Vec3 primaryColor = Vec3(0.55f, 0.5f, 0.45f);
    Vec3 secondaryColor = Vec3(0.3f, 0.35f, 0.28f);
    Vec3 atmosphereColor = Vec3(0.35f, 0.55f, 0.95f);
    f32 atmosphereHeightFraction = 0.025f;
    f32 atmosphereDensity = 1.0f;
    f32 roughness = 0.85f;
    f32 metallic = 0.0f;
    f32 emissiveStrength = 0.0f;
    f32 surfaceDetail = 1.0f;
    f32 cloudCoverage = 0.0f;
    f32 iceCoverage = 0.0f;
    f32 nightLights = 0.0f;
    u64 surfaceSeed = 1;
    CelestialSurface surfaceType = CelestialSurface::Rock;
    bool hasRing = false;
    f32 ringInnerFraction = 1.3f;
    f32 ringOuterFraction = 2.2f;
    Vec3 ringColor = Vec3(0.72f, 0.64f, 0.52f);
};

struct CelestialLighting {
    Vec3 starDirection = Vec3(0.0f, 0.0f, -1.0f);
    Vec3 starColor = Vec3(1.0f, 0.97f, 0.92f);
    f32 starIntensity = 1.0f;
    Vec3 ambientColor = Vec3(0.02f, 0.025f, 0.04f);
    Vec3 secondaryDirection = Vec3(0.0f, 1.0f, 0.0f);
    Vec3 secondaryColor = Vec3(0.0f, 0.0f, 0.0f);
    f32 elapsedSeconds = 0.0f;
};

class CelestialBodyPass {
public:
    Status initialize();
    void release();
    void render(const Camera& camera, const std::vector<CelestialBodyDraw>& bodies, const CelestialLighting& lighting);
    void applyDetail(u32 sphereSubdivisions, bool enableAtmosphere, bool enableRings);
    bool ready() const { return surfaceShader.valid(); }
    u32 detailSubdivisions() const { return currentSubdivisions; }

private:
    void drawBody(const Camera& camera, const CelestialBodyDraw& body, const CelestialLighting& lighting);
    void drawAtmosphere(const Camera& camera, const CelestialBodyDraw& body, const CelestialLighting& lighting);
    void drawRing(const Camera& camera, const CelestialBodyDraw& body, const CelestialLighting& lighting);

    Shader surfaceShader;
    Shader atmosphereShader;
    Shader ringShader;
    Mesh sphereMesh;
    Mesh ringMesh;
    u32 currentSubdivisions = 5;
    bool atmosphereEnabled = true;
    bool ringsEnabled = true;
};

}
