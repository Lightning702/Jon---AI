#include "Mesh.hpp"

#include "../math/Scalar.hpp"

#include <map>

namespace sf {

Mesh::~Mesh() {
    release();
}

void Mesh::upload(const std::vector<MeshVertex>& vertices, const std::vector<u32>& indexData) {
    GLApi& api = gl();
    if (vertexArray == 0) api.genVertexArrays(1, &vertexArray);
    if (vertexBuffer == 0) api.genBuffers(1, &vertexBuffer);
    if (indexBuffer == 0) api.genBuffers(1, &indexBuffer);

    api.bindVertexArray(vertexArray);
    api.bindBuffer(GL_ARRAY_BUFFER, vertexBuffer);
    api.bufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(vertices.size() * sizeof(MeshVertex)), vertices.data(),
                   GL_STATIC_DRAW);
    api.bindBuffer(GL_ELEMENT_ARRAY_BUFFER, indexBuffer);
    api.bufferData(GL_ELEMENT_ARRAY_BUFFER, static_cast<GLsizeiptr>(indexData.size() * sizeof(u32)), indexData.data(),
                   GL_STATIC_DRAW);

    api.enableVertexAttribArray(0);
    api.vertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(MeshVertex), reinterpret_cast<const void*>(0));
    api.enableVertexAttribArray(1);
    api.vertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(MeshVertex), reinterpret_cast<const void*>(sizeof(Vec3)));
    api.enableVertexAttribArray(2);
    api.vertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, sizeof(MeshVertex),
                            reinterpret_cast<const void*>(sizeof(Vec3) * 2));

    api.bindVertexArray(0);
    indices = static_cast<u32>(indexData.size());
    vertexCapacity = static_cast<u32>(vertices.size());
}

void Mesh::updateVertices(const std::vector<MeshVertex>& vertices) {
    if (vertexBuffer == 0) return;
    GLApi& api = gl();
    api.bindBuffer(GL_ARRAY_BUFFER, vertexBuffer);
    if (vertices.size() > vertexCapacity) {
        api.bufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(vertices.size() * sizeof(MeshVertex)), vertices.data(),
                       GL_DYNAMIC_DRAW);
        vertexCapacity = static_cast<u32>(vertices.size());
    } else {
        api.bufferSubData(GL_ARRAY_BUFFER, 0, static_cast<GLsizeiptr>(vertices.size() * sizeof(MeshVertex)),
                          vertices.data());
    }
}

void Mesh::release() {
    GLApi& api = gl();
    if (indexBuffer != 0) api.deleteBuffers(1, &indexBuffer);
    if (vertexBuffer != 0) api.deleteBuffers(1, &vertexBuffer);
    if (vertexArray != 0) api.deleteVertexArrays(1, &vertexArray);
    indexBuffer = 0;
    vertexBuffer = 0;
    vertexArray = 0;
    indices = 0;
    vertexCapacity = 0;
}

void Mesh::draw() const {
    if (vertexArray == 0 || indices == 0) return;
    GLApi& api = gl();
    api.bindVertexArray(vertexArray);
    glDrawElements(GL_TRIANGLES, static_cast<GLsizei>(indices), GL_UNSIGNED_INT, nullptr);
    api.bindVertexArray(0);
}

void Mesh::drawInstanced(u32 instanceCount) const {
    if (vertexArray == 0 || indices == 0 || instanceCount == 0) return;
    GLApi& api = gl();
    api.bindVertexArray(vertexArray);
    if (api.drawElementsInstanced) {
        api.drawElementsInstanced(GL_TRIANGLES, static_cast<GLsizei>(indices), GL_UNSIGNED_INT, nullptr,
                                  static_cast<GLsizei>(instanceCount));
    }
    api.bindVertexArray(0);
}

namespace {

u32 midpointVertex(std::vector<MeshVertex>& vertices, std::map<u64, u32>& cache, u32 a, u32 b) {
    const u64 key = a < b ? (static_cast<u64>(a) << 32) | b : (static_cast<u64>(b) << 32) | a;
    auto found = cache.find(key);
    if (found != cache.end()) return found->second;
    const Vec3 midpoint = normalize((vertices[a].position + vertices[b].position) * 0.5f);
    MeshVertex vertex;
    vertex.position = midpoint;
    vertex.normalVector = midpoint;
    vertices.push_back(vertex);
    const u32 index = static_cast<u32>(vertices.size() - 1);
    cache.emplace(key, index);
    return index;
}

}

