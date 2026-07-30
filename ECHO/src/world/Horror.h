#pragma once

#include "../render/Mesh.h"
#include "../render/Material.h"
#include "../render/Renderer.h"
#include "../core/Random.h"

namespace echo {

enum HorrorKind {
    HORROR_GAUNT = 0,
    HORROR_CRAWLER,
    HORROR_BANDAGED,
    HORROR_LONGARM,
    HORROR_KIND_COUNT
};

enum HorrorMode {
    HMODE_STARE = 0,
    HMODE_TWITCH,
    HMODE_LUNGE,
    HMODE_CRAWL,
    HMODE_SCREAM,
    HMODE_HANG
};

enum HorrorPart {
    HPART_PELVIS = 0,
    HPART_SPINE,
    HPART_RIBS,
    HPART_NECK,
    HPART_SKULL,
    HPART_JAW,
    HPART_ARM_L, HPART_FORE_L, HPART_CLAW_L,
    HPART_ARM_R, HPART_FORE_R, HPART_CLAW_R,
    HPART_THIGH_L, HPART_SHIN_L, HPART_FOOT_L,
    HPART_THIGH_R, HPART_SHIN_R, HPART_FOOT_R,
    HPART_HAIR,
    HPART_COUNT
};

struct HorrorLook {
    int kind = HORROR_GAUNT;
    em::Vec3 fleshTint = em::Vec3(0.78f, 0.74f, 0.72f);
    em::Vec3 darkTint = em::Vec3(0.10f, 0.08f, 0.09f);
    float height = 1.0f;
    float gaunt = 1.0f;
    float armStretch = 1.0f;
    float neckStretch = 1.0f;
    float jawDrop = 1.0f;
    bool hasHair = true;
};

class HorrorRig {
public:
    void build();
    void destroy();
    bool ready() const { return built; }
    const Mesh& part(int index) const { return parts[index < 0 || index >= HPART_COUNT ? 0 : index]; }

private:
    Mesh parts[HPART_COUNT];
    bool built = false;
};

class HorrorInstance {
public:
    void configure(int kind, u64 seed);
    void setMode(int mode);
    void update(float dt, float time, const em::Vec3& target);
    void submit(Renderer& renderer, const HorrorRig& rig) const;

    em::Vec3 position;
    float yaw = 0.0f;
    float visibility = 1.0f;
    float scale = 1.0f;
    bool active = false;

    int mode() const { return currentMode; }
    const HorrorLook& look() const { return appearance; }
    em::Vec3 headPosition() const;
    float lungeAmount() const { return lunge; }
    void faceTowards(const em::Vec3& p);

private:
    void computePose(float time);

    HorrorLook appearance;
    em::Mat4 partTransforms[HPART_COUNT];
    int currentMode = HMODE_STARE;
    float modeTime = 0.0f;
    float phase = 0.0f;
    float twitch = 0.0f;
    float twitchTimer = 0.0f;
    float lunge = 0.0f;
    float headYaw = 0.0f;
    float headPitch = 0.0f;
    float jawOpen = 0.0f;
    float breathe = 0.0f;
    u64 seedValue = 0;
};

}
