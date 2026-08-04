#include "Ship.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {

void Ship::configure(const ShipSpecification& value) {
    spec = value;
    hull = 1.0;
    cargoTonnes = 0.0;

    moduleStates.clear();
    moduleStates.resize(static_cast<usize>(ModuleSlot::Count));
    for (usize index = 0; index < moduleStates.size(); ++index) {
        moduleStates[index].slot = static_cast<ModuleSlot>(index);
        moduleStates[index].integrity = 1.0;
        moduleStates[index].online = true;
    }

    shield = ShieldState();
    power = PowerGridState();
    scanner = ScannerState();

    weapons.clear();
    WeaponGroupState pulse;
    pulse.name = "PULSLASER";
    pulse.energyBased = true;
    pulse.active = true;
    weapons.push_back(pulse);

    WeaponGroupState autocannon;
    autocannon.name = "AUTOKANONE";
    autocannon.energyBased = false;
    autocannon.ammunitionCapacity = 2400;
    autocannon.ammunition = 2400;
    weapons.push_back(autocannon);

    WeaponGroupState missiles;
    missiles.name = "LENKRAKETEN";
    missiles.energyBased = false;
    missiles.ammunitionCapacity = 24;
    missiles.ammunition = 24;
    weapons.push_back(missiles);

    WeaponGroupState railgun;
    railgun.name = "RAILGUN";
    railgun.energyBased = true;
    railgun.convergenceMeters = 3200.0;
    weapons.push_back(railgun);

    WeaponGroupState support;
    support.name = "HILFSSYSTEME";
    support.energyBased = true;
    support.ammunitionCapacity = 8;
    support.ammunition = 8;
    weapons.push_back(support);

    for (u32& level : upgrades) level = 0;
}

ShipSpecification Ship::specificationFor(ShipClassId classId, ShipSize size) {
    ShipSpecification specification;
    specification.classId = classId;
    specification.size = size;

    const f64 sizeScale = size == ShipSize::Small ? 0.62 : (size == ShipSize::Large ? 2.4 : 1.0);

    switch (classId) {
        case ShipClassId::Explorer:
            specification.name = "EXPLORER";
            specification.crewMinimum = 1;
            specification.crewMaximum = 4;
            specification.cargoCapacityTonnes = 60.0 * sizeScale;
            specification.flight.dryMassKilograms = 42000.0 * sizeScale;
            specification.flight.mainThrustNewtons = 2.6e6 * sizeScale;
            specification.hyperdrive = HyperdriveClass::MarkTwo;
            break;
        case ShipClassId::Fighter:
            specification.name = "FIGHTER";
            specification.crewMinimum = 1;
            specification.crewMaximum = 2;
            specification.cargoCapacityTonnes = 12.0 * sizeScale;
            specification.flight.dryMassKilograms = 18000.0 * sizeScale;
            specification.flight.mainThrustNewtons = 3.4e6 * sizeScale;
            specification.flight.angularThrustNewtonMetres = 1.6e6 * sizeScale;
            specification.hyperdrive = HyperdriveClass::MarkOne;
            specification.walkableInterior = size != ShipSize::Small;
            break;
        case ShipClassId::Hauler:
            specification.name = "HAULER";
            specification.crewMinimum = 1;
            specification.crewMaximum = 6;
            specification.cargoCapacityTonnes = 420.0 * sizeScale;
            specification.flight.dryMassKilograms = 165000.0 * sizeScale;
            specification.flight.mainThrustNewtons = 4.2e6 * sizeScale;
            specification.flight.angularThrustNewtonMetres = 5.0e5 * sizeScale;
            specification.hyperdrive = HyperdriveClass::MarkTwo;
            specification.deckCount = 2;
            break;
        case ShipClassId::ScienceVessel:
            specification.name = "SCIENCE VESSEL";
            specification.crewMinimum = 2;
            specification.crewMaximum = 8;
            specification.cargoCapacityTonnes = 140.0 * sizeScale;
            specification.flight.dryMassKilograms = 96000.0 * sizeScale;
            specification.flight.mainThrustNewtons = 2.9e6 * sizeScale;
            specification.hyperdrive = HyperdriveClass::MarkThree;
            specification.deckCount = 2;
            break;
        case ShipClassId::ColonyShip:
            specification.name = "COLONY SHIP";
            specification.crewMinimum = 4;
            specification.crewMaximum = 16;
            specification.cargoCapacityTonnes = 1800.0;
            specification.flight.dryMassKilograms = 940000.0;
            specification.flight.mainThrustNewtons = 9.4e6;
            specification.flight.angularThrustNewtonMetres = 2.4e6;
            specification.hyperdrive = HyperdriveClass::MarkThree;
            specification.deckCount = 4;
            break;
        case ShipClassId::CapitalShip:
            specification.name = "CAPITAL SHIP";
            specification.crewMinimum = 4;
            specification.crewMaximum = 32;
            specification.cargoCapacityTonnes = 6400.0;
            specification.flight.dryMassKilograms = 4.6e6;
            specification.flight.mainThrustNewtons = 3.8e7;
            specification.flight.angularThrustNewtonMetres = 1.4e7;
            specification.flight.momentOfInertia = 8.4e8;
            specification.hyperdrive = HyperdriveClass::MarkFour;
            specification.deckCount = 7;
            break;
        default:
            break;
    }

    specification.flight.momentOfInertia = maxValue(specification.flight.momentOfInertia,
                                                    specification.flight.dryMassKilograms * 120.0);
    specification.fuelCapacity = 2400.0 + specification.cargoCapacityTonnes * 6.0;
    return specification;
}

