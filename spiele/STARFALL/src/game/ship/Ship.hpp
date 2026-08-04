#pragma once

#include "../../engine/math/DVec3.hpp"
#include "../space/HyperdriveSystem.hpp"
#include "../space/SpaceFlightController.hpp"

#include <string>
#include <vector>

namespace sf {

enum class ShipClassId : u32 {
    Explorer = 0, Fighter, Hauler, ScienceVessel, ColonyShip, CapitalShip, Count
};

enum class ShipSize : u32 {
    Small = 0, Medium, Large, Count
};

enum class ShieldSector : u32 {
    Front = 0, Rear, Left, Right, Count
};

enum class PowerConsumer : u32 {
    Engines = 0, Shields, Weapons, Sensors, LifeSupport, Auxiliary, Count
};

enum class ModuleSlot : u32 {
    Reactor = 0, Engine, ShieldGenerator, WeaponBank, Scanner, Radiator, Hyperdrive, CargoHold, Count
};

enum class UpgradeBranch : u32 {
    Propulsion = 0, Defence, Armament, Sensors, Logistics, VoidTechnology, Count
};

struct ShipModuleState {
    ModuleSlot slot = ModuleSlot::Reactor;
    f64 integrity = 1.0;
    bool online = true;
    bool onFire = false;
    f64 repairProgress = 0.0;
};

struct ShieldState {
    f64 charge[static_cast<usize>(ShieldSector::Count)] = {1.0, 1.0, 1.0, 1.0};
    f64 capacity = 1.0;
    f64 regenerationPerSecond = 0.08;
    f64 regenerationDelaySeconds = 4.0;
    f64 timeSinceHit = 10.0;
    f64 lastImpactMagnitude = 0.0;
    ShieldSector lastImpactSector = ShieldSector::Front;
};

struct PowerGridState {
    f64 reactorOutput = 1.0;
    f64 allocation[static_cast<usize>(PowerConsumer::Count)] = {0.30, 0.22, 0.18, 0.10, 0.12, 0.08};
    f64 heat = 0.0;
    f64 radiatorCapacity = 1.0;
    bool overloaded = false;
};

struct WeaponGroupState {
    std::string name;
    f64 heat = 0.0;
    f64 cooldownSeconds = 0.0;
    u32 ammunition = 0;
    u32 ammunitionCapacity = 0;
    f64 convergenceMeters = 900.0;
    bool energyBased = true;
    bool active = false;
};

struct ScannerState {
    f64 tunedFrequency = 0.5;
    f64 targetFrequency = 0.5;
    f64 lockQuality = 0.0;
    f64 scanProgress = 0.0;
    f64 range = 40000.0;
    bool scanning = false;
};

struct ShipSpecification {
    ShipClassId classId = ShipClassId::Explorer;
    ShipSize size = ShipSize::Medium;
    std::string name = "URSPRUNG";
    u32 crewMinimum = 1;
    u32 crewMaximum = 4;
    f64 hullCapacity = 1.0;
    f64 cargoCapacityTonnes = 60.0;
    f64 fuelCapacity = 4000.0;
    bool walkableInterior = true;
    u32 deckCount = 1;
    FlightVehicleSpecification flight;
    HyperdriveClass hyperdrive = HyperdriveClass::MarkOne;
};

class Ship {
public:
    void configure(const ShipSpecification& value);
    const ShipSpecification& specification() const { return spec; }

    void step(f64 stepSeconds, f64 externalShieldDrainPerSecond, f64 externalHullStressPerSecond);

    void applyDamage(f64 amount, const DVec3& impactDirectionWorld, const Quat& shipOrientation);
    bool repairModule(ModuleSlot slot, f64 progressAmount);
    void setPowerAllocation(PowerConsumer consumer, f64 fraction);
    void normalizePowerAllocation();

    void beginScan(f64 targetFrequency);
    void tuneScanner(f64 delta);
    bool scanComplete() const { return scanner.scanProgress >= 1.0; }

    bool fireGroup(u32 groupIndex);
    void setWeaponGroupActive(u32 groupIndex, bool active);

    f64 hullIntegrity() const { return hull; }
    f64 totalShieldCharge() const;
    f64 heatFraction() const { return power.heat; }
    f64 driveIntegrity() const;
    f64 massTonnes() const;
    f64 cargoFraction() const { return cargoTonnes / maxValue(spec.cargoCapacityTonnes, 0.001); }
    bool destroyed() const { return hull <= 0.0; }

    const ShieldState& shields() const { return shield; }
    const PowerGridState& powerGrid() const { return power; }
    const ScannerState& scannerState() const { return scanner; }
    const std::vector<ShipModuleState>& modules() const { return moduleStates; }
    const std::vector<WeaponGroupState>& weaponGroups() const { return weapons; }
    ScannerState& mutableScanner() { return scanner; }

    u32 upgradeLevel(UpgradeBranch branch) const { return upgrades[static_cast<usize>(branch)]; }
    bool applyUpgrade(UpgradeBranch branch);

    void setCargoTonnes(f64 value) { cargoTonnes = clampValue(value, 0.0, spec.cargoCapacityTonnes); }
    f64 cargoTonnes_() const { return cargoTonnes; }

    static ShipSpecification specificationFor(ShipClassId classId, ShipSize size);
    static const char* classIdName(ShipClassId value);
    static const char* sectorName(ShieldSector value);
    static const char* consumerName(PowerConsumer value);
    static const char* moduleName(ModuleSlot value);
    static const char* branchName(UpgradeBranch value);

private:
    ShipModuleState& moduleState(ModuleSlot slot) { return moduleStates[static_cast<usize>(slot)]; }
    const ShipModuleState& moduleState(ModuleSlot slot) const { return moduleStates[static_cast<usize>(slot)]; }

    ShipSpecification spec;
    ShieldState shield;
    PowerGridState power;
    ScannerState scanner;
    std::vector<ShipModuleState> moduleStates;
    std::vector<WeaponGroupState> weapons;
    u32 upgrades[static_cast<usize>(UpgradeBranch::Count)] = {};
    f64 hull = 1.0;
    f64 cargoTonnes = 0.0;
};

}
