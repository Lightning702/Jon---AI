#pragma once

#include "../core/Math.h"
#include "../core/Random.h"

namespace echo {

enum SoundId {
    SFX_STEP_TILE = 0,
    SFX_STEP_CONCRETE,
    SFX_STEP_LINO,
    SFX_STEP_METAL,
    SFX_STEP_WATER,
    SFX_STEP_DEBRIS,
    SFX_DOOR_OPEN,
    SFX_DOOR_CLOSE,
    SFX_DOOR_CREAK,
    SFX_DOOR_LOCKED,
    SFX_DOOR_SLAM,
    SFX_DRAWER,
    SFX_SWITCH,
    SFX_PICKUP,
    SFX_PAPER,
    SFX_GLASS_BREAK,
    SFX_LIGHT_BUZZ,
    SFX_LIGHT_POP,
    SFX_DISTANT_STEPS,
    SFX_DISTANT_DOOR,
    SFX_WHISPER,
    SFX_VOICE_FAR,
    SFX_SCRATCH,
    SFX_METAL_DRAG,
    SFX_DRIP,
    SFX_VENT_HUM,
    SFX_WIND,
    SFX_PIPE_KNOCK,
    SFX_ELEVATOR_HUM,
    SFX_ELEVATOR_DING,
    SFX_PA_STATIC,
    SFX_HEARTBEAT,
    SFX_BREATH,
    SFX_WHEELCHAIR,
    SFX_BED_ROLL,
    SFX_STING_LOW,
    SFX_STING_HIGH,
    SFX_DRONE,
    SFX_TAPE_HISS,
    SFX_CLICK,
    SFX_MUSIC_LOBBY,
    SFX_SCREAM,
    SFX_SCREECH,
    SFX_SLAM_HIT,
    SFX_BREATH_CLOSE,
    SFX_BONE_CRACK,
    SFX_COUNT
};

struct SoundClip {
    std::vector<float> samples;
    int sampleRate = 48000;
    bool looping = false;
    float baseGain = 1.0f;

    float duration() const { return sampleRate > 0 ? (float)samples.size() / sampleRate : 0.0f; }
};

class SoundBank {
public:
    void generate(int sampleRate);
    void destroy();
    const SoundClip& get(int id) const { return clips[id < 0 || id >= SFX_COUNT ? 0 : id]; }
    int variantCount(int id) const;

private:
    SoundClip clips[SFX_COUNT];
};

}
