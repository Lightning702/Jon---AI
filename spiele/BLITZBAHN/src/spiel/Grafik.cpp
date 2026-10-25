#include "Grafik.hpp"

#include <cmath>

#include "fw/GL.hpp"
#include "fw/Protokoll.hpp"

namespace blitzbahn {

using namespace fw;

namespace {

constexpr GLenum RAHMEN = 0x8D40;
constexpr GLenum TIEFEN_ANHANG = 0x8D00;
constexpr GLenum RAHMEN_FERTIG = 0x8CD5;
constexpr GLenum TIEFE24 = 0x81A6;
constexpr GLenum TIEFE_ART = 0x1902;
constexpr GLenum VERGLEICH_MODUS = 0x884C;
constexpr GLenum VERGLEICH_FUNKTION = 0x884D;
constexpr GLenum VERGLEICH_REF = 0x884E;
constexpr GLenum KANTE = 0x812F;

using PfnGenFramebuffers = void(APIENTRY*)(GLsizei, GLuint*);
using PfnBindFramebuffer = void(APIENTRY*)(GLenum, GLuint);
using PfnFramebufferTexture2D = void(APIENTRY*)(GLenum, GLenum, GLenum, GLuint, GLint);
using PfnCheckFramebufferStatus = GLenum(APIENTRY*)(GLenum);
using PfnDeleteFramebuffers = void(APIENTRY*)(GLsizei, const GLuint*);

PfnGenFramebuffers genRahmen = nullptr;
PfnBindFramebuffer bindeRahmen = nullptr;
PfnFramebufferTexture2D rahmenBild = nullptr;
PfnCheckFramebufferStatus rahmenPruefen = nullptr;
PfnDeleteFramebuffers loescheRahmen = nullptr;

template <typename T>
bool laden(T& ziel, const char* name) {
    ziel = reinterpret_cast<T>(wglGetProcAddress(name));
    return ziel != nullptr;
}

const char* WELT_ECKEN = R"(#version 330 core
layout(location = 0) in vec3 aOrt;
layout(location = 1) in vec3 aNormale;
layout(location = 2) in vec3 aFarbe;
layout(location = 3) in float aRauheit;
uniform mat4 uModell;
uniform mat4 uSicht;
uniform mat4 uProjektion;
uniform mat4 uLichtMatrix;
out vec3 vOrt;
out vec3 vNormale;
out vec3 vFarbe;
out float vRauheit;
out vec4 vLicht;
void main() {
    vec4 w = uModell * vec4(aOrt, 1.0);
    vOrt = w.xyz;
    vNormale = mat3(uModell) * aNormale;
    vFarbe = aFarbe;
    vRauheit = aRauheit;
    vLicht = uLichtMatrix * w;
    gl_Position = uProjektion * uSicht * w;
}
)";

const char* WELT_FARBE = R"(#version 330 core
in vec3 vOrt;
in vec3 vNormale;
in vec3 vFarbe;
in float vRauheit;
in vec4 vLicht;
uniform vec3 uAuge;
uniform vec3 uSonne;
uniform vec3 uSonnenfarbe;
uniform vec3 uHimmel;
uniform vec3 uBoden;
uniform vec3 uZenit;
uniform vec3 uHorizont;
uniform vec3 uFarbton;
uniform float uNebelDichte;
uniform float uZeit;
uniform float uLeuchten;
uniform float uDeckkraft;
uniform float uStoff;
uniform float uSchattenAn;
uniform float uTexel;
uniform sampler2DShadow uSchatten;
out vec4 ausgabe;

float streu(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float rausch(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(streu(i), streu(i + vec2(1.0, 0.0)), u.x), mix(streu(i + vec2(0.0, 1.0)), streu(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
    float s = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; i++) {
        s += a * rausch(p);
        p = p * 2.03 + vec2(1.7, 9.2);
        a *= 0.5;
    }
    return s;
}
vec3 himmelFarbe(vec3 d) {
    float t = clamp(d.y, 0.0, 1.0);
    vec3 c = mix(uHorizont, uZenit, pow(t, 0.5));
    float s = max(dot(d, uSonne), 0.0);
    c += uSonnenfarbe * (pow(s, 900.0) * 14.0 + pow(s, 40.0) * 0.45 + pow(s, 5.0) * 0.12);
    if (d.y < 0.0) c = mix(uHorizont * 0.95, uBoden * 0.8, clamp(-d.y * 4.0, 0.0, 1.0));
    return c;
}
float schatten(vec3 n) {
    if (uSchattenAn < 0.5) return 1.0;
    vec3 p = vLicht.xyz / vLicht.w * 0.5 + 0.5;
    if (p.x <= 0.0 || p.x >= 1.0 || p.y <= 0.0 || p.y >= 1.0 || p.z >= 1.0) return 1.0;
    float neig = max(dot(n, uSonne), 0.0);
    float verschub = mix(0.0022, 0.0005, neig);
    float s = 0.0;
    for (int x = -1; x <= 1; x++)
        for (int y = -1; y <= 1; y++) s += texture(uSchatten, vec3(p.xy + vec2(x, y) * uTexel * 1.3, p.z - verschub));
    s /= 9.0;
    vec2 rand = abs(p.xy - 0.5) * 2.0;
    return mix(s, 1.0, smoothstep(0.82, 0.98, max(rand.x, rand.y)));
}
void main() {
    int stoff = int(uStoff + 0.5);
    vec3 blick = normalize(vOrt - uAuge);
    if (stoff == 5) {
        ausgabe = vec4(pow(himmelFarbe(blick), vec3(0.95)), 1.0);
        return;
    }
    vec3 basis = vFarbe * uFarbton;
    if (stoff == 6) {
        ausgabe = vec4(basis + basis * uLeuchten, clamp(vRauheit, 0.0, 1.0) * uDeckkraft);
        return;
    }
    vec3 n = normalize(vNormale);
    if (!gl_FrontFacing) n = -n;
    vec3 v = -blick;
    if (stoff == 3) {
        vec2 q = vOrt.xz * 0.08;
        float w1 = rausch(q + vec2(uZeit * 0.12, uZeit * 0.07));
        float w2 = rausch(q * 2.3 - vec2(uZeit * 0.09, uZeit * 0.15));
        n = normalize(vec3((w1 - 0.5) * 0.35, 1.0, (w2 - 0.5) * 0.35));
    }
    if (stoff == 1) {
        float g = fbm(vOrt.xz * 0.035);
        float fein = rausch(vOrt.xz * 0.7);
        basis *= 0.8 + 0.32 * g + 0.07 * fein;
        basis = mix(basis, basis * vec3(1.05, 1.02, 0.86), smoothstep(0.55, 0.8, rausch(vOrt.xz * 0.012)) * 0.5);
    } else if (stoff == 2) {
        float hoch = max(max(basis.r, basis.g), basis.b);
        float tief = min(min(basis.r, basis.g), basis.b);
        float hell = dot(basis, vec3(0.299, 0.587, 0.114));
        if (hoch - tief < 0.09 && hell < 0.5 && n.y > 0.5) {
            float k = rausch(vOrt.xz * 2.7) * 0.55 + rausch(vOrt.xz * 13.0) * 0.45;
            basis *= 0.86 + 0.24 * k;
        }
    }
    float sh = schatten(n);
    float sonneL = max(dot(n, uSonne), 0.0);
    vec3 umgebung = mix(uBoden, uHimmel, n.y * 0.5 + 0.5);
    vec3 farbe;
    if (stoff == 7) {
        farbe = basis * (0.78 + 0.32 * sonneL) + uSonnenfarbe * pow(max(dot(blick, uSonne), 0.0), 6.0) * 0.25;
    } else {
        vec3 licht = umgebung * 0.58 + uSonnenfarbe * sonneL * sh * 1.08;
        farbe = basis * licht;
        vec3 halb = normalize(uSonne + v);
        float rau = vRauheit;
        if (stoff == 4) {
            float fres = pow(1.0 - max(dot(n, v), 0.0), 4.0);
            farbe += himmelFarbe(reflect(-v, n)) * (0.06 + 0.5 * fres) * rau;
            farbe += uSonnenfarbe * pow(max(dot(n, halb), 0.0), 140.0) * 1.6 * sh * rau;
        } else if (stoff == 3) {
            float fres = 0.08 + 0.92 * pow(1.0 - max(dot(n, v), 0.0), 5.0);
            vec3 tiefe = vec3(0.05, 0.22, 0.28);
            farbe = mix(tiefe * (0.4 + 0.6 * sh), himmelFarbe(reflect(-v, n)), fres);
            farbe += uSonnenfarbe * pow(max(dot(n, halb), 0.0), 260.0) * 2.4 * sh;
        } else {
            farbe += uSonnenfarbe * pow(max(dot(n, halb), 0.0), mix(8.0, 90.0, rau)) * rau * 0.4 * sh;
        }
    }
    farbe += basis * uLeuchten;
    float weite = length(vOrt - uAuge);
    float nebel = 1.0 - exp(-max(weite - 160.0, 0.0) * uNebelDichte * exp(-max(vOrt.y, 0.0) * 0.004));
    vec3 nebelFarbe = mix(uHorizont, uSonnenfarbe * 1.05, pow(max(dot(blick, uSonne), 0.0), 8.0) * 0.45);
    farbe = mix(farbe, nebelFarbe, clamp(nebel, 0.0, 0.94));
    vec3 x = farbe * 1.04;
    farbe = clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
    float grau = dot(farbe, vec3(0.299, 0.587, 0.114));
    farbe = clamp(mix(vec3(grau), farbe, 1.12), 0.0, 1.0);
    ausgabe = vec4(pow(farbe, vec3(0.93)), uDeckkraft);
}
)";

const char* TIEFE_ECKEN = R"(#version 330 core
layout(location = 0) in vec3 aOrt;
uniform mat4 uLichtMatrix;
uniform mat4 uModell;
void main() { gl_Position = uLichtMatrix * uModell * vec4(aOrt, 1.0); }
)";

const char* TIEFE_FARBE = R"(#version 330 core
out vec4 ausgabe;
void main() { ausgabe = vec4(1.0); }
)";

}

