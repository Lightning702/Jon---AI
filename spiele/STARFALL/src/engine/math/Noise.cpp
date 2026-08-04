#include "Noise.hpp"

#include "Random.hpp"
#include "Scalar.hpp"

#include <cmath>

namespace sf {
namespace {

i64 floorToInt(f64 value) {
    const i64 truncated = static_cast<i64>(value);
    return value < static_cast<f64>(truncated) ? truncated - 1 : truncated;
}

f64 unitFromHash(u64 hash) {
    return static_cast<f64>(hash >> 11) * (1.0 / 9007199254740992.0);
}

f64 signedFromHash(u64 hash) {
    return unitFromHash(hash) * 2.0 - 1.0;
}

DVec3 gradientFromHash(u64 hash) {
    const f64 z = signedFromHash(hash);
    const f64 angle = unitFromHash(splitMix64(hash)) * kTwoPiDouble;
    const f64 planar = std::sqrt(maxValue(0.0, 1.0 - z * z));
    return DVec3(planar * std::cos(angle), planar * std::sin(angle), z);
}

f64 quinticFade(f64 t) {
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

}

f64 valueNoise3(u64 seed, const DVec3& position) {
    const i64 cellX = floorToInt(position.x);
    const i64 cellY = floorToInt(position.y);
    const i64 cellZ = floorToInt(position.z);
    const f64 fractionX = quinticFade(position.x - static_cast<f64>(cellX));
    const f64 fractionY = quinticFade(position.y - static_cast<f64>(cellY));
    const f64 fractionZ = quinticFade(position.z - static_cast<f64>(cellZ));

    f64 corners[8];
    for (u32 index = 0; index < 8; ++index) {
        const i64 offsetX = cellX + static_cast<i64>(index & 1u);
        const i64 offsetY = cellY + static_cast<i64>((index >> 1) & 1u);
        const i64 offsetZ = cellZ + static_cast<i64>((index >> 2) & 1u);
        corners[index] = signedFromHash(hashCoordinate(seed, offsetX, offsetY, offsetZ));
    }

    const f64 x00 = mixValue(corners[0], corners[1], fractionX);
    const f64 x10 = mixValue(corners[2], corners[3], fractionX);
    const f64 x01 = mixValue(corners[4], corners[5], fractionX);
    const f64 x11 = mixValue(corners[6], corners[7], fractionX);
    const f64 y0 = mixValue(x00, x10, fractionY);
    const f64 y1 = mixValue(x01, x11, fractionY);
    return mixValue(y0, y1, fractionZ);
}

f64 gradientNoise3(u64 seed, const DVec3& position) {
    const i64 cellX = floorToInt(position.x);
    const i64 cellY = floorToInt(position.y);
    const i64 cellZ = floorToInt(position.z);
    const f64 localX = position.x - static_cast<f64>(cellX);
    const f64 localY = position.y - static_cast<f64>(cellY);
    const f64 localZ = position.z - static_cast<f64>(cellZ);
    const f64 fadeX = quinticFade(localX);
    const f64 fadeY = quinticFade(localY);
    const f64 fadeZ = quinticFade(localZ);

    f64 corners[8];
    for (u32 index = 0; index < 8; ++index) {
        const i64 stepX = static_cast<i64>(index & 1u);
        const i64 stepY = static_cast<i64>((index >> 1) & 1u);
        const i64 stepZ = static_cast<i64>((index >> 2) & 1u);
        const DVec3 gradient = gradientFromHash(hashCoordinate(seed, cellX + stepX, cellY + stepY, cellZ + stepZ));
        const DVec3 offset(localX - static_cast<f64>(stepX), localY - static_cast<f64>(stepY),
                           localZ - static_cast<f64>(stepZ));
        corners[index] = dot(gradient, offset);
    }

    const f64 x00 = mixValue(corners[0], corners[1], fadeX);
    const f64 x10 = mixValue(corners[2], corners[3], fadeX);
    const f64 x01 = mixValue(corners[4], corners[5], fadeX);
    const f64 x11 = mixValue(corners[6], corners[7], fadeX);
    const f64 y0 = mixValue(x00, x10, fadeY);
    const f64 y1 = mixValue(x01, x11, fadeY);
    return mixValue(y0, y1, fadeZ) * 1.1547;
}

f64 simplexNoise3(u64 seed, const DVec3& position) {
    constexpr f64 skewFactor = 1.0 / 3.0;
    constexpr f64 unskewFactor = 1.0 / 6.0;

    const f64 skew = (position.x + position.y + position.z) * skewFactor;
    const i64 baseX = floorToInt(position.x + skew);
    const i64 baseY = floorToInt(position.y + skew);
    const i64 baseZ = floorToInt(position.z + skew);
    const f64 unskew = static_cast<f64>(baseX + baseY + baseZ) * unskewFactor;
    const f64 originX = static_cast<f64>(baseX) - unskew;
    const f64 originY = static_cast<f64>(baseY) - unskew;
    const f64 originZ = static_cast<f64>(baseZ) - unskew;
    const f64 x0 = position.x - originX;
    const f64 y0 = position.y - originY;
    const f64 z0 = position.z - originZ;

    i64 offset1X, offset1Y, offset1Z;
    i64 offset2X, offset2Y, offset2Z;
    if (x0 >= y0) {
        if (y0 >= z0) { offset1X = 1; offset1Y = 0; offset1Z = 0; offset2X = 1; offset2Y = 1; offset2Z = 0; }
        else if (x0 >= z0) { offset1X = 1; offset1Y = 0; offset1Z = 0; offset2X = 1; offset2Y = 0; offset2Z = 1; }
        else { offset1X = 0; offset1Y = 0; offset1Z = 1; offset2X = 1; offset2Y = 0; offset2Z = 1; }
    } else {
        if (y0 < z0) { offset1X = 0; offset1Y = 0; offset1Z = 1; offset2X = 0; offset2Y = 1; offset2Z = 1; }
        else if (x0 < z0) { offset1X = 0; offset1Y = 1; offset1Z = 0; offset2X = 0; offset2Y = 1; offset2Z = 1; }
        else { offset1X = 0; offset1Y = 1; offset1Z = 0; offset2X = 1; offset2Y = 1; offset2Z = 0; }
    }

    const f64 x1 = x0 - static_cast<f64>(offset1X) + unskewFactor;
    const f64 y1 = y0 - static_cast<f64>(offset1Y) + unskewFactor;
    const f64 z1 = z0 - static_cast<f64>(offset1Z) + unskewFactor;
    const f64 x2 = x0 - static_cast<f64>(offset2X) + 2.0 * unskewFactor;
    const f64 y2 = y0 - static_cast<f64>(offset2Y) + 2.0 * unskewFactor;
    const f64 z2 = z0 - static_cast<f64>(offset2Z) + 2.0 * unskewFactor;
    const f64 x3 = x0 - 1.0 + 3.0 * unskewFactor;
    const f64 y3 = y0 - 1.0 + 3.0 * unskewFactor;
    const f64 z3 = z0 - 1.0 + 3.0 * unskewFactor;

    const DVec3 corners[4] = {DVec3(x0, y0, z0), DVec3(x1, y1, z1), DVec3(x2, y2, z2), DVec3(x3, y3, z3)};
    const i64 cells[4][3] = {
        {baseX, baseY, baseZ},
        {baseX + offset1X, baseY + offset1Y, baseZ + offset1Z},
        {baseX + offset2X, baseY + offset2Y, baseZ + offset2Z},
        {baseX + 1, baseY + 1, baseZ + 1}};

    f64 total = 0.0;
    for (u32 index = 0; index < 4; ++index) {
        f64 attenuation = 0.6 - lengthSquared(corners[index]);
        if (attenuation <= 0.0) continue;
        attenuation *= attenuation;
        const DVec3 gradient = gradientFromHash(hashCoordinate(seed, cells[index][0], cells[index][1], cells[index][2]));
        total += attenuation * attenuation * dot(gradient, corners[index]);
    }
    return clampValue(total * 32.0, -1.0, 1.0);
}

f64 fractalNoise3(u64 seed, const DVec3& position, const FractalSettings& settings) {
    f64 total = 0.0;
    f64 amplitude = settings.amplitude;
    f64 frequency = settings.frequency;
    f64 normalization = 0.0;
    for (u32 octave = 0; octave < settings.octaves; ++octave) {
        total += simplexNoise3(hashCombine(seed, octave), position * frequency) * amplitude;
        normalization += amplitude;
        amplitude *= settings.gain;
        frequency *= settings.lacunarity;
    }
    return normalization > 0.0 ? total / normalization : 0.0;
}

f64 ridgedMultifractal3(u64 seed, const DVec3& position, const FractalSettings& settings) {
    f64 total = 0.0;
    f64 amplitude = settings.amplitude;
    f64 frequency = settings.frequency;
    f64 normalization = 0.0;
    f64 weight = 1.0;
    for (u32 octave = 0; octave < settings.octaves; ++octave) {
        f64 sample = simplexNoise3(hashCombine(seed, octave + 977u), position * frequency);
        sample = 1.0 - std::fabs(sample);
        sample *= sample;
        sample *= weight;
        weight = clampValue(sample * 2.0, 0.0, 1.0);
        total += sample * amplitude;
        normalization += amplitude;
        amplitude *= settings.gain;
        frequency *= settings.lacunarity;
    }
    return normalization > 0.0 ? (total / normalization) * 2.0 - 1.0 : 0.0;
}

f64 billowNoise3(u64 seed, const DVec3& position, const FractalSettings& settings) {
    f64 total = 0.0;
    f64 amplitude = settings.amplitude;
    f64 frequency = settings.frequency;
    f64 normalization = 0.0;
    for (u32 octave = 0; octave < settings.octaves; ++octave) {
        const f64 sample = std::fabs(simplexNoise3(hashCombine(seed, octave + 5471u), position * frequency));
        total += (sample * 2.0 - 1.0) * amplitude;
        normalization += amplitude;
        amplitude *= settings.gain;
        frequency *= settings.lacunarity;
    }
    return normalization > 0.0 ? total / normalization : 0.0;
}

DVec3 domainWarp3(u64 seed, const DVec3& position, f64 strength, f64 frequency) {
    const DVec3 scaled = position * frequency;
    const f64 warpX = simplexNoise3(hashCombine(seed, 0x1111u), scaled);
    const f64 warpY = simplexNoise3(hashCombine(seed, 0x2222u), scaled + DVec3(31.7, 17.3, 5.1));
    const f64 warpZ = simplexNoise3(hashCombine(seed, 0x3333u), scaled + DVec3(-13.9, 47.1, 23.7));
    return position + DVec3(warpX, warpY, warpZ) * strength;
}

WorleyResult worleyNoise3(u64 seed, const DVec3& position) {
    WorleyResult result;
    result.nearestDistance = 1.0e30;
    result.secondDistance = 1.0e30;

    const i64 baseX = floorToInt(position.x);
    const i64 baseY = floorToInt(position.y);
    const i64 baseZ = floorToInt(position.z);

    for (i64 offsetZ = -1; offsetZ <= 1; ++offsetZ) {
        for (i64 offsetY = -1; offsetY <= 1; ++offsetY) {
            for (i64 offsetX = -1; offsetX <= 1; ++offsetX) {
                const i64 cellX = baseX + offsetX;
                const i64 cellY = baseY + offsetY;
                const i64 cellZ = baseZ + offsetZ;
                const u64 cellHash = hashCoordinate(seed, cellX, cellY, cellZ);
                const DVec3 feature(static_cast<f64>(cellX) + unitFromHash(cellHash),
                                    static_cast<f64>(cellY) + unitFromHash(splitMix64(cellHash)),
                                    static_cast<f64>(cellZ) + unitFromHash(splitMix64(cellHash + 7919ull)));
                const f64 distanceToFeature = length(feature - position);
                if (distanceToFeature < result.nearestDistance) {
                    result.secondDistance = result.nearestDistance;
                    result.nearestDistance = distanceToFeature;
                    result.cellHash = cellHash;
                    result.featurePoint = feature;
                } else if (distanceToFeature < result.secondDistance) {
                    result.secondDistance = distanceToFeature;
                }
            }
        }
    }
    return result;
}

f64 worleyNearestDistance(u64 seed, const DVec3& position) {
    const i64 baseX = floorToInt(position.x);
    const i64 baseY = floorToInt(position.y);
    const i64 baseZ = floorToInt(position.z);
    f64 nearest = 1.0e30;

    for (i64 offsetZ = -1; offsetZ <= 1; ++offsetZ) {
        for (i64 offsetY = -1; offsetY <= 1; ++offsetY) {
            for (i64 offsetX = -1; offsetX <= 1; ++offsetX) {
                const i64 cellX = baseX + offsetX;
                const i64 cellY = baseY + offsetY;
                const i64 cellZ = baseZ + offsetZ;
                const u64 cellHash = hashCoordinate(seed, cellX, cellY, cellZ);
                const DVec3 feature(static_cast<f64>(cellX) + unitFromHash(cellHash),
                                    static_cast<f64>(cellY) + unitFromHash(splitMix64(cellHash)),
                                    static_cast<f64>(cellZ) + unitFromHash(splitMix64(cellHash + 7919ull)));
                nearest = minValue(nearest, lengthSquared(feature - position));
            }
        }
    }
    return std::sqrt(nearest);
}

f64 craterField(u64 seed, const DVec3& unitDirection, f64 density, f64 depth, u32 layers) {
    f64 total = 0.0;
    f64 scale = density;
    f64 weight = depth;
    for (u32 layer = 0; layer < layers; ++layer) {
        const WorleyResult cells = worleyNoise3(hashCombine(seed, layer + 811u), unitDirection * scale);
        const f64 radius = 0.28 + unitFromHash(cells.cellHash) * 0.30;
        const f64 normalized = cells.nearestDistance / radius;
        if (normalized < 1.0) {
            const f64 rim = std::cos(normalized * kPiDouble);
            const f64 profile = normalized < 0.72 ? -rim * 0.6 - 0.35 : (1.0 - normalized) * 2.4;
            total += profile * weight;
        }
        scale *= 2.31;
        weight *= 0.52;
    }
    return total;
}

}
