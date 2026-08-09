#include "Spiel.hpp"

#include "fw/Protokoll.hpp"
#include "fw/Werkzeug.hpp"

namespace blockwelt {
namespace {

using namespace fw;

const unsigned char TASCHE[9] = {ERDE, GRAS, STEIN, BRETT, ZIEGEL, GLAS, SAND, LAUB, LEUCHTSTEIN};

const Bauwerk BAUWERKE[5] = {Bauwerk::Haus, Bauwerk::Turm, Bauwerk::Bruecke, Bauwerk::Baum,
                             Bauwerk::Leuchtfeuer};

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
    sichtweite = stufe >= 2 ? 110.0f : (stufe == 1 ? 78.0f : 52.0f);

    notiz("Welt wird erzeugt ...");
    welt.erzeugen(werte.saat);
    ordnerAnlegen(ordnerNeben("saves"));
    if (!werte.frisch && welt.laden(speicherPfad())) {
        notiz("Gespeicherte Welt geladen, %zu Aenderungen", welt.aenderungen());
    }
    welt.netzeBauen();
    notiz("Welt fertig: %d Felder", welt.chunkZahl());

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
                Vec3 mitte = achse == 0 ? Vec3(0.0f, a, b) : (achse == 1 ? Vec3(a, 0.0f, b)
                                                                        : Vec3(a, b, 0.0f));
                bauer.quader(mitte, halb, farbe);
            }
        }
        rahmen.hochladen(bauer);
    }

    int startX = WEITE / 2;
    int startZ = WEITE / 2;
    int startY = welt.hoeheBei(startX, startZ) + 2;
    spieler.setzen(Vec3(static_cast<float>(startX) + 0.5f, static_cast<float>(startY),
                        static_cast<float>(startZ) + 0.5f));
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
    hand = TASCHE[0];
    if (werte.sofortBau >= 0) bauwerkWaehlen(werte.sofortBau);
    return true;
}

void Spiel::beenden() {
    welt.speichern(speicherPfad());
    ton.stoppen();
    jon.freigeben();
    rahmen.freigeben();
    welt.freigeben();
    schrift.freigeben();
    himmel.freigeben();
    maler.freigeben();
    fenster.schliessen();
}

void Spiel::meldungSetzen(const std::string& text, float dauer) {
    meldung = text;
    meldungZeit = dauer;
}

