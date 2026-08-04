#pragma once

#include "../crafting/ItemDatabase.hpp"
#include "../universe/PlanetGenerator.hpp"

namespace sf {

struct SurfaceSample {
    f64 elevationMeters = 0.0;
    f64 radiusMeters = 0.0;
    f64 temperatureKelvin = 0.0;
    f64 precipitation = 0.0;
    f64 slope = 0.0;
    BiomeType biome = BiomeType::Desert;
    bool underWater = false;
    Vec3 albedo = Vec3(0.5f, 0.5f, 0.5f);
};

class PlanetBody {
public:
    void configure(const PlanetProfile& profile, const DVec3& systemLocalPosition);

    const PlanetProfile& profile() const { return planet; }
    const DVec3& center() const { return centerPosition; }
    void setCenter(const DVec3& value) { centerPosition = value; }

    f64 seaLevelRadius() const { return planet.radiusMeters; }
    f64 terrainAmplitude() const { return amplitude; }
    f64 maximumRadius() const { return planet.radiusMeters + amplitude; }
    f64 atmosphereTopRadius() const { return planet.radiusMeters + atmosphereThickness; }

    f64 elevationAt(const DVec3& unitDirection) const;
    f64 elevationAtDetail(const DVec3& unitDirection, u32 detailLevel) const;
    f64 radiusAt(const DVec3& unitDirection) const;
    DVec3 surfacePoint(const DVec3& unitDirection) const;
    DVec3 upAt(const DVec3& localPosition) const;
    f64 altitudeAt(const DVec3& localPosition) const;
    f64 gravityMagnitudeAt(f64 radius) const;
    DVec3 gravityAt(const DVec3& localPosition) const;
    f64 atmosphericDensityAt(f64 altitudeMeters) const;
    f64 surfacePressureBar() const { return planet.atmospherePressureBar; }

    SurfaceSample sampleSurface(const DVec3& unitDirection, f64 dayPhase) const;
    SurfaceSample sampleSurfaceWithElevation(const DVec3& unitDirection, f64 dayPhase, f64 elevationMeters,
                                             f64 slope) const;
    DVec3 surfaceNormal(const DVec3& unitDirection, f64 sampleDistanceMeters) const;

    f64 dayLengthSeconds() const { return planet.rotationPeriodSeconds; }
    f64 rotationPhase(f64 universeSeconds) const;
    DVec3 sunDirectionAt(const DVec3& unitDirection, f64 universeSeconds, const DVec3& starLocalPosition) const;
    f64 sunElevationAt(const DVec3& unitDirection, f64 universeSeconds, const DVec3& starLocalPosition) const;

    f64 radiationAt(const DVec3& unitDirection, f64 dayPhase) const;
    f64 toxicityAt(const DVec3& unitDirection) const;
    f64 resourceRichness(const DVec3& unitDirection, ItemId resource) const;
    ItemId dominantResource(const DVec3& unitDirection) const;

    static Vec3 biomeAlbedo(BiomeType biome, const PlanetProfile& planet);

private:
    PlanetProfile planet;
    DVec3 centerPosition = DVec3::zero();
    f64 amplitude = 12000.0;
    f64 atmosphereThickness = 60000.0;
    f64 gravitationalParameter = 0.0;
};

}
