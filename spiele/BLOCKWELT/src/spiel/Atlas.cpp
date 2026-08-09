#include "Atlas.hpp"

#include <cmath>
#include <vector>

#include "fw/GL.hpp"

namespace blockwelt {
namespace {

std::vector<unsigned char> bild;
unsigned long long streuzahl = 987234911ull;

float wurf() {
    streuzahl = (streuzahl * 16807ull) % 2147483647ull;
    return static_cast<float>(streuzahl) / 2147483647.0f;
}

void punkt(int kachel, int x, int y, float r, float g, float b, float a = 1.0f) {
    if (x < 0 || y < 0 || x >= KACHEL || y >= KACHEL) return;
    int px = kachel * KACHEL + x;
    size_t i = (static_cast<size_t>(y) * (KACHELN * KACHEL) + px) * 4;
    auto klemme = [](float wert) {
        float k = wert < 0.0f ? 0.0f : (wert > 255.0f ? 255.0f : wert);
        return static_cast<unsigned char>(k);
    };
    if (a >= 0.999f) {
        bild[i + 0] = klemme(r);
        bild[i + 1] = klemme(g);
        bild[i + 2] = klemme(b);
        bild[i + 3] = 255;
        return;
    }
    bild[i + 0] = klemme(bild[i + 0] * (1.0f - a) + r * a);
    bild[i + 1] = klemme(bild[i + 1] * (1.0f - a) + g * a);
    bild[i + 2] = klemme(bild[i + 2] * (1.0f - a) + b * a);
    bild[i + 3] = 255;
}

void grundkachel(int kachel, float r, float g, float b, float streuung) {
    for (int y = 0; y < KACHEL; ++y) {
        for (int x = 0; x < KACHEL; ++x) {
            float f = 1.0f + (wurf() - 0.5f) * streuung;
            punkt(kachel, x, y, r * f, g * f, b * f);
        }
    }
}

}

Atlas::~Atlas() { freigeben(); }

bool Atlas::erstellen() {
    freigeben();
    streuzahl = 987234911ull;
    bild.assign(static_cast<size_t>(KACHELN) * KACHEL * KACHEL * 4, 0);

    grundkachel(0, 109, 176, 66, 0.22f);
    grundkachel(1, 134, 96, 67, 0.22f);
    for (int x = 0; x < KACHEL; ++x) {
        int tiefe = 3 + static_cast<int>(wurf() * 2.0f);
        for (int y = 0; y < tiefe; ++y) {
            float f = 1.0f + (wurf() - 0.5f) * 0.25f;
            punkt(1, x, y, 109 * f, 176 * f, 66 * f);
        }
    }
    grundkachel(2, 134, 96, 67, 0.22f);
    grundkachel(3, 127, 127, 127, 0.16f);
    grundkachel(4, 218, 205, 160, 0.12f);
    grundkachel(5, 52, 104, 220, 0.12f);
    for (int i = 0; i < 8; ++i) {
        punkt(5, static_cast<int>(wurf() * KACHEL), static_cast<int>(wurf() * KACHEL), 110, 160, 240);
    }
    grundkachel(6, 104, 82, 50, 0.15f);
    for (int x = 0; x < KACHEL; ++x) {
        if (wurf() >= 0.35f) continue;
        float f = 0.7f + wurf() * 0.15f;
        for (int y = 0; y < KACHEL; ++y) punkt(6, x, y, 104 * f, 82 * f, 50 * f);
    }
    for (int y = 0; y < KACHEL; ++y) {
        for (int x = 0; x < KACHEL; ++x) {
            float d = std::fmax(std::fabs(x - 7.5f), std::fabs(y - 7.5f));
            float r = 178.0f;
            float g = 143.0f;
            float b = 90.0f;
            if (d > 6.5f) {
                r = 104.0f;
                g = 82.0f;
                b = 50.0f;
            } else if ((static_cast<int>(std::floor(d)) & 1) == 1) {
                r = 150.0f;
                g = 118.0f;
                b = 70.0f;
            }
            float f = 1.0f + (wurf() - 0.5f) * 0.1f;
            punkt(7, x, y, r * f, g * f, b * f);
        }
    }
    grundkachel(8, 58, 138, 48, 0.35f);
    for (int i = 0; i < 18; ++i) {
        int x = static_cast<int>(wurf() * KACHEL);
        int y = static_cast<int>(wurf() * KACHEL);
        punkt(8, x, y, 32, 92, 30);
    }
    grundkachel(9, 240, 246, 250, 0.05f);
    grundkachel(10, 162, 131, 81, 0.12f);
    for (int y = 3; y < KACHEL; y += 4) {
        for (int x = 0; x < KACHEL; ++x) punkt(10, x, y, 110, 89, 55);
    }
    for (int b = 0; b < 4; ++b) {
        int sx = (b * 5 + 3) % KACHEL;
        for (int dy = 0; dy < 3; ++dy) punkt(10, sx, b * 4 + dy, 122, 98, 61);
    }
    grundkachel(11, 198, 232, 240, 0.03f);
    for (int y = 0; y < KACHEL; ++y) {
        for (int x = 0; x < KACHEL; ++x) punkt(11, x, y, 214, 240, 246);
    }
    for (int i = 0; i < KACHEL; ++i) {
        punkt(11, i, 0, 190, 215, 230);
        punkt(11, i, KACHEL - 1, 190, 215, 230);
        punkt(11, 0, i, 190, 215, 230);
        punkt(11, KACHEL - 1, i, 190, 215, 230);
    }
    punkt(11, 3, 3, 245, 252, 255);
    punkt(11, 4, 4, 245, 252, 255);
    punkt(11, 5, 5, 245, 252, 255);
    punkt(11, 10, 8, 240, 250, 255);
    punkt(11, 11, 9, 240, 250, 255);
    grundkachel(12, 122, 122, 122, 0.3f);
    for (int i = 0; i < 9; ++i) {
        int bx = 1 + static_cast<int>(wurf() * 13.0f);
        int by = 1 + static_cast<int>(wurf() * 13.0f);
        float f = 0.65f + wurf() * 0.6f;
        for (int dx = 0; dx < 2; ++dx) {
            for (int dy = 0; dy < 2; ++dy) punkt(12, bx + dx, by + dy, 122 * f, 122 * f, 122 * f);
        }
    }
    grundkachel(13, 168, 160, 152, 0.08f);
    for (int band = 0; band < 4; ++band) {
        int versatz = (band % 2) ? 4 : 0;
        for (int x = 0; x < KACHEL; ++x) {
            if ((x + versatz) % 8 == 7) continue;
            for (int dy = 0; dy < 3; ++dy) {
                float f = 1.0f + (wurf() - 0.5f) * 0.18f;
                punkt(13, x, band * 4 + dy, 146 * f, 90 * f, 77 * f);
            }
        }
    }
    grundkachel(14, 60, 118, 38, 0.15f);
    for (int y = 0; y < KACHEL; ++y) {
        punkt(14, 2, y, 45, 90, 28);
        punkt(14, 6, y, 45, 90, 28);
        punkt(14, 10, y, 45, 90, 28);
        punkt(14, 14, y, 45, 90, 28);
        punkt(14, 0, y, 40, 80, 26);
        punkt(14, 15, y, 40, 80, 26);
    }
    grundkachel(15, 96, 152, 62, 0.12f);
    for (int y = 0; y < KACHEL; ++y) {
        for (int x = 0; x < KACHEL; ++x) {
            float d = std::fmax(std::fabs(x - 7.5f), std::fabs(y - 7.5f));
            if (d > 6.5f) punkt(15, x, y, 60, 118, 38);
        }
    }
    grundkachel(16, 214, 201, 154, 0.07f);
    for (int yy : {0, 5, 10, 15}) {
        for (int x = 0; x < KACHEL; ++x) punkt(16, x, yy, 196, 182, 132);
    }
    grundkachel(17, 12, 60, 52, 0.1f);
    for (int y = 0; y < KACHEL; ++y) {
        for (int x = 0; x < KACHEL; ++x) {
            float d = std::sqrt((x - 7.5f) * (x - 7.5f) + (y - 7.5f) * (y - 7.5f));
            if (d >= 7.0f) continue;
            float f = 1.0f + (wurf() - 0.5f) * 0.25f;
            float r = 18.0f;
            float g = 92.0f;
            float b = 78.0f;
            if (d > 5.4f) {
                r = 9.0f;
                g = 48.0f;
                b = 42.0f;
            }
            punkt(17, x, y, r * f, g * f, b * f);
        }
    }
    punkt(17, 5, 5, 120, 220, 190);
    punkt(17, 6, 4, 160, 240, 215);
    punkt(17, 6, 5, 90, 190, 160);
    punkt(17, 10, 9, 70, 170, 145);
    grundkachel(18, 196, 58, 38, 0.15f);
    for (int y = 5; y <= 10; ++y) {
        for (int x = 0; x < KACHEL; ++x) {
            float f = 1.0f + (wurf() - 0.5f) * 0.08f;
            punkt(18, x, y, 232 * f, 226 * f, 214 * f);
        }
    }
    const char* schrift[4] = {"111101111", "010111010", "010111010", "010101010"};
    for (int ry = 0; ry < 4; ++ry) {
        for (int rx = 0; rx < 9; ++rx) {
            if (schrift[ry][rx] == '1') punkt(18, 3 + rx, 6 + ry, 32, 26, 26);
        }
    }
    grundkachel(19, 196, 58, 38, 0.15f);
    for (int y = 4; y <= 11; ++y) {
        for (int x = 4; x <= 11; ++x) {
            float f = 1.0f + (wurf() - 0.5f) * 0.08f;
            punkt(19, x, y, 232 * f, 226 * f, 214 * f);
        }
    }
    for (int y = 7; y <= 8; ++y) {
        for (int x = 7; x <= 8; ++x) punkt(19, x, y, 32, 26, 26);
    }

    glGenTextures(1, &textur);
    glBindTexture(GL_TEXTURE_2D, textur);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, KACHELN * KACHEL, KACHEL, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                 bild.data());
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glBindTexture(GL_TEXTURE_2D, 0);
    bild.clear();
    bild.shrink_to_fit();
    return textur != 0;
}

void Atlas::freigeben() {
    if (textur) {
        glDeleteTextures(1, &textur);
        textur = 0;
    }
}

}
