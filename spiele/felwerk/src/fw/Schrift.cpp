#include "Schrift.hpp"

#include <cstring>

#include "Protokoll.hpp"

namespace fw {
namespace {

constexpr int ATLAS = 512;

const char* ECKEN_QUELLE = R"(#version 330 core
layout(location = 0) in vec2 aOrt;
layout(location = 1) in vec2 aUV;
layout(location = 2) in vec4 aFarbe;
uniform vec2 uFlaeche;
out vec2 vUV;
out vec4 vFarbe;
void main() {
    vec2 norm = vec2(aOrt.x / uFlaeche.x * 2.0 - 1.0, 1.0 - aOrt.y / uFlaeche.y * 2.0);
    gl_Position = vec4(norm, 0.0, 1.0);
    vUV = aUV;
    vFarbe = aFarbe;
}
)";

const char* FARB_QUELLE = R"(#version 330 core
in vec2 vUV;
in vec4 vFarbe;
uniform sampler2D uAtlas;
out vec4 ausgabe;
void main() {
    float deckung = texture(uAtlas, vUV).r;
    ausgabe = vec4(vFarbe.rgb, vFarbe.a * deckung);
    if (ausgabe.a < 0.004) discard;
}
)";

}

Schrift::~Schrift() { freigeben(); }

bool Schrift::erstellen(const char* name, int hoehe, bool fett) {
    freigeben();
    if (!schattierer.bauen(ECKEN_QUELLE, FARB_QUELLE)) return false;

    HDC bildschirm = GetDC(nullptr);
    HDC speicher = CreateCompatibleDC(bildschirm);
    ReleaseDC(nullptr, bildschirm);

    BITMAPINFO angabe = {};
    angabe.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    angabe.bmiHeader.biWidth = ATLAS;
    angabe.bmiHeader.biHeight = -ATLAS;
    angabe.bmiHeader.biPlanes = 1;
    angabe.bmiHeader.biBitCount = 32;
    angabe.bmiHeader.biCompression = BI_RGB;
    void* rohdaten = nullptr;
    HBITMAP bild = CreateDIBSection(speicher, &angabe, DIB_RGB_COLORS, &rohdaten, nullptr, 0);
    if (!bild || !rohdaten) {
        DeleteDC(speicher);
        warnung("Schriftatlas konnte nicht angelegt werden");
        return false;
    }
    HGDIOBJ altesBild = SelectObject(speicher, bild);
    std::memset(rohdaten, 0, static_cast<size_t>(ATLAS) * ATLAS * 4);

    HFONT schriftart = CreateFontA(-hoehe, 0, 0, 0, fett ? FW_SEMIBOLD : FW_NORMAL, FALSE, FALSE, FALSE,
                                   DEFAULT_CHARSET, OUT_TT_PRECIS, CLIP_DEFAULT_PRECIS,
                                   CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, name);
    HGDIOBJ alteSchrift = SelectObject(speicher, schriftart);
    SetTextColor(speicher, RGB(255, 255, 255));
    SetBkMode(speicher, TRANSPARENT);

    TEXTMETRICA masse = {};
    GetTextMetricsA(speicher, &masse);
    hoeheZeile = static_cast<float>(masse.tmHeight);

    int stiftX = 2;
    int stiftY = 2;
    int reihenhoehe = masse.tmHeight + 2;
    for (int code = 32; code < 256; ++code) {
        char text[2] = {static_cast<char>(code), '\0'};
        SIZE groesse = {};
        GetTextExtentPoint32A(speicher, text, 1, &groesse);
        if (groesse.cx <= 0) groesse.cx = masse.tmAveCharWidth;
        if (stiftX + groesse.cx + 2 >= ATLAS) {
            stiftX = 2;
            stiftY += reihenhoehe;
        }
        if (stiftY + reihenhoehe >= ATLAS - 4) break;
        TextOutA(speicher, stiftX, stiftY, text, 1);
        Zeichen& z = zeichen[code];
        z.u0 = static_cast<float>(stiftX) / ATLAS;
        z.v0 = static_cast<float>(stiftY) / ATLAS;
        z.u1 = static_cast<float>(stiftX + groesse.cx) / ATLAS;
        z.v1 = static_cast<float>(stiftY + masse.tmHeight) / ATLAS;
        z.breite = static_cast<float>(groesse.cx);
        z.hoehe = static_cast<float>(masse.tmHeight);
        z.vorschub = static_cast<float>(groesse.cx);
        stiftX += groesse.cx + 2;
    }

    unsigned char* bildpunkte = static_cast<unsigned char*>(rohdaten);
    std::vector<unsigned char> deckung(static_cast<size_t>(ATLAS) * ATLAS);
    for (size_t i = 0; i < deckung.size(); ++i) {
        unsigned char b = bildpunkte[i * 4 + 0];
        unsigned char g = bildpunkte[i * 4 + 1];
        unsigned char r = bildpunkte[i * 4 + 2];
        unsigned char hell = r > g ? r : g;
        deckung[i] = hell > b ? hell : b;
    }
    deckung[deckung.size() - 1] = 255;
    deckung[deckung.size() - 2] = 255;
    deckung[deckung.size() - 1 - ATLAS] = 255;
    deckung[deckung.size() - 2 - ATLAS] = 255;
    weissU = (ATLAS - 1.5f) / ATLAS;
    weissV = (ATLAS - 1.5f) / ATLAS;

    glGenTextures(1, &atlas);
    glBindTexture(GL_TEXTURE_2D, atlas);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, ATLAS, ATLAS, 0, GL_RED, GL_UNSIGNED_BYTE, deckung.data());
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glBindTexture(GL_TEXTURE_2D, 0);

    SelectObject(speicher, alteSchrift);
    DeleteObject(schriftart);
    SelectObject(speicher, altesBild);
    DeleteObject(bild);
    DeleteDC(speicher);

    glGenVertexArrays(1, &feld);
    glGenBuffers(1, &puffer);
    glBindVertexArray(feld);
    glBindBuffer(GL_ARRAY_BUFFER, puffer);
    glBufferData(GL_ARRAY_BUFFER, 1, nullptr, GL_DYNAMIC_DRAW);
    const GLsizei schritt = 8 * sizeof(float);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, schritt, reinterpret_cast<void*>(0));
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, schritt, reinterpret_cast<void*>(2 * sizeof(float)));
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, schritt, reinterpret_cast<void*>(4 * sizeof(float)));
    glBindVertexArray(0);
    return true;
}

