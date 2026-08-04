#pragma once

#include "GLApi.hpp"

namespace sf {

class RenderTarget {
public:
    RenderTarget() = default;
    ~RenderTarget();

    RenderTarget(const RenderTarget&) = delete;
    RenderTarget& operator=(const RenderTarget&) = delete;

    bool create(u32 width, u32 height, GLenum colorFormat, bool withDepth);
    void resize(u32 width, u32 height);
    void release();

    void bindForDrawing() const;
    void clear(f32 red, f32 green, f32 blue, f32 alpha, bool clearDepth) const;

    GLuint colorTexture() const { return colorAttachment; }
    GLuint depthTexture() const { return depthAttachment; }
    u32 width() const { return currentWidth; }
    u32 height() const { return currentHeight; }
    bool valid() const { return framebuffer != 0; }

    static void bindDefault(u32 width, u32 height);

private:
    GLuint framebuffer = 0;
    GLuint colorAttachment = 0;
    GLuint depthAttachment = 0;
    GLenum format = GL_RGBA16F;
    u32 currentWidth = 0;
    u32 currentHeight = 0;
    bool depthEnabled = false;
};

void bindTextureUnit(u32 unit, GLuint texture);

}
