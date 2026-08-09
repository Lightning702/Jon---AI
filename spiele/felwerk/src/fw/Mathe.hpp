#pragma once

#include <cmath>
#include <cstdint>

namespace fw {

constexpr float PI = 3.14159265358979323846f;
constexpr float TAU = 6.28318530717958647692f;

inline float grad(float bogen) { return bogen * 180.0f / PI; }
inline float bogen(float grade) { return grade * PI / 180.0f; }

inline float klemme(float wert, float unten, float oben) {
    return wert < unten ? unten : (wert > oben ? oben : wert);
}

inline float mische(float a, float b, float t) { return a + (b - a) * t; }

inline float sanft(float kante0, float kante1, float wert) {
    float t = klemme((wert - kante0) / (kante1 - kante0 + 1e-9f), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

inline float naehern(float aktuell, float ziel, float schritt) {
    if (aktuell < ziel) return aktuell + schritt < ziel ? aktuell + schritt : ziel;
    return aktuell - schritt > ziel ? aktuell - schritt : ziel;
}

inline float winkelDifferenz(float a, float b) {
    float d = std::fmod(b - a + PI, TAU);
    if (d < 0.0f) d += TAU;
    return d - PI;
}

struct Vec2 {
    float x = 0.0f;
    float y = 0.0f;
    Vec2() = default;
    Vec2(float ax, float ay) : x(ax), y(ay) {}
};

inline Vec2 operator+(Vec2 a, Vec2 b) { return Vec2(a.x + b.x, a.y + b.y); }
inline Vec2 operator-(Vec2 a, Vec2 b) { return Vec2(a.x - b.x, a.y - b.y); }
inline Vec2 operator*(Vec2 a, float s) { return Vec2(a.x * s, a.y * s); }
inline float laenge(Vec2 a) { return std::sqrt(a.x * a.x + a.y * a.y); }

struct Vec3 {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    Vec3() = default;
    Vec3(float ax, float ay, float az) : x(ax), y(ay), z(az) {}
    explicit Vec3(float wert) : x(wert), y(wert), z(wert) {}
};

inline Vec3 operator+(Vec3 a, Vec3 b) { return Vec3(a.x + b.x, a.y + b.y, a.z + b.z); }
inline Vec3 operator-(Vec3 a, Vec3 b) { return Vec3(a.x - b.x, a.y - b.y, a.z - b.z); }
inline Vec3 operator-(Vec3 a) { return Vec3(-a.x, -a.y, -a.z); }
inline Vec3 operator*(Vec3 a, float s) { return Vec3(a.x * s, a.y * s, a.z * s); }
inline Vec3 operator*(float s, Vec3 a) { return a * s; }
inline Vec3 operator*(Vec3 a, Vec3 b) { return Vec3(a.x * b.x, a.y * b.y, a.z * b.z); }
inline Vec3& operator+=(Vec3& a, Vec3 b) { a = a + b; return a; }
inline Vec3& operator-=(Vec3& a, Vec3 b) { a = a - b; return a; }
inline Vec3& operator*=(Vec3& a, float s) { a = a * s; return a; }

inline float punkt(Vec3 a, Vec3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec3 kreuz(Vec3 a, Vec3 b) {
    return Vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
}
inline float laenge(Vec3 a) { return std::sqrt(punkt(a, a)); }
inline float laengeQuadrat(Vec3 a) { return punkt(a, a); }
inline Vec3 normiert(Vec3 a) {
    float l = laenge(a);
    return l > 1e-8f ? a * (1.0f / l) : Vec3(0.0f, 1.0f, 0.0f);
}
inline Vec3 mische(Vec3 a, Vec3 b, float t) {
    return Vec3(mische(a.x, b.x, t), mische(a.y, b.y, t), mische(a.z, b.z, t));
}

struct Mat4 {
    float m[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
};

inline Mat4 einheit() { return Mat4(); }

inline Mat4 operator*(const Mat4& a, const Mat4& b) {
    Mat4 r;
    for (int spalte = 0; spalte < 4; ++spalte) {
        for (int zeile = 0; zeile < 4; ++zeile) {
            float summe = 0.0f;
            for (int k = 0; k < 4; ++k) summe += a.m[k * 4 + zeile] * b.m[spalte * 4 + k];
            r.m[spalte * 4 + zeile] = summe;
        }
    }
    return r;
}

inline Vec3 wandle(const Mat4& a, Vec3 p) {
    return Vec3(a.m[0] * p.x + a.m[4] * p.y + a.m[8] * p.z + a.m[12],
                a.m[1] * p.x + a.m[5] * p.y + a.m[9] * p.z + a.m[13],
                a.m[2] * p.x + a.m[6] * p.y + a.m[10] * p.z + a.m[14]);
}

inline Mat4 verschiebung(Vec3 v) {
    Mat4 r;
    r.m[12] = v.x;
    r.m[13] = v.y;
    r.m[14] = v.z;
    return r;
}

inline Mat4 skalierung(Vec3 v) {
    Mat4 r;
    r.m[0] = v.x;
    r.m[5] = v.y;
    r.m[10] = v.z;
    return r;
}

inline Mat4 drehungX(float winkel) {
    Mat4 r;
    float s = std::sin(winkel);
    float c = std::cos(winkel);
    r.m[5] = c;
    r.m[6] = s;
    r.m[9] = -s;
    r.m[10] = c;
    return r;
}

inline Mat4 drehungY(float winkel) {
    Mat4 r;
    float s = std::sin(winkel);
    float c = std::cos(winkel);
    r.m[0] = c;
    r.m[2] = -s;
    r.m[8] = s;
    r.m[10] = c;
    return r;
}

inline Mat4 drehungZ(float winkel) {
    Mat4 r;
    float s = std::sin(winkel);
    float c = std::cos(winkel);
    r.m[0] = c;
    r.m[1] = s;
    r.m[4] = -s;
    r.m[5] = c;
    return r;
}

inline Mat4 perspektive(float sichtfeld, float seite, float nah, float fern) {
    Mat4 r;
    float f = 1.0f / std::tan(sichtfeld * 0.5f);
    for (int i = 0; i < 16; ++i) r.m[i] = 0.0f;
    r.m[0] = f / seite;
    r.m[5] = f;
    r.m[10] = (fern + nah) / (nah - fern);
    r.m[11] = -1.0f;
    r.m[14] = (2.0f * fern * nah) / (nah - fern);
    return r;
}

inline Mat4 orthogonal(float links, float rechts, float unten, float oben, float nah, float fern) {
    Mat4 r;
    for (int i = 0; i < 16; ++i) r.m[i] = 0.0f;
    r.m[0] = 2.0f / (rechts - links);
    r.m[5] = 2.0f / (oben - unten);
    r.m[10] = -2.0f / (fern - nah);
    r.m[12] = -(rechts + links) / (rechts - links);
    r.m[13] = -(oben + unten) / (oben - unten);
    r.m[14] = -(fern + nah) / (fern - nah);
    r.m[15] = 1.0f;
    return r;
}

inline Mat4 blickRichtung(Vec3 auge, Vec3 ziel, Vec3 oben) {
    Vec3 f = normiert(ziel - auge);
    Vec3 s = normiert(kreuz(f, oben));
    Vec3 u = kreuz(s, f);
    Mat4 r;
    r.m[0] = s.x;
    r.m[4] = s.y;
    r.m[8] = s.z;
    r.m[1] = u.x;
    r.m[5] = u.y;
    r.m[9] = u.z;
    r.m[2] = -f.x;
    r.m[6] = -f.y;
    r.m[10] = -f.z;
    r.m[12] = -punkt(s, auge);
    r.m[13] = -punkt(u, auge);
    r.m[14] = punkt(f, auge);
    return r;
}

inline Mat4 normalenBasis(const Mat4& modell) {
    Mat4 r = modell;
    r.m[12] = 0.0f;
    r.m[13] = 0.0f;
    r.m[14] = 0.0f;
    return r;
}

}
