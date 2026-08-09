#pragma once

#include "fw/Mathe.hpp"

namespace blockwelt {

constexpr int KACHELN = 20;
constexpr int KACHEL = 16;

class Atlas {
public:
    ~Atlas();

    bool erstellen();
    void freigeben();
    unsigned kennung() const { return textur; }

    static fw::Vec2 bildpunkt(int kachel, float u, float v) {
        const float rand = 0.5f / static_cast<float>(KACHELN * KACHEL);
        float breite = 1.0f / static_cast<float>(KACHELN);
        float links = static_cast<float>(kachel) * breite + rand;
        float rechts = static_cast<float>(kachel + 1) * breite - rand;
        return fw::Vec2(links + (rechts - links) * u, rand + (1.0f - 2.0f * rand) * v);
    }

private:
    unsigned textur = 0;
};

}
