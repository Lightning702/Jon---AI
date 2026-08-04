#include "TerrainPass.hpp"

#include "../core/Log.hpp"
#include "../math/Scalar.hpp"
#include "../math/Transform.hpp"
#include "../../game/planet/TerrainChunk.hpp"
#include "SkyCommon.hpp"

#include <string>

namespace sf {
namespace {

const char* const kTerrainVertexSource = R"GLSL(#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec3 aAlbedo;
layout(location = 3) in float aElevation;
layout(location = 4) in float aSlope;
layout(location = 5) in float aWater;

uniform mat4 uViewProjection;
uniform vec3 uChunkOrigin;

out vec3 vWorldPosition;
out vec3 vNormal;
out vec3 vAlbedo;
out float vElevation;
out float vSlope;
out float vWater;

void main() {
    vec3 world = aPosition + uChunkOrigin;
    vWorldPosition = world;
    vNormal = normalize(aNormal);
    vAlbedo = aAlbedo;
    vElevation = aElevation;
    vSlope = aSlope;
    vWater = aWater;
    gl_Position = uViewProjection * vec4(world, 1.0);
}
)GLSL";

const char* const kTerrainFragmentBody = R"GLSL(
in vec3 vWorldPosition;
in vec3 vNormal;
in vec3 vAlbedo;
in float vElevation;
in float vSlope;
in float vWater;
out vec4 fragColor;

uniform vec3 uCameraPosition;
uniform vec3 uStarDirection;
uniform vec3 uStarColor;
uniform float uStarIntensity;
uniform vec3 uAmbientColor;
uniform vec3 uPlanetCenter;
uniform vec3 uWaterColor;
uniform vec3 uFogColor;
uniform float uFogDensity;
uniform float uDetailStrength;
uniform float uTime;
uniform float uWaterEnabled;

void main() {
    vec3 normalVector = normalize(vNormal);
    vec3 viewVector = uCameraPosition - vWorldPosition;
    float viewDistance = length(viewVector);
    viewVector /= max(viewDistance, 1.0e-4);

    vec3 up = normalize(vWorldPosition - uPlanetCenter);
    float detailNoise = skyFractal(vWorldPosition * 0.09, 3);
    float grain = skyFractal(vWorldPosition * 1.1, 2);

    vec3 albedo = vAlbedo;
    float rockMask = clamp(vSlope * 1.4, 0.0, 1.0);
    vec3 rockColor = mix(albedo * 0.55, vec3(0.32, 0.30, 0.28), 0.45);
    albedo = mix(albedo, rockColor, rockMask);
    albedo *= 0.80 + detailNoise * 0.40 * uDetailStrength;
    albedo *= 0.92 + grain * 0.16 * uDetailStrength;

    float roughness = mix(0.92, 0.42, clamp(vWater * uWaterEnabled, 0.0, 1.0));
    if (vWater > 0.5 && uWaterEnabled > 0.5) {
        float ripple = sin(vWorldPosition.x * 0.35 + uTime * 1.4) * sin(vWorldPosition.z * 0.31 - uTime * 1.1);
        albedo = mix(uWaterColor, uWaterColor * 1.6, 0.5 + 0.5 * ripple);
        normalVector = normalize(normalVector + up * 0.0 + vec3(ripple * 0.02, 0.0, ripple * 0.02));
    }

    vec3 lightVector = normalize(-uStarDirection);
    float normalDotLight = max(dot(normalVector, lightVector), 0.0);
    float wrapped = clamp((dot(normalVector, lightVector) + 0.28) / 1.28, 0.0, 1.0);

    vec3 halfVector = normalize(viewVector + lightVector);
    float specularPower = mix(12.0, 128.0, 1.0 - roughness);
    float specular = pow(max(dot(normalVector, halfVector), 0.0), specularPower) * (1.0 - roughness) * 0.5;

    vec3 radiance = uStarColor * uStarIntensity;
    vec3 color = albedo * radiance * (normalDotLight * 0.82 + wrapped * 0.18);
    color += radiance * specular;
    color += albedo * uAmbientColor;
    color += albedo * uStarColor * 0.06 * max(dot(normalVector, up), 0.0);

    if (uFogDensity > 0.0) {
        float fog = 1.0 - exp(-viewDistance * uFogDensity);
        color = mix(color, uFogColor * (0.35 + 0.65 * max(dot(up, lightVector), 0.0)), clamp(fog, 0.0, 0.92));
    }

    fragColor = vec4(color, 1.0);
}
)GLSL";

