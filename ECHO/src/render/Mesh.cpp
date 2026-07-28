#include "Mesh.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

void Mesh::upload(const std::vector<Vertex>& v, const std::vector<u32>& idx, const std::vector<SubMesh>& s) {
    destroy();
    if (v.empty() || idx.empty()) return;

    subs = s;
    totalIndices = (u32)idx.size();
    totalVertices = (u32)v.size();
    aabb = AABB();
    for (const auto& sm : subs) aabb.expand(sm.bounds);
    if (!aabb.valid()) for (const auto& vt : v) aabb.expand(vt.pos);

    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);

    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)(v.size() * sizeof(Vertex)), v.data(), GL_STATIC_DRAW);

    glGenBuffers(1, &ibo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, (GLsizeiptr)(idx.size() * sizeof(u32)), idx.data(), GL_STATIC_DRAW);

    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, pos));
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, normal));
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, tangent));
    glEnableVertexAttribArray(3);
    glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, uv));
    glEnableVertexAttribArray(4);
    glVertexAttribPointer(4, 4, GL_UNSIGNED_BYTE, GL_TRUE, sizeof(Vertex), (void*)offsetof(Vertex, color));

    glBindVertexArray(0);
}

void Mesh::setInstanceBuffer(GLuint buffer, int stride) {
    if (!vao) return;
    glBindVertexArray(vao);
    glBindBuffer(GL_ARRAY_BUFFER, buffer);
    for (int i = 0; i < 4; i++) {
        glEnableVertexAttribArray(5 + i);
        glVertexAttribPointer(5 + i, 4, GL_FLOAT, GL_FALSE, stride, (void*)(size_t)(i * 16));
        glVertexAttribDivisor(5 + i, 1);
    }
    glBindVertexArray(0);
}

void Mesh::destroy() {
    if (ibo) { glDeleteBuffers(1, &ibo); ibo = 0; }
    if (vbo) { glDeleteBuffers(1, &vbo); vbo = 0; }
    if (vao) { glDeleteVertexArrays(1, &vao); vao = 0; }
    subs.clear();
    totalIndices = totalVertices = 0;
}

void Mesh::bind() const { glBindVertexArray(vao); }

void Mesh::draw() const {
    if (!vao) return;
    glBindVertexArray(vao);
    glDrawElements(GL_TRIANGLES, (GLsizei)totalIndices, GL_UNSIGNED_INT, nullptr);
}

void Mesh::drawSub(int index) const {
    if (!vao || index < 0 || index >= (int)subs.size()) return;
    const SubMesh& s = subs[index];
    glDrawElements(GL_TRIANGLES, (GLsizei)s.indexCount, GL_UNSIGNED_INT, (void*)(size_t)(s.indexOffset * sizeof(u32)));
}

void Mesh::drawSubInstanced(int index, int count) const {
    if (!vao || index < 0 || index >= (int)subs.size()) return;
    const SubMesh& s = subs[index];
    glDrawElementsInstanced(GL_TRIANGLES, (GLsizei)s.indexCount, GL_UNSIGNED_INT, (void*)(size_t)(s.indexOffset * sizeof(u32)), count);
}

void MeshBuilder::clear() {
    verts.clear();
    inds.clear();
    subs.clear();
    stack.clear();
    xform.identity();
    aabb = AABB();
    subAabb = AABB();
    current = 0;
    pendingStart = 0;
    vcolor = Vec4(1, 1, 1, 1);
    uvScale = Vec2(1, 1);
    uvOffset = Vec2(0, 0);
}

void MeshBuilder::pushTransform(const Mat4& m) {
    stack.push_back(xform);
    xform = xform * m;
}

void MeshBuilder::popTransform() {
    if (stack.empty()) { xform.identity(); return; }
    xform = stack.back();
    stack.pop_back();
}

u32 MeshBuilder::addVertex(const Vec3& p, const Vec3& n, const Vec2& uv) {
    Vertex v;
    v.pos = xform.mulPoint(p);
    v.normal = normalize(xform.mulDir(n));
    v.uv = Vec2(uv.x * uvScale.x + uvOffset.x, uv.y * uvScale.y + uvOffset.y);
    v.tangent = Vec4(0, 0, 0, 1);
    v.color[0] = (u8)(saturate(vcolor.x) * 255.0f);
    v.color[1] = (u8)(saturate(vcolor.y) * 255.0f);
    v.color[2] = (u8)(saturate(vcolor.z) * 255.0f);
    v.color[3] = (u8)(saturate(vcolor.w) * 255.0f);
    verts.push_back(v);
    aabb.expand(v.pos);
    subAabb.expand(v.pos);
    return (u32)verts.size() - 1;
}

