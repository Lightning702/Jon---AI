#include "RecipeDatabase.hpp"

#include "../player/Inventory.hpp"

namespace sf {
namespace {

Recipe make(u32 id, const char* name, RecipeKind kind, std::vector<RecipeIngredient> inputs, ItemId output,
            u32 outputAmount, f64 seconds, u32 tier) {
    Recipe recipe;
    recipe.id = id;
    recipe.name = name;
    recipe.kind = kind;
    recipe.inputs = std::move(inputs);
    recipe.output = output;
    recipe.outputAmount = outputAmount;
    recipe.secondsPerBatch = seconds;
    recipe.requiredResearchTier = tier;
    return recipe;
}

}

RecipeDatabase::RecipeDatabase() {
    u32 nextId = 1;

    entries.push_back(make(nextId++, "Kohlenstoff verdichten", RecipeKind::Refine,
                           {{ItemId::Carbon, 2}}, ItemId::CondensedCarbon, 1, 0.6, 1));
    entries.push_back(make(nextId++, "Ferrit schmelzen", RecipeKind::Refine, {{ItemId::Ferrite, 1}},
                           ItemId::PureFerrite, 1, 0.5, 1));
    entries.push_back(make(nextId++, "Chromatisches Metall gewinnen", RecipeKind::Refine,
                           {{ItemId::Copper, 2}}, ItemId::Chromatic, 1, 1.2, 2));
    entries.push_back(make(nextId++, "Chromatisches Metall aus Kobalt", RecipeKind::Refine,
                           {{ItemId::Cobalt, 2}}, ItemId::Chromatic, 1, 1.2, 2));
    entries.push_back(make(nextId++, "Sauerstoff aus Eis", RecipeKind::Refine,
                           {{ItemId::IceCrystal, 2}}, ItemId::Oxygen, 1, 0.8, 1));
    entries.push_back(make(nextId++, "Tritium aus Deuterium", RecipeKind::Refine,
                           {{ItemId::Deuterium, 3}, {ItemId::Uranite, 1}}, ItemId::Tritium, 2, 2.4, 3));

    entries.push_back(make(nextId++, "Metallplatte", RecipeKind::Handcraft, {{ItemId::PureFerrite, 50}},
                           ItemId::MetalPlate, 1, 1.0, 1));
    entries.push_back(make(nextId++, "Kohlenstoffnanoroehre", RecipeKind::Handcraft,
                           {{ItemId::CondensedCarbon, 50}}, ItemId::CarbonNanotube, 1, 1.0, 1));
    entries.push_back(make(nextId++, "Chemiezelle", RecipeKind::Handcraft,
                           {{ItemId::CondensedCarbon, 20}, {ItemId::Sulphur, 40}}, ItemId::ChemicalCell, 1, 1.0, 2));
    entries.push_back(make(nextId++, "Thermalzelle", RecipeKind::Handcraft,
                           {{ItemId::ChemicalCell, 1}, {ItemId::Phosphor, 30}}, ItemId::ThermalCell, 1, 1.0, 2));
    entries.push_back(make(nextId++, "Lebenserhaltungsgel", RecipeKind::Handcraft,
                           {{ItemId::Oxygen, 60}, {ItemId::CondensedCarbon, 20}}, ItemId::LifeSupportGel, 1, 1.0, 1));
    entries.push_back(make(nextId++, "Gefahrenkapsel", RecipeKind::Handcraft,
                           {{ItemId::SaltCrystal, 40}, {ItemId::ThermalCell, 1}}, ItemId::HazardCapsule, 1, 1.0, 2));
    entries.push_back(make(nextId++, "Startbrennstoff", RecipeKind::Handcraft,
                           {{ItemId::Ferrite, 40}, {ItemId::CondensedCarbon, 30}}, ItemId::LaunchFuel, 1, 1.0, 1));
    entries.push_back(make(nextId++, "Brennstab", RecipeKind::Handcraft,
                           {{ItemId::CondensedCarbon, 50}, {ItemId::Uranite, 20}}, ItemId::FuelRod, 1, 1.5, 2));
    entries.push_back(make(nextId++, "Strukturplatte", RecipeKind::Handcraft,
                           {{ItemId::MetalPlate, 1}, {ItemId::Silicate, 40}}, ItemId::StructurePanel, 2, 1.0, 1));
    entries.push_back(make(nextId++, "Energiekupplung", RecipeKind::Handcraft,
                           {{ItemId::Chromatic, 20}, {ItemId::CarbonNanotube, 1}}, ItemId::PowerCoupling, 1, 1.2, 2));
    entries.push_back(make(nextId++, "Antimaterie-Gehaeuse", RecipeKind::Handcraft,
                           {{ItemId::MetalPlate, 1}, {ItemId::Chromatic, 30}}, ItemId::AntimatterHousing, 1, 1.4, 3));
    entries.push_back(make(nextId++, "Antimaterie", RecipeKind::Handcraft,
                           {{ItemId::Chromatic, 25}, {ItemId::CondensedCarbon, 40}, {ItemId::Phosphor, 20}},
                           ItemId::Antimatter, 1, 2.0, 3));
    entries.push_back(make(nextId++, "Warpzelle", RecipeKind::Handcraft,
                           {{ItemId::Antimatter, 1}, {ItemId::AntimatterHousing, 1}}, ItemId::WarpCell, 1, 2.0, 3));
    entries.push_back(make(nextId++, "Reparaturkit", RecipeKind::Handcraft,
                           {{ItemId::MetalPlate, 1}, {ItemId::ChemicalCell, 1}}, ItemId::RepairKit, 1, 1.2, 2));
    entries.push_back(make(nextId++, "Navigationskarte", RecipeKind::Handcraft,
                           {{ItemId::Chromatic, 10}, {ItemId::Silicate, 60}}, ItemId::NavigationChart, 1, 1.0, 2));

    entries.push_back(make(nextId++, "Ration zubereiten", RecipeKind::Cook,
                           {{ItemId::Carbon, 30}, {ItemId::SaltCrystal, 10}}, ItemId::Ration, 2, 3.0, 1));

    entries.push_back(make(nextId++, "Lensed Alloy giessen", RecipeKind::Refine,
                           {{ItemId::VoidMatter, 2}, {ItemId::MetalPlate, 2}}, ItemId::LensedAlloy, 1, 6.0, 4));
    entries.push_back(make(nextId++, "Singularity Core stabilisieren", RecipeKind::Refine,
                           {{ItemId::VoidMatter, 8}, {ItemId::ChrononCrystal, 2}, {ItemId::LensedAlloy, 4}},
                           ItemId::SingularityCore, 1, 24.0, 5));
}

const RecipeDatabase& RecipeDatabase::instance() {
    static RecipeDatabase database;
    return database;
}

const Recipe* RecipeDatabase::find(u32 id) const {
    for (const Recipe& recipe : entries) {
        if (recipe.id == id) return &recipe;
    }
    return nullptr;
}

std::vector<const Recipe*> RecipeDatabase::forOutput(ItemId output) const {
    std::vector<const Recipe*> result;
    for (const Recipe& recipe : entries) {
        if (recipe.output == output) result.push_back(&recipe);
    }
    return result;
}

std::vector<const Recipe*> RecipeDatabase::ofKind(RecipeKind kind) const {
    std::vector<const Recipe*> result;
    for (const Recipe& recipe : entries) {
        if (recipe.kind == kind) result.push_back(&recipe);
    }
    return result;
}

std::vector<const Recipe*> RecipeDatabase::craftableFrom(const Inventory& inventory, u32 researchTier) const {
    std::vector<const Recipe*> result;
    for (const Recipe& recipe : entries) {
        if (canCraft(recipe, inventory, researchTier)) result.push_back(&recipe);
    }
    return result;
}

const char* RecipeDatabase::kindName(RecipeKind kind) {
    switch (kind) {
        case RecipeKind::Handcraft: return "HANDWERK";
        case RecipeKind::Refine: return "RAFFINERIE";
        case RecipeKind::Cook: return "KUECHE";
        default: return "";
    }
}

bool canCraft(const Recipe& recipe, const Inventory& inventory, u32 researchTier) {
    if (researchTier < recipe.requiredResearchTier) return false;
    for (const RecipeIngredient& ingredient : recipe.inputs) {
        if (!inventory.has(ingredient.id, ingredient.amount)) return false;
    }
    return inventory.acceptableAmount(recipe.output) >= recipe.outputAmount;
}

bool performCraft(const Recipe& recipe, Inventory& inventory, u32 researchTier) {
    if (!canCraft(recipe, inventory, researchTier)) return false;
    for (const RecipeIngredient& ingredient : recipe.inputs) {
        inventory.remove(ingredient.id, ingredient.amount);
    }
    inventory.add(recipe.output, recipe.outputAmount);
    return true;
}

}
