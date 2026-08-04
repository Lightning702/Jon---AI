#include "SkyCommon.hpp"

namespace sf {

const char* const kFullscreenVertexSource = R"GLSL(#version 330 core
out vec2 vScreenUv;
void main() {
    vec2 corner = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    vScreenUv = corner;
    gl_Position = vec4(corner * 2.0 - 1.0, 0.0, 1.0);
}
)GLSL";

const char* const kColorCommonSource = R"GLSL(
vec3 planckianChromaticity(float kelvin) {
    float temperature = clamp(kelvin, 1500.0, 29000.0);
    float inverse = 1000.0 / temperature;
    float x;
    if (temperature < 4000.0) {
        x = -0.2661239 * inverse * inverse * inverse - 0.2343589 * inverse * inverse
            + 0.8776956 * inverse + 0.179910;
    } else {
        x = -3.0258469 * inverse * inverse * inverse + 2.1070379 * inverse * inverse
            + 0.2226347 * inverse + 0.240390;
    }
    float y;
    if (temperature < 2222.0) {
        y = -1.1063814 * x * x * x - 1.34811020 * x * x + 2.18555832 * x - 0.20219683;
    } else if (temperature < 4000.0) {
        y = -0.9549476 * x * x * x - 1.37418593 * x * x + 2.09137015 * x - 0.16748867;
    } else {
        y = 3.0817580 * x * x * x - 5.87338670 * x * x + 3.75112997 * x - 0.37001483;
    }
    return vec3(x, y, 1.0 - x - y);
}

vec3 chromaticityToLinearRgb(vec3 xyz1) {
    float x = xyz1.x;
    float y = max(xyz1.y, 1e-4);
    vec3 tristimulus = vec3(x / y, 1.0, (1.0 - x - y) / y);
    mat3 xyzToRgb = mat3(
        3.2404542, -0.9692660, 0.0556434,
       -1.5371385,  1.8760108, -0.2040259,
       -0.4985314,  0.0415560, 1.0572252);
    return max(xyzToRgb * tristimulus, vec3(0.0));
}

vec3 blackBodyRadiance(float kelvin, float radiantScale) {
    vec3 linear = chromaticityToLinearRgb(planckianChromaticity(kelvin));
    float normalization = max(dot(linear, vec3(0.2126, 0.7152, 0.0722)), 1e-4);
    return linear / normalization * radiantScale;
}

float luminanceOf(vec3 color) {
    return dot(color, vec3(0.2126, 0.7152, 0.0722));
}
)GLSL";

const char* const kSkyCommonSource = R"GLSL(
float skyHash11(float value) {
    value = fract(value * 0.1031);
    value *= value + 33.33;
    value *= value + value;
    return fract(value);
}

float skyHash31(vec3 point) {
    point = fract(point * vec3(0.1031, 0.1030, 0.0973));
    point += dot(point, point.yxz + 33.33);
    return fract((point.x + point.y) * point.z);
}

vec3 skyHash33(vec3 point) {
    point = vec3(dot(point, vec3(127.1, 311.7, 74.7)),
                 dot(point, vec3(269.5, 183.3, 246.1)),
                 dot(point, vec3(113.5, 271.9, 124.6)));
    return fract(sin(point) * 43758.5453123);
}

float skyValueNoise(vec3 point) {
    vec3 cell = floor(point);
    vec3 local = fract(point);
    vec3 weight = local * local * (3.0 - 2.0 * local);
    float n000 = skyHash31(cell + vec3(0.0, 0.0, 0.0));
    float n100 = skyHash31(cell + vec3(1.0, 0.0, 0.0));
    float n010 = skyHash31(cell + vec3(0.0, 1.0, 0.0));
    float n110 = skyHash31(cell + vec3(1.0, 1.0, 0.0));
    float n001 = skyHash31(cell + vec3(0.0, 0.0, 1.0));
    float n101 = skyHash31(cell + vec3(1.0, 0.0, 1.0));
    float n011 = skyHash31(cell + vec3(0.0, 1.0, 1.0));
    float n111 = skyHash31(cell + vec3(1.0, 1.0, 1.0));
    float x00 = mix(n000, n100, weight.x);
    float x10 = mix(n010, n110, weight.x);
    float x01 = mix(n001, n101, weight.x);
    float x11 = mix(n011, n111, weight.x);
    return mix(mix(x00, x10, weight.y), mix(x01, x11, weight.y), weight.z);
}