void MeshBuilder::addTri(u32 a, u32 b, u32 c) {
    inds.push_back(a);
    inds.push_back(b);
    inds.push_back(c);
}

void MeshBuilder::addQuad(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d, const Vec3& n, bool planarUV) {
    Vec2 uv0(0, 0), uv1(1, 0), uv2(1, 1), uv3(0, 1);
    if (planarUV) {
        Vec3 an = absv(n);
        Vec3 uAxis, vAxis;
        if (an.y >= an.x && an.y >= an.z) { uAxis = Vec3(1, 0, 0); vAxis = Vec3(0, 0, 1); }
        else if (an.x >= an.z) { uAxis = Vec3(0, 0, 1); vAxis = Vec3(0, 1, 0); }
        else { uAxis = Vec3(1, 0, 0); vAxis = Vec3(0, 1, 0); }
        uv0 = Vec2(dot(a, uAxis), dot(a, vAxis));
        uv1 = Vec2(dot(b, uAxis), dot(b, vAxis));
        uv2 = Vec2(dot(c, uAxis), dot(c, vAxis));
        uv3 = Vec2(dot(d, uAxis), dot(d, vAxis));
    }
    u32 i0 = addVertex(a, n, uv0);
    u32 i1 = addVertex(b, n, uv1);
    u32 i2 = addVertex(c, n, uv2);
    u32 i3 = addVertex(d, n, uv3);
    addTri(i0, i1, i2);
    addTri(i0, i2, i3);
}

void MeshBuilder::addBoxFaces(const Vec3& c, const Vec3& h, int faceMask) {
    Vec3 p[8] = {
        Vec3(c.x - h.x, c.y - h.y, c.z - h.z), Vec3(c.x + h.x, c.y - h.y, c.z - h.z),
        Vec3(c.x + h.x, c.y + h.y, c.z - h.z), Vec3(c.x - h.x, c.y + h.y, c.z - h.z),
        Vec3(c.x - h.x, c.y - h.y, c.z + h.z), Vec3(c.x + h.x, c.y - h.y, c.z + h.z),
        Vec3(c.x + h.x, c.y + h.y, c.z + h.z), Vec3(c.x - h.x, c.y + h.y, c.z + h.z)
    };
    if (faceMask & 1) addQuad(p[4], p[5], p[6], p[7], Vec3(0, 0, 1));
    if (faceMask & 2) addQuad(p[1], p[0], p[3], p[2], Vec3(0, 0, -1));
    if (faceMask & 4) addQuad(p[1], p[2], p[6], p[5], Vec3(1, 0, 0));
    if (faceMask & 8) addQuad(p[0], p[4], p[7], p[3], Vec3(-1, 0, 0));
    if (faceMask & 16) addQuad(p[3], p[7], p[6], p[2], Vec3(0, 1, 0));
    if (faceMask & 32) addQuad(p[0], p[1], p[5], p[4], Vec3(0, -1, 0));
}

void MeshBuilder::addBox(const Vec3& c, const Vec3& h) {
    addBoxFaces(c, h, 63);
}

void MeshBuilder::addBoxInner(const Vec3& c, const Vec3& h) {
    Vec3 p[8] = {
        Vec3(c.x - h.x, c.y - h.y, c.z - h.z), Vec3(c.x + h.x, c.y - h.y, c.z - h.z),
        Vec3(c.x + h.x, c.y + h.y, c.z - h.z), Vec3(c.x - h.x, c.y + h.y, c.z - h.z),
        Vec3(c.x - h.x, c.y - h.y, c.z + h.z), Vec3(c.x + h.x, c.y - h.y, c.z + h.z),
        Vec3(c.x + h.x, c.y + h.y, c.z + h.z), Vec3(c.x - h.x, c.y + h.y, c.z + h.z)
    };
    addQuad(p[7], p[6], p[5], p[4], Vec3(0, 0, -1));
    addQuad(p[2], p[3], p[0], p[1], Vec3(0, 0, 1));
    addQuad(p[5], p[6], p[2], p[1], Vec3(-1, 0, 0));
    addQuad(p[3], p[7], p[4], p[0], Vec3(1, 0, 0));
    addQuad(p[2], p[6], p[7], p[3], Vec3(0, -1, 0));
    addQuad(p[4], p[5], p[1], p[0], Vec3(0, 1, 0));
}