bool Grafik::erstellen(int schattenGroesse) {
    groesse = schattenGroesse;
    if (!welt.bauen(WELT_ECKEN, WELT_FARBE)) {
        warnung("Weltschattierer: %s", welt.fehler().c_str());
        return false;
    }
    schattenBereit = false;
    if (!tiefe.bauen(TIEFE_ECKEN, TIEFE_FARBE)) {
        warnung("Tiefenschattierer: %s", tiefe.fehler().c_str());
        return true;
    }
    if (!laden(genRahmen, "glGenFramebuffers") || !laden(bindeRahmen, "glBindFramebuffer") ||
        !laden(rahmenBild, "glFramebufferTexture2D") || !laden(rahmenPruefen, "glCheckFramebufferStatus") ||
        !laden(loescheRahmen, "glDeleteFramebuffers")) {
        warnung("Keine Bildpuffer, Schatten bleiben aus");
        return true;
    }
    glGenTextures(1, &tiefenBild);
    glBindTexture(GL_TEXTURE_2D, tiefenBild);
    glTexImage2D(GL_TEXTURE_2D, 0, TIEFE24, groesse, groesse, 0, TIEFE_ART, GL_UNSIGNED_INT, nullptr);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, KANTE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, KANTE);
    glTexParameteri(GL_TEXTURE_2D, VERGLEICH_MODUS, VERGLEICH_REF);
    glTexParameteri(GL_TEXTURE_2D, VERGLEICH_FUNKTION, GL_LEQUAL);
    genRahmen(1, &rahmen);
    bindeRahmen(RAHMEN, rahmen);
    rahmenBild(RAHMEN, TIEFEN_ANHANG, GL_TEXTURE_2D, tiefenBild, 0);
    glDrawBuffer(GL_NONE);
    glReadBuffer(GL_NONE);
    schattenBereit = rahmenPruefen(RAHMEN) == RAHMEN_FERTIG;
    bindeRahmen(RAHMEN, 0);
    glBindTexture(GL_TEXTURE_2D, 0);
    notiz("Schatten %s (%d px)", schattenBereit ? "an" : "aus", groesse);
    return true;
}

