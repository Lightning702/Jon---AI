#include "BaseGrid.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {
namespace {

BuildPartDefinition make(BuildPartId id, const char* name, BuildCategory category,
                         std::vector<RecipeIngredient> cost, f32 footprint, f32 height, f64 production, f64 draw,
                         f64 storage, f64 support, f64 load, u32 tier, const Vec3& tint) {
    BuildPartDefinition definition;
    definition.id = id;
    definition.name = name;
    definition.category = category;
    definition.cost = std::move(cost);
    definition.footprintMeters = footprint;
    definition.heightMeters = height;
    definition.powerProduction = production;
    definition.powerDraw = draw;
    definition.storageCapacity = storage;
    definition.structuralSupport = support;
    definition.structuralLoad = load;
    definition.requiredResearchTier = tier;
    definition.tint = tint;
    return definition;
}

}

BuildPartCatalog::BuildPartCatalog() {
    entries.resize(static_cast<usize>(BuildPartId::Count));

    entries[static_cast<usize>(BuildPartId::Foundation)] =
        make(BuildPartId::Foundation, "Fundament", BuildCategory::Habitation, {{ItemId::StructurePanel, 1}}, 4.0f,
             0.4f, 0.0, 0.0, 0.0, 6.0, 0.2, 1, Vec3(0.58f, 0.60f, 0.64f));
    entries[static_cast<usize>(BuildPartId::Wall)] =
        make(BuildPartId::Wall, "Wand", BuildCategory::Habitation, {{ItemId::StructurePanel, 1}}, 4.0f, 3.0f, 0.0,
             0.0, 0.0, 1.6, 0.6, 1, Vec3(0.60f, 0.62f, 0.66f));
    entries[static_cast<usize>(BuildPartId::Doorway)] =
        make(BuildPartId::Doorway, "Durchgang", BuildCategory::Habitation, {{ItemId::StructurePanel, 1}}, 4.0f, 3.0f,
             0.0, 0.05, 0.0, 1.2, 0.6, 1, Vec3(0.56f, 0.62f, 0.70f));
    entries[static_cast<usize>(BuildPartId::Roof)] =
        make(BuildPartId::Roof, "Dach", BuildCategory::Habitation, {{ItemId::StructurePanel, 1}}, 4.0f, 0.4f, 0.0,
             0.0, 0.0, 0.4, 1.4, 1, Vec3(0.54f, 0.56f, 0.60f));
    entries[static_cast<usize>(BuildPartId::Ramp)] =
        make(BuildPartId::Ramp, "Rampe", BuildCategory::Habitation, {{ItemId::StructurePanel, 1}}, 4.0f, 3.0f, 0.0,
             0.0, 0.0, 1.0, 0.8, 1, Vec3(0.58f, 0.58f, 0.60f));
    entries[static_cast<usize>(BuildPartId::HabitatDome)] =
        make(BuildPartId::HabitatDome, "Habitatkuppel", BuildCategory::Habitation,
             {{ItemId::StructurePanel, 4}, {ItemId::MetalPlate, 2}}, 7.0f, 5.0f, 0.0, 0.6, 0.0, 4.0, 2.4, 1,
             Vec3(0.66f, 0.70f, 0.76f));
    entries[static_cast<usize>(BuildPartId::Airlock)] =
        make(BuildPartId::Airlock, "Druckschleuse", BuildCategory::Habitation,
             {{ItemId::MetalPlate, 2}, {ItemId::ChemicalCell, 1}}, 4.0f, 3.0f, 0.0, 0.4, 0.0, 1.6, 0.9, 1,
             Vec3(0.48f, 0.62f, 0.72f));
    entries[static_cast<usize>(BuildPartId::Greenhouse)] =
        make(BuildPartId::Greenhouse, "Gewaechshaus", BuildCategory::Habitation,
             {{ItemId::StructurePanel, 3}, {ItemId::Silicate, 80}}, 6.0f, 4.0f, 0.0, 0.9, 0.0, 2.4, 1.8, 2,
             Vec3(0.52f, 0.78f, 0.58f));

    entries[static_cast<usize>(BuildPartId::ResearchTerminal)] =
        make(BuildPartId::ResearchTerminal, "Forschungsterminal", BuildCategory::Laboratory,
             {{ItemId::MetalPlate, 1}, {ItemId::Chromatic, 20}}, 2.0f, 2.0f, 0.0, 1.4, 0.0, 0.4, 0.6, 2,
             Vec3(0.40f, 0.72f, 0.86f));
    entries[static_cast<usize>(BuildPartId::Refiner)] =
        make(BuildPartId::Refiner, "Raffinerie", BuildCategory::Factory,
             {{ItemId::MetalPlate, 1}, {ItemId::PureFerrite, 30}}, 2.4f, 2.2f, 0.0, 1.8, 0.0, 0.4, 0.8, 1,
             Vec3(0.72f, 0.56f, 0.32f));
    entries[static_cast<usize>(BuildPartId::Smelter)] =
        make(BuildPartId::Smelter, "Schmelze", BuildCategory::Factory,
             {{ItemId::MetalPlate, 2}, {ItemId::ThermalCell, 1}}, 3.2f, 3.0f, 0.0, 3.2, 0.0, 0.6, 1.2, 2,
             Vec3(0.86f, 0.44f, 0.22f));
    entries[static_cast<usize>(BuildPartId::AssemblyLine)] =
        make(BuildPartId::AssemblyLine, "Fertigungsstrasse", BuildCategory::Factory,
             {{ItemId::MetalPlate, 3}, {ItemId::PowerCoupling, 2}}, 8.0f, 3.0f, 0.0, 5.4, 0.0, 0.8, 2.2, 3,
             Vec3(0.62f, 0.62f, 0.68f));
    entries[static_cast<usize>(BuildPartId::CropBed)] =
        make(BuildPartId::CropBed, "Feldkultur", BuildCategory::Farm, {{ItemId::StructurePanel, 1}}, 3.0f, 0.6f, 0.0,
             0.2, 0.0, 0.3, 0.4, 1, Vec3(0.44f, 0.62f, 0.30f));
    entries[static_cast<usize>(BuildPartId::Hydroponics)] =
        make(BuildPartId::Hydroponics, "Hydroponik", BuildCategory::Farm,
             {{ItemId::StructurePanel, 2}, {ItemId::ChemicalCell, 1}}, 4.0f, 2.2f, 0.0, 1.6, 0.0, 0.5, 1.0, 2,
             Vec3(0.36f, 0.76f, 0.66f));
    entries[static_cast<usize>(BuildPartId::LandingPad)] =
        make(BuildPartId::LandingPad, "Landeplattform", BuildCategory::Hangar,
             {{ItemId::MetalPlate, 4}, {ItemId::StructurePanel, 4}}, 14.0f, 0.8f, 0.0, 1.2, 0.0, 4.0, 3.0, 2,
             Vec3(0.50f, 0.54f, 0.58f));
    entries[static_cast<usize>(BuildPartId::RepairDock)] =
        make(BuildPartId::RepairDock, "Reparaturdock", BuildCategory::Hangar,
             {{ItemId::MetalPlate, 3}, {ItemId::PowerCoupling, 1}}, 8.0f, 5.0f, 0.0, 4.0, 0.0, 1.6, 2.4, 3,
             Vec3(0.56f, 0.58f, 0.66f));

    entries[static_cast<usize>(BuildPartId::SolarPanel)] =
        make(BuildPartId::SolarPanel, "Solarpaneel", BuildCategory::PowerPlant,
             {{ItemId::Silicate, 60}, {ItemId::Chromatic, 10}}, 2.6f, 2.0f, 2.4, 0.0, 0.0, 0.3, 0.4, 1,
             Vec3(0.30f, 0.42f, 0.72f));
    entries[static_cast<usize>(BuildPartId::WindTurbine)] =
        make(BuildPartId::WindTurbine, "Windturbine", BuildCategory::PowerPlant,
             {{ItemId::MetalPlate, 1}, {ItemId::CarbonNanotube, 1}}, 3.0f, 8.0f, 3.6, 0.0, 0.0, 0.4, 0.8, 1,
             Vec3(0.74f, 0.76f, 0.80f));
    entries[static_cast<usize>(BuildPartId::Geothermal)] =
        make(BuildPartId::Geothermal, "Geothermie", BuildCategory::PowerPlant,
             {{ItemId::MetalPlate, 2}, {ItemId::ThermalCell, 2}}, 4.0f, 3.0f, 9.0, 0.0, 0.0, 0.8, 1.4, 2,
             Vec3(0.84f, 0.38f, 0.24f));
    entries[static_cast<usize>(BuildPartId::FusionReactor)] =
        make(BuildPartId::FusionReactor, "Fusionsreaktor", BuildCategory::PowerPlant,
             {{ItemId::MetalPlate, 4}, {ItemId::PowerCoupling, 2}, {ItemId::Deuterium, 120}}, 6.0f, 5.0f, 34.0, 0.0,
             0.0, 1.2, 2.6, 3, Vec3(0.36f, 0.86f, 0.92f));
    entries[static_cast<usize>(BuildPartId::SingularityReactor)] =
        make(BuildPartId::SingularityReactor, "Singularitaetsreaktor", BuildCategory::PowerPlant,
             {{ItemId::SingularityCore, 1}, {ItemId::LensedAlloy, 4}}, 8.0f, 7.0f, 180.0, 0.0, 0.0, 1.6, 4.0, 5,
             Vec3(0.20f, 0.14f, 0.34f));

    entries[static_cast<usize>(BuildPartId::Turret)] =
        make(BuildPartId::Turret, "Geschuetzturm", BuildCategory::Defence,
             {{ItemId::MetalPlate, 2}, {ItemId::ChemicalCell, 2}}, 2.4f, 3.2f, 0.0, 2.2, 0.0, 0.4, 0.9, 2,
             Vec3(0.46f, 0.46f, 0.50f));
    entries[static_cast<usize>(BuildPartId::ShieldPylon)] =
        make(BuildPartId::ShieldPylon, "Schildgenerator", BuildCategory::Defence,
             {{ItemId::MetalPlate, 2}, {ItemId::PowerCoupling, 2}}, 2.4f, 4.0f, 0.0, 6.0, 0.0, 0.4, 1.0, 3,
             Vec3(0.32f, 0.68f, 0.92f));
    entries[static_cast<usize>(BuildPartId::SensorMast)] =
        make(BuildPartId::SensorMast, "Sensorturm", BuildCategory::Defence,
             {{ItemId::MetalPlate, 1}, {ItemId::Chromatic, 15}}, 1.8f, 6.0f, 0.0, 1.0, 0.0, 0.3, 0.7, 2,
             Vec3(0.40f, 0.60f, 0.70f));

    entries[static_cast<usize>(BuildPartId::StorageContainer)] =
        make(BuildPartId::StorageContainer, "Lagercontainer", BuildCategory::Logistics,
             {{ItemId::MetalPlate, 2}, {ItemId::StructurePanel, 2}}, 3.2f, 2.4f, 0.0, 0.2, 1000.0, 0.6, 1.2, 1,
             Vec3(0.68f, 0.60f, 0.34f));
    entries[static_cast<usize>(BuildPartId::Conveyor)] =
        make(BuildPartId::Conveyor, "Foerderband", BuildCategory::Logistics,
             {{ItemId::PureFerrite, 40}, {ItemId::CarbonNanotube, 1}}, 4.0f, 0.8f, 0.0, 0.4, 0.0, 0.2, 0.3, 2,
             Vec3(0.52f, 0.52f, 0.54f));
    entries[static_cast<usize>(BuildPartId::DronePort)] =
        make(BuildPartId::DronePort, "Drohnenhafen", BuildCategory::Logistics,
             {{ItemId::MetalPlate, 2}, {ItemId::PowerCoupling, 1}}, 4.0f, 2.0f, 0.0, 2.4, 0.0, 0.5, 1.0, 3,
             Vec3(0.44f, 0.66f, 0.74f));
    entries[static_cast<usize>(BuildPartId::Teleporter)] =
        make(BuildPartId::Teleporter, "Teleportgate", BuildCategory::Logistics,
             {{ItemId::LensedAlloy, 2}, {ItemId::PowerCoupling, 4}, {ItemId::Chromatic, 120}}, 5.0f, 5.0f, 0.0, 24.0,
             0.0, 0.8, 2.0, 5, Vec3(0.62f, 0.36f, 0.86f));
}

