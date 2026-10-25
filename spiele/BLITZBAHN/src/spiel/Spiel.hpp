#pragma once

#include <map>
#include <string>
#include <vector>

#include "Fahrzeug.hpp"
#include "Geist.hpp"
#include "Grafik.hpp"
#include "Modelle.hpp"
#include "Pilot.hpp"
#include "Strecke.hpp"
#include "fw/Fenster.hpp"
#include "fw/Koop.hpp"
#include "fw/Maler.hpp"
#include "fw/Netz.hpp"
#include "fw/Schrift.hpp"
#include "fw/Ton.hpp"

namespace blitzbahn {

struct Startwerte {
    int breite = 1360;
    int hoehe = 800;
    bool vollbild = false;
    int bilder = 0;
    std::string bilddatei;
    std::string ansicht;
    std::string strecke;
    bool autopilot = false;
    std::string koopWunsch;
    bool koopStarten = false;
};

enum class Ansicht { Haupt, Auswahl, Rennen, Editor, Garage, Mehrspieler, Einstellungen };

struct Profil {
    std::string name = "Fahrer";
    Lackierung farben;
    float lautstaerke = 0.55f;
    bool geist = true;
    bool schatten = true;
    int kamera = 0;
};

struct Teilchen {
    fw::Vec3 ort;
    fw::Vec3 fahrt;
    fw::Vec3 farbe;
    float alter = 0.0f;
    float dauer = 1.0f;
    float groesse = 1.0f;
    float wachsen = 1.0f;
    float deck = 0.5f;
    float auftrieb = 0.0f;
};

struct Ergebnis {
    std::string name;
    int ms = 0;
};

class Spiel {
public:
    bool starten(const Startwerte& werte);
    void laufen();
    void beenden();

private:
    void bild(float dt);
    void ansichtWechseln(Ansicht neu);

    void weltLaden(const Strecke& strecke);
    void autoNetzBauen();
    void szeneZeichnen(const fw::Mat4& sicht, const fw::Mat4& projektion, fw::Vec3 auge, bool mitTorFarben);
    void himmelZeichnen(fw::Vec3 auge);
    void autoZeichnen(const Lage& lage, float rad, float lenk, float deckkraft, fw::Vec3 toenung, float glut,
                      bool eigenesNetz);
    void schattenZeichnen(const Fahrzeug& wagen);
    void schattenPass(fw::Vec3 mitte, bool mitAuto);
    void autoSchatten(const Lage& lage, float rad, float lenk, bool eigenesNetz);
    void teilchenPflegen(float dt);
    void teilchenZeichnen();
    void spurSetzen(int rad, fw::Vec3 punkt);

    void rennenStarten(const Strecke& strecke, bool testfahrt);
    void rennenNeu();
    void rennenSchritt(float dt);
    void physikTick(float dt);
    void zurKontrolle();
    void zielErreicht();
    void kameraFuehren(float dt);
    void rennenAnzeige();
    void tonPflegen(float dt);

    void hauptSchritt(float dt);
    void hauptAnzeige();
    void auswahlAnzeige();
    void garageSchritt(float dt);
    void garageAnzeige();
    void einstellungenAnzeige();
    void mehrspielerAnzeige();

    void editorStarten(const Strecke& strecke);
    void editorSchritt(float dt);
    void editorZeichnen();
    void editorAnzeige();
    void editorSetzen();
    void editorEntfernen();
    void editorMerken();
    bool editorSpeichern();
    void editorVorschauBauen();

    void koopSchritt(float dt);
    void koopNachricht(const std::string& zeile);
    void koopStreckeSenden();
    void koopZeichnen();

    bool knopf(float x, float y, float b, float h, const std::string& text, bool hervor = false, bool aus = false);
    void tafel(float x, float y, float b, float h, float deck = 0.9f);
    void schreiben(float x, float y, const std::string& text, fw::Farbe farbe, int groesse = 1);
    void mittig(float x, float y, const std::string& text, fw::Farbe farbe, int groesse = 1);
    float breiteVon(const std::string& text, int groesse = 1);
    bool texteingabe(std::string& ziel, size_t laenge);
    bool ueber(float x, float y, float b, float h) const;
    void miniKarte(const Strecke& strecke, float x, float y, float b, float h);
    void meldung(const std::string& text, float dauer = 2.6f);
    bool bildschirmPunkt(fw::Vec3 welt, float& x, float& y) const;

