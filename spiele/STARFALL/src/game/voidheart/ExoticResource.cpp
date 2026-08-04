#include "ExoticResource.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {

ExoticResourceLedger::ExoticResourceLedger() {
    catalogue.resize(static_cast<usize>(ExoticResourceId::Count));

    ExoticResourceDefinition& voidMatter = catalogue[static_cast<usize>(ExoticResourceId::VoidMatter)];
    voidMatter.id = ExoticResourceId::VoidMatter;
    voidMatter.name = "Void Matter";
    voidMatter.description = "Exotische Materie mit negativer Energiedichte, Treibstoff des Void-Antriebs.";
    voidMatter.harvestLocation = "Verzerrungszone, Randbereich der Akkretionsscheibe";
    voidMatter.unitMassKilograms = 0.4;
    voidMatter.baseValue = 24000.0;
    voidMatter.minimumZoneRadiusInGravitationalRadii = 90.0;

    ExoticResourceDefinition& chronon = catalogue[static_cast<usize>(ExoticResourceId::ChrononCrystal)];
    chronon.id = ExoticResourceId::ChrononCrystal;
    chronon.name = "Chronon Crystal";
    chronon.description = "Kristallisierte Zeitdifferenz, Basis aller Zeitmodule.";
    chronon.harvestLocation = "Ergosphaere, entlang der Frame-Dragging-Front";
    chronon.unitMassKilograms = 1.8;
    chronon.baseValue = 61000.0;
    chronon.minimumZoneRadiusInGravitationalRadii = 2.4;
    chronon.requiresVoidDrive = true;

    ExoticResourceDefinition& core = catalogue[static_cast<usize>(ExoticResourceId::SingularityCore)];
    core.id = ExoticResourceId::SingularityCore;
    core.name = "Singularity Core";
    core.description = "Eingeschlossene Mikrosingularitaet, Energiequelle hoechster Stufe.";
    core.harvestLocation = "NULL FOUNDRY, Giessbahn drei";
    core.unitMassKilograms = 480.0;
    core.baseValue = 310000.0;
    core.minimumZoneRadiusInGravitationalRadii = 61.0;
    core.requiresVoidDrive = true;

    ExoticResourceDefinition& alloy = catalogue[static_cast<usize>(ExoticResourceId::LensedAlloy)];
    alloy.id = ExoticResourceId::LensedAlloy;
    alloy.name = "Lensed Alloy";
    alloy.description = "In gekruemmtem Raum erstarrte Legierung, hoechste Rumpfklasse.";
    alloy.harvestLocation = "NULL FOUNDRY, Schmelzkathedrale";
    alloy.unitMassKilograms = 42.0;
    alloy.baseValue = 88000.0;
    alloy.minimumZoneRadiusInGravitationalRadii = 61.0;

    ExoticResourceDefinition& dust = catalogue[static_cast<usize>(ExoticResourceId::HorizonDust)];
    dust.id = ExoticResourceId::HorizonDust;
    dust.name = "Horizon Dust";
    dust.description = "Staub aus der Photonensphaere, Katalysator der Endgame-Forschung.";
    dust.harvestLocation = "Photonensphaere bei 1,5 Schwarzschild-Radien";
    dust.unitMassKilograms = 0.02;
    dust.baseValue = 145000.0;
    dust.minimumZoneRadiusInGravitationalRadii = 3.1;
    dust.requiresVoidDrive = true;
}

void ExoticResourceLedger::add(ExoticResourceId id, f64 quantity) {
    if (quantity <= 0.0) return;
    amounts[static_cast<usize>(id)] += quantity;
}

bool ExoticResourceLedger::consume(ExoticResourceId id, f64 quantity) {
    const usize index = static_cast<usize>(id);
    if (amounts[index] < quantity) return false;
    amounts[index] -= quantity;
    return true;
}

f64 ExoticResourceLedger::totalValue() const {
    f64 total = 0.0;
    for (usize index = 0; index < static_cast<usize>(ExoticResourceId::Count); ++index) {
        total += amounts[index] * catalogue[index].baseValue;
    }
    return total;
}

f64 ExoticResourceLedger::totalMassKilograms() const {
    f64 total = 0.0;
    for (usize index = 0; index < static_cast<usize>(ExoticResourceId::Count); ++index) {
        total += amounts[index] * catalogue[index].unitMassKilograms;
    }
    return total;
}

void ExoticResourceLedger::clear() {
    for (usize index = 0; index < static_cast<usize>(ExoticResourceId::Count); ++index) {
        amounts[index] = 0.0;
    }
}

f64 ExoticResourceLedger::harvestRatePerSecond(ExoticResourceId id, f64 radiusInGravitationalRadii,
                                               f64 scannerQuality) {
    f64 optimum = 0.0;
    f64 spread = 1.0;
    f64 peakRate = 0.0;
    switch (id) {
        case ExoticResourceId::VoidMatter: optimum = 140.0; spread = 90.0; peakRate = 0.42; break;
        case ExoticResourceId::ChrononCrystal: optimum = 2.1; spread = 0.9; peakRate = 0.06; break;
        case ExoticResourceId::SingularityCore: optimum = 61.0; spread = 12.0; peakRate = 0.004; break;
        case ExoticResourceId::LensedAlloy: optimum = 61.0; spread = 24.0; peakRate = 0.09; break;
        case ExoticResourceId::HorizonDust: optimum = 3.0; spread = 0.8; peakRate = 0.14; break;
        default: return 0.0;
    }
    const f64 offset = (radiusInGravitationalRadii - optimum) / spread;
    const f64 window = std::exp(-offset * offset);
    return peakRate * window * clampValue(scannerQuality, 0.0, 2.0);
}

}
