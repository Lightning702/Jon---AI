#include "PlanetBody.hpp"

#include "../../engine/math/Noise.hpp"
#include "../../engine/math/Scalar.hpp"

namespace sf {

void PlanetBody::configure(const PlanetProfile& profile, const DVec3& systemLocalPosition) {
    planet = profile;
    centerPosition = systemLocalPosition;
    amplitude = planet.radiusMeters * 0.0022 * (0.45 + planet.mountainRuggedness);
    atmosphereThickness = maxValue(planet.atmosphereScaleHeightMeters * 7.0, 2000.0);
    gravitationalParameter = kGravitationalConstant * planet.massKilograms;
}

f64 PlanetBody::elevationAt(const DVec3& unitDirection) const {
    return PlanetGenerator::surfaceHeightAt(planet, unitDirection) * amplitude;
}

f64 PlanetBody::radiusAt(const DVec3& unitDirection) const {
    const f64 elevation = elevationAt(unitDirection);
    if (planet.waterFraction > 0.02 && elevation < 0.0) return planet.radiusMeters;
    return planet.radiusMeters + elevation;
}

DVec3 PlanetBody::surfacePoint(const DVec3& unitDirection) const {
    return centerPosition + unitDirection * radiusAt(unitDirection);
}

DVec3 PlanetBody::upAt(const DVec3& localPosition) const {
    const DVec3 offset = localPosition - centerPosition;
    const f64 distance = length(offset);
    return distance > 0.0 ? offset / distance : DVec3::unitY();
}

f64 PlanetBody::altitudeAt(const DVec3& localPosition) const {
    const DVec3 offset = localPosition - centerPosition;
    const f64 distance = length(offset);
    if (distance <= 0.0) return -planet.radiusMeters;
    return distance - radiusAt(offset / distance);
}

f64 PlanetBody::gravityMagnitudeAt(f64 radius) const {
    const f64 safeRadius = maxValue(radius, planet.radiusMeters * 0.05);
    if (safeRadius < planet.radiusMeters) {
        return gravitationalParameter * safeRadius / (planet.radiusMeters * planet.radiusMeters * planet.radiusMeters);
    }
    return gravitationalParameter / (safeRadius * safeRadius);
}

DVec3 PlanetBody::gravityAt(const DVec3& localPosition) const {
    const DVec3 offset = localPosition - centerPosition;
    const f64 distance = length(offset);
    if (distance <= 0.0) return DVec3::zero();
    return offset / distance * (-gravityMagnitudeAt(distance));
}

f64 PlanetBody::atmosphericDensityAt(f64 altitudeMeters) const {
    if (planet.atmospherePressureBar <= 0.0001) return 0.0;
    const f64 surfaceDensity = 1.225 * planet.atmospherePressureBar;
    if (altitudeMeters < 0.0) return surfaceDensity;
    return surfaceDensity * std::exp(-altitudeMeters / maxValue(planet.atmosphereScaleHeightMeters, 1.0));
}

f64 PlanetBody::rotationPhase(f64 universeSeconds) const {
    const f64 period = maxValue(planet.rotationPeriodSeconds, 1.0);
    return std::fmod(universeSeconds / period, 1.0) * kTwoPiDouble;
}

DVec3 PlanetBody::sunDirectionAt(const DVec3& unitDirection, f64 universeSeconds,
                                 const DVec3& starLocalPosition) const {
    const DVec3 toStar = starLocalPosition - centerPosition;
    const f64 distance = length(toStar);
    if (distance <= 0.0) return DVec3::unitY();
    const DVec3 fixedDirection = toStar / distance;

    const f64 phase = rotationPhase(universeSeconds);
    const f64 cosinePhase = std::cos(-phase);
    const f64 sinePhase = std::sin(-phase);
    const DVec3 rotated(fixedDirection.x * cosinePhase - fixedDirection.z * sinePhase, fixedDirection.y,
                        fixedDirection.x * sinePhase + fixedDirection.z * cosinePhase);

    const f64 tilt = planet.axialTiltRadians;
    const f64 cosineTilt = std::cos(tilt);
    const f64 sineTilt = std::sin(tilt);
    const DVec3 tilted(rotated.x * cosineTilt - rotated.y * sineTilt, rotated.x * sineTilt + rotated.y * cosineTilt,
                       rotated.z);
    (void)unitDirection;
    return normalize(tilted);
}

f64 PlanetBody::sunElevationAt(const DVec3& unitDirection, f64 universeSeconds,
                               const DVec3& starLocalPosition) const {
    if (planet.features.tidallyLocked) {
        const DVec3 toStar = normalize(starLocalPosition - centerPosition);
        return dot(unitDirection, toStar);
    }
    return dot(unitDirection, sunDirectionAt(unitDirection, universeSeconds, starLocalPosition));
}

DVec3 PlanetBody::surfaceNormal(const DVec3& unitDirection, f64 sampleDistanceMeters) const {
    const DVec3 reference = std::fabs(unitDirection.y) < 0.9 ? DVec3::unitY() : DVec3::unitX();
    const DVec3 tangent = normalize(cross(reference, unitDirection));
    const DVec3 bitangent = cross(unitDirection, tangent);
    const f64 step = sampleDistanceMeters / maxValue(planet.radiusMeters, 1.0);

    const DVec3 forwardDirection = normalize(unitDirection + tangent * step);
    const DVec3 backwardDirection = normalize(unitDirection - tangent * step);
    const DVec3 rightDirection = normalize(unitDirection + bitangent * step);
    const DVec3 leftDirection = normalize(unitDirection - bitangent * step);

    const DVec3 forwardPoint = forwardDirection * radiusAt(forwardDirection);
    const DVec3 backwardPoint = backwardDirection * radiusAt(backwardDirection);
    const DVec3 rightPoint = rightDirection * radiusAt(rightDirection);
    const DVec3 leftPoint = leftDirection * radiusAt(leftDirection);

    const DVec3 normalVector = cross(forwardPoint - backwardPoint, rightPoint - leftPoint);
    const f64 magnitude = length(normalVector);
    if (magnitude <= 0.0) return unitDirection;
    const DVec3 candidate = normalVector / magnitude;
    return dot(candidate, unitDirection) < 0.0 ? candidate * -1.0 : candidate;
}

SurfaceSample PlanetBody::sampleSurface(const DVec3& unitDirection, f64 dayPhase) const {
    const f64 elevation = elevationAt(unitDirection);
    const DVec3 normalVector = surfaceNormal(unitDirection, 60.0);
    const f64 slope = clampValue(1.0 - dot(normalVector, unitDirection), 0.0, 1.0) * 6.0;
    return sampleSurfaceWithElevation(unitDirection, dayPhase, elevation, slope);
}

SurfaceSample PlanetBody::sampleSurfaceWithElevation(const DVec3& unitDirection, f64 dayPhase, f64 elevationMeters,
                                                     f64 slope) const {
    SurfaceSample sample;
    sample.elevationMeters = elevationMeters;
    sample.radiusMeters = planet.radiusMeters + sample.elevationMeters;
    sample.underWater = planet.waterFraction > 0.02 && sample.elevationMeters < 0.0;

    const f64 latitude = std::fabs(unitDirection.y);
    const f64 elevationFraction = clampValue(sample.elevationMeters / maxValue(amplitude, 1.0), -1.0, 1.0);

    const f64 latitudeCooling = latitude * latitude * 46.0;
    const f64 altitudeCooling = maxValue(sample.elevationMeters, 0.0) * 0.0062;
    const f64 dayVariation = std::cos(dayPhase * kTwoPiDouble) * planet.temperatureAmplitudeKelvin * 0.5;
    sample.temperatureKelvin = planet.meanSurfaceTemperatureKelvin - latitudeCooling - altitudeCooling + dayVariation;

    FractalSettings moisture;
    moisture.octaves = 4;
    moisture.frequency = 2.4;
    const f64 humidityNoise = fractalNoise3(planet.seed ^ 0x484D44ull, unitDirection, moisture) * 0.5 + 0.5;
    sample.precipitation = clampValue(humidityNoise * (0.25 + planet.waterFraction * 1.5) *
                                          clampValue(planet.atmospherePressureBar, 0.0, 1.6),
                                      0.0, 1.0);

    sample.slope = clampValue(slope, 0.0, 6.0);
    sample.biome = PlanetGenerator::classifyBiome(sample.temperatureKelvin, sample.precipitation, elevationFraction,
                                                  sample.slope, planet);
    sample.albedo = biomeAlbedo(sample.biome, planet);
    return sample;
}

f64 PlanetBody::radiationAt(const DVec3& unitDirection, f64 dayPhase) const {
    const f64 shielding = 1.0 / (1.0 + planet.magneticFieldTesla * 3.0e4) /
                          (1.0 + planet.atmospherePressureBar * 1.4);
    const f64 daySide = clampValue(std::cos(dayPhase * kTwoPiDouble) * 0.5 + 0.5, 0.0, 1.0);
    const f64 polarBoost = 1.0 + std::fabs(unitDirection.y) * 0.4;
    return planet.radiationLevelSieverts * shielding * polarBoost * (0.35 + daySide * 0.65) * 4.0;
}

f64 PlanetBody::toxicityAt(const DVec3& unitDirection) const {
    FractalSettings settings;
    settings.octaves = 3;
    settings.frequency = 3.1;
    const f64 patch = fractalNoise3(planet.seed ^ 0x544F58ull, unitDirection, settings) * 0.5 + 0.5;
    const f64 base = planet.methaneFraction * 1.6 + planet.carbonDioxideFraction * 0.5;
    return clampValue(base * (0.4 + patch), 0.0, 2.0);
}

f64 PlanetBody::resourceRichness(const DVec3& unitDirection, ItemId resource) const {
    u64 salt = 0;
    f64 base = 0.0;
    f64 frequency = 5.0;

    switch (resource) {
        case ItemId::Ferrite: salt = 0x464552ull; base = 0.85; frequency = 3.2; break;
        case ItemId::Silicate: salt = 0x53494Cull; base = 0.7; frequency = 3.6; break;
        case ItemId::Carbon: salt = 0x434152ull; base = 0.35 + planet.vegetationDensity * 0.7; frequency = 4.4; break;
        case ItemId::Copper: salt = 0x435550ull; base = planet.metalAbundance * 0.6; frequency = 7.5; break;
        case ItemId::Cobalt: salt = 0x434F42ull; base = planet.metalAbundance * 0.5; frequency = 8.1; break;
        case ItemId::Sulphur: salt = 0x53554Cull; base = planet.volcanism * 0.8; frequency = 6.4; break;
        case ItemId::Phosphor: salt = 0x50484Full; base = planet.biosphereLevel * 0.6; frequency = 6.9; break;
        case ItemId::Uranite: salt = 0x555241ull; base = planet.radiationLevelSieverts * 0.4; frequency = 9.2; break;
        case ItemId::Platinum: salt = 0x504C41ull; base = planet.metalAbundance * 0.22; frequency = 11.0; break;
        case ItemId::Gold: salt = 0x474F4Cull; base = planet.metalAbundance * 0.20; frequency = 11.7; break;
        case ItemId::IceCrystal: salt = 0x494345ull; base = clampValue((263.0 - planet.meanSurfaceTemperatureKelvin) / 60.0, 0.0, 1.0); frequency = 5.2; break;
        case ItemId::SaltCrystal: salt = 0x53414Cull; base = clampValue(planet.waterFraction * 0.9, 0.0, 1.0); frequency = 5.8; break;
        case ItemId::Deuterium: salt = 0x444555ull; base = planet.fuelAbundance * 0.5; frequency = 8.8; break;
        case ItemId::Oxygen: salt = 0x4F5859ull; base = planet.oxygenFraction * 2.4; frequency = 4.9; break;
        default: return 0.0;
    }
    if (base <= 0.0) return 0.0;

    FractalSettings settings;
    settings.octaves = 3;
    settings.frequency = frequency;
    const f64 field = fractalNoise3(planet.seed ^ salt, unitDirection, settings) * 0.5 + 0.5;
    return clampValue(base * std::pow(field, 2.2) * 1.8, 0.0, 1.0);
}

ItemId PlanetBody::dominantResource(const DVec3& unitDirection) const {
    const ItemId candidates[] = {ItemId::Ferrite,  ItemId::Silicate,   ItemId::Carbon,  ItemId::Copper,
                                 ItemId::Cobalt,   ItemId::Sulphur,    ItemId::Phosphor, ItemId::Uranite,
                                 ItemId::Platinum, ItemId::Gold,       ItemId::IceCrystal, ItemId::SaltCrystal,
                                 ItemId::Deuterium};
    ItemId best = ItemId::Ferrite;
    f64 bestRichness = 0.0;
    for (ItemId candidate : candidates) {
        const f64 richness = resourceRichness(unitDirection, candidate);
        if (richness <= bestRichness) continue;
        bestRichness = richness;
        best = candidate;
    }
    return bestRichness > 0.28 ? best : ItemId::Ferrite;
}

Vec3 PlanetBody::biomeAlbedo(BiomeType biome, const PlanetProfile& planet) {
    switch (biome) {
        case BiomeType::Tundra: return lerp(planet.groundColor, Vec3(0.62f, 0.64f, 0.60f), 0.45f);
        case BiomeType::Taiga: return lerp(planet.vegetationColor, planet.groundColor, 0.42f);
        case BiomeType::DeciduousForest: return lerp(planet.vegetationColor, Vec3(0.24f, 0.36f, 0.16f), 0.35f);
        case BiomeType::Rainforest: return lerp(planet.vegetationColor, Vec3(0.10f, 0.32f, 0.12f), 0.55f);
        case BiomeType::Savanna: return lerp(planet.groundColor, Vec3(0.66f, 0.58f, 0.26f), 0.55f);
        case BiomeType::Desert: return lerp(planet.groundColor, Vec3(0.78f, 0.64f, 0.40f), 0.62f);
        case BiomeType::SaltFlat: return Vec3(0.88f, 0.87f, 0.83f);
        case BiomeType::Steppe: return lerp(planet.groundColor, Vec3(0.56f, 0.52f, 0.32f), 0.48f);
        case BiomeType::Swamp: return lerp(planet.vegetationColor, Vec3(0.22f, 0.26f, 0.16f), 0.6f);
        case BiomeType::Mangrove: return lerp(planet.vegetationColor, Vec3(0.18f, 0.34f, 0.22f), 0.5f);
        case BiomeType::HighMountain: return lerp(planet.highlandColor, Vec3(0.52f, 0.50f, 0.48f), 0.5f);
        case BiomeType::Glacier: return Vec3(0.86f, 0.91f, 0.96f);
        case BiomeType::VolcanicField: return Vec3(0.22f, 0.14f, 0.12f);
        case BiomeType::AshDesert: return Vec3(0.32f, 0.30f, 0.30f);
        case BiomeType::CrystalField: return lerp(planet.groundColor, Vec3(0.62f, 0.78f, 0.92f), 0.6f);
        case BiomeType::FungalForest: return lerp(planet.vegetationColor, Vec3(0.52f, 0.34f, 0.56f), 0.55f);
        case BiomeType::BioluminescentNight: return lerp(planet.vegetationColor, Vec3(0.16f, 0.52f, 0.62f), 0.6f);
        case BiomeType::AmmoniaLake: return Vec3(0.56f, 0.62f, 0.48f);
        case BiomeType::MethaneBog: return Vec3(0.36f, 0.42f, 0.34f);
        case BiomeType::IronOxidePlain: return Vec3(0.58f, 0.28f, 0.18f);
        case BiomeType::StormZone: return lerp(planet.groundColor, Vec3(0.42f, 0.42f, 0.46f), 0.5f);
        case BiomeType::CoastalCliffs: return lerp(planet.groundColor, planet.highlandColor, 0.5f);
        case BiomeType::CoralShelf: return lerp(planet.waterColor, Vec3(0.42f, 0.72f, 0.66f), 0.5f);
        case BiomeType::DeepTrench: return planet.waterColor * 0.5f;
        default: return planet.groundColor;
    }
}

}