void Ship::normalizePowerAllocation() {
    f64 total = 0.0;
    for (f64 value : power.allocation) total += value;
    if (total <= 0.0) {
        for (f64& value : power.allocation) value = 1.0 / static_cast<f64>(PowerConsumer::Count);
        return;
    }
    for (f64& value : power.allocation) value /= total;
}

void Ship::setPowerAllocation(PowerConsumer consumer, f64 fraction) {
    power.allocation[static_cast<usize>(consumer)] = clampValue(fraction, 0.0, 1.0);
    normalizePowerAllocation();
}

f64 Ship::totalShieldCharge() const {
    f64 total = 0.0;
    for (f64 value : shield.charge) total += value;
    return total / static_cast<f64>(ShieldSector::Count);
}

f64 Ship::driveIntegrity() const {
    return moduleState(ModuleSlot::Hyperdrive).integrity;
}

f64 Ship::massTonnes() const {
    return spec.flight.dryMassKilograms / 1000.0 + cargoTonnes;
}

void Ship::step(f64 stepSeconds, f64 externalShieldDrainPerSecond, f64 externalHullStressPerSecond) {
    if (stepSeconds <= 0.0) return;

    const f64 reactorHealth = moduleState(ModuleSlot::Reactor).integrity;
    power.reactorOutput = clampValue(reactorHealth * (1.0 + static_cast<f64>(upgrades[static_cast<usize>(UpgradeBranch::Logistics)]) * 0.12),
                                     0.0, 2.0);

    f64 demand = 0.0;
    for (f64 value : power.allocation) demand += value;
    power.overloaded = demand > power.reactorOutput + 1.0e-6;

    const f64 radiatorHealth = moduleState(ModuleSlot::Radiator).integrity;
    power.radiatorCapacity = clampValue(radiatorHealth, 0.0, 1.0);
    const f64 heatGeneration = maxValue(demand - power.reactorOutput, 0.0) * 0.9 + demand * 0.05;
    const f64 heatDissipation = 0.35 * power.radiatorCapacity;
    power.heat = clampValue(power.heat + (heatGeneration - heatDissipation * power.heat) * stepSeconds, 0.0, 1.8);

    if (power.heat > 1.2) {
        const f64 overheatDamage = (power.heat - 1.2) * 0.12 * stepSeconds;
        moduleState(ModuleSlot::Reactor).integrity = maxValue(reactorHealth - overheatDamage, 0.0);
    }

    shield.timeSinceHit += stepSeconds;
    const f64 shieldPower = power.allocation[static_cast<usize>(PowerConsumer::Shields)] *
                            clampValue(power.reactorOutput, 0.0, 2.0);
    shield.capacity = clampValue(moduleState(ModuleSlot::ShieldGenerator).integrity *
                                     (1.0 + static_cast<f64>(upgrades[static_cast<usize>(UpgradeBranch::Defence)]) * 0.18),
                                 0.0, 2.4);
    shield.regenerationPerSecond = 0.05 + shieldPower * 0.28;

    for (usize sector = 0; sector < static_cast<usize>(ShieldSector::Count); ++sector) {
        f64& charge = shield.charge[sector];
        charge = maxValue(charge - externalShieldDrainPerSecond * 0.01 * stepSeconds, 0.0);
        if (shield.timeSinceHit > shield.regenerationDelaySeconds && charge < shield.capacity) {
            charge = minValue(charge + shield.regenerationPerSecond * stepSeconds, shield.capacity);
        }
    }

    if (externalHullStressPerSecond > 0.0) {
        hull = maxValue(hull - externalHullStressPerSecond * stepSeconds, 0.0);
    }

    for (ShipModuleState& module : moduleStates) {
        if (module.onFire) {
            module.integrity = maxValue(module.integrity - 0.035 * stepSeconds, 0.0);
            hull = maxValue(hull - 0.004 * stepSeconds, 0.0);
        }
        module.online = module.integrity > 0.12;
    }

    for (WeaponGroupState& group : weapons) {
        group.cooldownSeconds = maxValue(group.cooldownSeconds - stepSeconds, 0.0);
        group.heat = maxValue(group.heat - 0.32 * stepSeconds, 0.0);
    }

    if (scanner.scanning) {
        const f64 tuningError = std::fabs(scanner.tunedFrequency - scanner.targetFrequency);
        scanner.lockQuality = clampValue(1.0 - tuningError * 6.0, 0.0, 1.0);
        const f64 sensorPower = power.allocation[static_cast<usize>(PowerConsumer::Sensors)] * 2.4;
        const f64 sensorHealth = moduleState(ModuleSlot::Scanner).integrity;
        scanner.scanProgress = clampValue(scanner.scanProgress +
                                              scanner.lockQuality * sensorPower * sensorHealth * 0.42 * stepSeconds,
                                          0.0, 1.0);
        if (scanner.scanProgress >= 1.0) scanner.scanning = false;
    }
}

