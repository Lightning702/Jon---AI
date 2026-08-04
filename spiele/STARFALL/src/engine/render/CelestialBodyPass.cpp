#include "CelestialBodyPass.hpp"

#include "../core/Log.hpp"
#include "../math/Scalar.hpp"
#include "../math/Transform.hpp"
#include "SkyCommon.hpp"

#include <string>

namespace sf {
namespace {

const char* const kBodyVertexSource = R"GLSL(#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexcoord;

uniform mat4 uViewProjection;
uniform mat4 uModel;
uniform mat4 uNormalRotation;

out vec3 vWorldPosition;
out vec3 vNormal;
out vec3 vObjectDirection;

void main() {
    vec4 world = uModel * vec4(aPosition, 1.0);
    vWorldPosition = world.xyz;
    vNormal = normalize((uNormalRotation * vec4(aNormal, 0.0)).xyz);
    vObjectDirection = normalize(aPosition);
    gl_Position = uViewProjection * world;
}
)GLSL";

const char* const kSurfaceFragmentBody = R"GLSL(
in vec3 vWorldPosition;
in vec3 vNormal;
in vec3 vObjectDirection;
out vec4 fragColor;

uniform vec3 uCameraPosition;
uniform vec3 uStarDirection;
uniform vec3 uStarColor;
uniform float uStarIntensity;
uniform vec3 uAmbientColor;
uniform vec3 uSecondaryDirection;
uniform vec3 uSecondaryColor;
uniform vec3 uPrimaryColor;
uniform vec3 uSecondaryTint;
uniform float uRoughness;
uniform float uMetallic;
uniform float uEmissive;
uniform float uSurfaceDetail;
uniform float uCloudCoverage;
uniform float uIceCoverage;
uniform float uNightLights;
uniform float uSeedOffset;
uniform float uTime;
uniform int uSurfaceType;

float distributionGgx(float normalDotHalf, float roughness) {
    float alpha = roughness * roughness;
    float alphaSquared = alpha * alpha;
    float denominator = normalDotHalf * normalDotHalf * (alphaSquared - 1.0) + 1.0;
    return alphaSquared / max(3.14159265 * denominator * denominator, 1.0e-6);
}

float geometrySchlick(float normalDotVector, float roughness) {
    float k = (roughness + 1.0) * (roughness + 1.0) / 8.0;
    return normalDotVector / max(normalDotVector * (1.0 - k) + k, 1.0e-6);
}

vec3 fresnelSchlick(float cosineTheta, vec3 baseReflectance) {
    return baseReflectance + (1.0 - baseReflectance) * pow(clamp(1.0 - cosineTheta, 0.0, 1.0), 5.0);
}

float terrainHeight(vec3 direction) {
    vec3 warped = direction * 3.4 + uSeedOffset;
    float continents = skyFractal(warped, 5) * 2.0 - 1.0;
    float mountains = skyFractal(warped * 5.1 + 17.0, 5);
    float ridged = 1.0 - abs(mountains * 2.0 - 1.0);
    return continents * 0.7 + ridged * ridged * 0.5 * uSurfaceDetail;
}

vec3 surfaceAlbedo(vec3 direction, out float shininess) {
    float height = terrainHeight(direction);
    float latitude = abs(direction.y);
    float polarBand = smoothstep(0.62 - uIceCoverage * 0.42, 0.86 - uIceCoverage * 0.42, latitude);
    shininess = 0.0;

    vec3 lowland = uPrimaryColor;
    vec3 highland = uSecondaryTint;
    vec3 albedo = mix(lowland, highland, clamp(height * 0.75 + 0.35, 0.0, 1.0));

    if (uSurfaceType == 1) {
        float waterMask = smoothstep(0.06, -0.10, height);
        vec3 deepWater = vec3(0.012, 0.048, 0.105);
        vec3 shallowWater = vec3(0.05, 0.20, 0.30);
        vec3 water = mix(deepWater, shallowWater, smoothstep(-0.32, 0.05, height));
        albedo = mix(albedo, water, waterMask);
        shininess = waterMask;
    } else if (uSurfaceType == 4) {
        float lavaVeins = smoothstep(0.52, 0.86, skyFractal(direction * 9.0 + uSeedOffset + uTime * 0.02, 4));
        albedo = mix(albedo, vec3(2.4, 0.62, 0.10), lavaVeins);
    } else if (uSurfaceType == 5) {
        float bands = 0.5 + 0.5 * sin(direction.y * 22.0 + skyFractal(direction * 3.0 + uSeedOffset, 4) * 6.0);
        float storms = smoothstep(0.66, 0.92, skyFractal(direction * 6.0 + 41.0, 4));
        albedo = mix(uPrimaryColor, uSecondaryTint, bands);
        albedo = mix(albedo, vec3(0.92, 0.74, 0.55), storms * 0.55);
    } else if (uSurfaceType == 8) {
        float facets = skyFractal(direction * 16.0 + uSeedOffset, 3);
        albedo = mix(uPrimaryColor, uSecondaryTint, step(0.5, facets));
        shininess = 0.75;
    }

    vec3 ice = vec3(0.86, 0.91, 0.97);
    albedo = mix(albedo, ice, polarBand * clamp(uIceCoverage + 0.35, 0.0, 1.0));
    shininess = max(shininess, polarBand * 0.45);
    return albedo;
}

vec3 perturbedNormal(vec3 baseNormal, vec3 direction) {
    float epsilon = 0.0035;
    vec3 tangent = normalize(cross(abs(direction.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0), direction));
    vec3 bitangent = cross(direction, tangent);
    float center = terrainHeight(direction);
    float alongTangent = terrainHeight(normalize(direction + tangent * epsilon));
    float alongBitangent = terrainHeight(normalize(direction + bitangent * epsilon));
    vec3 gradient = (tangent * (alongTangent - center) + bitangent * (alongBitangent - center)) / epsilon;
    return normalize(baseNormal - gradient * 0.045 * uSurfaceDetail);
}

void main() {
    vec3 viewVector = normalize(uCameraPosition - vWorldPosition);
    vec3 lightVector = normalize(-uStarDirection);
    vec3 objectDirection = normalize(vObjectDirection);

    if (uSurfaceType == 6) {
        float limb = pow(clamp(dot(normalize(vNormal), viewVector), 0.0, 1.0), 0.42);
        float granulation = 0.86 + 0.14 * skyFractal(objectDirection * 26.0 + uTime * 0.05, 3);
        fragColor = vec4(uPrimaryColor * uEmissive * limb * granulation, 1.0);
        return;
    }

    float shininess = 0.0;
    vec3 albedo = surfaceAlbedo(objectDirection, shininess);
    vec3 normalVector = perturbedNormal(normalize(vNormal), objectDirection);

    float cloudMask = 0.0;
    if (uCloudCoverage > 0.001) {
        vec3 cloudDirection = objectDirection * 4.6 + vec3(uTime * 0.0045, 0.0, uSeedOffset);
        float cloudNoise = skyFractal(cloudDirection, 5);
        cloudMask = smoothstep(0.62 - uCloudCoverage * 0.42, 0.82 - uCloudCoverage * 0.30, cloudNoise);
        albedo = mix(albedo, vec3(0.92, 0.93, 0.95), cloudMask * 0.85);
        shininess *= 1.0 - cloudMask;
    }

    float roughness = clamp(mix(uRoughness, 0.10, shininess), 0.04, 1.0);
    vec3 baseReflectance = mix(vec3(0.04), albedo, uMetallic);

    vec3 halfVector = normalize(viewVector + lightVector);
    float normalDotLight = max(dot(normalVector, lightVector), 0.0);
    float normalDotView = max(dot(normalVector, viewVector), 1.0e-4);
    float normalDotHalf = max(dot(normalVector, halfVector), 0.0);

    float distribution = distributionGgx(normalDotHalf, roughness);
    float geometry = geometrySchlick(normalDotView, roughness) * geometrySchlick(normalDotLight, roughness);
    vec3 fresnel = fresnelSchlick(max(dot(halfVector, viewVector), 0.0), baseReflectance);
    vec3 specular = (distribution * geometry * fresnel) / max(4.0 * normalDotView * normalDotLight, 1.0e-4);
    vec3 diffuse = (vec3(1.0) - fresnel) * (1.0 - uMetallic) * albedo / 3.14159265;

    vec3 radiance = uStarColor * uStarIntensity;
    vec3 color = (diffuse + specular) * radiance * normalDotLight;
    color += albedo * uSecondaryColor * max(dot(normalVector, normalize(-uSecondaryDirection)), 0.0);
    color += albedo * uAmbientColor;

    if (uNightLights > 0.001) {
        float nightMask = smoothstep(0.06, -0.16, dot(normalVector, lightVector));
        float settlement = smoothstep(0.70, 0.88, skyFractal(objectDirection * 30.0 + uSeedOffset * 1.7, 4));
        color += vec3(1.0, 0.78, 0.42) * nightMask * settlement * uNightLights * 1.6;
    }
    color += albedo * uEmissive;

    fragColor = vec4(color, 1.0);
}
)GLSL";