void Spiel::bauwerkWaehlen(int nummer) {
    if (nummer < 0 || nummer > 4) return;
    jon.auftrag(BAUWERKE[nummer], welt, spieler.fuesse(), spieler.gierung());
    menueOffen = false;
    meldungSetzen(std::string("Mini Jon baut: ") + bauwerkName(BAUWERKE[nummer]), 3.0f);
    if (tonAn) ton.ereignis(Klang::Freude, 0.7f);
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
    if (fenster.tasteGedrueckt(VK_F5)) sichtweite = klemme(sichtweite - 16.0f, 40.0f, 160.0f);
    if (fenster.tasteGedrueckt(VK_F6)) sichtweite = klemme(sichtweite + 16.0f, 40.0f, 160.0f);
    if (fenster.tasteGedrueckt('P')) {
        bildschirmfoto(ordnerNeben("blockwelt-bild.bmp"), fenster.breite(), fenster.hoehe());
        meldungSetzen("Bild gespeichert");
    }
    if (fenster.tasteGedrueckt('F')) {
        spieler.fliegenUmschalten();
        meldungSetzen(spieler.fliegtGerade() ? "Flugmodus an" : "Flugmodus aus");
    }
    if (fenster.tasteGedrueckt('T')) {
        menueOffen = !menueOffen;
        if (menueOffen) meldungZeit = 0.0f;
    }
    if (einblendung > 0.0f && fenster.mausGedrueckt(Maustaste::Links)) einblendung = 0.0f;

    if (menueOffen) {
        for (int i = 0; i < 5; ++i) {
            if (fenster.tasteGedrueckt('1' + i)) bauwerkWaehlen(i);
        }
        return;
    }

    for (int i = 0; i < 9; ++i) {
        if (fenster.tasteGedrueckt('1' + i)) {
            handFach = i;
            hand = TASCHE[i];
            meldungSetzen(std::string("In der Hand: ") + blockart(hand).name, 1.4f);
        }
    }
    float rad = fenster.radBewegung();
    if (rad != 0.0f) {
        handFach = (handFach + (rad > 0.0f ? 8 : 1)) % 9;
        hand = TASCHE[handFach];
        meldungSetzen(std::string("In der Hand: ") + blockart(hand).name, 1.4f);
    }

    if (!fenster.mausGefangen()) {
        if (fenster.mausGedrueckt(Maustaste::Links)) fenster.mausFangen(true);
    } else {
        Vec2 bewegung = fenster.mausBewegung();
        spieler.umsehen(bewegung.x, bewegung.y);
        if (fenster.tasteGedrueckt(VK_SPACE)) spieler.springen();

        if (fenster.mausGedrueckt(Maustaste::Links) && ziel.getroffen) {
            welt.setzeBlock(ziel.x, ziel.y, ziel.z, LUFT);
            if (tonAn) ton.ereignis(Klang::Hammer, 0.8f);
        }
        if (fenster.mausGedrueckt(Maustaste::Rechts) && ziel.getroffen) {
            Vec3 fuss = spieler.fuesse();
            bool imWeg = ziel.vorX == static_cast<int>(std::floor(fuss.x)) &&
                         ziel.vorZ == static_cast<int>(std::floor(fuss.z)) &&
                         (ziel.vorY == static_cast<int>(std::floor(fuss.y)) ||
                          ziel.vorY == static_cast<int>(std::floor(fuss.y + 1.0f)));
            if (!imWeg) {
                welt.setzeBlock(ziel.vorX, ziel.vorY, ziel.vorZ, hand);
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
    if (einblendung > 0.0f) einblendung = klemme(einblendung - dt * 0.2f, 0.0f, 1.0f);

    spieler.schritt(dt, welt, fenster, fenster.mausGefangen() && !menueOffen);
    jon.schritt(dt, welt, spieler.fuesse(), spieler.gierung());
    if (jon.hatGesetzt() && tonAn) ton.ereignis(Klang::Ernte, 0.35f);
    welt.netzeAuffrischen();
    ziel = welt.strahl(spieler.auge(), spieler.blick(), 6.5f);

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
    Mat4 projektion = perspektive(sichtfeld, fenster.seitenverhaeltnis(), 0.08f, 400.0f);
    maler.beginnen(sicht, projektion, auge, zeit);

    Vec3 sonnenfarbe = mische(Vec3(0.22f, 0.24f, 0.34f), Vec3(1.08f, 0.94f, 0.76f), tag);
    Vec3 himmelfarbe = mische(Vec3(0.1f, 0.12f, 0.2f), Vec3(0.5f, 0.62f, 0.82f), tag);
    Vec3 bodenfarbe = mische(Vec3(0.05f, 0.06f, 0.09f), Vec3(0.36f, 0.34f, 0.3f), tag);
    Vec3 nebelfarbe = mische(Vec3(0.08f, 0.09f, 0.14f), Vec3(0.78f, 0.83f, 0.88f), tag);
    Vec3 sonnenrichtung = sonne.y > 0.02f ? sonne : Vec3(-sonne.x, -sonne.y, -sonne.z) * 0.6f;
    maler.licht(sonnenrichtung, sonnenfarbe, himmelfarbe, bodenfarbe);
    maler.nebel(nebelfarbe, 0.9f / sichtweite, 0.0f, auge, sichtweite * 0.55f);

    welt.zeichnen(maler, auge, sichtweite);
    jon.zeichnen(maler, zeit);

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

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDisable(GL_CULL_FACE);
    glDepthMask(GL_FALSE);
    maler.deckkraft(0.72f);
    maler.welle(0.055f, 0.55f);
    welt.zeichnenWasser(maler, auge, sichtweite);
    maler.welle(0.0f, 0.0f);
    maler.deckkraft(1.0f);
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

    const float feld = 40.0f;
    const float leiste = 9.0f * (feld + 6.0f) + 10.0f;
    float leisteX = breite * 0.5f - leiste * 0.5f;
    float leisteY = hoehe - feld - 26.0f;
    schrift.flaeche(leisteX, leisteY, leiste, feld + 16.0f, dunkel);
    for (int i = 0; i < 9; ++i) {
        float x = leisteX + 8.0f + static_cast<float>(i) * (feld + 6.0f);
        const Blockart& art = blockart(TASCHE[i]);
        schrift.flaeche(x, leisteY + 8.0f, feld, feld, Farbe(art.oben, 0.95f));
        if (i == handFach) {
            schrift.rahmen(x - 3.0f, leisteY + 5.0f, feld + 6.0f, feld + 6.0f, 2.0f,
                           Farbe(0.98f, 0.86f, 0.42f, 0.95f));
        }
        schrift.text(x + 3.0f, leisteY + 8.0f, std::to_string(i + 1), Farbe(0.1f, 0.1f, 0.12f, 0.8f),
                     0.7f);
    }
    std::string handText = blockart(hand).name;
    schrift.textMittig(breite * 0.5f, leisteY - zeile - 2.0f, handText, tinte, 0.9f);

    std::string kopf = std::string("Mini Jon: ") + (jon.baut() ? "baut gerade" : "wartet auf T");
    float kopfBreite = schrift.textBreite(kopf, 0.9f) + 24.0f;
    schrift.flaeche(16.0f, 16.0f, kopfBreite, zeile + 12.0f, dunkel);
    schrift.text(28.0f, 22.0f, kopf, tinte, 0.9f);

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
        float y = hoehe - feld - 84.0f;
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
        schrift.textMittig(breite * 0.5f, hoehe * 0.34f, "Blockwelt",
                           Farbe(0.98f, 0.92f, 0.76f, sicht), 2.4f);
        schrift.textMittig(breite * 0.5f, hoehe * 0.34f + zeile * 2.8f, "Bauen mit Mini Jon",
                           Farbe(0.9f, 0.88f, 0.86f, sicht), 1.1f);
        const char* zeilen[4] = {"Maus schauen  -  WASD laufen  -  Leertaste springen",
                                 "Links abbauen  -  Rechts setzen  -  1 bis 9 Block waehlen",
                                 "T ruft Mini Jon  -  F Flugmodus  -  Esc gibt die Maus frei",
                                 "Klick ins Bild faengt die Maus"};
        for (int i = 0; i < 4; ++i) {
            schrift.textMittig(breite * 0.5f, hoehe * 0.58f + static_cast<float>(i) * zeile * 1.35f,
                               zeilen[i], Farbe(0.88f, 0.87f, 0.86f, sicht), 0.95f);
        }
    } else if (!fenster.mausGefangen()) {
        std::string text = "Klick ins Bild, dann faengt die Maus wieder";
        float w = schrift.textBreite(text, 0.9f) + 24.0f;
        schrift.flaeche(breite * 0.5f - w * 0.5f, hoehe * 0.5f + 40.0f, w, zeile + 12.0f, dunkel);
        schrift.textMittig(breite * 0.5f, hoehe * 0.5f + 46.0f, text, tinte, 0.9f);
    }

    schrift.beenden();
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
