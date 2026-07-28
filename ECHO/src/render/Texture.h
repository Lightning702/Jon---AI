#pragma once

#include "../platform/GL.h"
#include "../core/Math.h"

namespace echo {

struct TextureDesc {
    int width = 1;
    int height = 1;
    int depth = 1;
    GLenum internalFormat = GL_RGBA8;
    GLenum format = GL_RGBA;
    GLenum type = GL_UNSIGNED_BYTE;
    GLenum target = GL_TEXTURE_2D;
    GLenum minFilter = GL_LINEAR_MIPMAP_LINEAR;
    GLenum magFilter = GL_LINEAR;
    GLenum wrap = GL_REPEAT;
    bool mipmaps = true;
    bool anisotropic = true;
    bool shadowCompare = false;
    em::Vec4 borderColor = em::Vec4(1, 1, 1, 1);
};

class Texture {
public:
    Texture() {}
    ~Texture() { destroy(); }
    Texture(const Texture&) = delete;
    Texture& operator=(const Texture&) = delete;
    Texture(Texture&& o) noexcept { *this = std::move(o); }
    Texture& operator=(Texture&& o) noexcept {
        destroy();
        tex = o.tex; desc = o.desc;
        o.tex = 0;
        return *this;
    }

    void create(const TextureDesc& d, const void* pixels = nullptr);
    void update(const void* pixels, int level = 0);
    void updateLayer(const void* pixels, int layer);
    void destroy();
    void bind(int unit) const;
    void generateMips();
    void resize(int w, int h);

    GLuint id() const { return tex; }
    int width() const { return desc.width; }
    int height() const { return desc.height; }
    GLenum target() const { return desc.target; }
    bool valid() const { return tex != 0; }

private:
    void applyParams();
    GLuint tex = 0;
    TextureDesc desc;
};

struct Image {
    int w = 0, h = 0, channels = 4;
    std::vector<u8> data;

    void allocate(int width, int height, int ch = 4) {
        w = width; h = height; channels = ch;
        data.assign((size_t)w * h * ch, 0);
    }
    u8* at(int x, int y) { return &data[((size_t)y * w + x) * channels]; }
    const u8* at(int x, int y) const { return &data[((size_t)y * w + x) * channels]; }
    void set(int x, int y, const em::Vec4& c) {
        u8* p = at(x, y);
        for (int i = 0; i < channels; i++) p[i] = (u8)(em::saturate(c[i]) * 255.0f + 0.5f);
    }
    void set(int x, int y, const em::Vec3& c) {
        u8* p = at(x, y);
        for (int i = 0; i < std::min(channels, 3); i++) p[i] = (u8)(em::saturate(c[i]) * 255.0f + 0.5f);
        if (channels == 4) p[3] = 255;
    }
    em::Vec4 get(int x, int y) const {
        const u8* p = at(x, y);
        em::Vec4 c(0, 0, 0, 1);
        for (int i = 0; i < channels; i++) c[i] = p[i] / 255.0f;
        return c;
    }
    em::Vec4 sampleWrap(int x, int y) const {
        x = ((x % w) + w) % w;
        y = ((y % h) + h) % h;
        return get(x, y);
    }
};

Ref<Texture> makeTexture2D(const Image& img, bool srgb, bool mips = true, GLenum wrap = GL_REPEAT);
Ref<Texture> makeSolidTexture(const em::Vec4& color, bool srgb);
void imageToNormalMap(const Image& height, Image& outNormal, float strength);

}
