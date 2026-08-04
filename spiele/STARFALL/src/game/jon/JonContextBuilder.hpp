#pragma once

#include "../../engine/net/Json.hpp"
#include "../ship/Ship.hpp"
#include "../voidheart/VoidHeart.hpp"

#include <string>
#include <vector>

namespace sf {

struct JonWorldContext {
    std::string systemName;
    std::string starClass;
    std::string nearestBodyName;
    std::string planetClass;
    f64 distanceToNearestBodyMeters = 0.0;
    f64 speedMetresPerSecond = 0.0;
    f64 hullIntegrity = 1.0;
    f64 shieldCharge = 1.0;
    f64 fuelKilograms = 0.0;
    f64 fuelCapacity = 1.0;
    f64 heatFraction = 0.0;
    f64 oxygenFraction = 1.0;
    f64 habitability = 0.0;
    f64 radiationSieverts = 0.0;
    f64 surfaceTemperatureKelvin = 0.0;
    f64 surfaceGravity = 0.0;
    f64 timeDilation = 1.0;
    f64 hullStress = 0.0;
    f64 tidalStress = 0.0;
    VoidZone voidZone = VoidZone::FarField;
    bool inAtmosphere = false;
    bool communicationBlackout = false;
    bool voidDriveInstalled = false;
    u32 discoveredStations = 0;
    u32 completedEndgameMissions = 0;
    u32 researchTier = 1;
    std::vector<std::string> recentEvents;
};

class JonContextBuilder {
public:
    JsonValue buildRequestPayload(const JonWorldContext& context, const std::string& playerMessage) const;
    std::string buildSummaryLine(const JonWorldContext& context) const;
    std::string buildSystemPrompt() const;
};

}
