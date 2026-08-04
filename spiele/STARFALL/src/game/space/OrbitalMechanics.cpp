#include "OrbitalMechanics.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {

f64 KeplerElements::orbitalPeriodSeconds() const {
    if (semiMajorAxisMeters <= 0.0 || gravitationalParameter <= 0.0) return 0.0;
    return kTwoPiDouble * std::sqrt(semiMajorAxisMeters * semiMajorAxisMeters * semiMajorAxisMeters /
                                    gravitationalParameter);
}

f64 KeplerElements::meanAnomalyAt(f64 seconds) const {
    const f64 period = orbitalPeriodSeconds();
    if (period <= 0.0) return meanAnomalyAtEpoch;
    const f64 meanMotion = kTwoPiDouble / period;
    f64 anomaly = std::fmod(meanAnomalyAtEpoch + meanMotion * seconds, kTwoPiDouble);
    if (anomaly < 0.0) anomaly += kTwoPiDouble;
    return anomaly;
}

f64 KeplerElements::eccentricAnomalyAt(f64 seconds) const {
    return OrbitalMechanics::solveKeplerEquation(meanAnomalyAt(seconds), eccentricity);
}

f64 KeplerElements::trueAnomalyAt(f64 seconds) const {
    const f64 eccentricAnomaly = eccentricAnomalyAt(seconds);
    const f64 halfEccentric = eccentricAnomaly * 0.5;
    return 2.0 * std::atan2(std::sqrt(1.0 + eccentricity) * std::sin(halfEccentric),
                            std::sqrt(maxValue(1.0 - eccentricity, 1.0e-9)) * std::cos(halfEccentric));
}

DVec3 KeplerElements::positionAt(f64 seconds) const {
    const f64 eccentricAnomaly = eccentricAnomalyAt(seconds);
    const f64 cosineEccentric = std::cos(eccentricAnomaly);
    const f64 sineEccentric = std::sin(eccentricAnomaly);
    const f64 planarX = semiMajorAxisMeters * (cosineEccentric - eccentricity);
    const f64 planarZ = semiMajorAxisMeters * std::sqrt(maxValue(1.0 - eccentricity * eccentricity, 0.0)) * sineEccentric;

    const f64 cosineArgument = std::cos(argumentOfPeriapsis);
    const f64 sineArgument = std::sin(argumentOfPeriapsis);
    const f64 cosineNode = std::cos(longitudeOfAscendingNode);
    const f64 sineNode = std::sin(longitudeOfAscendingNode);
    const f64 cosineInclination = std::cos(inclinationRadians);
    const f64 sineInclination = std::sin(inclinationRadians);

    const f64 rotatedX = planarX * cosineArgument - planarZ * sineArgument;
    const f64 rotatedZ = planarX * sineArgument + planarZ * cosineArgument;

    const f64 inclinedY = rotatedZ * sineInclination;
    const f64 inclinedZ = rotatedZ * cosineInclination;

    return DVec3(rotatedX * cosineNode - inclinedZ * sineNode, inclinedY,
                 rotatedX * sineNode + inclinedZ * cosineNode);
}

DVec3 KeplerElements::velocityAt(f64 seconds) const {
    const f64 delta = maxValue(orbitalPeriodSeconds() * 1.0e-6, 1.0e-3);
    const DVec3 ahead = positionAt(seconds + delta);
    const DVec3 behind = positionAt(seconds - delta);
    return (ahead - behind) / (2.0 * delta);
}

f64 KeplerElements::speedAt(f64 radiusMeters) const {
    const f64 safeRadius = maxValue(radiusMeters, 1.0);
    return std::sqrt(maxValue(gravitationalParameter * (2.0 / safeRadius - 1.0 / semiMajorAxisMeters), 0.0));
}

f64 OrbitalMechanics::solveKeplerEquation(f64 meanAnomaly, f64 eccentricity, u32 maximumIterations) {
    f64 eccentricAnomaly = eccentricity < 0.8 ? meanAnomaly : kPiDouble;
    for (u32 iteration = 0; iteration < maximumIterations; ++iteration) {
        const f64 residual = eccentricAnomaly - eccentricity * std::sin(eccentricAnomaly) - meanAnomaly;
        const f64 derivative = 1.0 - eccentricity * std::cos(eccentricAnomaly);
        if (std::fabs(derivative) < 1.0e-12) break;
        const f64 correction = residual / derivative;
        eccentricAnomaly -= correction;
        if (std::fabs(correction) < 1.0e-12) break;
    }
    return eccentricAnomaly;
}