void Grafik::freigeben() {
    if (rahmen && loescheRahmen) loescheRahmen(1, &rahmen);
    if (tiefenBild) glDeleteTextures(1, &tiefenBild);
    rahmen = 0;
    tiefenBild = 0;
    welt.freigeben();
    tiefe.freigeben();
}

void Grafik::schattenBeginnen(Vec3 mitte, Vec3 sonne, float radius) {
    if (!schattenBereit) return;
    Vec3 s = normiert(sonne);
    float raster = radius * 2.0f / static_cast<float>(groesse);
    mitte.x = std::floor(mitte.x / raster) * raster;
    mitte.z = std::floor(mitte.z / raster) * raster;
    Mat4 blick = blickRichtung(mitte + s * 600.0f, mitte, std::fabs(s.y) > 0.95f ? Vec3(0.0f, 0.0f, 1.0f) : Vec3(0.0f, 1.0f, 0.0f));
    lichtMatrix = orthogonal(-radius, radius, -radius, radius, 10.0f, 1400.0f) * blick;
    bindeRahmen(RAHMEN, rahmen);
    glViewport(0, 0, groesse, groesse);
    glClear(GL_DEPTH_BUFFER_BIT);
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_BLEND);
    glEnable(GL_POLYGON_OFFSET_FILL);
    glPolygonOffset(2.0f, 3.0f);
    tiefe.benutzen();
    tiefe.setze("uLichtMatrix", lichtMatrix);
    tiefe.setze("uModell", einheit());
}

