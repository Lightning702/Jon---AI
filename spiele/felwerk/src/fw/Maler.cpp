#include "Maler.hpp"

namespace fw {
namespace {

const char* ECKEN_QUELLE = R"(#version 330 core
layout(location = 0) in vec3 aOrt;
layout(location = 1) in vec3 aNormale;
layout(location = 2) in vec3 aFarbe;
layout(location = 3) in float aRauheit;
layout(location = 4) in vec2 aBild;

uniform mat4 uModell;
uniform mat4 uSicht;
uniform mat4 uProjektion;
uniform float uZeit;
uniform float uWelleStaerke;
uniform float uWelleWeite;

out vec3 vOrt;
out vec3 vNormale;
out vec3 vFarbe;
out float vRauheit;
out vec2 vBild;

void main() {
    vec4 welt = uModell * vec4(aOrt, 1.0);
    vec3 normale = mat3(uModell) * aNormale;
    if (uWelleStaerke > 0.0001) {
        float a = welt.x * uWelleWeite + uZeit * 0.9;
        float b = welt.z * uWelleWeite * 0.82 - uZeit * 0.7;
        float c = (welt.x + welt.z) * uWelleWeite * 0.45 + uZeit * 1.4;
        float hub = (sin(a) * 0.55 + sin(b) * 0.35 + sin(c) * 0.22) * uWelleStaerke;
        welt.y += hub;
        vec3 neigung = vec3(cos(a) * uWelleWeite * 0.55 + cos(c) * uWelleWeite * 0.1, 0.0,
                            cos(b) * uWelleWeite * 0.35 + cos(c) * uWelleWeite * 0.1);
        normale = normalize(vec3(-neigung.x * uWelleStaerke, 1.0, -neigung.z * uWelleStaerke));
    }
    vOrt = welt.xyz;
    vNormale = normale;
    vFarbe = aFarbe;
    vRauheit = aRauheit;
    vBild = aBild;
    gl_Position = uProjektion * uSicht * welt;
}
)";

const char* FARB_QUELLE = R"(#version 330 core
in vec3 vOrt;
in vec3 vNormale;
in vec3 vFarbe;
in float vRauheit;
in vec2 vBild;

uniform vec3 uAuge;
uniform vec3 uSonne;
uniform vec3 uSonnenfarbe;
uniform vec3 uHimmel;
uniform vec3 uBoden;
uniform vec3 uNebelfarbe;
uniform vec3 uNebelBezug;
uniform float uNebelDichte;
uniform float uNebelStart;
uniform float uHoehenfall;
uniform float uStufen;
uniform float uLeuchten;
uniform float uDeckkraft;
uniform float uZeit;
uniform vec3 uFarbton;
uniform sampler2D uAtlas;
uniform float uTexturAn;

out vec4 ausgabe;

void main() {
    vec3 normale = normalize(vNormale);
    vec3 blick = normalize(uAuge - vOrt);
    float weich = dot(normale, uSonne) * 0.5 + 0.5;
    float sonne = weich * weich;
    if (uStufen > 0.5) {
        float bander = floor(sonne * uStufen) / uStufen;
        sonne = mix(sonne, bander + 0.5 / uStufen, 0.55);
    }
    float himmelAnteil = normale.y * 0.5 + 0.5;
    vec3 umgebung = mix(uBoden, uHimmel, himmelAnteil);
    vec3 licht = umgebung * 0.62 + uSonnenfarbe * sonne * 0.85;

    vec3 halb = normalize(uSonne + blick);
    float glanz = pow(max(dot(normale, halb), 0.0), mix(6.0, 90.0, vRauheit));
    float saum = pow(1.0 - max(dot(normale, blick), 0.0), 3.0);

    vec3 eigen = vFarbe * uFarbton;
    if (uTexturAn > 0.5) eigen *= texture(uAtlas, vBild).rgb;
    vec3 farbe = eigen * licht;
    farbe += uSonnenfarbe * glanz * vRauheit * 0.85;
    farbe += uHimmel * saum * 0.14;
    farbe += eigen * uLeuchten;

    float weite = max(length(uNebelBezug - vOrt) - uNebelStart, 0.0);
    float hoehe = exp(-max(vOrt.y, 0.0) * uHoehenfall);
    float nebel = 1.0 - exp(-weite * uNebelDichte * hoehe);
    farbe = mix(farbe, uNebelfarbe, clamp(nebel, 0.0, 0.88));

    vec3 x = farbe * 1.02;
    vec3 abgebildet = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);
    farbe = clamp(abgebildet, 0.0, 1.0);
    float grau = dot(farbe, vec3(0.299, 0.587, 0.114));
    farbe = clamp(mix(vec3(grau), farbe, 1.14), 0.0, 1.0);
    ausgabe = vec4(pow(farbe, vec3(0.92)), uDeckkraft);
}
)";

}

bool Maler::erstellen() { return programm.bauen(ECKEN_QUELLE, FARB_QUELLE); }

void Maler::freigeben() { programm.freigeben(); }

void Maler::beginnen(const Mat4& sicht, const Mat4& projektion, Vec3 auge, float zeit) {
    programm.benutzen();
    programm.setze("uSicht", sicht);
    programm.setze("uProjektion", projektion);
    programm.setze("uAuge", auge);
    programm.setze("uZeit", zeit);
    programm.setze("uModell", einheit());
    programm.setze("uLeuchten", 0.0f);
    programm.setze("uDeckkraft", 1.0f);
    programm.setze("uWelleStaerke", 0.0f);
    programm.setze("uWelleWeite", 0.0f);
    programm.setze("uStufen", 0.0f);
    programm.setze("uFarbton", Vec3(1.0f, 1.0f, 1.0f));
    programm.setze("uTexturAn", 0.0f);
    programm.setze("uAtlas", 0);
}

void Maler::textur(unsigned kennung) {
    programm.setze("uTexturAn", kennung ? 1.0f : 0.0f);
    if (kennung) {
        programm.setze("uAtlas", 0);
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, kennung);
    }
}

void Maler::toenung(Vec3 farbe) { programm.setze("uFarbton", farbe); }

void Maler::licht(Vec3 richtung, Vec3 sonne, Vec3 himmel, Vec3 boden) {
    programm.setze("uSonne", normiert(richtung));
    programm.setze("uSonnenfarbe", sonne);
    programm.setze("uHimmel", himmel);
    programm.setze("uBoden", boden);
}

void Maler::nebel(Vec3 farbe, float dichte, float hoehenfall, Vec3 bezug, float start) {
    programm.setze("uNebelfarbe", farbe);
    programm.setze("uNebelDichte", dichte);
    programm.setze("uHoehenfall", hoehenfall);
    programm.setze("uNebelBezug", bezug);
    programm.setze("uNebelStart", start);
}

void Maler::stufen(float wert) { programm.setze("uStufen", wert); }

void Maler::modell(const Mat4& matrix) { programm.setze("uModell", matrix); }

void Maler::leuchten(float wert) { programm.setze("uLeuchten", wert); }

void Maler::deckkraft(float wert) { programm.setze("uDeckkraft", wert); }

void Maler::welle(float staerke, float weite) {
    programm.setze("uWelleStaerke", staerke);
    programm.setze("uWelleWeite", weite);
}

void Maler::zeichnen(const Netz& netz) { netz.zeichnen(); }

}
