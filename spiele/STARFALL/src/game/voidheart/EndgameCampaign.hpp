#pragma once

#include "ExoticResource.hpp"
#include "VoidStation.hpp"

namespace sf {

enum class EndgameMissionId : u32 {
    TheSignal = 0,
    Approach,
    TheClockRuns,
    TheArchive,
    TheRing,
    BeyondTheVoid,
    Count
};

enum class MissionState : u32 {
    Locked = 0,
    Available,
    Active,
    Completed
};

struct EndgameObjective {
    std::string description;
    bool completed = false;
};

struct EndgameMission {
    EndgameMissionId id = EndgameMissionId::TheSignal;
    std::string title;
    std::string briefing;
    std::string debriefing;
    MissionState state = MissionState::Locked;
    u32 maximumPlayers = 4;
    u32 requiredResearchTier = 5;
    u32 requiredRecognizedCivilizations = 2;
    std::vector<EndgameObjective> objectives;

    bool allObjectivesComplete() const;
    f32 progressFraction() const;
};

class EndgameCampaign {
public:
    EndgameCampaign();

    void evaluateUnlocks(u32 researchTier, u32 recognizedCivilizations, const VoidStationRegistry& stations);
    bool startMission(EndgameMissionId id);
    bool completeObjective(EndgameMissionId id, usize objectiveIndex);
    bool completeMission(EndgameMissionId id);

    const std::vector<EndgameMission>& missions() const { return entries; }
    const EndgameMission& mission(EndgameMissionId id) const { return entries[static_cast<usize>(id)]; }
    u32 completedCount() const;
    bool newGamePlusUnlocked() const;
    const EndgameMission* activeMission() const;

private:
    std::vector<EndgameMission> entries;
    bool newGamePlus = false;
};

}
