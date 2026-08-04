#pragma once

#include "../core/Result.hpp"
#include "Mesh.hpp"
#include "RenderTarget.hpp"
#include "Shader.hpp"

namespace sf {

struct PostProcessParameters {
    f32 exposure = 1.0f;
    f32 bloomStrength = 0.055f;
    f32 bloomThreshold = 1.15f;
    f32 vignetteStrength = 0.32f;
    f32 chromaticAberration = 0.0016f;
    f32 filmGrain = 0.016f;
    f32 elapsedSeconds = 0.0f;
    f32 distortionStrength = 0.0f;
    f32 fadeToBlack = 0.0f;
    f32 desaturation = 0.0f;
    u32 bloomLevels = 5;
};

class PostProcessPass {
public:
    Status initialize();
    void release();
    void resize(u32 width, u32 height);
    void render(GLuint sourceTexture, u32 outputWidth, u32 outputHeight, const PostProcessParameters& parameters);
    bool ready() const { return compositeShader.valid(); }

private:
    static constexpr u32 kBloomLevels = 5;

    Shader brightPassShader;
    Shader blurShader;
    Shader compositeShader;
    RenderTarget bloomChain[kBloomLevels];
    RenderTarget blurScratch[kBloomLevels];
    FullscreenTriangle triangle;
    u32 baseWidth = 0;
    u32 baseHeight = 0;
};

}
