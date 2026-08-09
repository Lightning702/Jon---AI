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
    HOLZ = 5,
    LAUB = 6,
    BRETT = 7,
    ZIEGEL = 8,
    GLAS = 9,
    WASSER = 10,
    LEUCHTSTEIN = 11,
    SCHNEE = 12,
    KIES = 13,
    BLOCK_ANZAHL = 14
};

inline Vec3 ausByte(int r, int g, int b) {
    return Vec3(static_cast<float>(r) / 255.0f, static_cast<float>(g) / 255.0f,
                static_cast<float>(b) / 255.0f);
}

struct Blockart {
    const char* name;
    Vec3 oben;
    Vec3 seite;
    Vec3 unten;
    bool fest;
    bool sichtdurch;
    float leuchten;
};

inline const Blockart& blockart(unsigned char id) {
    static const Blockart arten[BLOCK_ANZAHL] = {
        {"Luft", Vec3(0, 0, 0), Vec3(0, 0, 0), Vec3(0, 0, 0), false, true, 0.0f},
        {"Gras", ausByte(126, 190, 96), ausByte(146, 116, 78), ausByte(134, 104, 72), true, false, 0.0f},
        {"Erde", ausByte(146, 112, 76), ausByte(140, 106, 72), ausByte(134, 102, 70), true, false, 0.0f},
        {"Stein", ausByte(146, 146, 154), ausByte(138, 138, 146), ausByte(128, 128, 136), true, false, 0.0f},
        {"Sand", ausByte(232, 214, 166), ausByte(226, 206, 158), ausByte(218, 198, 150), true, false, 0.0f},
        {"Holz", ausByte(160, 122, 74), ausByte(132, 98, 60), ausByte(160, 122, 74), true, false, 0.0f},
        {"Laub", ausByte(94, 162, 84), ausByte(86, 150, 78), ausByte(74, 132, 68), true, false, 0.0f},
        {"Bretter", ausByte(206, 160, 104), ausByte(198, 152, 98), ausByte(186, 142, 92), true, false, 0.0f},
        {"Ziegel", ausByte(196, 106, 92), ausByte(186, 98, 86), ausByte(176, 92, 80), true, false, 0.0f},
        {"Glas", ausByte(198, 232, 240), ausByte(198, 232, 240), ausByte(198, 232, 240), true, true, 0.0f},
        {"Wasser", ausByte(62, 130, 186), ausByte(58, 122, 178), ausByte(52, 112, 168), false, true, 0.0f},
        {"Leuchtstein", ausByte(250, 224, 150), ausByte(246, 214, 132), ausByte(240, 204, 120), true,
         false, 0.55f},
        {"Schnee", ausByte(244, 248, 252), ausByte(236, 240, 248), ausByte(228, 234, 244), true, false,
         0.0f},
        {"Kies", ausByte(168, 162, 156), ausByte(160, 154, 148), ausByte(152, 146, 140), true, false,
         0.0f}};
    return arten[id < BLOCK_ANZAHL ? id : 0];
}

inline bool istFest(unsigned char id) { return blockart(id).fest; }
inline bool istLuft(unsigned char id) { return id == LUFT; }
inline bool istFluessig(unsigned char id) { return id == WASSER; }

}
