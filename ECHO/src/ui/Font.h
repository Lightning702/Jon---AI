#pragma once

#include "../render/Texture.h"

namespace echo {

struct Glyph {
    float u0 = 0, v0 = 0, u1 = 1, v1 = 1;
    float advance = 0.6f;
    float width = 0.6f;
    bool empty = true;
};

class Font {
public:
    void build(int cellSize);
    void destroy();

    const Glyph& glyph(char c) const;
    GLuint texture() const { return atlas ? atlas->id() : 0; }
    float measure(const std::string& text, float size, float tracking = 0.0f) const;
    float lineHeight(float size) const { return size * 1.45f; }
    std::vector<std::string> wrap(const std::string& text, float size, float maxWidth, float tracking = 0.0f) const;

private:
    Ref<Texture> atlas;
    Glyph glyphs[128];
    int cell = 32;
};

}
