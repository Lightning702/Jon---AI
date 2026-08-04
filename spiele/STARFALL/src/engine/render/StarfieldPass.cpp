#include "StarfieldPass.hpp"

#include "SkyCommon.hpp"

#include <string>

namespace sf {
namespace {

const char* const kStarfieldBody = R"GLSL(
in vec2 vScreenUv;
out vec4 fragColor;

uniform vec3 uCameraRight;
uniform vec3 uCameraUp;
uniform vec3 uCameraForward;
uniform float uTanHalfFieldOfView;
uniform float uAspectRatio;
uniform float uTime;
uniform float uNebulaIntensity;
uniform float uGalaxyIntensity;
uniform float uStarIntensity;
uniform float uExposure;
uniform vec3 uLocalStarDirection;
uniform vec3 uLocalStarColor;
uniform float uLocalStarAngularRadius;
uniform float uLocalStarIntensity;
uniform float uWarpFactor;
uniform vec3 uWarpDirection;
uniform int uSkyDetail;

void main() {
    vec2 normalizedScreen = vScreenUv * 2.0 - 1.0;
    vec3 direction = normalize(uCameraForward +
                               uCameraRight * (normalizedScreen.x * uTanHalfFieldOfView * uAspectRatio) +
                               uCameraUp * (normalizedScreen.y * uTanHalfFieldOfView));

    vec3 sampleDirection = direction;
    float aberrationBoost = 1.0;
    if (uWarpFactor > 0.001) {
        float alignment = dot(direction, uWarpDirection);
        float beta = clamp(uWarpFactor, 0.0, 0.995);
        float aberrated = (alignment + beta) / (1.0 + beta * alignment);
        vec3 lateral = normalize(direction - uWarpDirection * alignment + vec3(1.0e-5));
        float lateralAmount = sqrt(max(1.0 - aberrated * aberrated, 0.0));
        sampleDirection = normalize(uWarpDirection * aberrated + lateral * lateralAmount);
        aberrationBoost = pow((1.0 + beta * alignment) / max(1.0 - beta * beta, 1.0e-4), 1.5);
    }

    vec3 color = vec3(0.0);
    color += starLayer(sampleDirection, 220.0, 0.14, 5.2, 0.0) * uStarIntensity;
    if (uSkyDetail >= 1) color += starLayer(sampleDirection, 96.0, 0.10, 12.0, 37.0) * uStarIntensity;
    if (uSkyDetail >= 2) color += starLayer(sampleDirection, 42.0, 0.06, 26.0, 91.0) * uStarIntensity;
    color += galacticPlane(sampleDirection, uSkyDetail) * uGalaxyIntensity;
    if (uSkyDetail >= 1) color += nebulaField(sampleDirection, uTime, uSkyDetail) * uNebulaIntensity;
    color *= aberrationBoost;

    if (uLocalStarIntensity > 0.001) {
        float starAlignment = dot(direction, normalize(uLocalStarDirection));
        float angularDistance = acos(clamp(starAlignment, -1.0, 1.0));
        float discRadius = clamp(uLocalStarAngularRadius, 0.0004, 0.12);
        float disc = 1.0 - smoothstep(discRadius * 0.86, discRadius, angularDistance);
        float halo = min(discRadius * discRadius / max(angularDistance * angularDistance, 1.0e-8), 1.0);
        color += uLocalStarColor * (disc * uLocalStarIntensity + halo * uLocalStarIntensity * 0.035);
    }

    fragColor = vec4(color * uExposure, 1.0);
}
)GLSL";

std::string buildFragmentSource() {
    std::string source = "#version 330 core\n";
    source += kColorCommonSource;
    source += kSkyCommonSource;
    source += kStarfieldBody;
    return source;
}

}

Status StarfieldPass::initialize() {
    triangle.initialize();
    const std::string fragmentSource = buildFragmentSource();
    return shader.compile("Starfield", kFullscreenVertexSource, fragmentSource.c_str());
}

void StarfieldPass::release() {
    shader.release();
    triangle.release();
}

void StarfieldPass::render(const Camera& camera, const StarfieldParameters& parameters) {
    if (!shader.valid()) return;
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_BLEND);
    glDisable(GL_CULL_FACE);

    shader.bind();
    shader.setVec3("uCameraRight", camera.right());
    shader.setVec3("uCameraUp", camera.up());
    shader.setVec3("uCameraForward", camera.forward());
    shader.setFloat("uTanHalfFieldOfView", std::tan(camera.verticalFieldOfView() * 0.5f));
    shader.setFloat("uAspectRatio", camera.aspectRatio());
    shader.setFloat("uTime", parameters.elapsedSeconds);
    shader.setFloat("uNebulaIntensity", parameters.nebulaIntensity);
    shader.setFloat("uGalaxyIntensity", parameters.galaxyIntensity);
    shader.setFloat("uStarIntensity", parameters.starIntensity);
    shader.setFloat("uExposure", parameters.exposureScale);
    shader.setVec3("uLocalStarDirection", parameters.localStarDirection);
    shader.setVec3("uLocalStarColor", parameters.localStarColor);
    shader.setFloat("uLocalStarAngularRadius", parameters.localStarAngularRadius);
    shader.setFloat("uLocalStarIntensity", parameters.localStarIntensity);
    shader.setFloat("uWarpFactor", parameters.warpFactor);
    shader.setVec3("uWarpDirection", parameters.warpDirection);
    shader.setInt("uSkyDetail", parameters.skyDetail);

    triangle.draw();
}

}
