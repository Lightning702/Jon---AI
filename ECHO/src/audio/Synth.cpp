#include "Synth.h"
#include "../core/Log.h"
#include "../core/Time.h"

using namespace em;

namespace echo {

namespace {

struct Biquad {
    float b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
    float z1 = 0, z2 = 0;

    void lowpass(float freq, float q, float sr) {
        float w = TAU * clampf(freq, 20.0f, sr * 0.45f) / sr;
        float alpha = std::sin(w) / (2.0f * std::max(q, 0.05f));
        float cw = std::cos(w);
        float a0 = 1.0f + alpha;
        b0 = ((1.0f - cw) * 0.5f) / a0;
        b1 = (1.0f - cw) / a0;
        b2 = b0;
        a1 = (-2.0f * cw) / a0;
        a2 = (1.0f - alpha) / a0;
    }
    void highpass(float freq, float q, float sr) {
        float w = TAU * clampf(freq, 20.0f, sr * 0.45f) / sr;
        float alpha = std::sin(w) / (2.0f * std::max(q, 0.05f));
        float cw = std::cos(w);
        float a0 = 1.0f + alpha;
        b0 = ((1.0f + cw) * 0.5f) / a0;
        b1 = -(1.0f + cw) / a0;
        b2 = b0;
        a1 = (-2.0f * cw) / a0;
        a2 = (1.0f - alpha) / a0;
    }
    void bandpass(float freq, float q, float sr) {
        float w = TAU * clampf(freq, 20.0f, sr * 0.45f) / sr;
        float alpha = std::sin(w) / (2.0f * std::max(q, 0.05f));
        float cw = std::cos(w);
        float a0 = 1.0f + alpha;
        b0 = alpha / a0;
        b1 = 0.0f;
        b2 = -alpha / a0;
        a1 = (-2.0f * cw) / a0;
        a2 = (1.0f - alpha) / a0;
    }
    float process(float x) {
        float y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        return y;
    }
    void reset() { z1 = z2 = 0; }
};

struct Env {
    float attack = 0.005f, decay = 0.2f, sustain = 0.0f, release = 0.1f;
    float at(float t, float dur) const {
        if (t < attack) return t / std::max(attack, 1e-5f);
        float d = t - attack;
        if (d < decay) return lerpf(1.0f, sustain, d / std::max(decay, 1e-5f));
        float relStart = dur - release;
        if (t >= relStart) return sustain * clampf((dur - t) / std::max(release, 1e-5f), 0.0f, 1.0f);
        return sustain;
    }
};

void allocate(SoundClip& c, int sr, float seconds) {
    c.sampleRate = sr;
    c.samples.assign((size_t)std::max(1, (int)(sr * seconds)), 0.0f);
}

void normalize(SoundClip& c, float peak) {
    float mx = 0.0f;
    for (float s : c.samples) mx = std::max(mx, std::fabs(s));
    if (mx < 1e-6f) return;
    float g = peak / mx;
    for (float& s : c.samples) s *= g;
}

void fadeEdges(SoundClip& c, float attackSec, float releaseSec) {
    int n = (int)c.samples.size();
    int a = std::max(1, (int)(attackSec * c.sampleRate));
    int r = std::max(1, (int)(releaseSec * c.sampleRate));
    for (int i = 0; i < a && i < n; i++) c.samples[(size_t)i] *= (float)i / a;
    for (int i = 0; i < r && i < n; i++) c.samples[(size_t)(n - 1 - i)] *= (float)i / r;
}

void genFootstep(SoundClip& c, int sr, Rng& rng, float bright, float thump, float grit, float dur) {
    allocate(c, sr, dur);
    Biquad body, high, noiseLp;
    body.bandpass(lerpf(90.0f, 240.0f, thump), 1.6f, (float)sr);
    high.bandpass(lerpf(1400.0f, 5200.0f, bright), 1.1f, (float)sr);
    noiseLp.lowpass(lerpf(1200.0f, 7000.0f, bright), 0.7f, (float)sr);

    int n = (int)c.samples.size();
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float e = std::exp(-t * lerpf(38.0f, 16.0f, thump));
        float eg = std::exp(-t * lerpf(90.0f, 30.0f, grit));
        float noise = rng.range(-1.0f, 1.0f);
        float v = body.process(noise) * e * (0.55f + thump * 0.6f);
        v += high.process(noise) * eg * (0.25f + bright * 0.5f);
        v += noiseLp.process(noise) * eg * grit * 0.35f;
        c.samples[(size_t)i] = v;
    }
    fadeEdges(c, 0.001f, 0.02f);
    normalize(c, 0.85f);
}

void genDoor(SoundClip& c, int sr, Rng& rng, float dur, float creakAmount, float thudAmount, float pitch) {
    allocate(c, sr, dur);
    int n = (int)c.samples.size();
    Biquad woodBp, creakBp, thudLp;
    woodBp.bandpass(220.0f * pitch, 2.5f, (float)sr);
    creakBp.bandpass(900.0f * pitch, 12.0f, (float)sr);
    thudLp.lowpass(160.0f, 0.8f, (float)sr);

    float creakPhase = 0.0f;
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float u = t / dur;
        float noise = rng.range(-1.0f, 1.0f);

        float stick = 0.0f;
        creakPhase += (0.4f + 0.9f * fbm2(Vec2(t * 3.0f, 0.0f), 3)) * 0.02f;
        float sq = std::sin(creakPhase * 40.0f);
        stick = (sq > 0.0f ? 1.0f : -1.0f) * (0.4f + 0.6f * fbm2(Vec2(t * 9.0f, 3.0f), 3));
        float creakEnv = std::sin(u * PI) * creakAmount;
        float creak = creakBp.process(stick * 0.6f + noise * 0.2f) * creakEnv;

        float thudEnv = std::exp(-std::max(0.0f, t - dur * 0.82f) * 26.0f) * (t > dur * 0.82f ? 1.0f : 0.0f);
        float thud = thudLp.process(noise) * thudEnv * thudAmount * 2.4f;

        float body = woodBp.process(noise) * std::exp(-t * 3.0f) * 0.22f;

        c.samples[(size_t)i] = creak + thud + body;
    }
    fadeEdges(c, 0.004f, 0.05f);
    normalize(c, 0.8f);
}

