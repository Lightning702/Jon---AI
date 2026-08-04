#pragma once

#include "Types.hpp"

namespace sf {

f64 clockSeconds();
void sleepMilliseconds(u32 milliseconds);
u64 wallClockUnixSeconds();

class FrameClock {
public:
    void reset();
    void tick();

    f64 deltaSeconds() const { return delta; }
    f64 smoothedDeltaSeconds() const { return smoothedDelta; }
    f64 elapsedSeconds() const { return elapsed; }
    u64 frameIndex() const { return frames; }
    f64 framesPerSecond() const { return smoothedDelta > 0.0 ? 1.0 / smoothedDelta : 0.0; }

private:
    f64 previous = 0.0;
    f64 delta = 0.0;
    f64 smoothedDelta = 1.0 / 60.0;
    f64 elapsed = 0.0;
    u64 frames = 0;
};

class FixedStepAccumulator {
public:
    explicit FixedStepAccumulator(f64 stepSeconds = 1.0 / 60.0) : step(stepSeconds) {}

    void addTime(f64 seconds);
    bool consumeStep();

    f64 stepSeconds() const { return step; }
    f64 interpolationAlpha() const { return accumulated / step; }
    u64 stepIndex() const { return steps; }
    void setTimeScale(f64 scale) { timeScale = scale; }
    f64 timeScaleValue() const { return timeScale; }

private:
    f64 step;
    f64 accumulated = 0.0;
    f64 timeScale = 1.0;
    u64 steps = 0;
};

}