    void profilLaden();
    void profilSpeichern();
    void rekordeLaden();
    void rekordeSpeichern();
    void eigeneLaden();
    std::string schluesselVon(const Strecke& strecke) const;
    std::string geistPfad(const std::string& schluessel) const;

    fw::Fenster fenster;
    fw::Maler maler;
    Grafik grafik;
    fw::Schrift schrift;
    fw::Schrift gross;
    fw::Schrift riesig;
    fw::Ton ton;
    fw::Koop koop;

    fw::Netz streckeNetz;
    fw::Netz leuchtNetz;
    fw::Netz landNetz;
    fw::Netz baumNetz;
    fw::Netz himmelNetz;
    fw::Netz wolkenNetz;
    fw::Netz sonneNetz;
    fw::Netz torNetz;
    fw::Netz tafelNetz;
    fw::Netz autoNetz;
    fw::Netz glutNetz;
    fw::Netz fremdNetz;
    fw::Netz radNetz;
    fw::Netz radBreitNetz;
    fw::Netz schattenNetz;
    fw::Netz gitterNetz;
    fw::Netz vorschauNetz;
    fw::Netz vorschauLeucht;
    fw::Netz zeigerNetz;
    fw::Netz bodenNetz;
    fw::Netz wasserNetz;
    fw::Netz teilchenNetz;
    fw::Netz spurNetz;
    std::vector<Teilchen> teilchen;
    std::vector<fw::Vec3> spuren;
    size_t spurZeiger = 0;
    bool spurAlt = false;
    float spurUhr = 0.0f;
    fw::Vec3 spurLetzt[2];
    bool spurHat[2] = {false, false};
    float teilchenUhr = 0.0f;
    bool warInLuft = false;

    Startwerte start;
    Profil profil;
    Ansicht ansicht = Ansicht::Haupt;
    std::vector<Strecke> offizielle;
    std::vector<Strecke> eigene;
    std::map<std::string, int> rekorde;
    Strecke strecke;
    std::string geladeneWelt;
    fw::Vec3 sonnenRichtung = fw::Vec3(0.5f, 0.56f, 0.42f);

    Fahrzeug wagen;
    Eingabe eingabe;
    Pilot pilot;
    float physikRest = 0.0f;
    float rennUhr = 0.0f;
    float vorlauf = 0.0f;
    bool rennenLaeuft = false;
    bool rennenFertig = false;
    bool pause = false;
    bool testfahrt = false;
    bool autopilotAn = false;
    int zielMs = 0;
    int besterMs = 0;
    bool neuerRekord = false;
    std::vector<int> erreicht;
    fw::Vec3 kontrollOrt;
    float kontrollGier = 0.0f;
    Geist aufnahme;
    Geist bester;
    int aufnahmeTakt = 0;
    float kontrollZeit = 0.0f;
    std::vector<Ergebnis> ergebnisse;
    int letzterVorlaufTon = -1;

    fw::Vec3 kameraOrt;
    fw::Vec3 kameraZiel;
    float sichtfeld = 1.2f;
    float wackeln = 0.0f;
    fw::Mat4 sichtMatrix;
    fw::Mat4 projMatrix;

    float zeit = 0.0f;
    float meldungZeit = 0.0f;
    std::string meldungText;
    int bildZaehler = 0;
    int auswahlReiter = 0;
    float auswahlRollen = 0.0f;
    bool tonAn = false;
    std::string* tippZiel = nullptr;
    std::string koopCode;
    int koopWahl = 0;
    std::string koopStreckeText;
    std::map<int, std::string> koopTeile;
    int koopTeileGesamt = 0;
    bool koopRennenAktiv = false;
    bool koopStreckeDa = false;

    Strecke edit;
    std::vector<Strecke> editRueck;
    int editTeil = GERADE;
    int editDreh = 0;
    int editEbene = 0;
    fw::Vec3 editZiel;
    float editAbstand = 150.0f;
    float editGier = 0.8f;
    float editNeigung = 0.85f;
    bool editHover = false;
    int editHoverX = 0;
    int editHoverZ = 0;
    int editVorschauX = 99999;
    int editVorschauZ = 0;
    int editVorschauTeil = -1;
    int editVorschauDreh = -1;
    int editVorschauEbene = -1;
    bool editGeaendert = false;
    fw::Vec2 mausVorher;
    fw::Vec2 rechtsStart;
    bool rechtsZieht = false;
    float garageDreh = 0.0f;
};

}
