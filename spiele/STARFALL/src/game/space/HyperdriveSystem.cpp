#include "HyperdriveSystem.hpp"

#include "../../engine/math/Random.hpp"
#include "../../engine/math/Scalar.hpp"

#include <algorithm>
#include <queue>

namespace sf {

HyperdriveSpecification HyperdriveSystem::specificationFor(HyperdriveClass driveClass) {
    HyperdriveSpecification specification;
    specification.driveClass = driveClass;
    switch (driveClass) {
        case HyperdriveClass::MarkOne:
            specification.rangeLightYears = 8.0;
            specification.baseChargeSeconds = 6.0;
            specification.baseFuelCost = 1.0;
            specification.fuel = FuelType::Deuterium;
            break;
        case HyperdriveClass::MarkTwo:
            specification.rangeLightYears = 25.0;
            specification.baseChargeSeconds = 9.0;
            specification.baseFuelCost = 1.6;
            specification.fuel = FuelType::Deuterium;
            break;
        case HyperdriveClass::MarkThree:
            specification.rangeLightYears = 75.0;
            specification.baseChargeSeconds = 13.0;
            specification.baseFuelCost = 2.4;
            specification.fuel = FuelType::Tritium;
            break;
        case HyperdriveClass::MarkFour:
            specification.rangeLightYears = 200.0;
            specification.baseChargeSeconds = 17.0;
            specification.baseFuelCost = 3.6;
            specification.fuel = FuelType::Tritium;
            break;
        case HyperdriveClass::VoidDrive:
            specification.rangeLightYears = 600.0;
            specification.baseChargeSeconds = 20.0;
            specification.baseFuelCost = 6.2;
            specification.fuel = FuelType::VoidMatter;
            specification.worksInVoidZone = true;
            break;
        default:
            break;
    }
    return specification;
}

f64 HyperdriveSystem::distanceLightYears(const SystemCoord& from, const SystemCoord& to) {
    const f64 deltaX = static_cast<f64>(to.x - from.x);
    const f64 deltaY = static_cast<f64>(to.y - from.y);
    const f64 deltaZ = static_cast<f64>(to.z - from.z);
    return std::sqrt(deltaX * deltaX + deltaY * deltaY + deltaZ * deltaZ);
}

f64 HyperdriveSystem::energyCost(f64 distance, f64 shipMassTonnes, f64 cargoFraction, f64 driveIntegrity) const {
    const f64 massFactor = clampValue(shipMassTonnes / 42.0, 0.4, 6.0);
    const f64 cargoFactor = 1.0 + clampValue(cargoFraction, 0.0, 1.0) * 0.65;
    const f64 conditionFactor = 1.0 + (1.0 - clampValue(driveIntegrity, 0.05, 1.0)) * 1.8;
    return specification.baseFuelCost * std::pow(maxValue(distance, 0.001), 1.15) * massFactor * cargoFactor *
           conditionFactor;
}

f64 HyperdriveSystem::chargeSecondsFor(f64 distance, f64 zoneMultiplier) const {
    const f64 rangeFraction = clampValue(distance / maxValue(specification.rangeLightYears, 0.001), 0.0, 1.0);
    const f64 base = specification.baseChargeSeconds * (0.62 + rangeFraction * 0.9);
    return clampValue(base * maxValue(zoneMultiplier, 0.05), 4.0, 240.0);
}

JumpDenialReason HyperdriveSystem::evaluateJump(const SystemCoord& from, const SystemCoord& to, f64 availableFuel,
                                                f64 shipMassTonnes, f64 massLockStrength, f64 driveIntegrity,
                                                bool insideVoidZone) const {
    if (insideVoidZone && !specification.worksInVoidZone) return JumpDenialReason::VoidDriveRequired;
    if (driveIntegrity < 0.15) return JumpDenialReason::DriveDamaged;

    const f64 distance = distanceLightYears(from, to);
    if (distance > specification.rangeLightYears + 1.0e-6) return JumpDenialReason::OutOfRange;
    if (massLockStrength > 0.6) return JumpDenialReason::MassLock;

    const f64 required = energyCost(distance, shipMassTonnes, 0.0, driveIntegrity);
    if (availableFuel < required) return JumpDenialReason::InsufficientFuel;
    return JumpDenialReason::None;
}

bool HyperdriveSystem::beginJump(HyperdriveState& state, const SystemCoord& destination, f64 distance,
                                 f64 zoneMultiplier) {
    if (state.phase != HyperdrivePhase::Idle) return false;
    state.destination = destination;
    state.phase = HyperdrivePhase::Charging;
    state.chargeSeconds = 0.0;
    state.requiredChargeSeconds = chargeSecondsFor(distance, zoneMultiplier);
    state.requiredTransitSeconds = clampValue(4.0 + distance * 0.055, 4.0, 15.0);
    state.transitSeconds = 0.0;
    state.activeHazard = TransitHazard::None;
    state.warpFactor = 0.0;
    return true;
}

void HyperdriveSystem::abortJump(HyperdriveState& state) const {
    state.phase = HyperdrivePhase::Idle;
    state.chargeSeconds = 0.0;
    state.transitSeconds = 0.0;
    state.warpFactor = 0.0;
    state.activeHazard = TransitHazard::None;
}

void HyperdriveSystem::update(HyperdriveState& state, f64 stepSeconds, f64 alignmentDegrees, u64 randomSeed) const {
    state.alignmentDegrees = alignmentDegrees;
    state.shieldOfflineSeconds = maxValue(state.shieldOfflineSeconds - stepSeconds, 0.0);
    state.weaponsOfflineSeconds = maxValue(state.weaponsOfflineSeconds - stepSeconds, 0.0);

    switch (state.phase) {
        case HyperdrivePhase::Idle:
            state.warpFactor = maxValue(state.warpFactor - stepSeconds * 1.4, 0.0);
            break;
        case HyperdrivePhase::Charging:
            state.chargeSeconds += stepSeconds;
            if (state.chargeSeconds >= state.requiredChargeSeconds) {
                state.phase = HyperdrivePhase::Aligning;
            }
            break;
        case HyperdrivePhase::Aligning:
            if (alignmentDegrees < 4.0) {
                state.phase = HyperdrivePhase::Tunnelling;
                state.transitSeconds = 0.0;
                Random random(hashCombine(randomSeed, static_cast<u64>(state.destination.key())));
                const f64 hazardRoll = random.nextDouble();
                if (hazardRoll < 0.04) state.activeHazard = TransitHazard::MassEjection;
                else if (hazardRoll < 0.08) state.activeHazard = TransitHazard::Anomaly;
                else if (hazardRoll < 0.13) state.activeHazard = TransitHazard::Interdiction;
                else if (hazardRoll < 0.18) state.activeHazard = TransitHazard::NebulaInterference;
                else if (hazardRoll < 0.20) state.activeHazard = TransitHazard::VoidEcho;
                else if (hazardRoll < 0.24) state.activeHazard = TransitHazard::RadiationBurst;
                else state.activeHazard = TransitHazard::None;
            }
            break;
        case HyperdrivePhase::Tunnelling: {
            state.transitSeconds += stepSeconds;
            const f64 fraction = clampValue(state.transitSeconds / maxValue(state.requiredTransitSeconds, 0.01), 0.0, 1.0);
            state.warpFactor = std::sin(fraction * kPiDouble) * 0.985;
            f64 effectiveDuration = state.requiredTransitSeconds;
            if (state.activeHazard == TransitHazard::NebulaInterference) effectiveDuration *= 1.8;
            if (state.transitSeconds >= effectiveDuration) {
                state.phase = HyperdrivePhase::Exiting;
                state.shieldOfflineSeconds = 3.0;
                state.weaponsOfflineSeconds = 2.0;
            }
            break;
        }
        case HyperdrivePhase::Exiting:
            state.warpFactor = maxValue(state.warpFactor - stepSeconds * 2.6, 0.0);
            if (state.warpFactor <= 0.0) {
                state.phase = HyperdrivePhase::Cooldown;
                state.cooldownSeconds = 5.0;
            }
            break;
        case HyperdrivePhase::Cooldown:
            state.cooldownSeconds -= stepSeconds;
            if (state.cooldownSeconds <= 0.0) {
                state.phase = HyperdrivePhase::Idle;
                state.chargeSeconds = 0.0;
                state.transitSeconds = 0.0;
            }
            break;
    }
}

const char* HyperdriveSystem::driveClassName(HyperdriveClass value) {
    switch (value) {
        case HyperdriveClass::MarkOne: return "MK1";
        case HyperdriveClass::MarkTwo: return "MK2";
        case HyperdriveClass::MarkThree: return "MK3";
        case HyperdriveClass::MarkFour: return "MK4";
        case HyperdriveClass::VoidDrive: return "VOID DRIVE";
        default: return "UNBEKANNT";
    }
}

const char* HyperdriveSystem::hazardName(TransitHazard value) {
    switch (value) {
        case TransitHazard::None: return "KEINE";
        case TransitHazard::MassEjection: return "MASSENAUSWURF";
        case TransitHazard::Anomaly: return "HYPERRAUM-ANOMALIE";
        case TransitHazard::Interdiction: return "INTERDIKTION";
        case TransitHazard::NebulaInterference: return "NEBELINTERFERENZ";
        case TransitHazard::VoidEcho: return "VOID-ECHO";
        case TransitHazard::RadiationBurst: return "STRAHLUNGSAUSBRUCH";
        default: return "UNBEKANNT";
    }
}

const char* HyperdriveSystem::hazardResolution(TransitHazard value) {
    switch (value) {
        case TransitHazard::MassEjection:
            return "Erzwungener Austritt in ein unbekanntes System. Position neu bestimmen und Route neu planen.";
        case TransitHazard::Anomaly:
            return "Antriebsschaden. Feldspulen im Maschinenraum neu ausrichten, dann erneut laden.";
        case TransitHazard::Interdiction:
            return "Aus dem Transit gerissen. Kampf oder Flucht mit vollem Schub, Schilde brauchen drei Sekunden.";
        case TransitHazard::NebulaInterference:
            return "Transit verlaengert sich, Sensoren fallen aus. Auf Traegheitsnavigation umschalten.";
        case TransitHazard::VoidEcho:
            return "Austritt in eine Zone veraenderter Zeitrate. Bordzeit gegen Weltzeit abgleichen.";
        case TransitHazard::RadiationBurst:
            return "Besatzungsschaden. Abschirmung hochfahren und Medizinstation aufsuchen.";
        default:
            return "";
    }
}

const char* HyperdriveSystem::fuelName(FuelType value) {
    switch (value) {
        case FuelType::Deuterium: return "Deuterium";
        case FuelType::Tritium: return "Tritium";
        case FuelType::VoidMatter: return "Void Matter";
        default: return "Unbekannt";
    }
}

const char* HyperdriveSystem::denialReasonText(JumpDenialReason value) {
    switch (value) {
        case JumpDenialReason::None: return "";
        case JumpDenialReason::OutOfRange: return "Ziel ausserhalb der Reichweite des Antriebs.";
        case JumpDenialReason::InsufficientFuel: return "Nicht genug Treibstoff fuer diesen Sprung.";
        case JumpDenialReason::MassLock: return "Massenverriegelung: zu nah an einem Gravitationsbrunnen.";
        case JumpDenialReason::RestrictedSpace: return "Sperrgebiet, Sprung wird verweigert.";
        case JumpDenialReason::DriveDamaged: return "Hyperantrieb beschaedigt, Reparatur noetig.";
        case JumpDenialReason::VoidDriveRequired: return "In dieser Zone funktioniert nur der Void-Antrieb.";
        default: return "";
    }
}

f64 HyperRouteSolver::edgeWeight(const StarNode& from, const StarNode& to, f64 distance,
                                 RoutePreference preference) const {
    const f64 unknownPenalty = to.surveyed ? 1.0 : 1.35;
    const f64 restrictedPenalty = to.restricted ? 6.0 : 1.0;
    switch (preference) {
        case RoutePreference::Economical:
            return std::pow(maxValue(distance, 0.001), 1.15) * unknownPenalty * restrictedPenalty;
        case RoutePreference::Safest:
            return distance * (1.0 + (from.hazardRating + to.hazardRating) * 3.4) * unknownPenalty *
                   restrictedPenalty;
        default:
            return distance * unknownPenalty * restrictedPenalty;
    }
}

HyperRoute HyperRouteSolver::solve(const SystemCoord& from, const SystemCoord& to, f64 jumpRangeLightYears,
                                   f64 fuelBudget, RoutePreference preference) const {
    HyperRoute route;
    if (nodes.empty()) return route;

    usize startIndex = kInvalidIndex64;
    usize goalIndex = kInvalidIndex64;
    for (usize index = 0; index < nodes.size(); ++index) {
        if (nodes[index].coordinate == from) startIndex = index;
        if (nodes[index].coordinate == to) goalIndex = index;
    }
    if (startIndex == kInvalidIndex64 || goalIndex == kInvalidIndex64) return route;

    std::vector<f64> costSoFar(nodes.size(), 1.0e300);
    std::vector<usize> cameFrom(nodes.size(), kInvalidIndex64);
    std::vector<bool> visited(nodes.size(), false);

    using Entry = std::pair<f64, usize>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> frontier;
    costSoFar[startIndex] = 0.0;
    frontier.push({0.0, startIndex});

    while (!frontier.empty()) {
        const usize current = frontier.top().second;
        frontier.pop();
        if (visited[current]) continue;
        visited[current] = true;
        if (current == goalIndex) break;

        for (usize candidate = 0; candidate < nodes.size(); ++candidate) {
            if (candidate == current || visited[candidate]) continue;
            const f64 distance = HyperdriveSystem::distanceLightYears(nodes[current].coordinate,
                                                                     nodes[candidate].coordinate);
            if (distance > jumpRangeLightYears) continue;
            const f64 stepCost = edgeWeight(nodes[current], nodes[candidate], distance, preference);
            const f64 total = costSoFar[current] + stepCost;
            if (total >= costSoFar[candidate]) continue;
            costSoFar[candidate] = total;
            cameFrom[candidate] = current;
            const f64 heuristic = HyperdriveSystem::distanceLightYears(nodes[candidate].coordinate,
                                                                      nodes[goalIndex].coordinate);
            frontier.push({total + heuristic, candidate});
        }
    }

    if (cameFrom[goalIndex] == kInvalidIndex64 && startIndex != goalIndex) return route;

    std::vector<usize> reversed;
    usize cursor = goalIndex;
    while (cursor != kInvalidIndex64) {
        reversed.push_back(cursor);
        if (cursor == startIndex) break;
        cursor = cameFrom[cursor];
    }
    std::reverse(reversed.begin(), reversed.end());

    f64 remainingFuel = fuelBudget;
    f64 hazardSum = 0.0;
    for (usize index = 1; index < reversed.size(); ++index) {
        const StarNode& previous = nodes[reversed[index - 1]];
        const StarNode& node = nodes[reversed[index]];
        RouteLeg leg;
        leg.target = node.coordinate;
        leg.distanceLightYears = HyperdriveSystem::distanceLightYears(previous.coordinate, node.coordinate);
        leg.fuelCost = std::pow(maxValue(leg.distanceLightYears, 0.001), 1.15);
        leg.hazardRating = node.hazardRating;
        remainingFuel -= leg.fuelCost;
        if (remainingFuel < 0.0 && node.hasRefuel) {
            leg.refuelStop = true;
            remainingFuel = fuelBudget;
        }
        hazardSum += leg.hazardRating;
        route.totalDistanceLightYears += leg.distanceLightYears;
        route.totalFuelCost += leg.fuelCost;
        route.legs.push_back(leg);
    }

    route.estimatedSeconds = static_cast<f64>(route.legs.size()) * 24.0 + route.totalDistanceLightYears * 0.06;
    route.averageHazard = route.legs.empty() ? 0.0 : hazardSum / static_cast<f64>(route.legs.size());
    route.reachable = !route.legs.empty() || startIndex == goalIndex;
    return route;
}

}
