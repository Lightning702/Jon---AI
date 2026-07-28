#include "UIRenderer.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

bool UIRenderer::init() {
    if (!shader.loadFromFiles("shaders/ui.vert", "shaders/ui.frag")) return false;
    fontData.build(40);

    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(UIVertex) * 8192, nullptr, GL_STREAM_DRAW);

    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, sizeof(UIVertex), (void*)offsetof(UIVertex, pos));
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, sizeof(UIVertex), (void*)offsetof(UIVertex, uv));
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, sizeof(UIVertex), (void*)offsetof(UIVertex, color));
    glBindVertexArray(0);

    vertices.reserve(8192);
    return true;
}

void UIRenderer::shutdown() {
    fontData.destroy();
    shader.destroy();
    if (vbo) { glDeleteBuffers(1, &vbo); vbo = 0; }
    if (vao) { glDeleteVertexArrays(1, &vao); vao = 0; }
}

void UIRenderer::begin(int width, int height, float time) {
    screenW = std::max(width, 1);
    screenH = std::max(height, 1);
    time_ = time;
    vertices.clear();
    currentMode = -1;
    currentTex = 0;

    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glDisable(GL_CULL_FACE);
    glEnable(GL_BLEND);
    glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
    glViewport(0, 0, screenW, screenH);

    shader.bind();
    Mat4 proj = Mat4::ortho(0.0f, (float)screenW, (float)screenH, 0.0f, -1.0f, 1.0f);
    shader.setMat4("uProjection", proj);
    shader.setFloat("uSmoothing", 0.02f);
    shader.setFloat("uTime", time_);
}

void UIRenderer::end() {
    flush();
    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_TRUE);
    glEnable(GL_CULL_FACE);
    glDisable(GL_BLEND);
}

void UIRenderer::setMode(int mode, GLuint tex) {
    if (mode == currentMode && tex == currentTex) return;
    flush();
    currentMode = mode;
    currentTex = tex;
    shader.setInt("uMode", mode);
    if (tex) {
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, tex);
        shader.setInt("uTexture", 0);
    }
}

void UIRenderer::flush() {
    if (vertices.empty()) return;
    glBindVertexArray(vao);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    size_t bytes = vertices.size() * sizeof(UIVertex);
    static size_t capacity = sizeof(UIVertex) * 8192;
    if (bytes > capacity) {
        capacity = bytes * 2;
        glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)capacity, nullptr, GL_STREAM_DRAW);
    }
    glBufferSubData(GL_ARRAY_BUFFER, 0, (GLsizeiptr)bytes, vertices.data());
    glDrawArrays(GL_TRIANGLES, 0, (GLsizei)vertices.size());
    glBindVertexArray(0);
    vertices.clear();
}

void UIRenderer::pushQuadColors(float x, float y, float w, float h, const Vec4& c0, const Vec4& c1, const Vec4& c2, const Vec4& c3) {
    auto add = [&](float px, float py, float u, float v, const Vec4& c) {
        UIVertex vtx;
        vtx.pos = Vec2(px, py);
        vtx.uv = Vec2(u, v);
        vtx.color[0] = c.x; vtx.color[1] = c.y; vtx.color[2] = c.z; vtx.color[3] = c.w;
        vertices.push_back(vtx);
    };
    add(x, y, 0, 0, c0);
    add(x + w, y, 1, 0, c1);
    add(x + w, y + h, 1, 1, c2);
    add(x, y, 0, 0, c0);
    add(x + w, y + h, 1, 1, c2);
    add(x, y + h, 0, 1, c3);
}

void UIRenderer::pushQuad(float x, float y, float w, float h, float u0, float v0, float u1, float v1, const Vec4& c) {
    auto add = [&](float px, float py, float u, float v) {
        UIVertex vtx;
        vtx.pos = Vec2(px, py);
        vtx.uv = Vec2(u, v);
        vtx.color[0] = c.x; vtx.color[1] = c.y; vtx.color[2] = c.z; vtx.color[3] = c.w;
        vertices.push_back(vtx);
    };
    add(x, y, u0, v0);
    add(x + w, y, u1, v0);
    add(x + w, y + h, u1, v1);
    add(x, y, u0, v0);
    add(x + w, y + h, u1, v1);
    add(x, y + h, u0, v1);
}

