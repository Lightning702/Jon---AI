#pragma once

#include "../platform/GL.h"
#include "../core/Math.h"

namespace echo {

struct AttachmentDesc {
    GLenum internalFormat = GL_RGBA8;
    GLenum format = GL_RGBA;
    GLenum type = GL_UNSIGNED_BYTE;
    GLenum filter = GL_LINEAR;
    GLenum wrap = GL_CLAMP_TO_EDGE;
    bool mipmaps = false;
    bool shadowCompare = false;
};

class Framebuffer {
public:
    Framebuffer() {}
    ~Framebuffer() { destroy(); }
    Framebuffer(const Framebuffer&) = delete;
    Framebuffer& operator=(const Framebuffer&) = delete;

    void create(int width, int height, const std::vector<AttachmentDesc>& colors, const AttachmentDesc* depth);
    void createDepthOnly(int width, int height, const AttachmentDesc& depth);
    void resize(int width, int height);
    void destroy();

    void bind() const;
    void bindWithViewport() const;
    static void unbind(int screenW, int screenH);

    GLuint id() const { return fbo; }
    GLuint colorTex(int i) const { return i >= 0 && i < (int)colorTextures.size() ? colorTextures[i] : 0; }
    GLuint depthTex() const { return depthTexture; }
    int width() const { return w; }
    int height() const { return h; }
    int colorCount() const { return (int)colorTextures.size(); }
    void generateColorMips(int i) const;

private:
    GLuint createTexture(const AttachmentDesc& d, int width, int height);

    GLuint fbo = 0;
    GLuint depthTexture = 0;
    std::vector<GLuint> colorTextures;
    std::vector<AttachmentDesc> colorDescs;
    AttachmentDesc depthDesc;
    bool hasDepth = false;
    int w = 0, h = 0;
};

}
