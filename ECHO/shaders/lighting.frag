#version 330 core

#include "common.glsl"

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uAlbedoAO;
uniform sampler2D uNormalTex;
uniform sampler2D uMaterialTex;
uniform sampler2D uDepthTex;
uniform sampler2D uSSAOTex;
uniform sampler2D uShadowAtlas;

uniform mat4 uInvViewProj;
uniform vec3 uCameraPos;
uniform vec2 uResolution;
uniform float uTime;
uniform float uNear;
uniform float uFar;

uniform int uLightCount;
uniform vec4 uLightPosRange[MAX_LIGHTS];
uniform vec4 uLightColor[MAX_LIGHTS];
uniform vec4 uLightDir[MAX_LIGHTS];
uniform vec4 uLightExtra[MAX_LIGHTS];
uniform mat4 uShadowMatrix[MAX_SHADOWS];

uniform vec3 uAmbientTop;
uniform vec3 uAmbientBottom;
uniform float uAmbientIntensity;
uniform float uShadowTexel;
uniform float uSanity;

uniform int uSkyEnabled;
uniform vec3 uSunDir;
uniform vec3 uSunColor;
uniform float uSunIntensity;
uniform vec3 uSkyZenith;
uniform vec3 uSkyHorizon;
uniform vec3 uSkyGround;
uniform float uSunDisc;
uniform float uStars;
uniform float uClouds;
uniform float uAerialDensity;
uniform float uAerialHeight;

vec3 skyRadiance(vec3 dir) {
    float up = dir.y;
    vec3 col = mix(uSkyHorizon, uSkyZenith, pow(clamp(up, 0.0, 1.0), 0.55));
    col = mix(col, uSkyGround, smoothstep(0.0, -0.22, up));

    float sunAmount = max(dot(dir, -normalize(uSunDir)), 0.0);
    col += uSunColor * pow(sunAmount, 8.0) * 0.35;
    col += uSunColor * pow(sunAmount, 900.0) * 26.0 * uSunDisc;

    if (uClouds > 0.001 && up > -0.02) {
        vec2 cuv = dir.xz / max(up + 0.18, 0.05);
        float c = fbm3d(vec3(cuv * 0.55 + vec2(uTime * 0.004, 0.0), uTime * 0.008), 4);
        float band = smoothstep(0.45, 0.78, c) * smoothstep(0.0, 0.22, up);
        col = mix(col, mix(vec3(0.72, 0.74, 0.78), uSunColor * 1.1, sunAmount * 0.5), band * uClouds);
    }

    if (uStars > 0.001) {
        vec3 sp = floor(dir * 340.0);
        float star = step(0.9975, hash13(sp));
        col += vec3(star) * uStars * (0.5 + 0.5 * hash13(sp + 3.1));
    }
    return col;
}

float sampleShadow(int slot, vec3 worldPos, vec3 N, float NoL) {
    if (slot < 0 || slot >= MAX_SHADOWS) return 1.0;
    vec4 lp = uShadowMatrix[slot] * vec4(worldPos + N * (0.035 + 0.10 * (1.0 - NoL)), 1.0);
    if (lp.w <= 0.0) return 1.0;
    vec3 proj = lp.xyz / lp.w;
    proj = proj * 0.5 + 0.5;
    if (proj.z > 1.0 || proj.z < 0.0) return 1.0;
    if (proj.x < 0.002 || proj.x > 0.998 || proj.y < 0.002 || proj.y > 0.998) return 1.0;

    float tile = 1.0 / float(SHADOW_TILES);
    vec2 base = vec2(float(slot % SHADOW_TILES), float(slot / SHADOW_TILES)) * tile;
    vec2 uv = base + proj.xy * tile;

    float bias = max(0.0060 * (1.0 - NoL), 0.0016);
    float current = proj.z - bias;

    float shadow = 0.0;
    float texel = uShadowTexel;
    float rot = interleavedGradientNoise(gl_FragCoord.xy) * 6.2831853;
    float cs = cos(rot), sn = sin(rot);
    mat2 rotM = mat2(cs, -sn, sn, cs);

    const vec2 poisson[8] = vec2[8](
        vec2(-0.7071, 0.7071), vec2(0.7071, 0.7071),
        vec2(-0.7071, -0.7071), vec2(0.7071, -0.7071),
        vec2(-1.0, 0.0), vec2(1.0, 0.0),
        vec2(0.0, -1.0), vec2(0.0, 1.0));

    for (int i = 0; i < 8; i++) {
        vec2 o = rotM * poisson[i] * texel * 1.4;
        vec2 s = clamp(proj.xy + o, vec2(0.001), vec2(0.999));
        float d = texture(uShadowAtlas, base + s * tile).r;
        shadow += current <= d ? 1.0 : 0.0;
    }
    float centerD = texture(uShadowAtlas, uv).r;
    shadow += (current <= centerD ? 1.0 : 0.0);
    return shadow / 9.0;
}

