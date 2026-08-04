#include "StarSystemGenerator.hpp"

#include "../../engine/math/Noise.hpp"
#include "../../engine/math/Scalar.hpp"

namespace sf {
namespace {

struct ClassWeight {
    StarClass starClass;
    f64 weight;
};

const ClassWeight kClassWeights[] = {
    {StarClass::M, 0.5100}, {StarClass::K, 0.1600}, {StarClass::G, 0.0900},
    {StarClass::F, 0.0600}, {StarClass::A, 0.0350}, {StarClass::B, 0.0140},
    {StarClass::O, 0.0025}, {StarClass::WhiteDwarf, 0.0800}, {StarClass::RedGiant, 0.0350},
    {StarClass::NeutronStar, 0.0090}, {StarClass::Pulsar, 0.0035}, {StarClass::BlackHole, 0.0010}};

StarClass pickClass(Random& random) {
    f64 total = 0.0;
    for (const ClassWeight& entry : kClassWeights) total += entry.weight;
    f64 roll = random.rangeDouble(0.0, total);
    for (const ClassWeight& entry : kClassWeights) {
        roll -= entry.weight;
        if (roll <= 0.0) return entry.starClass;
    }
    return StarClass::M;
}

}

f64 StarSystemProfile::totalMassKilograms() const {
    f64 total = 0.0;
    for (const StarProfile& star : stars) total += star.massSolar * kSolarMass;
    for (const PlanetProfile& planet : planets) total += planet.massKilograms;
    return total;
}

Vec3 StarSystemGenerator::starColorFromTemperature(f64 temperatureKelvin) {
    const f64 clamped = clampValue(temperatureKelvin, 1500.0, 40000.0);
    const f64 inverse = 1000.0 / clamped;
    f64 x;
    if (clamped < 4000.0) {
        x = -0.2661239 * inverse * inverse * inverse - 0.2343589 * inverse * inverse + 0.8776956 * inverse + 0.179910;
    } else {
        x = -3.0258469 * inverse * inverse * inverse + 2.1070379 * inverse * inverse + 0.2226347 * inverse + 0.240390;
    }
    f64 y;
    if (clamped < 2222.0) {
        y = -1.1063814 * x * x * x - 1.34811020 * x * x + 2.18555832 * x - 0.20219683;
    } else if (clamped < 4000.0) {
        y = -0.9549476 * x * x * x - 1.37418593 * x * x + 2.09137015 * x - 0.16748867;
    } else {
        y = 3.0817580 * x * x * x - 5.87338670 * x * x + 3.75112997 * x - 0.37001483;
    }
    const f64 safeY = maxValue(y, 1.0e-4);
    const f64 tristimulusX = x / safeY;
    const f64 tristimulusZ = (1.0 - x - y) / safeY;
    Vec3 linear(static_cast<f32>(3.2404542 * tristimulusX - 1.5371385 - 0.4985314 * tristimulusZ),
                static_cast<f32>(-0.9692660 * tristimulusX + 1.8760108 + 0.0415560 * tristimulusZ),
                static_cast<f32>(0.0556434 * tristimulusX - 0.2040259 + 1.0572252 * tristimulusZ));
    linear = maxComponents(linear, Vec3(0.0f));
    const f32 peak = maxValue(maxValue(linear.x, linear.y), maxValue(linear.z, 1.0e-4f));
    return linear / peak;
}

StarProfile StarSystemGenerator::makeStar(u64 seed, StarClass forcedClass) {
    Random random(seed);
    StarProfile star;
    star.seed = seed;
    star.starClass = forcedClass == StarClass::Count ? pickClass(random) : forcedClass;
    star.name = generateStarDesignation(seed);

    switch (star.starClass) {
        case StarClass::O:
            star.massSolar = random.rangeDouble(16.0, 60.0);
            star.surfaceTemperatureKelvin = random.rangeDouble(30000.0, 45000.0);
            break;
        case StarClass::B:
            star.massSolar = random.rangeDouble(2.1, 16.0);
            star.surfaceTemperatureKelvin = random.rangeDouble(10000.0, 30000.0);
            break;
        case StarClass::A:
            star.massSolar = random.rangeDouble(1.4, 2.1);
            star.surfaceTemperatureKelvin = random.rangeDouble(7500.0, 10000.0);
            break;
        case StarClass::F:
            star.massSolar = random.rangeDouble(1.04, 1.4);
            star.surfaceTemperatureKelvin = random.rangeDouble(6000.0, 7500.0);
            break;
        case StarClass::G:
            star.massSolar = random.rangeDouble(0.8, 1.04);
            star.surfaceTemperatureKelvin = random.rangeDouble(5200.0, 6000.0);
            break;
        case StarClass::K:
            star.massSolar = random.rangeDouble(0.45, 0.8);
            star.surfaceTemperatureKelvin = random.rangeDouble(3700.0, 5200.0);
            break;
        case StarClass::M:
            star.massSolar = random.rangeDouble(0.08, 0.45);
            star.surfaceTemperatureKelvin = random.rangeDouble(2400.0, 3700.0);
            break;
        case StarClass::WhiteDwarf:
            star.massSolar = random.rangeDouble(0.5, 1.3);
            star.surfaceTemperatureKelvin = random.rangeDouble(8000.0, 40000.0);
            break;
        case StarClass::NeutronStar:
            star.massSolar = random.rangeDouble(1.2, 2.1);
            star.surfaceTemperatureKelvin = random.rangeDouble(500000.0, 1200000.0);
            break;
        case StarClass::Pulsar:
            star.massSolar = random.rangeDouble(1.3, 2.0);
            star.surfaceTemperatureKelvin = random.rangeDouble(600000.0, 1600000.0);
            break;
        case StarClass::RedGiant:
            star.massSolar = random.rangeDouble(0.8, 8.0);
            star.surfaceTemperatureKelvin = random.rangeDouble(3000.0, 4800.0);
            break;
        case StarClass::BlackHole:
            star.massSolar = random.rangeDouble(4.0, 28.0);
            star.surfaceTemperatureKelvin = 0.0;
            break;
        default:
            break;
    }

    if (star.starClass == StarClass::WhiteDwarf) {
        star.radiusMeters = random.rangeDouble(6.0e6, 1.6e7);
    } else if (star.starClass == StarClass::NeutronStar || star.starClass == StarClass::Pulsar) {
        star.radiusMeters = random.rangeDouble(1.0e4, 1.4e4);
    } else if (star.starClass == StarClass::BlackHole) {
        star.radiusMeters = 2.0 * kGravitationalConstant * star.massSolar * kSolarMass /
                            (kSpeedOfLight * kSpeedOfLight);
    } else if (star.starClass == StarClass::RedGiant) {
        star.radiusMeters = 6.957e8 * random.rangeDouble(18.0, 180.0);
    } else {
        star.radiusMeters = 6.957e8 * std::pow(star.massSolar, 0.8);
    }

    const f64 surfaceArea = 4.0 * kPiDouble * star.radiusMeters * star.radiusMeters;
    const f64 emitted = surfaceArea * kStefanBoltzmann * std::pow(star.surfaceTemperatureKelvin, 4.0);
    star.luminositySolar = maxValue(emitted / 3.828e26, 1.0e-8);
    star.radiationOutput = clampValue(star.luminositySolar * 0.4 +
                                          (star.starClass == StarClass::Pulsar ? 8.0 : 0.0),
                                      0.0, 40.0);
    star.habitableZoneInnerMeters = kAstronomicalUnit * std::sqrt(star.luminositySolar / 1.1);
    star.habitableZoneOuterMeters = kAstronomicalUnit * std::sqrt(star.luminositySolar / 0.53);
    star.lightColor = star.starClass == StarClass::BlackHole
                          ? Vec3(0.12f, 0.10f, 0.16f)
                          : starColorFromTemperature(star.surfaceTemperatureKelvin);
    return star;
}

StarSystemProfile StarSystemGenerator::generate(const UniverseSeed& universe, u64 galaxySeed,
                                                const SystemCoord& coordinate) const {
    const u64 systemSeed = universe.systemSeed(galaxySeed, coordinate);
    Random random(systemSeed);

    StarSystemProfile system;
    system.coordinate = coordinate;
    system.seed = systemSeed;

    const f64 distanceFromCore = std::sqrt(static_cast<f64>(coordinate.x) * static_cast<f64>(coordinate.x) +
                                           static_cast<f64>(coordinate.y) * static_cast<f64>(coordinate.y) +
                                           static_cast<f64>(coordinate.z) * static_cast<f64>(coordinate.z));
    system.metallicity = clampValue(1.05 - distanceFromCore / 52000.0 + random.rangeDouble(-0.18, 0.18), 0.02, 1.0);
    system.ageGigayears = random.rangeDouble(0.4, 12.6);
    system.hasNebula = random.chance(0.09f);
    system.nebulaColor = Vec3(static_cast<f32>(random.rangeDouble(0.1, 0.8)),
                              static_cast<f32>(random.rangeDouble(0.1, 0.6)),
                              static_cast<f32>(random.rangeDouble(0.2, 0.9)));
    system.dominantCulture = static_cast<NameCulture>(
        random.rangeInt(0, static_cast<i32>(NameCulture::Count)));

    const u32 starCount = random.chance(0.28f) ? (random.chance(0.22f) ? 3u : 2u) : 1u;
    for (u32 index = 0; index < starCount; ++index) {
        StarProfile star = makeStar(hashCombine(systemSeed, index + 0x5741u), StarClass::Count);
        if (index > 0) {
            star.companionSeparationMeters = random.rangeDouble(4.0e9, 9.0e11);
            const f64 angle = random.rangeDouble(0.0, kTwoPiDouble);
            star.localOffset = DVec3(std::cos(angle), 0.0, std::sin(angle)) * star.companionSeparationMeters;
        }
        system.stars.push_back(star);
    }
    system.name = system.stars[0].name;

    const StarProfile& primary = system.stars[0];
    const u32 planetCount = static_cast<u32>(random.rangeInt(0, 13));
    f64 orbitRadius = kAstronomicalUnit * random.rangeDouble(0.08, 0.55) *
                      maxValue(std::sqrt(primary.luminositySolar), 0.12);
    PlanetGenerator planetGenerator;

    for (u32 index = 0; index < planetCount; ++index) {
        const u64 planetSeed = universe.planetSeed(systemSeed, index);
        PlanetProfile planet = planetGenerator.generate(planetSeed, index, system.name, primary.luminositySolar,
                                                        primary.surfaceTemperatureKelvin, orbitRadius,
                                                        system.metallicity);
        system.planets.push_back(planet);
        orbitRadius *= random.rangeDouble(1.42, 2.35);
    }

    const u32 beltCount = static_cast<u32>(random.rangeInt(0, 3));
    for (u32 index = 0; index < beltCount; ++index) {
        AsteroidBeltProfile belt;
        belt.innerRadiusMeters = kAstronomicalUnit * random.rangeDouble(1.4, 34.0);
        belt.outerRadiusMeters = belt.innerRadiusMeters * random.rangeDouble(1.15, 1.9);
        belt.density = random.rangeDouble(0.15, 1.0);
        belt.metalRichness = clampValue(system.metallicity * random.rangeDouble(0.6, 1.5), 0.0, 1.0);
        system.belts.push_back(belt);
    }

    const u32 stationCount = system.planets.empty() ? 0u : static_cast<u32>(random.rangeInt(0, 4));
    for (u32 index = 0; index < stationCount; ++index) {
        StationProfile station;
        station.seed = hashCombine(systemSeed, index + 0x5354u);
        station.orbitingPlanetIndex = static_cast<u32>(random.rangeInt(0, static_cast<i32>(system.planets.size())));
        const PlanetProfile& host = system.planets[station.orbitingPlanetIndex];
        station.orbitRadiusMeters = host.radiusMeters * random.rangeDouble(2.6, 14.0);
        station.orbitalPeriodSeconds =
            kTwoPiDouble * std::sqrt(station.orbitRadiusMeters * station.orbitRadiusMeters *
                                     station.orbitRadiusMeters / (kGravitationalConstant * host.massKilograms));
        station.radiusMeters = random.rangeDouble(320.0, 3400.0);
        station.owner = system.dominantCulture;
        station.name = generateName(station.seed, station.owner, 2, 3) + " Station";
        station.tradePost = random.chance(0.82f);
        station.shipyard = random.chance(0.34f);
        station.research = random.chance(0.28f);
        system.stations.push_back(station);
    }

    return system;
}

const char* StarSystemGenerator::starClassName(StarClass value) {
    switch (value) {
        case StarClass::O: return "O";
        case StarClass::B: return "B";
        case StarClass::A: return "A";
        case StarClass::F: return "F";
        case StarClass::G: return "G";
        case StarClass::K: return "K";
        case StarClass::M: return "M";
        case StarClass::WhiteDwarf: return "Weisser Zwerg";
        case StarClass::NeutronStar: return "Neutronenstern";
        case StarClass::Pulsar: return "Pulsar";
        case StarClass::RedGiant: return "Roter Riese";
        case StarClass::BlackHole: return "Schwarzes Loch";
        default: return "Unbekannt";
    }
}

}
