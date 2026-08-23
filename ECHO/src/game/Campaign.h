#pragma once

#include "../world/World.h"
#include "Player.h"

namespace echo {

enum CampaignStep {
    STEP_INTRO = 0,
    STEP_GOTO_PICKUP,
    STEP_TAKE_BODY,
    STEP_GOTO_MORGUE,
    STEP_DELIVER,
    STEP_TRANSITION,
    STEP_FINALE,
    STEP_DONE
};

struct CutShot {
    em::Vec3 camFrom;
    em::Vec3 camTo;
    em::Vec3 lookFrom;
    em::Vec3 lookTo;
    float duration = 4.0f;
    float fov = 1.05f;
    std::string line;
};

class CutscenePlayer {
public:
    void play(const std::vector<CutShot>& shots);
    void stop();
    bool update(float dt);
    bool active() const { return running; }
    CameraData camera(float aspect) const;
    std::string currentLine() const;
    float fade() const;
    float progress() const;

private:
    std::vector<CutShot> list;
    int index = 0;
    float timer = 0.0f;
    float total = 0.0f;
    float elapsed = 0.0f;
    bool running = false;
};

struct TransportRun {
    int pickupRoom = -1;
    int gurneyProp = -1;
    int pickupInteract = -1;
    int bodyProp = -1;
    bool bodyMissing = false;
};

class Campaign {
public:
    void init(World* world, u64 seed);
    void reset();
    void update(Player& player, float dt, float time);

    const std::string& objective() const { return objectiveText; }
    const std::string& chapterName() const { return chapterText; }
    bool hasMarker() const { return markerValid; }
    em::Vec3 marker() const { return markerPos; }
    float markerDistance(const em::Vec3& from) const;

    bool hasGuide() const { return guideValid; }
    em::Vec3 guide() const { return guidePos; }
    const std::string& guideHint() const { return guideText; }
    int targetFloor() const { return targetFloorIndex; }
    int playerFloor() const { return playerFloorIndex; }
    bool guideIsStairs() const { return guideStairs; }
    void onFloorReached(int floor);

    bool carryingBody() const { return carrying; }
    int runIndex() const { return currentRun; }
    int runCount() const { return (int)runs.size(); }
    int step() const { return currentStep; }
    bool finished() const { return currentStep == STEP_DONE; }

    bool onInteract(int kind, int targetId, const em::Vec3& pos);
    bool consumeCutscene(std::vector<CutShot>& out);
    bool consumeMessage(std::string& text, float& duration);
    bool consumeEvent(int& eventId);

    void serialize(std::vector<u8>& out) const;
    void deserialize(const u8* data, size_t size);

private:
    void buildRuns(em::Rng& rng);
    void enterStep(int step);
    void startRun(int index);
    void queueCutscene(const std::vector<CutShot>& shots);
    void queueMessage(const std::string& text, float duration);
    void refreshObjective();
    em::Vec3 roomAnchor(int roomId) const;

    World* world = nullptr;
    std::vector<TransportRun> runs;
    std::vector<CutShot> pendingCutscene;
    std::vector<std::pair<std::string, float>> messages;
    std::vector<int> events;

    int morgueRoom = -1;
    int morgueInteract = -1;
    int lockerRoom = -1;
    int currentRun = 0;
    int currentStep = STEP_INTRO;
    bool carrying = false;
    bool cutsceneReady = false;
    float stepTimer = 0.0f;

    std::string objectiveText;
    std::string chapterText;
    em::Vec3 markerPos;
    bool markerValid = false;
    em::Vec3 guidePos;
    bool guideValid = false;
    bool guideStairs = false;
    std::string guideText;
    int targetFloorIndex = -1;
    int playerFloorIndex = -1;
    float guideTimer = 0.0f;
    void updateGuidance(const em::Vec3& playerPos, float dt);
    em::Rng rng;
};

}
