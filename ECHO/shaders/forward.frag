#version 330 core

#include "common.glsl"

in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vUV;
in vec4 vColor;

out vec4 oColor;

uniform sampler2DArray uAlbedoArray;
uniform sampler2DArray uORMArray;

uniform vec4 uMatA[MAT_COUNT];
uniform vec4 uMatB[MAT_COUNT];
uniform vec4 uMatC[MAT_COUNT];

uniform int uMaterial;
uniform vec3 uCameraPos;
uniform float uTime;
uniform float uAlpha;

uniform int uLightCount;
uniform vec4 uLightPosRange[MAX_LIGHTS];
uniform vec4 uLightColor[MAX_LIGHTS];
uniform vec4 uLightDir[MAX_LIGHTS];
uniform vec4 uLightExtra[MAX_LIGHTS];
uniform vec3 uAmbientTop;
uniform vec3 uAmbientBottom;
uniform float uAmbientIntensity;

void main() {
    int mi = clamp(uMaterial, 0, MAT_COUNT - 1);
    vec4 A = uMatA[mi];
    vec4 B = uMatB[mi];
    vec4 C = uMatC[mi];

    vec2 uv = vUV * A.xy;
    vec4 albedo = texture(uAlbedoArray, vec3(uv, A.w));
    vec3 orm = texture(uORMArray, vec3(uv, A.w)).rgb;

    vec3 col = albedo.rgb * B.rgb * vColor.rgb;
    float rough = clamp(orm.g * C.x, 0.03, 1.0);
    float metal = clamp(orm.b * C.y, 0.0, 1.0);

    vec3 N = normalize(vNormal);
    vec3 V = normalize(uCameraPos - vWorldPos);
    if (dot(N, V) < 0.0) N = -N;
    float NoV = max(dot(N, V), 1e-4);

    vec3 f0 = mix(vec3(0.04), col, metal);
    vec3 diffuseColor = col * (1.0 - metal);
    vec3 result = vec3(0.0);

    for (int i = 0; i < uLightCount; i++) {
        vec4 pr = uLightPosRange[i];
        vec3 toLight = pr.xyz - vWorldPos;
        float dist = length(toLight);
        if (dist > pr.w) continue;
        vec3 L = toLight / max(dist, 1e-4);
        float NoL = dot(N, L);
        if (NoL <= 0.0) continue;

        float atten = attenuate(dist, pr.w);
        vec4 lc = uLightColor[i];
        if (lc.w > 0.5) {
            vec4 ld = uLightDir[i];
            vec4 ex = uLightExtra[i];
            float cd = dot(-L, normalize(ld.xyz));
            float spot = saturate((cd - ld.w) / max(ex.x - ld.w, 1e-4));
            spot *= spot;
            atten *= spot;
        }
        if (atten <= 0.0002) continue;

        vec3 H = normalize(V + L);
        float NoH = saturate(dot(N, H));
        float LoH = saturate(dot(L, H));
        float D = D_GGX(NoH, rough);
        float Vis = V_SmithGGX(NoV, NoL, rough);
        vec3 F = F_Schlick(f0, LoH);
        result += (diffuseColor * INV_PI + D * Vis * F) * lc.rgb * (NoL * atten);
    }

    vec3 ambient = mix(uAmbientBottom, uAmbientTop, N.y * 0.5 + 0.5) * uAmbientIntensity;
    result += diffuseColor * ambient;
    result += ambient * envBRDFApprox(f0, rough, NoV);
    result += col * B.a;

    float fres = pow(1.0 - NoV, 4.0);
    float alpha = clamp(uAlpha * C.w + fres * 0.6, 0.0, 1.0);
    result += vec3(fres) * 0.12;

    oColor = vec4(result, alpha);
}
