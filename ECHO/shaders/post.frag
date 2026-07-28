#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uSceneTex;
uniform sampler2D uBloomTex;
uniform sampler2D uDepthTex;
uniform sampler2D uBlueNoise;

uniform vec2 uResolution;
uniform float uTime;
uniform float uExposure;
uniform float uBloomStrength;
uniform float uVignette;
uniform float uGrain;
uniform float uChromatic;
uniform float uSaturation;
uniform float uContrast;
uniform vec3 uLift;
uniform vec3 uGamma;
uniform vec3 uGain;
uniform float uSanity;
uniform float uDistortion;
uniform float uPulse;
uniform float uFlashWhite;
uniform float uFade;
uniform float uScanline;

vec3 applyGrade(vec3 c) {
    c = pow(max(c, vec3(0.0)), vec3(1.0)) * uGain + uLift * (1.0 - c);
    c = pow(max(c, vec3(1e-5)), vec3(1.0) / max(uGamma, vec3(0.05)));
    float l = luminance(c);
    c = mix(vec3(l), c, uSaturation);
    c = (c - 0.5) * uContrast + 0.5;
    return c;
}

void main() {
    vec2 uv = vUV;
    vec2 centered = uv - 0.5;
    float r2 = dot(centered, centered);

    float breath = sin(uTime * 1.1) * 0.5 + 0.5;
    float warp = uDistortion * (0.02 + 0.02 * breath);
    if (warp > 0.0001) {
        float wob = fbm3d(vec3(uv * 3.0, uTime * 0.35), 3) - 0.5;
        uv += centered * r2 * warp * 2.2;
        uv += vec2(wob, -wob) * warp * 0.6;
    }
    if (uPulse > 0.0001) {
        uv += centered * sin(uTime * 6.0) * uPulse * 0.012;
    }

    float ca = uChromatic * (1.0 + r2 * 4.5) + uDistortion * 0.0035;
    vec3 color;
    if (ca > 0.00002) {
        vec2 dir = normalize(centered + 1e-6);
        color.r = texture(uSceneTex, uv + dir * ca).r;
        color.g = texture(uSceneTex, uv).g;
        color.b = texture(uSceneTex, uv - dir * ca).b;
    } else {
        color = texture(uSceneTex, uv).rgb;
    }

    vec3 bloom = texture(uBloomTex, uv).rgb;
    color += bloom * uBloomStrength;

    color *= uExposure;
    color = tonemapACESFitted(color);
    color = applyGrade(color);

    float vig = 1.0 - smoothstep(0.22, 0.86, r2 * (1.0 + uVignette));
    vig = mix(1.0, vig, saturate(uVignette));
    color *= vig;

    if (uScanline > 0.001) {
        float sl = sin(uv.y * uResolution.y * 1.35 + uTime * 12.0) * 0.5 + 0.5;
        color *= mix(1.0, 0.86 + 0.14 * sl, uScanline);
    }

    float noise = texture(uBlueNoise, gl_FragCoord.xy / 64.0 + vec2(fract(uTime * 13.7), fract(uTime * 7.3))).r;
    float grainAmount = uGrain * (1.0 + (1.0 - uSanity) * 1.6);
    color += (noise - 0.5) * grainAmount * mix(0.35, 1.0, 1.0 - luminance(color));

    color = mix(color, vec3(1.0), saturate(uFlashWhite));
    color *= uFade;

    color += (hash12(gl_FragCoord.xy + fract(uTime) * 91.0) - 0.5) / 255.0;

    oColor = vec4(max(color, vec3(0.0)), 1.0);
}