void MeshBuilder::addPlane(const Vec3& c, const Vec2& size, const Vec3& n, int subdiv) {
    Vec3 up = std::fabs(n.y) > 0.9f ? Vec3(0, 0, 1) : Vec3(0, 1, 0);
    Vec3 t = normalize(cross(up, n));
    Vec3 b = cross(n, t);
    if (subdiv < 1) subdiv = 1;
    for (int j = 0; j < subdiv; j++) {
        for (int i = 0; i < subdiv; i++) {
            float x0 = (float)i / subdiv - 0.5f, x1 = (float)(i + 1) / subdiv - 0.5f;
            float y0 = (float)j / subdiv - 0.5f, y1 = (float)(j + 1) / subdiv - 0.5f;
            Vec3 a = c + t * (x0 * size.x) + b * (y0 * size.y);
            Vec3 bb = c + t * (x1 * size.x) + b * (y0 * size.y);
            Vec3 cc = c + t * (x1 * size.x) + b * (y1 * size.y);
            Vec3 dd = c + t * (x0 * size.x) + b * (y1 * size.y);
            u32 i0 = addVertex(a, n, Vec2((x0 + 0.5f) * size.x, (y0 + 0.5f) * size.y));
            u32 i1 = addVertex(bb, n, Vec2((x1 + 0.5f) * size.x, (y0 + 0.5f) * size.y));
            u32 i2 = addVertex(cc, n, Vec2((x1 + 0.5f) * size.x, (y1 + 0.5f) * size.y));
            u32 i3 = addVertex(dd, n, Vec2((x0 + 0.5f) * size.x, (y1 + 0.5f) * size.y));
            addTri(i0, i1, i2);
            addTri(i0, i2, i3);
        }
    }
}

void MeshBuilder::addCylinder(const Vec3& base, float radius, float height, int segments, bool caps) {
    addCone(base, radius, radius, height, segments, caps);
}

void MeshBuilder::addCone(const Vec3& base, float r0, float r1, float height, int segments, bool caps) {
    if (segments < 3) segments = 3;
    float circ = TAU * std::max(r0, r1);
    for (int i = 0; i < segments; i++) {
        float a0 = TAU * i / segments;
        float a1 = TAU * (i + 1) / segments;
        Vec3 d0(std::cos(a0), 0, std::sin(a0));
        Vec3 d1(std::cos(a1), 0, std::sin(a1));
        Vec3 p0 = base + d0 * r0;
        Vec3 p1 = base + d1 * r0;
        Vec3 p2 = base + Vec3(0, height, 0) + d1 * r1;
        Vec3 p3 = base + Vec3(0, height, 0) + d0 * r1;
        Vec3 n0 = normalize(Vec3(d0.x, (r0 - r1) / std::max(height, 0.001f), d0.z));
        Vec3 n1 = normalize(Vec3(d1.x, (r0 - r1) / std::max(height, 0.001f), d1.z));
        float u0 = circ * i / segments, u1 = circ * (i + 1) / segments;
        u32 i0 = addVertex(p0, n0, Vec2(u0, 0));
        u32 i1 = addVertex(p1, n1, Vec2(u1, 0));
        u32 i2 = addVertex(p2, n1, Vec2(u1, height));
        u32 i3 = addVertex(p3, n0, Vec2(u0, height));
        addTri(i0, i3, i2);
        addTri(i0, i2, i1);
    }
    if (caps) {
        if (r1 > 0.0001f) {
            u32 center = addVertex(base + Vec3(0, height, 0), Vec3(0, 1, 0), Vec2(0, 0));
            for (int i = 0; i < segments; i++) {
                float a0 = TAU * i / segments, a1 = TAU * (i + 1) / segments;
                u32 v0 = addVertex(base + Vec3(0, height, 0) + Vec3(std::cos(a0), 0, std::sin(a0)) * r1, Vec3(0, 1, 0), Vec2(std::cos(a0) * r1, std::sin(a0) * r1));
                u32 v1 = addVertex(base + Vec3(0, height, 0) + Vec3(std::cos(a1), 0, std::sin(a1)) * r1, Vec3(0, 1, 0), Vec2(std::cos(a1) * r1, std::sin(a1) * r1));
                addTri(center, v1, v0);
            }
        }
        if (r0 > 0.0001f) {
            u32 center = addVertex(base, Vec3(0, -1, 0), Vec2(0, 0));
            for (int i = 0; i < segments; i++) {
                float a0 = TAU * i / segments, a1 = TAU * (i + 1) / segments;
                u32 v0 = addVertex(base + Vec3(std::cos(a0), 0, std::sin(a0)) * r0, Vec3(0, -1, 0), Vec2(std::cos(a0) * r0, std::sin(a0) * r0));
                u32 v1 = addVertex(base + Vec3(std::cos(a1), 0, std::sin(a1)) * r0, Vec3(0, -1, 0), Vec2(std::cos(a1) * r0, std::sin(a1) * r0));
                addTri(center, v0, v1);
            }
        }
    }
}