const char* const kScatterVertexSource = R"GLSL(#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexcoord;

uniform mat4 uViewProjection;
uniform mat4 uModel;
uniform mat4 uNormalRotation;

out vec3 vWorldPosition;
out vec3 vNormal;
out float vHeightFraction;

void main() {
    vec4 world = uModel * vec4(aPosition, 1.0);
    vWorldPosition = world.xyz;
    vNormal = normalize((uNormalRotation * vec4(aNormal, 0.0)).xyz);
    vHeightFraction = clamp(aPosition.y * 0.5 + 0.5, 0.0, 1.0);
    gl_Position = uViewProjection * world;
}
)GLSL";

const char* const kScatterFragmentBody = R"GLSL(
in vec3 vWorldPosition;
in vec3 vNormal;
in float vHeightFraction;
out vec4 fragColor;

uniform vec3 uCameraPosition;
uniform vec3 uStarDirection;
uniform vec3 uStarColor;
uniform float uStarIntensity;
uniform vec3 uAmbientColor;
uniform vec3 uTint;
uniform vec3 uFogColor;
uniform float uFogDensity;

void main() {
    vec3 normalVector = normalize(vNormal);
    vec3 lightVector = normalize(-uStarDirection);
    float wrapped = clamp((dot(normalVector, lightVector) + 0.42) / 1.42, 0.0, 1.0);
    float subsurface = pow(1.0 - abs(dot(normalVector, lightVector)), 2.0) * 0.32;

    vec3 albedo = uTint * mix(0.62, 1.15, vHeightFraction);
    vec3 color = albedo * uStarColor * uStarIntensity * (wrapped + subsurface);
    color += albedo * uAmbientColor;

    float viewDistance = length(uCameraPosition - vWorldPosition);
    if (uFogDensity > 0.0) {
        float fog = 1.0 - exp(-viewDistance * uFogDensity);
        color = mix(color, uFogColor, clamp(fog, 0.0, 0.92));
    }
    fragColor = vec4(color, 1.0);
}
)GLSL";

std::string composeFragment(const char* body) {
    std::string source = "#version 330 core\n";
    source += kColorCommonSource;
    source += kSkyCommonSource;
    source += body;
    return source;
}

void buildCone(f32 radius, f32 height, u32 segments, std::vector<MeshVertex>& vertices, std::vector<u32>& indices) {
    vertices.clear();
    indices.clear();
    MeshVertex apex;
    apex.position = Vec3(0.0f, height, 0.0f);
    apex.normalVector = Vec3(0.0f, 1.0f, 0.0f);
    vertices.push_back(apex);

    for (u32 index = 0; index <= segments; ++index) {
        const f32 angle = static_cast<f32>(index) / static_cast<f32>(segments) * kTwoPi;
        MeshVertex vertex;
        vertex.position = Vec3(std::cos(angle) * radius, 0.0f, std::sin(angle) * radius);
        vertex.normalVector = normalize(Vec3(std::cos(angle), 0.42f, std::sin(angle)));
        vertex.texcoordU = static_cast<f32>(index) / static_cast<f32>(segments);
        vertices.push_back(vertex);
    }
    for (u32 index = 1; index <= segments; ++index) {
        indices.push_back(0);
        indices.push_back(index);
        indices.push_back(index + 1);
    }
}

}

Status TerrainPass::initialize() {
    Status status = terrainShader.compile("Terrain", kTerrainVertexSource, composeFragment(kTerrainFragmentBody).c_str());
    if (!status.ok()) return status;
    status = scatterShader.compile("Scatter", kScatterVertexSource, composeFragment(kScatterFragmentBody).c_str());
    if (!status.ok()) return status;

    std::vector<MeshVertex> vertices;
    std::vector<u32> indices;
    buildCone(0.42f, 1.0f, 7, vertices, indices);
    coneMesh.upload(vertices, indices);
    buildBox(Vec3(0.35f, 0.6f, 0.35f), vertices, indices);
    blockMesh.upload(vertices, indices);

    logInfo("render", "Terrain-Pass bereit");
    return statusOk();
}

