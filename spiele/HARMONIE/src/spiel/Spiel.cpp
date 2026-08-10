#include "Spiel.hpp"

#include <cstdio>

#include "Farben.hpp"
#include "fw/Protokoll.hpp"
#include "fw/Werkzeug.hpp"

namespace harmonie {
namespace {

using namespace fw;

constexpr int STUFEN = 6;

struct Auftrag {
    Gabe gabe;
    int menge;
};

const Auftrag AUFTRAEGE[STUFEN] = {{Gabe::Korn, 3},  {Gabe::Stein, 4}, {Gabe::Brett, 4},
                                   {Gabe::Korn, 5},  {Gabe::Stein, 5}, {Gabe::Brett, 6}};

const char* gabenName(Gabe gabe) {
    switch (gabe) {
        case Gabe::Korn: return "Korn";
        case Gabe::Stein: return "Stein";
        case Gabe::Brett: return "Brett";
        default: return "";
    }
}

Vec3 gabenFarbe(Gabe gabe) {
    switch (gabe) {
        case Gabe::Korn: return FARBE_KORN;
        case Gabe::Stein: return FARBE_FELS_HELL;
        case Gabe::Brett: return FARBE_HOLZ_HELL;
        default: return FARBE_SCHAUM;
    }
}

std::string bezirksName(const Welt& welt, Vec3 ort) {
    float beste = 1e9f;
    std::string name = "Offenes Meer";
    for (const Insel& stueck : welt.inseln()) {
        float dx = ort.x - stueck.mitte.x;
        float dz = ort.z - stueck.mitte.y;
        float abstand = std::sqrt(dx * dx + dz * dz) - stueck.radius;
        if (abstand < beste) {
            beste = abstand;
            if (abstand < 2.5f) name = stueck.name;
        }
    }
    return name;
}

}

bool Spiel::starten(const Startwerte& werte) {
    start = werte;
    FensterWunsch wunsch;
    wunsch.titel = "Harmonische Inseln - Vereinte Inseln";
    wunsch.breite = werte.breite;
    wunsch.hoehe = werte.hoehe;
    wunsch.vollbild = werte.vollbild;
    wunsch.vsync = werte.bilder == 0;
    if (!fenster.oeffnen(wunsch)) return false;

    if (!maler.erstellen()) {
        warnung("Der Weltshader liess sich nicht bauen");
        return false;
    }
    if (!himmel.erstellen()) {
        warnung("Der Himmelshader liess sich nicht bauen");
        return false;
    }
    if (!schrift.erstellen("Segoe UI", 17, true)) {
        warnung("Die Schrift liess sich nicht laden");
    }

    const char* renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    std::string kennung = renderer ? renderer : "";
    int gewuenscht = werte.qualitaet;
    if (gewuenscht < 0) {
        gewuenscht = 2;
        if (kennung.find("Intel") != std::string::npos || kennung.find("UHD") != std::string::npos ||
            kennung.find("HD Graphics") != std::string::npos) {
            gewuenscht = 1;
        }
    }
    qualitaetSetzen(gewuenscht);

    welt.detailStufe(qualitaet);
    welt.erzeugen(werte.saat);
    welt.netzeBauen();
    volk.erstellen(welt, werte.saat, qualitaet >= 2 ? 26 : 16);
    funken.erstellen();
    funken.grenze(qualitaet >= 2 ? 420 : 160);

    {
        Bauer bauer;
        Volk::gestaltBauen(bauer, FARBE_HAUT[0], FARBE_HAAR[4], FARBE_KLEID[0], 2, true);
        spielerNetz.hochladen(bauer);
    }
    for (int i = 0; i < 3; ++i) {
        Bauer bauer;
        Gabe gabe = i == 0 ? Gabe::Korn : (i == 1 ? Gabe::Stein : Gabe::Brett);
        if (gabe == Gabe::Korn) {
            bauer.kugel(Vec3(0.0f, 0.0f, 0.0f), Vec3(0.2f, 0.24f, 0.2f), FARBE_KORN, 6, 9);
        } else if (gabe == Gabe::Stein) {
            bauer.kugel(Vec3(0.0f, 0.0f, 0.0f), Vec3(0.22f, 0.18f, 0.2f), FARBE_FELS_HELL, 5, 7);
        } else {
            bauer.quader(Vec3(0.0f, 0.0f, 0.0f), Vec3(0.3f, 0.06f, 0.14f), FARBE_HOLZ_HELL);
        }
        gabenNetz[i].hochladen(bauer);
    }

    spielerOrt = welt.mittelpunkt(Bezirk::Herz) + Vec3(0.0f, 0.0f, 6.0f);
    spielerOrt.y = welt.bodenBei(spielerOrt.x, spielerOrt.z);
    kameraZiel = spielerOrt;

    auftragLesen();
    koop.anlegen("harmonie", "Inselfreund");
    laden();
    if (werte.ortGesetzt) {
        spielerOrt = Vec3(werte.ortX, welt.bodenBei(werte.ortX, werte.ortZ), werte.ortZ);
        kameraZiel = spielerOrt;
    }
    uebersicht = werte.uebersicht;
    anzeigeAn = !werte.ohneAnzeige;
    if (werte.stufe >= 0) {
        stufeErreicht = static_cast<int>(klemme(static_cast<float>(werte.stufe), 0.0f, 6.0f));
        stufeGebracht = 0;
        auftragLesen();
    }
    welt.leuchtturmStufe(stufeErreicht);

    if (werte.bilder == 0) {
        tonAn = ton.starten();
        if (tonAn) ton.lautstaerke(0.45f);
    }
    if (werte.schnellstart) einblendung = 0.0f;

    ordnerAnlegen(ordnerNeben("saves"));
    if (!werte.koopWunsch.empty()) {
        if (werte.koopWunsch == "host") {
            koop.gastgeben(werte.saat, spielerOrt);
        } else {
            koop.beitreten(werte.koopWunsch);
        }
        koopSchirm.oeffnen();
    }
    laeuft = true;
    notiz("Archipel bereit, Stufe %d, Qualitaet %d", stufeErreicht, qualitaet);
    return true;
}

void Spiel::qualitaetSetzen(int stufe) {
    qualitaet = static_cast<int>(klemme(static_cast<float>(stufe), 0.0f, 2.0f));
    funken.grenze(qualitaet >= 2 ? 420 : (qualitaet == 1 ? 200 : 60));
}

void Spiel::auftragLesen() {
    int stufe = static_cast<int>(klemme(static_cast<float>(stufeErreicht), 0.0f, STUFEN - 1.0f));
    stufeGabe = AUFTRAEGE[stufe].gabe;
    stufeBedarf = AUFTRAEGE[stufe].menge;
}

void Spiel::beenden() {
    koop.verlassen();
    koop.beenden();
    speichern();
    ton.stoppen();
    funken.freigeben();
    volk.freigeben();
    welt.freigeben();
    spielerNetz.freigeben();
    for (Netz& netz : gabenNetz) netz.freigeben();
    schrift.freigeben();
    himmel.freigeben();
    maler.freigeben();
    fenster.schliessen();
    laeuft = false;
}

Vec3 Spiel::kameraBlick() const {
    return normiert(Vec3(std::sin(kameraDrehung), 0.0f, std::cos(kameraDrehung)));
}

Vec3 Spiel::kameraRechts() const {
    Vec3 blick = kameraBlick();
    return normiert(Vec3(blick.z, 0.0f, -blick.x));
}

void Spiel::eingabeLesen(float dt) {
    if (koopSchirm.offen()) {
        koopSchirm.tasten(fenster, koop, start.saat, spielerOrt);
        if (fenster.tasteGedrueckt('K')) koopSchirm.umschalten();
        return;
    }
    if (fenster.tasteGedrueckt(VK_ESCAPE)) fenster.schliessenAnfordern();
    if (fenster.tasteGedrueckt(VK_F11)) fenster.vollbildUmschalten();
    if (fenster.tasteGedrueckt(VK_TAB)) uebersicht = !uebersicht;
    if (fenster.tasteGedrueckt('H')) anzeigeAn = !anzeigeAn;
    if (fenster.tasteGedrueckt(VK_F5)) qualitaetSetzen(qualitaet - 1);
    if (fenster.tasteGedrueckt(VK_F6)) qualitaetSetzen(qualitaet + 1);
    if (fenster.tasteGedrueckt('P')) {
        std::string ziel = ordnerNeben("harmonie-bild.bmp");
        bildschirmfoto(ziel, fenster.breite(), fenster.hoehe());
        meldung = "Bild gespeichert";
        meldungZeit = 2.5f;
    }
    if (einblendung > 0.0f) {
        for (int taste = 8; taste < 200; ++taste) {
            if (fenster.tasteGedrueckt(taste)) {
                einblendung = 0.0f;
                break;
            }
        }
    }

    if (fenster.taste('Q')) kameraDrehung -= dt * 1.5f;
    if (fenster.taste('R')) kameraDrehung += dt * 1.5f;
    if (fenster.taste(VK_LEFT)) kameraDrehung -= dt * 1.5f;
    if (fenster.taste(VK_RIGHT)) kameraDrehung += dt * 1.5f;
    if (fenster.taste(VK_UP)) kameraNeigung = klemme(kameraNeigung + dt * 0.7f, 0.35f, 1.15f);
    if (fenster.taste(VK_DOWN)) kameraNeigung = klemme(kameraNeigung - dt * 0.7f, 0.35f, 1.15f);
    wunschWeite = klemme(wunschWeite - fenster.radBewegung() * 3.4f, 12.0f, 62.0f);
    kameraWeite = mische(kameraWeite, uebersicht ? 86.0f : wunschWeite, klemme(dt * 4.0f, 0.0f, 1.0f));

    Vec3 vor = kameraBlick() * -1.0f;
    Vec3 quer = kameraRechts();
    Vec3 wunsch(0.0f, 0.0f, 0.0f);
    if (fenster.taste('W')) wunsch += vor;
    if (fenster.taste('S')) wunsch -= vor;
    if (fenster.taste('D')) wunsch += quer;
    if (fenster.taste('A')) wunsch -= quer;
    float schnell = fenster.taste(VK_SHIFT) ? 7.4f : 4.3f;
    if (laenge(wunsch) > 0.01f) {
        wunsch = normiert(wunsch);
        spielerRichtung += winkelDifferenz(spielerRichtung, std::atan2(wunsch.x, wunsch.z)) *
                           klemme(dt * 11.0f, 0.0f, 1.0f);
        spielerTakt += dt * schnell * 1.5f;
        Vec3 schritt = wunsch * (schnell * dt);
        Vec3 versuch = spielerOrt + schritt;
        if (welt.bodenBei(versuch.x, versuch.z) > 0.06f) {
            spielerOrt.x = versuch.x;
            spielerOrt.z = versuch.z;
        } else {
            Vec3 nurX(spielerOrt.x + schritt.x, 0.0f, spielerOrt.z);
            Vec3 nurZ(spielerOrt.x, 0.0f, spielerOrt.z + schritt.z);
            if (welt.bodenBei(nurX.x, nurX.z) > 0.06f) spielerOrt.x = nurX.x;
            else if (welt.bodenBei(nurZ.x, nurZ.z) > 0.06f) spielerOrt.z = nurZ.z;
        }
        if (tonAn && std::sin(spielerTakt * 2.2f) > 0.985f) ton.ereignis(Klang::Schritt, 0.35f);
    }

    if (fenster.tasteGedrueckt(VK_SPACE) && sprung <= 0.001f) {
        sprungKraft = 4.4f;
        if (tonAn) ton.ereignis(Klang::Schritt, 0.5f);
    }
    if (fenster.tasteGedrueckt('E')) {
        abliefern();
        sammeln();
    }
    if (fenster.tasteGedrueckt('F')) {
        schenken();
        gruessen();
    }
    if (fenster.tasteGedrueckt('K')) koopSchirm.umschalten();
}

void Spiel::sammeln() {
    if (getragenZahl >= 4) {
        meldung = "Die Arme sind voll";
        meldungZeit = 2.0f;
        return;
    }
    float besteWeite = 2.4f;
    Fundort* naechster = nullptr;
    for (Fundort& fund : welt.fundorte()) {
        if (fund.reife < 0.6f) continue;
        Vec3 nach = fund.ort - spielerOrt;
        nach.y = 0.0f;
        float weite = laenge(nach);
        if (weite < besteWeite) {
            besteWeite = weite;
            naechster = &fund;
        }
    }
    if (!naechster) return;
    naechster->reife = 0.0f;
    naechster->nachwachsen = 22.0f;
    getragen[getragenZahl] = naechster->gabe;
    getragenZahl += 1;
    funken.streuen(Funke::Glanz, naechster->ort + Vec3(0.0f, 0.5f, 0.0f), 12, 0.7f);
    if (tonAn) ton.ereignis(Klang::Ernte, 0.8f);
    meldung = std::string(gabenName(naechster->gabe)) + " eingesammelt";
    meldungZeit = 2.0f;
}

void Spiel::abliefern() {
    if (stufeErreicht >= STUFEN) return;
    Vec3 fuss = welt.leuchtturmFuss();
    Vec3 nach = fuss - spielerOrt;
    nach.y = 0.0f;
    if (laenge(nach) > 6.0f || getragenZahl == 0) return;
    int wert = 0;
    for (int i = 0; i < getragenZahl; ++i) wert += getragen[i] == stufeGabe ? 2 : 1;
    stufeGebracht += wert;
    koop.handlungSenden("signal", "liefer", static_cast<double>(wert), spielerOrt);
    getragenZahl = 0;
    for (Gabe& gabe : getragen) gabe = Gabe::Keine;
    funken.streuen(Funke::Glanz, fuss + Vec3(0.0f, 2.0f, 0.0f), 26, 1.3f);
    if (tonAn) ton.ereignis(Klang::Hammer, 1.0f);
    meldung = "Abgegeben, danke!";
    meldungZeit = 2.4f;
}

void Spiel::schenken() {
    Bewohner* person = volk.naechsterBewohner(spielerOrt, 3.0f);
    if (person == nullptr) return;
    if (person->wunsch == Gabe::Keine) {
        meldung = "Der Bewohner ist zufrieden";
        meldungZeit = 2.0f;
        return;
    }
    int fach = -1;
    for (int i = 0; i < getragenZahl; ++i) {
        if (getragen[i] == person->wunsch) {
            fach = i;
            break;
        }
    }
    if (fach < 0) {
        meldung = std::string("Gewuenscht wird: ") + gabenName(person->wunsch);
        meldungZeit = 2.6f;
        return;
    }
    for (int i = fach; i + 1 < getragenZahl; ++i) getragen[i] = getragen[i + 1];
    getragenZahl -= 1;
    getragen[getragenZahl] = Gabe::Keine;
    volk.wunschErfuellen(*person);
    herzen += 1;
    koop.handlungSenden("signal", "herz", 1.0, spielerOrt);
    funken.streuen(Funke::Herz, person->ort + Vec3(0.0f, 1.9f, 0.0f), 7, 0.7f);
    if (tonAn) ton.ereignis(Klang::Freude, 0.9f);
    meldung = "Geschenkt - ein Herz mehr";
    meldungZeit = 2.4f;
}

void Spiel::gruessen() {
    for (const Bewohner& person : volk.leute()) {
        Vec3 nach = person.ort - spielerOrt;
        nach.y = 0.0f;
        if (laenge(nach) < 2.6f) {
            funken.streuen(Funke::Herz, person.ort + Vec3(0.0f, 1.6f, 0.0f), 5, 0.6f);
            funken.streuen(Funke::Herz, spielerOrt + Vec3(0.0f, 1.6f, 0.0f), 3, 0.6f);
            if (tonAn) ton.ereignis(Klang::Freude, 0.7f);
            meldung = "Ihr winkt euch zu";
            meldungZeit = 2.0f;
            return;
        }
    }
}

void Spiel::weltSchritt(float dt) {
    zeit += dt;
    sonnenWinkel += dt * 0.006f;
    if (einblendung > 0.0f) einblendung = klemme(einblendung - dt * 0.16f, 0.0f, 1.0f);
    if (meldungZeit > 0.0f) meldungZeit -= dt;
    if (feierBlitz > 0.0f) feierBlitz -= dt;

    sprungKraft -= 14.0f * dt;
    sprung += sprungKraft * dt;
    if (sprung < 0.0f) {
        sprung = 0.0f;
        sprungKraft = 0.0f;
    }
    spielerOrt.y = welt.bodenBei(spielerOrt.x, spielerOrt.z);

    for (Fundort& fund : welt.fundorte()) {
        if (fund.reife >= 1.0f) continue;
        fund.nachwachsen -= dt;
        if (fund.nachwachsen <= 0.0f) fund.reife = 1.0f;
    }

    for (Tier& tier : welt.tiere()) {
        tier.takt += dt * 0.6f;
        tier.weideZiel -= dt;
        if (tier.weideZiel <= 0.0f) {
            tier.weideZiel = 3.0f + std::fabs(std::sin(tier.takt * 3.1f)) * 5.0f;
            tier.richtung += std::sin(tier.takt * 5.7f) * 1.4f;
        }
        Vec3 schritt(std::sin(tier.richtung) * 0.32f * dt, 0.0f, std::cos(tier.richtung) * 0.32f * dt);
        Vec3 versuch = tier.ort + schritt;
        if (welt.aufLand(versuch.x, versuch.z, 2.0f)) {
            tier.ort = versuch;
            tier.ort.y = welt.bodenBei(tier.ort.x, tier.ort.z);
        } else {
            tier.richtung += 1.9f;
        }
    }

    bool feiern = false;
    while (stufeErreicht < STUFEN && stufeGebracht >= stufeBedarf) {
        stufeGebracht -= stufeBedarf;
        stufeErreicht += 1;
        welt.leuchtturmStufe(stufeErreicht);
        auftragLesen();
        funken.streuen(Funke::Glanz, welt.leuchtturmFuss() + Vec3(0.0f, 4.0f, 0.0f), 60, 1.8f);
        if (tonAn) ton.ereignis(Klang::Glocke, 1.0f);
        feierBlitz = 1.6f;
        feiern = true;
        if (stufeErreicht >= STUFEN) {
            fest = true;
            festUhr = 0.0f;
            volk.feiernLassen(welt.leuchtturmFuss());
            meldung = "Der Leuchtturm brennt - die Inseln sind vereint";
            meldungZeit = 6.0f;
        } else {
            meldung = std::string("Stufe ") + std::to_string(stufeErreicht) + " steht";
            meldungZeit = 3.4f;
        }
        speichern();
    }
    if (fest) {
        festUhr += dt;
        regenbogen = klemme(regenbogen + dt * 0.2f, 0.0f, 1.6f);
        if (qualitaet >= 1) {
            static float feuerUhr = 0.0f;
            feuerUhr -= dt;
            if (feuerUhr <= 0.0f) {
                feuerUhr = 0.35f;
                Vec3 himmelOrt = welt.leuchtturmFuss() +
                                 Vec3(std::cos(zeit * 1.7f) * 9.0f, 12.0f + std::sin(zeit) * 3.0f,
                                      std::sin(zeit * 1.3f) * 9.0f);
                funken.streuen(Funke::Glanz, himmelOrt, 22, 1.6f);
            }
        }
    }

    volk.aktualisieren(dt, welt, spielerOrt, feiern);
    stufeGebracht += volk.lieferungenAbholen();
    koopSchritt(dt);

    funken.wind(Vec3(std::cos(zeit * 0.09f) * 0.5f, 0.0f, std::sin(zeit * 0.07f) * 0.4f));
    if (qualitaet >= 1) {
        static float blattUhr = 0.0f;
        blattUhr -= dt;
        if (blattUhr <= 0.0f) {
            blattUhr = qualitaet >= 2 ? 0.28f : 0.7f;
            const Insel& herz = welt.insel(Bezirk::Herz);
            float winkel = zeit * 1.7f;
            Vec3 ort(herz.mitte.x + std::cos(winkel) * 20.0f, 4.5f, herz.mitte.y + std::sin(winkel) * 20.0f);
            funken.streuen(Funke::Blatt, ort, 1);
            funken.streuen(Funke::Staub, spielerOrt + Vec3(std::sin(zeit) * 8.0f, 2.0f,
                                                           std::cos(zeit * 1.3f) * 8.0f),
                           1);
        }
        static float gischtUhr = 0.0f;
        gischtUhr -= dt;
        if (gischtUhr <= 0.0f) {
            gischtUhr = qualitaet >= 2 ? 0.22f : 0.6f;
            const Insel& stueck = welt.inseln()[(static_cast<int>(zeit * 3.0f)) % welt.inseln().size()];
            float winkel = zeit * 2.3f;
            Vec3 ort(stueck.mitte.x + std::cos(winkel) * stueck.radius * 1.02f, 0.15f,
                     stueck.mitte.y + std::sin(winkel) * stueck.radius * 1.02f);
            funken.streuen(Funke::Gischt, ort, 2, 0.6f);
        }
    }
    funken.aktualisieren(dt, zeit);

    Vec3 wunschZiel = spielerOrt;
    if (uebersicht) wunschZiel = Vec3(2.0f, 3.0f, 0.0f);
    kameraZiel = mische(kameraZiel, wunschZiel, klemme(dt * 4.5f, 0.0f, 1.0f));

    if (tonAn) {
        float naeheWasser = klemme(1.4f - spielerOrt.y * 0.2f, 0.2f, 1.0f);
        ton.stimmung(0.3f, naeheWasser * 0.55f);
    }
}

void Spiel::koopSchritt(float dt) {
    fw::KoopZustand zustand;
    zustand.ort = spielerOrt;
    zustand.gierung = spielerRichtung;
    koop.eigenerZustand(zustand);
    koop.schritt(dt);
    koop.freundeBewegen(dt);
    if (koop.startpunktFrisch()) {
        Vec3 punkt = koop.startpunkt();
        if (welt.bodenBei(punkt.x, punkt.z) > 0.1f) {
            spielerOrt = Vec3(punkt.x, welt.bodenBei(punkt.x, punkt.z), punkt.z);
            kameraZiel = spielerOrt;
        }
    }
    fw::KoopEreignis ereignis;
    while (koop.ereignisHolen(ereignis)) {
        if (ereignis.kennung == "liefer") {
            stufeGebracht += static_cast<int>(ereignis.wert);
            meldung = "Ein Mitspieler hat abgegeben";
            meldungZeit = 2.4f;
            funken.streuen(Funke::Glanz, welt.leuchtturmFuss() + Vec3(0.0f, 2.0f, 0.0f), 14, 1.0f);
        } else if (ereignis.kennung == "herz") {
            herzen += static_cast<int>(ereignis.wert);
        }
    }
    std::string zeile;
    while (koop.spruchHolen(zeile)) {
        meldung = zeile;
        meldungZeit = 4.0f;
    }
    static int letzterStand = -1;
    if (koop.stand() != letzterStand) {
        letzterStand = koop.stand();
        notiz("Koop: Stand %d, Code %s, Spieler %d, %s", letzterStand,
              koop.code().empty() ? "-" : koop.code().c_str(), koop.spielerzahl(),
              koop.fehler().empty() ? koop.hinweis().c_str() : koop.fehler().c_str());
    }
}

void Spiel::koopZeichnen() {
    if (!koop.aktiv()) return;
    int platz = 0;
    for (const fw::KoopFreund& freund : koop.mitspieler()) {
        platz += 1;
        if (!freund.anwesend) continue;
        float hub = std::fabs(std::sin(freund.schrittTakt)) * 0.09f;
        float stauchen = 1.0f - hub * 0.5f;
        Mat4 modell = verschiebung(freund.zeigeOrt + Vec3(0.0f, hub, 0.0f)) *
                      drehungY(freund.zeigeGierung) *
                      skalierung(Vec3(FIGUR_MASS / stauchen, FIGUR_MASS * stauchen,
                                      FIGUR_MASS / stauchen));
        maler.modell(modell);
        maler.zeichnen(volk.gestaltNetz(platz + 2));
    }
    maler.modell(einheit());
}

void Spiel::kameraSetzen() {
    float seite = fenster.seitenverhaeltnis();
    Vec3 richtung(std::sin(kameraDrehung) * std::cos(kameraNeigung), std::sin(kameraNeigung),
                  std::cos(kameraDrehung) * std::cos(kameraNeigung));
    Vec3 auge = kameraZiel + richtung * 150.0f;
    Mat4 sicht = blickRichtung(auge, kameraZiel, Vec3(0.0f, 1.0f, 0.0f));
    Mat4 projektion = orthogonal(-kameraWeite * seite, kameraWeite * seite, -kameraWeite,
                                 kameraWeite, 1.0f, 420.0f);
    maler.beginnen(sicht, projektion, auge, zeit);
    Vec3 sonne = normiert(Vec3(std::cos(sonnenWinkel), 0.46f, std::sin(sonnenWinkel)));
    Vec3 sonnenfarbe = Vec3(1.06f, 0.82f, 0.58f) * (1.0f + feierBlitz * 0.35f);
    maler.licht(sonne, sonnenfarbe, Vec3(0.52f, 0.62f, 0.78f), Vec3(0.36f, 0.34f, 0.3f));
    maler.nebel(Vec3(0.94f, 0.9f, 0.87f), uebersicht ? 0.009f : 0.013f, 0.012f, kameraZiel,
                uebersicht ? 90.0f : 46.0f);
}

void Spiel::bildBauen() {
    glViewport(0, 0, fenster.breite(), fenster.hoehe());
    glClearColor(0.62f, 0.72f, 0.82f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_DEPTH_TEST);
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);
    glFrontFace(GL_CCW);

