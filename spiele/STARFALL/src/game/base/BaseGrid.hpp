#pragma once

#include "../crafting/RecipeDatabase.hpp"
#include "../planet/PlanetBody.hpp"
#include "../player/Inventory.hpp"

#include <string>
#include <vector>

namespace sf {

enum class BuildCategory : u32 {
    Habitation = 0,
    Laboratory,
    Factory,
    Farm,
    Hangar,
    PowerPlant,
    Defence,
    Logistics,
    Count
};

enum class BuildPartId : u32 {
    Foundation = 0,
    Wall,
    Doorway,
    Roof,
    Ramp,
    HabitatDome,
    Airlock,
    Greenhouse,
    ResearchTerminal,
    Refiner,
    Smelter,
    AssemblyLine,
    CropBed,
    Hydroponics,
    LandingPad,
    RepairDock,
    SolarPanel,
    WindTurbine,
    Geothermal,
    FusionReactor,
    SingularityReactor,
    Turret,
    ShieldPylon,
    SensorMast,
    StorageContainer,
    Conveyor,
    DronePort,
    Teleporter,
    Count
};

struct BuildPartDefinition {
    BuildPartId id = BuildPartId::Foundation;
    std::string name;
    BuildCategory category = BuildCategory::Habitation;
    std::vector<RecipeIngredient> cost;
    f32 footprintMeters = 4.0f;
    f32 heightMeters = 3.0f;
    f64 powerProduction = 0.0;
    f64 powerDraw = 0.0;
    f64 storageCapacity = 0.0;
    f64 structuralSupport = 1.0;
    f64 structuralLoad = 1.0;
    u32 requiredResearchTier = 1;
    Vec3 tint = Vec3(0.62f, 0.64f, 0.68f);
};

struct BasePart {
    u32 instanceId = 0;
    BuildPartId partId = BuildPartId::Foundation;
    DVec3 localPosition = DVec3::zero();
    DVec3 upDirection = DVec3::unitY();
    f32 rotation = 0.0f;
    f64 health = 1.0;
    bool powered = false;
};

struct BasePowerReport {
    f64 production = 0.0;
    f64 draw = 0.0;
    f64 balance = 0.0;
    f64 storageCapacity = 0.0;
    u32 unpoweredParts = 0;
    bool stable = true;
};

class BuildPartCatalog {
public:
    static const BuildPartCatalog& instance();
    const BuildPartDefinition& definition(BuildPartId id) const { return entries[static_cast<usize>(id)]; }
    const std::vector<BuildPartDefinition>& all() const { return entries; }
    std::vector<const BuildPartDefinition*> ofCategory(BuildCategory category) const;
    static const char* categoryName(BuildCategory category);

private:
    BuildPartCatalog();
    std::vector<BuildPartDefinition> entries;
};

enum class PlacementResult : u32 {
    Ok = 0,
    TooSteep,
    Overlapping,
    OutOfRange,
    MissingMaterial,
    Unsupported,
    ResearchMissing
};

class BaseGrid {
public:
    void configure(const std::string& baseName, const DVec3& anchorLocalPosition);

    PlacementResult evaluatePlacement(const PlanetBody& body, BuildPartId partId, const DVec3& localPosition,
                                      const Inventory& inventory, u32 researchTier) const;
    bool place(const PlanetBody& body, BuildPartId partId, const DVec3& localPosition, f32 rotation,
               Inventory& inventory, u32 researchTier);
    bool removeNearest(const DVec3& localPosition, f64 maximumDistance, Inventory& inventory);

    DVec3 snapPosition(const PlanetBody& body, const DVec3& desiredLocalPosition, BuildPartId partId) const;

    BasePowerReport powerReport() const;
    const std::vector<BasePart>& parts() const { return placedParts; }
    const std::string& name() const { return displayName; }
    const DVec3& anchor() const { return anchorPosition; }
    bool empty() const { return placedParts.empty(); }
    bool sheltersPoint(const DVec3& localPosition) const;
    f64 totalValue() const;

    static const char* placementMessage(PlacementResult result);

private:
    std::vector<BasePart> placedParts;
    std::string displayName = "BASIS";
    DVec3 anchorPosition = DVec3::zero();
    u32 nextInstanceId = 1;
};

}
