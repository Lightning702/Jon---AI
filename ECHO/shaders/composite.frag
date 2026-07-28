#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uSceneTex;
uniform sampler2D uSSRTex;
uniform sampler2D uFogTex;
uniform sampler2D uNormalTex;
uniform sampler2D uMaterialTex;
uniform sampler2D uAlbedoAO;
uniform sampler2D uDepthTex;

uniform mat4 uInvViewProj;
uniform vec3 uCameraPos;
uniform float uSSRStrength;
uniform float uFogStrength;

void main() {
    vec3 color = texture(uSceneTex, vUV).rgb;
    float depth = texture(uDepthTex, vUV).r;

    if (depth < 0.99999) {
        vec4 ssr = texture(uSSRTex, vUV);
        if (ssr.a > 0.001) {
            vec3 N = decodeNormal(texture(uNormalTex, vUV).rgb);
            vec4 mat = texture(uMaterialTex, vUV);
            vec3 albedo = texture(uAlbedoAO, vUV).rgb;
            float rough = mat.r;
            float metal = mat.g;
            vec3 worldPos = worldFromDepth(vUV, depth, uInvViewProj);
            vec3 V = normalize(uCameraPos - worldPos);
            float NoV = max(dot(N, V), 1e-4);
            vec3 f0 = mix(vec3(0.04), albedo, metal);
            vec3 fres = envBRDFApprox(f0, rough, NoV);
            color += ssr.rgb * fres * ssr.a * uSSRStrength * texture(uAlbedoAO, vUV).a;
        }
    }

    vec4 fog = texture(uFogTex, vUV);
    color = color * mix(1.0, fog.a, uFogStrength) + fog.rgb * uFogStrength;

    oColor = vec4(color, 1.0);
}
