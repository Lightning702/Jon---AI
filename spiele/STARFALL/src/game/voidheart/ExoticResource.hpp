#pragma once

#include "../../engine/core/Types.hpp"

#include <string>
#include <vector>

namespace sf {

enum class ExoticResourceId : u32 {
    VoidMatter = 0,
    ChrononCrystal,
    SingularityCore,
    LensedAlloy,
    HorizonDust,
    Count
};

struct ExoticResourceDefinition {
    ExoticResourceId id = ExoticResourceId::VoidMatter;
    std::string name;
    std::string description;
    std::string harvestLocation;
    f64 unitMassKilograms = 1.0;
    f64 baseValue = 1000.0;
    f64 minimumZoneRadiusInGravitationalRadii = 90.0;
    bool requiresVoidDrive = false;
};

class ExoticResourceLedger {
public:
    ExoticResourceLedger();

    const std::vector<ExoticResourceDefinition>& definitions() const { return catalogue; }
    const ExoticResourceDefinition& definition(ExoticResourceId id) const {
        return catalogue[static_cast<usize>(id)];
    }

    void add(ExoticResourceId id, f64 quantity);
    bool consume(ExoticResourceId id, f64 quantity);
    f64 quantity(ExoticResourceId id) const { return amounts[static_cast<usize>(id)]; }
    f64 totalValue() const;
    f64 totalMassKilograms() const;
    void clear();

    static f64 harvestRatePerSecond(ExoticResourceId id, f64 radiusInGravitationalRadii, f64 scannerQuality);

private:
    std::vector<ExoticResourceDefinition> catalogue;
    f64 amounts[static_cast<usize>(ExoticResourceId::Count)] = {};
};

}