    himmel.zeichnen(zeit, sonnenWinkel - kameraDrehung, regenbogen,
                    Vec2(static_cast<float>(fenster.breite()), static_cast<float>(fenster.hoehe())));

    kameraSetzen();

    maler.modell(einheit());
    maler.zeichnen(welt.fernNetz());
    maler.zeichnen(welt.landNetz());
    maler.zeichnen(welt.bautenNetz());
    maler.zeichnen(welt.gruenNetz());
    maler.zeichnen(welt.turmNetz());
    maler.zeichnen(welt.booteNetz());

    glDisable(GL_CULL_FACE);
    maler.welle(0.18f, 0.085f);
    maler.zeichnen(welt.wasserNetz());
    maler.welle(0.0f, 0.0f);

    if (regenbogen > 0.02f) {
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE);
        glDepthMask(GL_FALSE);
        maler.deckkraft(regenbogen * 0.16f);
        maler.leuchten(0.45f);
        maler.modell(verschiebung(welt.regenbogenOrt()) * drehungY(kameraDrehung));
        maler.zeichnen(welt.regenbogenNetz());
        maler.modell(einheit());
        maler.leuchten(0.0f);
        maler.deckkraft(1.0f);
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
    }
    glEnable(GL_CULL_FACE);

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDepthMask(GL_FALSE);
    maler.deckkraft(0.2f);
    maler.zeichnen(welt.schattenNetz());
    maler.deckkraft(1.0f);
    volk.zeichnenSchatten(maler, welt);
    maler.deckkraft(0.26f);
    Mat4 spielerSchatten = verschiebung(Vec3(spielerOrt.x, spielerOrt.y + 0.05f, spielerOrt.z)) *
                           skalierung(Vec3(0.46f * FIGUR_MASS, 1.0f, 0.34f * FIGUR_MASS));
    maler.modell(spielerSchatten);
    maler.zeichnen(volk.schattenNetz());
    maler.deckkraft(1.0f);
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);

    volk.zeichnenLeute(maler, zeit);
    volk.zeichnenTiere(maler, welt, zeit);
    koopZeichnen();

    float hub = std::fabs(std::sin(spielerTakt * 2.2f)) * 0.09f;
    float stauchen = 1.0f - hub * 0.5f;
    Mat4 spieler = verschiebung(spielerOrt + Vec3(0.0f, hub + sprung, 0.0f)) *
                   drehungY(spielerRichtung) *
                   skalierung(Vec3(FIGUR_MASS / stauchen, FIGUR_MASS * stauchen,
                                   FIGUR_MASS / stauchen));
    maler.modell(spieler);
    maler.zeichnen(spielerNetz);

    for (int i = 0; i < getragenZahl; ++i) {
        Gabe gabe = getragen[i];
        int index = gabe == Gabe::Korn ? 0 : (gabe == Gabe::Stein ? 1 : 2);
        Mat4 last = verschiebung(spielerOrt + Vec3(0.0f, 1.55f * FIGUR_MASS + hub + sprung +
                                                             static_cast<float>(i) * 0.26f, 0.0f)) *
                    drehungY(spielerRichtung + zeit * 0.6f);
        maler.modell(last);
        maler.zeichnen(gabenNetz[index]);
    }

    for (const Fundort& fund : welt.fundorte()) {
        if (fund.reife < 0.6f) continue;
        Vec3 nach = fund.ort - spielerOrt;
        nach.y = 0.0f;
        if (laenge(nach) > 3.4f) continue;
        int index = fund.gabe == Gabe::Korn ? 0 : (fund.gabe == Gabe::Stein ? 1 : 2);
        Mat4 zeiger = verschiebung(fund.ort + Vec3(0.0f, 1.2f + std::sin(zeit * 3.0f) * 0.12f, 0.0f)) *
                      drehungY(zeit * 1.4f);
        maler.modell(zeiger);
        maler.leuchten(0.35f);
        maler.zeichnen(gabenNetz[index]);
        maler.leuchten(0.0f);
    }

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDepthMask(GL_FALSE);
    glDisable(GL_CULL_FACE);
    Vec3 blick = kameraBlick();
    Vec3 rechts = kameraRechts();
    Vec3 oben = normiert(kreuz(rechts, blick * -1.0f));
    funken.zeichnen(maler, rechts, oben);
    glEnable(GL_CULL_FACE);
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);

    maler.modell(einheit());
    anzeige();
}

