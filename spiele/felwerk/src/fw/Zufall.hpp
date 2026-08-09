#pragma once

#include <cstdint>

#include "Mathe.hpp"

namespace fw {

class Zufall {
public:
    explicit Zufall(uint64_t saat = 0x9E3779B97F4A7C15ull) : zustand(saat | 1ull) {}

    uint32_t naechste() {
        zustand ^= zustand << 13;
        zustand ^= zustand >> 7;
        zustand ^= zustand << 17;
        return static_cast<uint32_t>(zustand >> 32);
    }

    float einheit() { return static_cast<float>(naechste() & 0xFFFFFF) / 16777215.0f; }

    float bereich(float unten, float oben) { return unten + (oben - unten) * einheit(); }

    int ganz(int unten, int oben) {
        if (oben <= unten) return unten;
        return unten + static_cast<int>(naechste() % static_cast<uint32_t>(oben - unten));
    }

    bool chance(float wahrscheinlichkeit) { return einheit() < wahrscheinlichkeit; }

private:
    uint64_t zustand;
};

inline float streu(int x, int y, int saat) {
    uint32_t h = static_cast<uint32_t>(x) * 374761393u + static_cast<uint32_t>(y) * 668265263u +
                 static_cast<uint32_t>(saat) * 2246822519u;
    h = (h ^ (h >> 13)) * 1274126177u;
    h ^= h >> 16;
    return static_cast<float>(h & 0xFFFFFF) / 16777215.0f;
}

inline float wertRauschen(float x, float y, int saat) {
    float fx = std::floor(x);
    float fy = std::floor(y);
    int ix = static_cast<int>(fx);
    int iy = static_cast<int>(fy);
    float tx = x - fx;
    float ty = y - fy;
    float sx = tx * tx * (3.0f - 2.0f * tx);
    float sy = ty * ty * (3.0f - 2.0f * ty);
    float a = streu(ix, iy, saat);
    float b = streu(ix + 1, iy, saat);
    float c = streu(ix, iy + 1, saat);
    float d = streu(ix + 1, iy + 1, saat);
    return mische(mische(a, b, sx), mische(c, d, sx), sy);
}

inline float bergRauschen(float x, float y, int saat, int lagen = 4, float verfall = 0.5f) {
    float summe = 0.0f;
    float gewicht = 0.0f;
    float staerke = 1.0f;
    float weite = 1.0f;
    for (int i = 0; i < lagen; ++i) {
        summe += wertRauschen(x * weite, y * weite, saat + i * 131) * staerke;
        gewicht += staerke;
        staerke *= verfall;
        weite *= 2.0f;
    }
    return gewicht > 0.0f ? summe / gewicht : 0.0f;
}

}