KeplerElements OrbitalMechanics::fromStateVectors(const DVec3& position, const DVec3& velocity,
                                                  f64 gravitationalParameter) {
    KeplerElements elements;
    elements.gravitationalParameter = gravitationalParameter;

    const f64 radius = length(position);
    const f64 speed = length(velocity);
    if (radius <= 0.0 || gravitationalParameter <= 0.0) return elements;

    const DVec3 angularMomentum = cross(position, velocity);
    const f64 angularMomentumMagnitude = length(angularMomentum);
    const DVec3 eccentricityVector =
        (cross(velocity, angularMomentum) / gravitationalParameter) - (position / radius);

    elements.eccentricity = clampValue(length(eccentricityVector), 0.0, 0.999);
    const f64 specificEnergy = speed * speed * 0.5 - gravitationalParameter / radius;
    elements.semiMajorAxisMeters = std::fabs(specificEnergy) > 1.0e-12
                                       ? -gravitationalParameter / (2.0 * specificEnergy)
                                       : radius;

    elements.inclinationRadians = angularMomentumMagnitude > 0.0
                                      ? std::acos(clampValue(angularMomentum.y / angularMomentumMagnitude, -1.0, 1.0))
                                      : 0.0;

    const DVec3 nodeVector = cross(DVec3::unitY(), angularMomentum);
    const f64 nodeMagnitude = length(nodeVector);
    elements.longitudeOfAscendingNode = nodeMagnitude > 1.0e-9 ? std::atan2(nodeVector.z, nodeVector.x) : 0.0;

    if (nodeMagnitude > 1.0e-9 && elements.eccentricity > 1.0e-9) {
        const f64 cosineArgument = dot(nodeVector, eccentricityVector) /
                                   (nodeMagnitude * length(eccentricityVector));
        elements.argumentOfPeriapsis = std::acos(clampValue(cosineArgument, -1.0, 1.0));
        if (eccentricityVector.y < 0.0) elements.argumentOfPeriapsis = kTwoPiDouble - elements.argumentOfPeriapsis;
    }

    if (elements.eccentricity > 1.0e-9) {
        const f64 cosineTrue = dot(eccentricityVector, position) / (length(eccentricityVector) * radius);
        f64 trueAnomaly = std::acos(clampValue(cosineTrue, -1.0, 1.0));
        if (dot(position, velocity) < 0.0) trueAnomaly = kTwoPiDouble - trueAnomaly;
        const f64 eccentricAnomaly = 2.0 * std::atan2(std::sqrt(maxValue(1.0 - elements.eccentricity, 0.0)) *
                                                          std::sin(trueAnomaly * 0.5),
                                                      std::sqrt(1.0 + elements.eccentricity) *
                                                          std::cos(trueAnomaly * 0.5));
        elements.meanAnomalyAtEpoch = eccentricAnomaly - elements.eccentricity * std::sin(eccentricAnomaly);
    }
    return elements;
}

f64 OrbitalMechanics::sphereOfInfluenceRadius(f64 bodyMass, f64 parentMass, f64 semiMajorAxis) {
    if (parentMass <= 0.0) return semiMajorAxis;
    return semiMajorAxis * std::pow(maxValue(bodyMass / parentMass, 1.0e-12), 0.4);
}

f64 OrbitalMechanics::circularOrbitSpeed(f64 gravitationalParameter, f64 radiusMeters) {
    return std::sqrt(gravitationalParameter / maxValue(radiusMeters, 1.0));
}

f64 OrbitalMechanics::escapeSpeed(f64 gravitationalParameter, f64 radiusMeters) {
    return std::sqrt(2.0 * gravitationalParameter / maxValue(radiusMeters, 1.0));
}

f64 OrbitalMechanics::hohmannTransferDeltaV(f64 gravitationalParameter, f64 fromRadius, f64 toRadius) {
    const f64 start = maxValue(fromRadius, 1.0);
    const f64 target = maxValue(toRadius, 1.0);
    const f64 firstBurn = std::sqrt(gravitationalParameter / start) *
                          (std::sqrt(2.0 * target / (start + target)) - 1.0);
    const f64 secondBurn = std::sqrt(gravitationalParameter / target) *
                           (1.0 - std::sqrt(2.0 * start / (start + target)));
    return std::fabs(firstBurn) + std::fabs(secondBurn);
}

DVec3 OrbitalMechanics::gravitationalAcceleration(const DVec3& fromPosition, const DVec3& bodyPosition, f64 bodyMass,
                                                  f64 softeningMeters) {
    const DVec3 offset = bodyPosition - fromPosition;
    const f64 distanceSquared = lengthSquared(offset) + softeningMeters * softeningMeters;
    if (distanceSquared <= 0.0) return DVec3::zero();
    const f64 distance = std::sqrt(distanceSquared);
    const f64 magnitude = kGravitationalConstant * bodyMass / distanceSquared;
    return offset / distance * magnitude;
}

f64 OrbitalMechanics::tidalAccelerationAcross(f64 bodyMass, f64 distanceMeters, f64 spanMeters) {
    const f64 safeDistance = maxValue(distanceMeters, 1.0);
    return 2.0 * kGravitationalConstant * bodyMass * spanMeters / (safeDistance * safeDistance * safeDistance);
}

}
