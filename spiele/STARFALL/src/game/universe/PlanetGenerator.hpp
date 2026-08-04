#pragma once

#include "../../engine/math/Vec3.hpp"
#include "../../engine/render/CelestialBodyPass.hpp"
#include "NameGenerator.hpp"
#include "UniverseSeed.hpp"

#include <string>
#include <vector>

namespace sf {

enum class PlanetClass : u32 {
    Barren = 0,
    Rocky,
    Ocean,
    Terrestrial,
    Desert,
    Ice,
    Volcanic,
    Toxic,
    GasGiant,
    IceGiant,
    Crystal,
    Fungal,
    Count
};

enum class BiomeType : u32 {
    Tundra = 0, Taiga, DeciduousForest, Rainforest, Savanna, Desert, SaltFlat, Steppe,
    Swamp, Mangrove, HighMountain, Glacier, VolcanicField, AshDesert, CrystalField,
    FungalForest, BioluminescentNight, AmmoniaLake, MethaneBog, IronOxidePlain,
    StormZone, CoastalCliffs, CoralShelf, DeepTrench, Count
};

struct PlanetFeatures {
    bool ringSystem = false;
    bool bioluminescentNight = false;
    bool crystalDesert = false;
    bool stormWorld = false;
    bool oceanWorld = false;
    bool tidallyLocked = false;
    bool gravityAnomaly = false;
    bool precursorRuins = false;
};

struct PlanetProfile {
    std::string name;
    u64 seed = 0;
    u32 index = 0;
    PlanetClass planetClass = PlanetClass::Rocky;

    f64 radiusMeters = 6.0e6;
    f64 massKilograms = 5.0e24;
    f64 surfaceGravity = 9.81;
    f64 semiMajorAxisMeters = 1.5e11;
    f64 orbitalEccentricity = 0.02;
    f64 orbitalInclinationRadians = 0.0;
    f64 orbitalPeriodSeconds = 3.15e7;
    f64 argumentOfPeriapsis = 0.0;
    f64 meanAnomalyAtEpoch = 0.0;
    f64 rotationPeriodSeconds = 86400.0;
    f64 axialTiltRadians = 0.4;

    f64 atmospherePressureBar = 1.0;
    f64 atmosphereScaleHeightMeters = 8500.0;
    f64 oxygenFraction = 0.0;
    f64 carbonDioxideFraction = 0.0;
    f64 methaneFraction = 0.0;
    f64 waterFraction = 0.0;
    f64 meanSurfaceTemperatureKelvin = 255.0;
    f64 temperatureAmplitudeKelvin = 30.0;
    f64 albedo = 0.3;
    f64 magneticFieldTesla = 0.0;
    f64 radiationLevelSieverts = 0.0;

    f64 tectonicActivity = 0.4;
    f64 volcanism = 0.2;
    f64 surfaceAgeGigayears = 3.0;
    f64 erosionFactor = 0.5;
    f64 craterDensity = 0.4;
    f64 mountainRuggedness = 0.5;

    f64 biosphereLevel = 0.0;
    f64 vegetationDensity = 0.0;
    f64 faunaDiversity = 0.0;
    u32 civilizationLevel = 0;

    f64 metalAbundance = 0.4;
    f64 crystalAbundance = 0.2;
    f64 organicAbundance = 0.1;
    f64 exoticAbundance = 0.0;
    f64 fuelAbundance = 0.3;

    u32 moonCount = 0;
    PlanetFeatures features;

    Vec3 groundColor = Vec3(0.45f, 0.40f, 0.34f);
    Vec3 highlandColor = Vec3(0.32f, 0.30f, 0.27f);
    Vec3 skyColor = Vec3(0.35f, 0.55f, 0.95f);
    Vec3 waterColor = Vec3(0.05f, 0.20f, 0.34f);
    Vec3 vegetationColor = Vec3(0.20f, 0.42f, 0.16f);
    Vec3 ringColor = Vec3(0.72f, 0.64f, 0.52f);

    f64 habitabilityIndex() const;
    bool breathable() const;
    CelestialBodyDraw toDrawParameters(const DVec3& worldPosition, f64 rotationPhase) const;
};

struct MoonProfile {
    std::string name;
    u64 seed = 0;
    f64 radiusMeters = 1.7e6;
    f64 surfaceGravity = 1.62;
    f64 orbitRadiusMeters = 3.8e8;
    f64 orbitalPeriodSeconds = 2.36e6;
    f64 orbitalInclinationRadians = 0.0;
    f64 atmospherePressureBar = 0.0;
    PlanetClass moonClass = PlanetClass::Barren;
    Vec3 groundColor = Vec3(0.42f, 0.41f, 0.39f);
};

class PlanetGenerator {
public:
    PlanetProfile generate(u64 planetSeed, u32 planetIndex, const std::string& starName, f64 starLuminosity,
                           f64 starTemperature, f64 semiMajorAxisMeters, f64 systemMetallicity) const;
    std::vector<MoonProfile> generateMoons(const PlanetProfile& planet, const UniverseSeed& universe) const;

    static BiomeType classifyBiome(f64 temperatureKelvin, f64 precipitation, f64 elevationFraction, f64 slope,
                                   const PlanetProfile& planet);
    static const char* planetClassName(PlanetClass value);
    static const char* biomeName(BiomeType value);
    static f64 surfaceHeightAt(const PlanetProfile& planet, const DVec3& unitDirection);
};

}
