#pragma once

#include <string>

#include "Bewohner.hpp"
#include "Himmel.hpp"
#include "Partikel.hpp"
#include "Welt.hpp"
#include "fw/Fenster.hpp"
#include "fw/Koop.hpp"
#include "fw/KoopSchirm.hpp"
#include "fw/Maler.hpp"
#include "fw/Schrift.hpp"
#include "fw/Ton.hpp"

namespace harmonie {

struct Startwerte {
    int breite = 1360;
    int hoehe = 800;
    bool vollbild = false;
    bool schnellstart = false;
    int bilder = 0;
    int stufe = -1;
    int qualitaet = -1;
    unsigned saat = 7;
    bool uebersicht = false;
    bool ohneAnzeige = false;
    bool ortGesetzt = false;
    float ortX = 0.0f;
    float ortZ = 0.0f;
    std::string bilddatei;
    std::string koopWunsch;
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
    void kameraSetzen();
    void qualitaetSetzen(int stufe);
    void speichern();
    void laden();
    void sammeln();
    void abliefern();
    void gruessen();
    void schenken();
    void auftragLesen();
    void koopSchritt(float dt);
    void koopZeichnen();
    Vec3 kameraBlick() const;
    Vec3 kameraRechts() const;

    fw::Fenster fenster;
    fw::Maler maler;
    fw::Schrift schrift;
    fw::Ton ton;
    Himmel himmel;
    Welt welt;
    Volk volk;
    Funken funken;
    fw::Netz spielerNetz;
    fw::Netz gabenNetz[3];
    fw::Koop koop;
    fw::KoopSchirm koopSchirm;

    Startwerte start;
    Vec3 spielerOrt;
    Vec3 kameraZiel;
    float spielerRichtung = 0.0f;
    float spielerTakt = 0.0f;
    float sprung = 0.0f;
    float sprungKraft = 0.0f;
    float kameraDrehung = 0.785f;
    float kameraNeigung = 0.62f;
    float kameraWeite = 22.0f;
    float wunschWeite = 22.0f;
    float sonnenWinkel = 2.1f;
    float zeit = 0.0f;
    float einblendung = 1.0f;
    float meldungZeit = 0.0f;
    float feierBlitz = 0.0f;
    float regenbogen = 0.85f;
    float bildrate = 60.0f;
    std::string meldung;
    Gabe getragen[4] = {Gabe::Keine, Gabe::Keine, Gabe::Keine, Gabe::Keine};
    int getragenZahl = 0;
    int fortschritt = 0;
    int stufeErreicht = 0;
    int stufeGebracht = 0;
    int herzen = 0;
    Gabe stufeGabe = Gabe::Korn;
    int stufeBedarf = 3;
    float festUhr = 0.0f;
    int nebelStufe = 0;
    int nebelGebracht = 0;
    int nebelBedarf = 6;
    float zuzugUhr = 0.0f;
    bool fest = false;
    int qualitaet = 2;
    int bildZaehler = 0;
    bool uebersicht = false;
    bool anzeigeAn = true;
    bool laeuft = false;
    bool tonAn = true;
};

}