void Spiel::anzeige() {
    if (!anzeigeAn) return;
    const float breite = static_cast<float>(fenster.breite());
    const float hoehe = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    const float rand = 18.0f;
    const float zeile = schrift.zeilenhoehe();
    const Farbe tinte(0.16f, 0.12f, 0.16f, 0.95f);
    const Farbe blass(0.32f, 0.26f, 0.3f, 0.9f);
    const Farbe papier(1.0f, 0.98f, 0.97f, 0.82f);

    auto tafel = [&](float x, float y, float w, float h) {
        schrift.flaeche(x, y, w, h, papier);
        schrift.rahmen(x, y, w, h, 1.0f, Farbe(0.85f, 0.72f, 0.7f, 0.7f));
    };

    std::string ortsName = bezirksName(welt, spielerOrt);
    float kopfBreite = schrift.textBreite(ortsName) + 28.0f;
    if (kopfBreite < 150.0f) kopfBreite = 150.0f;
    tafel(rand, rand, kopfBreite, zeile + 14.0f);
    schrift.text(rand + 14.0f, rand + 7.0f, ortsName, tinte);

    const float punktGroesse = 13.0f;
    float leisteBreite = STUFEN * (punktGroesse + 6.0f) + 22.0f;
    float leisteX = breite - rand - leisteBreite;
    tafel(leisteX, rand, leisteBreite, punktGroesse + 20.0f);
    for (int i = 0; i < STUFEN; ++i) {
        float x = leisteX + 11.0f + static_cast<float>(i) * (punktGroesse + 6.0f);
        bool voll = i < stufeErreicht;
        Farbe farbe = voll ? Farbe(0.95f, 0.68f, 0.36f, 1.0f) : Farbe(0.7f, 0.66f, 0.64f, 0.45f);
        schrift.flaeche(x, rand + 10.0f, punktGroesse, punktGroesse, farbe);
    }

    std::string auftrag;
    if (fest) {
        auftrag = "Der Leuchtturm brennt - " + std::to_string(herzen) + " Herzen geschenkt";
    } else {
        auftrag = "Der Leuchtturm braucht " + std::to_string(stufeBedarf) + " x " +
                  gabenName(stufeGabe) + "   " + std::to_string(stufeGebracht) + " / " +
                  std::to_string(stufeBedarf);
    }
    float auftragBreite = schrift.textBreite(auftrag) + 30.0f;
    float auftragX = breite * 0.5f - auftragBreite * 0.5f;
    tafel(auftragX, rand, auftragBreite, zeile + 14.0f);
    schrift.text(auftragX + 15.0f, rand + 7.0f, auftrag, tinte);
    if (!fest) {
        float balken = auftragBreite - 30.0f;
        float anteil = klemme(static_cast<float>(stufeGebracht) / static_cast<float>(stufeBedarf),
                              0.0f, 1.0f);
        schrift.flaeche(auftragX + 15.0f, rand + zeile + 9.0f, balken, 3.0f,
                        Farbe(0.75f, 0.7f, 0.68f, 0.35f));
        schrift.flaeche(auftragX + 15.0f, rand + zeile + 9.0f, balken * anteil, 3.0f,
                        Farbe(0.95f, 0.68f, 0.36f, 0.95f));
    }

    std::string herzText = std::string("Herzen ") + std::to_string(herzen);
    float herzBreite = schrift.textBreite(herzText, 0.9f) + 26.0f;
    tafel(rand, rand + zeile + 22.0f, herzBreite, zeile + 12.0f);
    schrift.flaeche(rand + 10.0f, rand + zeile + 30.0f, 9.0f, 9.0f, Farbe(0.92f, 0.5f, 0.6f, 1.0f));
    schrift.text(rand + 25.0f, rand + zeile + 27.0f, herzText, tinte, 0.9f);

    if (getragenZahl > 0) {
        float feld = 22.0f;
        float w = getragenZahl * (feld + 6.0f) + 16.0f;
        float x = breite * 0.5f - w * 0.5f;
        float y = hoehe - rand - feld - 18.0f;
        tafel(x, y, w, feld + 16.0f);
        for (int i = 0; i < getragenZahl; ++i) {
            Vec3 farbe = gabenFarbe(getragen[i]);
            schrift.flaeche(x + 8.0f + static_cast<float>(i) * (feld + 6.0f), y + 8.0f, feld, feld,
                            Farbe(farbe, 1.0f));
        }
    }

    if (meldungZeit > 0.0f && !meldung.empty()) {
        float w = schrift.textBreite(meldung) + 30.0f;
        float x = breite * 0.5f - w * 0.5f;
        float y = hoehe - rand - 92.0f;
        float sicht = klemme(meldungZeit, 0.0f, 1.0f);
        schrift.flaeche(x, y, w, zeile + 14.0f, Farbe(1.0f, 0.98f, 0.97f, 0.8f * sicht));
        schrift.rahmen(x, y, w, zeile + 14.0f, 1.0f, Farbe(0.85f, 0.72f, 0.7f, 0.6f * sicht));
        schrift.textMittig(breite * 0.5f, y + 7.0f, meldung, Farbe(0.16f, 0.12f, 0.16f, sicht));
    }

    if (einblendung > 0.0f) {
        float sicht = klemme(einblendung * 1.4f, 0.0f, 1.0f);
        schrift.flaeche(0.0f, 0.0f, breite, hoehe, Farbe(1.0f, 0.96f, 0.94f, sicht * 0.72f));
        std::string titel = "Harmonische Inseln";
        std::string unter = "Vereinte Inseln";
        schrift.textMittig(breite * 0.5f, hoehe * 0.38f, titel, Farbe(0.24f, 0.16f, 0.2f, sicht), 2.1f);
        schrift.textMittig(breite * 0.5f, hoehe * 0.38f + zeile * 2.4f, unter,
                           Farbe(0.4f, 0.3f, 0.34f, sicht), 1.2f);
        schrift.textMittig(breite * 0.5f, hoehe * 0.62f,
                           "WASD laufen  -  E sammeln und abgeben  -  F gruessen",
                           Farbe(0.34f, 0.26f, 0.3f, sicht), 1.0f);
        schrift.textMittig(breite * 0.5f, hoehe * 0.62f + zeile * 1.4f,
                           "Q und R drehen  -  Mausrad naeher  -  Tab Uebersicht",
                           Farbe(0.34f, 0.26f, 0.3f, sicht), 1.0f);
    } else {
        std::string hinweis = "WASD laufen - E sammeln und abgeben - F schenken - K zusammen spielen";
        float w = schrift.textBreite(hinweis, 0.86f) + 22.0f;
        schrift.flaeche(breite * 0.5f - w * 0.5f, hoehe - rand - 26.0f, w, 22.0f,
                        Farbe(1.0f, 0.98f, 0.97f, 0.45f));
        schrift.textMittig(breite * 0.5f, hoehe - rand - 22.0f, hinweis, blass, 0.86f);
    }

    if (uebersicht) {
        for (const Insel& stueck : welt.inseln()) {
            (void)stueck;
        }
        std::string text = "Uebersicht";
        float w = schrift.textBreite(text) + 24.0f;
        tafel(breite * 0.5f - w * 0.5f, rand, w, zeile + 14.0f);
        schrift.textMittig(breite * 0.5f, rand + 7.0f, text, tinte);
    }

    if (fest && festUhr > 1.5f) {
        float sicht = klemme((festUhr - 1.5f) * 0.6f, 0.0f, 1.0f);
        std::string titel = "Die Inseln sind vereint";
        std::string unter = std::to_string(herzen) + " Herzen verschenkt";
        float w = schrift.textBreite(titel, 1.6f) + 60.0f;
        float h = zeile * 5.0f + 20.0f;
        float x = breite * 0.5f - w * 0.5f;
        float y = hoehe * 0.16f;
        schrift.flaeche(x, y, w, h, Farbe(1.0f, 0.98f, 0.97f, 0.78f * sicht));
        schrift.rahmen(x, y, w, h, 1.0f, Farbe(0.9f, 0.72f, 0.55f, 0.7f * sicht));
        schrift.textMittig(breite * 0.5f, y + 14.0f, titel, Farbe(0.24f, 0.16f, 0.2f, sicht), 1.6f);
        schrift.textMittig(breite * 0.5f, y + 16.0f + zeile * 2.0f, unter,
                           Farbe(0.4f, 0.3f, 0.34f, sicht), 1.0f);
        schrift.textMittig(breite * 0.5f, y + 16.0f + zeile * 3.3f,
                           "Bleib so lange du magst", Farbe(0.45f, 0.36f, 0.4f, sicht), 0.9f);
    }

    koopSchirm.randzeile(schrift, koop, fenster.breite(), fenster.hoehe());
    koopSchirm.zeichnen(schrift, koop, fenster.breite(), fenster.hoehe());
    schrift.beenden();
}

