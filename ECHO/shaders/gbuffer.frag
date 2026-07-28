#version 330 core

#include "common.glsl"

in vec3 vWorldPos;
in vec3 vNormal;
in vec4 vTangent;
in vec2 vUV;
in vec4 vColor;

layout(location = 0) out vec4 oAlbedoAO;
layout(location = 1) out vec4 oNormal;
layout(location = 2) out vec4 oMaterial;

uniform sampler2DArray uAlbedoArray;
uniform sampler2DArray uNormalArray;
uniform sampler2DArray uORMArray;
uniform sampler2D uDetailNoise;

uniform vec4 uMatA[MAT_COUNT];
uniform vec4 uMatB[MAT_COUNT];
uniform vec4 uMatC[MAT_COUNT];

uniform int uMaterial;
uniform vec3 uCameraPos;
uniform float uTime;
uniform float uGlobalWetness;
uniform float uDecay;
uniform vec4 uTintOverride;

void main() {
    int mi = clamp(uMaterial, 0, MAT_COUNT - 1);
    vec4 A = uMatA[mi];
    vec4 B = uMatB[mi];
    vec4 C = uMatC[mi];

    vec2 uv = vUV * A.xy;
    float layer = A.w;

    vec4 albedo = texture(uAlbedoArray, vec3(uv, layer));
    vec3 nrm = texture(uNormalArray, vec3(uv, layer)).rgb * 2.0 - 1.0;
    vec3 orm = texture(uORMArray, vec3(uv, layer)).rgb;

    vec3 macro = texture(uDetailNoise, vWorldPos.xz * 0.031 + vWorldPos.y * 0.017).rgb;
    float macroDirt = mix(0.82, 1.12, macro.x);

    vec3 col = albedo.rgb * B.rgb * vColor.rgb * macroDirt;
    col *= uTintOverride.rgb;

    float ao = orm.r;
    float rough = clamp(orm.g * C.x, 0.03, 1.0);
    float metal = clamp(orm.b * C.y, 0.0, 1.0);

    float grime = smoothstep(0.35, 0.85, macro.y) * uDecay;
    col = mix(col, col * vec3(0.55, 0.52, 0.46), grime * 0.45);
    rough = clamp(rough + grime * 0.15, 0.03, 1.0);
    ao *= 1.0 - grime * 0.18;

    vec3 N = normalize(vNormal);
    vec3 T = normalize(vTangent.xyz - N * dot(N, vTangent.xyz));
    vec3 Bn = cross(N, T) * vTangent.w;
    nrm.xy *= C.z;
    vec3 worldN = normalize(mat3(T, Bn, N) * normalize(nrm));

    float wet = clamp(A.z + uGlobalWetness * step(0.55, N.y), 0.0, 1.0);
    if (wet > 0.001) {
        float puddle = smoothstep(0.42, 0.62, macro.z);
        float w = wet * puddle;
        rough = mix(rough, 0.045, w);
        col = mix(col, col * 0.42, w * 0.8);
        worldN = normalize(mix(worldN, N, w * 0.85));
        ao = mix(ao, 1.0, w * 0.5);
    }

    float emissive = B.a;

    oAlbedoAO = vec4(col, ao);
    oNormal = vec4(encodeNormal(worldN), 1.0);
    oMaterial = vec4(rough, metal, emissive, vColor.a);
}
