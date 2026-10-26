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

    Strecke offen;
    streckeBauen("PPPPPPPPPPPPPPPPPPPPPPPPPPPPPP", offen);
    Vec3 offenOrt;
    float offenGier = 0.0f;
    offen.startpunkt(offenOrt, offenGier);
    Fahrzeug tipp;
    tipp.setzen(offenOrt, offenGier);
    Eingabe vollgas;
    vollgas.gas = 1.0f;
    for (int i = 0; i < 120 * 3; ++i) tipp.schritt(offen, vollgas, 1.0f / 120.0f);
    float vorTipp = tipp.gier;
    Eingabe kurz = vollgas;
    kurz.lenkung = 1.0f;
    for (int i = 0; i < 30; ++i) tipp.schritt(offen, kurz, 1.0f / 120.0f);
    for (int i = 0; i < 60; ++i) tipp.schritt(offen, vollgas, 1.0f / 120.0f);
    float gedreht = std::fabs(winkelDifferenz(vorTipp, tipp.gier)) * 180.0f / PI;
    pruefe(gedreht > 1.0f && gedreht < 20.0f, "Kurzes Antippen von A dreht nur ein wenig (" + std::to_string(static_cast<int>(gedreht)) + " Grad)");

    Fahrzeug dauer;
    dauer.setzen(offenOrt, offenGier);
    for (int i = 0; i < 120 * 3; ++i) dauer.schritt(offen, vollgas, 1.0f / 120.0f);
    float start = dauer.gier;
    for (int i = 0; i < 120; ++i) dauer.schritt(offen, kurz, 1.0f / 120.0f);
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

    Fahrzeug kreis;
    platz.startpunkt(ort, gier);
    kreis.setzen(ort, gier);
    Eingabe halten;
    for (int i = 0; i < 120 * 6 && kreis.tempo() < 28.0f; ++i) kreis.schritt(platz, vollgas, 1.0f / 120.0f);
    halten.lenkung = 1.0f;
    for (int i = 0; i < 24; ++i) {
        halten.gas = kreis.tempo() < 28.0f ? 1.0f : 0.0f;
        kreis.schritt(platz, halten, 1.0f / 120.0f);
    }
    float kreisStart = kreis.gier;
    float kreisTempo = 0.0f;
    bool kreisAmBoden = true;
    for (int i = 0; i < 24; ++i) {
        halten.gas = kreis.tempo() < 28.0f ? 1.0f : 0.0f;
        kreis.schritt(platz, halten, 1.0f / 120.0f);
        kreisTempo += kreis.tempo() / 24.0f;
        kreisAmBoden = kreisAmBoden && kreis.amBoden;
    }
    float kreisRate = std::fabs(winkelDifferenz(kreisStart, kreis.gier)) / 0.2f;
    float kurvenRadius = kreisTempo / std::max(kreisRate, 1e-3f);
    pruefe(kreisAmBoden && kreisTempo > 25.0f && kurvenRadius < 11.0f, "Mit 100 km/h passt das Auto durch eine Kurve mit 10 m Radius (" + std::to_string(static_cast<int>(kurvenRadius)) + " m)");

    Fahrzeug schraeg;
    schraeg.setzen(ort, gier);
    for (int i = 0; i < 120 * 2; ++i) schraeg.schritt(s, vollgas, 1.0f / 120.0f);
    schraeg.ort.x = 3.2f;
    schraeg.gier = gier + 0.12f;
    schraeg.fahrt = schraeg.vorne() * 34.0f;
    float schraegStoss = 0.0f;
    for (int i = 0; i < 120 * 2; ++i) {
        schraeg.schritt(s, vollgas, 1.0f / 120.0f);
        schraegStoss = std::max(schraegStoss, schraeg.wandstoss);
    }
    pruefe(schraegStoss < 0.12f && std::fabs(winkelDifferenz(schraeg.gier, gier)) < 0.06f,
           "Fahrhilfe richtet das Auto vor der Leitplanke aus (Stoss " + std::to_string(static_cast<int>(schraegStoss * 100.0f)) + " %)");

    Fahrzeug anprall;
    anprall.setzen(ort, gier);
    for (int i = 0; i < 120 * 2; ++i) anprall.schritt(s, vollgas, 1.0f / 120.0f);
    anprall.ort.x = HALBE_BREITE - AUTO_RADIUS - 0.4f;
    anprall.gier = gier + 0.3f;
    anprall.fahrt = anprall.vorne() * 40.0f;
    for (int i = 0; i < 120; ++i) anprall.schritt(s, vollgas, 1.0f / 120.0f);
    float nachAnprall = anprall.vorwaerts();
    pruefe(nachAnprall > 34.0f, "Streifen der Wand kostet kaum Tempo (" + std::to_string(static_cast<int>(nachAnprall * 3.6f)) + " km/h)");
    pruefe(std::fabs(winkelDifferenz(anprall.gier, gier)) < 0.08f, "Nach dem Streifen zeigt das Auto die Bahn entlang");

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

    Strecke weit;
    streckeBauen("SSSJ____GGGGGZ", weit);
    Fahrzeug schief;
    weit.startpunkt(ort, gier);
    schief.setzen(ort, gier);
    for (int i = 0; i < 120 * 8; ++i) {
        schief.schritt(weit, g, 1.0f / 120.0f);
        if (schief.bodenTeil == SCHANZE && schief.bodenLz > 7.0f) break;
    }
    schief.gier = gier + 0.3f;
    float schiefC = std::cos(0.3f);
    float schiefS = std::sin(0.3f);
    schief.fahrt = Vec3(schief.fahrt.x * schiefC + schief.fahrt.z * schiefS, schief.fahrt.y, -schief.fahrt.x * schiefS + schief.fahrt.z * schiefC);
    bool schiefGelandet = false;
    for (int i = 0; i < 120 * 8 && !schiefGelandet; ++i) {
        schief.schritt(weit, g, 1.0f / 120.0f);
        if (schief.luftzeit == 0.0f && schief.bodenTeil == GERADE) schiefGelandet = true;
        if (schief.ort.y < weit.tiefstes() - 20.0f) break;
    }
    pruefe(schiefGelandet, "Wer schraeg ueber die Schanze faehrt, landet trotzdem auf der Bahn");
}

