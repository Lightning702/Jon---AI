#include "VoidStation.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {

DVec3 VoidStationProfile::positionAt(const VoidHeart& heart, f64 universeSeconds) const {
    const f64 radius = orbitRadiusInGravitationalRadii * heart.gravitationalRadiusMeters();
    const f64 period = orbitalPeriodSeconds(heart);
    const f64 angle = orbitalPhaseRadians + kTwoPiDouble * (period > 0.0 ? universeSeconds / period : 0.0);
    const f64 inclinationCosine = std::cos(orbitalInclinationRadians);
    const f64 inclinationSine = std::sin(orbitalInclinationRadians);
    const DVec3 planar(std::cos(angle) * radius, 0.0, std::sin(angle) * radius);
    const DVec3 inclined(planar.x, planar.z * inclinationSine, planar.z * inclinationCosine);
    return heart.localPosition() + inclined;
}

f64 VoidStationProfile::orbitalPeriodSeconds(const VoidHeart& heart) const {
    const f64 radius = orbitRadiusInGravitationalRadii * heart.gravitationalRadiusMeters();
    return kTwoPiDouble * std::sqrt(radius * radius * radius /
                                    (kGravitationalConstant * heart.massKilograms()));
}

VoidStationRegistry::VoidStationRegistry() {
    entries.resize(static_cast<usize>(VoidStationId::Count));

    VoidStationProfile& horizonWatch = entries[static_cast<usize>(VoidStationId::HorizonWatch)];
    horizonWatch.id = VoidStationId::HorizonWatch;
    horizonWatch.name = "HORIZON WATCH";
    horizonWatch.purpose = "Forschungsstation der Vorlaeufer, vermisst den Horizont seit 900.000 Jahren.";
    horizonWatch.architecture = "Ringfoermiger Beobachtungskranz um einen Gravitationslinsen-Spiegel.";
    horizonWatch.orbitRadiusInGravitationalRadii = 74.0;
    horizonWatch.orbitalInclinationRadians = 0.12;
    horizonWatch.orbitalPhaseRadians = 0.0;
    horizonWatch.radiusMeters = 3100.0;
    horizonWatch.puzzleStages = 4;
    horizonWatch.reward = "Blaupause: VOID DRIVE";
    horizonWatch.logbook = {
        {"Beobachterin Sael", "Der Horizont wirft unser eigenes Signal zurueck. Sechs Sekunden spaeter. Immer sechs."},
        {"Beobachterin Sael", "Wir haben aufgehoert zu senden. Es sendet trotzdem."},
        {"Technikrat Orath", "Der Antrieb funktioniert. Er faltet nicht den Raum, er faltet den Fall."}};

    VoidStationProfile& anchor = entries[static_cast<usize>(VoidStationId::TheAnchor)];
    anchor.id = VoidStationId::TheAnchor;
    anchor.name = "THE ANCHOR";
    anchor.purpose = "Ankerstation an einem stabilen Punkt, einziger sicherer Hyperraum-Ausstieg der Zone.";
    anchor.architecture = "Massiver Gegengewichts-Turm mit ausgefahrenen Traegheitsankern.";
    anchor.orbitRadiusInGravitationalRadii = 118.0;
    anchor.orbitalInclinationRadians = -0.04;
    anchor.orbitalPhaseRadians = 2.1;
    anchor.radiusMeters = 4200.0;
    anchor.puzzleStages = 3;
    anchor.reward = "Sicherer Sprungpunkt in Zone 3";
    anchor.logbook = {
        {"Ankermeister Tuun", "Wer hier ohne Anker austritt, tritt in drei Stuecken aus."},
        {"Ankermeister Tuun", "Die Verankerung haelt. Was sie festhaelt, weiss niemand mehr."}};

    VoidStationProfile& foundry = entries[static_cast<usize>(VoidStationId::NullFoundry)];
    foundry.id = VoidStationId::NullFoundry;
    foundry.name = "NULL FOUNDRY";
    foundry.purpose = "Fabrikstation, verarbeitet exotische Materie zu Void-Legierungen.";
    foundry.architecture = "Schmelzkathedrale mit offenen Giessbahnen ueber dem Akkretionsschein.";
    foundry.orbitRadiusInGravitationalRadii = 61.0;
    foundry.orbitalInclinationRadians = 0.31;
    foundry.orbitalPhaseRadians = 4.0;
    foundry.radiusMeters = 5600.0;
    foundry.puzzleStages = 5;
    foundry.reward = "Fertigung: Lensed Alloy und Singularity Core";
    foundry.logbook = {
        {"Giessmeisterin Vrahl", "Das Metall erinnert sich an die Kruemmung. Man kann es nicht gerade biegen."},
        {"Giessmeisterin Vrahl", "Schicht drei ist ausgefallen. Die Uhren dort gehen langsamer als unsere."}};

    VoidStationProfile& lastLight = entries[static_cast<usize>(VoidStationId::LastLight)];
    lastLight.id = VoidStationId::LastLight;
    lastLight.name = "LAST LIGHT";
    lastLight.purpose = "Havariertes Kolonieschiff der Vorlaeufer, erklaert ihr Verschwinden.";
    lastLight.architecture = "Kilometerlanger Generationenrumpf, halb in der Linse verzerrt.";
    lastLight.orbitRadiusInGravitationalRadii = 43.0;
    lastLight.orbitalInclinationRadians = 0.58;
    lastLight.orbitalPhaseRadians = 5.4;
    lastLight.radiusMeters = 9800.0;
    lastLight.puzzleStages = 6;
    lastLight.reward = "Archiv der Vorlaeufer, Endgame-Freischaltung";
    lastLight.logbook = {
        {"Kapitaen Ilun-Serah", "Wir sind nicht gestrandet. Wir sind angekommen."},
        {"Kapitaen Ilun-Serah", "Draussen sind vierzig Jahre vergangen. Hier drinnen elf Tage."},
        {"Kapitaen Ilun-Serah", "Sie sind alle hindurch. Ich bleibe, damit jemand die Tuer beschreibt."}};
}

bool VoidStationRegistry::markDiscovered(VoidStationId id) {
    VoidStationProfile& station = entries[static_cast<usize>(id)];
    if (station.discovered) return false;
    station.discovered = true;
    return true;
}

bool VoidStationRegistry::solveStage(VoidStationId id) {
    VoidStationProfile& station = entries[static_cast<usize>(id)];
    if (station.puzzleStagesSolved >= station.puzzleStages) return false;
    ++station.puzzleStagesSolved;
    if (station.puzzleStagesSolved >= station.puzzleStages) station.interiorCleared = true;
    return true;
}

u32 VoidStationRegistry::discoveredCount() const {
    u32 total = 0;
    for (const VoidStationProfile& station : entries) {
        if (station.discovered) ++total;
    }
    return total;
}

u32 VoidStationRegistry::clearedCount() const {
    u32 total = 0;
    for (const VoidStationProfile& station : entries) {
        if (station.interiorCleared) ++total;
    }
    return total;
}

bool VoidStationRegistry::voidDriveBlueprintUnlocked() const {
    return entries[static_cast<usize>(VoidStationId::HorizonWatch)].interiorCleared;
}

}