float skyFractal(vec3 point, int octaves) {
    float total = 0.0;
    float amplitude = 0.5;
    float normalization = 0.0;
    for (int index = 0; index < octaves; ++index) {
        total += skyValueNoise(point) * amplitude;
        normalization += amplitude;
        point *= 2.03;
        amplitude *= 0.5;
    }
    return total / max(normalization, 1e-4);
}

vec3 starLayer(vec3 direction, float cellScale, float density, float brightness, float seedOffset) {
    vec3 scaled = direction * cellScale;
    vec3 cell = floor(scaled);
    vec3 local = fract(scaled);
    vec3 accumulated = vec3(0.0);
    for (int z = -1; z <= 1; ++z) {
        for (int y = -1; y <= 1; ++y) {
            for (int x = -1; x <= 1; ++x) {
                vec3 offset = vec3(float(x), float(y), float(z));
                vec3 neighbour = cell + offset;
                vec3 random = skyHash33(neighbour + seedOffset);
                if (random.z > density) continue;
                vec3 starPosition = offset + random - local;
                float distanceToStar = length(starPosition);
                float core = exp(-distanceToStar * distanceToStar * 900.0);
                float halo = exp(-distanceToStar * distanceToStar * 42.0) * 0.06;
                float magnitude = pow(skyHash11(random.x * 91.7 + random.y * 13.1), 5.0);
                float temperature = mix(2600.0, 19000.0, pow(random.y, 1.7));
                vec3 tint = blackBodyRadiance(temperature, 1.0);
                accumulated += tint * (core + halo) * magnitude * brightness;
            }
        }
    }
    return accumulated;
}

vec3 nebulaField(vec3 direction, float time, int detail) {
    vec3 warp = direction * 2.6 + vec3(11.3, 4.7, 21.9);
    int coarseOctaves = detail >= 2 ? 5 : 3;
    int fineOctaves = detail >= 2 ? 4 : 2;
    float lowFrequency = skyFractal(warp * 1.1, coarseOctaves);
    float highFrequency = skyFractal(warp * 4.3 + vec3(lowFrequency * 2.0), fineOctaves);
    float mask = smoothstep(0.42, 0.86, lowFrequency * 0.65 + highFrequency * 0.45);

    vec3 emissionRed = vec3(0.62, 0.11, 0.16) * pow(highFrequency, 1.6);
    vec3 emissionTeal = vec3(0.06, 0.34, 0.44) * pow(lowFrequency, 2.1);
    vec3 emissionGold = detail >= 2
        ? vec3(0.42, 0.27, 0.07) * pow(skyFractal(warp * 2.2 + 7.0, 3), 3.0)
        : vec3(0.0);
    float breathing = 0.94 + 0.06 * sin(time * 0.05 + lowFrequency * 6.0);
    return (emissionRed + emissionTeal + emissionGold) * mask * breathing * 0.30;
}

vec3 galacticPlane(vec3 direction, int detail) {
    float height = abs(direction.y);
    float band = exp(-height * height * 34.0);
    float structure = skyFractal(direction * 7.0 + vec3(3.1, 0.0, 9.4), detail >= 2 ? 5 : 3);
    float dustLane = detail >= 2 ? smoothstep(0.30, 0.72, skyFractal(direction * 13.0 + 21.0, 4)) : 0.0;
    vec3 core = vec3(0.52, 0.44, 0.34) * band * structure;
    return core * (1.0 - dustLane * 0.72) * 0.34;
}

vec3 sampleDeepSky(vec3 direction, float time, int detail) {
    vec3 result = vec3(0.0);
    result += starLayer(direction, 220.0, 0.14, 5.2, 0.0);
    if (detail >= 1) result += starLayer(direction, 96.0, 0.10, 12.0, 37.0);
    if (detail >= 2) result += starLayer(direction, 42.0, 0.06, 26.0, 91.0);
    result += galacticPlane(direction, detail);
    if (detail >= 1) result += nebulaField(direction, time, detail);
    return result;
}

vec3 applySpectralShift(vec3 color, float shiftFactor) {
    float warmth = clamp(shiftFactor, 0.15, 6.0);
    vec3 weights = vec3(1.0 / warmth, 1.0, warmth);
    weights /= max(dot(weights, vec3(0.2126, 0.7152, 0.0722)), 1e-4);
    float intensity = pow(shiftFactor, 4.0);
    return color * weights * intensity;
}
)GLSL";

}
