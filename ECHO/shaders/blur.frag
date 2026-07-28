#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uSource;
uniform sampler2D uDepthTex;
uniform vec2 uTexelSize;
uniform vec2 uDirection;
uniform float uDepthSigma;
uniform float uNear;
uniform float uFar;

void main() {
    float centerDepth = linearDepth(texture(uDepthTex, vUV).r, uNear, uFar);
    vec4 sum = texture(uSource, vUV);
    float weightSum = 1.0;

    const float weights[5] = float[5](1.0, 0.85, 0.6, 0.35, 0.16);

    for (int i = 1; i < 5; i++) {
        vec2 off = uDirection * uTexelSize * float(i);

        vec2 uvA = vUV + off;
        float dA = linearDepth(texture(uDepthTex, uvA).r, uNear, uFar);
        float wA = weights[i] * exp(-abs(dA - centerDepth) * uDepthSigma);
        sum += texture(uSource, uvA) * wA;
        weightSum += wA;

        vec2 uvB = vUV - off;
        float dB = linearDepth(texture(uDepthTex, uvB).r, uNear, uFar);
        float wB = weights[i] * exp(-abs(dB - centerDepth) * uDepthSigma);
        sum += texture(uSource, uvB) * wB;
        weightSum += wB;
    }

    oColor = sum / max(weightSum, 1e-4);
}
