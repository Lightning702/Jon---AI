#pragma once

#include "../core/Math.h"
#include "../core/Random.h"

namespace aeth {

class AetheriaWorld;

enum QuestKind {
    QUEST_GATHER = 0,
    QUEST_HUNT,
    QUEST_TRAVEL,
    QUEST_LANDMARK,
    QUEST_KIND_COUNT
};

enum QuestState {
    QUEST_HIDDEN = 0,
    QUEST_OFFERED,
    QUEST_ACTIVE,
    QUEST_READY,
    QUEST_DONE
};

struct Quest {
    int id = 0;
    int kind = QUEST_GATHER;
    int village = 0;
    int chain = -1;
    int target = 0;
    int needed = 1;
    int progress = 0;
    int state = QUEST_HIDDEN;
    int xp = 60;
    int gold = 20;
    bool tracked = false;
    em::Vec3 marker;
    float markerRadius = 10.0f;
    std::string title;
    std::string task;
    std::string offer;
    std::string thanks;
    std::string giver;
    std::string place;
};

class QuestLog {
public:
    void build(const AetheriaWorld& world, u64 seed);
    void clear();

    int count() const { return (int)quests.size(); }
    Quest& at(int i) { return quests[(size_t)i]; }
    const Quest& at(int i) const { return quests[(size_t)i]; }
    const std::vector<Quest>& all() const { return quests; }

    void revealVillage(int village);
    int offeredFor(int village) const;
    int readyFor(int village) const;
    int activeCount() const;
    int completedCount() const { return completed; }

    void accept(int index);
    bool complete(int index);

    bool reportGather(int floraType);
    bool reportHunt(int species);
    int checkPositions(const em::Vec3& player);

    int trackedIndex() const { return tracked; }
    void setTracked(int index) { tracked = index; }
    void cycleTracked();

    std::vector<std::string> journalLines() const;

private:
    void advanceChain();

    std::vector<Quest> quests;
    int tracked = -1;
    int completed = 0;
    int chainStage = 0;
};

}