void genImpact(SoundClip& c, int sr, Rng& rng, float dur, float freq, float q, float decay, float noiseMix) {
    allocate(c, sr, dur);
    int n = (int)c.samples.size();
    Biquad bp1, bp2, bp3;
    bp1.bandpass(freq, q, (float)sr);
    bp2.bandpass(freq * 2.37f, q * 1.4f, (float)sr);
    bp3.bandpass(freq * 4.11f, q * 1.8f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float noise = rng.range(-1.0f, 1.0f);
        float e = std::exp(-t * decay);
        float v = bp1.process(noise) * e;
        v += bp2.process(noise) * e * 0.55f;
        v += bp3.process(noise) * std::exp(-t * decay * 2.2f) * 0.3f;
        v += noise * std::exp(-t * 120.0f) * noiseMix;
        c.samples[(size_t)i] = v;
    }
    fadeEdges(c, 0.0008f, 0.02f);
    normalize(c, 0.85f);
}

void genNoiseTexture(SoundClip& c, int sr, Rng& rng, float dur, float lowFreq, float highFreq, float modRate, bool loop) {
    allocate(c, sr, dur);
    c.looping = loop;
    int n = (int)c.samples.size();
    Biquad lp, hp;
    lp.lowpass(highFreq, 0.7f, (float)sr);
    hp.highpass(lowFreq, 0.7f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float noise = rng.range(-1.0f, 1.0f);
        float v = hp.process(lp.process(noise));
        float mod = 0.65f + 0.35f * fbm2(Vec2(t * modRate, 0.0f), 4);
        c.samples[(size_t)i] = v * mod;
    }
    if (loop) {
        int fade = std::min(n / 4, (int)(sr * 0.35f));
        for (int i = 0; i < fade; i++) {
            float a = (float)i / fade;
            float head = c.samples[(size_t)i];
            float tail = c.samples[(size_t)(n - fade + i)];
            c.samples[(size_t)i] = head * a + tail * (1.0f - a);
        }
        c.samples.resize((size_t)(n - fade));
    } else {
        fadeEdges(c, 0.05f, 0.2f);
    }
    normalize(c, 0.6f);
}

