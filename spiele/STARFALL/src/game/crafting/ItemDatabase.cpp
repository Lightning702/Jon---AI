#include "ItemDatabase.hpp"

namespace sf {
namespace {

ItemDefinition make(ItemId id, const char* name, const char* shortName, const char* description,
                    ItemCategory category, u32 stackSize, f64 baseValue, f64 mass, bool minable, bool refinable,
                    const Vec3& tint) {
    ItemDefinition definition;
    definition.id = id;
    definition.name = name;
    definition.shortName = shortName;
    definition.description = description;
    definition.category = category;
    definition.stackSize = stackSize;
    definition.baseValue = baseValue;
    definition.unitMassKilograms = mass;
    definition.minable = minable;
    definition.refinable = refinable;
    definition.tint = tint;
    return definition;
}

}

ItemDatabase::ItemDatabase() {
    entries.resize(static_cast<usize>(ItemId::Count));

    entries[static_cast<usize>(ItemId::None)] =
        make(ItemId::None, "Leer", "--", "Kein Gegenstand.", ItemCategory::Element, 0, 0.0, 0.0, false, false,
             Vec3(0.5f, 0.5f, 0.5f));

    entries[static_cast<usize>(ItemId::Ferrite)] =
        make(ItemId::Ferrite, "Ferrit", "Fe", "Haeufiges Eisenerz aus Felsformationen. Grundstoff jeder Reparatur.",
             ItemCategory::Element, 250, 14.0, 1.0, true, true, Vec3(0.62f, 0.40f, 0.28f));
    entries[static_cast<usize>(ItemId::Copper)] =
        make(ItemId::Copper, "Kupfer", "Cu", "Leitfaehiges Metall aus Adern in Riftzonen.", ItemCategory::Element,
             250, 42.0, 1.1, true, true, Vec3(0.82f, 0.44f, 0.22f));
    entries[static_cast<usize>(ItemId::Cobalt)] =
        make(ItemId::Cobalt, "Kobalt", "Co", "Blaues Metall, waechst in Hoehlen an Waenden.", ItemCategory::Element,
             250, 38.0, 1.2, true, true, Vec3(0.24f, 0.42f, 0.86f));
    entries[static_cast<usize>(ItemId::Silicate)] =
        make(ItemId::Silicate, "Silikat", "Si", "Kristallines Pulver aus Sand und Gestein.", ItemCategory::Element,
             250, 18.0, 0.8, true, true, Vec3(0.76f, 0.74f, 0.62f));
    entries[static_cast<usize>(ItemId::Carbon)] =
        make(ItemId::Carbon, "Kohlenstoff", "C", "Aus allem Organischen zu gewinnen. Brennstoff fuer Werkzeuge.",
             ItemCategory::Element, 250, 12.0, 0.6, true, true, Vec3(0.18f, 0.18f, 0.20f));
    entries[static_cast<usize>(ItemId::Oxygen)] =
        make(ItemId::Oxygen, "Sauerstoff", "O", "Aus Pflanzen und Eis. Haelt den Anzug am Laufen.",
             ItemCategory::Element, 250, 34.0, 0.2, true, true, Vec3(0.44f, 0.86f, 0.92f));
    entries[static_cast<usize>(ItemId::Nitrogen)] =
        make(ItemId::Nitrogen, "Stickstoff", "N", "Atmosphaerisches Gas, mit Extraktor abbaubar.",
             ItemCategory::Element, 250, 44.0, 0.2, true, true, Vec3(0.52f, 0.72f, 0.44f));
    entries[static_cast<usize>(ItemId::Sulphur)] =
        make(ItemId::Sulphur, "Schwefel", "S", "Gelber Kristall aus Vulkanfeldern.", ItemCategory::Element, 250, 46.0,
             0.9, true, true, Vec3(0.92f, 0.82f, 0.28f));
    entries[static_cast<usize>(ItemId::Deuterium)] =
        make(ItemId::Deuterium, "Deuterium", "D", "Standardtreibstoff des Hyperantriebs.", ItemCategory::Element, 250,
             68.0, 0.5, true, true, Vec3(0.36f, 0.78f, 0.88f));
    entries[static_cast<usize>(ItemId::Tritium)] =
        make(ItemId::Tritium, "Tritium", "T", "Langstreckentreibstoff aus Kometeneis.", ItemCategory::Element, 250,
             86.0, 0.5, true, true, Vec3(0.48f, 0.90f, 0.76f));
    entries[static_cast<usize>(ItemId::IceCrystal)] =
        make(ItemId::IceCrystal, "Eiskristall", "Ice", "Gefrorenes Wasser aus Gletscherfeldern.",
             ItemCategory::Element, 250, 22.0, 1.0, true, true, Vec3(0.78f, 0.90f, 0.98f));
    entries[static_cast<usize>(ItemId::SaltCrystal)] =
        make(ItemId::SaltCrystal, "Salzkristall", "Salt", "Aus Salzwuesten und Kuestenbecken.", ItemCategory::Element,
             250, 26.0, 1.0, true, true, Vec3(0.92f, 0.90f, 0.86f));
    entries[static_cast<usize>(ItemId::Phosphor)] =
        make(ItemId::Phosphor, "Phosphor", "P", "Leuchtet im Dunkeln, waechst in Pilzwaeldern.",
             ItemCategory::Element, 250, 52.0, 0.8, true, true, Vec3(0.68f, 0.94f, 0.42f));
    entries[static_cast<usize>(ItemId::Uranite)] =
        make(ItemId::Uranite, "Uranit", "U", "Radioaktives Erz. Ohne Abschirmung gefaehrlich.",
             ItemCategory::Element, 250, 118.0, 2.4, true, true, Vec3(0.44f, 0.92f, 0.32f));
    entries[static_cast<usize>(ItemId::Platinum)] =
        make(ItemId::Platinum, "Platin", "Pt", "Seltenes Edelmetall aus Tiefenadern.", ItemCategory::Element, 250,
             196.0, 2.1, true, true, Vec3(0.86f, 0.88f, 0.90f));
    entries[static_cast<usize>(ItemId::Gold)] =
        make(ItemId::Gold, "Gold", "Au", "Handelsware ohne technische Bedeutung.", ItemCategory::Element, 250, 212.0,
             2.4, true, true, Vec3(0.94f, 0.78f, 0.30f));
    entries[static_cast<usize>(ItemId::Chromatic)] =
        make(ItemId::Chromatic, "Chromatisches Metall", "Cr", "Aus Farbmetallen raffiniert, Basis vieler Module.",
             ItemCategory::Refined, 250, 245.0, 1.6, false, false, Vec3(0.62f, 0.34f, 0.86f));

    entries[static_cast<usize>(ItemId::CondensedCarbon)] =
        make(ItemId::CondensedCarbon, "Kondensierter Kohlenstoff", "C+", "Verdichteter Kohlenstoff, doppelte Energie.",
             ItemCategory::Refined, 250, 48.0, 0.9, false, false, Vec3(0.12f, 0.12f, 0.14f));
    entries[static_cast<usize>(ItemId::PureFerrite)] =
        make(ItemId::PureFerrite, "Reines Ferrit", "Fe+", "Geschmolzenes Ferrit fuer Bauteile.", ItemCategory::Refined,
             250, 34.0, 1.0, false, false, Vec3(0.74f, 0.52f, 0.34f));
    entries[static_cast<usize>(ItemId::MetalPlate)] =
        make(ItemId::MetalPlate, "Metallplatte", "Plate", "Gepresste Platte, Grundelement jedes Bauteils.",
             ItemCategory::Component, 100, 220.0, 6.0, false, false, Vec3(0.66f, 0.68f, 0.70f));
    entries[static_cast<usize>(ItemId::CarbonNanotube)] =
        make(ItemId::CarbonNanotube, "Kohlenstoffnanoroehre", "Tube", "Zugfeste Faser fuer Strukturen.",
             ItemCategory::Component, 100, 285.0, 2.0, false, false, Vec3(0.22f, 0.24f, 0.26f));
    entries[static_cast<usize>(ItemId::ChemicalCell)] =
        make(ItemId::ChemicalCell, "Chemiezelle", "Cell", "Energiezelle fuer Werkzeuge und Anlagen.",
             ItemCategory::Component, 100, 310.0, 3.0, false, false, Vec3(0.36f, 0.82f, 0.52f));
    entries[static_cast<usize>(ItemId::ThermalCell)] =
        make(ItemId::ThermalCell, "Thermalzelle", "Therm", "Reguliert Anzugstemperatur in Extremzonen.",
             ItemCategory::Component, 100, 340.0, 3.2, false, false, Vec3(0.92f, 0.52f, 0.24f));
    entries[static_cast<usize>(ItemId::LifeSupportGel)] =
        make(ItemId::LifeSupportGel, "Lebenserhaltungsgel", "Gel", "Fuellt die Lebenserhaltung des Anzugs auf.",
             ItemCategory::Consumable, 50, 410.0, 1.4, false, false, Vec3(0.42f, 0.88f, 0.86f));
    entries[static_cast<usize>(ItemId::HazardCapsule)] =
        make(ItemId::HazardCapsule, "Gefahrenkapsel", "Haz", "Laedt den Gefahrenschutz vollstaendig auf.",
             ItemCategory::Consumable, 50, 440.0, 1.4, false, false, Vec3(0.92f, 0.72f, 0.28f));
    entries[static_cast<usize>(ItemId::FuelRod)] =
        make(ItemId::FuelRod, "Brennstab", "Rod", "Treibstoff fuer Basisgeneratoren.", ItemCategory::Component, 100,
             520.0, 8.0, false, false, Vec3(0.52f, 0.88f, 0.36f));
    entries[static_cast<usize>(ItemId::LaunchFuel)] =
        make(ItemId::LaunchFuel, "Startbrennstoff", "Launch", "Fuellt die Startdüsen des Schiffs.",
             ItemCategory::Component, 100, 480.0, 5.0, false, false, Vec3(0.86f, 0.44f, 0.30f));
    entries[static_cast<usize>(ItemId::WarpCell)] =
        make(ItemId::WarpCell, "Warpzelle", "Warp", "Ein Sprung pro Zelle.", ItemCategory::Component, 50, 1240.0,
             12.0, false, false, Vec3(0.48f, 0.62f, 0.96f));
    entries[static_cast<usize>(ItemId::StructurePanel)] =
        make(ItemId::StructurePanel, "Strukturplatte", "Struct", "Bauteil fuer Habitate und Hallen.",
             ItemCategory::Component, 100, 190.0, 9.0, false, false, Vec3(0.58f, 0.60f, 0.64f));
    entries[static_cast<usize>(ItemId::PowerCoupling)] =
        make(ItemId::PowerCoupling, "Energiekupplung", "Coup", "Verbindet Erzeuger und Verbraucher einer Basis.",
             ItemCategory::Component, 100, 265.0, 2.6, false, false, Vec3(0.36f, 0.86f, 0.92f));
    entries[static_cast<usize>(ItemId::Antimatter)] =
        make(ItemId::Antimatter, "Antimaterie", "Anti", "In Magnetfeldern gehalten, Kern jeder Warpzelle.",
             ItemCategory::Component, 50, 980.0, 0.4, false, false, Vec3(0.94f, 0.36f, 0.86f));
    entries[static_cast<usize>(ItemId::AntimatterHousing)] =
        make(ItemId::AntimatterHousing, "Antimaterie-Gehaeuse", "Hous", "Behaelter fuer Antimaterie.",
             ItemCategory::Component, 50, 260.0, 5.0, false, false, Vec3(0.62f, 0.64f, 0.68f));
    entries[static_cast<usize>(ItemId::NavigationChart)] =
        make(ItemId::NavigationChart, "Navigationskarte", "Chart", "Weist auf ein unbekanntes Ziel im System.",
             ItemCategory::Technology, 20, 720.0, 0.2, false, false, Vec3(0.42f, 0.88f, 0.88f));
    entries[static_cast<usize>(ItemId::RepairKit)] =
        make(ItemId::RepairKit, "Reparaturkit", "Kit", "Setzt ein beschaedigtes Schiffsmodul instand.",
             ItemCategory::Consumable, 50, 560.0, 4.0, false, false, Vec3(0.88f, 0.86f, 0.42f));
    entries[static_cast<usize>(ItemId::Ration)] =
        make(ItemId::Ration, "Ration", "Food", "Stellt Ausdauer und Gesundheit wieder her.",
             ItemCategory::Consumable, 50, 130.0, 0.6, false, false, Vec3(0.78f, 0.62f, 0.34f));

    entries[static_cast<usize>(ItemId::VoidMatter)] =
        make(ItemId::VoidMatter, "Void Matter", "Void", "Exotische Materie mit negativer Energiedichte.",
             ItemCategory::Exotic, 100, 24000.0, 0.4, false, false, Vec3(0.42f, 0.18f, 0.72f));
    entries[static_cast<usize>(ItemId::ChrononCrystal)] =
        make(ItemId::ChrononCrystal, "Chronon Crystal", "Chron", "Kristallisierte Zeitdifferenz.",
             ItemCategory::Exotic, 100, 61000.0, 1.8, false, false, Vec3(0.86f, 0.92f, 0.98f));
    entries[static_cast<usize>(ItemId::SingularityCore)] =
        make(ItemId::SingularityCore, "Singularity Core", "Sing", "Eingeschlossene Mikrosingularitaet.",
             ItemCategory::Exotic, 10, 310000.0, 480.0, false, false, Vec3(0.10f, 0.10f, 0.14f));
    entries[static_cast<usize>(ItemId::LensedAlloy)] =
        make(ItemId::LensedAlloy, "Lensed Alloy", "Lens", "In gekruemmtem Raum erstarrte Legierung.",
             ItemCategory::Exotic, 100, 88000.0, 42.0, false, false, Vec3(0.72f, 0.68f, 0.86f));
    entries[static_cast<usize>(ItemId::HorizonDust)] =
        make(ItemId::HorizonDust, "Horizon Dust", "Dust", "Staub aus der Photonensphaere.", ItemCategory::Exotic, 100,
             145000.0, 0.02, false, false, Vec3(0.98f, 0.86f, 0.54f));
}

const ItemDatabase& ItemDatabase::instance() {
    static ItemDatabase database;
    return database;
}

ItemId ItemDatabase::findByName(const std::string& name) const {
    for (const ItemDefinition& definition : entries) {
        if (definition.name == name || definition.shortName == name) return definition.id;
    }
    return ItemId::None;
}

const char* ItemDatabase::categoryName(ItemCategory category) {
    switch (category) {
        case ItemCategory::Element: return "ELEMENT";
        case ItemCategory::Refined: return "RAFFINIERT";
        case ItemCategory::Component: return "BAUTEIL";
        case ItemCategory::Consumable: return "VERBRAUCH";
        case ItemCategory::Technology: return "TECHNOLOGIE";
        case ItemCategory::Exotic: return "EXOTISCH";
        default: return "";
    }
}

}