void MeshBuilder::addSphere(const Vec3& c, float radius, int rings, int segments) {
    if (rings < 2) rings = 2;
    if (segments < 3) segments = 3;
    u32 base = (u32)verts.size();
    for (int y = 0; y <= rings; y++) {
        float v = (float)y / rings;
        float phi = v * PI;
        for (int x = 0; x <= segments; x++) {
            float u = (float)x / segments;
            float theta = u * TAU;
            Vec3 n(std::sin(phi) * std::cos(theta), std::cos(phi), std::sin(phi) * std::sin(theta));
            addVertex(c + n * radius, n, Vec2(u * TAU * radius, v * PI * radius));
        }
    }
    for (int y = 0; y < rings; y++) {
        for (int x = 0; x < segments; x++) {
            u32 i0 = base + y * (segments + 1) + x;
            u32 i1 = i0 + segments + 1;
            addTri(i0, i0 + 1, i1);
            addTri(i0 + 1, i1 + 1, i1);
        }
    }
}

void MeshBuilder::addTorusArc(const Vec3& c, float major, float minor, float startAngle, float sweep, int seg, int sides) {
    if (seg < 2) seg = 2;
    if (sides < 3) sides = 3;
    u32 base = (u32)verts.size();
    for (int i = 0; i <= seg; i++) {
        float t = (float)i / seg;
        float a = startAngle + sweep * t;
        Vec3 center(std::cos(a) * major, 0, std::sin(a) * major);
        Vec3 outward(std::cos(a), 0, std::sin(a));
        for (int j = 0; j <= sides; j++) {
            float b = TAU * j / sides;
            Vec3 n = outward * std::cos(b) + Vec3(0, 1, 0) * std::sin(b);
            addVertex(c + center + n * minor, n, Vec2(t * major * std::fabs(sweep), (float)j / sides * TAU * minor));
        }
    }
    for (int i = 0; i < seg; i++) {
        for (int j = 0; j < sides; j++) {
            u32 i0 = base + i * (sides + 1) + j;
            u32 i1 = i0 + sides + 1;
            addTri(i0, i0 + 1, i1);
            addTri(i0 + 1, i1 + 1, i1);
        }
    }
}

