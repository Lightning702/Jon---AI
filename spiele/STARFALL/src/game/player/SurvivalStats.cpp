#include "SurvivalStats.hpp"

#include "../../engine/math/Scalar.hpp"

#include <cstdio>

namespace sf {

void SurvivalStats::reset() {
    healthValue = 1.0;
    lifeSupportValue = 1.0;
    hazardProtectionValue = 1.0;
    staminaValue = 1.0;
    jetpackFuelValue = 1.0;
    oxygenReserveValue = 1.0;
    hazardSeverityValue = 0.0;
    damageAccumulator = 0.0;
    currentHazard = HazardKind::None;
    warningText.clear();
}

void SurvivalStats::setSuitUpgrades(u32 lifeSupportTier, u32 hazardTier, u32 jetpackTier) {
    lifeSupportUpgrade = clampValue(lifeSupportTier, 0u, 5u);
    hazardUpgrade = clampValue(hazardTier, 0u, 5u);
    jetpackUpgrade = clampValue(jetpackTier, 0u, 5u);
}

HazardKind SurvivalStats::classifyHazard(const EnvironmentReading& environment, f64& severityOut) {
    struct Candidate {
        HazardKind kind;
        f64 severity;
    };

    const f64 heat = clampValue((environment.temperatureKelvin - 318.0) / 90.0, 0.0, 3.0);
    const f64 cold = clampValue((248.0 - environment.temperatureKelvin) / 90.0, 0.0, 3.0);
    const f64 toxic = clampValue(environment.toxicity * 1.2, 0.0, 3.0);
    const f64 radiation = clampValue(environment.radiationSieverts * 1.6, 0.0, 3.0);
    const f64 vacuum = environment.pressureBar < 0.08 ? clampValue((0.08 - environment.pressureBar) * 14.0, 0.0, 3.0) : 0.0;
    const f64 pressure = environment.pressureBar > 6.0 ? clampValue((environment.pressureBar - 6.0) / 20.0, 0.0, 3.0) : 0.0;

    const Candidate candidates[] = {{HazardKind::Heat, heat},         {HazardKind::Cold, cold},
                                    {HazardKind::Toxic, toxic},       {HazardKind::Radiation, radiation},
                                    {HazardKind::Vacuum, vacuum},     {HazardKind::Pressure, pressure}};

    HazardKind best = HazardKind::None;
    f64 bestSeverity = 0.0;
    for (const Candidate& candidate : candidates) {
        if (candidate.severity <= bestSeverity) continue;
        bestSeverity = candidate.severity;
        best = candidate.kind;
    }
    severityOut = bestSeverity;
    return bestSeverity > 0.02 ? best : HazardKind::None;
}

void SurvivalStats::step(f64 stepSeconds, const EnvironmentReading& environment, bool sprinting,
                         bool jetpackActive) {
    if (stepSeconds <= 0.0) return;

    currentHazard = classifyHazard(environment, hazardSeverityValue);
    const f64 hazardResistance = 1.0 + static_cast<f64>(hazardUpgrade) * 0.55;
    const f64 lifeSupportEfficiency = 1.0 + static_cast<f64>(lifeSupportUpgrade) * 0.45;

    if (environment.inShelter) {
        lifeSupportValue = clampValue(lifeSupportValue + 0.09 * stepSeconds, 0.0, 1.0);
        hazardProtectionValue = clampValue(hazardProtectionValue + 0.12 * stepSeconds, 0.0, 1.0);
        oxygenReserveValue = clampValue(oxygenReserveValue + 0.14 * stepSeconds, 0.0, 1.0);
    } else {
        const f64 drain = (0.0042 + (currentHazard == HazardKind::Vacuum ? 0.010 : 0.0)) / lifeSupportEfficiency;
        lifeSupportValue = clampValue(lifeSupportValue - drain * stepSeconds, 0.0, 1.0);

        if (currentHazard != HazardKind::None) {
            const f64 hazardDrain = hazardSeverityValue * 0.052 / hazardResistance;
            hazardProtectionValue = clampValue(hazardProtectionValue - hazardDrain * stepSeconds, 0.0, 1.0);
        } else {
            hazardProtectionValue = clampValue(hazardProtectionValue + 0.02 * stepSeconds, 0.0, 1.0);
        }
    }

    const bool breathable = environment.oxygenFraction > 0.16 && environment.pressureBar > 0.5 &&
                            !environment.underWater;
    if (environment.underWater || !breathable) {
        oxygenReserveValue = clampValue(oxygenReserveValue - 0.028 * stepSeconds, 0.0, 1.0);
    } else {
        oxygenReserveValue = clampValue(oxygenReserveValue + 0.11 * stepSeconds, 0.0, 1.0);
    }

    if (sprinting) {
        staminaValue = clampValue(staminaValue - 0.18 * stepSeconds, 0.0, 1.0);
    } else {
        staminaValue = clampValue(staminaValue + 0.13 * stepSeconds, 0.0, 1.0);
    }

    if (jetpackActive) {
        jetpackFuelValue = clampValue(jetpackFuelValue - 0.30 * stepSeconds, 0.0, 1.0);
    } else {
        const f64 refill = 0.16 * (1.0 + static_cast<f64>(jetpackUpgrade) * 0.35);
        jetpackFuelValue = clampValue(jetpackFuelValue + refill * stepSeconds, 0.0, 1.0);
    }

    f64 damagePerSecond = 0.0;
    warningText.clear();
    char buffer[160];

    if (lifeSupportValue <= 0.0) {
        damagePerSecond += 0.085;
        warningText = "LEBENSERHALTUNG AUSGEFALLEN";
    } else if (lifeSupportValue < 0.2) {
        std::snprintf(buffer, sizeof(buffer), "LEBENSERHALTUNG %.0f%%", lifeSupportValue * 100.0);
        warningText = buffer;
    }

    if (oxygenReserveValue <= 0.0) {
        damagePerSecond += 0.12;
        warningText = "SAUERSTOFF LEER";
    } else if (oxygenReserveValue < 0.25 && warningText.empty()) {
        std::snprintf(buffer, sizeof(buffer), "SAUERSTOFF %.0f%%", oxygenReserveValue * 100.0);
        warningText = buffer;
    }

    if (currentHazard != HazardKind::None && hazardProtectionValue <= 0.0) {
        damagePerSecond += 0.055 * hazardSeverityValue;
        std::snprintf(buffer, sizeof(buffer), "%s OHNE SCHUTZ", hazardName(currentHazard));
        warningText = buffer;
    } else if (currentHazard != HazardKind::None && hazardProtectionValue < 0.25 && warningText.empty()) {
        std::snprintf(buffer, sizeof(buffer), "%s SCHUTZ %.0f%%", hazardName(currentHazard),
                      hazardProtectionValue * 100.0);
        warningText = buffer;
    }

    if (damagePerSecond > 0.0) {
        healthValue = clampValue(healthValue - damagePerSecond * stepSeconds, 0.0, 1.0);
    } else if (environment.inShelter) {
        healthValue = clampValue(healthValue + 0.03 * stepSeconds, 0.0, 1.0);
    }
}

void SurvivalStats::applyDamage(f64 amount) {
    healthValue = clampValue(healthValue - amount, 0.0, 1.0);
}

void SurvivalStats::heal(f64 amount) {
    healthValue = clampValue(healthValue + amount, 0.0, 1.0);
}

bool SurvivalStats::consumeItem(ItemId id, Inventory& inventory) {
    if (inventory.count(id) == 0) return false;
    switch (id) {
        case ItemId::LifeSupportGel:
            inventory.remove(id, 1);
            rechargeLifeSupport(1.0);
            return true;
        case ItemId::HazardCapsule:
            inventory.remove(id, 1);
            rechargeHazardProtection(1.0);
            return true;
        case ItemId::Ration:
            inventory.remove(id, 1);
            heal(0.35);
            staminaValue = 1.0;
            return true;
        case ItemId::Oxygen:
            if (inventory.count(id) < 25) return false;
            inventory.remove(id, 25);
            oxygenReserveValue = clampValue(oxygenReserveValue + 0.5, 0.0, 1.0);
            return true;
        case ItemId::CondensedCarbon:
            if (inventory.count(id) < 10) return false;
            inventory.remove(id, 10);
            rechargeLifeSupport(0.45);
            return true;
        default:
            return false;
    }
}

const char* SurvivalStats::hazardName(HazardKind hazard) {
    switch (hazard) {
        case HazardKind::Heat: return "HITZE";
        case HazardKind::Cold: return "KAELTE";
        case HazardKind::Toxic: return "GIFT";
        case HazardKind::Radiation: return "STRAHLUNG";
        case HazardKind::Vacuum: return "VAKUUM";
        case HazardKind::Pressure: return "DRUCK";
        default: return "KEINE";
    }
}

}