void buildIcoSphere(u32 subdivisions, std::vector<MeshVertex>& vertices, std::vector<u32>& indices) {
    vertices.clear();
    indices.clear();

    const f32 goldenRatio = (1.0f + std::sqrt(5.0f)) * 0.5f;
    const Vec3 basePositions[12] = {
        Vec3(-1.0f, goldenRatio, 0.0f), Vec3(1.0f, goldenRatio, 0.0f),
        Vec3(-1.0f, -goldenRatio, 0.0f), Vec3(1.0f, -goldenRatio, 0.0f),
        Vec3(0.0f, -1.0f, goldenRatio), Vec3(0.0f, 1.0f, goldenRatio),
        Vec3(0.0f, -1.0f, -goldenRatio), Vec3(0.0f, 1.0f, -goldenRatio),
        Vec3(goldenRatio, 0.0f, -1.0f), Vec3(goldenRatio, 0.0f, 1.0f),
        Vec3(-goldenRatio, 0.0f, -1.0f), Vec3(-goldenRatio, 0.0f, 1.0f)};

    for (const Vec3& position : basePositions) {
        MeshVertex vertex;
        vertex.position = normalize(position);
        vertex.normalVector = vertex.position;
        vertices.push_back(vertex);
    }

    const u32 baseIndices[60] = {0, 11, 5, 0, 5, 1, 0, 1, 7, 0, 7, 10, 0, 10, 11,
                                 1, 5, 9, 5, 11, 4, 11, 10, 2, 10, 7, 6, 7, 1, 8,
                                 3, 9, 4, 3, 4, 2, 3, 2, 6, 3, 6, 8, 3, 8, 9,
                                 4, 9, 5, 2, 4, 11, 6, 2, 10, 8, 6, 7, 9, 8, 1};
    indices.assign(baseIndices, baseIndices + 60);

    for (u32 level = 0; level < subdivisions; ++level) {
        std::map<u64, u32> cache;
        std::vector<u32> refined;
        refined.reserve(indices.size() * 4);
        for (usize triangle = 0; triangle < indices.size(); triangle += 3) {
            const u32 a = indices[triangle];
            const u32 b = indices[triangle + 1];
            const u32 c = indices[triangle + 2];
            const u32 ab = midpointVertex(vertices, cache, a, b);
            const u32 bc = midpointVertex(vertices, cache, b, c);
            const u32 ca = midpointVertex(vertices, cache, c, a);
            const u32 expanded[12] = {a, ab, ca, b, bc, ab, c, ca, bc, ab, bc, ca};
            refined.insert(refined.end(), expanded, expanded + 12);
        }
        indices.swap(refined);
    }

    for (MeshVertex& vertex : vertices) {
        vertex.texcoordU = 0.5f + std::atan2(vertex.position.z, vertex.position.x) / kTwoPi;
        vertex.texcoordV = 0.5f - std::asin(clampValue(vertex.position.y, -1.0f, 1.0f)) / kPi;
    }
}

void buildUvSphere(u32 rings, u32 segments, std::vector<MeshVertex>& vertices, std::vector<u32>& indices) {
    vertices.clear();
    indices.clear();
    for (u32 ring = 0; ring <= rings; ++ring) {
        const f32 v = static_cast<f32>(ring) / static_cast<f32>(rings);
        const f32 polar = v * kPi;
        for (u32 segment = 0; segment <= segments; ++segment) {
            const f32 u = static_cast<f32>(segment) / static_cast<f32>(segments);
            const f32 azimuth = u * kTwoPi;
            MeshVertex vertex;
            vertex.position = Vec3(std::sin(polar) * std::cos(azimuth), std::cos(polar),
                                   std::sin(polar) * std::sin(azimuth));
            vertex.normalVector = vertex.position;
            vertex.texcoordU = u;
            vertex.texcoordV = v;
            vertices.push_back(vertex);
        }
    }
    for (u32 ring = 0; ring < rings; ++ring) {
        for (u32 segment = 0; segment < segments; ++segment) {
            const u32 current = ring * (segments + 1) + segment;
            const u32 next = current + segments + 1;
            indices.push_back(current);
            indices.push_back(next);
            indices.push_back(current + 1);
            indices.push_back(current + 1);
            indices.push_back(next);
            indices.push_back(next + 1);
        }
    }
}

