#include "AudioEngine.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

namespace {

const int kCombTuning[8] = { 1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617 };
const int kAllpassTuning[4] = { 556, 441, 341, 225 };
const int kStereoSpread = 23;

}

bool AudioEngine::init() {
    if (!device.start([this](float* out, int frames, int channels) { renderAudio(out, frames, channels); })) {
        LOG_WARN("Audio device unavailable, running silent");
        return false;
    }

    int sr = device.sampleRate();
    sounds.generate(sr);

    float scale = sr / 44100.0f;
    for (int i = 0; i < 8; i++) {
        combsL[i].resize((int)(kCombTuning[i] * scale));
        combsR[i].resize((int)((kCombTuning[i] + kStereoSpread) * scale));
        combsL[i].feedback = combsR[i].feedback = reverbFeedback;
        combsL[i].damp = combsR[i].damp = reverbDamp;
    }
    for (int i = 0; i < 4; i++) {
        apsL[i].resize((int)(kAllpassTuning[i] * scale));
        apsR[i].resize((int)((kAllpassTuning[i] + kStereoSpread) * scale));
    }

    ready.store(true);
    return true;
}

void AudioEngine::shutdown() {
    ready.store(false);
    stopAll();
    device.stop();
    sounds.destroy();
}

void AudioEngine::setListener(const Vec3& position, const Vec3& forward, const Vec3& up, const Vec3& velocity) {
    std::lock_guard<std::mutex> g(lock);
    listenerPos = position;
    listenerFwd = normalize(forward);
    listenerUp = normalize(up);
    listenerRight = normalize(cross(listenerFwd, listenerUp));
    for (int i = 0; i < kMaxVoices; i++) {
        if (voices[i].active && voices[i].spatial) computePanning(voices[i]);
    }
}

void AudioEngine::setReverb(float roomSize, float damping, float wet) {
    std::lock_guard<std::mutex> g(lock);
    reverbFeedback = clampf(0.68f + roomSize * 0.27f, 0.5f, 0.96f);
    reverbDamp = clampf(damping, 0.0f, 0.95f);
    reverbWet = clampf(wet, 0.0f, 1.0f);
    for (int i = 0; i < 8; i++) {
        combsL[i].feedback = combsR[i].feedback = reverbFeedback;
        combsL[i].damp = combsR[i].damp = reverbDamp;
    }
}

void AudioEngine::computePanning(Voice& v) {
    if (!v.spatial) {
        v.gainL = v.gainR = 0.707f;
        return;
    }
    Vec3 d = v.position - listenerPos;
    float dist = length(d);
    float atten;
    if (dist <= v.minDistance) atten = 1.0f;
    else if (dist >= v.maxDistance) atten = 0.0f;
    else {
        float t = (dist - v.minDistance) / (v.maxDistance - v.minDistance);
        atten = 1.0f - t;
        atten *= atten;
    }

    float pan = 0.0f;
    float elevation = 0.0f;
    if (dist > 1e-4f) {
        Vec3 dir = d / dist;
        pan = clampf(dot(dir, listenerRight), -1.0f, 1.0f);
        elevation = clampf(dot(dir, listenerUp), -1.0f, 1.0f);
    }

    float proximity = clampf(1.0f - dist / std::max(v.minDistance * 2.0f, 0.5f), 0.0f, 1.0f);
    pan *= 1.0f - proximity * 0.6f;

    float angle = (pan * 0.5f + 0.5f) * HALF_PI;
    float l = std::cos(angle);
    float r = std::sin(angle);

    float shadow = 1.0f - std::fabs(elevation) * 0.18f;
    v.gainL = l * atten * shadow;
    v.gainR = r * atten * shadow;

    float behind = clampf(-dot(dist > 1e-4f ? (d / dist) : listenerFwd, listenerFwd), 0.0f, 1.0f);
    float distanceLp = clampf(dist / v.maxDistance, 0.0f, 1.0f);
    v.lowpass = clampf(v.lowpass * 0.0f + behind * 0.30f + distanceLp * 0.55f, 0.0f, 0.92f);
}

AudioEngine::Voice* AudioEngine::resolve(SoundHandle h) {
    if (h.index < 0 || h.index >= kMaxVoices) return nullptr;
    Voice& v = voices[h.index];
    if (!v.active || v.generation != h.generation) return nullptr;
    return &v;
}

const AudioEngine::Voice* AudioEngine::resolve(SoundHandle h) const {
    if (h.index < 0 || h.index >= kMaxVoices) return nullptr;
    const Voice& v = voices[h.index];
    if (!v.active || v.generation != h.generation) return nullptr;
    return &v;
}

