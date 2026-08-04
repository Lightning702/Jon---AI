#include "EndgameCampaign.hpp"

namespace sf {

bool EndgameMission::allObjectivesComplete() const {
    for (const EndgameObjective& objective : objectives) {
        if (!objective.completed) return false;
    }
    return !objectives.empty();
}

f32 EndgameMission::progressFraction() const {
    if (objectives.empty()) return 0.0f;
    u32 done = 0;
    for (const EndgameObjective& objective : objectives) {
        if (objective.completed) ++done;
    }
    return static_cast<f32>(done) / static_cast<f32>(objectives.size());
}

EndgameCampaign::EndgameCampaign() {
    entries.resize(static_cast<usize>(EndgameMissionId::Count));

    EndgameMission& signal = entries[static_cast<usize>(EndgameMissionId::TheSignal)];
    signal.id = EndgameMissionId::TheSignal;
    signal.title = "DAS SIGNAL";
    signal.briefing = "Ein Pulsar sendet eine Sequenz, die kein Pulsar senden kann. Finde die Quelle.";
    signal.debriefing = "Die Sequenz kommt nicht vom Pulsar. Sie wird an ihm gebrochen. Der Ursprung liegt im Zentrum.";
    signal.objectives = {{"Pulsarsignal dreimal aus unterschiedlichen Systemen peilen"},
                         {"Signalkegel triangulieren"},
                         {"Zielkoordinate im Galaxiezentrum bestaetigen"}};

    EndgameMission& approach = entries[static_cast<usize>(EndgameMissionId::Approach)];
    approach.id = EndgameMissionId::Approach;
    approach.title = "ANNAEHERUNG";
    approach.briefing = "Baue den Void-Antrieb aus den Blaupausen von HORIZON WATCH und erreiche Zone 3.";
    approach.debriefing = "Der Antrieb haelt. Die Instrumente nicht. Ab hier zaehlt nur, was du selbst siehst.";
    approach.objectives = {{"HORIZON WATCH finden und betreten"},
                           {"Blaupause des Void-Antriebs bergen"},
                           {"Void-Antrieb fertigen"},
                           {"Verzerrungszone erreichen und stabil halten"}};

    EndgameMission& clock = entries[static_cast<usize>(EndgameMissionId::TheClockRuns)];
    clock.id = EndgameMissionId::TheClockRuns;
    clock.title = "DIE UHR LAEUFT";
    clock.briefing = "Ein Frachter treibt in die Ergosphaere. Fuer die Besatzung sind es Minuten, fuer dich Stunden.";
    clock.debriefing = "Sie waren neunzehn Minuten alleine. Draussen waren es elf Tage.";
    clock.objectives = {{"Frachter im Frame-Dragging-Strom abfangen"},
                        {"Vier Rettungskapseln bergen"},
                        {"Vor Erreichen der Horizontnaehe ausbrechen"}};

    EndgameMission& archive = entries[static_cast<usize>(EndgameMissionId::TheArchive)];
    archive.id = EndgameMissionId::TheArchive;
    archive.title = "DAS ARCHIV";
    archive.briefing = "LAST LIGHT traegt die Logbuecher der Vorlaeufer. Berge sie, bevor der Rumpf reisst.";
    archive.debriefing = "Sie sind nicht ausgestorben. Sie sind gegangen. Freiwillig.";
    archive.objectives = {{"LAST LIGHT anfliegen und andocken"},
                          {"Sechs Archivkerne bergen"},
                          {"Kapitaensbruecke erreichen"},
                          {"Das letzte Logbuch abspielen"}};

    EndgameMission& ring = entries[static_cast<usize>(EndgameMissionId::TheRing)];
    ring.id = EndgameMissionId::TheRing;
    ring.title = "DER RING";
    ring.briefing = "Ein Fraktionsverband greift NULL FOUNDRY an. Der Kampf findet in der Ergosphaere statt.";
    ring.debriefing = "Die Giessbahnen laufen wieder. Der Verband nicht.";
    ring.objectives = {{"NULL FOUNDRY erreichen"},
                       {"Drei Angriffswellen abwehren"},
                       {"Das Flaggschiff in die Rotationsrichtung draengen"},
                       {"Giessbahn drei wieder anfahren"}};

    EndgameMission& beyond = entries[static_cast<usize>(EndgameMissionId::BeyondTheVoid)];
    beyond.id = EndgameMissionId::BeyondTheVoid;
    beyond.title = "BEYOND THE VOID";
    beyond.briefing = "Der Horizont ist keine Wand. Er ist eine Tuer. Durchquere ihn.";
    beyond.debriefing = "Auf der anderen Seite steht dein eigenes Signal und wartet seit neunhunderttausend Jahren.";
    beyond.objectives = {{"Alle vier Void-Stationen abschliessen"},
                         {"Void-Antrieb auf Stufe 5 bringen"},
                         {"Anflugvektor exakt auf die Spinachse legen"},
                         {"Ereignishorizont durchqueren"}};
}

void EndgameCampaign::evaluateUnlocks(u32 researchTier, u32 recognizedCivilizations,
                                      const VoidStationRegistry& stations) {
    const bool baseRequirement = researchTier >= 5 && recognizedCivilizations >= 2;
    if (!baseRequirement) return;

    EndgameMission& signal = entries[static_cast<usize>(EndgameMissionId::TheSignal)];
    if (signal.state == MissionState::Locked) signal.state = MissionState::Available;

    for (usize index = 1; index < entries.size(); ++index) {
        EndgameMission& mission = entries[index];
        if (mission.state != MissionState::Locked) continue;
        if (entries[index - 1].state != MissionState::Completed) continue;
        if (mission.id == EndgameMissionId::BeyondTheVoid && stations.clearedCount() < 4) continue;
        if (mission.id == EndgameMissionId::TheArchive &&
            !stations.station(VoidStationId::LastLight).discovered) {
            continue;
        }
        mission.state = MissionState::Available;
    }
}

bool EndgameCampaign::startMission(EndgameMissionId id) {
    EndgameMission& mission = entries[static_cast<usize>(id)];
    if (mission.state != MissionState::Available) return false;
    mission.state = MissionState::Active;
    return true;
}

bool EndgameCampaign::completeObjective(EndgameMissionId id, usize objectiveIndex) {
    EndgameMission& mission = entries[static_cast<usize>(id)];
    if (mission.state != MissionState::Active) return false;
    if (objectiveIndex >= mission.objectives.size()) return false;
    if (mission.objectives[objectiveIndex].completed) return false;
    mission.objectives[objectiveIndex].completed = true;
    if (mission.allObjectivesComplete()) completeMission(id);
    return true;
}

bool EndgameCampaign::completeMission(EndgameMissionId id) {
    EndgameMission& mission = entries[static_cast<usize>(id)];
    if (mission.state == MissionState::Completed) return false;
    for (EndgameObjective& objective : mission.objectives) objective.completed = true;
    mission.state = MissionState::Completed;
    if (id == EndgameMissionId::BeyondTheVoid) newGamePlus = true;
    return true;
}

u32 EndgameCampaign::completedCount() const {
    u32 total = 0;
    for (const EndgameMission& mission : entries) {
        if (mission.state == MissionState::Completed) ++total;
    }
    return total;
}

bool EndgameCampaign::newGamePlusUnlocked() const {
    return newGamePlus;
}

const EndgameMission* EndgameCampaign::activeMission() const {
    for (const EndgameMission& mission : entries) {
        if (mission.state == MissionState::Active) return &mission;
    }
    return nullptr;
}

}
