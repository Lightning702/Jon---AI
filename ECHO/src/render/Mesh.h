#pragma once

#include "../platform/GL.h"
#include "../core/Math.h"

namespace echo {

struct Vertex {
    em::Vec3 pos;
    em::Vec3 normal;
    em::Vec4 tangent;
    em::Vec2 uv;
    u8 color[4] = { 255, 255, 255, 255 };
};

struct SubMesh {
    u32 indexOffset = 0;
    u32 indexCount = 0;
    int material = 0;
    em::AABB bounds;
};

class Mesh {
public:
    Mesh() {}
    ~Mesh() { destroy(); }
    Mesh(const Mesh&) = delete;
    Mesh& operator=(const Mesh&) = delete;

    void upload(const std::vector<Vertex>& verts, const std::vector<u32>& indices, const std::vector<SubMesh>& subs);
    void destroy();
    void bind() const;
    void draw() const;
    void drawSub(int index) const;
    void drawSubInstanced(int index, int count) const;

    const std::vector<SubMesh>& subMeshes() const { return subs; }
    const em::AABB& bounds() const { return aabb; }
    u32 indexCount() const { return totalIndices; }
    u32 vertexCount() const { return totalVertices; }
    bool valid() const { return vao != 0; }

    void setInstanceBuffer(GLuint buffer, int stride);

private:
    GLuint vao = 0, vbo = 0, ibo = 0;
    u32 totalIndices = 0, totalVertices = 0;
    std::vector<SubMesh> subs;
    em::AABB aabb;
};

class MeshBuilder {
public:
    void clear();
    void setMaterial(int m) { current = m; }
    int material() const { return current; }
    void setColor(const em::Vec4& c) { vcolor = c; }
    void setUVScale(const em::Vec2& s) { uvScale = s; }
    void setUVOffset(const em::Vec2& o) { uvOffset = o; }

    void pushTransform(const em::Mat4& m);
    void popTransform();
    const em::Mat4& transform() const { return xform; }

    void addQuad(const em::Vec3& a, const em::Vec3& b, const em::Vec3& c, const em::Vec3& d, const em::Vec3& n, bool planarUV = true);
    void addBox(const em::Vec3& center, const em::Vec3& half);
    void addBoxInner(const em::Vec3& center, const em::Vec3& half);
    void addBoxFaces(const em::Vec3& center, const em::Vec3& half, int faceMask);
    void addPlane(const em::Vec3& center, const em::Vec2& size, const em::Vec3& normal, int subdiv = 1);
    void addCylinder(const em::Vec3& base, float radius, float height, int segments, bool caps = true);
    void addCone(const em::Vec3& base, float r0, float r1, float height, int segments, bool caps = true);
    void addSphere(const em::Vec3& center, float radius, int rings, int segments);
    void addTorusArc(const em::Vec3& center, float major, float minor, float startAngle, float sweep, int seg, int sides);
    void addWedge(const em::Vec3& center, const em::Vec3& half, int axis);

    void finishSubMesh();
    void buildTangents();
    void build(Mesh& out);

    std::vector<Vertex>& vertices() { return verts; }
    std::vector<u32>& indices() { return inds; }
    const em::AABB& bounds() const { return aabb; }
    bool empty() const { return inds.empty() && pendingStart == 0; }

private:
    u32 addVertex(const em::Vec3& p, const em::Vec3& n, const em::Vec2& uv);
    void addTri(u32 a, u32 b, u32 c);

    std::vector<Vertex> verts;
    std::vector<u32> inds;
    std::vector<SubMesh> subs;
    std::vector<em::Mat4> stack;
    em::Mat4 xform;
    em::AABB aabb;
    em::AABB subAabb;
    em::Vec4 vcolor = em::Vec4(1, 1, 1, 1);
    em::Vec2 uvScale = em::Vec2(1, 1);
    em::Vec2 uvOffset = em::Vec2(0, 0);
    int current = 0;
    u32 pendingStart = 0;
};

}