SoundHandle AudioEngine::play(int soundId, const PlayParams& params) {
    SoundHandle handle;
    if (!device.running()) return handle;
    if (soundId < 0 || soundId >= SFX_COUNT) return handle;

    std::lock_guard<std::mutex> g(lock);

    int slot = -1;
    for (int i = 0; i < kMaxVoices; i++) {
        if (!voices[i].active) { slot = i; break; }
    }
    if (slot < 0) {
        float worst = 1e30f;
        for (int i = 0; i < kMaxVoices; i++) {
            if (voices[i].looping) continue;
            float score = voices[i].gainL + voices[i].gainR;
            if (score < worst) { worst = score; slot = i; }
        }
    }
    if (slot < 0) return handle;

    Voice& v = voices[slot];
    v = Voice();
    v.sound = soundId;
    v.generation = nextGeneration++;
    v.active = true;
    v.looping = params.looping || sounds.get(soundId).looping;
    v.spatial = params.spatial;
    v.cursor = 0.0;
    v.volume = params.volume;
    v.pitch = params.pitch;
    v.minDistance = params.minDistance;
    v.maxDistance = params.maxDistance;
    v.reverbSend = params.reverbSend;
    v.position = params.position;
    v.fadeCurrent = params.fadeIn > 0.0f ? 0.0f : 1.0f;
    v.fadeTarget = 1.0f;
    v.fadeSpeed = params.fadeIn > 0.0f ? 1.0f / std::max(params.fadeIn, 0.01f) : 40.0f;
    computePanning(v);
    v.smoothL = v.gainL;
    v.smoothR = v.gainR;

    handle.index = slot;
    handle.generation = v.generation;
    return handle;
}

SoundHandle AudioEngine::playAt(int soundId, const Vec3& pos, float volume, float pitch) {
    PlayParams p;
    p.position = pos;
    p.volume = volume;
    p.pitch = pitch;
    return play(soundId, p);
}

SoundHandle AudioEngine::play2D(int soundId, float volume, float pitch) {
    PlayParams p;
    p.spatial = false;
    p.volume = volume;
    p.pitch = pitch;
    p.reverbSend = 0.06f;
    return play(soundId, p);
}

void AudioEngine::stop(SoundHandle h, float fadeOut) {
    std::lock_guard<std::mutex> g(lock);
    Voice* v = resolve(h);
    if (!v) return;
    if (fadeOut <= 0.001f) {
        v->active = false;
        return;
    }
    v->stopping = true;
    v->fadeTarget = 0.0f;
    v->fadeSpeed = 1.0f / std::max(fadeOut, 0.01f);
}

void AudioEngine::stopAll() {
    std::lock_guard<std::mutex> g(lock);
    for (int i = 0; i < kMaxVoices; i++) voices[i].active = false;
}

void AudioEngine::setPosition(SoundHandle h, const Vec3& p) {
    std::lock_guard<std::mutex> g(lock);
    Voice* v = resolve(h);
    if (!v) return;
    v->position = p;
    computePanning(*v);
}

void AudioEngine::setVolume(SoundHandle h, float value) {
    std::lock_guard<std::mutex> g(lock);
    Voice* v = resolve(h);
    if (v) v->volume = value;
}

void AudioEngine::setPitch(SoundHandle h, float value) {
    std::lock_guard<std::mutex> g(lock);
    Voice* v = resolve(h);
    if (v) v->pitch = clampf(value, 0.05f, 4.0f);
}

void AudioEngine::setLowpass(SoundHandle h, float value) {
    std::lock_guard<std::mutex> g(lock);
    Voice* v = resolve(h);
    if (v) v->lowpass = clampf(value, 0.0f, 0.98f);
}

bool AudioEngine::isPlaying(SoundHandle h) const {
    std::lock_guard<std::mutex> g(lock);
    return resolve(h) != nullptr;
}

void AudioEngine::update(float dt) {
}