const BuildPartCatalog& BuildPartCatalog::instance() {
    static BuildPartCatalog catalog;
    return catalog;
}

std::vector<const BuildPartDefinition*> BuildPartCatalog::ofCategory(BuildCategory category) const {
    std::vector<const BuildPartDefinition*> result;
    for (const BuildPartDefinition& definition : entries) {
        if (definition.category == category) result.push_back(&definition);
    }
    return result;
}

const char* BuildPartCatalog::categoryName(BuildCategory category) {
    switch (category) {
        case BuildCategory::Habitation: return "WOHNEN";
        case BuildCategory::Laboratory: return "LABOR";
        case BuildCategory::Factory: return "FABRIK";
        case BuildCategory::Farm: return "FARM";
        case BuildCategory::Hangar: return "HANGAR";
        case BuildCategory::PowerPlant: return "KRAFTWERK";
        case BuildCategory::Defence: return "VERTEIDIGUNG";
        case BuildCategory::Logistics: return "LOGISTIK";
        default: return "";
    }
}

void BaseGrid::configure(const std::string& baseName, const DVec3& anchorLocalPosition) {
    displayName = baseName;
    anchorPosition = anchorLocalPosition;
    placedParts.clear();
    nextInstanceId = 1;
}

DVec3 BaseGrid::snapPosition(const PlanetBody& body, const DVec3& desiredLocalPosition, BuildPartId partId) const {
    const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(partId);
    const f64 grid = static_cast<f64>(definition.footprintMeters);

    DVec3 best = desiredLocalPosition;
    f64 bestDistance = grid * 1.35;
    for (const BasePart& part : placedParts) {
        const BuildPartDefinition& existing = BuildPartCatalog::instance().definition(part.partId);
        const DVec3 up = part.upDirection;
        const DVec3 reference = std::fabs(up.y) < 0.9 ? DVec3::unitY() : DVec3::unitX();
        const DVec3 east = normalize(cross(reference, up));
        const DVec3 north = cross(up, east);
        const f64 spacing = (existing.footprintMeters + definition.footprintMeters) * 0.5;

        const DVec3 candidates[4] = {part.localPosition + east * spacing, part.localPosition - east * spacing,
                                     part.localPosition + north * spacing, part.localPosition - north * spacing};
        for (const DVec3& candidate : candidates) {
            const f64 distance = length(candidate - desiredLocalPosition);
            if (distance >= bestDistance) continue;
            bestDistance = distance;
            best = candidate;
        }
    }

    const DVec3 up = body.upAt(best);
    return body.center() + up * (body.radiusAt(up) + static_cast<f64>(definition.heightMeters) * 0.02);
}