void genTone(SoundClip& c, int sr, Rng& rng, float dur, float freq, float detune, float decay, int harmonics, bool loop) {
    allocate(c, sr, dur);
    c.looping = loop;
    int n = (int)c.samples.size();
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float v = 0.0f;
        for (int h = 1; h <= harmonics; h++) {
            float f = freq * h * (1.0f + detune * (h - 1) * 0.012f);
            v += std::sin(TAU * f * t + h * 0.7f) / (float)h;
        }
        float e = decay > 0.0f ? std::exp(-t * decay) : 1.0f;
        c.samples[(size_t)i] = v * e;
    }
    if (loop) fadeEdges(c, 0.02f, 0.02f);
    else fadeEdges(c, 0.01f, std::min(0.3f, dur * 0.4f));
    normalize(c, 0.7f);
}

void genWhisper(SoundClip& c, int sr, Rng& rng, float dur, float pitch) {
    allocate(c, sr, dur);
    int n = (int)c.samples.size();
    Biquad f1, f2, f3;
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float u = t / dur;
        float formantShift = 1.0f + 0.35f * std::sin(u * PI * 5.0f) + 0.2f * fbm2(Vec2(t * 6.0f, 1.0f), 3);
        f1.bandpass(520.0f * pitch * formantShift, 9.0f, (float)sr);
        f2.bandpass(1180.0f * pitch * formantShift, 11.0f, (float)sr);
        f3.bandpass(2620.0f * pitch * formantShift, 13.0f, (float)sr);
        float noise = rng.range(-1.0f, 1.0f);
        float syllable = smoothstepf(0.0f, 0.12f, std::fabs(std::sin(u * PI * 6.5f)));
        float v = (f1.process(noise) * 1.0f + f2.process(noise) * 0.65f + f3.process(noise) * 0.32f) * syllable;
        c.samples[(size_t)i] = v * std::sin(u * PI);
    }
    fadeEdges(c, 0.05f, 0.2f);
    normalize(c, 0.55f);
}

void genHeartbeat(SoundClip& c, int sr, Rng& rng) {
    allocate(c, sr, 1.0f);
    int n = (int)c.samples.size();
    Biquad lp;
    lp.lowpass(120.0f, 0.9f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float v = 0.0f;
        float b1 = t;
        float b2 = t - 0.28f;
        if (b1 >= 0.0f && b1 < 0.3f) v += std::sin(TAU * 46.0f * b1) * std::exp(-b1 * 22.0f);
        if (b2 >= 0.0f && b2 < 0.3f) v += std::sin(TAU * 38.0f * b2) * std::exp(-b2 * 26.0f) * 0.7f;
        c.samples[(size_t)i] = lp.process(v);
    }
    normalize(c, 0.9f);
}

void genBreath(SoundClip& c, int sr, Rng& rng) {
    allocate(c, sr, 2.4f);
    int n = (int)c.samples.size();
    Biquad bp;
    bp.bandpass(560.0f, 1.1f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float u = t / 2.4f;
        float inhale = std::exp(-std::pow((u - 0.22f) * 6.0f, 2.0f));
        float exhale = std::exp(-std::pow((u - 0.68f) * 4.2f, 2.0f));
        float noise = rng.range(-1.0f, 1.0f);
        c.samples[(size_t)i] = bp.process(noise) * (inhale * 0.9f + exhale * 1.1f);
    }
    fadeEdges(c, 0.05f, 0.2f);
    normalize(c, 0.55f);
}

void genPaStatic(SoundClip& c, int sr, Rng& rng) {
    allocate(c, sr, 3.2f);
    int n = (int)c.samples.size();
    Biquad bp, crackle;
    bp.bandpass(1500.0f, 0.8f, (float)sr);
    crackle.bandpass(3200.0f, 4.0f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float u = t / 3.2f;
        float noise = rng.range(-1.0f, 1.0f);
        float carrier = std::sin(TAU * 220.0f * t + std::sin(TAU * 3.1f * t) * 2.0f);
        float speechEnv = smoothstepf(0.05f, 0.2f, std::fabs(std::sin(u * PI * 9.0f))) * (u > 0.12f && u < 0.88f ? 1.0f : 0.0f);
        float pops = rng.chance(0.0012f) ? 1.0f : 0.0f;
        float v = bp.process(noise * 0.5f + carrier * 0.5f) * speechEnv;
        v += crackle.process(noise) * (0.18f + pops * 2.0f);
        c.samples[(size_t)i] = v;
    }
    fadeEdges(c, 0.03f, 0.25f);
    normalize(c, 0.7f);
}

