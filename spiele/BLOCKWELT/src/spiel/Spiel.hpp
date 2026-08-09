#pragma once

#include <string>
#include <vector>

#include "Atlas.hpp"
#include "Figuren.hpp"
#include "Himmel.hpp"
#include "Welt.hpp"
#include "fw/Fenster.hpp"
#include "fw/Maler.hpp"
#include "fw/Netz.hpp"
#include "fw/Schrift.hpp"
#include "fw/Ton.hpp"

namespace blockwelt {

struct Startwerte {
    int breite = 1360;
    int hoehe = 800;
    bool vollbild = false;
    bool schnellstart = false;
    bool ohneAnzeige = false;
    bool frisch = false;
    bool blickGesetzt = false;
    int bilder = 0;
    int qualitaet = -1;
    int sofortBau = -1;
    unsigned saat = 1337;
    float tageszeit = 0.26f;
    float gierung = 0.0f;
    float neigung = 0.0f;
    std::string bilddatei;
};

struct Zuender {
    int x = 0;
    int y = 0;
    int z = 0;
    float rest = 0.0f;
};

struct Perle {
    fw::Vec3 ort;
    fw::Vec3 fahrt;
    float alter = 0.0f;
    bool fliegt = false;
};

class Spiel {
public:
    bool starten(const Startwerte& werte);
    void laufen();
    void beenden();

private:
    void eingabeLesen(float dt);
    void weltSchritt(float dt);
    void bildBauen();
    void anzeige();
    void bauwerkWaehlen(int nummer);
    void meldungSetzen(const std::string& text, float dauer = 2.4f);
    void handWechseln(int schritt);
    void zuenden(int x, int y, int z);
    void sprengen(int x, int y, int z);
    void perleWerfen();
    void spielerAbsetzen();

    fw::Fenster fenster;
    fw::Maler maler;
    fw::Schrift schrift;
    fw::Ton ton;
    Atlas atlas;
    Himmel himmel;
    Welt welt;
    Spieler spieler;
    MiniJon jon;
    fw::Netz rahmen;
    fw::Netz wuerfel;

    Startwerte start;
    Treffer ziel;
    std::vector<Zuender> zuender;
    Perle perle;
    float zeit = 0.0f;
    float tageszeit = 0.26f;
    float sicherungsUhr = 60.0f;
    float meldungZeit = 0.0f;
    float einblendung = 1.0f;
    float bildrate = 60.0f;
    float sichtweite = 90.0f;
    float blitz = 0.0f;
    std::string meldung;
    int handFach = 0;
    int radius = 6;
    int bildZaehler = 0;
    bool menueOffen = false;
    bool anzeigeAn = true;
    bool tonAn = false;
};

}