PlacementResult BaseGrid::evaluatePlacement(const PlanetBody& body, BuildPartId partId, const DVec3& localPosition,
                                            const Inventory& inventory, u32 researchTier) const {
    const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(partId);
    if (researchTier < definition.requiredResearchTier) return PlacementResult::ResearchMissing;

    for (const RecipeIngredient& ingredient : definition.cost) {
        if (!inventory.has(ingredient.id, ingredient.amount)) return PlacementResult::MissingMaterial;
    }

    if (!placedParts.empty() && length(localPosition - anchorPosition) > 320.0) return PlacementResult::OutOfRange;

    const DVec3 up = body.upAt(localPosition);
    const DVec3 surfaceNormal = body.surfaceNormal(up, 6.0);
    if (dot(surfaceNormal, up) < 0.82) return PlacementResult::TooSteep;

    const SurfaceSample sample = body.sampleSurface(up, 0.5);
    if (sample.underWater && definition.category != BuildCategory::Habitation) return PlacementResult::Unsupported;

    for (const BasePart& part : placedParts) {
        const BuildPartDefinition& existing = BuildPartCatalog::instance().definition(part.partId);
        const f64 minimumSpacing = (existing.footprintMeters + definition.footprintMeters) * 0.34;
        if (length(part.localPosition - localPosition) < minimumSpacing) return PlacementResult::Overlapping;
    }

    if (definition.structuralLoad > 1.0 && !placedParts.empty()) {
        f64 nearbySupport = 0.0;
        for (const BasePart& part : placedParts) {
            if (length(part.localPosition - localPosition) > static_cast<f64>(definition.footprintMeters) * 1.6) continue;
            nearbySupport += BuildPartCatalog::instance().definition(part.partId).structuralSupport;
        }
        if (nearbySupport < definition.structuralLoad) return PlacementResult::Unsupported;
    }
    return PlacementResult::Ok;
}

