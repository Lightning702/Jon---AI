#pragma once

#include "../../engine/math/Scalar.hpp"
#include "Inventory.hpp"

#include <string>
#include <vector>

namespace sf {

enum class HazardKind : u32 {
    None = 0,
    Heat,
    Cold,
    Toxic,
    Radiation,
    Vacuum,
    Pressure,
    Count
};

struct EnvironmentReading {
    f64 temperatureKelvin = 288.0;
    f64 radiationSieverts = 0.0;
    f64 toxicity = 0.0;
    f64 pressureBar = 1.0;
    f64 oxygenFraction = 0.21;
    bool underWater = false;
    bool inShelter = false;
};

class SurvivalStats {
public:
    void reset();

    void step(f64 stepSeconds, const EnvironmentReading& environment, bool sprinting, bool jetpackActive);

    f64 health() const { return healthValue; }
    f64 lifeSupport() const { return lifeSupportValue; }
    f64 hazardProtection() const { return hazardProtectionValue; }
    f64 stamina() const { return staminaValue; }
    f64 jetpackFuel() const { return jetpackFuelValue; }
    f64 oxygenReserve() const { return oxygenReserveValue; }
    HazardKind activeHazard() const { return currentHazard; }
    f64 hazardSeverity() const { return hazardSeverityValue; }
    bool dead() const { return healthValue <= 0.0; }
    const std::string& lastWarning() const { return warningText; }

    void applyDamage(f64 amount);
    void heal(f64 amount);
    bool consumeItem(ItemId id, Inventory& inventory);
    void rechargeLifeSupport(f64 fraction) { lifeSupportValue = clampValue(lifeSupportValue + fraction, 0.0, 1.0); }
    void rechargeHazardProtection(f64 fraction) {
        hazardProtectionValue = clampValue(hazardProtectionValue + fraction, 0.0, 1.0);
    }
    void refillJetpack(f64 fraction) { jetpackFuelValue = clampValue(jetpackFuelValue + fraction, 0.0, 1.0); }

    void setSuitUpgrades(u32 lifeSupportTier, u32 hazardTier, u32 jetpackTier);
    u32 lifeSupportTier() const { return lifeSupportUpgrade; }
    u32 hazardTier() const { return hazardUpgrade; }
    u32 jetpackTier() const { return jetpackUpgrade; }

    static const char* hazardName(HazardKind hazard);
    static HazardKind classifyHazard(const EnvironmentReading& environment, f64& severityOut);

private:
    f64 healthValue = 1.0;
    f64 lifeSupportValue = 1.0;
    f64 hazardProtectionValue = 1.0;
    f64 staminaValue = 1.0;
    f64 jetpackFuelValue = 1.0;
    f64 oxygenReserveValue = 1.0;
    f64 hazardSeverityValue = 0.0;
    f64 damageAccumulator = 0.0;
    HazardKind currentHazard = HazardKind::None;
    std::string warningText;
    u32 lifeSupportUpgrade = 0;
    u32 hazardUpgrade = 0;
    u32 jetpackUpgrade = 0;
};

}