void buildBox(const Vec3& halfExtent, std::vector<MeshVertex>& vertices, std::vector<u32>& indices) {
    vertices.clear();
    indices.clear();
    const Vec3 faceNormals[6] = {Vec3(0.0f, 0.0f, 1.0f),  Vec3(0.0f, 0.0f, -1.0f), Vec3(1.0f, 0.0f, 0.0f),
                                 Vec3(-1.0f, 0.0f, 0.0f), Vec3(0.0f, 1.0f, 0.0f),  Vec3(0.0f, -1.0f, 0.0f)};
    for (u32 face = 0; face < 6; ++face) {
        const Vec3 normalVector = faceNormals[face];
        const Vec3 tangent = perpendicular(normalVector);
        const Vec3 bitangent = cross(normalVector, tangent);
        const u32 baseIndex = static_cast<u32>(vertices.size());
        for (u32 corner = 0; corner < 4; ++corner) {
            const f32 signU = (corner == 0 || corner == 3) ? -1.0f : 1.0f;
            const f32 signV = (corner < 2) ? -1.0f : 1.0f;
            MeshVertex vertex;
            vertex.position = (normalVector + tangent * signU + bitangent * signV) * halfExtent;
            vertex.normalVector = normalVector;
            vertex.texcoordU = signU * 0.5f + 0.5f;
            vertex.texcoordV = signV * 0.5f + 0.5f;
            vertices.push_back(vertex);
        }
        const u32 order[6] = {baseIndex, baseIndex + 1, baseIndex + 2, baseIndex, baseIndex + 2, baseIndex + 3};
        indices.insert(indices.end(), order, order + 6);
    }
}

void buildRing(f32 innerRadius, f32 outerRadius, u32 segments, std::vector<MeshVertex>& vertices,
               std::vector<u32>& indices) {
    vertices.clear();
    indices.clear();
    for (u32 segment = 0; segment <= segments; ++segment) {
        const f32 angle = static_cast<f32>(segment) / static_cast<f32>(segments) * kTwoPi;
        const f32 cosine = std::cos(angle);
        const f32 sine = std::sin(angle);
        MeshVertex inner;
        inner.position = Vec3(cosine * innerRadius, 0.0f, sine * innerRadius);
        inner.normalVector = Vec3(0.0f, 1.0f, 0.0f);
        inner.texcoordU = static_cast<f32>(segment) / static_cast<f32>(segments);
        inner.texcoordV = 0.0f;
        MeshVertex outer;
        outer.position = Vec3(cosine * outerRadius, 0.0f, sine * outerRadius);
        outer.normalVector = Vec3(0.0f, 1.0f, 0.0f);
        outer.texcoordU = inner.texcoordU;
        outer.texcoordV = 1.0f;
        vertices.push_back(inner);
        vertices.push_back(outer);
    }
    for (u32 segment = 0; segment < segments; ++segment) {
        const u32 base = segment * 2;
        indices.push_back(base);
        indices.push_back(base + 1);
        indices.push_back(base + 2);
        indices.push_back(base + 2);
        indices.push_back(base + 1);
        indices.push_back(base + 3);
    }
}

void FullscreenTriangle::initialize() {
    if (vertexArray != 0) return;
    gl().genVertexArrays(1, &vertexArray);
}

void FullscreenTriangle::release() {
    if (vertexArray == 0) return;
    gl().deleteVertexArrays(1, &vertexArray);
    vertexArray = 0;
}

void FullscreenTriangle::draw() const {
    if (vertexArray == 0) return;
    GLApi& api = gl();
    api.bindVertexArray(vertexArray);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    api.bindVertexArray(0);
}

}
