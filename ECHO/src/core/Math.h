#pragma once

#include "Common.h"
#include <cmath>

namespace em {

constexpr float PI = 3.14159265358979323846f;
constexpr float TAU = 6.28318530717958647692f;
constexpr float HALF_PI = 1.57079632679489661923f;
constexpr float DEG2RAD = PI / 180.0f;
constexpr float RAD2DEG = 180.0f / PI;
constexpr float EPS = 1e-6f;

inline float clampf(float v, float a, float b) { return v < a ? a : (v > b ? b : v); }
inline int clampi(int v, int a, int b) { return v < a ? a : (v > b ? b : v); }
inline float saturate(float v) { return clampf(v, 0.0f, 1.0f); }
inline float lerpf(float a, float b, float t) { return a + (b - a) * t; }
inline float smoothstepf(float a, float b, float x) { float t = saturate((x - a) / (b - a)); return t * t * (3.0f - 2.0f * t); }
inline float signf(float v) { return v < 0.0f ? -1.0f : (v > 0.0f ? 1.0f : 0.0f); }
inline float fractf(float v) { return v - std::floor(v); }
inline float wrapAngle(float a) { while (a > PI) a -= TAU; while (a < -PI) a += TAU; return a; }
inline float moveTowards(float c, float t, float d) { float diff = t - c; if (std::fabs(diff) <= d) return t; return c + signf(diff) * d; }
inline float expDamp(float c, float t, float rate, float dt) { return t + (c - t) * std::exp(-rate * dt); }

struct Vec2 {
    float x = 0, y = 0;
    Vec2() {}
    Vec2(float s) : x(s), y(s) {}
    Vec2(float _x, float _y) : x(_x), y(_y) {}
    Vec2 operator+(const Vec2& o) const { return Vec2(x + o.x, y + o.y); }
    Vec2 operator-(const Vec2& o) const { return Vec2(x - o.x, y - o.y); }
    Vec2 operator*(float s) const { return Vec2(x * s, y * s); }
    Vec2 operator*(const Vec2& o) const { return Vec2(x * o.x, y * o.y); }
    Vec2 operator/(float s) const { return Vec2(x / s, y / s); }
    Vec2 operator-() const { return Vec2(-x, -y); }
    Vec2& operator+=(const Vec2& o) { x += o.x; y += o.y; return *this; }
    Vec2& operator-=(const Vec2& o) { x -= o.x; y -= o.y; return *this; }
    Vec2& operator*=(float s) { x *= s; y *= s; return *this; }
    Vec2& operator/=(float s) { x /= s; y /= s; return *this; }
    bool operator==(const Vec2& o) const { return x == o.x && y == o.y; }
    float operator[](int i) const { return (&x)[i]; }
    float& operator[](int i) { return (&x)[i]; }
};

struct Vec3 {
    float x = 0, y = 0, z = 0;
    Vec3() {}
    Vec3(float s) : x(s), y(s), z(s) {}
    Vec3(float _x, float _y, float _z) : x(_x), y(_y), z(_z) {}
    Vec3(const Vec2& v, float _z) : x(v.x), y(v.y), z(_z) {}
    Vec3 operator+(const Vec3& o) const { return Vec3(x + o.x, y + o.y, z + o.z); }
    Vec3 operator-(const Vec3& o) const { return Vec3(x - o.x, y - o.y, z - o.z); }
    Vec3 operator*(float s) const { return Vec3(x * s, y * s, z * s); }
    Vec3 operator*(const Vec3& o) const { return Vec3(x * o.x, y * o.y, z * o.z); }
    Vec3 operator/(float s) const { return Vec3(x / s, y / s, z / s); }
    Vec3 operator/(const Vec3& o) const { return Vec3(x / o.x, y / o.y, z / o.z); }
    Vec3 operator-() const { return Vec3(-x, -y, -z); }
    Vec3& operator+=(const Vec3& o) { x += o.x; y += o.y; z += o.z; return *this; }
    Vec3& operator-=(const Vec3& o) { x -= o.x; y -= o.y; z -= o.z; return *this; }
    Vec3& operator*=(float s) { x *= s; y *= s; z *= s; return *this; }
    Vec3& operator*=(const Vec3& o) { x *= o.x; y *= o.y; z *= o.z; return *this; }
    Vec3& operator/=(float s) { x /= s; y /= s; z /= s; return *this; }
    bool operator==(const Vec3& o) const { return x == o.x && y == o.y && z == o.z; }
    bool operator!=(const Vec3& o) const { return !(*this == o); }
    float operator[](int i) const { return (&x)[i]; }
    float& operator[](int i) { return (&x)[i]; }
    Vec2 xz() const { return Vec2(x, z); }
    Vec2 xy() const { return Vec2(x, y); }
};

struct Vec4 {
    float x = 0, y = 0, z = 0, w = 0;
    Vec4() {}
    Vec4(float s) : x(s), y(s), z(s), w(s) {}
    Vec4(float _x, float _y, float _z, float _w) : x(_x), y(_y), z(_z), w(_w) {}
    Vec4(const Vec3& v, float _w) : x(v.x), y(v.y), z(v.z), w(_w) {}
    Vec4 operator+(const Vec4& o) const { return Vec4(x + o.x, y + o.y, z + o.z, w + o.w); }
    Vec4 operator-(const Vec4& o) const { return Vec4(x - o.x, y - o.y, z - o.z, w - o.w); }
    Vec4 operator*(float s) const { return Vec4(x * s, y * s, z * s, w * s); }
    Vec4& operator+=(const Vec4& o) { x += o.x; y += o.y; z += o.z; w += o.w; return *this; }
    float operator[](int i) const { return (&x)[i]; }
    float& operator[](int i) { return (&x)[i]; }
    Vec3 xyz() const { return Vec3(x, y, z); }
};

inline Vec2 operator*(float s, const Vec2& v) { return v * s; }
inline Vec3 operator*(float s, const Vec3& v) { return v * s; }

inline float dot(const Vec2& a, const Vec2& b) { return a.x * b.x + a.y * b.y; }
inline float dot(const Vec3& a, const Vec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline float dot(const Vec4& a, const Vec4& b) { return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w; }
inline Vec3 cross(const Vec3& a, const Vec3& b) { return Vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
inline float lengthSq(const Vec2& v) { return dot(v, v); }
inline float lengthSq(const Vec3& v) { return dot(v, v); }
inline float length(const Vec2& v) { return std::sqrt(dot(v, v)); }
inline float length(const Vec3& v) { return std::sqrt(dot(v, v)); }
inline float distance(const Vec2& a, const Vec2& b) { return length(a - b); }
inline float distance(const Vec3& a, const Vec3& b) { return length(a - b); }
inline float distanceSq(const Vec3& a, const Vec3& b) { return lengthSq(a - b); }
inline Vec2 normalize(const Vec2& v) { float l = length(v); return l > EPS ? v / l : Vec2(0, 0); }
inline Vec3 normalize(const Vec3& v) { float l = length(v); return l > EPS ? v / l : Vec3(0, 0, 0); }
inline Vec2 lerp(const Vec2& a, const Vec2& b, float t) { return a + (b - a) * t; }
inline Vec3 lerp(const Vec3& a, const Vec3& b, float t) { return a + (b - a) * t; }
inline Vec4 lerp(const Vec4& a, const Vec4& b, float t) { return a + (b - a) * t; }
inline Vec3 minv(const Vec3& a, const Vec3& b) { return Vec3(std::min(a.x, b.x), std::min(a.y, b.y), std::min(a.z, b.z)); }
inline Vec3 maxv(const Vec3& a, const Vec3& b) { return Vec3(std::max(a.x, b.x), std::max(a.y, b.y), std::max(a.z, b.z)); }
inline Vec3 absv(const Vec3& v) { return Vec3(std::fabs(v.x), std::fabs(v.y), std::fabs(v.z)); }
inline Vec3 clampv(const Vec3& v, const Vec3& a, const Vec3& b) { return minv(maxv(v, a), b); }
inline Vec3 reflect(const Vec3& i, const Vec3& n) { return i - n * (2.0f * dot(i, n)); }
inline Vec3 expDampV(const Vec3& c, const Vec3& t, float rate, float dt) { float f = std::exp(-rate * dt); return t + (c - t) * f; }
inline float maxComp(const Vec3& v) { return std::max(v.x, std::max(v.y, v.z)); }

struct Mat3 {
    float m[9];
    Mat3() { identity(); }
    void identity() { std::memset(m, 0, sizeof(m)); m[0] = m[4] = m[8] = 1.0f; }
    float& at(int c, int r) { return m[c * 3 + r]; }
    float at(int c, int r) const { return m[c * 3 + r]; }
    Vec3 operator*(const Vec3& v) const {
        return Vec3(m[0] * v.x + m[3] * v.y + m[6] * v.z,
                    m[1] * v.x + m[4] * v.y + m[7] * v.z,
                    m[2] * v.x + m[5] * v.y + m[8] * v.z);
    }
    Mat3 operator*(const Mat3& o) const {
        Mat3 r;
        for (int c = 0; c < 3; c++)
            for (int rr = 0; rr < 3; rr++) {
                float s = 0;
                for (int k = 0; k < 3; k++) s += at(k, rr) * o.at(c, k);
                r.at(c, rr) = s;
            }
        return r;
    }
    Mat3 transposed() const {
        Mat3 r;
        for (int c = 0; c < 3; c++) for (int rr = 0; rr < 3; rr++) r.at(c, rr) = at(rr, c);
        return r;
    }
    Vec3 column(int c) const { return Vec3(m[c * 3 + 0], m[c * 3 + 1], m[c * 3 + 2]); }
    void setColumn(int c, const Vec3& v) { m[c * 3 + 0] = v.x; m[c * 3 + 1] = v.y; m[c * 3 + 2] = v.z; }
    Mat3 cofactor() const;
};

struct Mat4 {
    float m[16];
    Mat4() { identity(); }
    void identity() { std::memset(m, 0, sizeof(m)); m[0] = m[5] = m[10] = m[15] = 1.0f; }
    static Mat4 zero() { Mat4 r; std::memset(r.m, 0, sizeof(r.m)); return r; }
    float& at(int c, int r) { return m[c * 4 + r]; }
    float at(int c, int r) const { return m[c * 4 + r]; }

    Mat4 operator*(const Mat4& o) const {
        Mat4 r = Mat4::zero();
        for (int c = 0; c < 4; c++)
            for (int rr = 0; rr < 4; rr++) {
                float s = 0;
                for (int k = 0; k < 4; k++) s += at(k, rr) * o.at(c, k);
                r.at(c, rr) = s;
            }
        return r;
    }
    Vec4 operator*(const Vec4& v) const {
        return Vec4(m[0] * v.x + m[4] * v.y + m[8] * v.z + m[12] * v.w,
                    m[1] * v.x + m[5] * v.y + m[9] * v.z + m[13] * v.w,
                    m[2] * v.x + m[6] * v.y + m[10] * v.z + m[14] * v.w,
                    m[3] * v.x + m[7] * v.y + m[11] * v.z + m[15] * v.w);
    }
    Vec3 mulPoint(const Vec3& v) const {
        Vec4 r = (*this) * Vec4(v, 1.0f);
        if (std::fabs(r.w) > EPS && std::fabs(r.w - 1.0f) > EPS) return Vec3(r.x / r.w, r.y / r.w, r.z / r.w);
        return Vec3(r.x, r.y, r.z);
    }
    Vec3 mulDir(const Vec3& v) const {
        return Vec3(m[0] * v.x + m[4] * v.y + m[8] * v.z,
                    m[1] * v.x + m[5] * v.y + m[9] * v.z,
                    m[2] * v.x + m[6] * v.y + m[10] * v.z);
    }
    Vec3 origin() const { return Vec3(m[12], m[13], m[14]); }
    Mat3 upper3() const {
        Mat3 r;
        for (int c = 0; c < 3; c++) for (int rr = 0; rr < 3; rr++) r.at(c, rr) = at(c, rr);
        return r;
    }

    static Mat4 translate(const Vec3& t) { Mat4 r; r.m[12] = t.x; r.m[13] = t.y; r.m[14] = t.z; return r; }
    static Mat4 scale(const Vec3& s) { Mat4 r; r.m[0] = s.x; r.m[5] = s.y; r.m[10] = s.z; return r; }
    static Mat4 rotateX(float a) {
        Mat4 r; float c = std::cos(a), s = std::sin(a);
        r.m[5] = c; r.m[6] = s; r.m[9] = -s; r.m[10] = c; return r;
    }
    static Mat4 rotateY(float a) {
        Mat4 r; float c = std::cos(a), s = std::sin(a);
        r.m[0] = c; r.m[2] = -s; r.m[8] = s; r.m[10] = c; return r;
    }
    static Mat4 rotateZ(float a) {
        Mat4 r; float c = std::cos(a), s = std::sin(a);
        r.m[0] = c; r.m[1] = s; r.m[4] = -s; r.m[5] = c; return r;
    }
    static Mat4 fromBasis(const Vec3& x, const Vec3& y, const Vec3& z, const Vec3& t) {
        Mat4 r;
        r.m[0] = x.x; r.m[1] = x.y; r.m[2] = x.z; r.m[3] = 0;
        r.m[4] = y.x; r.m[5] = y.y; r.m[6] = y.z; r.m[7] = 0;
        r.m[8] = z.x; r.m[9] = z.y; r.m[10] = z.z; r.m[11] = 0;
        r.m[12] = t.x; r.m[13] = t.y; r.m[14] = t.z; r.m[15] = 1;
        return r;
    }
    static Mat4 trs(const Vec3& t, float yaw, const Vec3& s) {
        Mat4 r = rotateY(yaw) * scale(s);
        r.m[12] = t.x; r.m[13] = t.y; r.m[14] = t.z;
        return r;
    }
    static Mat4 perspective(float fovY, float aspect, float zn, float zf) {
        Mat4 r = Mat4::zero();
        float t = 1.0f / std::tan(fovY * 0.5f);
        r.m[0] = t / aspect;
        r.m[5] = t;
        r.m[10] = (zf + zn) / (zn - zf);
        r.m[11] = -1.0f;
        r.m[14] = (2.0f * zf * zn) / (zn - zf);
        return r;
    }
    static Mat4 ortho(float l, float r_, float b, float t, float zn, float zf) {
        Mat4 r;
        r.m[0] = 2.0f / (r_ - l);
        r.m[5] = 2.0f / (t - b);
        r.m[10] = -2.0f / (zf - zn);
        r.m[12] = -(r_ + l) / (r_ - l);
        r.m[13] = -(t + b) / (t - b);
        r.m[14] = -(zf + zn) / (zf - zn);
        return r;
    }
    static Mat4 lookAt(const Vec3& eye, const Vec3& center, const Vec3& up) {
        Vec3 f = normalize(center - eye);
        Vec3 upn = up;
        if (std::fabs(dot(f, upn)) > 0.999f) upn = Vec3(1, 0, 0);
        Vec3 s = normalize(cross(f, upn));
        Vec3 u = cross(s, f);
        Mat4 r;
        r.m[0] = s.x; r.m[4] = s.y; r.m[8] = s.z;
        r.m[1] = u.x; r.m[5] = u.y; r.m[9] = u.z;
        r.m[2] = -f.x; r.m[6] = -f.y; r.m[10] = -f.z;
        r.m[12] = -dot(s, eye);
        r.m[13] = -dot(u, eye);
        r.m[14] = dot(f, eye);
        return r;
    }
    Mat4 transposed() const {
        Mat4 r;
        for (int c = 0; c < 4; c++) for (int rr = 0; rr < 4; rr++) r.at(c, rr) = at(rr, c);
        return r;
    }
    Mat4 inverted() const {
        const float* a = m;
        float inv[16];
        inv[0] = a[5]*a[10]*a[15] - a[5]*a[11]*a[14] - a[9]*a[6]*a[15] + a[9]*a[7]*a[14] + a[13]*a[6]*a[11] - a[13]*a[7]*a[10];
        inv[4] = -a[4]*a[10]*a[15] + a[4]*a[11]*a[14] + a[8]*a[6]*a[15] - a[8]*a[7]*a[14] - a[12]*a[6]*a[11] + a[12]*a[7]*a[10];
        inv[8] = a[4]*a[9]*a[15] - a[4]*a[11]*a[13] - a[8]*a[5]*a[15] + a[8]*a[7]*a[13] + a[12]*a[5]*a[11] - a[12]*a[7]*a[9];
        inv[12] = -a[4]*a[9]*a[14] + a[4]*a[10]*a[13] + a[8]*a[5]*a[14] - a[8]*a[6]*a[13] - a[12]*a[5]*a[10] + a[12]*a[6]*a[9];
        inv[1] = -a[1]*a[10]*a[15] + a[1]*a[11]*a[14] + a[9]*a[2]*a[15] - a[9]*a[3]*a[14] - a[13]*a[2]*a[11] + a[13]*a[3]*a[10];
        inv[5] = a[0]*a[10]*a[15] - a[0]*a[11]*a[14] - a[8]*a[2]*a[15] + a[8]*a[3]*a[14] + a[12]*a[2]*a[11] - a[12]*a[3]*a[10];
        inv[9] = -a[0]*a[9]*a[15] + a[0]*a[11]*a[13] + a[8]*a[1]*a[15] - a[8]*a[3]*a[13] - a[12]*a[1]*a[11] + a[12]*a[3]*a[9];
        inv[13] = a[0]*a[9]*a[14] - a[0]*a[10]*a[13] - a[8]*a[1]*a[14] + a[8]*a[2]*a[13] + a[12]*a[1]*a[10] - a[12]*a[2]*a[9];
        inv[2] = a[1]*a[6]*a[15] - a[1]*a[7]*a[14] - a[5]*a[2]*a[15] + a[5]*a[3]*a[14] + a[13]*a[2]*a[7] - a[13]*a[3]*a[6];
        inv[6] = -a[0]*a[6]*a[15] + a[0]*a[7]*a[14] + a[4]*a[2]*a[15] - a[4]*a[3]*a[14] - a[12]*a[2]*a[7] + a[12]*a[3]*a[6];
        inv[10] = a[0]*a[5]*a[15] - a[0]*a[7]*a[13] - a[4]*a[1]*a[15] + a[4]*a[3]*a[13] + a[12]*a[1]*a[7] - a[12]*a[3]*a[5];
        inv[14] = -a[0]*a[5]*a[14] + a[0]*a[6]*a[13] + a[4]*a[1]*a[14] - a[4]*a[2]*a[13] - a[12]*a[1]*a[6] + a[12]*a[2]*a[5];
        inv[3] = -a[1]*a[6]*a[11] + a[1]*a[7]*a[10] + a[5]*a[2]*a[11] - a[5]*a[3]*a[10] - a[9]*a[2]*a[7] + a[9]*a[3]*a[6];
        inv[7] = a[0]*a[6]*a[11] - a[0]*a[7]*a[10] - a[4]*a[2]*a[11] + a[4]*a[3]*a[10] + a[8]*a[2]*a[7] - a[8]*a[3]*a[6];
        inv[11] = -a[0]*a[5]*a[11] + a[0]*a[7]*a[9] + a[4]*a[1]*a[11] - a[4]*a[3]*a[9] - a[8]*a[1]*a[7] + a[8]*a[3]*a[5];
        inv[15] = a[0]*a[5]*a[10] - a[0]*a[6]*a[9] - a[4]*a[1]*a[10] + a[4]*a[2]*a[9] + a[8]*a[1]*a[6] - a[8]*a[2]*a[5];
        float det = a[0]*inv[0] + a[1]*inv[4] + a[2]*inv[8] + a[3]*inv[12];
        Mat4 r;
        if (std::fabs(det) < 1e-12f) return r;
        det = 1.0f / det;
        for (int i = 0; i < 16; i++) r.m[i] = inv[i] * det;
        return r;
    }
    Mat3 normalMatrix() const { return upper3().cofactor(); }
};

inline Mat3 Mat3::cofactor() const {
    Vec3 c0 = column(0), c1 = column(1), c2 = column(2);
    Mat3 r;
    r.setColumn(0, cross(c1, c2));
    r.setColumn(1, cross(c2, c0));
    r.setColumn(2, cross(c0, c1));
    return r;
}

struct AABB {
    Vec3 mn = Vec3(1e30f), mx = Vec3(-1e30f);
    AABB() {}
    AABB(const Vec3& a, const Vec3& b) : mn(a), mx(b) {}
    void expand(const Vec3& p) { mn = minv(mn, p); mx = maxv(mx, p); }
    void expand(const AABB& o) { mn = minv(mn, o.mn); mx = maxv(mx, o.mx); }
    void grow(float d) { mn -= Vec3(d); mx += Vec3(d); }
    Vec3 center() const { return (mn + mx) * 0.5f; }
    Vec3 extents() const { return (mx - mn) * 0.5f; }
    Vec3 size() const { return mx - mn; }
    bool valid() const { return mx.x >= mn.x; }
    bool contains(const Vec3& p) const { return p.x >= mn.x && p.x <= mx.x && p.y >= mn.y && p.y <= mx.y && p.z >= mn.z && p.z <= mx.z; }
    bool overlaps(const AABB& o) const { return mn.x <= o.mx.x && mx.x >= o.mn.x && mn.y <= o.mx.y && mx.y >= o.mn.y && mn.z <= o.mx.z && mx.z >= o.mn.z; }
    Vec3 closest(const Vec3& p) const { return clampv(p, mn, mx); }
    float distSq(const Vec3& p) const { Vec3 c = closest(p); return lengthSq(p - c); }
    static AABB fromCenter(const Vec3& c, const Vec3& half) { return AABB(c - half, c + half); }
    AABB transformed(const Mat4& mat) const {
        AABB r;
        for (int i = 0; i < 8; i++) {
            Vec3 p(i & 1 ? mx.x : mn.x, i & 2 ? mx.y : mn.y, i & 4 ? mx.z : mn.z);
            r.expand(mat.mulPoint(p));
        }
        return r;
    }
};

struct Plane {
    Vec3 n; float d = 0;
    Plane() {}
    Plane(const Vec3& _n, float _d) : n(_n), d(_d) {}
    float dist(const Vec3& p) const { return dot(n, p) + d; }
};

struct Frustum {
    Plane p[6];
    void fromMatrix(const Mat4& vp) {
        const float* m = vp.m;
        auto set = [&](int i, float a, float b, float c, float dd) {
            float l = std::sqrt(a * a + b * b + c * c);
            if (l < EPS) l = 1.0f;
            p[i] = Plane(Vec3(a / l, b / l, c / l), dd / l);
        };
        set(0, m[3] + m[0], m[7] + m[4], m[11] + m[8], m[15] + m[12]);
        set(1, m[3] - m[0], m[7] - m[4], m[11] - m[8], m[15] - m[12]);
        set(2, m[3] + m[1], m[7] + m[5], m[11] + m[9], m[15] + m[13]);
        set(3, m[3] - m[1], m[7] - m[5], m[11] - m[9], m[15] - m[13]);
        set(4, m[3] + m[2], m[7] + m[6], m[11] + m[10], m[15] + m[14]);
        set(5, m[3] - m[2], m[7] - m[6], m[11] - m[10], m[15] - m[14]);
    }
    bool testAABB(const AABB& b) const {
        Vec3 c = b.center(), e = b.extents();
        for (int i = 0; i < 6; i++) {
            float r = e.x * std::fabs(p[i].n.x) + e.y * std::fabs(p[i].n.y) + e.z * std::fabs(p[i].n.z);
            if (p[i].dist(c) < -r) return false;
        }
        return true;
    }
    bool testSphere(const Vec3& c, float r) const {
        for (int i = 0; i < 6; i++) if (p[i].dist(c) < -r) return false;
        return true;
    }
};

inline Vec3 sphericalDir(float yaw, float pitch) {
    float cp = std::cos(pitch);
    return Vec3(std::sin(yaw) * cp, std::sin(pitch), -std::cos(yaw) * cp);
}

inline float hash11(float p) {
    p = fractf(p * 0.1031f);
    p *= p + 33.33f;
    p *= p + p;
    return fractf(p);
}

inline float hash21(const Vec2& p) {
    Vec3 p3(fractf(p.x * 0.1031f), fractf(p.y * 0.1030f), fractf(p.x * 0.0973f));
    float d = dot(p3, Vec3(p3.y + 33.33f, p3.z + 33.33f, p3.x + 33.33f));
    p3 += Vec3(d);
    return fractf((p3.x + p3.y) * p3.z);
}

inline float hash31(const Vec3& p) {
    Vec3 p3(fractf(p.x * 0.1031f), fractf(p.y * 0.1030f), fractf(p.z * 0.0973f));
    float d = dot(p3, Vec3(p3.y + 33.33f, p3.z + 33.33f, p3.x + 33.33f));
    p3 += Vec3(d);
    return fractf((p3.x + p3.y) * p3.z);
}

inline float valueNoise2(const Vec2& p) {
    Vec2 i(std::floor(p.x), std::floor(p.y));
    Vec2 f(p.x - i.x, p.y - i.y);
    Vec2 u(f.x * f.x * (3.0f - 2.0f * f.x), f.y * f.y * (3.0f - 2.0f * f.y));
    float a = hash21(i);
    float b = hash21(i + Vec2(1, 0));
    float c = hash21(i + Vec2(0, 1));
    float d = hash21(i + Vec2(1, 1));
    return lerpf(lerpf(a, b, u.x), lerpf(c, d, u.x), u.y);
}

inline float valueNoise3(const Vec3& p) {
    Vec3 i(std::floor(p.x), std::floor(p.y), std::floor(p.z));
    Vec3 f = p - i;
    Vec3 u(f.x * f.x * (3 - 2 * f.x), f.y * f.y * (3 - 2 * f.y), f.z * f.z * (3 - 2 * f.z));
    float n000 = hash31(i);
    float n100 = hash31(i + Vec3(1, 0, 0));
    float n010 = hash31(i + Vec3(0, 1, 0));
    float n110 = hash31(i + Vec3(1, 1, 0));
    float n001 = hash31(i + Vec3(0, 0, 1));
    float n101 = hash31(i + Vec3(1, 0, 1));
    float n011 = hash31(i + Vec3(0, 1, 1));
    float n111 = hash31(i + Vec3(1, 1, 1));
    float x00 = lerpf(n000, n100, u.x);
    float x10 = lerpf(n010, n110, u.x);
    float x01 = lerpf(n001, n101, u.x);
    float x11 = lerpf(n011, n111, u.x);
    return lerpf(lerpf(x00, x10, u.y), lerpf(x01, x11, u.y), u.z);
}

inline float fbm2(Vec2 p, int oct, float lac = 2.0f, float gain = 0.5f) {
    float a = 0.5f, s = 0.0f, norm = 0.0f;
    for (int i = 0; i < oct; i++) {
        s += a * valueNoise2(p);
        norm += a;
        p *= lac;
        a *= gain;
    }
    return norm > 0 ? s / norm : 0.0f;
}

inline float fbm3(Vec3 p, int oct, float lac = 2.0f, float gain = 0.5f) {
    float a = 0.5f, s = 0.0f, norm = 0.0f;
    for (int i = 0; i < oct; i++) {
        s += a * valueNoise3(p);
        norm += a;
        p *= lac;
        a *= gain;
    }
    return norm > 0 ? s / norm : 0.0f;
}

inline float worley2(const Vec2& p, float& second) {
    Vec2 ip(std::floor(p.x), std::floor(p.y));
    float f1 = 1e9f, f2 = 1e9f;
    for (int y = -1; y <= 1; y++)
        for (int x = -1; x <= 1; x++) {
            Vec2 g = ip + Vec2((float)x, (float)y);
            Vec2 o(hash21(g), hash21(g + Vec2(37.1f, 11.7f)));
            float d = length(g + o - p);
            if (d < f1) { f2 = f1; f1 = d; }
            else if (d < f2) f2 = d;
        }
    second = f2;
    return f1;
}

}
