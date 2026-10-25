#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "spiel/Fahrzeug.hpp"
#include "spiel/Geist.hpp"
#include "spiel/Pilot.hpp"
#include "spiel/Strecke.hpp"
#include "fw/Mathe.hpp"

namespace blitzbahn {
namespace {

using namespace fw;

int fehlerZahl = 0;
int pruefZahl = 0;

void pruefe(bool bedingung, const std::string& was) {
    pruefZahl += 1;
    if (!bedingung) {
        fehlerZahl += 1;
        std::printf("  [fehlt] %s\n", was.c_str());
    } else {
        std::printf("  [gut  ] %s\n", was.c_str());
    }
}

void drehungenPruefen() {
    for (int d = 0; d < 4; ++d) {
        Stueck s;
        s.x = 3;
        s.y = 2;
        s.z = -4;
        s.dreh = d;
        Vec3 lokal(2.5f, 1.0f, -6.0f);
        Vec3 zurueck = weltZuLokal(s, lokalZuWelt(s, lokal));
        pruefe(laenge(zurueck - lokal) < 1e-3f, "Drehung " + std::to_string(d) + " hin und zurueck");
    }
    pruefe(laenge(richtungWelt(1, Vec3(0, 0, 1)) - Vec3(1, 0, 0)) < 1e-4f, "Drehung 1 zeigt nach +x");
}

void flaechenPruefen() {
    bool drin = false;
    Vec3 n;
    float h = teilHoehe(RAMPE, 0.0f, 0.0f, drin, n);
    pruefe(drin && std::fabs(h - STUFE * 0.5f) < 1e-3f, "Rampe ist in der Mitte halb so hoch");
    pruefe(n.y > 0.9f && n.z < 0.0f, "Rampennormale zeigt nach oben und hinten");
    teilHoehe(GERADE, 8.0f, 0.0f, drin, n);
    pruefe(!drin, "Neben der Geraden ist kein Boden");
    teilHoehe(KURVE, 0.0f, -10.0f, drin, n);
    pruefe(drin, "Kurve beginnt mittig an der Einfahrt");
    teilHoehe(KURVE, 10.0f, 0.0f, drin, n);
    pruefe(drin, "Kurve endet mittig an der Ausfahrt");
    teilHoehe(KURVE, 9.0f, -9.0f, drin, n);
    pruefe(!drin, "Kurveninnenseite ist frei");
    float lippe = teilHoehe(SCHANZE, 0.0f, 9.99f, drin, n);
    pruefe(std::fabs(lippe - SCHANZE_HOEHE) < 0.05f, "Schanze endet in voller Hoehe");
}

void streckenPruefen() {
    std::vector<Strecke> liste = offizielleStrecken();
    pruefe(liste.size() == 8, "Acht offizielle Strecken gebaut (" + std::to_string(liste.size()) + ")");
    for (const Strecke& s : liste) {
        pruefe(s.hatStart() && s.hatZiel() && s.kontrollZahl() >= 1, s.name + " hat Start, Ziel und Kontrolle");
        Vec3 ort;
        float gier = 0.0f;
        s.startpunkt(ort, gier);
        Boden b = s.boden(ort + Vec3(0, 0.5f, 0), 0.6f);
        pruefe(b.da && std::fabs(b.hoehe - ort.y) < 0.01f, s.name + " Startplatz hat Boden");
    }
    Strecke a;
    streckeBauen("GGLGRHGTKZ", a);
    a.name = "Test Bahn";
    Strecke b;
    pruefe(Strecke::laden(a.speichern(), b) && b.stuecke.size() == a.stuecke.size() && b.name == a.name,
           "Speichern und Laden behaelt alle Teile");
    Strecke c;
    pruefe(Strecke::ausKompakt(a.kompakt(), c) && c.stuecke.size() == a.stuecke.size(), "Kurzform fuer Mitspieler ist verlustfrei");
    int gueltig = 0;
    for (unsigned saat = 1; saat <= 20; ++saat) {
        Strecke z = zufallsStrecke(saat, 24);
        if (z.hatStart() && z.hatZiel()) ++gueltig;
    }
    pruefe(gueltig == 20, "Zwanzig Zufallsstrecken sind fahrbereit");
}

void fahrPruefen() {
    Strecke s;
    streckeBauen("GGGGGGGGGGGGGGGGGGGGZ", s);
    Fahrzeug f;
    Vec3 ort;
    float gier = 0.0f;
    s.startpunkt(ort, gier);
    f.setzen(ort, gier);
    Eingabe e;
    e.gas = 1.0f;
    for (int i = 0; i < 120 * 5; ++i) f.schritt(s, e, 1.0f / 120.0f);
    float v = f.tempo();
    pruefe(v > 40.0f && v < 90.0f, "Nach 5 s Vollgas zwischen 144 und 324 km/h (" + std::to_string(static_cast<int>(v * 3.6f)) + ")");
    pruefe(f.amBoden && std::fabs(f.ort.y) < 0.05f, "Das Auto bleibt auf der Geraden am Boden");
    pruefe(std::fabs(f.ort.x) < 0.5f, "Geradeaus bleibt geradeaus");

    Fahrzeug tipp;
    tipp.setzen(ort, gier);
    Eingabe vollgas;
    vollgas.gas = 1.0f;
    for (int i = 0; i < 120 * 3; ++i) tipp.schritt(s, vollgas, 1.0f / 120.0f);
    float vorTipp = tipp.gier;
    Eingabe kurz = vollgas;
    kurz.lenkung = 1.0f;
    for (int i = 0; i < 30; ++i) tipp.schritt(s, kurz, 1.0f / 120.0f);
    for (int i = 0; i < 60; ++i) tipp.schritt(s, vollgas, 1.0f / 120.0f);
    float gedreht = std::fabs(winkelDifferenz(vorTipp, tipp.gier)) * 180.0f / PI;
    pruefe(gedreht > 1.0f && gedreht < 20.0f, "Kurzes Antippen von A dreht nur ein wenig (" + std::to_string(static_cast<int>(gedreht)) + " Grad)");

    Fahrzeug dauer;
    dauer.setzen(ort, gier);
    for (int i = 0; i < 120 * 3; ++i) dauer.schritt(s, vollgas, 1.0f / 120.0f);
    float start = dauer.gier;
    for (int i = 0; i < 120; ++i) dauer.schritt(s, kurz, 1.0f / 120.0f);
    float eineSekunde = std::fabs(winkelDifferenz(start, dauer.gier)) * 180.0f / PI;
    pruefe(eineSekunde < 80.0f, "Eine Sekunde Vollgas mit Lenkung dreht unter 80 Grad (" + std::to_string(static_cast<int>(eineSekunde)) + ")");

    Strecke platz;
    streckeBauen("PPPPPPPPPP", platz);
    Fahrzeug d;
    platz.startpunkt(ort, gier);
    d.setzen(ort, gier);
    for (int i = 0; i < 120 * 2; ++i) d.schritt(platz, vollgas, 1.0f / 120.0f);
    Eingabe rutsch = vollgas;
    rutsch.lenkung = 1.0f;
    rutsch.handbremse = true;
    bool quer = false;
    for (int i = 0; i < 90; ++i) {
        d.schritt(platz, rutsch, 1.0f / 120.0f);
        if (d.driftet) quer = true;
    }
    pruefe(quer && d.drift > 0.5f, "Leertaste mit Lenkung bringt das Auto ins Driften");

    Fahrzeug w;
    w.setzen(ort, gier);
    e.lenkung = 1.0f;
    for (int i = 0; i < 120 * 4; ++i) w.schritt(s, e, 1.0f / 120.0f);
    pruefe(std::fabs(w.ort.x) <= HALBE_BREITE - AUTO_RADIUS + 0.05f, "Die Wand haelt das Auto auf der Bahn");

    Strecke sprung;
    streckeBauen("SSSJ___GGGGGZ", sprung);
    Fahrzeug j;
    sprung.startpunkt(ort, gier);
    j.setzen(ort, gier);
    Eingabe g;
    g.gas = 1.0f;
    bool flog = false;
    bool gelandet = false;
    float hoechst = 0.0f;
    for (int i = 0; i < 120 * 8 && !gelandet; ++i) {
        j.schritt(sprung, g, 1.0f / 120.0f);
        if (!j.amBoden && j.luftzeit > 0.3f) flog = true;
        if (flog && j.amBoden && j.ort.y > -0.5f) gelandet = true;
        hoechst = std::max(hoechst, j.ort.y);
    }
    pruefe(flog && hoechst > SCHANZE_HOEHE + 1.0f, "Die Schanze laesst das Auto fliegen (bis " + std::to_string(static_cast<int>(hoechst)) + " m)");
    pruefe(gelandet, "Nach dem Sprung landet das Auto wieder auf der Bahn");
}

void pilotPruefen() {
    for (const Strecke& s : offizielleStrecken()) {
        Fahrzeug f;
        Pilot p;
        Vec3 ort;
        float gier = 0.0f;
        s.startpunkt(ort, gier);
        f.setzen(ort, gier);
        std::vector<int> erreicht;
        float uhr = 0.0f;
        bool ziel = false;
        int stuerze = 0;
        Vec3 kontrollOrt = ort;
        float kontrollGier = gier;
        while (uhr < 240.0f && !ziel) {
            Eingabe e = p.lenken(s, f);
            f.schritt(s, e, 1.0f / 120.0f);
            uhr += 1.0f / 120.0f;
            if (f.bodenStueck >= 0 && std::fabs(f.bodenLz) < 3.5f && f.ort.y - f.bodenHoehe < 9.0f) {
                if (f.bodenTeil == KONTROLLE && std::find(erreicht.begin(), erreicht.end(), f.bodenStueck) == erreicht.end()) {
                    erreicht.push_back(f.bodenStueck);
                    const Stueck& st = s.stuecke[f.bodenStueck];
                    kontrollOrt = lokalZuWelt(st, Vec3(0, 0, 0));
                    Vec3 v = richtungWelt(st.dreh, Vec3(0, 0, 1));
                    kontrollGier = std::atan2(v.x, v.z);
                }
                if (f.bodenTeil == ZIEL && static_cast<int>(erreicht.size()) >= s.kontrollZahl()) ziel = true;
            }
            if (f.ort.y < s.tiefstes() - 40.0f) {
                ++stuerze;
                f.setzen(kontrollOrt, kontrollGier);
            }
        }
        char text[160];
        std::snprintf(text, sizeof(text), "Autopilot schafft %s in %.1f s (%d Stuerze)", s.name.c_str(), uhr, stuerze);
        pruefe(ziel, text);
    }
}

void geistPruefen() {
    Geist g;
    for (int i = 0; i < 30; ++i) {
        Lage l;
        l.ort = Vec3(static_cast<float>(i), 0.0f, 0.0f);
        g.aufnehmen(l);
    }
    Geist h;
    int ms = 0;
    pruefe(Geist::laden(g.speichern(12345), h, ms) && ms == 12345, "Geist wird mit Zeit gespeichert");
    Lage mitte = h.bei(GEIST_TAKT * 10.5f);
    pruefe(std::fabs(mitte.ort.x - 10.5f) < 0.01f, "Geist wird zwischen Proben weich verschoben");
}

}

int pruefungenLaufen() {
    std::printf("BLITZBAHN Pruefungen\n");
    drehungenPruefen();
    flaechenPruefen();
    streckenPruefen();
    fahrPruefen();
    geistPruefen();
    pilotPruefen();
    std::printf("%d von %d Pruefungen bestanden\n", pruefZahl - fehlerZahl, pruefZahl);
    return fehlerZahl;
}

}
