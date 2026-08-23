#pragma once

#include <string>
#include <vector>

#include "Welt.hpp"
#include "fw/Maler.hpp"
#include "fw/Netz.hpp"

namespace harmonie {

constexpr float FIGUR_MASS = 1.25f;

struct Gestalt {
    fw::Netz netz;
    Vec3 haar;
    Vec3 kleid;
};

enum class Laune { Schlendern, Wandern, Helfen, Jubeln, Rasten };

struct Bewohner {
    Vec3 ort;
    Vec3 ziel;
    float richtung = 0.0f;
    float tempo = 1.6f;
    float takt = 0.0f;
    float warten = 0.0f;
    int gestalt = 0;
    int haustier = -1;
    Laune laune = Laune::Schlendern;
    Bezirk heimat = Bezirk::Herz;
    Bezirk unterwegsNach = Bezirk::Herz;
    int wegPunkt = 0;
    bool traegtBrett = false;
    float jubel = 0.0f;
    Gabe wunsch = Gabe::Keine;
    float wunschUhr = 0.0f;
    bool beschenkt = false;
};

struct Begleiter {
    Vec3 ort;
    float richtung = 0.0f;
    float takt = 0.0f;
    int art = 0;
    int folgt = -1;
};

class Volk {
public:
    void erstellen(const Welt& welt, unsigned saat, int anzahl);
    void freigeben();

    void aktualisieren(float dt, const Welt& welt, Vec3 spieler, bool feiern);
    void zeichnenLeute(fw::Maler& maler, float zeit);
    void zeichnenTiere(fw::Maler& maler, const Welt& welt, float zeit);
    void zeichnenSchatten(fw::Maler& maler, const Welt& welt);

    int lieferungenAbholen();
    int wuenscheZaehlen() const;
    Bewohner* naechsterBewohner(Vec3 ort, float weite);
    void wunschErfuellen(Bewohner& person);
    void feiernLassen(Vec3 sammelpunkt);
    void zuzugAufnehmen(const Welt& welt, Vec3 ankunft);
    int anzahl() const { return static_cast<int>(volk.size()); }
    const std::vector<Bewohner>& leute() const { return volk; }
    const fw::Netz& gestaltNetz(int index) const { return gestalten[index % 6].netz; }
    const fw::Netz& brettNetz() const { return brett; }
    const fw::Netz& gabenzeiger() const { return zeiger; }
    const fw::Netz& schattenNetz() const { return schatten; }
    Vec3 gestaltKleid(int index) const { return gestalten[index % 6].kleid; }

    static void gestaltBauen(fw::Bauer& bauer, Vec3 haut, Vec3 haar, Vec3 kleid, int frisur,
                             bool hut);

private:
    Vec3 zufallszielAuf(const Welt& welt, Bezirk bezirk, unsigned& streuer) const;
    void neuesZiel(Bewohner& person, const Welt& welt);

    std::vector<Bewohner> volk;
    std::vector<Begleiter> begleiter;
    Gestalt gestalten[6];
    fw::Netz tierNetze[3];
    fw::Netz begleiterNetze[2];
    fw::Netz brett;
    fw::Netz schatten;
    fw::Netz zeiger;
    fw::Zufall wuerfel;
    int offeneLieferungen = 0;
    float feierZeit = 0.0f;
    bool festLaeuft = false;
    Vec3 festOrt;
};

}