void main() {
    float depth = texture(uDepthTex, vUV).r;
    if (depth >= 0.99999) {
        if (uSkyEnabled == 1) {
            vec3 far = worldFromDepth(vUV, 1.0, uInvViewProj);
            oColor = vec4(skyRadiance(normalize(far - uCameraPos)), 1.0);
        } else {
            oColor = vec4(0.0, 0.0, 0.0, 1.0);
        }
        return;
    }

    vec4 albedoAO = texture(uAlbedoAO, vUV);
    vec4 nrm = texture(uNormalTex, vUV);
    vec4 mat = texture(uMaterialTex, vUV);

    vec3 albedo = albedoAO.rgb;
    float texAO = albedoAO.a;
    vec3 N = decodeNormal(nrm.rgb);
    float rough = clamp(mat.r, 0.035, 1.0);
    float metal = mat.g;
    float emissive = mat.b;

    vec3 worldPos = worldFromDepth(vUV, depth, uInvViewProj);
    vec3 V = normalize(uCameraPos - worldPos);
    float NoV = max(dot(N, V), 1e-4);

    float ssao = texture(uSSAOTex, vUV).r;
    float ao = texAO * ssao;

    vec3 diffuseColor = albedo * (1.0 - metal);
    vec3 f0 = mix(vec3(0.04), albedo, metal);

    vec3 result = vec3(0.0);

    for (int i = 0; i < uLightCount; i++) {
        vec4 pr = uLightPosRange[i];
        vec4 lc = uLightColor[i];
        vec4 ld = uLightDir[i];
        vec4 ex = uLightExtra[i];

        vec3 toLight = pr.xyz - worldPos;
        float dist = length(toLight);
        if (dist > pr.w) continue;

        vec3 L = toLight / max(dist, 1e-4);
        float NoL = dot(N, L);
        if (NoL <= 0.0) continue;

        float atten = attenuate(dist, pr.w);
        if (lc.w > 0.5) {
            float cd = dot(-L, normalize(ld.xyz));
            float spot = saturate((cd - ld.w) / max(ex.x - ld.w, 1e-4));
            spot *= spot;
            if (spot <= 0.001) continue;
            atten *= spot;
        }
        if (atten <= 0.0001) continue;

        float shadow = 1.0;
        int slot = int(ex.y);
        if (slot >= 0) shadow = sampleShadow(slot, worldPos, N, NoL);
        if (shadow <= 0.001) continue;

        vec3 H = normalize(V + L);
        float NoH = saturate(dot(N, H));
        float LoH = saturate(dot(L, H));

        float D = D_GGX(NoH, rough);
        float Vis = V_SmithGGX(NoV, NoL, rough);
        vec3 F = F_Schlick(f0, LoH);

        vec3 spec = D * Vis * F;
        vec3 diff = diffuseColor * Fd_Burley(NoV, NoL, LoH, rough);

        result += (diff + spec) * lc.rgb * (NoL * atten * shadow);
    }

    if (uSunIntensity > 0.001) {
        vec3 L = -normalize(uSunDir);
        float NoL = dot(N, L);
        if (NoL > 0.0) {
            vec3 H = normalize(V + L);
            float NoH = saturate(dot(N, H));
            float LoH = saturate(dot(L, H));
            float D = D_GGX(NoH, rough);
            float Vis = V_SmithGGX(NoV, NoL, rough);
            vec3 F = F_Schlick(f0, LoH);
            vec3 diff = diffuseColor * Fd_Burley(NoV, NoL, LoH, rough);
            result += (diff + D * Vis * F) * uSunColor * uSunIntensity * NoL * (0.35 + 0.65 * ao);
        }
    }

    float hemi = N.y * 0.5 + 0.5;
    vec3 ambient = mix(uAmbientBottom, uAmbientTop, hemi) * uAmbientIntensity;
    vec3 irradiance = ambient * ao;
    result += diffuseColor * irradiance;

    vec3 R = reflect(-V, N);
    float horizon = saturate(1.0 + dot(R, N));
    horizon *= horizon;
    vec3 specAmbient = mix(uAmbientBottom, uAmbientTop, R.y * 0.5 + 0.5) * uAmbientIntensity;
    result += specAmbient * envBRDFApprox(f0, rough, NoV) * ao * horizon;

    result += albedo * emissive;

    if (uSkyEnabled == 1 && uAerialDensity > 0.0) {
        float dist = length(worldPos - uCameraPos);
        float heightFade = exp(-max(worldPos.y, 0.0) * uAerialHeight);
        float f = 1.0 - exp(-dist * uAerialDensity * heightFade);
        f = clamp(f, 0.0, 0.92);
        vec3 viewDir = normalize(worldPos - uCameraPos);
        result = mix(result, skyRadiance(viewDir) * 0.92, f);
    }

    float dissonance = 1.0 - uSanity;
    if (dissonance > 0.01) {
        float n = fbm3d(worldPos * 0.6 + vec3(0.0, uTime * 0.05, 0.0), 3);
        result = mix(result, result * vec3(0.86, 0.94, 1.06), dissonance * 0.45 * n);
    }

    oColor = vec4(result, 1.0);
}