bool BaseGrid::place(const PlanetBody& body, BuildPartId partId, const DVec3& localPosition, f32 rotation,
                     Inventory& inventory, u32 researchTier) {
    if (evaluatePlacement(body, partId, localPosition, inventory, researchTier) != PlacementResult::Ok) return false;

    const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(partId);
    for (const RecipeIngredient& ingredient : definition.cost) {
        inventory.remove(ingredient.id, ingredient.amount);
    }

    BasePart part;
    part.instanceId = nextInstanceId++;
    part.partId = partId;
    part.localPosition = localPosition;
    part.upDirection = body.upAt(localPosition);
    part.rotation = rotation;
    part.health = 1.0;
    placedParts.push_back(part);

    if (placedParts.size() == 1) anchorPosition = localPosition;
    return true;
}

bool BaseGrid::removeNearest(const DVec3& localPosition, f64 maximumDistance, Inventory& inventory) {
    usize bestIndex = placedParts.size();
    f64 bestDistance = maximumDistance;
    for (usize index = 0; index < placedParts.size(); ++index) {
        const f64 distance = length(placedParts[index].localPosition - localPosition);
        if (distance >= bestDistance) continue;
        bestDistance = distance;
        bestIndex = index;
    }
    if (bestIndex >= placedParts.size()) return false;

    const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(placedParts[bestIndex].partId);
    for (const RecipeIngredient& ingredient : definition.cost) {
        inventory.add(ingredient.id, ingredient.amount);
    }
    placedParts.erase(placedParts.begin() + static_cast<isize>(bestIndex));
    return true;
}

