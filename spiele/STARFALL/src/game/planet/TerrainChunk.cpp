#include "TerrainChunk.hpp"

#include "../../engine/job/ParallelFor.hpp"
#include "../../engine/math/Scalar.hpp"
#include "../../engine/math/SphericalCoords.hpp"

namespace sf {

void generateTerrainGeometry(const PlanetBody& body, u32 face, f64 originU, f64 originV, f64 size, f64 dayPhase,
                             TerrainGeometry& out) {
    const u32 resolution = kTerrainGridResolution;
    const u32 vertexCount = resolution * resolution;

    out.vertices.clear();
    out.indices.clear();
    out.indices.reserve((resolution - 1) * (resolution - 1) * 6 + resolution * 24);
    (void)vertexCount;

    const DVec3 centerDirection = cubeFaceDirection(face, originU + size * 0.5, originV + size * 0.5);
    const DVec3 centerPoint = centerDirection * body.radiusAt(centerDirection);
    out.originLocalPosition = body.center() + centerPoint;

    const f64 amplitude = maxValue(body.terrainAmplitude(), 1.0);
    const bool hasWater = body.profile().waterFraction > 0.02;

    const u32 borderedResolution = resolution + 2;
    const f64 step = size / static_cast<f64>(resolution - 1);
    const f64 chunkWorldSize = size * body.seaLevelRadius() * 1.7;
    const u32 detailLevel = PlanetGenerator::detailLevelForChunkSize(chunkWorldSize);

    std::vector<DVec3> directions(static_cast<usize>(borderedResolution) * borderedResolution);
    std::vector<f64> radii(directions.size());
    std::vector<f64> elevations(directions.size());

    const PlanetBody* bodyPointer = &body;
    parallelFor(borderedResolution, 4, [&](usize row) {
        for (u32 column = 0; column < borderedResolution; ++column) {
            const f64 u = originU + step * (static_cast<f64>(column) - 1.0);
            const f64 v = originV + step * (static_cast<f64>(row) - 1.0);
            const usize index = row * borderedResolution + column;
            directions[index] = cubeFaceDirection(face, u, v);
            elevations[index] = bodyPointer->elevationAtDetail(directions[index], detailLevel);
            radii[index] = hasWater && elevations[index] < 0.0
                               ? bodyPointer->seaLevelRadius()
                               : bodyPointer->seaLevelRadius() + elevations[index];
        }
    });

    out.vertices.resize(static_cast<usize>(resolution) * resolution);
    std::vector<f64> rowMaxima(resolution, 0.0);

    parallelFor(resolution, 4, [&](usize row) {
        for (u32 column = 0; column < resolution; ++column) {
            const u32 borderedRow = static_cast<u32>(row) + 1;
            const u32 borderedColumn = column + 1;
            const usize index = static_cast<usize>(borderedRow) * borderedResolution + borderedColumn;
            const DVec3 direction = directions[index];
            const DVec3 point = direction * radii[index];
            const DVec3 relative = point - centerPoint;

            const usize left = index - 1;
            const usize right = index + 1;
            const usize above = index - borderedResolution;
            const usize below = index + borderedResolution;

            const DVec3 horizontal = directions[right] * radii[right] - directions[left] * radii[left];
            const DVec3 vertical = directions[below] * radii[below] - directions[above] * radii[above];
            DVec3 normalVector = cross(vertical, horizontal);
            const f64 normalLength = length(normalVector);
            normalVector = normalLength > 0.0 ? normalVector / normalLength : direction;
            if (dot(normalVector, direction) < 0.0) normalVector *= -1.0;

            const f64 slope = clampValue(1.0 - dot(normalVector, direction), 0.0, 1.0) * 6.0;
            const SurfaceSample sample =
                body.sampleSurfaceWithElevation(direction, dayPhase, elevations[index], slope);

            TerrainVertex vertex;
            vertex.position = relative.toFloat();
            vertex.normalVector = normalVector.toFloat();
            vertex.albedo = sample.albedo;
            vertex.elevationFraction = static_cast<f32>(clampValue(elevations[index] / amplitude, -1.0, 1.0));
            vertex.slope = static_cast<f32>(slope * 0.84);
            vertex.water = (hasWater && elevations[index] < 0.0) ? 1.0f : 0.0f;

            out.vertices[row * resolution + column] = vertex;
            rowMaxima[row] = maxValue(rowMaxima[row], length(relative));
        }
    });

    f64 maximumDistance = 0.0;
    for (f64 rowMaximum : rowMaxima) maximumDistance = maxValue(maximumDistance, rowMaximum);

    for (u32 row = 0; row + 1 < resolution; ++row) {
        for (u32 column = 0; column + 1 < resolution; ++column) {
            const u32 topLeft = row * resolution + column;
            const u32 topRight = topLeft + 1;
            const u32 bottomLeft = topLeft + resolution;
            const u32 bottomRight = bottomLeft + 1;
            out.indices.push_back(topLeft);
            out.indices.push_back(bottomLeft);
            out.indices.push_back(topRight);
            out.indices.push_back(topRight);
            out.indices.push_back(bottomLeft);
            out.indices.push_back(bottomRight);
        }
    }

    const f32 skirtDepth = static_cast<f32>(clampValue(size * body.seaLevelRadius() * 0.05, 6.0, 900.0));
    const u32 skirtBase = static_cast<u32>(out.vertices.size());
    std::vector<u32> edgeIndices;
    for (u32 column = 0; column < resolution; ++column) edgeIndices.push_back(column);
    for (u32 row = 1; row < resolution; ++row) edgeIndices.push_back(row * resolution + resolution - 1);
    for (u32 column = resolution - 1; column > 0; --column) edgeIndices.push_back((resolution - 1) * resolution + column - 1);
    for (u32 row = resolution - 1; row > 0; --row) edgeIndices.push_back((row - 1) * resolution);

    for (u32 edge : edgeIndices) {
        TerrainVertex vertex = out.vertices[edge];
        const DVec3 direction = directions[edge];
        vertex.position -= direction.toFloat() * skirtDepth;
        out.vertices.push_back(vertex);
    }

    const u32 edgeCount = static_cast<u32>(edgeIndices.size());
    for (u32 index = 0; index < edgeCount; ++index) {
        const u32 nextIndex = (index + 1) % edgeCount;
        const u32 topCurrent = edgeIndices[index];
        const u32 topNext = edgeIndices[nextIndex];
        const u32 bottomCurrent = skirtBase + index;
        const u32 bottomNext = skirtBase + nextIndex;
        out.indices.push_back(topCurrent);
        out.indices.push_back(bottomCurrent);
        out.indices.push_back(topNext);
        out.indices.push_back(topNext);
        out.indices.push_back(bottomCurrent);
        out.indices.push_back(bottomNext);
    }

    out.boundingRadius = maximumDistance + static_cast<f64>(skirtDepth);
    out.underWater = false;
}

TerrainChunk::~TerrainChunk() {
    release();
}

TerrainChunk::TerrainChunk(TerrainChunk&& other) noexcept
    : vertexArray(other.vertexArray), vertexBuffer(other.vertexBuffer), indexBuffer(other.indexBuffer),
      indexCount(other.indexCount), origin(other.origin), radius(other.radius) {
    other.vertexArray = 0;
    other.vertexBuffer = 0;
    other.indexBuffer = 0;
    other.indexCount = 0;
}

TerrainChunk& TerrainChunk::operator=(TerrainChunk&& other) noexcept {
    if (this != &other) {
        release();
        vertexArray = other.vertexArray;
        vertexBuffer = other.vertexBuffer;
        indexBuffer = other.indexBuffer;
        indexCount = other.indexCount;
        origin = other.origin;
        radius = other.radius;
        other.vertexArray = 0;
        other.vertexBuffer = 0;
        other.indexBuffer = 0;
        other.indexCount = 0;
    }
    return *this;
}

void TerrainChunk::upload(const TerrainGeometry& geometry) {
    GLApi& api = gl();
    if (vertexArray == 0) api.genVertexArrays(1, &vertexArray);
    if (vertexBuffer == 0) api.genBuffers(1, &vertexBuffer);
    if (indexBuffer == 0) api.genBuffers(1, &indexBuffer);

    api.bindVertexArray(vertexArray);
    api.bindBuffer(GL_ARRAY_BUFFER, vertexBuffer);
    api.bufferData(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(geometry.vertices.size() * sizeof(TerrainVertex)),
                   geometry.vertices.data(), GL_STATIC_DRAW);
    api.bindBuffer(GL_ELEMENT_ARRAY_BUFFER, indexBuffer);
    api.bufferData(GL_ELEMENT_ARRAY_BUFFER, static_cast<GLsizeiptr>(geometry.indices.size() * sizeof(u32)),
                   geometry.indices.data(), GL_STATIC_DRAW);

    const GLsizei stride = static_cast<GLsizei>(sizeof(TerrainVertex));
    api.enableVertexAttribArray(0);
    api.vertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, reinterpret_cast<const void*>(0));
    api.enableVertexAttribArray(1);
    api.vertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, reinterpret_cast<const void*>(sizeof(f32) * 3));
    api.enableVertexAttribArray(2);
    api.vertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, stride, reinterpret_cast<const void*>(sizeof(f32) * 6));
    api.enableVertexAttribArray(3);
    api.vertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, stride, reinterpret_cast<const void*>(sizeof(f32) * 9));
    api.enableVertexAttribArray(4);
    api.vertexAttribPointer(4, 1, GL_FLOAT, GL_FALSE, stride, reinterpret_cast<const void*>(sizeof(f32) * 10));
    api.enableVertexAttribArray(5);
    api.vertexAttribPointer(5, 1, GL_FLOAT, GL_FALSE, stride, reinterpret_cast<const void*>(sizeof(f32) * 11));
    api.bindVertexArray(0);

    indexCount = static_cast<u32>(geometry.indices.size());
    origin = geometry.originLocalPosition;
    radius = geometry.boundingRadius;
}

void TerrainChunk::release() {
    GLApi& api = gl();
    if (indexBuffer != 0) api.deleteBuffers(1, &indexBuffer);
    if (vertexBuffer != 0) api.deleteBuffers(1, &vertexBuffer);
    if (vertexArray != 0) api.deleteVertexArrays(1, &vertexArray);
    indexBuffer = 0;
    vertexBuffer = 0;
    vertexArray = 0;
    indexCount = 0;
}

void TerrainChunk::draw() const {
    if (vertexArray == 0 || indexCount == 0) return;
    GLApi& api = gl();
    api.bindVertexArray(vertexArray);
    glDrawElements(GL_TRIANGLES, static_cast<GLsizei>(indexCount), GL_UNSIGNED_INT, nullptr);
    api.bindVertexArray(0);
}

}
