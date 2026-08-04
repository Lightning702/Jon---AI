#pragma once

#include "DVec3.hpp"
#include "Scalar.hpp"

namespace sf {

struct SphericalCoords {
    f64 radius = 1.0;
    f64 polarAngle = 0.0;
    f64 azimuthAngle = 0.0;

    static SphericalCoords fromCartesian(const DVec3& position) {
        SphericalCoords result;
        result.radius = length(position);
        if (result.radius <= 0.0) return result;
        result.polarAngle = std::acos(clampValue(position.y / result.radius, -1.0, 1.0));
        result.azimuthAngle = std::atan2(position.z, position.x);
        return result;
    }

    DVec3 toCartesian() const {
        const f64 sinePolar = std::sin(polarAngle);
        return DVec3(radius * sinePolar * std::cos(azimuthAngle), radius * std::cos(polarAngle),
                     radius * sinePolar * std::sin(azimuthAngle));
    }

    f64 latitudeRadians() const { return kPiDouble * 0.5 - polarAngle; }
    f64 longitudeRadians() const { return azimuthAngle; }
    f64 latitudeDegrees() const { return latitudeRadians() * (180.0 / kPiDouble); }
    f64 longitudeDegrees() const { return azimuthAngle * (180.0 / kPiDouble); }
};

inline DVec3 cubeFaceDirection(u32 face, f64 u, f64 v) {
    const f64 a = u * 2.0 - 1.0;
    const f64 b = v * 2.0 - 1.0;
    switch (face) {
        case 0: return normalize(DVec3(1.0, -b, -a));
        case 1: return normalize(DVec3(-1.0, -b, a));
        case 2: return normalize(DVec3(a, 1.0, b));
        case 3: return normalize(DVec3(a, -1.0, -b));
        case 4: return normalize(DVec3(a, -b, 1.0));
        default: return normalize(DVec3(-a, -b, -1.0));
    }
}

inline u32 cubeFaceFromDirection(const DVec3& direction, f64& u, f64& v) {
    const f64 absoluteX = std::fabs(direction.x);
    const f64 absoluteY = std::fabs(direction.y);
    const f64 absoluteZ = std::fabs(direction.z);
    u32 face = 0;
    f64 major = absoluteX;
    if (absoluteY > major) { major = absoluteY; face = 2; }
    if (absoluteZ > major) { major = absoluteZ; face = 4; }
    if (face == 0) face = direction.x > 0.0 ? 0 : 1;
    else if (face == 2) face = direction.y > 0.0 ? 2 : 3;
    else face = direction.z > 0.0 ? 4 : 5;

    f64 a = 0.0;
    f64 b = 0.0;
    switch (face) {
        case 0: a = -direction.z / absoluteX; b = -direction.y / absoluteX; break;
        case 1: a = direction.z / absoluteX; b = -direction.y / absoluteX; break;
        case 2: a = direction.x / absoluteY; b = direction.z / absoluteY; break;
        case 3: a = direction.x / absoluteY; b = -direction.z / absoluteY; break;
        case 4: a = direction.x / absoluteZ; b = -direction.y / absoluteZ; break;
        default: a = -direction.x / absoluteZ; b = -direction.y / absoluteZ; break;
    }
    u = (a + 1.0) * 0.5;
    v = (b + 1.0) * 0.5;
    return face;
}

}