void Ship::applyDamage(f64 amount, const DVec3& impactDirectionWorld, const Quat& shipOrientation) {
    if (amount <= 0.0) return;
    const Vec3 localDirection = shipOrientation.conjugate() * impactDirectionWorld.toFloat();
    ShieldSector sector = ShieldSector::Front;
    const f32 absoluteX = std::fabs(localDirection.x);
    const f32 absoluteZ = std::fabs(localDirection.z);
    if (absoluteZ >= absoluteX) {
        sector = localDirection.z < 0.0f ? ShieldSector::Front : ShieldSector::Rear;
    } else {
        sector = localDirection.x > 0.0f ? ShieldSector::Right : ShieldSector::Left;
    }

    shield.timeSinceHit = 0.0;
    shield.lastImpactSector = sector;
    shield.lastImpactMagnitude = amount;

    f64& charge = shield.charge[static_cast<usize>(sector)];
    const f64 absorbed = minValue(charge, amount);
    charge -= absorbed;
    const f64 leftover = amount - absorbed;
    if (leftover <= 0.0) return;

    hull = maxValue(hull - leftover * 0.55, 0.0);

    const usize moduleIndex = static_cast<usize>(std::fabs(localDirection.x * 7.0f + localDirection.z * 3.0f)) %
                              moduleStates.size();
    ShipModuleState& hitModule = moduleStates[moduleIndex];
    hitModule.integrity = maxValue(hitModule.integrity - leftover * 0.9, 0.0);
    if (leftover > 0.25 && hitModule.integrity < 0.5) hitModule.onFire = true;
}

bool Ship::repairModule(ModuleSlot slot, f64 progressAmount) {
    ShipModuleState& module = moduleState(slot);
    if (module.integrity >= 1.0) return false;
    module.repairProgress += progressAmount;
    module.onFire = false;
    if (module.repairProgress >= 1.0) {
        module.repairProgress = 0.0;
        module.integrity = minValue(module.integrity + 0.34, 1.0);
    }
    return true;
}

void Ship::beginScan(f64 targetFrequency) {
    scanner.scanning = true;
    scanner.scanProgress = 0.0;
    scanner.targetFrequency = clampValue(targetFrequency, 0.0, 1.0);
}

