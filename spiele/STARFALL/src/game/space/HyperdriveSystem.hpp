#pragma once

#include "../universe/CoordinateSpace.hpp"

#include <string>
#include <vector>

namespace sf {

enum class HyperdriveClass : u32 {
    MarkOne = 0,
    MarkTwo,
    MarkThree,
    MarkFour,
    VoidDrive,
    Count
};

enum class HyperdrivePhase : u32 {
    Idle = 0,
    Charging,
    Aligning,
    Tunnelling,
    Exiting,
    Cooldown
};

enum class JumpDenialReason : u32 {
    None = 0,
    OutOfRange,
    InsufficientFuel,
    MassLock,
    RestrictedSpace,
    DriveDamaged,
    VoidDriveRequired
};

enum class TransitHazard : u32 {
    None = 0,
    MassEjection,
    Anomaly,
    Interdiction,
    NebulaInterference,
    VoidEcho,
    RadiationBurst
};

enum class FuelType : u32 {
    Deuterium = 0,
    Tritium,
    VoidMatter,
    Count
};

struct HyperdriveSpecification {
    HyperdriveClass driveClass = HyperdriveClass::MarkOne;
    f64 rangeLightYears = 8.0;
    f64 baseChargeSeconds = 6.0;
    f64 baseFuelCost = 1.0;
    FuelType fuel = FuelType::Deuterium;
    bool worksInVoidZone = false;
};

struct RouteLeg {
    SystemCoord target;
    f64 distanceLightYears = 0.0;
    f64 fuelCost = 0.0;
    f64 hazardRating = 0.0;
    bool refuelStop = false;
};

struct HyperRoute {
    std::vector<RouteLeg> legs;
    f64 totalDistanceLightYears = 0.0;
    f64 totalFuelCost = 0.0;
    f64 estimatedSeconds = 0.0;
    f64 averageHazard = 0.0;
    bool reachable = false;
};

enum class RoutePreference : u32 {
    Shortest = 0,
    Economical,
    Safest
};

struct HyperdriveState {
    HyperdrivePhase phase = HyperdrivePhase::Idle;
    f64 chargeSeconds = 0.0;
    f64 requiredChargeSeconds = 0.0;
    f64 transitSeconds = 0.0;
    f64 requiredTransitSeconds = 0.0;
    f64 cooldownSeconds = 0.0;
    f64 alignmentDegrees = 180.0;
    f64 shieldOfflineSeconds = 0.0;
    f64 weaponsOfflineSeconds = 0.0;
    TransitHazard activeHazard = TransitHazard::None;
    SystemCoord destination;
    f64 warpFactor = 0.0;
};

class HyperdriveSystem {
public:
    void setSpecification(const HyperdriveSpecification& value) { specification = value; }
    const HyperdriveSpecification& driveSpecification() const { return specification; }
    static HyperdriveSpecification specificationFor(HyperdriveClass driveClass);

    JumpDenialReason evaluateJump(const SystemCoord& from, const SystemCoord& to, f64 availableFuel,
                                  f64 shipMassTonnes, f64 massLockStrength, f64 driveIntegrity,
                                  bool insideVoidZone) const;

    f64 energyCost(f64 distanceLightYears, f64 shipMassTonnes, f64 cargoFraction, f64 driveIntegrity) const;
    f64 chargeSecondsFor(f64 distanceLightYears, f64 zoneMultiplier) const;

    bool beginJump(HyperdriveState& state, const SystemCoord& destination, f64 distanceLightYears,
                   f64 zoneMultiplier);
    void abortJump(HyperdriveState& state) const;
    void update(HyperdriveState& state, f64 stepSeconds, f64 alignmentDegrees, u64 randomSeed) const;

    static const char* driveClassName(HyperdriveClass value);
    static const char* hazardName(TransitHazard value);
    static const char* hazardResolution(TransitHazard value);
    static const char* fuelName(FuelType value);
    static const char* denialReasonText(JumpDenialReason value);

    static f64 distanceLightYears(const SystemCoord& from, const SystemCoord& to);

private:
    HyperdriveSpecification specification = specificationFor(HyperdriveClass::MarkOne);
};

class HyperRouteSolver {
public:
    struct StarNode {
        SystemCoord coordinate;
        f64 hazardRating = 0.0;
        bool hasRefuel = false;
        bool restricted = false;
        bool surveyed = false;
    };

    void setNodes(std::vector<StarNode> value) { nodes = std::move(value); }
    const std::vector<StarNode>& starNodes() const { return nodes; }

    HyperRoute solve(const SystemCoord& from, const SystemCoord& to, f64 jumpRangeLightYears,
                     f64 fuelBudget, RoutePreference preference) const;

private:
    f64 edgeWeight(const StarNode& from, const StarNode& to, f64 distance, RoutePreference preference) const;

    std::vector<StarNode> nodes;
};

}
