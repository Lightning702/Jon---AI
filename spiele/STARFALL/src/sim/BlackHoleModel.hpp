#pragma once

#include "../engine/core/Types.hpp"

#include <string>
#include <vector>

namespace sf {

struct BlackHoleParameters {
    std::string name = "Sagittarius A*";
    std::string note;
    f64 massSolar = 4.297e6;
    f64 spin = 0.90;
    f64 accretionRate = 1.0;
    f64 diskOuterRadii = 26.0;
    f64 diskInnerTemperatureKelvin = 9800.0;
    f64 diskThickness = 0.055;
    f64 jetStrength = 1.0;
    f64 observerRadii = 42.0;
    f64 inclinationDegrees = 84.0;
};

struct BlackHoleDerived {
    f64 massKilograms = 0.0;
    f64 gravitationalRadiusMeters = 0.0;
    f64 schwarzschildRadiusMeters = 0.0;
    f64 horizonRadii = 2.0;
    f64 ergosphereEquatorialRadii = 2.0;
    f64 photonSphereRadii = 3.0;
    f64 innermostStableOrbitRadii = 6.0;
    f64 shadowAngularRadiusRadii = 5.196;
    f64 hawkingTemperatureKelvin = 0.0;
    f64 evaporationYears = 0.0;
    f64 diskInnerRadii = 6.0;
};

struct ObserverReadout {
    f64 radiusRadii = 42.0;
    f64 distanceMeters = 0.0;
    f64 gravitationalTimeDilation = 1.0;
    f64 circularOrbitSpeedFraction = 0.0;
    f64 escapeSpeedFraction = 0.0;
    f64 orbitalPeriodSeconds = 0.0;
    f64 tidalAccelerationPerMetre = 0.0;
    f64 properAccelerationToHover = 0.0;
    bool insideErgosphere = false;
    bool insidePhotonSphere = false;
    bool belowInnermostStableOrbit = false;
    bool insideHorizon = false;
};

class BlackHoleModel {
public:
    void setParameters(const BlackHoleParameters& value);
    const BlackHoleParameters& parameters() const { return current; }
    BlackHoleParameters& mutableParameters() { return current; }
    void refresh();

    const BlackHoleDerived& derived() const { return computed; }
    ObserverReadout observerAt(f64 radiusInGravitationalRadii) const;

    static f64 horizonRadii(f64 spin);
    static f64 ergosphereRadii(f64 spin, f64 polarCosine);
    static f64 photonSphereRadii(f64 spin);
    static f64 innermostStableOrbitRadii(f64 spin);
    static f64 gravitationalTimeDilation(f64 radiusRadii);
    static f64 hawkingTemperature(f64 massKilograms);
    static f64 evaporationYears(f64 massKilograms);
    static f64 pageThorneFlux(f64 radiusRadii, f64 innerRadii, f64 spin);
    static f64 diskTemperatureAt(f64 radiusRadii, f64 innerRadii, f64 innerTemperature, f64 spin);
    static f64 keplerianOrbitalPeriodSeconds(f64 radiusRadii, f64 spin, f64 gravitationalRadiusMeters);

    static const std::vector<BlackHoleParameters>& presets();
    static const char* zoneLabel(const BlackHoleDerived& derived, f64 radiusRadii);

private:
    BlackHoleParameters current;
    BlackHoleDerived computed;
};

}