void MeshBuilder::addWedge(const Vec3& c, const Vec3& h, int axis) {
    Vec3 a0(c.x - h.x, c.y - h.y, c.z - h.z);
    Vec3 a1(c.x + h.x, c.y - h.y, c.z - h.z);
    Vec3 a2(c.x + h.x, c.y - h.y, c.z + h.z);
    Vec3 a3(c.x - h.x, c.y - h.y, c.z + h.z);
    Vec3 t0(c.x - h.x, c.y + h.y, c.z - h.z);
    Vec3 t1(c.x + h.x, c.y + h.y, c.z - h.z);
    if (axis == 1) { t0 = Vec3(c.x - h.x, c.y + h.y, c.z + h.z); t1 = Vec3(c.x + h.x, c.y + h.y, c.z + h.z); }
    addQuad(a0, a1, a2, a3, Vec3(0, -1, 0));
    Vec3 slopeN = normalize(cross(t1 - t0, (axis == 1 ? a0 : a3) - t0));
    if (axis == 1) addQuad(t0, t1, a1, a0, slopeN);
    else addQuad(a3, a2, t1, t0, slopeN);
    if (axis == 1) {
        addQuad(a3, a2, t1, t0, Vec3(0, 0, 1));
        u32 s0 = addVertex(a0, Vec3(-1, 0, 0), Vec2(a0.z, a0.y));
        u32 s1 = addVertex(a3, Vec3(-1, 0, 0), Vec2(a3.z, a3.y));
        u32 s2 = addVertex(t0, Vec3(-1, 0, 0), Vec2(t0.z, t0.y));
        addTri(s0, s1, s2);
        u32 e0 = addVertex(a1, Vec3(1, 0, 0), Vec2(a1.z, a1.y));
        u32 e1 = addVertex(a2, Vec3(1, 0, 0), Vec2(a2.z, a2.y));
        u32 e2 = addVertex(t1, Vec3(1, 0, 0), Vec2(t1.z, t1.y));
        addTri(e0, e2, e1);
    } else {
        addQuad(a0, a1, t1, t0, Vec3(0, 0, -1));
        u32 s0 = addVertex(a0, Vec3(-1, 0, 0), Vec2(a0.z, a0.y));
        u32 s1 = addVertex(t0, Vec3(-1, 0, 0), Vec2(t0.z, t0.y));
        u32 s2 = addVertex(a3, Vec3(-1, 0, 0), Vec2(a3.z, a3.y));
        addTri(s0, s1, s2);
        u32 e0 = addVertex(a1, Vec3(1, 0, 0), Vec2(a1.z, a1.y));
        u32 e1 = addVertex(a2, Vec3(1, 0, 0), Vec2(a2.z, a2.y));
        u32 e2 = addVertex(t1, Vec3(1, 0, 0), Vec2(t1.z, t1.y));
        addTri(e0, e1, e2);
    }
}

void MeshBuilder::finishSubMesh() {
    u32 count = (u32)inds.size() - pendingStart;
    if (count == 0) return;
    SubMesh s;
    s.indexOffset = pendingStart;
    s.indexCount = count;
    s.material = current;
    s.bounds = subAabb;
    subs.push_back(s);
    pendingStart = (u32)inds.size();
    subAabb = AABB();
}

void MeshBuilder::buildTangents() {
    std::vector<Vec3> tan(verts.size(), Vec3(0));
    std::vector<Vec3> bit(verts.size(), Vec3(0));
    for (size_t i = 0; i + 2 < inds.size(); i += 3) {
        u32 a = inds[i], b = inds[i + 1], c = inds[i + 2];
        if (a >= verts.size() || b >= verts.size() || c >= verts.size()) continue;
        const Vec3& p0 = verts[a].pos;
        const Vec3& p1 = verts[b].pos;
        const Vec3& p2 = verts[c].pos;
        const Vec2& w0 = verts[a].uv;
        const Vec2& w1 = verts[b].uv;
        const Vec2& w2 = verts[c].uv;
        Vec3 e1 = p1 - p0, e2 = p2 - p0;
        float x1 = w1.x - w0.x, x2 = w2.x - w0.x;
        float y1 = w1.y - w0.y, y2 = w2.y - w0.y;
        float det = x1 * y2 - x2 * y1;
        if (std::fabs(det) < 1e-12f) continue;
        float r = 1.0f / det;
        Vec3 t = (e1 * y2 - e2 * y1) * r;
        Vec3 b2 = (e2 * x1 - e1 * x2) * r;
        tan[a] += t; tan[b] += t; tan[c] += t;
        bit[a] += b2; bit[b] += b2; bit[c] += b2;
    }
    for (size_t i = 0; i < verts.size(); i++) {
        const Vec3& n = verts[i].normal;
        Vec3 t = tan[i];
        if (lengthSq(t) < 1e-12f) {
            t = std::fabs(n.y) > 0.9f ? Vec3(1, 0, 0) : normalize(cross(Vec3(0, 1, 0), n));
        }
        t = normalize(t - n * dot(n, t));
        float w = dot(cross(n, t), bit[i]) < 0.0f ? -1.0f : 1.0f;
        verts[i].tangent = Vec4(t, w);
    }
}

void MeshBuilder::build(Mesh& out) {
    finishSubMesh();
    buildTangents();
    out.upload(verts, inds, subs);
}

}
