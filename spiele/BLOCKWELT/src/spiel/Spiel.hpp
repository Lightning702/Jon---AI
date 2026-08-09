#pragma once

#include <string>

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
    int bilder = 0;
    int qualitaet = -1;
    int sofortBau = -1;
    unsigned saat = 5;
    float tageszeit = 0.26f;
    bool blickGesetzt = false;
    float gierung = 0.0f;
    float neigung = 0.0f;
    std::string bilddatei;
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

    fw::Fenster fenster;
    fw::Maler maler;
    fw::Schrift schrift;
    fw::Ton ton;
    Himmel himmel;
    Welt welt;
    Spieler spieler;
    MiniJon jon;
    fw::Netz rahmen;

    Startwerte start;
    Treffer ziel;
    float zeit = 0.0f;
    float tageszeit = 0.26f;
    float sicherungsUhr = 45.0f;
    float meldungZeit = 0.0f;
    float einblendung = 1.0f;
    float bildrate = 60.0f;
    float sichtweite = 78.0f;
    std::string meldung;
    unsigned char hand = ERDE;
    int handFach = 0;
    int bildZaehler = 0;
    bool menueOffen = false;
    bool anzeigeAn = true;
    bool tonAn = false;
};

}
