#include "Himmel.hpp"

#include "fw/GL.hpp"

namespace harmonie {
namespace {

using namespace fw;

const char* ECKEN_QUELLE = R"(#version 330 core
layout(location = 0) in vec2 aOrt;
out vec2 vBild;
void main() {
    vBild = aOrt * 0.5 + 0.5;
    gl_Position = vec4(aOrt, 0.0, 1.0);
}
)";

const char* FARB_QUELLE = R"(#version 330 core
in vec2 vBild;
uniform float uZeit;
uniform float uDrehung;
uniform float uRegenbogen;
uniform vec2 uFlaeche;
out vec4 ausgabe;

float streu(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float rauschen(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = streu(i);
    float b = streu(i + vec2(1.0, 0.0));
    float c = streu(i + vec2(0.0, 1.0));
    float d = streu(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float wolken(vec2 p) {
    float summe = 0.0;
    float staerke = 0.5;
    for (int i = 0; i < 5; ++i) {
        summe += rauschen(p) * staerke;
        p *= 2.03;
        staerke *= 0.5;
    }
    return summe;
}

void main() {
    vec2 bild = vBild;
    float hoehe = bild.y;
    vec3 oben = vec3(0.36, 0.53, 0.80);
    vec3 mitte = vec3(0.75, 0.74, 0.86);
    vec3 unten = vec3(0.99, 0.82, 0.62);
    vec3 himmel = mix(mitte, oben, smoothstep(0.42, 1.0, hoehe));
    himmel = mix(unten, himmel, smoothstep(0.02, 0.5, hoehe));

    vec2 sonne = vec2(0.5 + 0.34 * sin(uDrehung), 0.62);
    float weite = length((bild - sonne) * vec2(uFlaeche.x / uFlaeche.y, 1.0));
    float scheibe = smoothstep(0.052, 0.03, weite);
    float schein = exp(-weite * 5.2) * 0.85 + exp(-weite * 1.6) * 0.3;
    himmel += vec3(1.0, 0.82, 0.55) * schein;
    himmel = mix(himmel, vec3(1.0, 0.96, 0.83), scheibe);

    vec2 wolkeUV = vec2(bild.x * 2.4 + uDrehung * 0.42 + uZeit * 0.006, (bild.y - 0.34) * 5.4);
    float band = smoothstep(0.3, 0.92, bild.y);
    float dichte = wolken(wolkeUV) - 0.46;
    float wolkig = smoothstep(0.0, 0.24, dichte) * band * 0.85;
    vec3 wolkenfarbe = mix(vec3(1.0, 0.88, 0.78), vec3(1.0, 0.97, 0.94), smoothstep(0.4, 0.9, bild.y));
    himmel = mix(himmel, wolkenfarbe, wolkig * 0.72);

    if (uRegenbogen > 0.001) {
        vec2 bogenMitte = vec2(0.5 - 0.3 * sin(uDrehung), 0.03);
        float r = length((bild - bogenMitte) * vec2(uFlaeche.x / uFlaeche.y, 1.0));
        float band2 = smoothstep(0.40, 0.42, r) * (1.0 - smoothstep(0.47, 0.50, r));
        float t = clamp((r - 0.415) / 0.075, 0.0, 1.0);
        vec3 bogen = vec3(0.5 + 0.5 * cos(6.2831 * (t + 0.0)),
                          0.5 + 0.5 * cos(6.2831 * (t + 0.33)),
                          0.5 + 0.5 * cos(6.2831 * (t + 0.67)));
        himmel += bogen * band2 * uRegenbogen * 0.34 * smoothstep(0.06, 0.3, bild.y);
    }

    float dunst = smoothstep(0.30, 0.0, hoehe);
    himmel = mix(himmel, vec3(0.94, 0.86, 0.79), dunst * 0.55);

    vec3 x = himmel * 1.02;
    vec3 abgebildet = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);
    himmel = clamp(abgebildet, 0.0, 1.0);
    ausgabe = vec4(pow(himmel, vec3(0.92)), 1.0);
}
)";

}

Himmel::~Himmel() { freigeben(); }

bool Himmel::erstellen() {
    if (!schattierer.bauen(ECKEN_QUELLE, FARB_QUELLE)) return false;
    const float ecken[] = {-1.0f, -1.0f, 3.0f, -1.0f, -1.0f, 3.0f};
    glGenVertexArrays(1, &feld);
    glGenBuffers(1, &puffer);
    glBindVertexArray(feld);
    glBindBuffer(GL_ARRAY_BUFFER, puffer);
    glBufferData(GL_ARRAY_BUFFER, sizeof(ecken), ecken, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), nullptr);
    glBindVertexArray(0);
    return true;
}

void Himmel::freigeben() {
    if (puffer) glDeleteBuffers(1, &puffer);
    if (feld) glDeleteVertexArrays(1, &feld);
    puffer = 0;
    feld = 0;
    schattierer.freigeben();
}

void Himmel::zeichnen(float zeit, float drehung, float regenbogen, Vec2 flaeche) {
    if (!feld) return;
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    schattierer.benutzen();
    schattierer.setze("uZeit", zeit);
    schattierer.setze("uDrehung", drehung);
    schattierer.setze("uRegenbogen", regenbogen);
    schattierer.setze("uFlaeche", flaeche);
    glBindVertexArray(feld);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glBindVertexArray(0);
    glDepthMask(GL_TRUE);
    glEnable(GL_DEPTH_TEST);
}

}
