#pragma once

#include <string>
#include <vector>

#include "Welt.hpp"
#include "fw/Fenster.hpp"
#include "fw/Maler.hpp"
#include "fw/Netz.hpp"

namespace blockwelt {

using fw::Vec3;

class Spieler {
public:
    void setzen(Vec3 ort);
    void blickSetzen(float gierung, float neigung);
    void schritt(float dt, const Welt& welt, fw::Fenster& fenster, bool eingabeAn);
    void umsehen(float dx, float dy);
    void springen();
    void fliegenUmschalten() { fliegt = !fliegt; }

    Vec3 fuesse() const { return ort; }
    Vec3 auge() const { return ort + Vec3(0.0f, 1.62f, 0.0f); }
    Vec3 blick() const;
    float gierung() const { return gier; }
    float neigung() const { return neig; }
    bool imWasser() const { return schwimmt; }
    bool fliegtGerade() const { return fliegt; }
    bool geradeGelaufen() const { return laufTakt > 0.0f; }
    float laufphase() const { return laufTakt; }

private:
    bool trifft(const Welt& welt, Vec3 pruefOrt) const;

    Vec3 ort{0.0f, 40.0f, 0.0f};
    Vec3 fahrt{0.0f, 0.0f, 0.0f};
    float gier = 0.0f;
    float neig = -0.2f;
    float laufTakt = 0.0f;
    bool amBoden = false;
    bool fliegt = false;
    bool schwimmt = false;
};

enum class Bauwerk { Haus, Turm, Bruecke, Baum, Leuchtfeuer };

struct Bauschritt {
    int x;
    int y;
    int z;
    unsigned char block;
};

class MiniJon {
public:
    void erstellen();
    void freigeben();
    void setzen(Vec3 ort);

    void schritt(float dt, Welt& welt, Vec3 spieler, float spielerGierung);
    void zeichnen(fw::Maler& maler, float zeit) const;

    void auftrag(Bauwerk werk, Welt& welt, Vec3 spieler, float gierung);
    bool baut() const { return !plan.empty(); }
    int offen() const { return static_cast<int>(plan.size()); }
    const std::string& spruch() const { return sagt; }
    float spruchZeit() const { return sagtZeit; }
    Vec3 ort() const { return stelle; }
    bool hatGesetzt() {
        bool wert = eben;
        eben = false;
        return wert;
    }

private:
    void planFuer(Bauwerk werk, const Welt& welt, int mx, int my, int mz);

    fw::Netz netz;
    std::vector<Bauschritt> plan;
    Vec3 stelle{0.0f, 40.0f, 0.0f};
    Vec3 ziel{0.0f, 40.0f, 0.0f};
    float richtung = 0.0f;
    float takt = 0.0f;
    float legeUhr = 0.0f;
    float sagtZeit = 0.0f;
    std::string sagt;
    bool eben = false;
};

const char* bauwerkName(Bauwerk werk);

}
