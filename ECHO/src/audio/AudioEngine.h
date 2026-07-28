#pragma once

#include "AudioDevice.h"
#include "Synth.h"
#include <mutex>
#include <atomic>

namespace echo {

struct SoundHandle {
    int index = -1;
    u32 generation = 0;
    bool valid() const { return index >= 0; }
};

struct PlayParams {
    em::Vec3 position;
    float volume = 1.0f;
    float pitch = 1.0f;
    float minDistance = 1.2f;
    float maxDistance = 26.0f;
    bool looping = false;
    bool spatial = true;
    float reverbSend = 0.35f;
    float lowpass = 0.0f;
    float fadeIn = 0.0f;
};

class AudioEngine {
public:
    bool init();
    void shutdown();

    void setListener(const em::Vec3& position, const em::Vec3& forward, const em::Vec3& up, const em::Vec3& velocity);
    void update(float dt);

    SoundHandle play(int soundId, const PlayParams& params);
    SoundHandle playAt(int soundId, const em::Vec3& pos, float volume = 1.0f, float pitch = 1.0f);
    SoundHandle play2D(int soundId, float volume = 1.0f, float pitch = 1.0f);
    void stop(SoundHandle h, float fadeOut = 0.05f);
    void stopAll();
    void setPosition(SoundHandle h, const em::Vec3& p);
    void setVolume(SoundHandle h, float v);
    void setPitch(SoundHandle h, float v);
    void setLowpass(SoundHandle h, float v);
    bool isPlaying(SoundHandle h) const;

    void setMasterVolume(float v) { masterVolume = em::clampf(v, 0.0f, 1.0f); }
    float masterVolume_() const { return masterVolume; }
    void setReverb(float roomSize, float damping, float wet);
    void setDucking(float amount) { ducking = em::clampf(amount, 0.0f, 1.0f); }
    void setHeartbeatRate(float bpm) { heartbeatBpm = bpm; }
    void setTension(float t) { tension = em::clampf(t, 0.0f, 1.0f); }

    const SoundBank& bank() const { return sounds; }
    int sampleRate() const { return device.sampleRate(); }
    bool available() const { return device.running(); }

private:
    struct Voice {
        int sound = -1;
        u32 generation = 0;
        bool active = false;
        bool looping = false;
        bool spatial = true;
        double cursor = 0.0;
        float volume = 1.0f;
        float pitch = 1.0f;
        float minDistance = 1.2f;
        float maxDistance = 26.0f;
        float reverbSend = 0.3f;
        float lowpass = 0.0f;
        float fadeTarget = 1.0f;
        float fadeCurrent = 1.0f;
        float fadeSpeed = 8.0f;
        em::Vec3 position;
        float gainL = 0.5f, gainR = 0.5f;
        float smoothL = 0.0f, smoothR = 0.0f;
        float lpStateL = 0.0f, lpStateR = 0.0f;
        bool stopping = false;
    };

    struct Comb {
        std::vector<float> buffer;
        int index = 0;
        float feedback = 0.84f;
        float damp = 0.2f;
        float store = 0.0f;
        void resize(int n) { buffer.assign((size_t)std::max(n, 1), 0.0f); index = 0; store = 0.0f; }
        float process(float input) {
            if (buffer.empty()) return 0.0f;
            float out = buffer[(size_t)index];
            store = out * (1.0f - damp) + store * damp;
            buffer[(size_t)index] = input + store * feedback;
            if (++index >= (int)buffer.size()) index = 0;
            return out;
        }
    };

    struct Allpass {
        std::vector<float> buffer;
        int index = 0;
        float feedback = 0.5f;
        void resize(int n) { buffer.assign((size_t)std::max(n, 1), 0.0f); index = 0; }
        float process(float input) {
            if (buffer.empty()) return input;
            float buf = buffer[(size_t)index];
            float out = -input + buf;
            buffer[(size_t)index] = input + buf * feedback;
            if (++index >= (int)buffer.size()) index = 0;
            return out;
        }
    };

    void renderAudio(float* output, int frames, int channels);
    void computePanning(Voice& v);
    Voice* resolve(SoundHandle h);
    const Voice* resolve(SoundHandle h) const;

    static const int kMaxVoices = 64;

    AudioDevice device;
    SoundBank sounds;
    Voice voices[kMaxVoices];
    mutable std::mutex lock;
    u32 nextGeneration = 1;

    em::Vec3 listenerPos, listenerFwd = em::Vec3(0, 0, -1), listenerUp = em::Vec3(0, 1, 0), listenerRight = em::Vec3(1, 0, 0);
    std::atomic<float> masterVolume{ 0.85f };
    std::atomic<float> ducking{ 0.0f };
    std::atomic<float> tension{ 0.0f };
    std::atomic<float> heartbeatBpm{ 0.0f };
    std::atomic<bool> ready{ false };

    Comb combsL[8], combsR[8];
    Allpass apsL[4], apsR[4];
    float reverbWet = 0.28f;
    float reverbFeedback = 0.84f;
    float reverbDamp = 0.28f;
    float heartbeatPhase = 0.0f;
};

}
