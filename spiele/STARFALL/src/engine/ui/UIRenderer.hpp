#pragma once

#include "../core/Result.hpp"
#include "../math/Vec2.hpp"
#include "../math/Vec4.hpp"
#include "../render/GLApi.hpp"
#include "../render/Shader.hpp"

#include <string>
#include <vector>

namespace sf {

enum class TextAlign : u32 {
    Left = 0,
    Center,
    Right
};

struct UIStyle {
    Vec4 panelFill = Vec4(0.02f, 0.05f, 0.07f, 0.72f);
    Vec4 panelEdge = Vec4(0.18f, 0.86f, 0.88f, 0.55f);
    Vec4 accent = Vec4(0.24f, 0.94f, 0.92f, 1.0f);
    Vec4 accentDim = Vec4(0.14f, 0.52f, 0.55f, 1.0f);
    Vec4 warning = Vec4(1.0f, 0.72f, 0.24f, 1.0f);
    Vec4 danger = Vec4(1.0f, 0.34f, 0.28f, 1.0f);
    Vec4 text = Vec4(0.86f, 0.95f, 0.97f, 1.0f);
    Vec4 textDim = Vec4(0.52f, 0.63f, 0.68f, 1.0f);
    Vec4 voidGold = Vec4(1.0f, 0.78f, 0.38f, 1.0f);
    f32 gridSpacing = 26.0f;
};

class UIRenderer {
public:
    Status initialize();
    void release();

    void beginFrame(u32 width, u32 height);
    void endFrame();

    void drawRect(f32 x, f32 y, f32 width, f32 height, const Vec4& color);
    void drawRectOutline(f32 x, f32 y, f32 width, f32 height, f32 thickness, const Vec4& color);
    void drawLine(f32 fromX, f32 fromY, f32 toX, f32 toY, f32 thickness, const Vec4& color);
    void drawCircleOutline(f32 centerX, f32 centerY, f32 radius, f32 thickness, u32 segments, const Vec4& color);
    void drawHologramPanel(f32 x, f32 y, f32 width, f32 height, const UIStyle& style, f32 glowPulse);
    void drawText(const std::string& text, f32 x, f32 y, f32 scale, const Vec4& color, TextAlign align = TextAlign::Left);
    void drawTextShadowed(const std::string& text, f32 x, f32 y, f32 scale, const Vec4& color,
                          TextAlign align = TextAlign::Left);
    void drawProgressBar(f32 x, f32 y, f32 width, f32 height, f32 fraction, const Vec4& fill, const Vec4& frame);

    f32 textWidth(const std::string& text, f32 scale) const;
    f32 textHeight(f32 scale) const;

    u32 surfaceWidth() const { return viewportWidth; }
    u32 surfaceHeight() const { return viewportHeight; }
    const UIStyle& style() const { return activeStyle; }
    UIStyle& mutableStyle() { return activeStyle; }

private:
    struct Vertex {
        f32 x = 0.0f;
        f32 y = 0.0f;
        f32 u = 0.0f;
        f32 v = 0.0f;
        f32 red = 1.0f;
        f32 green = 1.0f;
        f32 blue = 1.0f;
        f32 alpha = 1.0f;
        f32 textured = 0.0f;
    };

    void pushQuad(f32 x, f32 y, f32 width, f32 height, f32 u0, f32 v0, f32 u1, f32 v1, const Vec4& color,
                  bool textured);
    void flush();
    void buildFontTexture();

    Shader shader;
    GLuint vertexArray = 0;
    GLuint vertexBuffer = 0;
    GLuint fontTexture = 0;
    std::vector<Vertex> vertices;
    u32 viewportWidth = 0;
    u32 viewportHeight = 0;
    UIStyle activeStyle;
};

}
