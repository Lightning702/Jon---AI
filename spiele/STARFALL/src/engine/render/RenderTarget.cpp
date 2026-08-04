#include "RenderTarget.hpp"

#include "../core/Log.hpp"

namespace sf {

RenderTarget::~RenderTarget() {
    release();
}

bool RenderTarget::create(u32 width, u32 height, GLenum colorFormat, bool withDepth) {
    release();
    if (width == 0 || height == 0) return false;
    GLApi& api = gl();
    format = colorFormat;
    depthEnabled = withDepth;
    currentWidth = width;
    currentHeight = height;

    api.genFramebuffers(1, &framebuffer);
    api.bindFramebuffer(GL_FRAMEBUFFER, framebuffer);

    glGenTextures(1, &colorAttachment);
    glBindTexture(GL_TEXTURE_2D, colorAttachment);
    const GLenum pixelType = (colorFormat == GL_RGBA8 || colorFormat == GL_SRGB8_ALPHA8) ? GL_UNSIGNED_BYTE : GL_FLOAT;
    glTexImage2D(GL_TEXTURE_2D, 0, static_cast<GLint>(colorFormat), static_cast<GLsizei>(width),
                 static_cast<GLsizei>(height), 0, GL_RGBA, pixelType, nullptr);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    api.framebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, colorAttachment, 0);

    if (withDepth) {
        glGenTextures(1, &depthAttachment);
        glBindTexture(GL_TEXTURE_2D, depthAttachment);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, static_cast<GLsizei>(width),
                     static_cast<GLsizei>(height), 0, GL_DEPTH_COMPONENT, GL_FLOAT, nullptr);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        api.framebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depthAttachment, 0);
    }

    const GLenum status = api.checkFramebufferStatus(GL_FRAMEBUFFER);
    api.bindFramebuffer(GL_FRAMEBUFFER, 0);
    if (status != GL_FRAMEBUFFER_COMPLETE) {
        logError("render", "Framebuffer unvollstaendig (0x%X)", status);
        release();
        return false;
    }
    return true;
}

void RenderTarget::resize(u32 width, u32 height) {
    if (width == currentWidth && height == currentHeight) return;
    create(width, height, format, depthEnabled);
}

void RenderTarget::release() {
    GLApi& api = gl();
    if (depthAttachment != 0) glDeleteTextures(1, &depthAttachment);
    if (colorAttachment != 0) glDeleteTextures(1, &colorAttachment);
    if (framebuffer != 0) api.deleteFramebuffers(1, &framebuffer);
    depthAttachment = 0;
    colorAttachment = 0;
    framebuffer = 0;
    currentWidth = 0;
    currentHeight = 0;
}

void RenderTarget::bindForDrawing() const {
    gl().bindFramebuffer(GL_FRAMEBUFFER, framebuffer);
    glViewport(0, 0, static_cast<GLsizei>(currentWidth), static_cast<GLsizei>(currentHeight));
}

void RenderTarget::clear(f32 red, f32 green, f32 blue, f32 alpha, bool clearDepth) const {
    glClearColor(red, green, blue, alpha);
    GLbitfield mask = GL_COLOR_BUFFER_BIT;
    if (clearDepth && depthEnabled) mask |= GL_DEPTH_BUFFER_BIT;
    glClear(mask);
}

void RenderTarget::bindDefault(u32 width, u32 height) {
    gl().bindFramebuffer(GL_FRAMEBUFFER, 0);
    glViewport(0, 0, static_cast<GLsizei>(width), static_cast<GLsizei>(height));
}

void bindTextureUnit(u32 unit, GLuint texture) {
    GLApi& api = gl();
    api.activeTexture(GL_TEXTURE0 + unit);
    glBindTexture(GL_TEXTURE_2D, texture);
}

}
