#pragma once

#include "fw/Mathe.hpp"

namespace harmonie {

using fw::Vec3;

inline Vec3 ausByte(int r, int g, int b) {
    return Vec3(static_cast<float>(r) / 255.0f, static_cast<float>(g) / 255.0f,
                static_cast<float>(b) / 255.0f);
}

const Vec3 FARBE_SAND = ausByte(238, 214, 168);
const Vec3 FARBE_SAND_DUNKEL = ausByte(214, 184, 138);
const Vec3 FARBE_GRAS_HELL = ausByte(148, 196, 108);
const Vec3 FARBE_GRAS_TIEF = ausByte(92, 152, 88);
const Vec3 FARBE_ERDE = ausByte(146, 106, 74);
const Vec3 FARBE_FELS = ausByte(158, 150, 168);
const Vec3 FARBE_FELS_HELL = ausByte(196, 190, 204);
const Vec3 FARBE_FELS_TIEF = ausByte(104, 96, 118);
const Vec3 FARBE_HOEHLE = ausByte(46, 40, 58);
const Vec3 FARBE_RUINE = ausByte(180, 174, 160);
const Vec3 FARBE_KRISTALL = ausByte(150, 214, 226);

const Vec3 FARBE_WASSER_TIEF = ausByte(38, 96, 132);
const Vec3 FARBE_WASSER_FLACH = ausByte(96, 186, 194);
const Vec3 FARBE_SCHAUM = ausByte(226, 246, 246);

const Vec3 FARBE_HOLZ = ausByte(196, 142, 92);
const Vec3 FARBE_HOLZ_HELL = ausByte(222, 176, 124);
const Vec3 FARBE_HOLZ_DUNKEL = ausByte(140, 96, 62);
const Vec3 FARBE_SEIL = ausByte(206, 178, 132);
const Vec3 FARBE_PFLASTER = ausByte(206, 192, 172);
const Vec3 FARBE_LEHM = ausByte(238, 222, 196);
const Vec3 FARBE_LEHM_HELL = ausByte(248, 238, 218);
const Vec3 FARBE_SCHEUNE = ausByte(214, 138, 116);
const Vec3 FARBE_FENSTER = ausByte(252, 214, 138);
const Vec3 FARBE_GLAS = ausByte(198, 232, 238);
const Vec3 FARBE_PLAN = ausByte(214, 228, 240);
const Vec3 FARBE_LATERNE = ausByte(255, 216, 150);
const Vec3 FARBE_LICHT = ausByte(255, 240, 196);

const Vec3 FARBE_DACH_ZIEGEL = ausByte(206, 106, 92);
const Vec3 FARBE_DACH_TEAL = ausByte(104, 168, 168);
const Vec3 FARBE_TURM_ROT = ausByte(214, 118, 108);
const Vec3 FARBE_TURM_HELL = ausByte(248, 240, 228);

const Vec3 FARBE_LAUB = ausByte(112, 176, 100);
const Vec3 FARBE_LAUB_WARM = ausByte(160, 190, 92);
const Vec3 FARBE_LAUB_KUEHL = ausByte(94, 156, 128);
const Vec3 FARBE_BUSCH = ausByte(120, 168, 104);
const Vec3 FARBE_KORN = ausByte(224, 194, 108);
const Vec3 FARBE_FRUCHT = ausByte(226, 112, 104);
const Vec3 FARBE_FRUCHT_ZWEI = ausByte(240, 178, 88);
const Vec3 FARBE_SEGEL = ausByte(250, 244, 232);
const Vec3 FARBE_FERN = ausByte(150, 168, 194);
const Vec3 FARBE_FERN_TIEF = ausByte(116, 132, 162);

const Vec3 FARBE_DACH[3] = {ausByte(206, 106, 92), ausByte(104, 168, 168), ausByte(226, 168, 92)};
const Vec3 FARBE_STAND[5] = {ausByte(232, 138, 130), ausByte(238, 190, 106), ausByte(126, 186, 172),
                             ausByte(176, 156, 214), ausByte(240, 168, 190)};
const Vec3 FARBE_ACKER[4] = {ausByte(168, 132, 92), ausByte(150, 176, 96), ausByte(188, 158, 96),
                             ausByte(134, 164, 112)};
const Vec3 FARBE_BLUETE[4] = {ausByte(244, 176, 200), ausByte(250, 226, 132), ausByte(196, 176, 236),
                              ausByte(248, 156, 140)};

const Vec3 FARBE_HAUT[4] = {ausByte(244, 208, 178), ausByte(226, 176, 140), ausByte(186, 134, 100),
                            ausByte(134, 92, 68)};
const Vec3 FARBE_HAAR[6] = {ausByte(84, 60, 48),   ausByte(202, 148, 78), ausByte(220, 108, 84),
                            ausByte(58, 58, 72),   ausByte(238, 216, 188), ausByte(150, 112, 194)};
const Vec3 FARBE_KLEID[6] = {ausByte(226, 122, 128), ausByte(120, 172, 206), ausByte(150, 198, 140),
                             ausByte(238, 190, 118), ausByte(178, 158, 220), ausByte(238, 226, 208)};

const Vec3 FARBE_TIER[3] = {ausByte(238, 226, 206), ausByte(206, 176, 140), ausByte(160, 124, 96)};

}
