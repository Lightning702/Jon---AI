#include "BlackHoleModel.hpp"

#include "../engine/math/Scalar.hpp"

#include <cmath>

namespace sf {
namespace {

constexpr f64 kPlanckReduced = 1.054571817e-34;
constexpr f64 kBoltzmann = 1.380649e-23;
constexpr f64 kSecondsPerYear = 3.15576e7;

}

void BlackHoleModel::setParameters(const BlackHoleParameters& value) {
    current = value;
    refresh();
}

void BlackHoleModel::refresh() {
    current.spin = clampValue(current.spin, 0.0, 0.998);
    current.massSolar = maxValue(current.massSolar, 1.0e-6);

    computed.massKilograms = current.massSolar * kSolarMass;
    computed.gravitationalRadiusMeters =
        kGravitationalConstant * computed.massKilograms / (kSpeedOfLight * kSpeedOfLight);
    computed.schwarzschildRadiusMeters = computed.gravitationalRadiusMeters * 2.0;
    computed.horizonRadii = horizonRadii(current.spin);
    computed.ergosphereEquatorialRadii = ergosphereRadii(current.spin, 0.0);
    computed.photonSphereRadii = photonSphereRadii(current.spin);
    computed.innermostStableOrbitRadii = innermostStableOrbitRadii(current.spin);
    computed.shadowAngularRadiusRadii = 2.0 * std::sqrt(27.0) / 2.0;
    computed.hawkingTemperatureKelvin = hawkingTemperature(computed.massKilograms);
    computed.evaporationYears = evaporationYears(computed.massKilograms);
    computed.diskInnerRadii = computed.innermostStableOrbitRadii;

    current.diskOuterRadii = maxValue(current.diskOuterRadii, computed.diskInnerRadii * 1.4);
}

f64 BlackHoleModel::horizonRadii(f64 spin) {
    const f64 clamped = clampValue(spin, 0.0, 0.998);
    return 1.0 + std::sqrt(maxValue(1.0 - clamped * clamped, 0.0));
}

f64 BlackHoleModel::ergosphereRadii(f64 spin, f64 polarCosine) {
    const f64 clamped = clampValue(spin, 0.0, 0.998);
    return 1.0 + std::sqrt(maxValue(1.0 - clamped * clamped * polarCosine * polarCosine, 0.0));
}

f64 BlackHoleModel::photonSphereRadii(f64 spin) {
    const f64 clamped = clampValue(spin, 0.0, 0.998);
    return 2.0 * (1.0 + std::cos((2.0 / 3.0) * std::acos(-clamped)));
}

f64 BlackHoleModel::innermostStableOrbitRadii(f64 spin) {
    const f64 clamped = clampValue(spin, 0.0, 0.998);
    const f64 factorOne = 1.0 + std::cbrt(1.0 - clamped * clamped) *
                                    (std::cbrt(1.0 + clamped) + std::cbrt(1.0 - clamped));
    const f64 factorTwo = std::sqrt(3.0 * clamped * clamped + factorOne * factorOne);
    return 3.0 + factorTwo - std::sqrt(maxValue((3.0 - factorOne) * (3.0 + factorOne + 2.0 * factorTwo), 0.0));
}

f64 BlackHoleModel::gravitationalTimeDilation(f64 radiusRadii) {
    if (radiusRadii <= 2.0) return 0.0;
    return std::sqrt(1.0 - 2.0 / radiusRadii);
}

f64 BlackHoleModel::hawkingTemperature(f64 massKilograms) {
    if (massKilograms <= 0.0) return 0.0;
    const f64 numerator = kPlanckReduced * kSpeedOfLight * kSpeedOfLight * kSpeedOfLight;
    const f64 denominator = 8.0 * kPiDouble * kGravitationalConstant * massKilograms * kBoltzmann;
    return numerator / denominator;
}

f64 BlackHoleModel::evaporationYears(f64 massKilograms) {
    if (massKilograms <= 0.0) return 0.0;
    const f64 seconds = 5120.0 * kPiDouble * std::pow(kGravitationalConstant, 2.0) * std::pow(massKilograms, 3.0) /
                        (kPlanckReduced * std::pow(kSpeedOfLight, 4.0));
    return seconds / kSecondsPerYear;
}

f64 BlackHoleModel::diskTemperatureAt(f64 radiusRadii, f64 innerRadii, f64 innerTemperature) {
    if (radiusRadii <= innerRadii) return 0.0;
    const f64 ratio = innerRadii / radiusRadii;
    const f64 edgeFalloff = 1.0 - std::sqrt(clampValue(ratio, 0.0, 1.0));
    return innerTemperature * std::pow(ratio, 0.75) * std::pow(maxValue(edgeFalloff, 1.0e-6), 0.25) * 1.85;
}

f64 BlackHoleModel::keplerianOrbitalPeriodSeconds(f64 radiusRadii, f64 spin, f64 gravitationalRadiusMeters) {
    const f64 angularRate = 1.0 / (std::pow(maxValue(radiusRadii, 1.0e-6), 1.5) + spin);
    const f64 periodInGeometricTime = kTwoPiDouble / angularRate;
    return periodInGeometricTime * gravitationalRadiusMeters / kSpeedOfLight;
}

ObserverReadout BlackHoleModel::observerAt(f64 radiusInGravitationalRadii) const {
    ObserverReadout readout;
    readout.radiusRadii = radiusInGravitationalRadii;
    readout.distanceMeters = radiusInGravitationalRadii * computed.gravitationalRadiusMeters;
    readout.gravitationalTimeDilation = gravitationalTimeDilation(radiusInGravitationalRadii);

    if (radiusInGravitationalRadii > 1.0e-6) {
        readout.circularOrbitSpeedFraction = clampValue(1.0 / std::sqrt(radiusInGravitationalRadii), 0.0, 1.0);
        readout.escapeSpeedFraction = clampValue(std::sqrt(2.0 / radiusInGravitationalRadii), 0.0, 1.0);
        readout.orbitalPeriodSeconds = keplerianOrbitalPeriodSeconds(radiusInGravitationalRadii, current.spin,
                                                                    computed.gravitationalRadiusMeters);
    }

    const f64 distance = maxValue(readout.distanceMeters, 1.0);
    readout.tidalAccelerationPerMetre =
        2.0 * kGravitationalConstant * computed.massKilograms / (distance * distance * distance);

    const f64 dilation = readout.gravitationalTimeDilation;
    readout.properAccelerationToHover =
        dilation > 1.0e-9
            ? kGravitationalConstant * computed.massKilograms / (distance * distance) / dilation
            : 0.0;

    readout.insideErgosphere = radiusInGravitationalRadii <= computed.ergosphereEquatorialRadii;
    readout.insidePhotonSphere = radiusInGravitationalRadii <= computed.photonSphereRadii;
    readout.belowInnermostStableOrbit = radiusInGravitationalRadii <= computed.innermostStableOrbitRadii;
    readout.insideHorizon = radiusInGravitationalRadii <= computed.horizonRadii;
    return readout;
}

const std::vector<BlackHoleParameters>& BlackHoleModel::presets() {
    static std::vector<BlackHoleParameters> catalogue = [] {
        std::vector<BlackHoleParameters> entries;

        BlackHoleParameters sagittarius;
        sagittarius.name = "SAGITTARIUS A*";
        sagittarius.note = "Zentrum der Milchstrasse, 26.700 Lichtjahre entfernt";
        sagittarius.massSolar = 4.297e6;
        sagittarius.spin = 0.90;
        sagittarius.accretionRate = 0.35;
        sagittarius.diskOuterRadii = 22.0;
        sagittarius.diskInnerTemperatureKelvin = 9400.0;
        sagittarius.jetStrength = 0.25;
        sagittarius.observerRadii = 40.0;
        sagittarius.inclinationDegrees = 84.0;
        entries.push_back(sagittarius);

        BlackHoleParameters messier;
        messier.name = "M87*";
        messier.note = "Erstes direkt abgebildetes Schwarzes Loch, 2019";
        messier.massSolar = 6.5e9;
        messier.spin = 0.94;
        messier.accretionRate = 1.4;
        messier.diskOuterRadii = 30.0;
        messier.diskInnerTemperatureKelvin = 8200.0;
        messier.jetStrength = 2.4;
        messier.observerRadii = 46.0;
        messier.inclinationDegrees = 73.0;
        entries.push_back(messier);

        BlackHoleParameters cygnus;
        cygnus.name = "CYGNUS X-1";
        cygnus.note = "Stellares Schwarzes Loch mit Begleitstern";
        cygnus.massSolar = 21.2;
        cygnus.spin = 0.95;
        cygnus.accretionRate = 2.6;
        cygnus.diskOuterRadii = 34.0;
        cygnus.diskInnerTemperatureKelvin = 12500.0;
        cygnus.jetStrength = 1.2;
        cygnus.observerRadii = 38.0;
        cygnus.inclinationDegrees = 68.0;
        entries.push_back(cygnus);

        BlackHoleParameters schwarzschild;
        schwarzschild.name = "SCHWARZSCHILD";
        schwarzschild.note = "Ohne Drehimpuls, ISCO bei genau 6 r_g";
        schwarzschild.massSolar = 1.0e6;
        schwarzschild.spin = 0.0;
        schwarzschild.accretionRate = 1.0;
        schwarzschild.diskOuterRadii = 28.0;
        schwarzschild.diskInnerTemperatureKelvin = 9800.0;
        schwarzschild.jetStrength = 0.0;
        schwarzschild.observerRadii = 44.0;
        schwarzschild.inclinationDegrees = 80.0;
        entries.push_back(schwarzschild);

        BlackHoleParameters extremal;
        extremal.name = "NAHEZU EXTREMAL";
        extremal.note = "Spin 0,998, Thorne-Grenze der Akkretion";
        extremal.massSolar = 4.1e6;
        extremal.spin = 0.998;
        extremal.accretionRate = 1.8;
        extremal.diskOuterRadii = 26.0;
        extremal.diskInnerTemperatureKelvin = 11000.0;
        extremal.jetStrength = 1.8;
        extremal.observerRadii = 30.0;
        extremal.inclinationDegrees = 86.0;
        entries.push_back(extremal);

        BlackHoleParameters voidHeart;
        voidHeart.name = "THE VOID HEART";
        voidHeart.note = "Frei erfunden, 4,1 Millionen Sonnenmassen, Spin 0,94";
        voidHeart.massSolar = 4.1e6;
        voidHeart.spin = 0.94;
        voidHeart.accretionRate = 1.0;
        voidHeart.diskOuterRadii = 26.0;
        voidHeart.diskInnerTemperatureKelvin = 9800.0;
        voidHeart.jetStrength = 1.0;
        voidHeart.observerRadii = 42.0;
        voidHeart.inclinationDegrees = 84.0;
        entries.push_back(voidHeart);

        return entries;
    }();
    return catalogue;
}

const char* BlackHoleModel::zoneLabel(const BlackHoleDerived& derivedValues, f64 radiusRadii) {
    if (radiusRadii <= derivedValues.horizonRadii) return "INNERHALB DES HORIZONTS";
    if (radiusRadii <= derivedValues.photonSphereRadii) return "PHOTONENSPHAERE";
    if (radiusRadii <= derivedValues.ergosphereEquatorialRadii) return "ERGOSPHAERE";
    if (radiusRadii <= derivedValues.innermostStableOrbitRadii) return "UNTERHALB DER ISCO";
    if (radiusRadii <= 20.0) return "INNERE AKKRETIONSSCHEIBE";
    if (radiusRadii <= 120.0) return "AEUSSERE SCHEIBE";
    return "FERNFELD";
}

}
