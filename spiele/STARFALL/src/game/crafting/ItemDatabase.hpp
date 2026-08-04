#pragma once

#include "../../engine/core/Types.hpp"
#include "../../engine/math/Vec3.hpp"

#include <string>
#include <vector>

namespace sf {

enum class ItemId : u32 {
    None = 0,
    Ferrite,
    Copper,
    Cobalt,
    Silicate,
    Carbon,
    CondensedCarbon,
    Oxygen,
    Nitrogen,
    Sulphur,
    Deuterium,
    Tritium,
    IceCrystal,
    SaltCrystal,
    Phosphor,
    Uranite,
    Platinum,
    Gold,
    Chromatic,
    PureFerrite,
    MetalPlate,
    CarbonNanotube,
    ChemicalCell,
    ThermalCell,
    LifeSupportGel,
    HazardCapsule,
    FuelRod,
    LaunchFuel,
    WarpCell,
    StructurePanel,
    PowerCoupling,
    Antimatter,
    AntimatterHousing,
    VoidMatter,
    ChrononCrystal,
    SingularityCore,
    LensedAlloy,
    HorizonDust,
    NavigationChart,
    RepairKit,
    Ration,
    Count
};

enum class ItemCategory : u32 {
    Element = 0,
    Refined,
    Component,
    Consumable,
    Technology,
    Exotic,
    Count
};

struct ItemDefinition {
    ItemId id = ItemId::None;
    std::string name;
    std::string shortName;
    std::string description;
    ItemCategory category = ItemCategory::Element;
    u32 stackSize = 250;
    f64 baseValue = 10.0;
    f64 unitMassKilograms = 1.0;
    bool minable = false;
    bool refinable = false;
    Vec3 tint = Vec3(0.7f, 0.7f, 0.7f);
};

class ItemDatabase {
public:
    static const ItemDatabase& instance();

    const ItemDefinition& definition(ItemId id) const { return entries[static_cast<usize>(id)]; }
    const std::vector<ItemDefinition>& all() const { return entries; }
    ItemId findByName(const std::string& name) const;

    static const char* categoryName(ItemCategory category);

private:
    ItemDatabase();
    std::vector<ItemDefinition> entries;
};

struct ItemStack {
    ItemId id = ItemId::None;
    u32 count = 0;

    bool empty() const { return id == ItemId::None || count == 0; }
    void clear() {
        id = ItemId::None;
        count = 0;
    }
    f64 value() const { return static_cast<f64>(count) * ItemDatabase::instance().definition(id).baseValue; }
    f64 massKilograms() const {
        return static_cast<f64>(count) * ItemDatabase::instance().definition(id).unitMassKilograms;
    }
};

}
