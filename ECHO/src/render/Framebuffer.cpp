#include "Framebuffer.h"
#include "../core/Log.h"

namespace echo {

GLuint Framebuffer::createTexture(const AttachmentDesc& d, int width, int height) {
    GLuint t = 0;
    glGenTextures(1, &t);
    glBindTexture(GL_TEXTURE_2D, t);
    glTexImage2D(GL_TEXTURE_2D, 0, d.internalFormat, width, height, 0, d.format, d.type, nullptr);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, d.mipmaps ? GL_LINEAR_MIPMAP_LINEAR : d.filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, d.filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, d.wrap);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, d.wrap);
    if (d.wrap == GL_CLAMP_TO_BORDER) {
        float border[4] = { 1, 1, 1, 1 };
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, border);
    }
    if (d.shadowCompare) {
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL);
    }
    if (d.mipmaps) glGenerateMipmap(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, 0);
    return t;
}

void Framebuffer::create(int width, int height, const std::vector<AttachmentDesc>& colors, const AttachmentDesc* depth) {
    destroy();
    w = std::max(width, 1);
    h = std::max(height, 1);
    colorDescs = colors;
    hasDepth = depth != nullptr;
    if (hasDepth) depthDesc = *depth;

    glGenFramebuffers(1, &fbo);
    glBindFramebuffer(GL_FRAMEBUFFER, fbo);

    std::vector<GLenum> drawBufs;
    for (size_t i = 0; i < colors.size(); i++) {
        GLuint t = createTexture(colors[i], w, h);
        colorTextures.push_back(t);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0 + (GLenum)i, GL_TEXTURE_2D, t, 0);
        drawBufs.push_back(GL_COLOR_ATTACHMENT0 + (GLenum)i);
    }

    if (drawBufs.empty()) {
        glDrawBuffer(GL_NONE);
        glReadBuffer(GL_NONE);
    } else {
        glDrawBuffers((GLsizei)drawBufs.size(), drawBufs.data());
    }

    if (hasDepth) {
        depthTexture = createTexture(depthDesc, w, h);
        GLenum att = depthDesc.format == GL_DEPTH_STENCIL ? GL_DEPTH_STENCIL_ATTACHMENT : GL_DEPTH_ATTACHMENT;
        glFramebufferTexture2D(GL_FRAMEBUFFER, att, GL_TEXTURE_2D, depthTexture, 0);
    }

    GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (status != GL_FRAMEBUFFER_COMPLETE) LOG_ERROR("Framebuffer incomplete: 0x%04X (%dx%d)", status, w, h);
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
}

void Framebuffer::createDepthOnly(int width, int height, const AttachmentDesc& depth) {
    create(width, height, {}, &depth);
}

void Framebuffer::resize(int width, int height) {
    if (width == w && height == h) return;
    std::vector<AttachmentDesc> c = colorDescs;
    AttachmentDesc d = depthDesc;
    bool hd = hasDepth;
    create(width, height, c, hd ? &d : nullptr);
}

void Framebuffer::destroy() {
    if (!colorTextures.empty()) {
        glDeleteTextures((GLsizei)colorTextures.size(), colorTextures.data());
        colorTextures.clear();
    }
    if (depthTexture) { glDeleteTextures(1, &depthTexture); depthTexture = 0; }
    if (fbo) { glDeleteFramebuffers(1, &fbo); fbo = 0; }
}

void Framebuffer::bind() const {
    glBindFramebuffer(GL_FRAMEBUFFER, fbo);
}

void Framebuffer::bindWithViewport() const {
    glBindFramebuffer(GL_FRAMEBUFFER, fbo);
    glViewport(0, 0, w, h);
}

void Framebuffer::unbind(int screenW, int screenH) {
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    glViewport(0, 0, screenW, screenH);
}

void Framebuffer::generateColorMips(int i) const {
    if (i < 0 || i >= (int)colorTextures.size()) return;
    glBindTexture(GL_TEXTURE_2D, colorTextures[i]);
    glGenerateMipmap(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, 0);
}

}
