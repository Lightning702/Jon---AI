#include "VoidHeart.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {

VoidHeart::VoidHeart() {
    gravitationalRadius = kGravitationalConstant * massValue / (kSpeedOfLight * kSpeedOfLight);
    coordinate.x = 0;
    coordinate.y = 0;
    coordinate.z = 0;
}

void VoidHeart::configure(const SystemCoord& hostSystem, const DVec3& localPosition) {
    coordinate = hostSystem;
    position = localPosition;
}

f64 VoidHeart::horizonRadiusMeters() const {
    return gravitationalRadius * (1.0 + std::sqrt(maxValue(1.0 - spinValue * spinValue, 0.0)));
}

f64 VoidHeart::ergosphereEquatorialRadiusMeters() const {
    return gravitationalRadius * 2.0;
}

f64 VoidHeart::photonSphereRadiusMeters() const {
    return gravitationalRadius * static_cast<f64>(BlackHolePass::photonSphereRadius(static_cast<f32>(spinValue)));
}

f64 VoidHeart::innermostStableOrbitMeters() const {
    return gravitationalRadius *
           static_cast<f64>(BlackHolePass::innermostStableCircularOrbit(static_cast<f32>(spinValue)));
}

bool VoidHeart::withinInfluence(const DVec3& observerLocalPosition) const {
    return length(observerLocalPosition - position) < influenceRadiusMeters();
}

VoidHeartState VoidHeart::evaluate(const DVec3& observerLocalPosition) const {
    VoidHeartState state;
    const DVec3 offset = observerLocalPosition - position;
    const f64 distance = maxValue(length(offset), 1.0);
    state.distanceMeters = distance;
    state.radiusInGravitationalRadii = distance / gravitationalRadius;

    const f64 horizon = horizonRadiusMeters();
    const f64 ergosphere = ergosphereEquatorialRadiusMeters();
    const f64 horizonBand = horizon * 1.35;

    if (distance <= horizon) state.zone = VoidZone::EventHorizon;
    else if (distance <= horizonBand) state.zone = VoidZone::HorizonProximity;
    else if (distance <= ergosphere) state.zone = VoidZone::Ergosphere;
    else if (distance <= distortionZoneRadiusMeters()) state.zone = VoidZone::Distortion;
    else if (distance <= driftZoneRadiusMeters()) state.zone = VoidZone::GravityDrift;
    else state.zone = VoidZone::FarField;

    state.timeDilation = BlackHolePass::timeDilationFactor(state.radiusInGravitationalRadii, spinValue);

    const f64 acceleration = kGravitationalConstant * massValue / (distance * distance);
    state.gravitationalAcceleration = normalize(offset) * (-acceleration);

    const f64 angularUnit = spinValue * gravitationalRadius * kSpeedOfLight;
    state.frameDraggingAngularRate = 2.0 * angularUnit / (distance * distance * distance) * gravitationalRadius;

    const f64 shipLengthMeters = 60.0;
    state.tidalStressPerSecond = 2.0 * kGravitationalConstant * massValue * shipLengthMeters /
                                 (distance * distance * distance);

    switch (state.zone) {
        case VoidZone::FarField:
            state.instrumentNoise = 0.0;
            state.hyperdriveChargeMultiplier = 1.0;
            state.fuelConsumptionMultiplier = 1.0;
            break;
        case VoidZone::GravityDrift:
            state.instrumentNoise = 0.06;
            state.hyperdriveChargeMultiplier = 1.15;
            state.fuelConsumptionMultiplier = 1.35;
            break;
        case VoidZone::Distortion:
            state.instrumentNoise = 0.42;
            state.hyperdriveChargeMultiplier = 2.4;
            state.fuelConsumptionMultiplier = 2.1;
            state.shieldDrainPerSecond = 0.6;
            break;
        case VoidZone::Ergosphere:
            state.instrumentNoise = 0.78;
            state.hyperdriveChargeMultiplier = 5.5;
            state.fuelConsumptionMultiplier = 4.2;
            state.shieldDrainPerSecond = 4.5;
            state.voidDriveRequired = true;
            break;
        case VoidZone::HorizonProximity:
            state.instrumentNoise = 0.95;
            state.hyperdriveChargeMultiplier = 12.0;
            state.fuelConsumptionMultiplier = 9.0;
            state.shieldDrainPerSecond = 12.0;
            state.voidDriveRequired = true;
            break;
        case VoidZone::EventHorizon:
            state.instrumentNoise = 1.0;
            state.hyperdriveChargeMultiplier = 0.0;
            state.fuelConsumptionMultiplier = 0.0;
            state.shieldDrainPerSecond = 100.0;
            state.voidDriveRequired = true;
            state.escapePossible = false;
            state.timeDilation = 0.0;
            break;
    }

    return state;
}

