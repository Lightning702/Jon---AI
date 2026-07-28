const float PI = 3.14159265359;
const float INV_PI = 0.31830988618;

float saturate(float x) { return clamp(x, 0.0, 1.0); }
vec3 saturate3(vec3 x) { return clamp(x, vec3(0.0), vec3(1.0)); }

float luminance(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

vec3 encodeNormal(vec3 n) { return normalize(n) * 0.5 + 0.5; }
vec3 decodeNormal(vec3 e) { return normalize(e * 2.0 - 1.0); }

float linearDepth(float d, float zn, float zf) {
    float z = d * 2.0 - 1.0;
    return (2.0 * zn * zf) / (zf + zn - z * (zf - zn));
}

vec3 worldFromDepth(vec2 uv, float depth, mat4 invViewProj) {
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 w = invViewProj * ndc;
    return w.xyz / w.w;
}

vec3 viewFromDepth(vec2 uv, float depth, mat4 invProj) {
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 v = invProj * ndc;
    return v.xyz / v.w;
}

float D_GGX(float NoH, float rough) {
    float a = rough * rough;
    float a2 = a * a;
    float d = (NoH * a2 - NoH) * NoH + 1.0;
    return a2 / max(PI * d * d, 1e-7);
}

float V_SmithGGX(float NoV, float NoL, float rough) {
    float a = rough * rough;
    float a2 = a * a;
    float lv = NoL * sqrt(NoV * NoV * (1.0 - a2) + a2);
    float ll = NoV * sqrt(NoL * NoL * (1.0 - a2) + a2);
    return 0.5 / max(lv + ll, 1e-7);
}

vec3 F_Schlick(vec3 f0, float u) {
    float f = pow(1.0 - u, 5.0);
    return f0 + (vec3(1.0) - f0) * f;
}

float F_Schlick90(float u, float f0, float f90) {
    return f0 + (f90 - f0) * pow(1.0 - u, 5.0);
}

float Fd_Burley(float NoV, float NoL, float LoH, float rough) {
    float f90 = 0.5 + 2.0 * rough * LoH * LoH;
    float lightScatter = F_Schlick90(NoL, 1.0, f90);
    float viewScatter = F_Schlick90(NoV, 1.0, f90);
    return lightScatter * viewScatter * INV_PI;
}

vec3 envBRDFApprox(vec3 f0, float rough, float NoV) {
    const vec4 c0 = vec4(-1.0, -0.0275, -0.572, 0.022);
    const vec4 c1 = vec4(1.0, 0.0425, 1.04, -0.04);
    vec4 r = rough * c0 + c1;
    float a004 = min(r.x * r.x, exp2(-9.28 * NoV)) * r.x + r.y;
    vec2 ab = vec2(-1.04, 1.04) * a004 + r.zw;
    return f0 * ab.x + ab.y;
}

float attenuate(float dist, float range) {
    float d = dist / max(range, 0.001);
    float d2 = d * d;
    float f = saturate(1.0 - d2 * d2);
    return (f * f) / (dist * dist + 0.01);
}

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float hash13(vec3 p3) {
    p3 = fract(p3 * 0.1031);
    p3 += dot(p3, p3.zyx + 31.32);
    return fract((p3.x + p3.y) * p3.z);
}

float vnoise3(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float n000 = hash13(i);
    float n100 = hash13(i + vec3(1, 0, 0));
    float n010 = hash13(i + vec3(0, 1, 0));
    float n110 = hash13(i + vec3(1, 1, 0));
    float n001 = hash13(i + vec3(0, 0, 1));
    float n101 = hash13(i + vec3(1, 0, 1));
    float n011 = hash13(i + vec3(0, 1, 1));
    float n111 = hash13(i + vec3(1, 1, 1));
    return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
               mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}

float fbm3d(vec3 p, int octaves) {
    float a = 0.5, s = 0.0, n = 0.0;
    for (int i = 0; i < octaves; i++) {
        s += a * vnoise3(p);
        n += a;
        p *= 2.02;
        a *= 0.5;
    }
    return s / max(n, 1e-5);
}

float interleavedGradientNoise(vec2 p) {
    return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715))));
}

vec3 ACESFilm(vec3 x) {
    const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
    return saturate3((x * (a * x + b)) / (x * (c * x + d) + e));
}

vec3 tonemapACESFitted(vec3 color) {
    const mat3 inputMat = mat3(
        0.59719, 0.07600, 0.02840,
        0.35458, 0.90834, 0.13383,
        0.04823, 0.01566, 0.83777);
    const mat3 outputMat = mat3(
        1.60475, -0.10208, -0.00327,
        -0.53108, 1.10813, -0.07276,
        -0.07367, -0.00605, 1.07602);
    vec3 v = inputMat * color;
    vec3 a = v * (v + 0.0245786) - 0.000090537;
    vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081;
    return saturate3(outputMat * (a / b));
}

vec3 linearToSrgb(vec3 c) {
    return mix(c * 12.92, 1.055 * pow(max(c, vec3(1e-5)), vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}

vec3 srgbToLinear(vec3 c) {
    return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}
