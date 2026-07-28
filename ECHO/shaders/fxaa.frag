#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uSource;
uniform vec2 uTexelSize;

void main() {
    vec3 rgbNW = texture(uSource, vUV + vec2(-1.0, -1.0) * uTexelSize).rgb;
    vec3 rgbNE = texture(uSource, vUV + vec2(1.0, -1.0) * uTexelSize).rgb;
    vec3 rgbSW = texture(uSource, vUV + vec2(-1.0, 1.0) * uTexelSize).rgb;
    vec3 rgbSE = texture(uSource, vUV + vec2(1.0, 1.0) * uTexelSize).rgb;
    vec3 rgbM = texture(uSource, vUV).rgb;

    const vec3 luma = vec3(0.299, 0.587, 0.114);
    float lNW = dot(rgbNW, luma);
    float lNE = dot(rgbNE, luma);
    float lSW = dot(rgbSW, luma);
    float lSE = dot(rgbSE, luma);
    float lM = dot(rgbM, luma);

    float lMin = min(lM, min(min(lNW, lNE), min(lSW, lSE)));
    float lMax = max(lM, max(max(lNW, lNE), max(lSW, lSE)));

    if (lMax - lMin < max(0.0312, lMax * 0.125)) {
        oColor = vec4(rgbM, 1.0);
        return;
    }

    vec2 dir;
    dir.x = -((lNW + lNE) - (lSW + lSE));
    dir.y = ((lNW + lSW) - (lNE + lSE));

    float dirReduce = max((lNW + lNE + lSW + lSE) * 0.03125, 0.0078125);
    float rcpDirMin = 1.0 / (min(abs(dir.x), abs(dir.y)) + dirReduce);
    dir = clamp(dir * rcpDirMin, vec2(-8.0), vec2(8.0)) * uTexelSize;

    vec3 rgbA = 0.5 * (texture(uSource, vUV + dir * (1.0 / 3.0 - 0.5)).rgb +
                       texture(uSource, vUV + dir * (2.0 / 3.0 - 0.5)).rgb);
    vec3 rgbB = rgbA * 0.5 + 0.25 * (texture(uSource, vUV + dir * -0.5).rgb +
                                     texture(uSource, vUV + dir * 0.5).rgb);

    float lB = dot(rgbB, luma);
    oColor = vec4((lB < lMin || lB > lMax) ? rgbA : rgbB, 1.0);
}
