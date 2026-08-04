#pragma once

#include "VoidHeart.hpp"

#include <vector>

namespace sf {

enum class VoidStationId : u32 {
    HorizonWatch = 0,
    TheAnchor,
    NullFoundry,
    LastLight,
    Count
};

struct VoidStationLogEntry {
    std::string author;
    std::string text;
};

struct VoidStationProfile {
    VoidStationId id = VoidStationId::HorizonWatch;
    std::string name;
    std::string purpose;
    std::string architecture;
    f64 orbitRadiusInGravitationalRadii = 120.0;
    f64 orbitalInclinationRadians = 0.0;
    f64 orbitalPhaseRadians = 0.0;
    f64 radiusMeters = 2400.0;
    bool discovered = false;
    bool interiorCleared = false;
    u32 puzzleStages = 3;
    u32 puzzleStagesSolved = 0;
    std::string reward;
    std::vector<VoidStationLogEntry> logbook;

    DVec3 positionAt(const VoidHeart& heart, f64 universeSeconds) const;
    f64 orbitalPeriodSeconds(const VoidHeart& heart) const;
};

class VoidStationRegistry {
public:
    VoidStationRegistry();

    const std::vector<VoidStationProfile>& stations() const { return entries; }
    std::vector<VoidStationProfile>& mutableStations() { return entries; }
    const VoidStationProfile& station(VoidStationId id) const { return entries[static_cast<usize>(id)]; }
    VoidStationProfile& mutableStation(VoidStationId id) { return entries[static_cast<usize>(id)]; }

    bool markDiscovered(VoidStationId id);
    bool solveStage(VoidStationId id);
    u32 discoveredCount() const;
    u32 clearedCount() const;
    bool voidDriveBlueprintUnlocked() const;

private:
    std::vector<VoidStationProfile> entries;
};

}
