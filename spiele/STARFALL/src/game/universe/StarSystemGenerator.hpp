#pragma once

#include "PlanetGenerator.hpp"

namespace sf {

enum class StarClass : u32 {
    O = 0, B, A, F, G, K, M, WhiteDwarf, NeutronStar, Pulsar, RedGiant, BlackHole, Count
};

struct StarProfile {
    std::string name;
    u64 seed = 0;
    StarClass starClass = StarClass::G;
    f64 massSolar = 1.0;
    f64 radiusMeters = 6.957e8;
    f64 luminositySolar = 1.0;
    f64 surfaceTemperatureKelvin = 5778.0;
    f64 radiationOutput = 1.0;
    f64 habitableZoneInnerMeters = 0.95 * kAstronomicalUnit;
    f64 habitableZoneOuterMeters = 1.67 * kAstronomicalUnit;
    Vec3 lightColor = Vec3(1.0f, 0.97f, 0.92f);
    DVec3 localOffset = DVec3::zero();
    f64 companionSeparationMeters = 0.0;
};

struct AsteroidBeltProfile {
    f64 innerRadiusMeters = 0.0;
    f64 outerRadiusMeters = 0.0;
    f64 density = 0.0;
    f64 metalRichness = 0.0;
};

struct StationProfile {
    std::string name;
    u64 seed = 0;
    u32 orbitingPlanetIndex = kInvalidIndex32;
    f64 orbitRadiusMeters = 0.0;
    f64 orbitalPeriodSeconds = 1.0;
    f64 radiusMeters = 900.0;
    NameCulture owner = NameCulture::Human;
    bool tradePost = true;
    bool shipyard = false;
    bool research = false;
};

struct StarSystemProfile {
    SystemCoord coordinate;
    u64 seed = 0;
    std::string name;
    std::vector<StarProfile> stars;
    std::vector<PlanetProfile> planets;
    std::vector<AsteroidBeltProfile> belts;
    std::vector<StationProfile> stations;
    f64 metallicity = 0.5;
    f64 ageGigayears = 5.0;
    bool hasNebula = false;
    Vec3 nebulaColor = Vec3(0.2f, 0.3f, 0.5f);
    NameCulture dominantCulture = NameCulture::Human;
    bool containsVoidHeart = false;

    f64 totalMassKilograms() const;
    const StarProfile& primaryStar() const { return stars[0]; }
};

class StarSystemGenerator {
public:
    StarSystemProfile generate(const UniverseSeed& universe, u64 galaxySeed, const SystemCoord& coordinate) const;
    static const char* starClassName(StarClass value);
    static Vec3 starColorFromTemperature(f64 temperatureKelvin);
    static StarProfile makeStar(u64 seed, StarClass forcedClass);
};

}
