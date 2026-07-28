#pragma once

#include "Font.h"
#include "../render/Shader.h"

namespace echo {

enum TextAlign { ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT };

class UIRenderer {
public:
    bool init();
    void shutdown();

    void begin(int width, int height, float time);
    void end();

    void rect(float x, float y, float w, float h, const em::Vec4& color);
    void rectOutline(float x, float y, float w, float h, float thickness, const em::Vec4& color);
    void gradientRect(float x, float y, float w, float h, const em::Vec4& top, const em::Vec4& bottom);
    void gradientRectH(float x, float y, float w, float h, const em::Vec4& left, const em::Vec4& right);
    void text(const std::string& s, float x, float y, float size, const em::Vec4& color, int align = ALIGN_LEFT, float tracking = 0.0f);
    void textShadow(const std::string& s, float x, float y, float size, const em::Vec4& color, int align = ALIGN_LEFT, float tracking = 0.0f);
    void textBlock(const std::vector<std::string>& lines, float x, float y, float size, const em::Vec4& color, int align = ALIGN_LEFT, float lineGap = 1.35f);
    void crosshair(float x, float y, float size, float openAmount, const em::Vec4& color);
    void circle(float cx, float cy, float radius, int segments, const em::Vec4& color);
    void triangle(const em::Vec2& a, const em::Vec2& b, const em::Vec2& c, const em::Vec4& color);
    void diamond(float cx, float cy, float radius, const em::Vec4& color);
    void image(float x, float y, float w, float h, GLuint texture, const em::Vec4& tint);
    void imageUV(float x, float y, float w, float h, GLuint texture, const em::Vec4& tint,
                 float u0, float v0, float u1, float v1);
    void rotatedQuad(float cx, float cy, float w, float h, float angle, const em::Vec4& color);
    void arrow(float cx, float cy, float radius, float angle, const em::Vec4& color);
    void ring(float cx, float cy, float radius, float thickness, float fraction, const em::Vec4& color);

    Font& font() { return fontData; }
    const Font& font() const { return fontData; }
    int width() const { return screenW; }
    int height() const { return screenH; }

private:
    struct UIVertex {
        em::Vec2 pos;
        em::Vec2 uv;
        float color[4];
    };

    void flush();
    void setMode(int mode, GLuint tex);
    void pushQuad(float x, float y, float w, float h, float u0, float v0, float u1, float v1, const em::Vec4& c);
    void pushQuadColors(float x, float y, float w, float h, const em::Vec4& c0, const em::Vec4& c1, const em::Vec4& c2, const em::Vec4& c3);
    void pushTri(const em::Vec2& a, const em::Vec2& b, const em::Vec2& c, const em::Vec4& color);

    Shader shader;
    Font fontData;
    GLuint vao = 0, vbo = 0;
    std::vector<UIVertex> vertices;
    int currentMode = -1;
    GLuint currentTex = 0;
    int screenW = 1, screenH = 1;
    float time_ = 0.0f;
};

}