void Spiel::speichern() {
    char text[256];
    std::snprintf(text, sizeof(text), "fortschritt %d\nort %.2f %.2f\nsaat %u\n", fortschritt,
                  spielerOrt.x, spielerOrt.z, start.saat);
    schreibeText(ordnerNeben("saves\\harmonie.txt"), text);
}

void Spiel::laden() {
    std::string inhalt = leseText(ordnerNeben("saves\\harmonie.txt"));
    if (inhalt.empty()) return;
    float x = spielerOrt.x;
    float z = spielerOrt.z;
    for (const std::string& zeile : zerlegen(inhalt, '\n')) {
        std::string sauber = putzen(zeile);
        if (sauber.rfind("stufe", 0) == 0) {
            stufeErreicht = std::atoi(sauber.c_str() + 5);
        } else if (sauber.rfind("gebracht", 0) == 0) {
            stufeGebracht = std::atoi(sauber.c_str() + 8);
        } else if (sauber.rfind("herzen", 0) == 0) {
            herzen = std::atoi(sauber.c_str() + 6);
        } else if (sauber.rfind("ort", 0) == 0) {
            std::sscanf(sauber.c_str() + 3, "%f %f", &x, &z);
        }
    }
    stufeErreicht = static_cast<int>(klemme(static_cast<float>(stufeErreicht), 0.0f,
                                            static_cast<float>(STUFEN)));
    if (stufeGebracht < 0) stufeGebracht = 0;
    if (herzen < 0) herzen = 0;
    fest = stufeErreicht >= STUFEN;
    auftragLesen();
    if (welt.bodenBei(x, z) > 0.1f) {
        spielerOrt = Vec3(x, welt.bodenBei(x, z), z);
        kameraZiel = spielerOrt;
    }
}

void Spiel::laufen() {
    double letzte = jetzt();
    int bilder = 0;
    while (fenster.offen()) {
        fenster.ereignisse();
        double nun = jetzt();
        float dt = static_cast<float>(nun - letzte);
        letzte = nun;
        if (dt > 0.1f) dt = 0.1f;
        if (dt < 0.0001f) dt = 0.0001f;
        bildrate = mische(bildrate, 1.0f / dt, 0.05f);

        eingabeLesen(dt);
        weltSchritt(dt);
        bildBauen();
        fenster.zeigen();

        bilder += 1;
        bildZaehler = bilder;
        if (start.bilder > 0 && bilder >= start.bilder) {
            if (!start.bilddatei.empty()) {
                bildschirmfoto(start.bilddatei, fenster.breite(), fenster.hoehe());
            }
            break;
        }
    }
    notiz("Beendet nach %d Bildern, zuletzt %.1f Bilder je Sekunde", bildZaehler, bildrate);
}

}
