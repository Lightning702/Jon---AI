#include "Spiel.hpp"

#include <algorithm>

#include "fw/Protokoll.hpp"
#include "fw/Werkzeug.hpp"

namespace blockwelt {
namespace {

using namespace fw;

const unsigned char TASCHE[] = {GRAS, ERDE,  STEIN,      SAND,   SANDSTEIN, BRUCHSTEIN,
                                BRETT, ZIEGEL, GLAS,      STAMM,  LAUB,      SCHNEE,
                                KAKTUS, WASSER, ENDERPERLE, TNT};
constexpr int TASCHENZAHL = static_cast<int>(sizeof(TASCHE) / sizeof(TASCHE[0]));

const Bauwerk BAUWERKE[5] = {Bauwerk::Haus, Bauwerk::Turm, Bauwerk::Bruecke, Bauwerk::Baum,
                             Bauwerk::Leuchtfeuer};

constexpr float ZUENDZEIT = 2.6f;
constexpr float SPRENGWEITE = 3.4f;

std::string speicherPfad() { return ordnerNeben("saves\\blockwelt.txt"); }

}

bool Spiel::starten(const Startwerte& werte) {
    start = werte;
    tageszeit = werte.tageszeit;

    FensterWunsch wunsch;
    wunsch.titel = "Blockwelt - bauen mit Mini Jon";
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
    if (!atlas.erstellen()) {
        warnung("Der Texturatlas liess sich nicht anlegen");
        return false;
    }
    if (!schrift.erstellen("Segoe UI", 17, true)) warnung("Die Schrift liess sich nicht laden");

    const char* renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    std::string kennung = renderer ? renderer : "";
    int stufe = werte.qualitaet;
    if (stufe < 0) {
        stufe = 2;
        if (kennung.find("Intel") != std::string::npos || kennung.find("UHD") != std::string::npos ||
            kennung.find("HD Graphics") != std::string::npos) {
            stufe = 1;
        }
    }
    radius = stufe >= 2 ? 8 : (stufe == 1 ? 6 : 4);
    sichtweite = static_cast<float>(radius * CHUNK);

    ordnerAnlegen(ordnerNeben("saves"));
    welt.beginnen(werte.saat);
    if (!werte.frisch && welt.laden(speicherPfad())) {
        notiz("Gespeicherte Welt geladen, Saat %u, %zu Aenderungen", welt.saat(), welt.aenderungen());
    }

    jon.erstellen();
    {
        Bauer bauer;
        const float r = 0.503f;
        const Vec3 farbe(0.05f, 0.05f, 0.06f);
        const float d = 0.022f;
        for (int achse = 0; achse < 3; ++achse) {
            for (int i = 0; i < 4; ++i) {
                float a = (i & 1) ? r : -r;
                float b = (i & 2) ? r : -r;
                Vec3 halb = achse == 0 ? Vec3(r, d, d) : (achse == 1 ? Vec3(d, r, d) : Vec3(d, d, r));
                Vec3 mitte = achse == 0 ? Vec3(0.0f, a, b)
                                        : (achse == 1 ? Vec3(a, 0.0f, b) : Vec3(a, b, 0.0f));
                bauer.quader(mitte, halb, farbe);
            }
        }
        rahmen.hochladen(bauer);
    }
    {
        Bauer bauer;
        bauer.kugel(Vec3(0.0f, 0.0f, 0.0f), Vec3(0.16f, 0.16f, 0.16f), Vec3(0.16f, 0.72f, 0.62f), 8,
                    12, 0.6f);
        wuerfel.hochladen(bauer);
    }
    {
        Bauer bauer;
        const Vec3 hose(0.22f, 0.26f, 0.52f);
        const Vec3 hemd(0.24f, 0.62f, 0.48f);
        const Vec3 haut(0.92f, 0.74f, 0.58f);
        const Vec3 haar(0.28f, 0.2f, 0.16f);
        for (float sx : {-1.0f, 1.0f}) {
            bauer.quader(Vec3(sx * 0.13f, 0.35f, 0.0f), Vec3(0.11f, 0.35f, 0.12f), hose);
            bauer.quader(Vec3(sx * 0.38f, 1.05f, 0.0f), Vec3(0.11f, 0.32f, 0.12f), hemd);
            bauer.quader(Vec3(sx * 0.38f, 0.72f, 0.0f), Vec3(0.1f, 0.06f, 0.11f), haut);
        }
        bauer.quader(Vec3(0.0f, 1.05f, 0.0f), Vec3(0.26f, 0.36f, 0.14f), hemd);
        bauer.quader(Vec3(0.0f, 1.62f, 0.0f), Vec3(0.24f, 0.23f, 0.24f), haut);
        bauer.quader(Vec3(0.0f, 1.78f, 0.0f), Vec3(0.25f, 0.09f, 0.25f), haar);
        for (float sx : {-1.0f, 1.0f}) {
            bauer.quader(Vec3(sx * 0.1f, 1.66f, -0.24f), Vec3(0.05f, 0.05f, 0.02f),
                         Vec3(0.1f, 0.1f, 0.14f));
        }
        freundNetz.hochladen(bauer);
    }
    koop.anlegen("blockwelt", "Blockbauer");

    spielerAbsetzen();
    if (werte.blickGesetzt) spieler.blickSetzen(werte.gierung, werte.neigung);
    jon.setzen(spieler.auge() + Vec3(1.5f, 0.0f, 0.0f));

    if (werte.bilder == 0) {
        tonAn = ton.starten();
        if (tonAn) {
            ton.lautstaerke(0.35f);
            ton.stimmung(0.22f, 0.1f);
        }
        fenster.mausFangen(true);
    }
    anzeigeAn = !werte.ohneAnzeige;
    if (werte.schnellstart) einblendung = 0.0f;
    if (werte.sofortBau >= 0) bauwerkWaehlen(werte.sofortBau);
    if (!werte.koopWunsch.empty()) {
        if (werte.koopWunsch == "host") {
            koop.gastgeben(welt.saat(), spieler.fuesse());
        } else {
            koop.beitreten(werte.koopWunsch);
        }
        koopSchirm.oeffnen();
    }
    notiz("Welt bereit, Saat %u, Sichtweite %d Felder", welt.saat(), radius);
    return true;
}

void Spiel::spielerAbsetzen() {
    int x = 8;
    int z = 8;
    for (int versuch = 0; versuch < 64; ++versuch) {
        int h = hoeheAn(x, z, welt.saat());
        if (h > MEER + 1) break;
        x += 24;
        z += 13;
    }
    welt.umgebungPflegen(Vec3(static_cast<float>(x), 0.0f, static_cast<float>(z)), 1, 64, 0);
    int boden = welt.hoeheBei(x, z);
    spieler.setzen(Vec3(static_cast<float>(x) + 0.5f, static_cast<float>(boden + 2),
                        static_cast<float>(z) + 0.5f));
}

void Spiel::beenden() {
    koop.verlassen();
    koop.beenden();
    freundNetz.freigeben();
    welt.speichern(speicherPfad());
    ton.stoppen();
    jon.freigeben();
    rahmen.freigeben();
    wuerfel.freigeben();
    welt.freigeben();
    atlas.freigeben();
    schrift.freigeben();
    himmel.freigeben();
    maler.freigeben();
    fenster.schliessen();
}

void Spiel::meldungSetzen(const std::string& text, float dauer) {
    meldung = text;
    meldungZeit = dauer;
}

void Spiel::handWechseln(int schritt) {
    handFach = (handFach + schritt % TASCHENZAHL + TASCHENZAHL) % TASCHENZAHL;
    meldungSetzen(std::string("In der Hand: ") + blockart(TASCHE[handFach]).name, 1.4f);
}

void Spiel::bauwerkWaehlen(int nummer) {
    if (nummer < 0 || nummer > 4) return;
    jon.auftrag(BAUWERKE[nummer], welt, spieler.fuesse(), spieler.gierung());
    menueOffen = false;
    meldungSetzen(std::string("Mini Jon baut: ") + bauwerkName(BAUWERKE[nummer]), 3.0f);
    if (tonAn) ton.ereignis(Klang::Freude, 0.7f);
}

void Spiel::zuenden(int x, int y, int z) {
    for (const Zuender& z2 : zuender) {
        if (z2.x == x && z2.y == y && z2.z == z) return;
    }
    zuender.push_back({x, y, z, ZUENDZEIT});
    if (tonAn) ton.ereignis(Klang::Glocke, 0.5f);
}

void Spiel::sprengen(int x, int y, int z) {
    const int weite = static_cast<int>(SPRENGWEITE) + 1;
    for (int dy = -weite; dy <= weite; ++dy) {
        for (int dz = -weite; dz <= weite; ++dz) {
            for (int dx = -weite; dx <= weite; ++dx) {
                float abstand = std::sqrt(static_cast<float>(dx * dx + dy * dy + dz * dz));
                if (abstand > SPRENGWEITE) continue;
                int bx = x + dx;
                int by = y + dy;
                int bz = z + dz;
                unsigned char id = welt.block(bx, by, bz);
                if (id == LUFT || id == WASSER) continue;
                if (id == TNT && !(dx == 0 && dy == 0 && dz == 0)) {
                    zuenden(bx, by, bz);
                    continue;
                }
                welt.setzeBlock(bx, by, bz, LUFT);
            }
        }
    }
    blitz = 0.5f;
    if (tonAn) ton.ereignis(Klang::Hammer, 1.5f);
}

void Spiel::perleWerfen() {
    perle.ort = spieler.auge();
    perle.fahrt = normiert(spieler.blick()) * 24.0f;
    perle.alter = 0.0f;
    perle.fliegt = true;
    if (tonAn) ton.ereignis(Klang::Platsch, 0.6f);
    meldungSetzen("Enderperle geworfen", 1.6f);
}

void Spiel::eingabeLesen(float dt) {
    if (fenster.tasteGedrueckt(VK_ESCAPE)) {
        if (menueOffen) {
            menueOffen = false;
        } else if (fenster.mausGefangen()) {
            fenster.mausFangen(false);
        } else {
            fenster.schliessenAnfordern();
        }
    }
    if (fenster.tasteGedrueckt(VK_F11)) fenster.vollbildUmschalten();
    if (fenster.tasteGedrueckt('H')) anzeigeAn = !anzeigeAn;
    if (fenster.tasteGedrueckt(VK_F5) && radius > 3) {
        radius -= 1;
        sichtweite = static_cast<float>(radius * CHUNK);
        meldungSetzen("Sichtweite " + std::to_string(radius) + " Felder", 1.6f);
    }
    if (fenster.tasteGedrueckt(VK_F6) && radius < 12) {
        radius += 1;
        sichtweite = static_cast<float>(radius * CHUNK);
        meldungSetzen("Sichtweite " + std::to_string(radius) + " Felder", 1.6f);
    }
    if (fenster.tasteGedrueckt('P')) {
        bildschirmfoto(ordnerNeben("blockwelt-bild.bmp"), fenster.breite(), fenster.hoehe());
        meldungSetzen("Bild gespeichert");
    }
    if (fenster.tasteGedrueckt('F')) {
        spieler.fliegenUmschalten();
        meldungSetzen(spieler.fliegtGerade() ? "Flugmodus an" : "Flugmodus aus");
    }
    if (fenster.tasteGedrueckt('T') && !koopSchirm.offen()) {
        menueOffen = !menueOffen;
        if (menueOffen) meldungZeit = 0.0f;
    }
    if (fenster.tasteGedrueckt('K')) {
        koopSchirm.umschalten();
        if (koopSchirm.offen()) {
            fenster.mausFangen(false);
            menueOffen = false;
        }
    }
    if (koopSchirm.offen()) {
        Vec3 fuss = spieler.fuesse();
        koopSchirm.tasten(fenster, koop, welt.saat(), fuss);
        return;
    }
    if (einblendung > 0.0f && fenster.mausGedrueckt(Maustaste::Links)) einblendung = 0.0f;

    if (menueOffen) {
        for (int i = 0; i < 5; ++i) {
            if (fenster.tasteGedrueckt('1' + i)) bauwerkWaehlen(i);
        }
        return;
    }

    for (int i = 0; i < 9; ++i) {
        if (fenster.tasteGedrueckt('1' + i) && i < TASCHENZAHL) {
            handFach = i;
            meldungSetzen(std::string("In der Hand: ") + blockart(TASCHE[handFach]).name, 1.4f);
        }
    }
    float rad = fenster.radBewegung();
    if (rad > 0.0f) handWechseln(-1);
    if (rad < 0.0f) handWechseln(1);

    if (!fenster.mausGefangen()) {
        if (fenster.mausGedrueckt(Maustaste::Links)) fenster.mausFangen(true);
        return;
    }

    Vec2 bewegung = fenster.mausBewegung();
    spieler.umsehen(bewegung.x, bewegung.y);
    if (fenster.tasteGedrueckt(VK_SPACE)) spieler.springen();

    if (fenster.mausGedrueckt(Maustaste::Links) && ziel.getroffen) {
        if (ziel.block == TNT) {
            zuenden(ziel.x, ziel.y, ziel.z);
            meldungSetzen("TNT gezuendet", 1.8f);
        } else {
            welt.setzeBlock(ziel.x, ziel.y, ziel.z, LUFT);
            koop.blockSenden(ziel.x, ziel.y, ziel.z, LUFT, spieler.fuesse());
            if (tonAn) ton.ereignis(Klang::Hammer, 0.8f);
        }
    }
    if (fenster.mausGedrueckt(Maustaste::Rechts)) {
        unsigned char hand = TASCHE[handFach];
        if (hand == ENDERPERLE) {
            perleWerfen();
        } else if (ziel.getroffen) {
            Vec3 fuss = spieler.fuesse();
            bool imWeg = ziel.vorX == static_cast<int>(std::floor(fuss.x)) &&
                         ziel.vorZ == static_cast<int>(std::floor(fuss.z)) &&
                         (ziel.vorY == static_cast<int>(std::floor(fuss.y)) ||
                          ziel.vorY == static_cast<int>(std::floor(fuss.y + 1.0f)));
            if (!imWeg) {
                welt.setzeBlock(ziel.vorX, ziel.vorY, ziel.vorZ, hand);
                koop.blockSenden(ziel.vorX, ziel.vorY, ziel.vorZ, hand, spieler.fuesse());
                if (tonAn) ton.ereignis(Klang::Schritt, 0.6f);
            }
        }
    }
    (void)dt;
}

void Spiel::weltSchritt(float dt) {
    zeit += dt;
    tageszeit += dt / 420.0f;
    if (tageszeit > 1.0f) tageszeit -= 1.0f;
    if (meldungZeit > 0.0f) meldungZeit -= dt;
    if (blitz > 0.0f) blitz -= dt;
    if (einblendung > 0.0f) einblendung = klemme(einblendung - dt * 0.2f, 0.0f, 1.0f);

    spieler.schritt(dt, welt, fenster,
                    fenster.mausGefangen() && !menueOffen && !koopSchirm.offen());
    welt.umgebungPflegen(spieler.fuesse(), radius, 3, 2);
    koopSchritt(dt);
    jon.schritt(dt, welt, spieler.fuesse(), spieler.gierung());
    if (jon.hatGesetzt() && tonAn) ton.ereignis(Klang::Ernte, 0.35f);
    ziel = welt.strahl(spieler.auge(), spieler.blick(), 6.5f);

    for (size_t i = 0; i < zuender.size();) {
        zuender[i].rest -= dt;
        if (zuender[i].rest <= 0.0f) {
            Zuender kopie = zuender[i];
            zuender[i] = zuender.back();
            zuender.pop_back();
            sprengen(kopie.x, kopie.y, kopie.z);
            continue;
        }
        ++i;
    }

    if (perle.fliegt) {
        perle.alter += dt;
        perle.fahrt.y -= 18.0f * dt;
        Vec3 naechster = perle.ort + perle.fahrt * dt;
        int bx = static_cast<int>(std::floor(naechster.x));
        int by = static_cast<int>(std::floor(naechster.y));
        int bz = static_cast<int>(std::floor(naechster.z));
        if (welt.festBei(bx, by, bz) || perle.alter > 5.0f) {
            perle.fliegt = false;
            int landeY = by;
            while (landeY < HOEHE - 2 && welt.festBei(bx, landeY, bz)) ++landeY;
            spieler.setzen(Vec3(static_cast<float>(bx) + 0.5f, static_cast<float>(landeY),
                                static_cast<float>(bz) + 0.5f));
            if (tonAn) ton.ereignis(Klang::Freude, 0.9f);
            meldungSetzen("Hierher versetzt", 2.0f);
        } else {
            perle.ort = naechster;
        }
    }

    if (tonAn) {
        float nacht = klemme(1.0f - std::sin(tageszeit * TAU) * 1.4f, 0.0f, 1.0f);
        ton.stimmung(0.14f + nacht * 0.16f, spieler.imWasser() ? 0.5f : 0.06f);
    }

    sicherungsUhr -= dt;
    if (sicherungsUhr <= 0.0f) {
        sicherungsUhr = 60.0f;
        welt.speichern(speicherPfad());
    }
}

void Spiel::bildBauen() {
    glViewport(0, 0, fenster.breite(), fenster.hoehe());
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_DEPTH_TEST);
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);
    glFrontFace(GL_CCW);

    Vec3 auge = spieler.auge();
    Vec3 blick = normiert(spieler.blick());
    Vec3 rechts = normiert(kreuz(blick, Vec3(0.0f, 1.0f, 0.0f)));
    Vec3 oben = normiert(kreuz(rechts, blick));
    const float sichtfeld = bogen(74.0f);

    float sonnenWinkel = tageszeit * TAU;
    Vec3 sonne = normiert(Vec3(std::cos(sonnenWinkel) * 0.6f, std::sin(sonnenWinkel), 0.34f));
    float tag = klemme(sonne.y * 1.6f + 0.22f, 0.0f, 1.0f);

    himmel.zeichnen(blick, rechts, oben, sonne, tag, sichtfeld, fenster.seitenverhaeltnis());

    Mat4 sicht = blickRichtung(auge, auge + blick, Vec3(0.0f, 1.0f, 0.0f));
    Mat4 projektion = perspektive(sichtfeld, fenster.seitenverhaeltnis(), 0.08f, 520.0f);
    maler.beginnen(sicht, projektion, auge, zeit);

    float grelle = 1.0f + klemme(blitz, 0.0f, 1.0f) * 0.9f;
    Vec3 sonnenfarbe = mische(Vec3(0.22f, 0.24f, 0.34f), Vec3(1.12f, 0.98f, 0.8f), tag) * grelle;
    Vec3 himmelfarbe = mische(Vec3(0.1f, 0.12f, 0.2f), Vec3(0.5f, 0.62f, 0.82f), tag);
    Vec3 bodenfarbe = mische(Vec3(0.05f, 0.06f, 0.09f), Vec3(0.36f, 0.34f, 0.3f), tag);
    Vec3 nebelfarbe = mische(Vec3(0.08f, 0.09f, 0.14f), Vec3(0.78f, 0.83f, 0.88f), tag);
    Vec3 sonnenrichtung = sonne.y > 0.02f ? sonne : Vec3(-sonne.x, -sonne.y, -sonne.z) * 0.6f;
    maler.licht(sonnenrichtung, sonnenfarbe, himmelfarbe, bodenfarbe);
    maler.nebel(nebelfarbe, 1.35f / sichtweite, 0.0f, auge, sichtweite * 0.5f);

    maler.textur(atlas.kennung());
    welt.zeichnen(maler, auge, sichtweite);
    maler.textur(0);

    jon.zeichnen(maler, zeit);
    koopZeichnen();

    if (perle.fliegt) {
        maler.modell(verschiebung(perle.ort));
        maler.leuchten(0.7f);
        maler.zeichnen(wuerfel);
        maler.leuchten(0.0f);
        maler.modell(einheit());
    }

    if (ziel.getroffen) {
        Mat4 modell = verschiebung(Vec3(static_cast<float>(ziel.x) + 0.5f,
                                        static_cast<float>(ziel.y) + 0.5f,
                                        static_cast<float>(ziel.z) + 0.5f));
        maler.modell(modell);
        maler.leuchten(0.4f);
        maler.zeichnen(rahmen);
        maler.leuchten(0.0f);
        maler.modell(einheit());
    }

    for (const Zuender& z : zuender) {
        float puls = 0.5f + 0.5f * std::sin(z.rest * 22.0f);
        Mat4 modell = verschiebung(Vec3(static_cast<float>(z.x) + 0.5f, static_cast<float>(z.y) + 0.5f,
                                        static_cast<float>(z.z) + 0.5f)) *
                      skalierung(Vec3(1.06f, 1.06f, 1.06f));
        maler.modell(modell);
        maler.leuchten(0.4f + puls * 0.9f);
        maler.toenung(Vec3(1.0f, 0.5f, 0.4f));
        maler.zeichnen(rahmen);
        maler.toenung(Vec3(1.0f, 1.0f, 1.0f));
        maler.leuchten(0.0f);
        maler.modell(einheit());
    }

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDisable(GL_CULL_FACE);
    glDepthMask(GL_FALSE);
    maler.textur(atlas.kennung());
    maler.deckkraft(0.74f);
    maler.welle(0.05f, 0.55f);
    welt.zeichnenWasser(maler, auge, sichtweite);
    maler.welle(0.0f, 0.0f);
    maler.deckkraft(1.0f);
    maler.textur(0);
    glDepthMask(GL_TRUE);
    glEnable(GL_CULL_FACE);
    glDisable(GL_BLEND);

    anzeige();
}