void TerrainPass::release() {
    terrainShader.release();
    scatterShader.release();
    coneMesh.release();
    blockMesh.release();
}

void TerrainPass::renderChunks(const Camera& camera, const std::vector<const TerrainChunk*>& chunks,
                               const TerrainRenderParameters& parameters, const CelestialLighting& lighting) {
    if (!terrainShader.valid() || chunks.empty()) return;

    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);
    glDepthMask(GL_TRUE);
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);
    glDisable(GL_BLEND);

    terrainShader.bind();
    terrainShader.setMat4("uViewProjection", camera.viewProjectionMatrix());
    terrainShader.setVec3("uCameraPosition", camera.relativePosition());
    terrainShader.setVec3("uStarDirection", lighting.starDirection);
    terrainShader.setVec3("uStarColor", lighting.starColor);
    terrainShader.setFloat("uStarIntensity", lighting.starIntensity);
    terrainShader.setVec3("uAmbientColor", lighting.ambientColor);
    terrainShader.setVec3("uPlanetCenter", (parameters.planetCenter - camera.origin()).toFloat());
    terrainShader.setVec3("uWaterColor", parameters.waterColor);
    terrainShader.setVec3("uFogColor", parameters.fogColor);
    terrainShader.setFloat("uFogDensity", parameters.fogDensity);
    terrainShader.setFloat("uDetailStrength", parameters.detailStrength);
    terrainShader.setFloat("uTime", parameters.elapsedSeconds);
    terrainShader.setFloat("uWaterEnabled", parameters.waterEnabled ? 1.0f : 0.0f);

    for (const TerrainChunk* chunk : chunks) {
        if (!chunk || !chunk->valid()) continue;
        const Vec3 origin = (chunk->originLocalPosition() - camera.origin()).toFloat();
        terrainShader.setVec3("uChunkOrigin", origin);
        chunk->draw();
    }
}

void TerrainPass::renderScatter(const Camera& camera, const std::vector<ScatterRenderItem>& items,
                                const TerrainRenderParameters& parameters, const CelestialLighting& lighting) {
    if (!scatterShader.valid() || items.empty()) return;

    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);
    glDepthMask(GL_TRUE);
    glDisable(GL_CULL_FACE);
    glDisable(GL_BLEND);

    scatterShader.bind();
    scatterShader.setMat4("uViewProjection", camera.viewProjectionMatrix());
    scatterShader.setVec3("uCameraPosition", camera.relativePosition());
    scatterShader.setVec3("uStarDirection", lighting.starDirection);
    scatterShader.setVec3("uStarColor", lighting.starColor);
    scatterShader.setFloat("uStarIntensity", lighting.starIntensity);
    scatterShader.setVec3("uAmbientColor", lighting.ambientColor);
    scatterShader.setVec3("uFogColor", parameters.fogColor);
    scatterShader.setFloat("uFogDensity", parameters.fogDensity);

    for (const ScatterRenderItem& item : items) {
        const Vec3 up = normalize(item.upDirection);
        const Vec3 reference = std::fabs(up.y) < 0.9f ? Vec3::unitY() : Vec3::unitX();
        const Vec3 right = normalize(cross(reference, up));
        const Vec3 forward = cross(up, right);

        Mat3 basis = Mat3::fromColumns(right, up, forward);
        Transform transform;
        transform.position = item.relativePosition;
        transform.rotation = Quat::fromBasis(right, up, forward * -1.0f) *
                             Quat::fromAxisAngle(Vec3::unitY(), item.rotation);
        transform.scale = Vec3(item.scale);
        (void)basis;

        scatterShader.setMat4("uModel", transform.toMatrix());
        scatterShader.setMat4("uNormalRotation", Mat4::fromMat3(transform.rotation.toMat3()));
        scatterShader.setVec3("uTint", item.tint);
        if (item.kind == 2) blockMesh.draw();
        else coneMesh.draw();
    }

    glEnable(GL_CULL_FACE);
}

}
