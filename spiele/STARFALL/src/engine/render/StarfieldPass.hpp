#pragma once

#include "../core/Result.hpp"
#include "Camera.hpp"
#include "Mesh.hpp"
#include "Shader.hpp"

namespace sf {

struct StarfieldParameters {
    f32 elapsedSeconds = 0.0f;
    f32 nebulaIntensity = 1.0f;
    f32 galaxyIntensity = 1.0f;
    f32 starIntensity = 1.0f;
    f32 exposureScale = 1.0f;
    Vec3 localStarDirection = Vec3(0.0f, 0.0f, -1.0f);
    Vec3 localStarColor = Vec3(1.0f, 0.96f, 0.9f);
    f32 localStarAngularRadius = 0.0045f;
    f32 localStarIntensity = 120.0f;
    f32 warpFactor = 0.0f;
    Vec3 warpDirection = Vec3(0.0f, 0.0f, -1.0f);
    i32 skyDetail = 2;
};

class StarfieldPass {
public:
    Status initialize();
    void release();
    void render(const Camera& camera, const StarfieldParameters& parameters);
    bool ready() const { return shader.valid(); }

private:
    Shader shader;
    FullscreenTriangle triangle;
};

}
