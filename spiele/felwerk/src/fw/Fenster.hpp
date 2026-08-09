#pragma once

#include <string>

#include "GL.hpp"
#include "Mathe.hpp"

namespace fw {

enum class Maustaste { Links = 0, Rechts = 1, Mitte = 2 };

struct FensterWunsch {
    std::string titel = "FelWorks";
    int breite = 1280;
    int hoehe = 760;
    bool vollbild = false;
    bool vsync = true;
};

class Fenster {
public:
    ~Fenster();

    bool oeffnen(const FensterWunsch& wunsch);
    void schliessen();
    void ereignisse();
    void zeigen();

    bool offen() const { return !schliessenGewuenscht; }
    void schliessenAnfordern() { schliessenGewuenscht = true; }
    int breite() const { return fensterBreite; }
    int hoehe() const { return fensterHoehe; }
    float seitenverhaeltnis() const {
        return fensterHoehe > 0 ? static_cast<float>(fensterBreite) / static_cast<float>(fensterHoehe) : 1.0f;
    }
    bool fokussiert() const { return hatFokus; }
    void titelSetzen(const std::string& titel);
    void vollbildUmschalten();
    void vsyncSetzen(bool an);

    void mausFangen(bool an);
    bool mausGefangen() const { return mausFang; }

    bool taste(int schluessel) const { return schluessel >= 0 && schluessel < 256 && tasten[schluessel]; }
    bool tasteGedrueckt(int schluessel) const {
        return schluessel >= 0 && schluessel < 256 && tasten[schluessel] && !tastenVorher[schluessel];
    }
    bool tasteLosgelassen(int schluessel) const {
        return schluessel >= 0 && schluessel < 256 && !tasten[schluessel] && tastenVorher[schluessel];
    }
    bool maus(Maustaste taste) const { return maustasten[static_cast<int>(taste)]; }
    bool mausGedrueckt(Maustaste taste) const {
        int i = static_cast<int>(taste);
        return maustasten[i] && !maustastenVorher[i];
    }
    Vec2 mausOrt() const { return Vec2(mausX, mausY); }
    Vec2 mausBewegung() const { return Vec2(mausDeltaX, mausDeltaY); }
    float radBewegung() const { return radDelta; }

    void tasteMelden(unsigned schluessel, bool gedrueckt);
    void maustasteMelden(Maustaste taste, bool gedrueckt);
    void mausMelden(float x, float y);
    void radMelden(float wert);
    void groesseMelden(int breite, int hoehe);
    void fokusMelden(bool wert);

private:
    void mausMitteHalten();

    void* fenster = nullptr;
    void* geraet = nullptr;
    void* kontext = nullptr;
    int fensterBreite = 0;
    int fensterHoehe = 0;
    int gemerktX = 0;
    int gemerktY = 0;
    int gemerkteBreite = 0;
    int gemerkteHoehe = 0;
    bool vollbildAktiv = false;
    bool schliessenGewuenscht = false;
    bool hatFokus = true;
    bool mausFang = false;
    bool tasten[256] = {};
    bool tastenVorher[256] = {};
    bool maustasten[3] = {};
    bool maustastenVorher[3] = {};
    float mausX = 0.0f;
    float mausY = 0.0f;
    float mausDeltaX = 0.0f;
    float mausDeltaY = 0.0f;
    float radDelta = 0.0f;
};

}