void Grafik::schattenModell(const Mat4& matrix) {
    if (schattenBereit) tiefe.setze("uModell", matrix);
}

void Grafik::schattenZeichnen(const Netz& netz) {
    if (schattenBereit) netz.zeichnen();
}

void Grafik::schattenBeenden(int breite, int hoehe) {
    if (!schattenBereit) return;
    glDisable(GL_POLYGON_OFFSET_FILL);
    bindeRahmen(RAHMEN, 0);
    glViewport(0, 0, breite, hoehe);
}

void Grafik::beginnen(const Mat4& sicht, const Mat4& projektion, Vec3 auge, float zeit, Vec3 sonne, bool mitSchatten) {
    welt.benutzen();
    welt.setze("uSicht", sicht);
    welt.setze("uProjektion", projektion);
    welt.setze("uAuge", auge);
    welt.setze("uZeit", zeit);
    welt.setze("uModell", einheit());
    welt.setze("uSonne", normiert(sonne));
    welt.setze("uSonnenfarbe", Vec3(1.0f, 0.93f, 0.82f));
    welt.setze("uHimmel", Vec3(0.6f, 0.74f, 0.95f));
    welt.setze("uBoden", Vec3(0.34f, 0.38f, 0.3f));
    welt.setze("uZenit", Vec3(0.2f, 0.42f, 0.78f));
    welt.setze("uHorizont", Vec3(0.7f, 0.82f, 0.94f));
    welt.setze("uFarbton", Vec3(1.0f, 1.0f, 1.0f));
    welt.setze("uLeuchten", 0.0f);
    welt.setze("uDeckkraft", 1.0f);
    welt.setze("uStoff", 0.0f);
    welt.setze("uNebelDichte", 0.00055f);
    welt.setze("uTexel", 1.0f / static_cast<float>(groesse));
    bool schatten = mitSchatten && schattenBereit;
    welt.setze("uSchattenAn", schatten ? 1.0f : 0.0f);
    welt.setze("uLichtMatrix", lichtMatrix);
    welt.setze("uSchatten", 1);
    glActiveTexture(GL_TEXTURE0 + 1);
    glBindTexture(GL_TEXTURE_2D, schatten ? tiefenBild : 0);
    glActiveTexture(GL_TEXTURE0);
}

void Grafik::stoff(int art) { welt.setze("uStoff", static_cast<float>(art)); }

void Grafik::modell(const Mat4& matrix) { welt.setze("uModell", matrix); }

void Grafik::toenung(Vec3 farbe) { welt.setze("uFarbton", farbe); }

void Grafik::leuchten(float wert) { welt.setze("uLeuchten", wert); }

void Grafik::deckkraft(float wert) { welt.setze("uDeckkraft", wert); }

void Grafik::nebel(float dichte) { welt.setze("uNebelDichte", dichte); }

void Grafik::zeichnen(const Netz& netz) { netz.zeichnen(); }

}
