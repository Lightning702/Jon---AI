#include "UIRenderer.hpp"

#include "../core/Log.hpp"
#include "../math/Scalar.hpp"
#include "FontAtlas.hpp"

namespace sf {
namespace {

constexpr u32 kAtlasColumns = 16;
constexpr u32 kAtlasRows = 6;
constexpr u32 kCellWidth = 8;
constexpr u32 kCellHeight = 8;
constexpr u32 kAtlasWidth = kAtlasColumns * kCellWidth;
constexpr u32 kAtlasHeight = kAtlasRows * kCellHeight;
constexpr f32 kGlyphAdvance = 6.0f;

const char* const kUiVertexSource = R"GLSL(#version 330 core
layout(location = 0) in vec2 aPosition;
layout(location = 1) in vec2 aTexcoord;
layout(location = 2) in vec4 aColor;
layout(location = 3) in float aTextured;

uniform vec2 uSurfaceSize;

out vec2 vTexcoord;
out vec4 vColor;
out float vTextured;

void main() {
    vTexcoord = aTexcoord;
    vColor = aColor;
    vTextured = aTextured;
    vec2 normalized = vec2(aPosition.x / uSurfaceSize.x, 1.0 - aPosition.y / uSurfaceSize.y);
    gl_Position = vec4(normalized * 2.0 - 1.0, 0.0, 1.0);
}
)GLSL";

const char* const kUiFragmentSource = R"GLSL(#version 330 core
in vec2 vTexcoord;
in vec4 vColor;
in float vTextured;
out vec4 fragColor;

uniform sampler2D uFont;

void main() {
    float coverage = 1.0;
    if (vTextured > 0.5) {
        coverage = texture(uFont, vTexcoord).r;
        if (coverage < 0.04) discard;
    }
    fragColor = vec4(vColor.rgb, vColor.a * coverage);
}
)GLSL";

}

Status UIRenderer::initialize() {
    const Status compiled = shader.compile("UserInterface", kUiVertexSource, kUiFragmentSource);
    if (!compiled.ok()) return compiled;

    GLApi& api = gl();
    api.genVertexArrays(1, &vertexArray);
    api.genBuffers(1, &vertexBuffer);
    api.bindVertexArray(vertexArray);
    api.bindBuffer(GL_ARRAY_BUFFER, vertexBuffer);
    api.bufferData(GL_ARRAY_BUFFER, 0, nullptr, GL_DYNAMIC_DRAW);

    api.enableVertexAttribArray(0);
    api.vertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void*>(0));
    api.enableVertexAttribArray(1);
    api.vertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void*>(sizeof(f32) * 2));
    api.enableVertexAttribArray(2);
    api.vertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void*>(sizeof(f32) * 4));
    api.enableVertexAttribArray(3);
    api.vertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, sizeof(Vertex), reinterpret_cast<const void*>(sizeof(f32) * 8));
    api.bindVertexArray(0);

    buildFontTexture();
    logInfo("ui", "Oberflaeche bereit");
    return statusOk();
}

void UIRenderer::buildFontTexture() {
    std::vector<u8> pixels(static_cast<usize>(kAtlasWidth) * kAtlasHeight, 0);
    for (u32 glyph = 0; glyph < kGlyphCount; ++glyph) {
        const u32 cellX = (glyph % kAtlasColumns) * kCellWidth;
        const u32 cellY = (glyph / kAtlasColumns) * kCellHeight;
        const u8* columns = glyphColumns(kGlyphFirst + glyph);
        for (u32 column = 0; column < kGlyphColumns; ++column) {
            for (u32 row = 0; row < kGlyphRows; ++row) {
                if ((columns[column] & (1u << row)) == 0) continue;
                const u32 x = cellX + column;
                const u32 y = cellY + row;
                pixels[static_cast<usize>(y) * kAtlasWidth + x] = 255;
            }
        }
    }

    glGenTextures(1, &fontTexture);
    glBindTexture(GL_TEXTURE_2D, fontTexture);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_R8, static_cast<GLsizei>(kAtlasWidth), static_cast<GLsizei>(kAtlasHeight), 0,
                 GL_RED, GL_UNSIGNED_BYTE, pixels.data());
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
}

void UIRenderer::release() {
    GLApi& api = gl();
    if (fontTexture != 0) glDeleteTextures(1, &fontTexture);
    if (vertexBuffer != 0) api.deleteBuffers(1, &vertexBuffer);
    if (vertexArray != 0) api.deleteVertexArrays(1, &vertexArray);
    fontTexture = 0;
    vertexBuffer = 0;
    vertexArray = 0;
    shader.release();
}