void Spiel::anzeige() {
    if (!anzeigeAn) return;
    const float breite = static_cast<float>(fenster.breite());
    const float hoehe = static_cast<float>(fenster.hoehe());
    const float zeile = schrift.zeilenhoehe();
    schrift.beginnen(fenster.breite(), fenster.hoehe());

    const Farbe tinte(0.96f, 0.95f, 0.94f, 0.96f);
    const Farbe dunkel(0.05f, 0.05f, 0.07f, 0.55f);

    schrift.flaeche(breite * 0.5f - 8.0f, hoehe * 0.5f - 1.0f, 16.0f, 2.0f,
                    Farbe(1.0f, 1.0f, 1.0f, 0.65f));
    schrift.flaeche(breite * 0.5f - 1.0f, hoehe * 0.5f - 8.0f, 2.0f, 16.0f,
                    Farbe(1.0f, 1.0f, 1.0f, 0.65f));

    float feld = 34.0f;
    float abstand = 4.0f;
    float leiste = TASCHENZAHL * (feld + abstand) + 10.0f;
    if (leiste > breite - 40.0f) {
        feld = (breite - 60.0f) / TASCHENZAHL - abstand;
        leiste = TASCHENZAHL * (feld + abstand) + 10.0f;
    }
    float leisteX = breite * 0.5f - leiste * 0.5f;
    float leisteY = hoehe - feld - 26.0f;
    schrift.flaeche(leisteX, leisteY, leiste, feld + 14.0f, dunkel);
    for (int i = 0; i < TASCHENZAHL; ++i) {
        float x = leisteX + 7.0f + static_cast<float>(i) * (feld + abstand);
        Vec3 farbe = kachelfarbe(TASCHE[i]);
        schrift.flaeche(x, leisteY + 7.0f, feld, feld, Farbe(farbe, 0.96f));
        if (i == handFach) {
            schrift.rahmen(x - 3.0f, leisteY + 4.0f, feld + 6.0f, feld + 6.0f, 2.0f,
                           Farbe(0.98f, 0.86f, 0.42f, 0.95f));
        }
        if (i < 9) {
            schrift.text(x + 2.0f, leisteY + 6.0f, std::to_string(i + 1),
                         Farbe(0.08f, 0.08f, 0.1f, 0.85f), 0.66f);
        }
    }
    schrift.textMittig(breite * 0.5f, leisteY - zeile - 2.0f, blockart(TASCHE[handFach]).name, tinte,
                       0.9f);

    Vec3 fuss = spieler.fuesse();
    std::string kopf = welt.bezirkName(static_cast<int>(std::floor(fuss.x)),
                                       static_cast<int>(std::floor(fuss.z)));
    kopf += "   " + std::to_string(static_cast<int>(std::floor(fuss.x))) + " / " +
            std::to_string(static_cast<int>(std::floor(fuss.y))) + " / " +
            std::to_string(static_cast<int>(std::floor(fuss.z)));
    float kopfBreite = schrift.textBreite(kopf, 0.9f) + 24.0f;
    schrift.flaeche(16.0f, 16.0f, kopfBreite, zeile + 12.0f, dunkel);
    schrift.text(28.0f, 22.0f, kopf, tinte, 0.9f);

    std::string zweite = std::string("Mini Jon: ") + (jon.baut() ? "baut gerade" : "wartet auf T");
    float zweiteBreite = schrift.textBreite(zweite, 0.85f) + 24.0f;
    schrift.flaeche(16.0f, 16.0f + zeile + 16.0f, zweiteBreite, zeile + 10.0f, dunkel);
    schrift.text(28.0f, 20.0f + zeile + 16.0f, zweite, Farbe(0.86f, 0.85f, 0.84f, 0.9f), 0.85f);

    if (jon.spruchZeit() > 0.0f && !jon.spruch().empty()) {
        float w = schrift.textBreite(jon.spruch(), 0.95f) + 26.0f;
        float x = breite * 0.5f - w * 0.5f;
        float y = hoehe * 0.62f;
        float sicht = klemme(jon.spruchZeit(), 0.0f, 1.0f);
        schrift.flaeche(x, y, w, zeile + 14.0f, Farbe(0.05f, 0.05f, 0.07f, 0.6f * sicht));
        schrift.rahmen(x, y, w, zeile + 14.0f, 1.0f, Farbe(0.83f, 0.69f, 0.22f, 0.7f * sicht));
        schrift.textMittig(breite * 0.5f, y + 7.0f, jon.spruch(),
                           Farbe(0.98f, 0.92f, 0.76f, sicht), 0.95f);
    }

    if (meldungZeit > 0.0f && !meldung.empty()) {
        float sicht = klemme(meldungZeit, 0.0f, 1.0f);
        float w = schrift.textBreite(meldung, 0.9f) + 24.0f;
        float x = breite * 0.5f - w * 0.5f;
        float y = hoehe - feld - 88.0f;
        schrift.flaeche(x, y, w, zeile + 12.0f, Farbe(0.05f, 0.05f, 0.07f, 0.5f * sicht));
        schrift.textMittig(breite * 0.5f, y + 6.0f, meldung, Farbe(0.96f, 0.95f, 0.94f, sicht), 0.9f);
    }

    if (menueOffen) {
        const float w = 320.0f;
        const float h = zeile * 8.0f + 40.0f;
        float x = breite * 0.5f - w * 0.5f;
        float y = hoehe * 0.5f - h * 0.5f;
        schrift.flaeche(x, y, w, h, Farbe(0.05f, 0.05f, 0.07f, 0.86f));
        schrift.rahmen(x, y, w, h, 1.5f, Farbe(0.83f, 0.69f, 0.22f, 0.8f));
        schrift.textMittig(breite * 0.5f, y + 14.0f, "Was soll Mini Jon bauen?",
                           Farbe(0.98f, 0.92f, 0.76f, 1.0f), 1.0f);
        for (int i = 0; i < 5; ++i) {
            std::string eintrag = std::to_string(i + 1) + "   " + bauwerkName(BAUWERKE[i]);
            schrift.text(x + 34.0f, y + 44.0f + static_cast<float>(i) * zeile * 1.25f, eintrag, tinte,
                         0.95f);
        }
        schrift.textMittig(breite * 0.5f, y + h - zeile - 10.0f, "T oder Esc schliesst",
                           Farbe(0.8f, 0.79f, 0.78f, 0.8f), 0.82f);
    }

    if (einblendung > 0.0f) {
        float sicht = klemme(einblendung * 1.3f, 0.0f, 1.0f);
        schrift.flaeche(0.0f, 0.0f, breite, hoehe, Farbe(0.03f, 0.04f, 0.06f, sicht * 0.78f));
        schrift.textMittig(breite * 0.5f, hoehe * 0.3f, "Blockwelt",
                           Farbe(0.98f, 0.92f, 0.76f, sicht), 2.4f);
        schrift.textMittig(breite * 0.5f, hoehe * 0.3f + zeile * 2.8f, "Endlose Welt mit Mini Jon",
                           Farbe(0.9f, 0.88f, 0.86f, sicht), 1.1f);
        const char* zeilen[5] = {"Maus schauen  -  WASD laufen  -  Leertaste springen",
                                 "Links abbauen  -  Rechts setzen  -  1-9 und Mausrad waehlen",
                                 "TNT anklicken zuendet  -  Enderperle rechts wirft und versetzt",
                                 "T ruft Mini Jon  -  F Flugmodus  -  F5/F6 Sichtweite",
                                 "Klick ins Bild faengt die Maus"};
        for (int i = 0; i < 5; ++i) {
            schrift.textMittig(breite * 0.5f, hoehe * 0.55f + static_cast<float>(i) * zeile * 1.35f,
                               zeilen[i], Farbe(0.88f, 0.87f, 0.86f, sicht), 0.95f);
        }
    } else if (!fenster.mausGefangen()) {
        std::string text = "Klick ins Bild, dann faengt die Maus wieder";
        float w = schrift.textBreite(text, 0.9f) + 24.0f;
        schrift.flaeche(breite * 0.5f - w * 0.5f, hoehe * 0.5f + 40.0f, w, zeile + 12.0f, dunkel);
        schrift.textMittig(breite * 0.5f, hoehe * 0.5f + 46.0f, text, tinte, 0.9f);
    }

    koopSchirm.randzeile(schrift, koop, fenster.breite(), fenster.hoehe());
    koopSchirm.zeichnen(schrift, koop, fenster.breite(), fenster.hoehe());
    schrift.beenden();
}