void UIRenderer::pushTri(const Vec2& a, const Vec2& b, const Vec2& c, const Vec4& color) {
    auto add = [&](const Vec2& p) {
        UIVertex vtx;
        vtx.pos = p;
        vtx.uv = Vec2(0, 0);
        vtx.color[0] = color.x; vtx.color[1] = color.y; vtx.color[2] = color.z; vtx.color[3] = color.w;
        vertices.push_back(vtx);
    };
    add(a); add(b); add(c);
}

void UIRenderer::rect(float x, float y, float w, float h, const Vec4& color) {
    if (color.w <= 0.001f) return;
    setMode(0, 0);
    pushQuad(x, y, w, h, 0, 0, 1, 1, color);
}

void UIRenderer::gradientRect(float x, float y, float w, float h, const Vec4& top, const Vec4& bottom) {
    setMode(0, 0);
    pushQuadColors(x, y, w, h, top, top, bottom, bottom);
}

void UIRenderer::gradientRectH(float x, float y, float w, float h, const Vec4& left, const Vec4& right) {
    setMode(0, 0);
    pushQuadColors(x, y, w, h, left, right, right, left);
}

void UIRenderer::rectOutline(float x, float y, float w, float h, float t, const Vec4& color) {
    rect(x, y, w, t, color);
    rect(x, y + h - t, w, t, color);
    rect(x, y + t, t, h - t * 2, color);
    rect(x + w - t, y + t, t, h - t * 2, color);
}

void UIRenderer::text(const std::string& s, float x, float y, float size, const Vec4& color, int align, float tracking) {
    if (color.w <= 0.002f || s.empty()) return;
    setMode(1, fontData.texture());

    float total = fontData.measure(s, size, tracking);
    float cursor = x;
    if (align == ALIGN_CENTER) cursor -= total * 0.5f;
    else if (align == ALIGN_RIGHT) cursor -= total;

    for (char c : s) {
        const Glyph& g = fontData.glyph(c);
        if (!g.empty) {
            float gw = g.width * size;
            pushQuad(cursor, y, gw, size, g.u0, g.v0, g.u1, g.v1, color);
        }
        cursor += g.advance * size + tracking;
    }
}

void UIRenderer::textShadow(const std::string& s, float x, float y, float size, const Vec4& color, int align, float tracking) {
    float o = std::max(1.0f, size * 0.055f);
    text(s, x + o, y + o, size, Vec4(0, 0, 0, color.w * 0.8f), align, tracking);
    text(s, x, y, size, color, align, tracking);
}

void UIRenderer::textBlock(const std::vector<std::string>& lines, float x, float y, float size, const Vec4& color, int align, float lineGap) {
    float ly = y;
    for (const auto& line : lines) {
        text(line, x, ly, size, color, align);
        ly += size * lineGap;
    }
}

void UIRenderer::crosshair(float x, float y, float size, float openAmount, const Vec4& color) {
    setMode(0, 0);
    float gap = size * (0.35f + openAmount * 0.65f);
    float len = size * 0.42f;
    float t = std::max(1.0f, size * 0.075f);
    pushQuad(x - gap - len, y - t * 0.5f, len, t, 0, 0, 1, 1, color);
    pushQuad(x + gap, y - t * 0.5f, len, t, 0, 0, 1, 1, color);
    pushQuad(x - t * 0.5f, y - gap - len, t, len, 0, 0, 1, 1, color);
    pushQuad(x - t * 0.5f, y + gap, t, len, 0, 0, 1, 1, color);
}

