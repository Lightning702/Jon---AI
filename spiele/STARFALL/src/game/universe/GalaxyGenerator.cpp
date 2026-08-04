#include "GalaxyGenerator.hpp"

#include "../../engine/math/Noise.hpp"
#include "../../engine/math/Scalar.hpp"

namespace sf {

GalaxyProfile GalaxyGenerator::generate(const UniverseSeed& universe, u32 galaxyIndex) const {
    const u64 seed = universe.galaxySeed(galaxyIndex);
    Random random(seed);

    GalaxyProfile galaxy;
    galaxy.index = galaxyIndex;
    galaxy.seed = seed;
    galaxy.hostsVoidHeart = galaxyIndex == 0;
    galaxy.name = galaxyIndex == 0 ? std::string("AURELIA") : generateName(seed, NameCulture::Human, 2, 4);

    if (galaxyIndex == 0) {
        galaxy.type = GalaxyType::BarredSpiral;
    } else {
        const f64 roll = random.nextDouble();
        if (roll < 0.34) galaxy.type = GalaxyType::Spiral;
        else if (roll < 0.60) galaxy.type = GalaxyType::BarredSpiral;
        else if (roll < 0.76) galaxy.type = GalaxyType::Elliptical;
        else if (roll < 0.88) galaxy.type = GalaxyType::Irregular;
        else if (roll < 0.95) galaxy.type = GalaxyType::Ring;
        else galaxy.type = GalaxyType::Dwarf;
    }

    switch (galaxy.type) {
        case GalaxyType::Dwarf:
            galaxy.radiusLightYears = random.rangeDouble(3000.0, 12000.0);
            galaxy.thicknessLightYears = galaxy.radiusLightYears * random.rangeDouble(0.30, 0.60);
            galaxy.estimatedStarCount = random.rangeDouble(2.0e8, 4.0e9);
            break;
        case GalaxyType::Elliptical:
            galaxy.radiusLightYears = random.rangeDouble(24000.0, 160000.0);
            galaxy.thicknessLightYears = galaxy.radiusLightYears * random.rangeDouble(0.55, 0.92);
            galaxy.estimatedStarCount = random.rangeDouble(6.0e10, 1.2e12);
            break;
        default:
            galaxy.radiusLightYears = random.rangeDouble(28000.0, 92000.0);
            galaxy.thicknessLightYears = random.rangeDouble(600.0, 2400.0);
            galaxy.estimatedStarCount = random.rangeDouble(4.0e10, 6.0e11);
            break;
    }

    galaxy.armCount = static_cast<u32>(random.rangeInt(2, 7));
    galaxy.armWindingTightness = random.rangeDouble(0.14, 0.36);
    galaxy.coreRadiusLightYears = galaxy.radiusLightYears * random.rangeDouble(0.05, 0.14);
    galaxy.barLengthLightYears = galaxy.type == GalaxyType::BarredSpiral
                                     ? galaxy.radiusLightYears * random.rangeDouble(0.10, 0.24)
                                     : 0.0;
    galaxy.coreMetallicity = random.rangeDouble(0.7, 1.3);
    galaxy.haloDensity = random.rangeDouble(0.01, 0.09);

    galaxy.coreColor = Vec3(static_cast<f32>(random.rangeDouble(0.9, 1.0)),
                            static_cast<f32>(random.rangeDouble(0.72, 0.92)),
                            static_cast<f32>(random.rangeDouble(0.48, 0.74)));
    galaxy.armColor = Vec3(static_cast<f32>(random.rangeDouble(0.42, 0.72)),
                           static_cast<f32>(random.rangeDouble(0.58, 0.86)),
                           static_cast<f32>(random.rangeDouble(0.80, 1.0)));
    galaxy.dustColor = Vec3(static_cast<f32>(random.rangeDouble(0.18, 0.36)),
                            static_cast<f32>(random.rangeDouble(0.10, 0.24)),
                            static_cast<f32>(random.rangeDouble(0.06, 0.18)));
    return galaxy;
}

f64 GalaxyGenerator::stellarDensity(const GalaxyProfile& galaxy, const DVec3& positionLightYears) {
    const f64 planarRadius = std::sqrt(positionLightYears.x * positionLightYears.x +
                                       positionLightYears.z * positionLightYears.z);
    if (planarRadius > galaxy.radiusLightYears * 1.4) return 0.0;

    const f64 verticalFalloff = std::exp(-std::fabs(positionLightYears.y) /
                                         maxValue(galaxy.thicknessLightYears * 0.5, 1.0));
    const f64 coreBulge = std::exp(-planarRadius / maxValue(galaxy.coreRadiusLightYears, 1.0));
    const f64 diskFalloff = std::exp(-planarRadius / maxValue(galaxy.radiusLightYears * 0.32, 1.0));

    f64 structure = 0.0;
    switch (galaxy.type) {
        case GalaxyType::Elliptical:
            structure = coreBulge * 2.4 + diskFalloff * 0.6;
            break;
        case GalaxyType::Ring: {
            const f64 ringCenter = galaxy.radiusLightYears * 0.62;
            const f64 ringWidth = galaxy.radiusLightYears * 0.16;
            const f64 offset = (planarRadius - ringCenter) / ringWidth;
            structure = std::exp(-offset * offset) * 2.2 + coreBulge * 0.8;
            break;
        }
        case GalaxyType::Irregular: {
            const f64 clumps = fractalNoise3(galaxy.seed, positionLightYears / (galaxy.radiusLightYears * 0.12),
                                             FractalSettings());
            structure = diskFalloff * (0.6 + clumps * 1.4);
            break;
        }
        case GalaxyType::Dwarf:
            structure = coreBulge * 1.6 + diskFalloff * 0.8;
            break;
        default: {
            const f64 azimuth = std::atan2(positionLightYears.z, positionLightYears.x);
            const f64 spiralPhase = azimuth - std::log(maxValue(planarRadius, 1.0)) / galaxy.armWindingTightness;
            const f64 armWave = std::cos(spiralPhase * static_cast<f64>(galaxy.armCount));
            const f64 armStrength = std::pow(clampValue(armWave * 0.5 + 0.5, 0.0, 1.0), 2.4);
            f64 barBoost = 0.0;
            if (galaxy.barLengthLightYears > 0.0 && planarRadius < galaxy.barLengthLightYears) {
                const f64 barAlignment = std::fabs(std::cos(azimuth));
                barBoost = std::pow(barAlignment, 6.0) * 1.6;
            }
            structure = diskFalloff * (0.35 + armStrength * 1.55) + coreBulge * 1.8 + barBoost;
            break;
        }
    }

    const f64 halo = galaxy.haloDensity * std::exp(-planarRadius / maxValue(galaxy.radiusLightYears, 1.0));
    return clampValue(structure * verticalFalloff + halo, 0.0, 4.0);
}

bool GalaxyGenerator::sampleStarAt(const GalaxyProfile& galaxy, const SystemCoord& coordinate) {
    const DVec3 position(static_cast<f64>(coordinate.x), static_cast<f64>(coordinate.y),
                         static_cast<f64>(coordinate.z));
    const f64 density = stellarDensity(galaxy, position);
    if (density <= 0.0) return false;
    const u64 hash = hashCoordinate(galaxy.seed, coordinate.x, coordinate.y, coordinate.z);
    const f64 roll = static_cast<f64>(hash >> 11) * (1.0 / 9007199254740992.0);
    return roll < clampValue(density * 0.26, 0.0, 0.92);
}

std::vector<SystemCoord> GalaxyGenerator::sampleNeighbourhood(const GalaxyProfile& galaxy, const SystemCoord& center,
                                                              i64 radiusLightYears, usize maximumCount) {
    std::vector<SystemCoord> results;
    if (radiusLightYears <= 0) return results;
    const i64 squaredLimit = radiusLightYears * radiusLightYears;

    for (i64 offsetZ = -radiusLightYears; offsetZ <= radiusLightYears; ++offsetZ) {
        for (i64 offsetY = -radiusLightYears; offsetY <= radiusLightYears; ++offsetY) {
            for (i64 offsetX = -radiusLightYears; offsetX <= radiusLightYears; ++offsetX) {
                if (offsetX * offsetX + offsetY * offsetY + offsetZ * offsetZ > squaredLimit) continue;
                SystemCoord candidate;
                candidate.x = center.x + offsetX;
                candidate.y = center.y + offsetY;
                candidate.z = center.z + offsetZ;
                if (!sampleStarAt(galaxy, candidate)) continue;
                results.push_back(candidate);
                if (results.size() >= maximumCount) return results;
            }
        }
    }
    return results;
}

const char* GalaxyGenerator::galaxyTypeName(GalaxyType value) {
    switch (value) {
        case GalaxyType::Spiral: return "Spiralgalaxie";
        case GalaxyType::BarredSpiral: return "Balkenspirale";
        case GalaxyType::Elliptical: return "Elliptisch";
        case GalaxyType::Irregular: return "Irregulaer";
        case GalaxyType::Ring: return "Ringgalaxie";
        case GalaxyType::Dwarf: return "Zwerggalaxie";
        default: return "Unbekannt";
    }
}

}