void Spiel::koopSchritt(float dt) {
    fw::KoopZustand zustand;
    zustand.ort = spieler.fuesse();
    zustand.gierung = spieler.gierung();
    zustand.neigung = spieler.neigung();
    koop.eigenerZustand(zustand);
    koop.schritt(dt);
    koop.freundeBewegen(dt);

    if (koop.spielt() && koop.saat() != 0 && koop.saat() != koopSaat) {
        koopSaat = koop.saat();
        if (static_cast<unsigned>(koopSaat) != welt.saat()) {
            welt.beginnen(static_cast<unsigned>(koopSaat));
            welt.umgebungPflegen(spieler.fuesse(), 2, 128, 0);
            meldungSetzen("Welt des Gastgebers geladen", 3.0f);
        }
    }
    if (koop.startpunktFrisch()) {
        Vec3 punkt = koop.startpunkt();
        welt.umgebungPflegen(punkt, 2, 128, 0);
        int boden = welt.hoeheBei(static_cast<int>(std::floor(punkt.x)),
                                  static_cast<int>(std::floor(punkt.z)));
        if (punkt.y < static_cast<float>(boden)) punkt.y = static_cast<float>(boden + 2);
        spieler.setzen(punkt);
    }

    int bx = 0;
    int by = 0;
    int bz = 0;
    int block = 0;
    while (koop.blockHolen(bx, by, bz, block)) {
        if (block >= 0 && block < BLOCK_ANZAHL) welt.setzeBlock(bx, by, bz, static_cast<unsigned char>(block));
    }
    std::string zeile;
    while (koop.spruchHolen(zeile)) meldungSetzen(zeile, 4.0f);
    if (start.koopStarten && koop.stand() == KOOP_LOBBY && koop.gastgeber() &&
        koop.spielerzahl() >= 2) {
        koop.startBitten();
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
    for (const fw::KoopFreund& freund : koop.mitspieler()) {
        if (!freund.anwesend) continue;
        float wippen = std::fabs(std::sin(freund.schrittTakt)) * 0.06f;
        Mat4 modell = verschiebung(freund.zeigeOrt + Vec3(0.0f, wippen, 0.0f)) *
                      drehungY(freund.zeigeGierung);
        maler.modell(modell);
        maler.toenung(Vec3(1.0f, 0.94f, 0.9f));
        maler.zeichnen(freundNetz);
        maler.toenung(Vec3(1.0f, 1.0f, 1.0f));
    }
    maler.modell(einheit());
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
    notiz("Beendet nach %d Bildern, zuletzt %.1f Bilder je Sekunde, %zu Felder geladen", bildZaehler,
          bildrate, welt.felderZahl());
}

}
