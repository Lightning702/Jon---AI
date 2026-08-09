#pragma once

#include "fw/Mathe.hpp"

namespace blockwelt {

using fw::Vec3;

enum Block : unsigned char {
    LUFT = 0,
    GRAS = 1,
    ERDE = 2,
    STEIN = 3,
    SAND = 4,
    WASSER = 5,
    STAMM = 6,
    LAUB = 7,
    SCHNEE = 8,
    BRETT = 9,
    GLAS = 10,
    BRUCHSTEIN = 11,
    ZIEGEL = 12,
    KAKTUS = 13,
    SANDSTEIN = 14,
    ENDERPERLE = 15,
    TNT = 16,
    BLOCK_ANZAHL = 17
};

struct Blockart {
    const char* name;
    int oben;
    int seite;
    int unten;
    bool fest;
    bool durchsichtig;
    Vec3 anzeige;
};

inline Vec3 ausByte(int r, int g, int b) {
    return Vec3(static_cast<float>(r) / 255.0f, static_cast<float>(g) / 255.0f,
                static_cast<float>(b) / 255.0f);
}

inline const Blockart& blockart(unsigned char id) {
    static const Blockart arten[BLOCK_ANZAHL] = {
        {"Luft", 0, 0, 0, false, true, ausByte(255, 255, 255)},
        {"Gras", 0, 1, 2, true, false, ausByte(109, 176, 66)},
        {"Erde", 2, 2, 2, true, false, ausByte(134, 96, 67)},
        {"Stein", 3, 3, 3, true, false, ausByte(127, 127, 127)},
        {"Sand", 4, 4, 4, true, false, ausByte(218, 205, 160)},
        {"Wasser", 5, 5, 5, false, true, ausByte(52, 104, 220)},
        {"Holzstamm", 7, 6, 7, true, false, ausByte(112, 88, 54)},
        {"Laub", 8, 8, 8, true, true, ausByte(58, 138, 48)},
        {"Schnee", 9, 9, 9, true, false, ausByte(240, 246, 250)},
        {"Bretter", 10, 10, 10, true, false, ausByte(162, 131, 81)},
        {"Glas", 11, 11, 11, true, true, ausByte(206, 236, 244)},
        {"Bruchstein", 12, 12, 12, true, false, ausByte(122, 122, 122)},
        {"Ziegel", 13, 13, 13, true, false, ausByte(152, 110, 95)},
        {"Kaktus", 15, 14, 15, true, false, ausByte(60, 118, 38)},
        {"Sandstein", 16, 16, 16, true, false, ausByte(214, 201, 154)},
        {"Enderperle", 17, 17, 17, true, false, ausByte(24, 108, 92)},
        {"TNT", 19, 18, 19, true, false, ausByte(196, 58, 38)}};
    return arten[id < BLOCK_ANZAHL ? id : 0];
}

inline bool istFest(unsigned char id) { return blockart(id).fest; }
inline bool istLuft(unsigned char id) { return id == LUFT; }
inline bool istFluessig(unsigned char id) { return id == WASSER; }
inline bool istDurchsichtig(unsigned char id) { return blockart(id).durchsichtig; }
inline bool leuchtet(unsigned char id) { return id == ENDERPERLE; }
inline Vec3 kachelfarbe(unsigned char id) { return blockart(id).anzeige; }

}
