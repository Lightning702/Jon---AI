#pragma once

#include "../math/Vec3.hpp"
#include "GLApi.hpp"

#include <vector>

namespace sf {

struct MeshVertex {
    Vec3 position;
    Vec3 normalVector;
    f32 texcoordU = 0.0f;
    f32 texcoordV = 0.0f;
};

class Mesh {
public:
    Mesh() = default;
    ~Mesh();

    Mesh(const Mesh&) = delete;
    Mesh& operator=(const Mesh&) = delete;

    void upload(const std::vector<MeshVertex>& vertices, const std::vector<u32>& indices);
    void updateVertices(const std::vector<MeshVertex>& vertices);
    void release();
    void draw() const;
    void drawInstanced(u32 instanceCount) const;

    u32 indexCount() const { return indices; }
    bool valid() const { return vertexArray != 0; }

private:
    GLuint vertexArray = 0;
    GLuint vertexBuffer = 0;
    GLuint indexBuffer = 0;
    u32 indices = 0;
    u32 vertexCapacity = 0;
};

void buildIcoSphere(u32 subdivisions, std::vector<MeshVertex>& vertices, std::vector<u32>& indices);
void buildUvSphere(u32 rings, u32 segments, std::vector<MeshVertex>& vertices, std::vector<u32>& indices);
void buildBox(const Vec3& halfExtent, std::vector<MeshVertex>& vertices, std::vector<u32>& indices);
void buildRing(f32 innerRadius, f32 outerRadius, u32 segments, std::vector<MeshVertex>& vertices,
               std::vector<u32>& indices);

class FullscreenTriangle {
public:
    void initialize();
    void release();
    void draw() const;

private:
    GLuint vertexArray = 0;
};

}