struct Fahrt {
    bool ziel = false;
    float zeit = 0.0f;
    int stuerze = 0;
    int wandkontakte = 0;
};

template <typename Fahrer>
Fahrt fahren(const Strecke& s, Fahrer fahrer) {
    Fahrt fahrt;
    Fahrzeug f;
    Vec3 ort;
    float gier = 0.0f;
    s.startpunkt(ort, gier);
    f.setzen(ort, gier);
    std::vector<int> erreicht;
    Vec3 kontrollOrt = ort;
    float kontrollGier = gier;
    bool anWand = false;
    while (fahrt.zeit < 240.0f && !fahrt.ziel) {
        f.schritt(s, fahrer(f), 1.0f / 120.0f);
        fahrt.zeit += 1.0f / 120.0f;
        if (f.wandstoss > 0.25f && !anWand) {
            ++fahrt.wandkontakte;
            anWand = true;
        }
        if (f.wandstoss < 0.05f) anWand = false;
        if (f.bodenStueck >= 0 && std::fabs(f.bodenLz) < 3.5f && f.ort.y - f.bodenHoehe < 9.0f) {
            if (f.bodenTeil == KONTROLLE && std::find(erreicht.begin(), erreicht.end(), f.bodenStueck) == erreicht.end()) {
                erreicht.push_back(f.bodenStueck);
                const Stueck& st = s.stuecke[f.bodenStueck];
                kontrollOrt = lokalZuWelt(st, Vec3(0, 0, 0));
                Vec3 v = richtungWelt(st.dreh, Vec3(0, 0, 1));
                kontrollGier = std::atan2(v.x, v.z);
            }
            if (f.bodenTeil == ZIEL && static_cast<int>(erreicht.size()) >= s.kontrollZahl()) fahrt.ziel = true;
        }
        if (f.ort.y < s.tiefstes() - 40.0f) {
            ++fahrt.stuerze;
            f.setzen(kontrollOrt, kontrollGier);
        }
    }
    return fahrt;
}

void tastaturPruefen() {
    int kontakte = 0;
    int geschafft = 0;
    for (const Strecke& s : offizielleStrecken()) {
        Pilot p;
        Fahrt fahrt = fahren(s, [&](const Fahrzeug& f) {
            Eingabe e = p.lenken(s, f);
            e.lenkung = std::fabs(e.lenkung) > 0.3f ? (e.lenkung > 0.0f ? 1.0f : -1.0f) : 0.0f;
            bool bremsen = e.bremse > 0.0f && f.vorwaerts() > 30.0f;
            e.bremse = bremsen ? 1.0f : 0.0f;
            e.gas = bremsen ? 0.0f : 1.0f;
            return e;
        });
        kontakte += fahrt.wandkontakte;
        geschafft += fahrt.ziel ? 1 : 0;
        std::printf("    Tastatur-Fahrer auf %s: %s in %.1f s, %d Wandkontakte, %d Stuerze\n", s.name.c_str(), fahrt.ziel ? "Ziel" : "kein Ziel", fahrt.zeit, fahrt.wandkontakte, fahrt.stuerze);
    }
    pruefe(geschafft == 8, "Tastatur-Fahrer mit spaetem Bremsen kommt auf allen Strecken ins Ziel (" + std::to_string(geschafft) + " von 8)");
    pruefe(kontakte <= 8, "Tastatur-Fahrer eckt selten an (" + std::to_string(kontakte) + " Wandkontakte auf 8 Strecken)");
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
    tastaturPruefen();
    std::printf("%d von %d Pruefungen bestanden\n", pruefZahl - fehlerZahl, pruefZahl);
    return fehlerZahl;
}

}