void AudioEngine::renderAudio(float* output, int frames, int channels) {
    std::memset(output, 0, (size_t)frames * channels * sizeof(float));
    if (channels < 1 || !ready.load()) return;

    std::lock_guard<std::mutex> g(lock);

    float master = masterVolume.load() * (1.0f - ducking.load() * 0.7f);
    float sr = (float)device.sampleRate();
    float bpm = heartbeatBpm.load();
    float tens = tension.load();

    static std::vector<float> mixL, mixR, sendL, sendR;
    if ((int)mixL.size() < frames) {
        mixL.resize((size_t)frames);
        mixR.resize((size_t)frames);
        sendL.resize((size_t)frames);
        sendR.resize((size_t)frames);
    }
    std::fill(mixL.begin(), mixL.begin() + frames, 0.0f);
    std::fill(mixR.begin(), mixR.begin() + frames, 0.0f);
    std::fill(sendL.begin(), sendL.begin() + frames, 0.0f);
    std::fill(sendR.begin(), sendR.begin() + frames, 0.0f);

    for (int vi = 0; vi < kMaxVoices; vi++) {
        Voice& v = voices[vi];
        if (!v.active) continue;

        const SoundClip& clip = sounds.get(v.sound);
        if (clip.samples.empty()) { v.active = false; continue; }

        double step = (double)v.pitch * clip.sampleRate / sr;
        float targetL = v.gainL * v.volume;
        float targetR = v.gainR * v.volume;
        float lpCoef = 1.0f - std::pow(1.0f - v.lowpass, 2.0f);
        lpCoef = clampf(lpCoef, 0.0f, 0.96f);

        for (int i = 0; i < frames; i++) {
            if (v.fadeCurrent != v.fadeTarget) {
                float d = v.fadeSpeed / sr;
                v.fadeCurrent = moveTowards(v.fadeCurrent, v.fadeTarget, d);
                if (v.stopping && v.fadeCurrent <= 0.0001f) { v.active = false; break; }
            }

            size_t idx = (size_t)v.cursor;
            if (idx + 1 >= clip.samples.size()) {
                if (v.looping) {
                    v.cursor = std::fmod(v.cursor, (double)(clip.samples.size() - 1));
                    idx = (size_t)v.cursor;
                } else {
                    v.active = false;
                    break;
                }
            }

            float frac = (float)(v.cursor - (double)idx);
            float s = lerpf(clip.samples[idx], clip.samples[idx + 1], frac);

            v.smoothL += (targetL - v.smoothL) * 0.002f;
            v.smoothR += (targetR - v.smoothR) * 0.002f;

            float l = s * v.smoothL * v.fadeCurrent;
            float r = s * v.smoothR * v.fadeCurrent;

            v.lpStateL += (l - v.lpStateL) * (1.0f - lpCoef);
            v.lpStateR += (r - v.lpStateR) * (1.0f - lpCoef);
            l = v.lpStateL;
            r = v.lpStateR;

            mixL[(size_t)i] += l;
            mixR[(size_t)i] += r;
            sendL[(size_t)i] += l * v.reverbSend;
            sendR[(size_t)i] += r * v.reverbSend;

            v.cursor += step;
        }
    }

    if (bpm > 1.0f) {
        const SoundClip& hb = sounds.get(SFX_HEARTBEAT);
        float period = 60.0f / bpm;
        float amp = clampf(tens * 0.55f, 0.0f, 0.6f);
        if (!hb.samples.empty() && amp > 0.005f) {
            for (int i = 0; i < frames; i++) {
                heartbeatPhase += 1.0f / sr;
                if (heartbeatPhase >= period) heartbeatPhase -= period;
                size_t idx = (size_t)(heartbeatPhase * hb.sampleRate);
                if (idx < hb.samples.size()) {
                    float s = hb.samples[idx] * amp;
                    mixL[(size_t)i] += s;
                    mixR[(size_t)i] += s;
                }
            }
        }
    }

    for (int i = 0; i < frames; i++) {
        float inL = sendL[(size_t)i] * 0.015f;
        float inR = sendR[(size_t)i] * 0.015f;
        float outL = 0.0f, outR = 0.0f;
        for (int c = 0; c < 8; c++) {
            outL += combsL[c].process(inL);
            outR += combsR[c].process(inR);
        }
        for (int a = 0; a < 4; a++) {
            outL = apsL[a].process(outL);
            outR = apsR[a].process(outR);
        }
        mixL[(size_t)i] += outL * reverbWet * 3.0f;
        mixR[(size_t)i] += outR * reverbWet * 3.0f;
    }

    for (int i = 0; i < frames; i++) {
        float l = mixL[(size_t)i] * master;
        float r = mixR[(size_t)i] * master;
        l = clampf(l, -1.0f, 1.0f);
        r = clampf(r, -1.0f, 1.0f);
        l = l - (l * l * l) / 3.0f;
        r = r - (r * r * r) / 3.0f;
        float* frame = output + (size_t)i * channels;
        if (channels == 1) {
            frame[0] = (l + r) * 0.5f;
        } else {
            frame[0] = l;
            frame[1] = r;
            for (int c = 2; c < channels; c++) frame[c] = 0.0f;
        }
    }
}

}
