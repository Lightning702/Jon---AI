#include "Font.h"
#include "../core/Log.h"
#include "../core/Parallel.h"

using namespace em;

namespace echo {

namespace {

struct GlyphDef {
    char c;
    const char* strokes;
    float advance;
};

const GlyphDef kGlyphs[] = {
    { 'A', "0004264440|0242", 5.0f },
    { 'B', "00063645443303|3342413000", 5.0f },
    { 'C', "4536160501103041", 5.0f },
    { 'D', "00063645413000", 5.0f },
    { 'E', "46060040|0333", 5.0f },
    { 'F', "460600|0333", 5.0f },
    { 'G', "45361605011030414323", 5.0f },
    { 'H', "0006|4046|0343", 5.0f },
    { 'I', "1636|2620|1030", 4.0f },
    { 'J', "4641301001", 5.0f },
    { 'K', "0006|460340", 5.0f },
    { 'L', "060040", 5.0f },
    { 'M', "0006234640", 5.0f },
    { 'N', "00064046", 5.0f },
    { 'O', "100105163645413010", 5.0f },
    { 'P', "00063645443303", 5.0f },
    { 'Q', "100105163645413010|2240", 5.0f },
    { 'R', "00063645443303|2340", 5.0f },
    { 'S', "011030414233130405163645", 5.0f },
    { 'T', "0646|2620", 5.0f },
    { 'U', "060110304146", 5.0f },
    { 'V', "062046", 5.0f },
    { 'W', "0610233046", 5.0f },
    { 'X', "0046|0640", 5.0f },
    { 'Y', "062346|2320", 5.0f },
    { 'Z', "06460040", 5.0f },
    { '0', "100105163645413010|0145", 5.0f },
    { '1', "152620|1030", 4.0f },
    { '2', "05163645440040", 5.0f },
    { '3', "0646234241301001", 5.0f },
    { '4', "30360242", 5.0f },
    { '5', "460604344341301001", 5.0f },
    { '6', "4536160501103041423303", 5.0f },
    { '7', "064610", 5.0f },
    { '8', "13040516364544331302011030414233", 5.0f },
    { '9', "0110304145361605041343", 5.0f },
    { '.', "2020", 2.0f },
    { ',', "2110", 2.0f },
    { ':', "2121|2424", 2.0f },
    { ';', "2424|2110", 2.0f },
    { '-', "1333", 4.0f },
    { '_', "0040", 5.0f },
    { '!', "2622|2020", 2.0f },
    { '?', "05163645442322|2020", 5.0f },
    { '\'', "2625", 2.0f },
    { '"', "1615|3635", 4.0f },
    { '(', "36141230", 3.0f },
    { ')', "16343210", 3.0f },
    { '/', "0046", 5.0f },
    { '\\', "0640", 5.0f },
    { '+', "2125|0343", 5.0f },
    { '=', "0242|0444", 5.0f },
    { '*', "2226|0345|0543", 5.0f },
    { '<', "360330", 4.0f },
    { '>', "163410", 4.0f },
    { '[', "36161030", 3.0f },
    { ']', "16363010", 3.0f },
    { '%', "0046|0516|3041", 5.0f },
    { '#', "1610|3630|0444|0242", 5.0f },
    { '&', "4005163634231041", 5.0f },
    { '|', "2620", 2.0f },
};

struct Seg {
    Vec2 a, b;
};

float distToSegment(const Vec2& p, const Vec2& a, const Vec2& b) {
    Vec2 ab = b - a;
    float len2 = lengthSq(ab);
    if (len2 < 1e-8f) return length(p - a);
    float t = clampf(dot(p - a, ab) / len2, 0.0f, 1.0f);
    return length(p - (a + ab * t));
}

void parseStrokes(const char* s, std::vector<Seg>& out) {
    out.clear();
    std::vector<Vec2> poly;
    for (const char* p = s; *p; ) {
        if (*p == '|') {
            for (size_t i = 0; i + 1 < poly.size(); i++) out.push_back({ poly[i], poly[i + 1] });
            if (poly.size() == 1) out.push_back({ poly[0], poly[0] });
            poly.clear();
            p++;
            continue;
        }
        if (*p == ' ') { p++; continue; }
        if (!p[1]) break;
        float x = (float)(p[0] - '0');
        float y = (float)(p[1] - '0');
        poly.push_back(Vec2(x, y));
        p += 2;
    }
    for (size_t i = 0; i + 1 < poly.size(); i++) out.push_back({ poly[i], poly[i + 1] });
    if (poly.size() == 1) out.push_back({ poly[0], poly[0] });
}

}

void Font::build(int cellSize) {
    cell = std::max(cellSize, 16);
    const int cols = 16, rows = 8;
    const int texW = cols * cell, texH = rows * cell;

    Image img;
    img.allocate(texW, texH, 1);
    std::fill(img.data.begin(), img.data.end(), (u8)0);

    for (int i = 0; i < 128; i++) {
        glyphs[i] = Glyph();
        glyphs[i].empty = true;
        glyphs[i].advance = 0.34f;
        glyphs[i].width = 0.0f;
    }

    const float gridW = 4.0f, gridH = 6.0f;
    const float pad = 0.22f;
    const float thickness = 0.62f;

    int count = (int)(sizeof(kGlyphs) / sizeof(kGlyphs[0]));
    for (int gi = 0; gi < count; gi++) {
        const GlyphDef& def = kGlyphs[gi];
        int code = (unsigned char)def.c;
        if (code >= 128) continue;

        int cx = (code - 32) % cols;
        int cy = (code - 32) / cols;
        if (cy >= rows) continue;

        std::vector<Seg> segs;
        parseStrokes(def.strokes, segs);
        if (segs.empty()) continue;

        float aspect = def.advance / (gridH + pad * 2.0f);

        for (int y = 0; y < cell; y++) {
            for (int x = 0; x < cell; x++) {
                float fx = ((float)x + 0.5f) / cell;
                float fy = ((float)y + 0.5f) / cell;
                float gx = fx * (gridW + pad * 2.0f) - pad;
                float gy = (1.0f - fy) * (gridH + pad * 2.0f) - pad;
                Vec2 p(gx, gy);

                float d = 1e9f;
                for (const Seg& s : segs) d = std::min(d, distToSegment(p, s.a, s.b));

                float sd = (thickness * 0.5f - d) / (thickness * 0.9f);
                float value = clampf(sd + 0.5f, 0.0f, 1.0f);
                img.data[(size_t)((cy * cell + y) * texW + (cx * cell + x))] = (u8)(value * 255.0f);
            }
        }

        Glyph& g = glyphs[code];
        g.u0 = (float)(cx * cell) / texW;
        g.v0 = (float)(cy * cell) / texH;
        g.u1 = (float)((cx + 1) * cell) / texW;
        g.v1 = (float)((cy + 1) * cell) / texH;
        g.advance = (def.advance + 1.35f) / (gridH + pad * 2.0f);
        g.width = (gridW + pad * 2.0f) / (gridH + pad * 2.0f);
        g.empty = false;
    }

    for (int c = 'a'; c <= 'z'; c++) glyphs[c] = glyphs[c - 32];
    glyphs[' '].empty = true;
    glyphs[' '].advance = 0.40f;

    atlas = makeTexture2D(img, false, false, GL_CLAMP_TO_EDGE);
    glBindTexture(GL_TEXTURE_2D, atlas->id());
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glBindTexture(GL_TEXTURE_2D, 0);

    LOG_INFO("Font atlas built %dx%d (%d glyphs)", texW, texH, count);
}

void Font::destroy() {
    atlas.reset();
}

const Glyph& Font::glyph(char c) const {
    unsigned char code = (unsigned char)c;
    if (code >= 128) code = '?';
    return glyphs[code];
}

float Font::measure(const std::string& text, float size, float tracking) const {
    float w = 0.0f;
    for (char c : text) w += glyph(c).advance * size + tracking;
    return w;
}

std::vector<std::string> Font::wrap(const std::string& text, float size, float maxWidth, float tracking) const {
    std::vector<std::string> lines;
    std::string current;
    std::string word;

    auto flushWord = [&]() {
        if (word.empty()) return;
        std::string test = current.empty() ? word : current + " " + word;
        if (measure(test, size, tracking) > maxWidth && !current.empty()) {
            lines.push_back(current);
            current = word;
        } else {
            current = test;
        }
        word.clear();
    };

    for (char c : text) {
        if (c == '\n') {
            flushWord();
            lines.push_back(current);
            current.clear();
        } else if (c == ' ') {
            flushWord();
        } else {
            word.push_back(c);
        }
    }
    flushWord();
    if (!current.empty()) lines.push_back(current);
    return lines;
}

}
