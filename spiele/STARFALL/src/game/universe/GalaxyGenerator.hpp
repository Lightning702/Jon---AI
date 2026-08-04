#pragma once

#include "StarSystemGenerator.hpp"

namespace sf {

enum class GalaxyType : u32 {
    Spiral = 0, BarredSpiral, Elliptical, Irregular, Ring, Dwarf, Count
};

struct GalaxyProfile {
    u32 index = 0;
    u64 seed = 0;
    std::string name;
    GalaxyType type = GalaxyType::BarredSpiral;
    f64 radiusLightYears = 52000.0;
    f64 thicknessLightYears = 1100.0;
    u32 armCount = 4;
    f64 armWindingTightness = 0.22;
    f64 coreRadiusLightYears = 4200.0;
    f64 barLengthLightYears = 8500.0;
    f64 coreMetallicity = 1.0;
    f64 haloDensity = 0.04;
    f64 estimatedStarCount = 2.4e11;
    Vec3 coreColor = Vec3(1.0f, 0.86f, 0.62f);
    Vec3 armColor = Vec3(0.62f, 0.74f, 1.0f);
    Vec3 dustColor = Vec3(0.28f, 0.18f, 0.12f);
    bool hostsVoidHeart = false;
};

class GalaxyGenerator {
public:
    GalaxyProfile generate(const UniverseSeed& universe, u32 galaxyIndex) const;

    static f64 stellarDensity(const GalaxyProfile& galaxy, const DVec3& positionLightYears);
    static bool sampleStarAt(const GalaxyProfile& galaxy, const SystemCoord& coordinate);
    static std::vector<SystemCoord> sampleNeighbourhood(const GalaxyProfile& galaxy, const SystemCoord& center,
                                                        i64 radiusLightYears, usize maximumCount);
    static const char* galaxyTypeName(GalaxyType value);
};

}
