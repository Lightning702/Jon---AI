#version 330 core

#include "common.glsl"

in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vUV;
in float vBiome;
in float vHeight;
in float vSlope;

layout(location = 0) out vec4 oAlbedoAO;
layout(location = 1) out vec4 oNormal;
layout(location = 2) out vec4 oMaterial;

uniform sampler2D uDetailNoise;
uniform float uTime;
uniform float uWaterLevel;
uniform float uMaxHeight;
uniform float uSnowLine;

vec3 biomeColor(float b) {
    if (b < 0.5) return vec3(0.115, 0.190, 0.072);
    if (b < 1.5) return vec3(0.062, 0.128, 0.055);
    if (b < 2.5) return vec3(0.290, 0.192, 0.058);
    if (b < 3.5) return vec3(0.128, 0.132, 0.108);
    if (b < 4.5) return vec3(0.700, 0.735, 0.790);
    if (b < 5.5) return vec3(0.086, 0.115, 0.078);
    return vec3(0.400, 0.360, 0.268);
}

float biomeRough(float b) {
    if (b < 0.5) return 0.86;
    if (b < 1.5) return 0.90;
    if (b < 2.5) return 0.84;
    if (b < 3.5) return 0.78;
    if (b < 4.5) return 0.62;
    if (b < 5.5) return 0.72;
    return 0.80;
}

void main() {
    vec3 N = normalize(vNormal);
    float slope = 1.0 - N.y;

    vec3 macro = texture(uDetailNoise, vUV * 0.012).rgb;
    vec3 meso = texture(uDetailNoise, vUV * 0.075).rgb;
    vec3 micro = texture(uDetailNoise, vUV * 0.55).rgb;

    float blend = smoothstep(0.15, 0.85, macro.x);
    vec3 base = biomeColor(vBiome);
    vec3 alt = biomeColor(clamp(vBiome + (blend > 0.5 ? 1.0 : -1.0), 0.0, 6.0));
    vec3 col = mix(base, alt, smoothstep(0.42, 0.62, macro.y) * 0.35);

    col *= 0.78 + 0.44 * meso.x;
    col *= 0.90 + 0.20 * micro.z;

    vec3 rock = vec3(0.118, 0.112, 0.104) * (0.72 + 0.55 * meso.y);
    float rockMask = smoothstep(0.30, 0.62, slope);
    col = mix(col, rock, rockMask);

    float snow = smoothstep(uSnowLine - 0.10, uSnowLine + 0.06, vHeight) * (1.0 - smoothstep(0.55, 0.80, slope));
    col = mix(col, vec3(0.760, 0.795, 0.845) * (0.90 + 0.16 * micro.x), snow);

    float sand = 1.0 - smoothstep(uWaterLevel + 0.4, uWaterLevel + 3.4, vWorldPos.y);
    col = mix(col, vec3(0.400, 0.355, 0.262) * (0.85 + 0.3 * meso.z), sand * (1.0 - rockMask));

    float wet = 1.0 - smoothstep(uWaterLevel - 0.2, uWaterLevel + 1.1, vWorldPos.y);
    col *= mix(1.0, 0.58, wet);

    float rough = biomeRough(vBiome);
    rough = mix(rough, 0.68, rockMask);
    rough = mix(rough, 0.42, snow);
    rough = mix(rough, 0.16, wet);
    rough = clamp(rough + (micro.y - 0.5) * 0.16, 0.05, 1.0);

    vec3 perturb = normalize(N + vec3((meso.x - 0.5) * 0.22, 0.0, (meso.z - 0.5) * 0.22));

    float ao = mix(1.0, 0.74, rockMask * 0.5);
    ao *= 0.86 + 0.14 * macro.z;

    oAlbedoAO = vec4(col, ao);
    oNormal = vec4(encodeNormal(perturb), 1.0);
    oMaterial = vec4(rough, 0.0, 0.0, 1.0);
}
