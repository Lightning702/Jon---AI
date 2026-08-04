#include "PostProcessPass.hpp"

#include "../core/Log.hpp"
#include "../math/Scalar.hpp"
#include "SkyCommon.hpp"

#include <string>

namespace sf {
namespace {

const char* const kBrightPassSource = R"GLSL(#version 330 core
in vec2 vScreenUv;
out vec4 fragColor;
uniform sampler2D uSource;
uniform float uThreshold;

void main() {
    vec3 color = texture(uSource, vScreenUv).rgb;
    float brightness = dot(color, vec3(0.2126, 0.7152, 0.0722));
    float weight = max(brightness - uThreshold, 0.0) / max(brightness, 1.0e-4);
    fragColor = vec4(color * weight, 1.0);
}
)GLSL";

const char* const kBlurSource = R"GLSL(#version 330 core
in vec2 vScreenUv;
out vec4 fragColor;
uniform sampler2D uSource;
uniform vec2 uTexelStep;

void main() {
    vec3 total = texture(uSource, vScreenUv).rgb * 0.227027;
    total += texture(uSource, vScreenUv + uTexelStep * 1.384615).rgb * 0.316216;
    total += texture(uSource, vScreenUv - uTexelStep * 1.384615).rgb * 0.316216;
    total += texture(uSource, vScreenUv + uTexelStep * 3.230769).rgb * 0.070270;
    total += texture(uSource, vScreenUv - uTexelStep * 3.230769).rgb * 0.070270;
    fragColor = vec4(total, 1.0);
}
)GLSL";

const char* const kCompositeSource = R"GLSL(#version 330 core
in vec2 vScreenUv;
out vec4 fragColor;

uniform sampler2D uScene;
uniform sampler2D uBloom0;
uniform sampler2D uBloom1;
uniform sampler2D uBloom2;
uniform sampler2D uBloom3;
uniform sampler2D uBloom4;
uniform float uExposure;
uniform float uBloomStrength;
uniform float uVignette;
uniform float uChromatic;
uniform float uGrain;
uniform float uTime;
uniform float uDistortion;
uniform float uFade;
uniform float uDesaturation;

vec3 acesFilmic(vec3 color) {
    mat3 inputMatrix = mat3(
        0.59719, 0.07600, 0.02840,
        0.35458, 0.90834, 0.13383,
        0.04823, 0.01566, 0.83777);
    mat3 outputMatrix = mat3(
         1.60475, -0.10208, -0.00327,
        -0.53108,  1.10813, -0.07276,
        -0.07367, -0.00605,  1.07602);
    vec3 working = inputMatrix * color;
    vec3 a = working * (working + 0.0245786) - 0.000090537;
    vec3 b = working * (0.983729 * working + 0.4329510) + 0.238081;
    return clamp(outputMatrix * (a / b), 0.0, 1.0);
}

