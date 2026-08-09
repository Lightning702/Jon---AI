#include "Himmel.hpp"

#include "fw/GL.hpp"

namespace blockwelt {
namespace {

using namespace fw;

const char* ECKEN_QUELLE = R"(#version 330 core
layout(location = 0) in vec2 aOrt;
out vec2 vBild;
void main() {
    vBild = aOrt;
    gl_Position = vec4(aOrt, 0.0, 1.0);
}
)";

const char* FARB_QUELLE = R"(#version 330 core
in vec2 vBild;
uniform vec3 uBlick;
uniform vec3 uRechts;
uniform vec3 uOben;
uniform vec3 uSonne;
uniform float uTag;
uniform float uHalbfeld;
uniform float uSeite;
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

void main() {
    vec3 richtung = normalize(uBlick + uRechts * vBild.x * uHalbfeld * uSeite +
                              uOben * vBild.y * uHalbfeld);
    float hoehe = richtung.y;
    float nacht = clamp(1.0 - uTag * 1.6, 0.0, 1.0);

    vec3 obenTag = vec3(0.24, 0.46, 0.78);
    vec3 untenTag = vec3(0.72, 0.84, 0.94);
    vec3 obenNacht = vec3(0.03, 0.04, 0.10);
    vec3 untenNacht = vec3(0.10, 0.12, 0.22);
    vec3 himmelOben = mix(obenTag, obenNacht, nacht);
    vec3 himmelUnten = mix(untenTag, untenNacht, nacht);
    vec3 farbe = mix(himmelUnten, himmelOben, clamp(hoehe * 1.35 + 0.12, 0.0, 1.0));

    float sonneNah = max(dot(richtung, uSonne), 0.0);
    float abend = clamp(1.0 - abs(uSonne.y) * 2.6, 0.0, 1.0);
    vec3 sonnenton = mix(vec3(1.0, 0.96, 0.86), vec3(1.0, 0.62, 0.36), abend);
    farbe += sonnenton * pow(sonneNah, 220.0) * 3.4;
    farbe += sonnenton * pow(sonneNah, 8.0) * 0.28 * (1.0 - nacht);
    farbe += vec3(0.85, 0.86, 1.0) * pow(max(dot(richtung, -uSonne), 0.0), 380.0) * nacht * 2.2;

    if (nacht > 0.15 && hoehe > 0.0) {
        vec2 gitter = richtung.xz / max(richtung.y, 0.08) * 22.0;
        float stern = step(0.9965, streu(floor(gitter)));
        farbe += vec3(0.9, 0.93, 1.0) * stern * nacht * 0.9;
    }

    float wolke = rauschen(richtung.xz / max(abs(richtung.y), 0.12) * 1.5 + vec2(uTag * 12.0, 0.0));
    wolke += rauschen(richtung.xz / max(abs(richtung.y), 0.12) * 3.2) * 0.5;
    float decke = smoothstep(0.72, 1.05, wolke) * smoothstep(0.02, 0.28, hoehe);
    farbe = mix(farbe, mix(vec3(1.0, 0.97, 0.94), vec3(0.3, 0.32, 0.4), nacht), decke * 0.55);

    float dunst = smoothstep(0.12, -0.06, hoehe);
    farbe = mix(farbe, mix(vec3(0.78, 0.83, 0.88), vec3(0.08, 0.09, 0.14), nacht), dunst * 0.75);

    vec3 x = farbe * 1.02;
    vec3 abgebildet = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);
    ausgabe = vec4(pow(clamp(abgebildet, 0.0, 1.0), vec3(0.92)), 1.0);
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

void Himmel::zeichnen(Vec3 blick, Vec3 rechts, Vec3 oben, Vec3 sonne, float tag, float sichtfeld,
                      float seite) {
    if (!feld) return;
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    schattierer.benutzen();
    schattierer.setze("uBlick", blick);
    schattierer.setze("uRechts", rechts);
    schattierer.setze("uOben", oben);
    schattierer.setze("uSonne", sonne);
    schattierer.setze("uTag", tag);
    schattierer.setze("uHalbfeld", std::tan(sichtfeld * 0.5f));
    schattierer.setze("uSeite", seite);
    glBindVertexArray(feld);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glBindVertexArray(0);
    glDepthMask(GL_TRUE);
    glEnable(GL_DEPTH_TEST);
}

}
