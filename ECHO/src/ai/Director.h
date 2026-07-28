#pragma once

#include "../world/World.h"
#include "../world/Human.h"
#include "../game/Player.h"
#include "../audio/AudioEngine.h"

namespace echo {

struct BehaviorProfile {
    float sprintRatio = 0.0f;
    float idleRatio = 0.0f;
    float lookBackRate = 0.0f;
    float explorationRate = 0.0f;
    float darkRatio = 0.0f;
    float nervousness = 0.0f;
    float backtrackRatio = 0.0f;
    float readingRate = 0.0f;
    float avoidance = 0.0f;
    float totalTime = 0.0f;
    float distanceWalked = 0.0f;
    int roomsSeen = 0;
    int roomsRevisited = 0;
    int doorsOpened = 0;
    int doorsIgnored = 0;
    int documentsRead = 0;
    int logsHeard = 0;
    int presencesSeen = 0;
    int presencesAvoided = 0;
    int truthLayers = 0;
};

class BehaviorTracker {
public:
    void reset();
    void update(const Player& player, const World& world, float dt, float time);
    void notifyDoorOpened(int doorId);
    void notifyDoorSeen(int doorId);
    void notifyDocumentRead(int layer);
    void notifyLogHeard(int layer);
    void notifyPresenceSeen(bool lookedAt);

    const BehaviorProfile& profile() const { return data; }
    int mostVisitedRoom() const;
    int currentRoom() const { return room; }
    float timeInCurrentRoom() const { return roomTime; }
    const std::unordered_map<int, int>& roomVisits() const { return visits; }
    const std::vector<int>& ignoredDoors() const { return ignored; }
    float lookDelta() const { return recentLookDelta; }
    bool lookedBackRecently() const { return lookBackTimer > 0.0f; }
    float stillTime() const { return standStillTime; }

private:
    BehaviorProfile data;
    std::unordered_map<int, int> visits;
    std::unordered_map<int, float> doorSeenTime;
    std::vector<int> ignored;
    std::vector<char> doorOpened;
    int room = -1;
    int previousRoom = -1;
    float roomTime = 0.0f;
    float sprintTime = 0.0f;
    float idleTime = 0.0f;
    float darkTime = 0.0f;
    float standStillTime = 0.0f;
    float lastYaw = 0.0f;
    float yawAccum = 0.0f;
    float lookBackTimer = 0.0f;
    float recentLookDelta = 0.0f;
    float turnRateAvg = 0.0f;
    em::Vec3 lastPos;
    std::vector<int> recentRooms;
};

enum ScareId {
    SCARE_DOOR_NURSE = 0,
    SCARE_CORRIDOR_PATIENT,
    SCARE_MIRROR_FIGURE,
    SCARE_WHEELCHAIR,
    SCARE_ELEVATOR_DOCTOR,
    SCARE_PA_FIGURE,
    SCARE_KEY_TURNAROUND,
    SCARE_FOOTSTEPS_BED,
    SCARE_COUNT
};

struct ScareState {
    bool used = false;
    bool armed = false;
    int stage = 0;
    float timer = 0.0f;
    float cooldown = 0.0f;
    int targetRoom = -1;
    int targetDoor = -1;
    int targetProp = -1;
    em::Vec3 anchor;
};

struct DirectorEvent {
    int kind = 0;
    em::Vec3 position;
    float value = 0.0f;
    int id = -1;
};

class Director {
public:
    void init(World* world, AudioEngine* audio, HumanRig* rig, u64 seed);
    void reset();
    void update(Player& player, float dt, float time);
    void submitPresences(Renderer& renderer);

    BehaviorTracker& tracker() { return behavior; }
    const BehaviorTracker& tracker() const { return behavior; }

    float tension() const { return tensionValue; }
    float dread() const { return dreadValue; }
    float sanity() const { return sanityValue; }
    float distortion() const { return distortionValue; }
    float ambientBoost() const { return ambientMod; }

    bool consumeSubtitle(std::string& text, float& duration);
    void queueSubtitle(const std::string& text, float duration);
    void notifyInteract(int kind, int targetId, const em::Vec3& pos);
    void notifyDocumentRead(int layer);
    void notifyLogHeard(int layer);

    int chooseEnding() const;
    int activeScare() const { return currentScare; }
    bool presenceVisible() const;

    float flashlightDisturb = 0.0f;
    float cameraShake = 0.0f;
    float forcedLookStrength = 0.0f;
    em::Vec3 forcedLookTarget;

private:
    void updateTension(const Player& player, float dt);
    void updateAmbientEvents(const Player& player, float dt, float time);
    void updateMutations(const Player& player, float dt, float time);
    void updateScares(Player& player, float dt, float time);
    void spawnPresence(const em::Vec3& pos, float faceYaw, int type, int pose);
    void despawnPresence(bool fade);
    bool playerLooksAt(const Player& player, const em::Vec3& pos, float cosLimit) const;
    bool inPlayerView(const Player& player, const em::Vec3& pos) const;
    bool roomOffScreen(const Player& player, int roomId) const;
    void mutateRoom(int roomId, float strength);
    void playCue(int sound, const em::Vec3& pos, float volume, float pitch);

    World* world = nullptr;
    AudioEngine* audio = nullptr;
    HumanRig* rig = nullptr;
    BehaviorTracker behavior;
    em::Rng rng;

    HumanInstance presence;
    float presenceTimer = 0.0f;
    float presenceFade = 0.0f;
    bool presenceActive = false;
    bool presenceSeen = false;

    ScareState scares[SCARE_COUNT];
    int currentScare = -1;
    float scareCooldown = 90.0f;

    float tensionValue = 0.0f;
    float dreadValue = 0.0f;
    float sanityValue = 1.0f;
    float distortionValue = 0.0f;
    float ambientMod = 0.0f;

    float ambientTimer = 0.0f;
    float mutationTimer = 0.0f;
    float whisperTimer = 0.0f;
    float paTimer = 0.0f;
    float heartbeatTarget = 0.0f;

    std::vector<std::pair<std::string, float>> subtitles;
    std::vector<int> mutatedRooms;
    SoundHandle ambienceHandle;
    SoundHandle droneHandle;
};

}
