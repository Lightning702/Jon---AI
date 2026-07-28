#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uSource;
uniform vec2 uTexelSize;
uniform float uThreshold;
uniform float uSoftKnee;
uniform float uClamp;

vec3 prefilter(vec3 c) {
    float br = max(c.r, max(c.g, c.b));
    float knee = uThreshold * uSoftKnee + 1e-5;
    float soft = clamp(br - uThreshold + knee, 0.0, 2.0 * knee);
    soft = soft * soft / (4.0 * knee);
    float contribution = max(soft, br - uThreshold) / max(br, 1e-5);
    return min(c, vec3(uClamp)) * contribution;
}

void main() {
    vec2 t = uTexelSize;
    vec3 a = texture(uSource, vUV + vec2(-t.x, -t.y)).rgb;
    vec3 b = texture(uSource, vUV + vec2(t.x, -t.y)).rgb;
    vec3 c = texture(uSource, vUV + vec2(-t.x, t.y)).rgb;
    vec3 d = texture(uSource, vUV + vec2(t.x, t.y)).rgb;
    vec3 e = texture(uSource, vUV).rgb;
    vec3 sum = (a + b + c + d) * 0.125 + e * 0.5;
    oColor = vec4(prefilter(sum), 1.0);
}
