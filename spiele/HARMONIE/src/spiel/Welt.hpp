#pragma once

#include <string>
#include <vector>

#include "fw/Mathe.hpp"
#include "fw/Netz.hpp"
#include "fw/Zufall.hpp"

namespace harmonie {

using fw::Bauer;
using fw::Mat4;
using fw::Netz;
using fw::Vec2;
using fw::Vec3;

enum class Bezirk { Herz, Farm, Berg, Werft, Nebel };

enum class Gabe { Keine, Korn, Stein, Brett };

struct Insel {
    Bezirk art = Bezirk::Herz;
    Vec2 mitte;
    float radius = 20.0f;
    float hoehe = 4.0f;
    std::string name;
};

struct Bruecke {
    Vec3 von;
    Vec3 bis;
};

struct Fundort {
    Gabe gabe = Gabe::Korn;
    Vec3 ort;
    float nachwachsen = 0.0f;
    float reife = 1.0f;
};

struct Tier {
    Vec3 ort;
    float richtung = 0.0f;
    int art = 0;
    float takt = 0.0f;
    float weideZiel = 0.0f;
};

class Welt {
public:
    void erzeugen(unsigned saat);
    void netzeBauen();
    void freigeben();

    float hoeheBei(float x, float z) const;
    bool aufLand(float x, float z, float rand = 0.0f) const;
    bool aufBruecke(float x, float z, float& hoehe) const;
    float bodenBei(float x, float z) const;

    const std::vector<Insel>& inseln() const { return inselListe; }
    const std::vector<Bruecke>& bruecken() const { return brueckenListe; }
    std::vector<Fundort>& fundorte() { return fundListe; }
    const std::vector<Fundort>& fundorte() const { return fundListe; }
    std::vector<Tier>& tiere() { return tierListe; }
    const std::vector<Tier>& tiere() const { return tierListe; }

    const Insel& insel(Bezirk art) const;
    Vec3 mittelpunkt(Bezirk art) const;
    Vec3 leuchtturmFuss() const { return leuchtturm; }
    Vec3 regenbogenOrt() const { return bogenOrt; }
    Vec3 werkstattOrt() const { return werkstatt; }

    void leuchtturmStufe(int stufe);
    int leuchtturmStufe() const { return turmStufe; }

    const Netz& landNetz() const { return land; }
    const Netz& bautenNetz() const { return bauten; }
    const Netz& gruenNetz() const { return gruen; }
    const Netz& wasserNetz() const { return wasser; }
    const Netz& turmNetz() const { return turm; }
    const Netz& fernNetz() const { return fern; }
    const Netz& booteNetz() const { return boote; }
    const Netz& regenbogenNetz() const { return regenbogen; }
    const Netz& schattenNetz() const { return schatten; }

    void detailStufe(int stufe) { detail = stufe; }

private:
    void inselnAnlegen();
    void landFormen(Bauer& bauer);
    void inselFormen(Bauer& bauer, const Insel& stueck);
    void wasserFormen(Bauer& bauer);
    void bruecken(Bauer& bauer);
    void herzBebauen(Bauer& bauer, Bauer& laub);
    void farmBebauen(Bauer& bauer, Bauer& laub);
    void bergBebauen(Bauer& bauer, Bauer& laub);
    void werftBebauen(Bauer& bauer, Bauer& laub);
    void ferneInseln(Bauer& bauer);
    void booteBauen(Bauer& bauer);
    void regenbogenBauen(Bauer& bauer);
    void schattenFormen(Bauer& bauer);
    void schattenMerken(Vec3 ort, float radius);
    void turmBauen();

    void baum(Bauer& stamm, Bauer& laub, Vec3 fuss, float mass, Vec3 laubfarbe);
    void stand(Bauer& bauer, Vec3 fuss, float drehung, Vec3 stoff);
    void haus(Bauer& bauer, Vec3 fuss, float breite, float tiefe, float hoehe, float drehung,
              Vec3 wandfarbe, Vec3 dachfarbe);
    void zaun(Bauer& bauer, Vec3 von, Vec3 bis, Vec3 farbe);

    std::vector<Insel> inselListe;
    std::vector<Bruecke> brueckenListe;
    std::vector<Fundort> fundListe;
    std::vector<Tier> tierListe;
    Vec3 leuchtturm;
    Vec3 werkstatt;
    Vec3 bogenOrt;
    int turmStufe = 0;
    int detail = 2;
    unsigned saatwert = 7;

    Netz land;
    Netz bauten;
    Netz gruen;
    Netz wasser;
    Netz turm;
    Netz fern;
    Netz boote;
    Netz regenbogen;
    Netz schatten;
    std::vector<Vec3> schattenOrte;
};

}
