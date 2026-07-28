#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uDepthTex;
uniform sampler2D uShadowAtlas;
uniform sampler2D uBlueNoise;

uniform mat4 uInvViewProj;
uniform mat4 uShadowMatrix[MAX_SHADOWS];
uniform vec3 uCameraPos;
uniform vec2 uResolution;
uniform float uTime;
uniform float uFrameIndex;

uniform int uLightCount;
uniform vec4 uLightPosRange[MAX_LIGHTS];
uniform vec4 uLightColor[MAX_LIGHTS];
uniform vec4 uLightDir[MAX_LIGHTS];
uniform vec4 uLightExtra[MAX_LIGHTS];

uniform float uFogDensity;
uniform float uFogHeightFalloff;
uniform float uFogBase;
uniform vec3 uFogColor;
uniform float uScattering;
uniform int uSteps;
uniform float uMaxDistance;
uniform float uDustAmount;

float shadowFactor(int slot, vec3 p) {
    if (slot < 0 || slot >= MAX_SHADOWS) return 1.0;
    vec4 lp = uShadowMatrix[slot] * vec4(p, 1.0);
    if (lp.w <= 0.0) return 1.0;
    vec3 proj = lp.xyz / lp.w * 0.5 + 0.5;
    if (proj.z > 1.0 || proj.x < 0.01 || proj.x > 0.99 || proj.y < 0.01 || proj.y > 0.99) return 1.0;
    float tile = 1.0 / float(SHADOW_TILES);
    vec2 base = vec2(float(slot % SHADOW_TILES), float(slot / SHADOW_TILES)) * tile;
    float d = texture(uShadowAtlas, base + proj.xy * tile).r;
    return proj.z - 0.0025 <= d ? 1.0 : 0.0;
}

float henyeyGreenstein(float cosT, float g) {
    float g2 = g * g;
    return (1.0 - g2) / (4.0 * PI * pow(max(1.0 + g2 - 2.0 * g * cosT, 1e-4), 1.5));
}

float fogDensityAt(vec3 p) {
    float h = exp(-max(p.y - uFogBase, 0.0) * uFogHeightFalloff);
    float turbulence = fbm3d(p * 0.22 + vec3(uTime * 0.013, uTime * 0.007, -uTime * 0.011), 3);
    float dust = mix(0.65, 1.5, turbulence);
    return uFogDensity * h * dust;
}

void main() {
    float depth = texture(uDepthTex, vUV).r;
    vec3 worldPos = worldFromDepth(vUV, min(depth, 0.9999), uInvViewProj);

    vec3 rayDir = worldPos - uCameraPos;
    float sceneDist = length(rayDir);
    rayDir /= max(sceneDist, 1e-4);
    float maxDist = min(sceneDist, uMaxDistance);

    float jitter = texture(uBlueNoise, gl_FragCoord.xy / 64.0).r;
    jitter = fract(jitter + uFrameIndex * 0.618034);

    float stepLen = maxDist / float(uSteps);
    vec3 accum = vec3(0.0);
    float transmittance = 1.0;

    float t = stepLen * jitter;

    for (int i = 0; i < uSteps; i++) {
        vec3 p = uCameraPos + rayDir * t;
        float density = fogDensityAt(p) * stepLen;
        if (density > 0.0001) {
            vec3 inScatter = vec3(0.0);
            for (int l = 0; l < uLightCount; l++) {
                vec4 pr = uLightPosRange[l];
                vec4 ex = uLightExtra[l];
                if (ex.z <= 0.001) continue;

                vec3 toL = pr.xyz - p;
                float dist = length(toL);
                if (dist > pr.w) continue;
                vec3 L = toL / max(dist, 1e-4);

                float atten = attenuate(dist, pr.w);
                vec4 lc = uLightColor[l];
                if (lc.w > 0.5) {
                    vec4 ld = uLightDir[l];
                    float cd = dot(-L, normalize(ld.xyz));
                    float spot = saturate((cd - ld.w) / max(ex.x - ld.w, 1e-4));
                    spot *= spot;
                    if (spot <= 0.002) continue;
                    atten *= spot;
                }
                if (atten <= 0.0002) continue;

                float sh = shadowFactor(int(ex.y), p);
                if (sh <= 0.001) continue;

                float phase = henyeyGreenstein(dot(rayDir, -L), uScattering);
                inScatter += lc.rgb * atten * sh * phase * ex.z;
            }

            inScatter += uFogColor * 0.06;

            vec3 s = inScatter * density;
            accum += s * transmittance;
            transmittance *= exp(-density * 1.35);
            if (transmittance < 0.005) break;
        }
        t += stepLen;
    }

    if (uDustAmount > 0.001) {
        float motes = fbm3d(worldPos * 3.5 + vec3(0.0, uTime * 0.08, 0.0), 2);
        motes = smoothstep(0.72, 0.95, motes);
        accum += vec3(motes) * uDustAmount * 0.02;
    }

    oColor = vec4(accum, transmittance);
}
