#pragma once

#include "Player.h"

namespace echo {

enum TutorialStep {
    TUT_MOVE = 0,
    TUT_LOOK,
    TUT_FLASHLIGHT,
    TUT_INTERACT,
    TUT_CROUCH,
    TUT_SPRINT,
    TUT_JOURNAL,
    TUT_PAUSE,
    TUT_OBJECTIVE,
    TUT_DONE
};

struct TutorialSignals {
    bool interacted = false;
    bool flashlightToggled = false;
    bool journalOpened = false;
    bool paused = false;
    bool crouched = false;
    bool sprinted = false;
};

class Tutorial {
public:
    void reset(bool enabled);
    void update(const Player& player, const TutorialSignals& signals, float dt);
    void skip();
    void complete();

    bool active() const { return enabled && current < TUT_DONE; }
    int step() const { return current; }
    void setStep(int s) { current = em::clampi(s, 0, TUT_DONE); }
    float alpha() const { return fade; }
    float holdProgress() const { return progress; }
    const char* keyLabel() const;
    const char* hintText() const;

private:
    void advance();

    bool enabled = true;
    int current = TUT_MOVE;
    float fade = 0.0f;
    float progress = 0.0f;
    float stepTimer = 0.0f;
    float doneTimer = 0.0f;
    float movedDistance = 0.0f;
    float turnedAmount = 0.0f;
    float lastYaw = 0.0f;
    em::Vec3 lastPos;
    bool initialized = false;
};

}
