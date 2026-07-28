#pragma once

#include "../core/Common.h"
#include <functional>

namespace echo {

class AudioDevice {
public:
    using RenderCallback = std::function<void(float* output, int frames, int channels)>;

    bool start(const RenderCallback& cb);
    void stop();
    bool running() const { return active; }
    int sampleRate() const { return rate; }
    int channels() const { return chans; }

private:
    static unsigned long __stdcall threadEntry(void* param);
    void threadMain();

    RenderCallback callback;
    void* thread = nullptr;
    void* stopEvent = nullptr;
    volatile bool active = false;
    int rate = 48000;
    int chans = 2;
};

}
