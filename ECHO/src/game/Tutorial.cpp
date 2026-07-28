#include "Tutorial.h"

using namespace em;

namespace echo {

namespace {

struct StepInfo {
    const char* key;
    const char* text;
};

const StepInfo kSteps[TUT_DONE] = {
    { "W A S D",        "Bewegen" },
    { "MAUS",           "Umsehen" },
    { "F",              "Taschenlampe an und aus" },
    { "E",              "Tueren oeffnen und Dinge benutzen" },
    { "STRG",           "Ducken" },
    { "SHIFT",          "Sprinten, kostet Ausdauer" },
    { "TAB",            "Tagebuch, Dokumente und Aufnahmen" },
    { "ESC",            "Pause und Speichern" },
    { "OBEN LINKS",     "Dort steht immer, was zu tun ist" }
};

}

void Tutorial::reset(bool on) {
    enabled = on;
    current = on ? TUT_MOVE : TUT_DONE;
    fade = 0.0f;
    progress = 0.0f;
    stepTimer = 0.0f;
    doneTimer = 0.0f;
    movedDistance = 0.0f;
    turnedAmount = 0.0f;
    initialized = false;
}

void Tutorial::skip() {
    current = TUT_DONE;
    fade = 0.0f;
}

void Tutorial::complete() {
    skip();
}

void Tutorial::advance() {
    if (current >= TUT_DONE) return;
    current++;
    stepTimer = 0.0f;
    progress = 0.0f;
    doneTimer = 0.0f;
    movedDistance = 0.0f;
    turnedAmount = 0.0f;
}

const char* Tutorial::keyLabel() const {
    if (current < 0 || current >= TUT_DONE) return "";
    return kSteps[current].key;
}

const char* Tutorial::hintText() const {
    if (current < 0 || current >= TUT_DONE) return "";
    return kSteps[current].text;
}

void Tutorial::update(const Player& player, const TutorialSignals& signals, float dt) {
    if (!enabled || current >= TUT_DONE) {
        fade = lerpf(fade, 0.0f, 1.0f - std::exp(-6.0f * dt));
        return;
    }

    if (!initialized) {
        lastPos = player.position();
        lastYaw = player.yawAngle();
        initialized = true;
    }

    stepTimer += dt;

    float moved = length(Vec2(player.position().x - lastPos.x, player.position().z - lastPos.z));
    lastPos = player.position();
    movedDistance += moved;

    float turn = std::fabs(wrapAngle(player.yawAngle() - lastYaw));
    lastYaw = player.yawAngle();
    turnedAmount += turn;

    float target = stepTimer > 0.9f ? 1.0f : 0.0f;
    fade = lerpf(fade, target, 1.0f - std::exp(-3.5f * dt));

    if (doneTimer > 0.0f) {
        doneTimer -= dt;
        fade = lerpf(fade, 0.0f, 1.0f - std::exp(-7.0f * dt));
        if (doneTimer <= 0.0f) advance();
        return;
    }

    bool satisfied = false;
    switch (current) {
    case TUT_MOVE:       progress = clampf(movedDistance / 5.0f, 0.0f, 1.0f); satisfied = movedDistance > 5.0f; break;
    case TUT_LOOK:       progress = clampf(turnedAmount / 2.6f, 0.0f, 1.0f); satisfied = turnedAmount > 2.6f; break;
    case TUT_FLASHLIGHT: progress = signals.flashlightToggled ? 1.0f : 0.0f; satisfied = signals.flashlightToggled; break;
    case TUT_INTERACT:   progress = signals.interacted ? 1.0f : 0.0f; satisfied = signals.interacted; break;
    case TUT_CROUCH:     progress = signals.crouched ? 1.0f : 0.0f; satisfied = signals.crouched; break;
    case TUT_SPRINT:     progress = signals.sprinted ? 1.0f : 0.0f; satisfied = signals.sprinted || stepTimer > 26.0f; break;
    case TUT_JOURNAL:    progress = signals.journalOpened ? 1.0f : 0.0f; satisfied = signals.journalOpened || stepTimer > 34.0f; break;
    case TUT_PAUSE:      progress = signals.paused ? 1.0f : 0.0f; satisfied = signals.paused || stepTimer > 30.0f; break;
    case TUT_OBJECTIVE:  progress = clampf(stepTimer / 7.0f, 0.0f, 1.0f); satisfied = stepTimer > 7.0f; break;
    default: satisfied = true; break;
    }

    if (satisfied && stepTimer > 1.2f) doneTimer = 0.85f;
}

}