void genRoll(SoundClip& c, int sr, Rng& rng, float dur, float rattle) {
    allocate(c, sr, dur);
    int n = (int)c.samples.size();
    Biquad lp, bp;
    lp.lowpass(900.0f, 0.7f, (float)sr);
    bp.bandpass(2400.0f, 6.0f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float noise = rng.range(-1.0f, 1.0f);
        float wobble = 0.6f + 0.4f * std::sin(TAU * 7.3f * t + std::sin(TAU * 1.7f * t));
        float v = lp.process(noise) * wobble * 0.7f;
        if (rng.chance(0.004f * rattle)) v += bp.process(2.0f);
        v += bp.process(noise * 0.15f * rattle);
        c.samples[(size_t)i] = v;
    }
    fadeEdges(c, 0.08f, 0.15f);
    normalize(c, 0.6f);
}

void genScratch(SoundClip& c, int sr, Rng& rng, float dur) {
    allocate(c, sr, dur);
    int n = (int)c.samples.size();
    Biquad bp;
    bp.bandpass(2800.0f, 3.5f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float u = t / dur;
        float stroke = std::fabs(std::sin(u * PI * 4.0f));
        stroke = std::pow(stroke, 3.0f);
        float noise = rng.range(-1.0f, 1.0f);
        c.samples[(size_t)i] = bp.process(noise) * stroke;
    }
    fadeEdges(c, 0.02f, 0.08f);
    normalize(c, 0.65f);
}

void genDrip(SoundClip& c, int sr, Rng& rng) {
    allocate(c, sr, 0.55f);
    int n = (int)c.samples.size();
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float f = 1400.0f * std::exp(-t * 16.0f) + 320.0f;
        float e = std::exp(-t * 26.0f);
        c.samples[(size_t)i] = std::sin(TAU * f * t) * e;
    }
    fadeEdges(c, 0.001f, 0.05f);
    normalize(c, 0.7f);
}

void genLobbyMusic(SoundClip& c, int sr, Rng& rng) {
    const float dur = 36.0f;
    allocate(c, sr, dur);
    c.looping = true;
    int n = (int)c.samples.size();

    Biquad body, air, sweep;
    body.lowpass(1500.0f, 0.55f, (float)sr);
    air.bandpass(4600.0f, 0.7f, (float)sr);
    sweep.bandpass(320.0f, 1.6f, (float)sr);

    const float root = 55.0f;
    const float partials[7] = { 0.5f, 1.0f, 1.0018f, 1.4983f, 1.5031f, 1.1892f, 2.0f };
    const float scaleSteps[6] = { 1.0f, 1.1892f, 1.3348f, 1.4983f, 1.7818f, 2.0f };

    struct Bell { float t, freq, amp, decay; };
    std::vector<Bell> bells;
    for (float t = 1.5f; t < dur - 5.0f; t += rng.range(2.6f, 6.4f)) {
        Bell b;
        b.t = t;
        b.freq = root * 8.0f * scaleSteps[rng.rangeInt(0, 6)] * (rng.chance(0.35f) ? 0.5f : 1.0f);
        b.amp = rng.range(0.16f, 0.40f);
        b.decay = rng.range(0.85f, 1.7f);
        bells.push_back(b);
    }

    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;

        float swell = 0.40f + 0.32f * std::sin(t * 0.052f * TAU) + 0.16f * std::sin(t * 0.019f * TAU + 1.7f);
        swell = clampf(swell, 0.05f, 1.0f);

        float drone = 0.0f;
        for (int v = 0; v < 7; v++) {
            float wobble = 1.0f + 0.0009f * std::sin(t * (0.07f + v * 0.013f) * TAU + v);
            drone += std::sin(TAU * root * partials[v] * wobble * t + v * 1.31f) / (1.0f + v * 0.62f);
        }
        drone *= swell * 0.34f;

        float bellSum = 0.0f;
        for (const Bell& b : bells) {
            float bt = t - b.t;
            if (bt < 0.0f || bt > 7.0f) continue;
            float env = std::exp(-bt * b.decay) * (1.0f - std::exp(-bt * 30.0f));
            bellSum += (std::sin(TAU * b.freq * bt)
                      + std::sin(TAU * b.freq * 2.01f * bt) * 0.34f
                      + std::sin(TAU * b.freq * 2.97f * bt) * 0.15f
                      + std::sin(TAU * b.freq * 4.13f * bt) * 0.07f) * env * b.amp;
        }

        float noise = rng.range(-1.0f, 1.0f);
        float hiss = air.process(noise) * 0.045f * (0.55f + 0.45f * swell);
        float rumble = sweep.process(noise) * 0.10f * swell;

        c.samples[(size_t)i] = body.process(drone + bellSum * 0.5f) + hiss + rumble;
    }

    int fade = std::min(n / 4, (int)(sr * 3.5f));
    for (int i = 0; i < fade; i++) {
        float a = (float)i / fade;
        float head = c.samples[(size_t)i];
        float tail = c.samples[(size_t)(n - fade + i)];
        c.samples[(size_t)i] = head * a + tail * (1.0f - a);
    }
    c.samples.resize((size_t)(n - fade));

    normalize(c, 0.60f);
}