void Ship::tuneScanner(f64 delta) {
    scanner.tunedFrequency = clampValue(scanner.tunedFrequency + delta, 0.0, 1.0);
}

bool Ship::fireGroup(u32 groupIndex) {
    if (groupIndex >= weapons.size()) return false;
    WeaponGroupState& group = weapons[groupIndex];
    if (!group.active || group.cooldownSeconds > 0.0) return false;
    if (!moduleState(ModuleSlot::WeaponBank).online) return false;

    if (group.energyBased) {
        const f64 weaponPower = power.allocation[static_cast<usize>(PowerConsumer::Weapons)];
        if (weaponPower < 0.04 || group.heat > 1.0) return false;
        group.heat += 0.22;
        group.cooldownSeconds = 0.18 / maxValue(weaponPower * 2.4, 0.2);
    } else {
        if (group.ammunition == 0) return false;
        --group.ammunition;
        group.cooldownSeconds = 0.32;
        group.heat += 0.08;
    }
    return true;
}

void Ship::setWeaponGroupActive(u32 groupIndex, bool active) {
    if (groupIndex >= weapons.size()) return;
    weapons[groupIndex].active = active;
}

bool Ship::applyUpgrade(UpgradeBranch branch) {
    u32& level = upgrades[static_cast<usize>(branch)];
    if (level >= 5) return false;
    ++level;
    if (branch == UpgradeBranch::Propulsion) {
        spec.flight.mainThrustNewtons *= 1.14;
        spec.flight.angularThrustNewtonMetres *= 1.10;
    } else if (branch == UpgradeBranch::Logistics) {
        spec.cargoCapacityTonnes *= 1.16;
        spec.fuelCapacity *= 1.12;
    }
    return true;
}

const char* Ship::classIdName(ShipClassId value) {
    switch (value) {
        case ShipClassId::Explorer: return "EXPLORER";
        case ShipClassId::Fighter: return "FIGHTER";
        case ShipClassId::Hauler: return "HAULER";
        case ShipClassId::ScienceVessel: return "SCIENCE VESSEL";
        case ShipClassId::ColonyShip: return "COLONY SHIP";
        case ShipClassId::CapitalShip: return "CAPITAL SHIP";
        default: return "UNBEKANNT";
    }
}

const char* Ship::sectorName(ShieldSector value) {
    switch (value) {
        case ShieldSector::Front: return "VORNE";
        case ShieldSector::Rear: return "HINTEN";
        case ShieldSector::Left: return "LINKS";
        case ShieldSector::Right: return "RECHTS";
        default: return "";
    }
}

const char* Ship::consumerName(PowerConsumer value) {
    switch (value) {
        case PowerConsumer::Engines: return "ANTRIEB";
        case PowerConsumer::Shields: return "SCHILDE";
        case PowerConsumer::Weapons: return "WAFFEN";
        case PowerConsumer::Sensors: return "SENSOREN";
        case PowerConsumer::LifeSupport: return "LEBENSERHALT";
        case PowerConsumer::Auxiliary: return "HILFSSYSTEME";
        default: return "";
    }
}

const char* Ship::moduleName(ModuleSlot value) {
    switch (value) {
        case ModuleSlot::Reactor: return "REAKTOR";
        case ModuleSlot::Engine: return "TRIEBWERK";
        case ModuleSlot::ShieldGenerator: return "SCHILDGENERATOR";
        case ModuleSlot::WeaponBank: return "WAFFENBANK";
        case ModuleSlot::Scanner: return "SCANNER";
        case ModuleSlot::Radiator: return "RADIATOR";
        case ModuleSlot::Hyperdrive: return "HYPERANTRIEB";
        case ModuleSlot::CargoHold: return "FRACHTRAUM";
        default: return "";
    }
}

const char* Ship::branchName(UpgradeBranch value) {
    switch (value) {
        case UpgradeBranch::Propulsion: return "ANTRIEB";
        case UpgradeBranch::Defence: return "VERTEIDIGUNG";
        case UpgradeBranch::Armament: return "BEWAFFNUNG";
        case UpgradeBranch::Sensors: return "SENSORIK";
        case UpgradeBranch::Logistics: return "LOGISTIK";
        case UpgradeBranch::VoidTechnology: return "VOID-TECHNOLOGIE";
        default: return "";
    }
}

}