void Schrift::freigeben() {
    if (atlas) {
        glDeleteTextures(1, &atlas);
        atlas = 0;
    }
    if (puffer) {
        glDeleteBuffers(1, &puffer);
        puffer = 0;
    }
    if (feld) {
        glDeleteVertexArrays(1, &feld);
        feld = 0;
    }
    schattierer.freigeben();
}

void Schrift::beginnen(int breite, int hoehe) {
    flaecheBreite = breite;
    flaecheHoehe = hoehe;
    staffel.clear();
    laeuft = true;
}

void Schrift::beenden() {
    ausgeben();
    laeuft = false;
}

void Schrift::quad(float x, float y, float breite, float hoehe, float u0, float v0, float u1,
                   float v1, Farbe farbe) {
    const float ecken[6][4] = {{x, y, u0, v0},
                               {x, y + hoehe, u0, v1},
                               {x + breite, y + hoehe, u1, v1},
                               {x, y, u0, v0},
                               {x + breite, y + hoehe, u1, v1},
                               {x + breite, y, u1, v0}};
    for (const float* e : ecken) {
        staffel.push_back(e[0]);
        staffel.push_back(e[1]);
        staffel.push_back(e[2]);
        staffel.push_back(e[3]);
        staffel.push_back(farbe.r);
        staffel.push_back(farbe.g);
        staffel.push_back(farbe.b);
        staffel.push_back(farbe.a);
    }
}

void Schrift::flaeche(float x, float y, float breite, float hoehe, Farbe farbe) {
    quad(x, y, breite, hoehe, weissU, weissV, weissU, weissV, farbe);
}

void Schrift::rahmen(float x, float y, float breite, float hoehe, float staerke, Farbe farbe) {
    flaeche(x, y, breite, staerke, farbe);
    flaeche(x, y + hoehe - staerke, breite, staerke, farbe);
    flaeche(x, y + staerke, staerke, hoehe - staerke * 2.0f, farbe);
    flaeche(x + breite - staerke, y + staerke, staerke, hoehe - staerke * 2.0f, farbe);
}

void Schrift::text(float x, float y, const std::string& inhalt, Farbe farbe, float mass) {
    float stift = x;
    for (unsigned char c : inhalt) {
        const Zeichen& z = zeichen[c];
        if (c == ' ' || z.breite <= 0.0f) {
            stift += (z.vorschub > 0.0f ? z.vorschub : hoeheZeile * 0.3f) * mass;
            continue;
        }
        quad(stift, y, z.breite * mass, z.hoehe * mass, z.u0, z.v0, z.u1, z.v1, farbe);
        stift += z.vorschub * mass;
    }
}

void Schrift::textMittig(float mitteX, float y, const std::string& inhalt, Farbe farbe, float mass) {
    text(mitteX - textBreite(inhalt, mass) * 0.5f, y, inhalt, farbe, mass);
}

float Schrift::textBreite(const std::string& inhalt, float mass) const {
    float summe = 0.0f;
    for (unsigned char c : inhalt) {
        const Zeichen& z = zeichen[c];
        summe += (z.vorschub > 0.0f ? z.vorschub : hoeheZeile * 0.3f) * mass;
    }
    return summe;
}

void Schrift::ausgeben() {
    if (staffel.empty() || !feld) return;
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    schattierer.benutzen();
    schattierer.setze("uFlaeche", Vec2(static_cast<float>(flaecheBreite), static_cast<float>(flaecheHoehe)));
    schattierer.setze("uAtlas", 0);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, atlas);
    glBindVertexArray(feld);
    glBindBuffer(GL_ARRAY_BUFFER, puffer);
    glBufferData(GL_ARRAY_BUFFER, static_cast<ptrdiff_t>(staffel.size() * sizeof(float)), staffel.data(),
                 GL_DYNAMIC_DRAW);
    glDrawArrays(GL_TRIANGLES, 0, static_cast<GLsizei>(staffel.size() / 8));
    glBindVertexArray(0);
    glEnable(GL_DEPTH_TEST);
    staffel.clear();
}

}