void genSting(SoundClip& c, int sr, Rng& rng, float dur, float baseFreq, bool rising) {
    allocate(c, sr, dur);
    int n = (int)c.samples.size();
    Biquad lp;
    lp.lowpass(4200.0f, 0.7f, (float)sr);
    for (int i = 0; i < n; i++) {
        float t = (float)i / sr;
        float u = t / dur;
        float f = rising ? baseFreq * (1.0f + u * 2.2f) : baseFreq * (1.0f - u * 0.42f);
        float v = 0.0f;
        v += std::sin(TAU * f * t);
        v += std::sin(TAU * f * 1.4983f * t) * 0.6f;
        v += std::sin(TAU * f * 2.0f * t + std::sin(TAU * f * 0.5f * t) * 3.0f) * 0.4f;
        v += rng.range(-1.0f, 1.0f) * 0.12f;
        float e = rising ? std::pow(u, 1.6f) * (1.0f - smoothstepf(0.82f, 1.0f, u)) : std::exp(-t * 2.4f);
        c.samples[(size_t)i] = lp.process(v) * e;
    }
    fadeEdges(c, 0.01f, 0.25f);
    normalize(c, 0.85f);
}

}

void SoundBank::generate(int sampleRate) {
    Clock clock;
    Rng rng(0xA0D10);

    genFootstep(clips[SFX_STEP_TILE], sampleRate, rng, 0.85f, 0.35f, 0.25f, 0.24f);
    genFootstep(clips[SFX_STEP_CONCRETE], sampleRate, rng, 0.55f, 0.55f, 0.45f, 0.28f);
    genFootstep(clips[SFX_STEP_LINO], sampleRate, rng, 0.45f, 0.30f, 0.30f, 0.22f);
    genFootstep(clips[SFX_STEP_METAL], sampleRate, rng, 1.0f, 0.20f, 0.15f, 0.40f);
    genFootstep(clips[SFX_STEP_WATER], sampleRate, rng, 0.70f, 0.25f, 0.90f, 0.34f);
    genFootstep(clips[SFX_STEP_DEBRIS], sampleRate, rng, 0.75f, 0.40f, 1.0f, 0.32f);

    genDoor(clips[SFX_DOOR_OPEN], sampleRate, rng, 1.35f, 0.85f, 0.25f, 1.0f);
    genDoor(clips[SFX_DOOR_CLOSE], sampleRate, rng, 1.05f, 0.45f, 0.9f, 1.05f);
    genDoor(clips[SFX_DOOR_CREAK], sampleRate, rng, 1.9f, 1.0f, 0.05f, 0.85f);
    genImpact(clips[SFX_DOOR_LOCKED], sampleRate, rng, 0.35f, 340.0f, 5.0f, 30.0f, 0.35f);
    genImpact(clips[SFX_DOOR_SLAM], sampleRate, rng, 0.9f, 95.0f, 1.2f, 9.0f, 0.55f);
    genImpact(clips[SFX_DRAWER], sampleRate, rng, 0.55f, 480.0f, 2.5f, 14.0f, 0.4f);
    genImpact(clips[SFX_SWITCH], sampleRate, rng, 0.12f, 2400.0f, 9.0f, 90.0f, 0.5f);
    genImpact(clips[SFX_PICKUP], sampleRate, rng, 0.3f, 900.0f, 4.0f, 26.0f, 0.3f);
    genImpact(clips[SFX_CLICK], sampleRate, rng, 0.08f, 3200.0f, 12.0f, 130.0f, 0.6f);
    genNoiseTexture(clips[SFX_PAPER], sampleRate, rng, 0.6f, 900.0f, 8000.0f, 22.0f, false);
    genImpact(clips[SFX_GLASS_BREAK], sampleRate, rng, 1.3f, 4200.0f, 8.0f, 7.0f, 0.8f);
    genImpact(clips[SFX_LIGHT_POP], sampleRate, rng, 0.42f, 1800.0f, 3.0f, 22.0f, 0.9f);
    genImpact(clips[SFX_PIPE_KNOCK], sampleRate, rng, 0.85f, 260.0f, 14.0f, 8.0f, 0.2f);

    genTone(clips[SFX_LIGHT_BUZZ], sampleRate, rng, 2.0f, 100.0f, 0.4f, 0.0f, 7, true);
    genNoiseTexture(clips[SFX_VENT_HUM], sampleRate, rng, 4.0f, 40.0f, 420.0f, 0.35f, true);
    genNoiseTexture(clips[SFX_WIND], sampleRate, rng, 6.0f, 120.0f, 1600.0f, 0.22f, true);
    genNoiseTexture(clips[SFX_TAPE_HISS], sampleRate, rng, 3.0f, 700.0f, 9000.0f, 0.8f, true);
    genTone(clips[SFX_ELEVATOR_HUM], sampleRate, rng, 3.0f, 62.0f, 0.6f, 0.0f, 5, true);
    genTone(clips[SFX_ELEVATOR_DING], sampleRate, rng, 1.8f, 880.0f, 0.02f, 2.6f, 3, false);
    genTone(clips[SFX_DRONE], sampleRate, rng, 8.0f, 44.0f, 0.9f, 0.0f, 6, true);

    genFootstep(clips[SFX_DISTANT_STEPS], sampleRate, rng, 0.25f, 0.7f, 0.1f, 0.5f);
    genDoor(clips[SFX_DISTANT_DOOR], sampleRate, rng, 1.6f, 0.4f, 0.6f, 0.7f);
    genWhisper(clips[SFX_WHISPER], sampleRate, rng, 3.4f, 1.0f);
    genWhisper(clips[SFX_VOICE_FAR], sampleRate, rng, 4.2f, 0.62f);
    genScratch(clips[SFX_SCRATCH], sampleRate, rng, 2.2f);
    genRoll(clips[SFX_METAL_DRAG], sampleRate, rng, 2.6f, 1.4f);
    genRoll(clips[SFX_WHEELCHAIR], sampleRate, rng, 3.4f, 1.0f);
    genRoll(clips[SFX_BED_ROLL], sampleRate, rng, 2.8f, 0.5f);
    genDrip(clips[SFX_DRIP], sampleRate, rng);
    genPaStatic(clips[SFX_PA_STATIC], sampleRate, rng);
    genHeartbeat(clips[SFX_HEARTBEAT], sampleRate, rng);
    genBreath(clips[SFX_BREATH], sampleRate, rng);
    genSting(clips[SFX_STING_LOW], sampleRate, rng, 3.6f, 38.0f, false);
    genSting(clips[SFX_STING_HIGH], sampleRate, rng, 2.4f, 210.0f, true);
    genLobbyMusic(clips[SFX_MUSIC_LOBBY], sampleRate, rng);

    size_t total = 0;
    for (int i = 0; i < SFX_COUNT; i++) total += clips[i].samples.size();
    LOG_INFO("Synthesized %d sounds (%.1f MB) in %.2fs", (int)SFX_COUNT, total * sizeof(float) / 1048576.0, clock.elapsed());
}

void SoundBank::destroy() {
    for (int i = 0; i < SFX_COUNT; i++) {
        clips[i].samples.clear();
        clips[i].samples.shrink_to_fit();
    }
}

int SoundBank::variantCount(int id) const { return 1; }

}