const char* const kAtmosphereFragmentBody = R"GLSL(
in vec3 vWorldPosition;
in vec3 vNormal;
in vec3 vObjectDirection;
out vec4 fragColor;

uniform vec3 uCameraPosition;
uniform vec3 uStarDirection;
uniform vec3 uStarColor;
uniform float uStarIntensity;
uniform vec3 uAtmosphereColor;
uniform float uDensity;
uniform vec3 uBodyCenter;
uniform float uBodyRadius;
uniform float uAtmosphereRadius;

float rayleighPhase(float cosineAngle) {
    return 0.05968310365 * (1.0 + cosineAngle * cosineAngle);
}

float miePhase(float cosineAngle, float anisotropy) {
    float squared = anisotropy * anisotropy;
    float denominator = 1.0 + squared - 2.0 * anisotropy * cosineAngle;
    return (1.0 - squared) / max(12.566370614 * denominator * sqrt(max(denominator, 1.0e-5)), 1.0e-5);
}

void main() {
    vec3 viewVector = normalize(uCameraPosition - vWorldPosition);
    vec3 lightVector = normalize(-uStarDirection);
    vec3 normalVector = normalize(vNormal);

    vec3 toCenter = vWorldPosition - uBodyCenter;
    float distanceFromCenter = length(toCenter);
    float shellHeight = clamp((distanceFromCenter - uBodyRadius) / max(uAtmosphereRadius - uBodyRadius, 1.0e-3), 0.0, 1.0);
    float opticalDepth = exp(-shellHeight * 4.4);

    float rim = pow(1.0 - clamp(dot(normalVector, viewVector), 0.0, 1.0), 2.6);
    float cosineAngle = dot(viewVector, lightVector);
    float sunLit = clamp(dot(normalVector, lightVector) * 1.4 + 0.30, 0.0, 1.0);

    vec3 rayleigh = uAtmosphereColor * rayleighPhase(cosineAngle) * 9.4;
    vec3 mie = vec3(1.0, 0.94, 0.86) * miePhase(cosineAngle, 0.76) * 0.9;
    vec3 scattering = (rayleigh + mie) * uStarColor * uStarIntensity * sunLit * opticalDepth * uDensity;

    float alpha = clamp(rim * opticalDepth * uDensity * 1.5, 0.0, 1.0);
    fragColor = vec4(scattering * rim * 1.8, alpha);
}
)GLSL";

