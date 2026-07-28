#include "Collision.h"

using namespace em;

namespace echo {

Vec3 Collider::toLocal(const Vec3& p) const {
    Vec3 d = p - center;
    if (std::fabs(yaw) < 1e-5f) return d;
    float c = std::cos(-yaw), s = std::sin(-yaw);
    return Vec3(d.x * c + d.z * s, d.y, -d.x * s + d.z * c);
}

Vec3 Collider::toWorld(const Vec3& p) const {
    if (std::fabs(yaw) < 1e-5f) return p + center;
    float c = std::cos(yaw), s = std::sin(yaw);
    return Vec3(p.x * c + p.z * s, p.y, -p.x * s + p.z * c) + center;
}

AABB Collider::worldBounds() const {
    if (std::fabs(yaw) < 1e-5f) return AABB(center - half, center + half);
    float c = std::fabs(std::cos(yaw)), s = std::fabs(std::sin(yaw));
    Vec3 e(half.x * c + half.z * s, half.y, half.x * s + half.z * c);
    return AABB(center - e, center + e);
}

Vec3 Collider::closestPoint(const Vec3& p) const {
    Vec3 l = toLocal(p);
    Vec3 cl = clampv(l, -half, half);
    return toWorld(cl);
}

bool Collider::containsPoint(const Vec3& p) const {
    Vec3 l = toLocal(p);
    return std::fabs(l.x) <= half.x && std::fabs(l.y) <= half.y && std::fabs(l.z) <= half.z;
}

bool rayAABB(const Vec3& origin, const Vec3& dir, const AABB& box, float maxDist, float& tOut, Vec3& nOut) {
    float tmin = 0.0f, tmax = maxDist;
    int axis = -1;
    float sign = 1.0f;

    for (int i = 0; i < 3; i++) {
        float d = dir[i];
        float o = origin[i];
        if (std::fabs(d) < 1e-8f) {
            if (o < box.mn[i] || o > box.mx[i]) return false;
            continue;
        }
        float inv = 1.0f / d;
        float t1 = (box.mn[i] - o) * inv;
        float t2 = (box.mx[i] - o) * inv;
        float s = -1.0f;
        if (t1 > t2) { std::swap(t1, t2); s = 1.0f; }
        if (t1 > tmin) { tmin = t1; axis = i; sign = s; }
        if (t2 < tmax) tmax = t2;
        if (tmin > tmax) return false;
    }

    tOut = tmin;
    nOut = Vec3(0, 0, 0);
    if (axis >= 0) nOut[axis] = sign;
    else nOut = -dir;
    return true;
}

bool rayCollider(const Vec3& origin, const Vec3& dir, const Collider& c, float maxDist, float& tOut, Vec3& nOut) {
    if (!c.enabled) return false;
    Vec3 lo = c.toLocal(origin);
    Vec3 ld = dir;
    if (std::fabs(c.yaw) > 1e-5f) {
        float cs = std::cos(-c.yaw), sn = std::sin(-c.yaw);
        ld = Vec3(dir.x * cs + dir.z * sn, dir.y, -dir.x * sn + dir.z * cs);
    }
    AABB box(-c.half, c.half);
    Vec3 ln;
    if (!rayAABB(lo, ld, box, maxDist, tOut, ln)) return false;
    if (std::fabs(c.yaw) > 1e-5f) {
        float cs = std::cos(c.yaw), sn = std::sin(c.yaw);
        nOut = Vec3(ln.x * cs + ln.z * sn, ln.y, -ln.x * sn + ln.z * cs);
    } else {
        nOut = ln;
    }
    return true;
}

bool sphereCollider(const Vec3& center, float radius, const Collider& c, Vec3& normalOut, float& depthOut) {
    if (!c.enabled) return false;
    Vec3 l = c.toLocal(center);
    Vec3 cl = clampv(l, -c.half, c.half);
    Vec3 d = l - cl;
    float dist2 = lengthSq(d);

    if (dist2 > radius * radius) return false;

    Vec3 n;
    if (dist2 > 1e-8f) {
        float dist = std::sqrt(dist2);
        n = d / dist;
        depthOut = radius - dist;
    } else {
        Vec3 dx = c.half - absv(l);
        if (dx.x <= dx.y && dx.x <= dx.z) { n = Vec3(l.x < 0 ? -1.0f : 1.0f, 0, 0); depthOut = radius + dx.x; }
        else if (dx.y <= dx.z) { n = Vec3(0, l.y < 0 ? -1.0f : 1.0f, 0); depthOut = radius + dx.y; }
        else { n = Vec3(0, 0, l.z < 0 ? -1.0f : 1.0f); depthOut = radius + dx.z; }
    }

    if (std::fabs(c.yaw) > 1e-5f) {
        float cs = std::cos(c.yaw), sn = std::sin(c.yaw);
        n = Vec3(n.x * cs + n.z * sn, n.y, -n.x * sn + n.z * cs);
    }
    normalOut = n;
    return true;
}

bool capsuleCollider(const Vec3& base, const Vec3& top, float radius, const Collider& c, Vec3& normalOut, float& depthOut) {
    if (!c.enabled) return false;
    Vec3 lb = c.toLocal(base);
    Vec3 lt = c.toLocal(top);

    float boxLow = -c.half.y;
    float boxHigh = c.half.y;
    float y = clampf((boxLow + boxHigh) * 0.5f, std::min(lb.y, lt.y), std::max(lb.y, lt.y));

    Vec3 axis = lt - lb;
    float axisLen = length(axis);
    float t = 0.0f;
    if (axisLen > 1e-5f) t = clampf((y - lb.y) / axis.y, 0.0f, 1.0f);
    Vec3 sphereCenterLocal = lb + axis * t;

    Vec3 cl = clampv(sphereCenterLocal, -c.half, c.half);
    Vec3 d = sphereCenterLocal - cl;
    float dist2 = lengthSq(d);
    if (dist2 > radius * radius) return false;

    Vec3 n;
    if (dist2 > 1e-8f) {
        float dist = std::sqrt(dist2);
        n = d / dist;
        depthOut = radius - dist;
    } else {
        Vec3 dx = c.half - absv(sphereCenterLocal);
        if (dx.x <= dx.z) { n = Vec3(sphereCenterLocal.x < 0 ? -1.0f : 1.0f, 0, 0); depthOut = radius + dx.x; }
        else { n = Vec3(0, 0, sphereCenterLocal.z < 0 ? -1.0f : 1.0f); depthOut = radius + dx.z; }
    }

    if (std::fabs(c.yaw) > 1e-5f) {
        float cs = std::cos(c.yaw), sn = std::sin(c.yaw);
        n = Vec3(n.x * cs + n.z * sn, n.y, -n.x * sn + n.z * cs);
    }
    normalOut = n;
    return true;
}

bool segmentCollider(const Vec3& a, const Vec3& b, const Collider& c) {
    Vec3 d = b - a;
    float len = length(d);
    if (len < 1e-5f) return c.containsPoint(a);
    d /= len;
    float t;
    Vec3 n;
    if (!rayCollider(a, d, c, len, t, n)) return false;
    return t >= 0.0f && t <= len;
}

}