BlackHoleRenderParameters VoidHeart::renderParameters(const DVec3& centerWorldPosition, f32 elapsedSeconds,
                                                      f32 qualityScale) const {
    BlackHoleRenderParameters parameters;
    parameters.centerWorldPosition = centerWorldPosition;
    parameters.gravitationalRadiusMeters = gravitationalRadius;
    parameters.spinParameter = static_cast<f32>(spinValue);
    parameters.diskInnerRadius = BlackHolePass::innermostStableCircularOrbit(static_cast<f32>(spinValue));
    parameters.diskOuterRadius = static_cast<f32>(accretionDiskOuterRadii);
    parameters.diskInnerTemperatureKelvin = 9800.0f;
    parameters.diskThickness = 0.055f;
    parameters.diskOpacity = 1.0f;
    parameters.diskBrightness = 26.0f;
    parameters.jetStrength = 1.0f;
    parameters.accretionRate = 1.0f;
    parameters.elapsedSeconds = elapsedSeconds;
    parameters.exposureScale = 1.0f;
    parameters.resolutionScale = clampValue(qualityScale, 0.25f, 1.0f);
    parameters.maximumSteps = static_cast<u32>(clampValue(qualityScale * 520.0f, 120.0f, 520.0f));
    parameters.stepFraction = clampValue(0.05f - qualityScale * 0.03f, 0.014f, 0.05f);
    return parameters;
}

f64 VoidHeart::orbitalSpeedAt(f64 radiusMeters) const {
    return std::sqrt(kGravitationalConstant * massValue / maxValue(radiusMeters, 1.0));
}

f64 VoidHeart::escapeSpeedAt(f64 radiusMeters) const {
    return std::sqrt(2.0 * kGravitationalConstant * massValue / maxValue(radiusMeters, 1.0));
}

const char* VoidHeart::zoneName(VoidZone zone) {
    switch (zone) {
        case VoidZone::FarField: return "FERNFELD";
        case VoidZone::GravityDrift: return "GRAVITATIONSDRIFT";
        case VoidZone::Distortion: return "VERZERRUNGSZONE";
        case VoidZone::Ergosphere: return "ERGOSPHAERE";
        case VoidZone::HorizonProximity: return "HORIZONTNAEHE";
        case VoidZone::EventHorizon: return "EREIGNISHORIZONT";
    }
    return "UNBEKANNT";
}

const char* VoidHeart::zoneDescription(VoidZone zone) {
    switch (zone) {
        case VoidZone::FarField: return "Keine Auswirkungen ausser der Sicht.";
        case VoidZone::GravityDrift: return "Langsamer Bahnzug, erhoehter Treibstoffverbrauch.";
        case VoidZone::Distortion: return "Instrumente flackern, Hyperantrieb laedt langsamer.";
        case VoidZone::Ergosphere: return "Zeitdilatation aktiv, Frame-Dragging, Schilde verlieren Energie.";
        case VoidZone::HorizonProximity: return "Gezeitenkraefte am Rumpf, Flucht nur mit Void-Antrieb.";
        case VoidZone::EventHorizon: return "Punkt ohne Wiederkehr.";
    }
    return "";
}

}