const char* const kRingFragmentBody = R"GLSL(
in vec3 vWorldPosition;
in vec3 vNormal;
in vec3 vObjectDirection;
out vec4 fragColor;

uniform vec3 uCameraPosition;
uniform vec3 uStarDirection;
uniform vec3 uStarColor;
uniform float uStarIntensity;
uniform vec3 uRingColor;
uniform vec3 uBodyCenter;
uniform float uBodyRadius;
uniform float uRingInner;
uniform float uRingOuter;
uniform float uSeedOffset;

void main() {
    float radialDistance = length(vWorldPosition - uBodyCenter);
    float normalized = clamp((radialDistance - uRingInner) / max(uRingOuter - uRingInner, 1.0e-3), 0.0, 1.0);

    float bands = skyFractal(vec3(normalized * 96.0, uSeedOffset, 0.0), 4);
    float gaps = smoothstep(0.30, 0.44, bands) * smoothstep(0.94, 0.72, normalized) * smoothstep(0.0, 0.06, normalized);
    float density = gaps * (0.45 + 0.55 * bands);
    if (density < 0.01) discard;

    vec3 lightVector = normalize(-uStarDirection);
    vec3 viewVector = normalize(uCameraPosition - vWorldPosition);
    float forwardScatter = pow(clamp(-dot(viewVector, lightVector), 0.0, 1.0), 6.0);
    vec3 color = uRingColor * uStarColor * uStarIntensity * (0.32 + forwardScatter * 1.5);

    vec3 planeNormal = normalize(vNormal);
    float grazing = abs(dot(viewVector, planeNormal));
    float alpha = clamp(density * (0.35 + 0.65 * grazing), 0.0, 1.0);
    fragColor = vec4(color * density, alpha);
}
)GLSL";

