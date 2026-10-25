#pragma once

#include "Strecke.hpp"
#include "fw/Netz.hpp"

namespace blitzbahn {

struct Lackierung {
    fw::Vec3 primaer = fw::Vec3(0.86f, 0.62f, 0.12f);
    fw::Vec3 sekundaer = fw::Vec3(0.08f, 0.1f, 0.16f);
    fw::Vec3 felgen = fw::Vec3(0.82f, 0.84f, 0.88f);
    fw::Vec3 rahmen = fw::Vec3(0.12f, 0.12f, 0.14f);
    int muster = 0;
};

void streckeBauen(const Strecke& strecke, fw::Bauer& fest, fw::Bauer& leucht);
void torBauen(fw::Bauer& tor, fw::Bauer& tafel);
void autoBauen(const Lackierung& farben, fw::Bauer& koerper, fw::Bauer& glut);
void radBauen(fw::Bauer& rad, fw::Vec3 felge, float breite);
void schattenBauen(fw::Bauer& schatten);
void landschaftBauen(const Strecke& strecke, unsigned saat, fw::Bauer& land, fw::Bauer& baeume);
float landHoehe(float x, float z, float x0, float z0, float x1, float z1, float flach, unsigned saat);
void himmelBauen(fw::Bauer& himmel, fw::Bauer& wolken, fw::Bauer& sonne, fw::Vec3 sonnenRichtung);
void gitterBauen(fw::Bauer& gitter, int mitteX, int mitteZ, int stufe, int weite);
void zeigerBauen(fw::Bauer& zeiger);

}
