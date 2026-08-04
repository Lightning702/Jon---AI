#pragma once

#include "../../engine/math/DVec3.hpp"

namespace sf {

struct KeplerElements {
    f64 semiMajorAxisMeters = 1.0e9;
    f64 eccentricity = 0.0;
    f64 inclinationRadians = 0.0;
    f64 longitudeOfAscendingNode = 0.0;
    f64 argumentOfPeriapsis = 0.0;
    f64 meanAnomalyAtEpoch = 0.0;
    f64 gravitationalParameter = 3.986e14;

    f64 orbitalPeriodSeconds() const;
    f64 periapsisMeters() const { return semiMajorAxisMeters * (1.0 - eccentricity); }
    f64 apoapsisMeters() const { return semiMajorAxisMeters * (1.0 + eccentricity); }
    f64 meanAnomalyAt(f64 seconds) const;
    f64 eccentricAnomalyAt(f64 seconds) const;
    f64 trueAnomalyAt(f64 seconds) const;
    DVec3 positionAt(f64 seconds) const;
    DVec3 velocityAt(f64 seconds) const;
    f64 speedAt(f64 radiusMeters) const;
};

class OrbitalMechanics {
public:
    static f64 solveKeplerEquation(f64 meanAnomaly, f64 eccentricity, u32 maximumIterations = 24);
    static KeplerElements fromStateVectors(const DVec3& position, const DVec3& velocity,
                                           f64 gravitationalParameter);
    static f64 sphereOfInfluenceRadius(f64 bodyMass, f64 parentMass, f64 semiMajorAxis);
    static f64 circularOrbitSpeed(f64 gravitationalParameter, f64 radiusMeters);
    static f64 escapeSpeed(f64 gravitationalParameter, f64 radiusMeters);
    static f64 hohmannTransferDeltaV(f64 gravitationalParameter, f64 fromRadius, f64 toRadius);
    static DVec3 gravitationalAcceleration(const DVec3& fromPosition, const DVec3& bodyPosition, f64 bodyMass,
                                           f64 softeningMeters);
    static f64 tidalAccelerationAcross(f64 bodyMass, f64 distanceMeters, f64 spanMeters);
};

}