std::string composeFragment(const char* body) {
    std::string source = "#version 330 core\n";
    source += kColorCommonSource;
    source += kSkyCommonSource;
    source += body;
    return source;
}

}

Status CelestialBodyPass::initialize() {
    std::vector<MeshVertex> vertices;
    std::vector<u32> indices;
    buildIcoSphere(5, vertices, indices);
    sphereMesh.upload(vertices, indices);
    buildRing(0.35f, 1.0f, 192, vertices, indices);
    ringMesh.upload(vertices, indices);

    Status status = surfaceShader.compile("CelestialSurface", kBodyVertexSource, composeFragment(kSurfaceFragmentBody).c_str());
    if (!status.ok()) return status;
    status = atmosphereShader.compile("CelestialAtmosphere", kBodyVertexSource, composeFragment(kAtmosphereFragmentBody).c_str());
    if (!status.ok()) return status;
    status = ringShader.compile("CelestialRing", kBodyVertexSource, composeFragment(kRingFragmentBody).c_str());
    if (!status.ok()) return status;

    logInfo("render", "Himmelskoerper-Pass bereit");
    return statusOk();
}

void CelestialBodyPass::applyDetail(u32 sphereSubdivisions, bool enableAtmosphere, bool enableRings) {
    atmosphereEnabled = enableAtmosphere;
    ringsEnabled = enableRings;
    const u32 clamped = clampValue(sphereSubdivisions, 1u, 6u);
    if (clamped == currentSubdivisions) return;
    currentSubdivisions = clamped;

    std::vector<MeshVertex> vertices;
    std::vector<u32> indices;
    buildIcoSphere(currentSubdivisions, vertices, indices);
    sphereMesh.upload(vertices, indices);
    logInfo("render", "Koerper-Detailstufe %u (%u Dreiecke)", currentSubdivisions,
            static_cast<u32>(indices.size() / 3));
}

void CelestialBodyPass::release() {
    surfaceShader.release();
    atmosphereShader.release();
    ringShader.release();
    sphereMesh.release();
    ringMesh.release();
}

void CelestialBodyPass::render(const Camera& camera, const std::vector<CelestialBodyDraw>& bodies,
                               const CelestialLighting& lighting) {
    if (!surfaceShader.valid()) return;

    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);
    glDepthMask(GL_TRUE);
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);
    glDisable(GL_BLEND);

    for (const CelestialBodyDraw& body : bodies) {
        drawBody(camera, body, lighting);
    }

    if (!ringsEnabled && !atmosphereEnabled) {
        glDepthMask(GL_TRUE);
        return;
    }

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDepthMask(GL_FALSE);
    if (ringsEnabled) {
        for (const CelestialBodyDraw& body : bodies) {
            if (body.hasRing) drawRing(camera, body, lighting);
        }
    }
    glCullFace(GL_FRONT);
    if (atmosphereEnabled) {
        for (const CelestialBodyDraw& body : bodies) {
            if (body.atmosphereDensity > 0.001f && body.surfaceType != CelestialSurface::Star) {
                drawAtmosphere(camera, body, lighting);
            }
        }
    }
    glCullFace(GL_BACK);
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);
}

