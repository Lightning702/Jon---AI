#pragma once

#include "../world/World.h"
#include "../world/Horror.h"
#include "../game/Player.h"
#include "../audio/AudioEngine.h"

namespace echo {

enum ScareTrigger {
    TRIG_RUSH_AHEAD = 0,
    TRIG_BEHIND_TURN,
    TRIG_DOOR_BURST,
    TRIG_CEILING_DROP,
    TRIG_FLOOR_CRAWL,
    TRIG_WALL_PEEK,
    TRIG_COUNT
};

enum ScarePhase {
    SPHASE_IDLE = 0,
    SPHASE_ARMED,
    SPHASE_HIT,
    SPHASE_HOLD,
    SPHASE_FADE
};

class JumpscareDirector {
public:
    void init(World* world, AudioEngine* audio, HorrorRig* rig, u64 seed);
    void reset();
    void update(Player& player, float dt, float time, float intensityScale);
    void submit(Renderer& renderer);

    bool active() const { return phase != SPHASE_IDLE && phase != SPHASE_ARMED; }
    bool entityVisible() const { return entity.active && entity.visibility > 0.02f; }
    int corridorsScared() const { return (int)done.size(); }
    int trigger() const { return currentTrigger; }
    float impact() const { return impactPulse; }
    bool consumeSubtitle(std::string& text, float& duration);

    float cameraShake = 0.0f;
    float flashlightKill = 0.0f;
    float forcedLookStrength = 0.0f;
    em::Vec3 forcedLookTarget;
    float bloodFlash = 0.0f;
    float deafen = 0.0f;

private:
    bool alreadyScared(int room) const;
    bool pickSetup(const Player& player, int room, float time);
    bool spawnAhead(const Player& player, const Room& room);
    bool spawnBehind(const Player& player, const Room& room);
    bool spawnDoor(const Player& player, const Room& room);
    bool spawnCeiling(const Player& player, const Room& room);
    bool spawnCrawl(const Player& player, const Room& room);
    bool spawnPeek(const Player& player, const Room& room);
    void arm(int trigger, const em::Vec3& pos, float faceYaw, int mode);
    void detonate(Player& player, float time);
    void killLights(int room, bool restore);
    void finish();
    bool looksAt(const Player& player, const em::Vec3& p, float cosLimit) const;
    float corridorLength(const Room& room) const;
    em::Vec3 corridorAxis(const Room& room) const;
    em::Vec3 floorPoint(const Room& room, const em::Vec3& p) const;

    World* world = nullptr;
    AudioEngine* audio = nullptr;
    HorrorRig* rig = nullptr;
    em::Rng rng;

    HorrorInstance entity;
    std::vector<int> done;
    std::vector<int> darkenedLights;
    std::vector<std::pair<std::string, float>> subtitles;

    int phase = SPHASE_IDLE;
    int currentTrigger = -1;
    int currentRoom = -1;
    int armedRoom = -1;
    int burstDoor = -1;
    float phaseTime = 0.0f;
    float armTime = 0.0f;
    float roomTime = 0.0f;
    float cooldown = 0.0f;
    float impactPulse = 0.0f;
    float lastYaw = 0.0f;
    float travelled = 0.0f;
    em::Vec3 lastPos;
    em::Vec3 anchor;
    em::Vec3 rushTarget;
    bool lightsKilled = false;
    bool restored = false;
    bool seeded = false;
};

}
