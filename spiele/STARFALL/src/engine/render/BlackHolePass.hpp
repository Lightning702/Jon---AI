#pragma once

#include "../core/Result.hpp"
#include "Camera.hpp"
#include "Mesh.hpp"
#include "RenderTarget.hpp"
#include "Shader.hpp"

namespace sf {

struct BlackHoleRenderParameters {
    DVec3 centerWorldPosition = DVec3::zero();
    f64 gravitationalRadiusMeters = 6.0553e9;
    f32 spinParameter = 0.94f;
    f32 diskInnerRadius = 0.0f;
    f32 diskOuterRadius = 26.0f;
    f32 diskInnerTemperatureKelvin = 26000.0f;
    f32 diskThickness = 0.055f;
    f32 diskOpacity = 1.0f;
    f32 diskBrightness = 22.0f;
    f32 jetStrength = 1.0f;
    f32 accretionRate = 1.0f;
    f32 elapsedSeconds = 0.0f;
    f32 exposureScale = 1.0f;
    u32 maximumSteps = 320;
    f32 stepFraction = 0.024f;
    f32 resolutionScale = 0.5f;
    i32 integratorOrder = 2;
    i32 skyDetail = 2;
    f32 accumulationResolutionScale = 1.0f;
    u32 accumulationLimit = 192;
    bool accumulate = false;
};

class BlackHolePass {
public:
    Status initialize();
    void release();

    void render(const Camera& camera, const BlackHoleRenderParameters& parameters, u32 targetWidth, u32 targetHeight);
    void resetAccumulation() { sampleIndex = 0; }

    GLuint resultTexture() const { return target.colorTexture(); }
    u32 resultWidth() const { return target.width(); }
    u32 resultHeight() const { return target.height(); }
    bool ready() const { return shader.valid(); }
    u32 accumulatedSamples() const { return sampleIndex; }
    bool converged() const { return sampleIndex >= convergenceLimit; }
    f32 convergenceFraction() const {
        return convergenceLimit == 0 ? 1.0f
                                     : clampValue(static_cast<f32>(sampleIndex) /
                                                      static_cast<f32>(convergenceLimit), 0.0f, 1.0f);
    }

    static f32 horizonRadius(f32 spin);
    static f32 innermostStableCircularOrbit(f32 spin);
    static f32 photonSphereRadius(f32 spin);
    static f32 ergosphereRadius(f32 spin, f32 polarCosine);
    static f64 timeDilationFactor(f64 radiusInGravitationalRadii, f64 spin);

private:
    Shader shader;
    RenderTarget target;
    FullscreenTriangle triangle;
    u32 sampleIndex = 0;
    u32 convergenceLimit = 192;
};

}
