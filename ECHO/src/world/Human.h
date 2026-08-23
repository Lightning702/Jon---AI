#pragma once

#include "../render/Mesh.h"
#include "../render/Material.h"
#include "../render/Renderer.h"
#include "../core/Random.h"

namespace echo {

enum HumanType {
    HUMAN_DOCTOR = 0,
    HUMAN_NURSE,
    HUMAN_PATIENT,
    HUMAN_CLEANER,
    HUMAN_SECURITY,
    HUMAN_TYPE_COUNT
};

enum HumanPose {
    POSE_STAND_STILL = 0,
    POSE_IDLE,
    POSE_SLOW_WALK,
    POSE_TURN_AWAY,
    POSE_FACE_WALL,
    POSE_SIT,
    POSE_LEAN,
    POSE_LOOK_UP,
    POSE_COUNT
};

enum BodyPart {
    PART_PELVIS = 0,
    PART_ABDOMEN,
    PART_CHEST,
    PART_NECK,
    PART_HEAD,
    PART_HAIR,
    PART_UPPER_ARM_L, PART_FOREARM_L, PART_HAND_L,
    PART_UPPER_ARM_R, PART_FOREARM_R, PART_HAND_R,
    PART_THIGH_L, PART_SHIN_L, PART_FOOT_L,
    PART_THIGH_R, PART_SHIN_R, PART_FOOT_R,
    PART_COUNT
};

struct HumanAppearance {
    int type = HUMAN_DOCTOR;
    em::Vec3 skinTint = em::Vec3(1, 1, 1);
    em::Vec3 clothTint = em::Vec3(1, 1, 1);
    em::Vec3 hairTint = em::Vec3(1, 1, 1);
    int clothMaterial = MAT_CLOTH_WHITE;
    float height = 1.0f;
    float build = 1.0f;
    bool hasHair = true;
    bool female = false;
};

class HumanRig {
public:
    void build();
    void destroy();
    const Mesh& part(int index) const { return parts[index < 0 || index >= PART_COUNT ? 0 : index]; }
    const em::AABB& partBounds(int index) const { return bounds[index < 0 || index >= PART_COUNT ? 0 : index]; }

private:
    Mesh parts[PART_COUNT];
    em::AABB bounds[PART_COUNT];
};

class HumanInstance {
public:
    void configure(int type, u64 seed);
    void setPose(int pose, float blendTime = 0.8f);
    void update(float dt, float time, const em::Vec3& lookTarget, bool hasLookTarget);
    void setLook(float yawOffset, float pitch);
    void clearLook();
    void submit(Renderer& renderer, const HumanRig& rig) const;

    em::Vec3 position;
    float yaw = 0.0f;
    float visibility = 1.0f;
    bool active = false;

    int pose() const { return currentPose; }
    const HumanAppearance& appearance() const { return look; }
    em::AABB worldBounds() const;
    em::Vec3 headPosition() const;
    float animationPhase() const { return phase; }
    void snapPose() { poseBlend = 1.0f; }

    float walkSpeed = 0.62f;
    float breathAmount = 1.0f;

private:
    void computePose(float t);

    HumanAppearance look;
    em::Mat4 partTransforms[PART_COUNT];
    int currentPose = POSE_STAND_STILL;
    int previousPose = POSE_STAND_STILL;
    float poseBlend = 1.0f;
    float blendSpeed = 1.25f;
    float phase = 0.0f;
    float breathPhase = 0.0f;
    float headYaw = 0.0f, headPitch = 0.0f;
    float targetHeadYaw = 0.0f, targetHeadPitch = 0.0f;
    bool lookForced = false;
    float swayPhase = 0.0f;
    float idleTimer = 0.0f;
    u64 seedValue = 0;
};

}