void UIRenderer::beginFrame(u32 width, u32 height) {
    viewportWidth = width;
    viewportHeight = height;
    vertices.clear();
}

void UIRenderer::endFrame() {
    flush();
}

void UIRenderer::pushQuad(f32 x, f32 y, f32 width, f32 height, f32 u0, f32 v0, f32 u1, f32 v1, const Vec4& color,
                          bool textured) {
    const f32 texturedFlag = textured ? 1.0f : 0.0f;
    const Vertex topLeft{x, y, u0, v0, color.x, color.y, color.z, color.w, texturedFlag};
    const Vertex topRight{x + width, y, u1, v0, color.x, color.y, color.z, color.w, texturedFlag};
    const Vertex bottomRight{x + width, y + height, u1, v1, color.x, color.y, color.z, color.w, texturedFlag};
    const Vertex bottomLeft{x, y + height, u0, v1, color.x, color.y, color.z, color.w, texturedFlag};

    vertices.push_back(topLeft);
    vertices.push_back(bottomLeft);
    vertices.push_back(bottomRight);
    vertices.push_back(topLeft);
    vertices.push_back(bottomRight);
    vertices.push_back(topRight);
}

void UIRenderer::flush() {
    if (vertices.empty() || !shader.valid()) return;
    GLApi& api = gl();

    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    shader.bind();
    shader.setVec2("uSurfaceSize", static_cast<f32>(viewportWidth), static_cast<f32>(viewportHeight));
    shader.setTextureUnit("uFont", 0);
    api.activeTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, fontTexture);

    api.bindVertexArray(vertexArray);
    api.bindBuffer(GL_ARRAY_BUFFER, vertexBuffer);
    api.bufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(vertices.size() * sizeof(Vertex)), vertices.data(),
                   GL_DYNAMIC_DRAW);
    glDrawArrays(GL_TRIANGLES, 0, static_cast<GLsizei>(vertices.size()));
    api.bindVertexArray(0);

    glDisable(GL_BLEND);
    vertices.clear();
}

void UIRenderer::drawRect(f32 x, f32 y, f32 width, f32 height, const Vec4& color) {
    pushQuad(x, y, width, height, 0.0f, 0.0f, 0.0f, 0.0f, color, false);
}

void UIRenderer::drawRectOutline(f32 x, f32 y, f32 width, f32 height, f32 thickness, const Vec4& color) {
    drawRect(x, y, width, thickness, color);
    drawRect(x, y + height - thickness, width, thickness, color);
    drawRect(x, y + thickness, thickness, height - thickness * 2.0f, color);
    drawRect(x + width - thickness, y + thickness, thickness, height - thickness * 2.0f, color);
}

void UIRenderer::drawLine(f32 fromX, f32 fromY, f32 toX, f32 toY, f32 thickness, const Vec4& color) {
    const f32 deltaX = toX - fromX;
    const f32 deltaY = toY - fromY;
    const f32 lineLength = std::sqrt(deltaX * deltaX + deltaY * deltaY);
    if (lineLength < 0.0001f) return;
    const u32 segments = static_cast<u32>(maxValue(1.0f, lineLength / maxValue(thickness, 1.0f)));
    for (u32 index = 0; index <= segments; ++index) {
        const f32 t = static_cast<f32>(index) / static_cast<f32>(segments);
        const f32 pointX = fromX + deltaX * t;
        const f32 pointY = fromY + deltaY * t;
        drawRect(pointX - thickness * 0.5f, pointY - thickness * 0.5f, thickness, thickness, color);
    }
}

void UIRenderer::drawCircleOutline(f32 centerX, f32 centerY, f32 radius, f32 thickness, u32 segments,
                                   const Vec4& color) {
    if (segments < 3) segments = 3;
    for (u32 index = 0; index < segments; ++index) {
        const f32 angle = static_cast<f32>(index) / static_cast<f32>(segments) * kTwoPi;
        const f32 pointX = centerX + std::cos(angle) * radius;
        const f32 pointY = centerY + std::sin(angle) * radius;
        drawRect(pointX - thickness * 0.5f, pointY - thickness * 0.5f, thickness, thickness, color);
    }
}

