#include "Time.hpp"

#include <chrono>
#include <thread>

namespace sf {

f64 clockSeconds() {
    using Clock = std::chrono::steady_clock;
    static const Clock::time_point origin = Clock::now();
    const Clock::time_point now = Clock::now();
    return std::chrono::duration<f64>(now - origin).count();
}

void sleepMilliseconds(u32 milliseconds) {
    std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

u64 wallClockUnixSeconds() {
    const auto now = std::chrono::system_clock::now().time_since_epoch();
    return static_cast<u64>(std::chrono::duration_cast<std::chrono::seconds>(now).count());
}

void FrameClock::reset() {
    previous = clockSeconds();
    delta = 0.0;
    smoothedDelta = 1.0 / 60.0;
    elapsed = 0.0;
    frames = 0;
}

void FrameClock::tick() {
    const f64 now = clockSeconds();
    if (previous <= 0.0) previous = now;
    delta = now - previous;
    previous = now;
    if (delta < 0.0) delta = 0.0;
    if (delta > 0.25) delta = 0.25;
    smoothedDelta = smoothedDelta * 0.92 + delta * 0.08;
    elapsed += delta;
    ++frames;
}

void FixedStepAccumulator::addTime(f64 seconds) {
    f64 scaled = seconds * timeScale;
    if (scaled < 0.0) scaled = 0.0;
    const f64 ceiling = step * 8.0;
    if (scaled > ceiling) scaled = ceiling;
    accumulated += scaled;
}

bool FixedStepAccumulator::consumeStep() {
    if (accumulated < step) return false;
    accumulated -= step;
    ++steps;
    return true;
}

}
