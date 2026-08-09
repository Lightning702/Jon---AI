#pragma once

#include <vector>

#include "fw/Maler.hpp"
#include "fw/Mathe.hpp"
#include "fw/Netz.hpp"
#include "fw/Zufall.hpp"

namespace harmonie {

using fw::Vec3;

enum class Funke { Blatt, Gischt, Herz, Glanz, Staub };

struct Teilchen {
    Vec3 ort;
    Vec3 fahrt;
    Vec3 farbe;
    Funke art = Funke::Blatt;
    float alter = 0.0f;
    float dauer = 4.0f;
    float mass = 0.12f;
    float dreh = 0.0f;
};

class Funken {
public:
    void erstellen();
    void freigeben();

    void streuen(Funke art, Vec3 ort, int anzahl, float wucht = 1.0f);
    void wind(Vec3 richtung) { luft = richtung; }
    void aktualisieren(float dt, float zeit);
    void zeichnen(fw::Maler& maler, Vec3 rechts, Vec3 oben);

    size_t anzahl() const { return teilchen.size(); }
    void grenze(size_t wert) { hoechstzahl = wert; }

private:
    std::vector<Teilchen> teilchen;
    fw::Bauer bauer;
    fw::Netz netz;
    fw::Zufall wuerfel{0xBEEFu};
    Vec3 luft{0.35f, 0.0f, 0.2f};
    size_t hoechstzahl = 420;
};

}