void UIRenderer::drawHologramPanel(f32 x, f32 y, f32 width, f32 height, const UIStyle& panelStyle, f32 glowPulse) {
    drawRect(x, y, width, height, panelStyle.panelFill);

    Vec4 edge = panelStyle.panelEdge;
    edge.w *= 0.55f + 0.45f * glowPulse;
    drawRectOutline(x, y, width, height, 1.0f, edge);

    Vec4 gridColor = panelStyle.panelEdge;
    gridColor.w *= 0.10f;
    for (f32 lineY = y + panelStyle.gridSpacing; lineY < y + height; lineY += panelStyle.gridSpacing) {
        drawRect(x + 2.0f, lineY, width - 4.0f, 1.0f, gridColor);
    }

    Vec4 cornerColor = panelStyle.accent;
    cornerColor.w *= 0.85f;
    const f32 cornerLength = minValue(22.0f, minValue(width, height) * 0.3f);
    drawRect(x, y, cornerLength, 2.0f, cornerColor);
    drawRect(x, y, 2.0f, cornerLength, cornerColor);
    drawRect(x + width - cornerLength, y + height - 2.0f, cornerLength, 2.0f, cornerColor);
    drawRect(x + width - 2.0f, y + height - cornerLength, 2.0f, cornerLength, cornerColor);
}

void UIRenderer::drawText(const std::string& text, f32 x, f32 y, f32 scale, const Vec4& color, TextAlign align) {
    f32 cursorX = x;
    if (align == TextAlign::Center) cursorX -= textWidth(text, scale) * 0.5f;
    else if (align == TextAlign::Right) cursorX -= textWidth(text, scale);

    const f32 cellU = 1.0f / static_cast<f32>(kAtlasColumns);
    const f32 cellV = 1.0f / static_cast<f32>(kAtlasRows);

    for (usize index = 0; index < text.size(); ++index) {
        u32 codepoint = static_cast<u8>(text[index]);
        if (codepoint >= 0xC0 && index + 1 < text.size()) {
            const u32 continuation = static_cast<u8>(text[index + 1]);
            if ((continuation & 0xC0) == 0x80) {
                codepoint = ((codepoint & 0x1F) << 6) | (continuation & 0x3F);
                ++index;
            }
        }
        codepoint = mapExtendedCharacter(codepoint);
        if (!glyphExists(codepoint)) codepoint = '?';

        const u32 glyph = codepoint - kGlyphFirst;
        const f32 u0 = static_cast<f32>(glyph % kAtlasColumns) * cellU;
        const f32 v0 = static_cast<f32>(glyph / kAtlasColumns) * cellV;
        const f32 u1 = u0 + cellU * (kGlyphAdvance / static_cast<f32>(kCellWidth));
        const f32 v1 = v0 + cellV * (static_cast<f32>(kGlyphRows) / static_cast<f32>(kCellHeight));

        pushQuad(cursorX, y, kGlyphAdvance * scale, static_cast<f32>(kGlyphRows) * scale, u0, v0, u1, v1, color, true);
        cursorX += kGlyphAdvance * scale;
    }
}

void UIRenderer::drawTextShadowed(const std::string& text, f32 x, f32 y, f32 scale, const Vec4& color,
                                  TextAlign align) {
    Vec4 shadow(0.0f, 0.0f, 0.0f, color.w * 0.75f);
    drawText(text, x + scale, y + scale, scale, shadow, align);
    drawText(text, x, y, scale, color, align);
}

void UIRenderer::drawProgressBar(f32 x, f32 y, f32 width, f32 height, f32 fraction, const Vec4& fill,
                                 const Vec4& frame) {
    drawRectOutline(x, y, width, height, 1.0f, frame);
    const f32 inner = clampValue(fraction, 0.0f, 1.0f) * (width - 4.0f);
    drawRect(x + 2.0f, y + 2.0f, inner, height - 4.0f, fill);
}

f32 UIRenderer::textWidth(const std::string& text, f32 scale) const {
    usize visible = 0;
    for (usize index = 0; index < text.size(); ++index) {
        const u32 codepoint = static_cast<u8>(text[index]);
        if (codepoint >= 0xC0 && index + 1 < text.size() && (static_cast<u8>(text[index + 1]) & 0xC0) == 0x80) {
            ++index;
        }
        ++visible;
    }
    return static_cast<f32>(visible) * kGlyphAdvance * scale;
}

f32 UIRenderer::textHeight(f32 scale) const {
    return static_cast<f32>(kGlyphRows) * scale;
}

}
