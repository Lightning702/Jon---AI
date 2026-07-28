#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uColorTex;
uniform sampler2D uDepthTex;
uniform sampler2D uNormalTex;
uniform sampler2D uMaterialTex;
uniform sampler2D uBlueNoise;

uniform mat4 uProj;
uniform mat4 uInvProj;
uniform mat4 uView;
uniform mat4 uInvView;
uniform vec2 uResolution;
uniform float uFrameIndex;
uniform float uMaxDistance;
uniform float uIntensity;
uniform int uSteps;
uniform int uRefineSteps;

void main() {
    float depth = texture(uDepthTex, vUV).r;
    vec4 mat = texture(uMaterialTex, vUV);
    float rough = mat.r;

    if (depth >= 0.99999 || rough > 0.55) {
        oColor = vec4(0.0);
        return;
    }

    vec3 viewPos = viewFromDepth(vUV, depth, uInvProj);
    vec3 worldN = decodeNormal(texture(uNormalTex, vUV).rgb);
    vec3 N = normalize(mat3(uView) * worldN);
    vec3 V = normalize(viewPos);
    vec3 R = reflect(V, N);

    if (R.z > 0.0 && viewPos.z > -0.2) {
        oColor = vec4(0.0);
        return;
    }

    float jitter = texture(uBlueNoise, gl_FragCoord.xy / 64.0).r;
    jitter = fract(jitter + uFrameIndex * 0.618034);

    float stepSize = uMaxDistance / float(uSteps);
    vec3 rayPos = viewPos + R * stepSize * (0.35 + jitter * 0.7);

    float hit = 0.0;
    vec2 hitUV = vec2(0.0);
    float lastDelta = 0.0;

    for (int i = 0; i < uSteps; i++) {
        rayPos += R * stepSize;
        if (rayPos.z > -0.05) break;

        vec4 clip = uProj * vec4(rayPos, 1.0);
        vec2 suv = (clip.xy / clip.w) * 0.5 + 0.5;
        if (suv.x < 0.0 || suv.x > 1.0 || suv.y < 0.0 || suv.y > 1.0) break;

        float sd = texture(uDepthTex, suv).r;
        if (sd >= 0.99999) continue;
        vec3 sceneView = viewFromDepth(suv, sd, uInvProj);

        float delta = sceneView.z - rayPos.z;
        if (delta > 0.0 && delta < stepSize * 2.4) {
            vec3 a = rayPos - R * stepSize;
            vec3 b = rayPos;
            for (int j = 0; j < uRefineSteps; j++) {
                vec3 mid = (a + b) * 0.5;
                vec4 mc = uProj * vec4(mid, 1.0);
                vec2 muv = (mc.xy / mc.w) * 0.5 + 0.5;
                float md = texture(uDepthTex, muv).r;
                vec3 mView = viewFromDepth(muv, md, uInvProj);
                if (mView.z - mid.z > 0.0) b = mid; else a = mid;
                suv = muv;
            }
            hit = 1.0;
            hitUV = suv;
            break;
        }
        lastDelta = delta;
    }

    if (hit < 0.5) {
        oColor = vec4(0.0);
        return;
    }

    vec2 edge = smoothstep(vec2(0.0), vec2(0.12), hitUV) * (1.0 - smoothstep(vec2(0.88), vec2(1.0), hitUV));
    float fade = edge.x * edge.y;
    fade *= 1.0 - smoothstep(0.35, 0.55, rough);

    float lod = rough * 5.0;
    vec3 reflected = textureLod(uColorTex, hitUV, lod).rgb;

    oColor = vec4(reflected, fade * uIntensity);
}
