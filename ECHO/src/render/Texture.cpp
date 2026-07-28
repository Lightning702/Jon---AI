#include "Texture.h"
#include "../core/Log.h"

namespace echo {

void Texture::applyParams() {
    GLenum t = desc.target;
    glTexParameteri(t, GL_TEXTURE_MIN_FILTER, desc.minFilter);
    glTexParameteri(t, GL_TEXTURE_MAG_FILTER, desc.magFilter);
    glTexParameteri(t, GL_TEXTURE_WRAP_S, desc.wrap);
    glTexParameteri(t, GL_TEXTURE_WRAP_T, desc.wrap);
    if (t == GL_TEXTURE_3D || t == GL_TEXTURE_2D_ARRAY || t == GL_TEXTURE_CUBE_MAP)
        glTexParameteri(t, GL_TEXTURE_WRAP_R, desc.wrap);
    if (desc.wrap == GL_CLAMP_TO_BORDER)
        glTexParameterfv(t, GL_TEXTURE_BORDER_COLOR, &desc.borderColor.x);
    if (desc.anisotropic && desc.mipmaps && glHasAnisotropy())
        glTexParameterf(t, GL_TEXTURE_MAX_ANISOTROPY, std::min(16.0f, glMaxAnisotropy()));
    if (desc.shadowCompare) {
        glTexParameteri(t, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE);
        glTexParameteri(t, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL);
    }
}

void Texture::create(const TextureDesc& d, const void* pixels) {
    destroy();
    desc = d;
    glGenTextures(1, &tex);
    glBindTexture(desc.target, tex);

    if (desc.target == GL_TEXTURE_2D) {
        glTexImage2D(GL_TEXTURE_2D, 0, desc.internalFormat, desc.width, desc.height, 0, desc.format, desc.type, pixels);
    } else if (desc.target == GL_TEXTURE_2D_ARRAY || desc.target == GL_TEXTURE_3D) {
        glTexImage3D(desc.target, 0, desc.internalFormat, desc.width, desc.height, desc.depth, 0, desc.format, desc.type, pixels);
    } else if (desc.target == GL_TEXTURE_CUBE_MAP) {
        for (int i = 0; i < 6; i++)
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, desc.internalFormat, desc.width, desc.height, 0, desc.format, desc.type, nullptr);
    }

    applyParams();
    if (desc.mipmaps && pixels) glGenerateMipmap(desc.target);
    glBindTexture(desc.target, 0);
}

void Texture::update(const void* pixels, int level) {
    if (!tex) return;
    glBindTexture(desc.target, tex);
    if (desc.target == GL_TEXTURE_2D)
        glTexSubImage2D(GL_TEXTURE_2D, level, 0, 0, desc.width >> level, desc.height >> level, desc.format, desc.type, pixels);
    else if (desc.target == GL_TEXTURE_2D_ARRAY || desc.target == GL_TEXTURE_3D)
        glTexSubImage3D(desc.target, level, 0, 0, 0, desc.width, desc.height, desc.depth, desc.format, desc.type, pixels);
    glBindTexture(desc.target, 0);
}

void Texture::updateLayer(const void* pixels, int layer) {
    if (!tex) return;
    glBindTexture(desc.target, tex);
    glTexSubImage3D(desc.target, 0, 0, 0, layer, desc.width, desc.height, 1, desc.format, desc.type, pixels);
    glBindTexture(desc.target, 0);
}

void Texture::generateMips() {
    if (!tex) return;
    glBindTexture(desc.target, tex);
    glGenerateMipmap(desc.target);
    glBindTexture(desc.target, 0);
}

void Texture::resize(int w, int h) {
    if (w == desc.width && h == desc.height) return;
    TextureDesc d = desc;
    d.width = w;
    d.height = h;
    create(d, nullptr);
}

void Texture::destroy() {
    if (tex) { glDeleteTextures(1, &tex); tex = 0; }
}

void Texture::bind(int unit) const {
    glActiveTexture(GL_TEXTURE0 + unit);
    glBindTexture(desc.target, tex);
}

Ref<Texture> makeTexture2D(const Image& img, bool srgb, bool mips, GLenum wrap) {
    TextureDesc d;
    d.width = img.w;
    d.height = img.h;
    d.target = GL_TEXTURE_2D;
    d.mipmaps = mips;
    d.wrap = wrap;
    d.minFilter = mips ? GL_LINEAR_MIPMAP_LINEAR : GL_LINEAR;
    switch (img.channels) {
    case 1: d.internalFormat = GL_R8; d.format = GL_RED; break;
    case 2: d.internalFormat = GL_RG8; d.format = GL_RG; break;
    case 3: d.internalFormat = srgb ? GL_SRGB8 : GL_RGB8; d.format = GL_RGB; break;
    default: d.internalFormat = srgb ? GL_SRGB8_ALPHA8 : GL_RGBA8; d.format = GL_RGBA; break;
    }
    d.type = GL_UNSIGNED_BYTE;
    auto t = std::make_shared<Texture>();
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    t->create(d, img.data.data());
    glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
    return t;
}

Ref<Texture> makeSolidTexture(const em::Vec4& color, bool srgb) {
    Image img;
    img.allocate(2, 2, 4);
    for (int y = 0; y < 2; y++) for (int x = 0; x < 2; x++) img.set(x, y, color);
    return makeTexture2D(img, srgb, false);
}

void imageToNormalMap(const Image& height, Image& outNormal, float strength) {
    outNormal.allocate(height.w, height.h, 3);
    for (int y = 0; y < height.h; y++) {
        for (int x = 0; x < height.w; x++) {
            float l = height.sampleWrap(x - 1, y).x;
            float r = height.sampleWrap(x + 1, y).x;
            float d = height.sampleWrap(x, y - 1).x;
            float u = height.sampleWrap(x, y + 1).x;
            em::Vec3 n = em::normalize(em::Vec3((l - r) * strength, (d - u) * strength, 1.0f));
            outNormal.set(x, y, em::Vec3(n.x * 0.5f + 0.5f, n.y * 0.5f + 0.5f, n.z * 0.5f + 0.5f));
        }
    }
}

}