void CelestialBodyPass::drawBody(const Camera& camera, const CelestialBodyDraw& body, const CelestialLighting& lighting) {
    const Vec3 relativeCenter = (body.worldPosition - camera.origin()).toFloat();
    const f32 radius = static_cast<f32>(body.radiusMeters);

    Transform transform;
    transform.position = relativeCenter;
    transform.rotation = body.orientation;
    transform.scale = Vec3(radius);

    surfaceShader.bind();
    surfaceShader.setMat4("uViewProjection", camera.viewProjectionMatrix());
    surfaceShader.setMat4("uModel", transform.toMatrix());
    surfaceShader.setMat4("uNormalRotation", Mat4::fromMat3(body.orientation.toMat3()));
    surfaceShader.setVec3("uCameraPosition", camera.relativePosition());
    surfaceShader.setVec3("uStarDirection", lighting.starDirection);
    surfaceShader.setVec3("uStarColor", lighting.starColor);
    surfaceShader.setFloat("uStarIntensity", lighting.starIntensity);
    surfaceShader.setVec3("uAmbientColor", lighting.ambientColor);
    surfaceShader.setVec3("uSecondaryDirection", lighting.secondaryDirection);
    surfaceShader.setVec3("uSecondaryColor", lighting.secondaryColor);
    surfaceShader.setVec3("uPrimaryColor", body.primaryColor);
    surfaceShader.setVec3("uSecondaryTint", body.secondaryColor);
    surfaceShader.setFloat("uRoughness", body.roughness);
    surfaceShader.setFloat("uMetallic", body.metallic);
    surfaceShader.setFloat("uEmissive", body.emissiveStrength);
    surfaceShader.setFloat("uSurfaceDetail", body.surfaceDetail);
    surfaceShader.setFloat("uCloudCoverage", body.cloudCoverage);
    surfaceShader.setFloat("uIceCoverage", body.iceCoverage);
    surfaceShader.setFloat("uNightLights", body.nightLights);
    surfaceShader.setFloat("uSeedOffset", static_cast<f32>(body.surfaceSeed % 8192u) * 0.017f);
    surfaceShader.setFloat("uTime", lighting.elapsedSeconds);
    surfaceShader.setInt("uSurfaceType", static_cast<i32>(body.surfaceType));

    sphereMesh.draw();
}

void CelestialBodyPass::drawAtmosphere(const Camera& camera, const CelestialBodyDraw& body,
                                       const CelestialLighting& lighting) {
    const Vec3 relativeCenter = (body.worldPosition - camera.origin()).toFloat();
    const f32 radius = static_cast<f32>(body.radiusMeters);
    const f32 shellRadius = radius * (1.0f + maxValue(body.atmosphereHeightFraction, 0.005f));

    Transform transform;
    transform.position = relativeCenter;
    transform.rotation = body.orientation;
    transform.scale = Vec3(shellRadius);

    atmosphereShader.bind();
    atmosphereShader.setMat4("uViewProjection", camera.viewProjectionMatrix());
    atmosphereShader.setMat4("uModel", transform.toMatrix());
    atmosphereShader.setMat4("uNormalRotation", Mat4::fromMat3(body.orientation.toMat3()));
    atmosphereShader.setVec3("uCameraPosition", camera.relativePosition());
    atmosphereShader.setVec3("uStarDirection", lighting.starDirection);
    atmosphereShader.setVec3("uStarColor", lighting.starColor);
    atmosphereShader.setFloat("uStarIntensity", lighting.starIntensity);
    atmosphereShader.setVec3("uAtmosphereColor", body.atmosphereColor);
    atmosphereShader.setFloat("uDensity", body.atmosphereDensity);
    atmosphereShader.setVec3("uBodyCenter", relativeCenter);
    atmosphereShader.setFloat("uBodyRadius", radius);
    atmosphereShader.setFloat("uAtmosphereRadius", shellRadius);

    sphereMesh.draw();
}

void CelestialBodyPass::drawRing(const Camera& camera, const CelestialBodyDraw& body, const CelestialLighting& lighting) {
    const Vec3 relativeCenter = (body.worldPosition - camera.origin()).toFloat();
    const f32 radius = static_cast<f32>(body.radiusMeters);

    Transform transform;
    transform.position = relativeCenter;
    transform.rotation = body.orientation;
    transform.scale = Vec3(radius * body.ringOuterFraction);

    ringShader.bind();
    ringShader.setMat4("uViewProjection", camera.viewProjectionMatrix());
    ringShader.setMat4("uModel", transform.toMatrix());
    ringShader.setMat4("uNormalRotation", Mat4::fromMat3(body.orientation.toMat3()));
    ringShader.setVec3("uCameraPosition", camera.relativePosition());
    ringShader.setVec3("uStarDirection", lighting.starDirection);
    ringShader.setVec3("uStarColor", lighting.starColor);
    ringShader.setFloat("uStarIntensity", lighting.starIntensity);
    ringShader.setVec3("uRingColor", body.ringColor);
    ringShader.setVec3("uBodyCenter", relativeCenter);
    ringShader.setFloat("uBodyRadius", radius);
    ringShader.setFloat("uRingInner", radius * body.ringInnerFraction);
    ringShader.setFloat("uRingOuter", radius * body.ringOuterFraction);
    ringShader.setFloat("uSeedOffset", static_cast<f32>(body.surfaceSeed % 4096u) * 0.031f);

    glDisable(GL_CULL_FACE);
    ringMesh.draw();
    glEnable(GL_CULL_FACE);
}

}
