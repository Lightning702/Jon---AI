#pragma once

#include <string>

#include "Fenster.hpp"
#include "Koop.hpp"
#include "Schrift.hpp"

namespace fw {

class KoopSchirm {
public:
    void umschalten() { sichtbar = !sichtbar; }
    void oeffnen() { sichtbar = true; }
    void schliessen() { sichtbar = false; }
    bool offen() const { return sichtbar; }

    void tasten(Fenster& fenster, Koop& koop, unsigned long long saat, Vec3 start);
    void zeichnen(Schrift& schrift, const Koop& koop, int breite, int hoehe);
    void randzeile(Schrift& schrift, const Koop& koop, int breite, int hoehe);

private:
    bool sichtbar = false;
    bool tippt = false;
    std::string eingabe;
};

}
