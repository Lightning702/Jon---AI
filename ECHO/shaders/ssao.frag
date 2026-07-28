#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uDepthTex;
uniform sampler2D uNormalTex;
uniform sampler2D uBlueNoise;

uniform mat4 uProj;
uniform mat4 uInvProj;
uniform mat4 uView;
uniform vec2 uResolution;
uniform vec3 uKernel[SSAO_KERNEL];
uniform float uRadius;
uniform float uIntensity;
uniform float uBias;
uniform float uFrameIndex;
uniform int uKernelCount;

void main() {
    float depth = texture(uDepthTex, vUV).r;
    if (depth >= 0.99999) {
        oColor = vec4(1.0);
        return;
    }

    vec3 viewPos = viewFromDepth(vUV, depth, uInvProj);
    vec3 worldN = decodeNormal(texture(uNormalTex, vUV).rgb);
    vec3 N = normalize(mat3(uView) * worldN);

    vec2 noiseUV = gl_FragCoord.xy / 64.0;
    float rnd = texture(uBlueNoise, noiseUV).r;
    float angle = fract(rnd + uFrameIndex * 0.618034) * 6.2831853;
    vec3 randVec = vec3(cos(angle), sin(angle), 0.0);

    vec3 T = normalize(randVec - N * dot(randVec, N));
    vec3 B = cross(N, T);
    mat3 TBN = mat3(T, B, N);

    float occlusion = 0.0;
    float radius = uRadius;

    for (int i = 0; i < uKernelCount; i++) {
        vec3 samplePos = viewPos + (TBN * uKernel[i]) * radius;
        vec4 offset = uProj * vec4(samplePos, 1.0);
        offset.xyz /= offset.w;
        vec2 sUV = offset.xy * 0.5 + 0.5;
        if (sUV.x < 0.0 || sUV.x > 1.0 || sUV.y < 0.0 || sUV.y > 1.0) continue;

        float sd = texture(uDepthTex, sUV).r;
        if (sd >= 0.99999) continue;
        vec3 sampleView = viewFromDepth(sUV, sd, uInvProj);

        float rangeCheck = smoothstep(0.0, 1.0, radius / max(abs(viewPos.z - sampleView.z), 1e-4));
        occlusion += (sampleView.z >= samplePos.z + uBias ? 1.0 : 0.0) * rangeCheck;
    }

    float ao = 1.0 - (occlusion / float(max(uKernelCount, 1))) * uIntensity;
    oColor = vec4(clamp(ao, 0.0, 1.0));
}