float grainNoise(vec2 coordinate, float time) {
    return fract(sin(dot(coordinate * (1.0 + time), vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec2 centered = vScreenUv - 0.5;
    float radial = length(centered);

    vec2 distortedUv = vScreenUv + centered * radial * radial * uDistortion;
    float aberration = uChromatic * (0.35 + radial * radial * 2.4);
    vec2 direction = radial > 1.0e-4 ? centered / radial : vec2(0.0);

    vec3 scene;
    scene.r = texture(uScene, clamp(distortedUv + direction * aberration, vec2(0.0), vec2(1.0))).r;
    scene.g = texture(uScene, clamp(distortedUv, vec2(0.0), vec2(1.0))).g;
    scene.b = texture(uScene, clamp(distortedUv - direction * aberration, vec2(0.0), vec2(1.0))).b;

    vec3 bloom = texture(uBloom0, distortedUv).rgb * 0.36;
    bloom += texture(uBloom1, distortedUv).rgb * 0.26;
    bloom += texture(uBloom2, distortedUv).rgb * 0.19;
    bloom += texture(uBloom3, distortedUv).rgb * 0.12;
    bloom += texture(uBloom4, distortedUv).rgb * 0.07;

    vec3 combined = scene + bloom * uBloomStrength * 6.0;
    combined *= uExposure;

    vec3 mapped = acesFilmic(combined);
    float luminance = dot(mapped, vec3(0.2126, 0.7152, 0.0722));
    mapped = mix(mapped, vec3(luminance), clamp(uDesaturation, 0.0, 1.0));

    float vignette = 1.0 - uVignette * smoothstep(0.28, 0.86, radial);
    mapped *= vignette;

    float grain = (grainNoise(vScreenUv * 1024.0, fract(uTime)) - 0.5) * uGrain;
    mapped += vec3(grain);

    mapped = mix(mapped, vec3(0.0), clamp(uFade, 0.0, 1.0));
    mapped = pow(max(mapped, vec3(0.0)), vec3(1.0 / 2.2));
    fragColor = vec4(mapped, 1.0);
}
)GLSL";

}

Status PostProcessPass::initialize() {
    triangle.initialize();
    Status status = brightPassShader.compile("BrightPass", kFullscreenVertexSource, kBrightPassSource);
    if (!status.ok()) return status;
    status = blurShader.compile("GaussianBlur", kFullscreenVertexSource, kBlurSource);
    if (!status.ok()) return status;
    status = compositeShader.compile("Composite", kFullscreenVertexSource, kCompositeSource);
    if (!status.ok()) return status;
    logInfo("render", "Postprocessing bereit");
    return statusOk();
}

void PostProcessPass::release() {
    brightPassShader.release();
    blurShader.release();
    compositeShader.release();
    for (u32 level = 0; level < kBloomLevels; ++level) {
        bloomChain[level].release();
        blurScratch[level].release();
    }
    triangle.release();
}

void PostProcessPass::resize(u32 width, u32 height) {
    if (width == baseWidth && height == baseHeight) return;
    baseWidth = width;
    baseHeight = height;
    u32 levelWidth = width / 2;
    u32 levelHeight = height / 2;
    for (u32 level = 0; level < kBloomLevels; ++level) {
        const u32 clampedWidth = maxValue<u32>(levelWidth, 8);
        const u32 clampedHeight = maxValue<u32>(levelHeight, 8);
        bloomChain[level].create(clampedWidth, clampedHeight, GL_RGBA16F, false);
        blurScratch[level].create(clampedWidth, clampedHeight, GL_RGBA16F, false);
        levelWidth = maxValue<u32>(levelWidth / 2, 8);
        levelHeight = maxValue<u32>(levelHeight / 2, 8);
    }
}

void PostProcessPass::render(GLuint sourceTexture, u32 outputWidth, u32 outputHeight,
                             const PostProcessParameters& parameters) {
    if (!compositeShader.valid()) return;
    resize(outputWidth, outputHeight);

    glDisable(GL_DEPTH_TEST);
    glDisable(GL_BLEND);
    glDisable(GL_CULL_FACE);

    const u32 activeLevels = parameters.bloomLevels > kBloomLevels ? kBloomLevels : parameters.bloomLevels;

    for (u32 level = activeLevels; level < kBloomLevels; ++level) {
        bloomChain[level].bindForDrawing();
        bloomChain[level].clear(0.0f, 0.0f, 0.0f, 1.0f, false);
    }

    if (activeLevels > 0) {
        brightPassShader.bind();
        brightPassShader.setTextureUnit("uSource", 0);
        brightPassShader.setFloat("uThreshold", parameters.bloomThreshold);
        bindTextureUnit(0, sourceTexture);
        bloomChain[0].bindForDrawing();
        triangle.draw();
    }

    for (u32 level = 1; level < activeLevels; ++level) {
        brightPassShader.bind();
        brightPassShader.setFloat("uThreshold", 0.0f);
        bindTextureUnit(0, bloomChain[level - 1].colorTexture());
        bloomChain[level].bindForDrawing();
        triangle.draw();
    }

    blurShader.bind();
    blurShader.setTextureUnit("uSource", 0);
    for (u32 level = 0; level < activeLevels; ++level) {
        const f32 texelX = 1.0f / static_cast<f32>(maxValue<u32>(bloomChain[level].width(), 1));
        const f32 texelY = 1.0f / static_cast<f32>(maxValue<u32>(bloomChain[level].height(), 1));

        blurShader.setVec2("uTexelStep", texelX, 0.0f);
        bindTextureUnit(0, bloomChain[level].colorTexture());
        blurScratch[level].bindForDrawing();
        triangle.draw();

        blurShader.setVec2("uTexelStep", 0.0f, texelY);
        bindTextureUnit(0, blurScratch[level].colorTexture());
        bloomChain[level].bindForDrawing();
        triangle.draw();
    }

    RenderTarget::bindDefault(outputWidth, outputHeight);
    compositeShader.bind();
    compositeShader.setTextureUnit("uScene", 0);
    compositeShader.setTextureUnit("uBloom0", 1);
    compositeShader.setTextureUnit("uBloom1", 2);
    compositeShader.setTextureUnit("uBloom2", 3);
    compositeShader.setTextureUnit("uBloom3", 4);
    compositeShader.setTextureUnit("uBloom4", 5);
    compositeShader.setFloat("uExposure", parameters.exposure);
    compositeShader.setFloat("uBloomStrength", parameters.bloomStrength);
    compositeShader.setFloat("uVignette", parameters.vignetteStrength);
    compositeShader.setFloat("uChromatic", parameters.chromaticAberration);
    compositeShader.setFloat("uGrain", parameters.filmGrain);
    compositeShader.setFloat("uTime", parameters.elapsedSeconds);
    compositeShader.setFloat("uDistortion", parameters.distortionStrength);
    compositeShader.setFloat("uFade", parameters.fadeToBlack);
    compositeShader.setFloat("uDesaturation", parameters.desaturation);

    bindTextureUnit(0, sourceTexture);
    for (u32 level = 0; level < kBloomLevels; ++level) {
        bindTextureUnit(1 + level, bloomChain[level].colorTexture());
    }
    triangle.draw();
    bindTextureUnit(0, 0);
}

}
