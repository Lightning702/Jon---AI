#include "PlanetGenerator.hpp"

#include "../../engine/math/Noise.hpp"
#include "../../engine/math/Scalar.hpp"

namespace sf {
namespace {

Vec3 harmonicColor(Random& random, f32 baseHue, f32 hueSpread, f32 saturation, f32 value) {
    const f32 hue = std::fmod(baseHue + random.range(-hueSpread, hueSpread) + 1.0f, 1.0f);
    const f32 sector = hue * 6.0f;
    const i32 index = static_cast<i32>(sector) % 6;
    const f32 fraction = sector - std::floor(sector);
    const f32 p = value * (1.0f - saturation);
    const f32 q = value * (1.0f - saturation * fraction);
    const f32 t = value * (1.0f - saturation * (1.0f - fraction));
    switch (index) {
        case 0: return Vec3(value, t, p);
        case 1: return Vec3(q, value, p);
        case 2: return Vec3(p, value, t);
        case 3: return Vec3(p, q, value);
        case 4: return Vec3(t, p, value);
        default: return Vec3(value, p, q);
    }
}

f64 equilibriumTemperature(f64 starLuminosity, f64 distanceMeters, f64 albedo, f64 greenhouse) {
    const f64 solarLuminosity = 3.828e26;
    const f64 flux = starLuminosity * solarLuminosity / (4.0 * kPiDouble * distanceMeters * distanceMeters);
    const f64 absorbed = flux * (1.0 - albedo) * 0.25;
    const f64 base = std::pow(maxValue(absorbed, 1.0e-6) / kStefanBoltzmann, 0.25);
    return base * (1.0 + greenhouse);
}

}

f64 PlanetProfile::habitabilityIndex() const {
    f64 score = 1.0;
    const f64 temperatureOffset = std::fabs(meanSurfaceTemperatureKelvin - 288.0);
    score *= std::exp(-temperatureOffset * temperatureOffset / 2600.0);
    const f64 pressureOffset = std::log(maxValue(atmospherePressureBar, 1.0e-4)) - std::log(1.0);
    score *= std::exp(-pressureOffset * pressureOffset / 2.4);
    score *= clampValue(oxygenFraction / 0.21, 0.0, 1.0) * 0.6 + 0.4;
    score *= clampValue(waterFraction * 3.0, 0.0, 1.0) * 0.7 + 0.3;
    score *= std::exp(-radiationLevelSieverts * 4.0);
    score *= clampValue(1.6 - std::fabs(surfaceGravity - 9.81) / 9.81, 0.0, 1.0);
    return clampValue(score, 0.0, 1.0);
}

bool PlanetProfile::breathable() const {
    return oxygenFraction > 0.16 && oxygenFraction < 0.30 && atmospherePressureBar > 0.6 &&
           atmospherePressureBar < 1.8 && meanSurfaceTemperatureKelvin > 253.0 &&
           meanSurfaceTemperatureKelvin < 318.0 && radiationLevelSieverts < 0.12;
}

CelestialBodyDraw PlanetProfile::toDrawParameters(const DVec3& worldPosition, f64 rotationPhase) const {
    CelestialBodyDraw draw;
    draw.worldPosition = worldPosition;
    draw.radiusMeters = radiusMeters;
    const Quat tilt = Quat::fromAxisAngle(Vec3(0.0f, 0.0f, 1.0f), static_cast<f32>(axialTiltRadians));
    const Quat spin = Quat::fromAxisAngle(Vec3(0.0f, 1.0f, 0.0f), static_cast<f32>(rotationPhase));
    draw.orientation = tilt * spin;
    draw.primaryColor = groundColor;
    draw.secondaryColor = highlandColor;
    draw.atmosphereColor = skyColor;
    draw.atmosphereHeightFraction = static_cast<f32>(clampValue(atmosphereScaleHeightMeters * 6.0 / radiusMeters, 0.004, 0.14));
    draw.atmosphereDensity = static_cast<f32>(clampValue(atmospherePressureBar * 0.85, 0.0, 3.0));
    draw.roughness = static_cast<f32>(clampValue(0.95 - metalAbundance * 0.35, 0.12, 1.0));
    draw.metallic = static_cast<f32>(clampValue(metalAbundance * 0.35, 0.0, 0.5));
    draw.emissiveStrength = planetClass == PlanetClass::Volcanic ? 0.20f : 0.0f;
    draw.surfaceDetail = static_cast<f32>(clampValue(mountainRuggedness * 1.4, 0.15, 1.6));
    draw.cloudCoverage = static_cast<f32>(clampValue(waterFraction * 1.2 * clampValue(atmospherePressureBar, 0.0, 2.0), 0.0, 0.95));
    draw.iceCoverage = static_cast<f32>(clampValue((273.0 - meanSurfaceTemperatureKelvin) / 90.0, 0.0, 1.0));
    draw.nightLights = civilizationLevel >= 3 ? static_cast<f32>(clampValue((civilizationLevel - 2) * 0.35, 0.0, 1.0)) : 0.0f;
    draw.surfaceSeed = seed;
    draw.hasRing = features.ringSystem;
    draw.ringInnerFraction = 1.35f;
    draw.ringOuterFraction = 2.35f;
    draw.ringColor = ringColor;

    switch (planetClass) {
        case PlanetClass::Ocean: draw.surfaceType = CelestialSurface::Ocean; break;
        case PlanetClass::Terrestrial: draw.surfaceType = CelestialSurface::Ocean; break;
        case PlanetClass::Ice: draw.surfaceType = CelestialSurface::Ice; break;
        case PlanetClass::Desert: draw.surfaceType = CelestialSurface::Desert; break;
        case PlanetClass::Volcanic: draw.surfaceType = CelestialSurface::Lava; break;
        case PlanetClass::GasGiant: draw.surfaceType = CelestialSurface::GasGiant; break;
        case PlanetClass::IceGiant: draw.surfaceType = CelestialSurface::GasGiant; break;
        case PlanetClass::Crystal: draw.surfaceType = CelestialSurface::Crystal; break;
        default: draw.surfaceType = CelestialSurface::Rock; break;
    }
    return draw;
}

PlanetProfile PlanetGenerator::generate(u64 planetSeed, u32 planetIndex, const std::string& starName,
                                        f64 starLuminosity, f64 starTemperature, f64 semiMajorAxisMeters,
                                        f64 systemMetallicity) const {
    Random random(planetSeed);
    PlanetProfile planet;
    planet.seed = planetSeed;
    planet.index = planetIndex;
    planet.semiMajorAxisMeters = semiMajorAxisMeters;
    planet.name = generatePlanetDesignation(starName, planetIndex + 1);

    const f64 frostLineMeters = 2.7 * kAstronomicalUnit * std::sqrt(maxValue(starLuminosity, 0.001));
    const bool beyondFrostLine = semiMajorAxisMeters > frostLineMeters;
    const f64 giantChance = beyondFrostLine ? 0.42 : 0.06;

    if (random.nextDouble() < giantChance) {
        planet.planetClass = random.chance(0.55f) ? PlanetClass::GasGiant : PlanetClass::IceGiant;
        planet.radiusMeters = random.rangeDouble(2.4e7, 8.0e7);
        planet.massKilograms = random.rangeDouble(2.0e26, 3.4e27);
        planet.atmospherePressureBar = random.rangeDouble(80.0, 4000.0);
        planet.atmosphereScaleHeightMeters = random.rangeDouble(20000.0, 60000.0);
        planet.albedo = random.rangeDouble(0.32, 0.58);
    } else {
        planet.radiusMeters = random.rangeDouble(1.6e6, 1.1e7);
        const f64 density = random.rangeDouble(3200.0, 6200.0) * (0.85 + systemMetallicity * 0.4);
        planet.massKilograms = (4.0 / 3.0) * kPiDouble * planet.radiusMeters * planet.radiusMeters *
                               planet.radiusMeters * density;
        planet.atmospherePressureBar = std::pow(10.0, random.rangeDouble(-4.0, 1.4));
        planet.atmosphereScaleHeightMeters = random.rangeDouble(3000.0, 22000.0);
        planet.albedo = random.rangeDouble(0.08, 0.62);
    }

    planet.surfaceGravity = kGravitationalConstant * planet.massKilograms /
                            (planet.radiusMeters * planet.radiusMeters);

    planet.orbitalEccentricity = clampValue(std::fabs(random.gaussian(0.04f, 0.06f)), 0.0f, 0.42f);
    planet.orbitalInclinationRadians = random.rangeDouble(-0.09, 0.09);
    planet.argumentOfPeriapsis = random.rangeDouble(0.0, kTwoPiDouble);
    planet.meanAnomalyAtEpoch = random.rangeDouble(0.0, kTwoPiDouble);

    const f64 starMassKilograms = std::pow(maxValue(starLuminosity, 0.0005), 1.0 / 3.5) * kSolarMass;
    planet.orbitalPeriodSeconds = kTwoPiDouble * std::sqrt(semiMajorAxisMeters * semiMajorAxisMeters *
                                                          semiMajorAxisMeters /
                                                          (kGravitationalConstant * starMassKilograms));

    planet.rotationPeriodSeconds = random.rangeDouble(5040.0, 1.44e6);
    planet.axialTiltRadians = random.rangeDouble(0.0, 1.2);

    const f64 greenhouse = clampValue(std::log10(maxValue(planet.atmospherePressureBar, 1.0e-5)) * 0.32 + 0.10, 0.0, 2.6);
    planet.meanSurfaceTemperatureKelvin = equilibriumTemperature(starLuminosity, semiMajorAxisMeters, planet.albedo,
                                                                 greenhouse);
    planet.temperatureAmplitudeKelvin = random.rangeDouble(6.0, 78.0) *
                                        (1.0 + planet.axialTiltRadians) /
                                        (1.0 + planet.atmospherePressureBar * 0.4);

    planet.magneticFieldTesla = random.rangeDouble(0.0, 8.0e-5) * (planet.massKilograms > 2.0e24 ? 1.0 : 0.2);
    planet.radiationLevelSieverts = clampValue(0.42 / (1.0 + planet.magneticFieldTesla * 3.0e4) /
                                                   (1.0 + planet.atmospherePressureBar * 1.4) *
                                                   (starTemperature / 5800.0),
                                               0.0, 4.0);

    planet.tectonicActivity = clampValue(random.nextDouble() * (planet.massKilograms / 6.0e24), 0.0, 1.0);
    planet.volcanism = clampValue(planet.tectonicActivity * random.rangeDouble(0.3, 1.4), 0.0, 1.0);
    planet.surfaceAgeGigayears = random.rangeDouble(0.2, 9.4);
    planet.erosionFactor = clampValue(planet.atmospherePressureBar * 0.45 + random.rangeDouble(0.0, 0.4), 0.0, 1.0);
    planet.craterDensity = clampValue((1.0 - planet.erosionFactor) * (planet.surfaceAgeGigayears / 9.4), 0.0, 1.0);
    planet.mountainRuggedness = clampValue(planet.tectonicActivity * 0.7 + random.rangeDouble(0.05, 0.5), 0.05, 1.4);

    const bool temperate = planet.meanSurfaceTemperatureKelvin > 250.0 && planet.meanSurfaceTemperatureKelvin < 330.0;
    planet.waterFraction = temperate && planet.atmospherePressureBar > 0.15
                               ? clampValue(random.nextDouble() * 1.15, 0.0, 1.0)
                               : (planet.meanSurfaceTemperatureKelvin < 250.0 ? random.rangeDouble(0.0, 0.35) : 0.0);

    if (planet.planetClass != PlanetClass::GasGiant && planet.planetClass != PlanetClass::IceGiant) {
        if (planet.meanSurfaceTemperatureKelvin > 640.0) planet.planetClass = PlanetClass::Volcanic;
        else if (planet.meanSurfaceTemperatureKelvin < 175.0) planet.planetClass = PlanetClass::Ice;
        else if (planet.atmospherePressureBar < 0.02) planet.planetClass = PlanetClass::Barren;
        else if (planet.waterFraction > 0.86) planet.planetClass = PlanetClass::Ocean;
        else if (planet.waterFraction > 0.25 && temperate) planet.planetClass = PlanetClass::Terrestrial;
        else if (planet.waterFraction < 0.06 && planet.meanSurfaceTemperatureKelvin > 300.0) planet.planetClass = PlanetClass::Desert;
        else planet.planetClass = PlanetClass::Rocky;
    }

    if (planet.planetClass == PlanetClass::Terrestrial || planet.planetClass == PlanetClass::Ocean) {
        planet.oxygenFraction = random.chance(0.42f) ? random.rangeDouble(0.10, 0.28) : random.rangeDouble(0.0, 0.05);
        planet.carbonDioxideFraction = random.rangeDouble(0.0004, 0.24);
        planet.biosphereLevel = clampValue(planet.oxygenFraction * 3.4 + planet.waterFraction * 0.8, 0.0, 1.0);
    } else {
        planet.oxygenFraction = random.rangeDouble(0.0, 0.02);
        planet.carbonDioxideFraction = random.rangeDouble(0.0, 0.95);
        planet.methaneFraction = random.rangeDouble(0.0, 0.35);
        planet.biosphereLevel = random.chance(0.08f) ? random.rangeDouble(0.05, 0.35) : 0.0;
    }
    planet.vegetationDensity = clampValue(planet.biosphereLevel * random.rangeDouble(0.4, 1.4), 0.0, 1.0);
    planet.faunaDiversity = clampValue(planet.biosphereLevel * random.rangeDouble(0.2, 1.2), 0.0, 1.0);

    if (planet.biosphereLevel > 0.55 && random.chance(0.16f)) {
        planet.civilizationLevel = static_cast<u32>(random.rangeInt(1, 5));
    } else if (random.chance(0.03f)) {
        planet.civilizationLevel = 5;
    }

    planet.metalAbundance = clampValue(systemMetallicity * random.rangeDouble(0.4, 1.6) + planet.tectonicActivity * 0.3, 0.0, 1.0);
    planet.crystalAbundance = clampValue(planet.volcanism * random.rangeDouble(0.3, 1.5), 0.0, 1.0);
    planet.organicAbundance = clampValue(planet.biosphereLevel * random.rangeDouble(0.6, 1.4), 0.0, 1.0);
    planet.fuelAbundance = clampValue(random.nextDouble() * (planet.planetClass == PlanetClass::GasGiant ? 1.6 : 0.7), 0.0, 1.0);
    planet.exoticAbundance = random.chance(0.05f) ? random.rangeDouble(0.05, 0.4) : 0.0;

    planet.features.ringSystem = random.chance(0.08f) || planet.planetClass == PlanetClass::GasGiant;
    planet.features.bioluminescentNight = planet.biosphereLevel > 0.3 && random.chance(0.05f);
    planet.features.crystalDesert = random.chance(0.02f);
    planet.features.stormWorld = random.chance(0.04f);
    planet.features.oceanWorld = planet.waterFraction > 0.92 || random.chance(0.06f);
    planet.features.tidallyLocked = random.chance(0.09f) || semiMajorAxisMeters < 0.12 * kAstronomicalUnit;
    planet.features.gravityAnomaly = random.chance(0.01f);
    planet.features.precursorRuins = random.chance(0.03f);

    if (planet.features.tidallyLocked) {
        planet.rotationPeriodSeconds = planet.orbitalPeriodSeconds;
    }
    if (planet.features.crystalDesert) planet.planetClass = PlanetClass::Crystal;
    if (planet.features.bioluminescentNight && planet.biosphereLevel > 0.5 && random.chance(0.4f)) {
        planet.planetClass = PlanetClass::Fungal;
    }

    const f32 baseHue = static_cast<f32>(random.nextDouble());
    planet.groundColor = harmonicColor(random, baseHue, 0.04f, random.range(0.18f, 0.62f), random.range(0.22f, 0.72f));
    planet.highlandColor = harmonicColor(random, baseHue + 0.08f, 0.04f, random.range(0.10f, 0.44f), random.range(0.16f, 0.58f));
    planet.vegetationColor = harmonicColor(random, baseHue + 0.42f, 0.07f, random.range(0.35f, 0.8f), random.range(0.24f, 0.62f));
    planet.skyColor = harmonicColor(random, baseHue + 0.55f, 0.10f, random.range(0.35f, 0.85f), random.range(0.45f, 0.95f));
    planet.waterColor = harmonicColor(random, baseHue + 0.58f, 0.05f, random.range(0.5f, 0.9f), random.range(0.12f, 0.4f));
    planet.ringColor = harmonicColor(random, baseHue + 0.12f, 0.03f, random.range(0.10f, 0.35f), random.range(0.55f, 0.9f));

    planet.moonCount = static_cast<u32>(random.rangeInt(0, planet.planetClass == PlanetClass::GasGiant ? 13 : 5));
    return planet;
}

std::vector<MoonProfile> PlanetGenerator::generateMoons(const PlanetProfile& planet,
                                                        const UniverseSeed& universe) const {
    std::vector<MoonProfile> moons;
    moons.reserve(planet.moonCount);
    for (u32 index = 0; index < planet.moonCount; ++index) {
        const u64 moonSeed = universe.moonSeed(planet.seed, index);
        Random random(moonSeed);
        MoonProfile moon;
        moon.seed = moonSeed;
        moon.name = generateMoonDesignation(planet.name, index);
        moon.radiusMeters = planet.radiusMeters * random.rangeDouble(0.05, 0.34);
        const f64 density = random.rangeDouble(1600.0, 3600.0);
        const f64 mass = (4.0 / 3.0) * kPiDouble * moon.radiusMeters * moon.radiusMeters * moon.radiusMeters * density;
        moon.surfaceGravity = kGravitationalConstant * mass / (moon.radiusMeters * moon.radiusMeters);
        moon.orbitRadiusMeters = planet.radiusMeters * random.rangeDouble(3.5, 62.0);
        moon.orbitalPeriodSeconds = kTwoPiDouble * std::sqrt(moon.orbitRadiusMeters * moon.orbitRadiusMeters *
                                                            moon.orbitRadiusMeters /
                                                            (kGravitationalConstant * planet.massKilograms));
        moon.orbitalInclinationRadians = random.rangeDouble(-0.35, 0.35);
        moon.atmospherePressureBar = random.chance(0.14f) ? random.rangeDouble(0.001, 1.6) : 0.0;
        moon.moonClass = moon.atmospherePressureBar > 0.4 ? PlanetClass::Rocky : PlanetClass::Barren;
        moon.groundColor = harmonicColor(random, static_cast<f32>(random.nextDouble()), 0.03f,
                                         random.range(0.05f, 0.3f), random.range(0.24f, 0.68f));
        moons.push_back(moon);
    }
    return moons;
}

BiomeType PlanetGenerator::classifyBiome(f64 temperatureKelvin, f64 precipitation, f64 elevationFraction, f64 slope,
                                         const PlanetProfile& planet) {
    if (planet.features.crystalDesert) return BiomeType::CrystalField;
    if (elevationFraction < 0.0) {
        return elevationFraction < -0.55 ? BiomeType::DeepTrench
                                         : (temperatureKelvin > 292.0 ? BiomeType::CoralShelf : BiomeType::DeepTrench);
    }
    if (elevationFraction > 0.72 && slope > 0.5) {
        return temperatureKelvin < 268.0 ? BiomeType::Glacier : BiomeType::HighMountain;
    }
    if (planet.volcanism > 0.72 && elevationFraction > 0.42) {
        return temperatureKelvin > 400.0 ? BiomeType::VolcanicField : BiomeType::AshDesert;
    }
    if (planet.methaneFraction > 0.18 && temperatureKelvin < 130.0) return BiomeType::MethaneBog;
    if (planet.methaneFraction > 0.08 && temperatureKelvin < 210.0) return BiomeType::AmmoniaLake;
    if (planet.features.stormWorld && elevationFraction < 0.22) return BiomeType::StormZone;
    if (planet.features.bioluminescentNight && precipitation > 0.6) return BiomeType::BioluminescentNight;
    if (planet.planetClass == PlanetClass::Fungal && precipitation > 0.45) return BiomeType::FungalForest;
    if (planet.metalAbundance > 0.78 && precipitation < 0.24) return BiomeType::IronOxidePlain;

    if (temperatureKelvin < 258.0) return precipitation > 0.35 ? BiomeType::Taiga : BiomeType::Tundra;
    if (temperatureKelvin < 283.0) {
        if (precipitation > 0.62) return BiomeType::DeciduousForest;
        if (precipitation > 0.28) return BiomeType::Steppe;
        return BiomeType::SaltFlat;
    }
    if (temperatureKelvin < 305.0) {
        if (precipitation > 0.78) return BiomeType::Rainforest;
        if (precipitation > 0.52) return BiomeType::Swamp;
        if (precipitation > 0.30) return BiomeType::Savanna;
        return BiomeType::Desert;
    }
    if (precipitation > 0.66) return BiomeType::Mangrove;
    if (elevationFraction < 0.08) return BiomeType::CoastalCliffs;
    return BiomeType::Desert;
}

const char* PlanetGenerator::planetClassName(PlanetClass value) {
    switch (value) {
        case PlanetClass::Barren: return "Kahl";
        case PlanetClass::Rocky: return "Gesteinswelt";
        case PlanetClass::Ocean: return "Ozeanwelt";
        case PlanetClass::Terrestrial: return "Erdaehnlich";
        case PlanetClass::Desert: return "Wuestenwelt";
        case PlanetClass::Ice: return "Eiswelt";
        case PlanetClass::Volcanic: return "Vulkanwelt";
        case PlanetClass::Toxic: return "Giftwelt";
        case PlanetClass::GasGiant: return "Gasriese";
        case PlanetClass::IceGiant: return "Eisriese";
        case PlanetClass::Crystal: return "Kristallwelt";
        case PlanetClass::Fungal: return "Pilzwelt";
        default: return "Unbekannt";
    }
}

const char* PlanetGenerator::biomeName(BiomeType value) {
    switch (value) {
        case BiomeType::Tundra: return "Tundra";
        case BiomeType::Taiga: return "Taiga";
        case BiomeType::DeciduousForest: return "Laubwald";
        case BiomeType::Rainforest: return "Regenwald";
        case BiomeType::Savanna: return "Savanne";
        case BiomeType::Desert: return "Wueste";
        case BiomeType::SaltFlat: return "Salzwueste";
        case BiomeType::Steppe: return "Steppe";
        case BiomeType::Swamp: return "Sumpf";
        case BiomeType::Mangrove: return "Mangrove";
        case BiomeType::HighMountain: return "Hochgebirge";
        case BiomeType::Glacier: return "Gletscher";
        case BiomeType::VolcanicField: return "Vulkanfeld";
        case BiomeType::AshDesert: return "Aschewueste";
        case BiomeType::CrystalField: return "Kristallfeld";
        case BiomeType::FungalForest: return "Pilzwald";
        case BiomeType::BioluminescentNight: return "Leuchtwald";
        case BiomeType::AmmoniaLake: return "Ammoniaksee";
        case BiomeType::MethaneBog: return "Methansumpf";
        case BiomeType::IronOxidePlain: return "Eisenoxid-Ebene";
        case BiomeType::StormZone: return "Sturmzone";
        case BiomeType::CoastalCliffs: return "Kuestenklippen";
        case BiomeType::CoralShelf: return "Korallenschelf";
        case BiomeType::DeepTrench: return "Tiefseegraben";
        default: return "Unbekannt";
    }
}

u32 PlanetGenerator::detailLevelForChunkSize(f64 chunkWorldSizeMeters) {
    if (chunkWorldSizeMeters > 260000.0) return 0;
    if (chunkWorldSizeMeters > 26000.0) return 1;
    if (chunkWorldSizeMeters > 2600.0) return 2;
    return 3;
}

f64 PlanetGenerator::surfaceHeightAt(const PlanetProfile& planet, const DVec3& unitDirection, u32 detailLevel) {
    const u32 detail = clampValue(detailLevel, 0u, 3u);

    FractalSettings continental;
    continental.octaves = detail == 0 ? 3u : (detail == 1 ? 4u : 6u);
    continental.frequency = 1.15;
    continental.lacunarity = 2.07;
    continental.gain = 0.52;

    const DVec3 warped = detail == 0 ? unitDirection : domainWarp3(planet.seed, unitDirection, 0.32, 1.7);
    f64 height = fractalNoise3(planet.seed, warped, continental) * 0.55;

    if (detail >= 1 && planet.mountainRuggedness > 0.02) {
        const WorleyResult plates = worleyNoise3(planet.seed ^ 0x504C4154ull, unitDirection * 2.6);
        const f64 plateBoundary = clampValue(1.0 - (plates.secondDistance - plates.nearestDistance) * 3.4, 0.0, 1.0);

        FractalSettings mountains;
        mountains.octaves = detail == 1 ? 4u : 7u;
        mountains.frequency = 4.2;
        mountains.lacunarity = 2.11;
        mountains.gain = 0.48;
        const f64 ridges = ridgedMultifractal3(planet.seed ^ 0x4D4E54ull, unitDirection, mountains);
        height += ridges * plateBoundary * planet.mountainRuggedness * 0.62;
    }

    if (detail >= 2 && planet.volcanism > 0.02) {
        const f64 hotspot = clampValue(
            1.0 - worleyNearestDistance(planet.seed ^ 0x564F4Cull, unitDirection * 3.1) * 2.6, 0.0, 1.0);
        height += planet.volcanism * hotspot * 0.34;
    }

    if (detail >= 2 && planet.craterDensity > 0.03) {
        const u32 layers = detail >= 3 ? 4u : 2u;
        height += craterField(planet.seed ^ 0x435241ull, unitDirection, 7.5, planet.craterDensity * 0.55, layers);
    }

    height *= 1.0 - planet.erosionFactor * 0.34;
    if (planet.features.oceanWorld) height -= 0.32;
    return height;
}

}
