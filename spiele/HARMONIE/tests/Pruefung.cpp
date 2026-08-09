#include <cstdio>
#include <string>

#include "spiel/Welt.hpp"
#include "fw/Mathe.hpp"
#include "fw/Werkzeug.hpp"
#include "fw/Zufall.hpp"

namespace harmonie {
namespace {

int fehlerZahl = 0;
int pruefZahl = 0;

void pruefe(bool bedingung, const char* was) {
    pruefZahl += 1;
    if (!bedingung) {
        fehlerZahl += 1;
        std::printf("  [fehlt] %s\n", was);
    } else {
        std::printf("  [gut  ] %s\n", was);
    }
}

void mathePruefen() {
    using namespace fw;
    pruefe(std::fabs(klemme(5.0f, 0.0f, 1.0f) - 1.0f) < 1e-5f, "klemme begrenzt nach oben");
    pruefe(std::fabs(mische(0.0f, 10.0f, 0.25f) - 2.5f) < 1e-5f, "mische trifft die Mitte");
    Vec3 a(1.0f, 0.0f, 0.0f);
    Vec3 b(0.0f, 1.0f, 0.0f);
    pruefe(std::fabs(punkt(a, b)) < 1e-6f, "senkrechte Vektoren haben Punktprodukt null");
    pruefe(std::fabs(laenge(kreuz(a, b)) - 1.0f) < 1e-5f, "Kreuzprodukt zweier Einheiten ist eins");
    Mat4 dreh = drehungY(PI * 0.5f);
    Vec3 gedreht = wandle(dreh, Vec3(1.0f, 0.0f, 0.0f));
    pruefe(std::fabs(gedreht.z + 1.0f) < 1e-4f, "Drehung um Y schickt X nach minus Z");
    Mat4 kette = verschiebung(Vec3(2.0f, 3.0f, 4.0f)) * skalierung(Vec3(2.0f, 2.0f, 2.0f));
    Vec3 punktA = wandle(kette, Vec3(1.0f, 0.0f, 0.0f));
    pruefe(std::fabs(punktA.x - 4.0f) < 1e-4f && std::fabs(punktA.y - 3.0f) < 1e-4f,
           "Matrizen werden in der richtigen Reihenfolge verkettet");
}

void rauschenPruefen() {
    using namespace fw;
    float kleinster = 1.0f;
    float groesster = 0.0f;
    for (int i = 0; i < 400; ++i) {
        float wert = bergRauschen(static_cast<float>(i) * 0.31f, static_cast<float>(i) * 0.17f, 5);
        if (wert < kleinster) kleinster = wert;
        if (wert > groesster) groesster = wert;
    }
    pruefe(kleinster >= 0.0f && groesster <= 1.0f, "Rauschen bleibt zwischen null und eins");
    pruefe(groesster - kleinster > 0.2f, "Rauschen ist nicht flach");
    pruefe(std::fabs(wertRauschen(3.25f, 1.5f, 9) - wertRauschen(3.25f, 1.5f, 9)) < 1e-6f,
           "Rauschen liefert bei gleicher Stelle den gleichen Wert");
}

void weltPruefen() {
    Welt welt;
    welt.erzeugen(7);
    pruefe(welt.inseln().size() == 4, "Es gibt vier Inseln");
    pruefe(welt.bruecken().size() == 3, "Drei Bruecken verbinden die Herzinsel");

    Vec3 herz = welt.mittelpunkt(Bezirk::Herz);
    pruefe(herz.y > 1.0f, "Die Herzinsel ragt aus dem Wasser");
    pruefe(welt.aufLand(herz.x, herz.z), "Die Mitte der Herzinsel ist Land");
    pruefe(!welt.aufLand(0.0f, 140.0f), "Weit draussen ist kein Land");
    pruefe(welt.hoeheBei(0.0f, 140.0f) < 0.01f, "Offenes Meer hat Hoehe null");

    const Insel& berg = welt.insel(Bezirk::Berg);
    pruefe(welt.hoeheBei(berg.mitte.x, berg.mitte.y) > herz.y, "Der Berg ist hoeher als die Herzinsel");

    bool korn = false;
    bool stein = false;
    bool brett = false;
    bool alleAnLand = true;
    for (const Fundort& fund : welt.fundorte()) {
        if (fund.gabe == Gabe::Korn) korn = true;
        if (fund.gabe == Gabe::Stein) stein = true;
        if (fund.gabe == Gabe::Brett) brett = true;
        if (fund.ort.y < 0.3f) alleAnLand = false;
    }
    pruefe(korn && stein && brett, "Alle drei Gaben kommen vor");
    pruefe(alleAnLand, "Jeder Fundort liegt ueber dem Wasser");
    pruefe(welt.tiere().size() > 5, "Auf der Farm stehen Tiere");

    float hoehe = 0.0f;
    const Bruecke& bruecke = welt.bruecken().front();
    Vec3 mitte = (bruecke.von + bruecke.bis) * 0.5f;
    pruefe(welt.aufBruecke(mitte.x, mitte.z, hoehe), "Die Bruecke traegt in ihrer Mitte");
    pruefe(hoehe > 0.4f, "Die Bruecke liegt ueber dem Wasser");
    pruefe(welt.bodenBei(mitte.x, mitte.z) >= hoehe - 0.01f, "Der Boden folgt der Bruecke");

    Welt zweite;
    zweite.erzeugen(7);
    pruefe(std::fabs(zweite.hoeheBei(3.0f, 4.0f) - welt.hoeheBei(3.0f, 4.0f)) < 1e-5f,
           "Gleiche Saat ergibt die gleiche Welt");
}

void turmPruefen() {
    Welt welt;
    welt.erzeugen(7);
    pruefe(welt.leuchtturmStufe() == 0, "Der Leuchtturm faengt bei null an");
    welt.leuchtturmStufe(3);
    pruefe(welt.leuchtturmStufe() == 3, "Die Stufe laesst sich setzen");
    welt.leuchtturmStufe(99);
    pruefe(welt.leuchtturmStufe() == 6, "Die Stufe bleibt bei sechs stehen");
    welt.leuchtturmStufe(-4);
    pruefe(welt.leuchtturmStufe() == 0, "Negative Stufen werden abgefangen");
    Vec3 fuss = welt.leuchtturmFuss();
    pruefe(welt.aufLand(fuss.x, fuss.z), "Der Leuchtturm steht an Land");
}

void werkzeugPruefen() {
    std::vector<std::string> teile = fw::zerlegen("a,b,,c", ',');
    pruefe(teile.size() == 4, "Zerlegen behaelt leere Felder");
    pruefe(teile[2].empty(), "Das leere Feld bleibt leer");
    pruefe(fw::putzen("  hallo \r\n") == "hallo", "Putzen entfernt Rand");
    pruefe(fw::putzen("   ").empty(), "Nur Leerzeichen werden leer");
}

}

int pruefungenLaufen() {
    std::printf("HARMONIE Pruefungen\n");
    std::printf(" Mathematik\n");
    mathePruefen();
    std::printf(" Rauschen\n");
    rauschenPruefen();
    std::printf(" Welt\n");
    weltPruefen();
    std::printf(" Leuchtturm\n");
    turmPruefen();
    std::printf(" Werkzeug\n");
    werkzeugPruefen();
    std::printf("\n%d Pruefungen, %d Fehler\n", pruefZahl, fehlerZahl);
    return fehlerZahl == 0 ? 0 : 1;
}

}