BasePowerReport BaseGrid::powerReport() const {
    BasePowerReport report;
    for (const BasePart& part : placedParts) {
        const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(part.partId);
        report.production += definition.powerProduction * part.health;
        report.draw += definition.powerDraw;
        report.storageCapacity += definition.storageCapacity;
    }
    report.balance = report.production - report.draw;
    report.stable = report.balance >= 0.0;
    if (!report.stable) {
        f64 deficit = -report.balance;
        for (usize index = placedParts.size(); index > 0 && deficit > 0.0; --index) {
            const BuildPartDefinition& definition =
                BuildPartCatalog::instance().definition(placedParts[index - 1].partId);
            if (definition.powerDraw <= 0.0) continue;
            deficit -= definition.powerDraw;
            ++report.unpoweredParts;
        }
    }
    return report;
}

bool BaseGrid::sheltersPoint(const DVec3& localPosition) const {
    for (const BasePart& part : placedParts) {
        const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(part.partId);
        if (definition.category != BuildCategory::Habitation) continue;
        if (definition.id == BuildPartId::Foundation || definition.id == BuildPartId::Ramp) continue;
        if (length(part.localPosition - localPosition) < static_cast<f64>(definition.footprintMeters) * 0.7) {
            return true;
        }
    }
    return false;
}

f64 BaseGrid::totalValue() const {
    f64 total = 0.0;
    for (const BasePart& part : placedParts) {
        const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(part.partId);
        for (const RecipeIngredient& ingredient : definition.cost) {
            total += ItemDatabase::instance().definition(ingredient.id).baseValue * ingredient.amount;
        }
    }
    return total;
}

const char* BaseGrid::placementMessage(PlacementResult result) {
    switch (result) {
        case PlacementResult::Ok: return "PLATZIERUNG MOEGLICH";
        case PlacementResult::TooSteep: return "UNTERGRUND ZU STEIL";
        case PlacementResult::Overlapping: return "KOLLIDIERT MIT BAUTEIL";
        case PlacementResult::OutOfRange: return "AUSSERHALB DER BASISGRENZE";
        case PlacementResult::MissingMaterial: return "MATERIAL FEHLT";
        case PlacementResult::Unsupported: return "NICHT AUSREICHEND ABGESTUETZT";
        case PlacementResult::ResearchMissing: return "FORSCHUNGSSTUFE ZU NIEDRIG";
        default: return "";
    }
}

}