void UIRenderer::triangle(const Vec2& a, const Vec2& b, const Vec2& c, const Vec4& color) {
    setMode(0, 0);
    pushTri(a, b, c, color);
}

void UIRenderer::diamond(float cx, float cy, float r, const Vec4& color) {
    setMode(0, 0);
    pushTri(Vec2(cx, cy - r), Vec2(cx + r, cy), Vec2(cx, cy + r), color);
    pushTri(Vec2(cx, cy - r), Vec2(cx, cy + r), Vec2(cx - r, cy), color);
}

void UIRenderer::image(float x, float y, float w, float h, GLuint texture, const Vec4& tint) {
    imageUV(x, y, w, h, texture, tint, 0.0f, 0.0f, 1.0f, 1.0f);
}

void UIRenderer::imageUV(float x, float y, float w, float h, GLuint texture, const Vec4& tint,
                         float u0, float v0, float u1, float v1) {
    if (!texture) return;
    setMode(2, texture);
    pushQuad(x, y, w, h, u0, v0, u1, v1, tint);
}

void UIRenderer::rotatedQuad(float cx, float cy, float w, float h, float angle, const Vec4& color) {
    setMode(0, 0);
    float c = std::cos(angle), s = std::sin(angle);
    Vec2 hx(c * w * 0.5f, s * w * 0.5f);
    Vec2 hy(-s * h * 0.5f, c * h * 0.5f);
    Vec2 p0(cx - hx.x - hy.x, cy - hx.y - hy.y);
    Vec2 p1(cx + hx.x - hy.x, cy + hx.y - hy.y);
    Vec2 p2(cx + hx.x + hy.x, cy + hx.y + hy.y);
    Vec2 p3(cx - hx.x + hy.x, cy - hx.y + hy.y);
    pushTri(p0, p1, p2, color);
    pushTri(p0, p2, p3, color);
}

void UIRenderer::arrow(float cx, float cy, float radius, float angle, const Vec4& color) {
    setMode(0, 0);
    float c = std::cos(angle), s = std::sin(angle);
    auto rot = [&](float ax, float ay) { return Vec2(cx + ax * c - ay * s, cy + ax * s + ay * c); };
    pushTri(rot(0.0f, -radius), rot(radius * 0.72f, radius * 0.72f), rot(0.0f, radius * 0.30f), color);
    pushTri(rot(0.0f, -radius), rot(0.0f, radius * 0.30f), rot(-radius * 0.72f, radius * 0.72f), color);
}

void UIRenderer::circle(float cx, float cy, float radius, int segments, const Vec4& color) {
    setMode(0, 0);
    if (segments < 3) segments = 3;
    for (int i = 0; i < segments; i++) {
        float a0 = TAU * i / segments;
        float a1 = TAU * (i + 1) / segments;
        pushTri(Vec2(cx, cy),
                Vec2(cx + std::cos(a0) * radius, cy + std::sin(a0) * radius),
                Vec2(cx + std::cos(a1) * radius, cy + std::sin(a1) * radius), color);
    }
}

void UIRenderer::ring(float cx, float cy, float radius, float thickness, float fraction, const Vec4& color) {
    setMode(0, 0);
    int segments = 64;
    int count = clampi((int)(segments * clampf(fraction, 0.0f, 1.0f)), 0, segments);
    float inner = radius - thickness;
    for (int i = 0; i < count; i++) {
        float a0 = -HALF_PI + TAU * i / segments;
        float a1 = -HALF_PI + TAU * (i + 1) / segments;
        Vec2 o0(cx + std::cos(a0) * radius, cy + std::sin(a0) * radius);
        Vec2 o1(cx + std::cos(a1) * radius, cy + std::sin(a1) * radius);
        Vec2 i0(cx + std::cos(a0) * inner, cy + std::sin(a0) * inner);
        Vec2 i1(cx + std::cos(a1) * inner, cy + std::sin(a1) * inner);
        pushTri(i0, o0, o1, color);
        pushTri(i0, o1, i1, color);
    }
}

}
