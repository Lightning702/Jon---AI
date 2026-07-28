#pragma once

#include "Common.h"
#include <chrono>

namespace echo {

class Clock {
public:
    Clock() { reset(); }
    void reset() { start = std::chrono::high_resolution_clock::now(); }
    double elapsed() const {
        auto now = std::chrono::high_resolution_clock::now();
        return std::chrono::duration<double>(now - start).count();
    }
    double lap() { double e = elapsed(); reset(); return e; }
private:
    std::chrono::high_resolution_clock::time_point start;
};

struct FrameTimer {
    double now = 0.0;
    float dt = 0.0f;
    float unscaledDt = 0.0f;
    float timeScale = 1.0f;
    float smoothFps = 60.0f;
    u64 frame = 0;

    void tick() {
        double t = clock.elapsed();
        double raw = t - now;
        now = t;
        if (raw > 0.1) raw = 0.1;
        if (raw < 0.0) raw = 0.0;
        unscaledDt = (float)raw;
        dt = unscaledDt * timeScale;
        if (unscaledDt > 1e-6f) smoothFps = smoothFps * 0.94f + (1.0f / unscaledDt) * 0.06f;
        frame++;
    }
    Clock clock;
};

}
