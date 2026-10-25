#include "Spiel.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <sstream>

#include "fw/Protokoll.hpp"
#include "fw/Werkzeug.hpp"
#include "fw/Zufall.hpp"

namespace blitzbahn {

using namespace fw;

namespace {

constexpr int T_RUECK = 0x08;
constexpr int T_ENTER = 0x0D;
constexpr int T_SHIFT = 0x10;
constexpr int T_STRG = 0x11;
constexpr int T_ESC = 0x1B;
constexpr int T_LEER = 0x20;
constexpr int T_BILDAUF = 0x21;
constexpr int T_BILDAB = 0x22;
constexpr int T_LINKS = 0x25;
constexpr int T_HOCH = 0x26;
constexpr int T_RECHTS = 0x27;
constexpr int T_RUNTER = 0x28;
constexpr int T_ENTF = 0x2E;
constexpr int T_F5 = 0x74;
constexpr int T_F11 = 0x7A;
constexpr int T_MINUS = 0xBD;

constexpr float TICK = 1.0f / 120.0f;
constexpr float VORLAUF = 2.4f;

const Farbe HELL(0.96f, 0.97f, 1.0f);
const Farbe GEDAEMPFT(0.66f, 0.71f, 0.84f);
const Farbe GOLD(0.98f, 0.77f, 0.24f);
const Farbe GRUEN(0.38f, 0.92f, 0.52f);
const Farbe ROT(1.0f, 0.42f, 0.36f);
const Farbe TAFEL(0.06f, 0.08f, 0.15f, 0.9f);
const Farbe TAFEL_HELL(0.11f, 0.14f, 0.26f, 0.94f);

const Vec3 HORIZONT(0.66f, 0.8f, 0.93f);

const Vec3 PALETTE[] = {
    Vec3(0.86f, 0.62f, 0.12f), Vec3(0.92f, 0.2f, 0.16f), Vec3(0.95f, 0.45f, 0.1f), Vec3(0.98f, 0.86f, 0.2f),
    Vec3(0.3f, 0.78f, 0.25f),  Vec3(0.1f, 0.5f, 0.3f),   Vec3(0.12f, 0.7f, 0.78f), Vec3(0.16f, 0.36f, 0.86f),
    Vec3(0.08f, 0.12f, 0.32f), Vec3(0.5f, 0.24f, 0.78f), Vec3(0.9f, 0.32f, 0.62f), Vec3(0.94f, 0.94f, 0.96f),
    Vec3(0.55f, 0.57f, 0.62f), Vec3(0.25f, 0.26f, 0.3f), Vec3(0.06f, 0.06f, 0.08f), Vec3(0.45f, 0.3f, 0.18f),
};
constexpr int PALETTE_ZAHL = 16;

const Vec3 SPIELERFARBEN[] = {Vec3(0.3f, 0.75f, 1.0f), Vec3(1.0f, 0.45f, 0.4f), Vec3(0.5f, 1.0f, 0.5f),
                              Vec3(1.0f, 0.85f, 0.3f), Vec3(0.85f, 0.5f, 1.0f), Vec3(0.4f, 1.0f, 0.9f)};

std::string latin(const std::string& text) {
    std::string aus;
    aus.reserve(text.size());
    for (size_t i = 0; i < text.size(); ++i) {
        unsigned char c = static_cast<unsigned char>(text[i]);
        if (c == 0xC3 && i + 1 < text.size()) {
            unsigned char d = static_cast<unsigned char>(text[i + 1]);
            aus.push_back(static_cast<char>(d + 0x40));
            ++i;
        } else if (c == 0xC2 && i + 1 < text.size()) {
            aus.push_back(text[i + 1]);
            ++i;
        } else if (c == 0xE2 && i + 2 < text.size()) {
            unsigned char d = static_cast<unsigned char>(text[i + 2]);
            if (d == 0x93 || d == 0x94) aus.push_back('-');
            else if (d == 0xA6) aus += "...";
            else aus.push_back('-');
            i += 2;
        } else {
            aus.push_back(static_cast<char>(c));
        }
    }
    return aus;
}

std::string zeitText(int ms) {
    if (ms < 0) ms = 0;
    char text[32];
    std::snprintf(text, sizeof(text), "%d:%02d.%03d", ms / 60000, (ms / 1000) % 60, ms % 1000);
    return text;
}

std::string differenzText(int ms) {
    char text[32];
    int b = std::abs(ms);
    std::snprintf(text, sizeof(text), "%c%d.%03d", ms < 0 ? '-' : '+', b / 1000, b % 1000);
    return text;
}

std::string dateiname(const std::string& name) {
    std::string aus;
    for (char c : name) {
        unsigned char u = static_cast<unsigned char>(c);
        if (std::isalnum(u) || c == '-' || c == '_') aus.push_back(c);
        else if (c == ' ') aus.push_back('_');
    }
    if (aus.empty()) aus = "strecke";
    return aus.substr(0, 48);
}

std::string farbText(Vec3 f) {
    char text[64];
    std::snprintf(text, sizeof(text), "%.3f,%.3f,%.3f", f.x, f.y, f.z);
    return text;
}

Vec3 farbLesen(const std::string& text, Vec3 ersatz) {
    Vec3 f;
    if (std::sscanf(text.c_str(), "%f,%f,%f", &f.x, &f.y, &f.z) == 3) return f;
    return ersatz;
}

Vec3 nachVorn(const Mat4& m, Vec3 p, float& w) {
    float x = m.m[0] * p.x + m.m[4] * p.y + m.m[8] * p.z + m.m[12];
    float y = m.m[1] * p.x + m.m[5] * p.y + m.m[9] * p.z + m.m[13];
    float z = m.m[2] * p.x + m.m[6] * p.y + m.m[10] * p.z + m.m[14];
    w = m.m[3] * p.x + m.m[7] * p.y + m.m[11] * p.z + m.m[15];
    return Vec3(x, y, z);
}

}

bool Spiel::starten(const Startwerte& werte) {
    start = werte;
    FensterWunsch wunsch;
    wunsch.titel = "BLITZBAHN - FelWorks";
    wunsch.breite = werte.breite;
    wunsch.hoehe = werte.hoehe;
    wunsch.vollbild = werte.vollbild;
    wunsch.vsync = true;
    if (!fenster.oeffnen(wunsch)) return false;
    if (!maler.erstellen()) {
        warnung("Maler konnte nicht erstellt werden");
        return false;
    }
    if (!grafik.erstellen(2048)) {
        warnung("Grafik konnte nicht erstellt werden");
        return false;
    }
    schrift.erstellen("Bahnschrift", 21, true);
    gross.erstellen("Bahnschrift", 44, true);
    riesig.erstellen("Bahnschrift", 16, false);

    ordnerAnlegen(ordnerNeben("saves"));
    ordnerAnlegen(ordnerNeben("saves/strecken"));
    ordnerAnlegen(ordnerNeben("saves/geister"));
    profilLaden();
    rekordeLaden();
    offizielle = offizielleStrecken();
    eigeneLaden();
    notiz("%zu offizielle und %zu eigene Strecken geladen", offizielle.size(), eigene.size());

    Bauer b;
    Bauer c;
    Bauer d;
    himmelBauen(b, c, d, sonnenRichtung);
    himmelNetz.hochladen(b);
    wolkenNetz.hochladen(c);
    sonneNetz.hochladen(d);
    torBauen(b, c);
    torNetz.hochladen(b);
    tafelNetz.hochladen(c);
    schattenBauen(b);
    schattenNetz.hochladen(b);
    zeigerBauen(b);
    zeigerNetz.hochladen(b);
    b.leeren();
    b.roehre(Vec3(0.0f, -0.4f, 0.0f), 7.5f, 7.5f, 0.4f, Vec3(0.2f, 0.22f, 0.27f), 40);
    b.scheibe(Vec3(0.0f, 0.0f, 0.0f), 7.5f, Vec3(0.3f, 0.32f, 0.38f), 40);
    b.scheibe(Vec3(0.0f, 0.01f, 0.0f), 6.9f, Vec3(0.86f, 0.62f, 0.12f) * 0.5f, 40);
    b.scheibe(Vec3(0.0f, 0.02f, 0.0f), 6.6f, Vec3(0.24f, 0.26f, 0.31f), 40);
    bodenNetz.hochladen(b);
    autoNetzBauen();

    koop.anlegen("blitzbahn", profil.name);

    if (werte.bilder == 0) {
        tonAn = ton.starten();
        if (tonAn) {
            ton.lautstaerke(profil.lautstaerke);
            ton.stimmung(0.06f, 0.0f);
        }
    }

    const Strecke* gewaehlt = offizielle.empty() ? nullptr : &offizielle.front();
    if (!werte.strecke.empty()) {
        for (const Strecke& s : offizielle)
            if (s.kennung == werte.strecke) gewaehlt = &s;
        for (const Strecke& s : eigene)
            if (s.name == werte.strecke) gewaehlt = &s;
    }
    if (gewaehlt) {
        strecke = *gewaehlt;
        weltLaden(strecke);
        wagen.setzen(Vec3(), 0.0f);
        Vec3 ort;
        float gier = 0.0f;
        strecke.startpunkt(ort, gier);
        wagen.setzen(ort, gier);
        kameraOrt = ort + Vec3(0.0f, 30.0f, -40.0f);
        kameraZiel = ort;
        pilot.neu();
    }

    autopilotAn = werte.autopilot;
    if (werte.ansicht == "rennen" && gewaehlt) {
        rennenStarten(*gewaehlt, false);
    } else if (werte.ansicht == "editor") {
        editorStarten(gewaehlt ? *gewaehlt : Strecke());
    } else if (werte.ansicht == "garage") {
        ansichtWechseln(Ansicht::Garage);
    } else if (werte.ansicht == "auswahl") {
        ansichtWechseln(Ansicht::Auswahl);
    } else if (werte.ansicht == "mehrspieler") {
        ansichtWechseln(Ansicht::Mehrspieler);
    } else if (werte.ansicht == "einstellungen") {
        ansichtWechseln(Ansicht::Einstellungen);
    } else {
        ansichtWechseln(Ansicht::Haupt);
    }
    if (!werte.koopWunsch.empty()) {
        ansichtWechseln(Ansicht::Mehrspieler);
        if (werte.koopWunsch == "host") koop.gastgeben(4242ull, Vec3(0.0f, 0.0f, 0.0f));
        else koop.beitreten(werte.koopWunsch);
    }
    mausVorher = fenster.mausOrt();
    notiz("BLITZBAHN bereit");
    return true;
}

void Spiel::beenden() {
    if (tonAn) ton.motor(0.0f, 0.0f, 0.0f);
    koop.verlassen();
    koop.beenden();
    ton.stoppen();
    profilSpeichern();
    rekordeSpeichern();
    for (Netz* n : {&streckeNetz, &leuchtNetz, &landNetz, &baumNetz, &himmelNetz, &wolkenNetz, &sonneNetz, &torNetz,
                    &tafelNetz, &autoNetz, &glutNetz, &fremdNetz, &radNetz, &radBreitNetz, &schattenNetz, &gitterNetz,
                    &vorschauNetz, &vorschauLeucht, &zeigerNetz, &bodenNetz}) {
        n->freigeben();
    }
    for (Netz* n : {&wasserNetz, &teilchenNetz, &spurNetz}) n->freigeben();
    grafik.freigeben();
    schrift.freigeben();
    gross.freigeben();
    riesig.freigeben();
    maler.freigeben();
    fenster.schliessen();
}

void Spiel::laufen() {
    double letzte = jetzt();
    while (fenster.offen()) {
        fenster.ereignisse();
        double nun = jetzt();
        float dt = static_cast<float>(nun - letzte);
        letzte = nun;
        dt = klemme(dt, 0.0001f, 0.1f);
        zeit += dt;
        bild(dt);
        fenster.zeigen();
        bildZaehler += 1;
        if (start.bilder > 0 && bildZaehler >= start.bilder) {
            if (!start.bilddatei.empty()) bildschirmfoto(start.bilddatei, fenster.breite(), fenster.hoehe());
            break;
        }
    }
    notiz("Beendet nach %d Bildern", bildZaehler);
}

void Spiel::ansichtWechseln(Ansicht neu) {
    ansicht = neu;
    tippZiel = nullptr;
    pause = false;
    if (neu == Ansicht::Haupt || neu == Ansicht::Auswahl || neu == Ansicht::Einstellungen || neu == Ansicht::Mehrspieler) {
        if (!offizielle.empty() && strecke.stuecke.empty()) strecke = offizielle.front();
        if (geladeneWelt != schluesselVon(strecke) || strecke.stuecke.empty()) {
            if (!offizielle.empty() && (neu == Ansicht::Haupt)) strecke = offizielle.front();
            weltLaden(strecke);
        }
        Vec3 ort;
        float gier = 0.0f;
        strecke.startpunkt(ort, gier);
        wagen.setzen(ort, gier);
        pilot.neu();
        rennenLaeuft = false;
        rennenFertig = false;
    }
}

std::string Spiel::schluesselVon(const Strecke& s) const {
    if (!s.kennung.empty()) return s.kennung;
    return "e_" + dateiname(s.name);
}

std::string Spiel::geistPfad(const std::string& schluessel) const {
    return ordnerNeben("saves/geister/" + dateiname(schluessel) + ".geist");
}

void Spiel::profilLaden() {
    std::string text = leseText(ordnerNeben("saves/profil.txt"));
    std::istringstream ein(text);
    std::string zeile;
    while (std::getline(ein, zeile)) {
        if (!zeile.empty() && zeile.back() == '\r') zeile.pop_back();
        size_t gleich = zeile.find('=');
        if (gleich == std::string::npos) continue;
        std::string k = zeile.substr(0, gleich);
        std::string v = zeile.substr(gleich + 1);
        if (k == "name" && !v.empty()) profil.name = v.substr(0, 20);
        else if (k == "primaer") profil.farben.primaer = farbLesen(v, profil.farben.primaer);
        else if (k == "sekundaer") profil.farben.sekundaer = farbLesen(v, profil.farben.sekundaer);
        else if (k == "felgen") profil.farben.felgen = farbLesen(v, profil.farben.felgen);
        else if (k == "rahmen") profil.farben.rahmen = farbLesen(v, profil.farben.rahmen);
        else if (k == "lautstaerke") profil.lautstaerke = klemme(static_cast<float>(std::atof(v.c_str())), 0.0f, 1.0f);
        else if (k == "geist") profil.geist = v == "1";
        else if (k == "schatten") profil.schatten = v == "1";
        else if (k == "kamera") profil.kamera = std::atoi(v.c_str()) % 2;
    }
}

void Spiel::profilSpeichern() {
    std::ostringstream aus;
    aus << "name=" << profil.name << "\n";
    aus << "primaer=" << farbText(profil.farben.primaer) << "\n";
    aus << "sekundaer=" << farbText(profil.farben.sekundaer) << "\n";
    aus << "felgen=" << farbText(profil.farben.felgen) << "\n";
    aus << "rahmen=" << farbText(profil.farben.rahmen) << "\n";
    aus << "lautstaerke=" << profil.lautstaerke << "\n";
    aus << "geist=" << (profil.geist ? 1 : 0) << "\n";
    aus << "schatten=" << (profil.schatten ? 1 : 0) << "\n";
    aus << "kamera=" << profil.kamera << "\n";
    schreibeText(ordnerNeben("saves/profil.txt"), aus.str());
}

void Spiel::rekordeLaden() {
    rekorde.clear();
    std::istringstream ein(leseText(ordnerNeben("saves/rekorde.txt")));
    std::string k;
    int ms = 0;
    while (ein >> k >> ms) rekorde[k] = ms;
}

void Spiel::rekordeSpeichern() {
    std::ostringstream aus;
    for (const auto& [k, ms] : rekorde) aus << k << " " << ms << "\n";
    schreibeText(ordnerNeben("saves/rekorde.txt"), aus.str());
}

void Spiel::eigeneLaden() {
    eigene.clear();
    std::error_code fehler;
    std::filesystem::path ordner(ordnerNeben("saves/strecken"));
    if (!std::filesystem::exists(ordner, fehler)) return;
    for (const auto& eintrag : std::filesystem::directory_iterator(ordner, fehler)) {
        if (!eintrag.is_regular_file() || eintrag.path().extension() != ".bahn") continue;
        Strecke s;
        if (Strecke::laden(leseText(eintrag.path().string()), s)) eigene.push_back(s);
    }
    std::sort(eigene.begin(), eigene.end(), [](const Strecke& a, const Strecke& b) { return a.name < b.name; });
}

void Spiel::autoNetzBauen() {
    Bauer koerper;
    Bauer glut;
    autoBauen(profil.farben, koerper, glut);
    autoNetz.hochladen(koerper);
    glutNetz.hochladen(glut);
    Lackierung fremd;
    fremd.primaer = Vec3(0.92f, 0.92f, 0.95f);
    fremd.sekundaer = Vec3(0.55f, 0.58f, 0.66f);
    autoBauen(fremd, koerper, glut);
    fremdNetz.hochladen(koerper);
    Bauer rad;
    radBauen(rad, profil.farben.felgen, 0.34f);
    radNetz.hochladen(rad);
    radBauen(rad, profil.farben.felgen, 0.44f);
    radBreitNetz.hochladen(rad);
}

void Spiel::weltLaden(const Strecke& s) {
    Bauer fest;
    Bauer leucht;
    streckeBauen(s, fest, leucht);
    streckeNetz.hochladen(fest);
    leuchtNetz.hochladen(leucht);
    std::string schluessel = schluesselVon(s);
    unsigned saat = 7u;
    for (char c : schluessel) saat = saat * 31u + static_cast<unsigned char>(c);
    Bauer land;
    Bauer baeume;
    landschaftBauen(s, saat % 997u, land, baeume);
    landNetz.hochladen(land);
    baumNetz.hochladen(baeume);
    int x0 = 0, z0 = 0, x1 = 0, z1 = 0;
    s.grenzen(x0, z0, x1, z1);
    float flach = std::min(0.0f, s.tiefstes()) - 0.6f;
    float y = flach - 1.5f;
    float ax = (x0 - 2) * ZELLE - 1300.0f;
    float bx = (x1 + 2) * ZELLE + 1300.0f;
    float az = (z0 - 2) * ZELLE - 1300.0f;
    float bz = (z1 + 2) * ZELLE + 1300.0f;
    Bauer wasser;
    wasser.viereck(Vec3(ax, y, az), Vec3(ax, y, bz), Vec3(bx, y, bz), Vec3(bx, y, az), Vec3(0.2f, 0.4f, 0.45f), 0.9f);
    wasserNetz.hochladen(wasser);
    spuren.clear();
    spurZeiger = 0;
    spurAlt = true;
    teilchen.clear();
    geladeneWelt = schluessel;
}

void Spiel::himmelZeichnen(Vec3 auge) {
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glDisable(GL_CULL_FACE);
    grafik.stoff(STOFF_HIMMEL);
    grafik.modell(verschiebung(auge));
    grafik.zeichnen(himmelNetz);
    grafik.stoff(STOFF_WOLKE);
    grafik.modell(verschiebung(Vec3(auge.x * 0.85f, 0.0f, auge.z * 0.85f)));
    grafik.nebel(0.0f);
    grafik.zeichnen(wolkenNetz);
    grafik.nebel(0.00055f);
    grafik.stoff(STOFF_NORMAL);
    grafik.modell(einheit());
    glDepthMask(GL_TRUE);
    glEnable(GL_DEPTH_TEST);
}

void Spiel::autoSchatten(const Lage& lage, float rad, float lenk, bool eigenesNetz) {
    Mat4 basis = lageMatrix(lage);
    grafik.schattenModell(basis);
    grafik.schattenZeichnen(eigenesNetz ? autoNetz : fremdNetz);
    for (int i = 0; i < 4; ++i) {
        float x = (i % 2 == 0) ? -0.99f : 0.99f;
        float z = (i < 2) ? 1.45f : -1.45f;
        Mat4 m = basis * verschiebung(Vec3(x, RADRADIUS, z));
        if (i < 2) m = m * drehungY(lenk);
        grafik.schattenModell(m * drehungX(rad));
        grafik.schattenZeichnen(i < 2 ? radNetz : radBreitNetz);
    }
}

void Spiel::schattenPass(Vec3 mitte, bool mitAuto) {
    if (!profil.schatten || !grafik.schattenMoeglich()) return;
    grafik.schattenBeginnen(mitte, sonnenRichtung, 150.0f);
    grafik.schattenModell(einheit());
    grafik.schattenZeichnen(streckeNetz);
    grafik.schattenZeichnen(baumNetz);
    for (const Stueck& s : strecke.stuecke) {
        if (!teilIstTor(s.teil)) continue;
        grafik.schattenModell(verschiebung(lokalZuWelt(s, Vec3(0.0f, 0.0f, s.teil == START ? 2.0f : 0.0f))) * drehungY(s.dreh * PI * 0.5f));
        grafik.schattenZeichnen(torNetz);
    }
    if (mitAuto) autoSchatten(wagen.lage(), wagen.radDrehung, wagen.lenkwinkel, true);
    if (koop.aktiv()) {
        for (const KoopFreund& f : koop.mitspieler()) {
            if (!f.anwesend) continue;
            Lage l;
            l.ort = f.zeigeOrt;
            float c = std::cos(f.zeigeNeigung);
            l.vorne = Vec3(std::sin(f.zeigeGierung) * c, std::sin(f.zeigeNeigung), std::cos(f.zeigeGierung) * c);
            autoSchatten(l, zeit * 18.0f, 0.0f, false);
        }
    }
    grafik.schattenBeenden(fenster.breite(), fenster.hoehe());
}

void Spiel::spurSetzen(int rad, Vec3 punkt) {
    if (spurHat[rad] && laenge(punkt - spurLetzt[rad]) < 0.45f) return;
    if (spurHat[rad] && laenge(punkt - spurLetzt[rad]) < 4.0f) {
        Vec3 richtung = normiert(punkt - spurLetzt[rad]);
        Vec3 quer = normiert(kreuz(Vec3(0.0f, 1.0f, 0.0f), richtung)) * 0.17f;
        Vec3 ecken[4] = {spurLetzt[rad] - quer, spurLetzt[rad] + quer, punkt + quer, punkt - quer};
        const size_t grenze = 1800 * 4;
        if (spuren.size() < grenze) {
            for (const Vec3& e : ecken) spuren.push_back(e);
        } else {
            for (int i = 0; i < 4; ++i) spuren[(spurZeiger + i) % grenze] = ecken[i];
            spurZeiger = (spurZeiger + 4) % grenze;
        }
        spurAlt = true;
    }
    spurLetzt[rad] = punkt;
    spurHat[rad] = true;
}

void Spiel::teilchenPflegen(float dt) {
    Zufall z(static_cast<uint64_t>(zeit * 100000.0f) + 17ull);
    Mat4 basis = wagen.matrix();
    float v = wagen.tempo();
    teilchenUhr += dt;
    bool spawn = teilchenUhr > 1.0f / 60.0f;
    if (spawn) teilchenUhr = 0.0f;
    if (wagen.amBoden && (wagen.driftet || (eingabe.handbremse && v > 6.0f))) {
        for (int seite = 0; seite < 2; ++seite) {
            Vec3 p = wandle(basis, Vec3(seite == 0 ? -0.99f : 0.99f, 0.05f, -1.45f));
            spurSetzen(seite, p + wagen.obenVektor() * 0.03f);
            if (spawn && teilchen.size() < 600) {
                Teilchen t;
                t.ort = p + Vec3(z.bereich(-0.3f, 0.3f), 0.25f, z.bereich(-0.3f, 0.3f));
                t.fahrt = wagen.fahrt * 0.12f + Vec3(z.bereich(-1.0f, 1.0f), z.bereich(0.8f, 2.0f), z.bereich(-1.0f, 1.0f));
                t.farbe = Vec3(0.88f, 0.89f, 0.92f);
                t.dauer = z.bereich(0.9f, 1.5f);
                t.groesse = 0.6f;
                t.wachsen = 4.0f;
                t.deck = 0.38f;
                t.auftrieb = 0.6f;
                teilchen.push_back(t);
            }
        }
    } else {
        spurHat[0] = false;
        spurHat[1] = false;
    }
    if (wagen.schub > 0.4f && spawn) {
        for (int i = 0; i < 2 && teilchen.size() < 600; ++i) {
            Teilchen t;
            t.ort = wandle(basis, Vec3(z.bereich(-0.08f, 0.08f), 0.5f, -2.1f));
            t.fahrt = wagen.fahrt * 0.7f - wagen.vorne() * z.bereich(4.0f, 9.0f);
            t.farbe = mische(Vec3(2.2f, 1.1f, 0.3f), Vec3(1.6f, 0.4f, 0.1f), z.einheit());
            t.dauer = z.bereich(0.12f, 0.26f);
            t.groesse = 0.42f;
            t.wachsen = -0.6f;
            t.deck = 0.85f;
            teilchen.push_back(t);
        }
    }
    if (wagen.amBoden && warInLuft && wagen.aufprall > 6.0f) {
        for (int i = 0; i < 18 && teilchen.size() < 600; ++i) {
            Teilchen t;
            float w = z.bereich(0.0f, TAU);
            t.ort = wagen.ort + Vec3(std::cos(w) * 1.4f, 0.2f, std::sin(w) * 2.0f);
            t.fahrt = Vec3(std::cos(w) * z.bereich(2.0f, 6.0f), z.bereich(1.0f, 3.0f), std::sin(w) * z.bereich(2.0f, 6.0f)) + wagen.fahrt * 0.3f;
            t.farbe = Vec3(0.72f, 0.7f, 0.66f);
            t.dauer = z.bereich(0.6f, 1.1f);
            t.groesse = 0.9f;
            t.wachsen = 2.5f;
            t.deck = 0.42f;
            teilchen.push_back(t);
        }
    }
    warInLuft = !wagen.amBoden;
    if (wagen.wandstoss > 0.35f && spawn) {
        for (int i = 0; i < 5 && teilchen.size() < 600; ++i) {
            Teilchen t;
            t.ort = wagen.ort + Vec3(0.0f, 0.5f, 0.0f) + wagen.vorne() * 1.5f;
            t.fahrt = Vec3(z.bereich(-6.0f, 6.0f), z.bereich(2.0f, 7.0f), z.bereich(-6.0f, 6.0f)) + wagen.fahrt * 0.5f;
            t.farbe = Vec3(2.0f, 1.6f, 0.6f);
            t.dauer = z.bereich(0.2f, 0.45f);
            t.groesse = 0.12f;
            t.wachsen = 0.0f;
            t.deck = 1.0f;
            t.auftrieb = -18.0f;
            teilchen.push_back(t);
        }
    }
    for (Teilchen& t : teilchen) {
        t.alter += dt;
        t.ort += t.fahrt * dt;
        t.fahrt = t.fahrt * std::max(0.0f, 1.0f - dt * 1.6f);
        t.fahrt.y += t.auftrieb * dt;
    }
    teilchen.erase(std::remove_if(teilchen.begin(), teilchen.end(), [](const Teilchen& t) { return t.alter >= t.dauer; }), teilchen.end());
}

void Spiel::teilchenZeichnen() {
    spurUhr += 1.0f / 60.0f;
    if (spurAlt && !spuren.empty() && spurUhr > 0.1f) {
        Bauer b;
        for (size_t i = 0; i + 3 < spuren.size(); i += 4) {
            b.viereck(spuren[i], spuren[i + 1], spuren[i + 2], spuren[i + 3], Vec3(0.05f, 0.05f, 0.06f), 0.42f);
        }
        spurNetz.hochladen(b, true);
        spurAlt = false;
        spurUhr = 0.0f;
    }
    glDepthMask(GL_FALSE);
    grafik.stoff(STOFF_TEILCHEN);
    grafik.modell(einheit());
    if (!spuren.empty()) grafik.zeichnen(spurNetz);
    if (!teilchen.empty()) {
        Vec3 rechts(sichtMatrix.m[0], sichtMatrix.m[4], sichtMatrix.m[8]);
        Vec3 hoch(sichtMatrix.m[1], sichtMatrix.m[5], sichtMatrix.m[9]);
        Bauer b;
        for (const Teilchen& t : teilchen) {
            float u = t.alter / t.dauer;
            float g = std::max(0.05f, t.groesse * (1.0f + t.wachsen * u));
            float a = t.deck * (1.0f - u) * std::min(1.0f, t.alter * 12.0f);
            Vec3 r = rechts * g;
            Vec3 o = hoch * g;
            b.viereck(t.ort - r - o, t.ort + r - o, t.ort + r + o, t.ort - r + o, t.farbe, a);
        }
        teilchenNetz.hochladen(b, true);
        grafik.zeichnen(teilchenNetz);
    }
    grafik.stoff(STOFF_NORMAL);
    glDepthMask(GL_TRUE);
}

void Spiel::autoZeichnen(const Lage& lage, float rad, float lenk, float deckkraft, Vec3 toenung, float glut,
                         bool eigenesNetz) {
    Mat4 basis = lageMatrix(lage);
    grafik.deckkraft(deckkraft);
    grafik.toenung(toenung);
    grafik.stoff(STOFF_LACK);
    grafik.modell(basis);
    grafik.zeichnen(eigenesNetz ? autoNetz : fremdNetz);
    grafik.stoff(STOFF_NORMAL);
    const float rx = 0.99f;
    const float rz = 1.45f;
    for (int i = 0; i < 4; ++i) {
        float x = (i % 2 == 0) ? -rx : rx;
        float z = (i < 2) ? rz : -rz;
        Mat4 m = basis * verschiebung(Vec3(x, RADRADIUS, z));
        if (i < 2) m = m * drehungY(lenk);
        m = m * drehungX(rad);
        grafik.modell(m);
        grafik.zeichnen(i < 2 ? radNetz : radBreitNetz);
    }
    grafik.modell(basis);
    grafik.leuchten(0.8f + glut * 3.0f);
    grafik.zeichnen(glutNetz);
    grafik.leuchten(0.0f);
    grafik.toenung(Vec3(1.0f, 1.0f, 1.0f));
    grafik.deckkraft(1.0f);
    grafik.modell(einheit());
}

void Spiel::schattenZeichnen(const Fahrzeug& w) {
    if (profil.schatten && grafik.schattenMoeglich()) return;
    Boden b = strecke.boden(w.ort + Vec3(0.0f, 0.5f, 0.0f), 0.2f);
    if (!b.da) return;
    float hoehe = w.ort.y - b.hoehe;
    if (hoehe > 30.0f) return;
    Lage l;
    l.ort = Vec3(w.ort.x, b.hoehe + 0.04f, w.ort.z);
    Vec3 f(std::sin(w.gier), 0.0f, std::cos(w.gier));
    l.vorne = normiert(f - b.normale * punkt(f, b.normale));
    l.oben = b.normale;
    glDepthMask(GL_FALSE);
    grafik.deckkraft(0.42f * (1.0f - hoehe / 30.0f));
    grafik.modell(lageMatrix(l));
    grafik.zeichnen(schattenNetz);
    grafik.deckkraft(1.0f);
    grafik.modell(einheit());
    glDepthMask(GL_TRUE);
}

void Spiel::szeneZeichnen(const Mat4& sicht, const Mat4& projektion, Vec3 auge, bool mitTorFarben) {
    sichtMatrix = sicht;
    projMatrix = projektion;
    glViewport(0, 0, fenster.breite(), fenster.hoehe());
    glClearColor(HORIZONT.x, HORIZONT.y, HORIZONT.z, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    grafik.beginnen(sicht, projektion, auge, zeit, sonnenRichtung, profil.schatten);
    himmelZeichnen(auge);
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    grafik.stoff(STOFF_LAND);
    grafik.zeichnen(landNetz);
    grafik.stoff(STOFF_WASSER);
    grafik.zeichnen(wasserNetz);
    grafik.stoff(STOFF_NORMAL);
    grafik.zeichnen(baumNetz);
    grafik.stoff(STOFF_BAHN);
    grafik.zeichnen(streckeNetz);
    grafik.stoff(STOFF_NORMAL);
    grafik.leuchten(0.7f + 0.5f * std::sin(zeit * 7.0f));
    grafik.zeichnen(leuchtNetz);
    grafik.leuchten(0.0f);
    for (int i = 0; i < static_cast<int>(strecke.stuecke.size()); ++i) {
        const Stueck& s = strecke.stuecke[i];
        if (!teilIstTor(s.teil)) continue;
        Mat4 m = verschiebung(lokalZuWelt(s, Vec3(0.0f, 0.0f, s.teil == START ? 2.0f : 0.0f))) *
                 drehungY(s.dreh * PI * 0.5f);
        grafik.modell(m);
        Vec3 farbe(0.95f, 0.95f, 0.97f);
        if (s.teil == KONTROLLE) {
            bool ok = std::find(erreicht.begin(), erreicht.end(), i) != erreicht.end();
            farbe = (mitTorFarben && ok) ? Vec3(0.4f, 1.0f, 0.5f) : Vec3(1.0f, 0.8f, 0.25f);
        } else if (s.teil == START) {
            farbe = Vec3(0.5f, 0.8f, 1.0f);
        }
        grafik.toenung(farbe);
        grafik.zeichnen(torNetz);
        grafik.toenung(Vec3(1.0f, 1.0f, 1.0f));
        if (s.teil != KONTROLLE) grafik.zeichnen(tafelNetz);
    }
    grafik.modell(einheit());
}

void Spiel::rennenStarten(const Strecke& s, bool fahrtTest) {
    strecke = s;
    testfahrt = fahrtTest;
    if (geladeneWelt != schluesselVon(strecke) || fahrtTest) weltLaden(strecke);
    ansicht = Ansicht::Rennen;
    tippZiel = nullptr;
    std::string schluessel = schluesselVon(strecke);
    besterMs = rekorde.count(schluessel) ? rekorde[schluessel] : 0;
    bester.leeren();
    int geistMs = 0;
    if (!fahrtTest) {
        Geist g;
        if (Geist::laden(leseText(geistPfad(schluessel)), g, geistMs)) bester = g;
    }
    ergebnisse.clear();
    rennenNeu();
}

void Spiel::rennenNeu() {
    Vec3 ort;
    float gier = 0.0f;
    if (!strecke.startpunkt(ort, gier)) meldung("Diese Strecke hat noch keinen Start");
    wagen.setzen(ort, gier);
    kontrollOrt = ort;
    kontrollGier = gier;
    kontrollZeit = 0.0f;
    erreicht.clear();
    rennUhr = 0.0f;
    vorlauf = VORLAUF;
    rennenLaeuft = false;
    rennenFertig = false;
    pause = false;
    neuerRekord = false;
    zielMs = 0;
    aufnahme.leeren();
    aufnahmeTakt = 0;
    physikRest = 0.0f;
    pilot.neu();
    spuren.clear();
    spurZeiger = 0;
    spurAlt = true;
    teilchen.clear();
    spurHat[0] = false;
    spurHat[1] = false;
    letzterVorlaufTon = -1;
    Vec3 vorne(std::sin(gier), 0.0f, std::cos(gier));
    kameraOrt = ort - vorne * 9.0f + Vec3(0.0f, 3.5f, 0.0f);
    kameraZiel = ort + Vec3(0.0f, 1.0f, 0.0f);
}

void Spiel::zurKontrolle() {
    wagen.setzen(kontrollOrt, kontrollGier);
    if (tonAn) ton.ereignis(Klang::Platsch, 0.6f);
}

void Spiel::zielErreicht() {
    rennenFertig = true;
    rennenLaeuft = false;
    zielMs = static_cast<int>(std::lround(rennUhr * 1000.0f));
    std::string schluessel = schluesselVon(strecke);
    neuerRekord = !testfahrt && (besterMs == 0 || zielMs < besterMs);
    if (neuerRekord) {
        rekorde[schluessel] = zielMs;
        rekordeSpeichern();
        aufnahme.aufnehmen(wagen.lage());
        schreibeText(geistPfad(schluessel), aufnahme.speichern(zielMs));
    }
    if (tonAn) ton.ereignis(Klang::Freude, 1.0f);
    if (koop.spielt()) {
        koop.plaudern("#BB:ZEIT:" + std::to_string(zielMs));
    }
    notiz("Ziel auf %s in %s%s", strecke.name.c_str(), zeitText(zielMs).c_str(), neuerRekord ? " (Rekord)" : "");
}

void Spiel::physikTick(float dt) {
    Eingabe e = eingabe;
    if (!rennenLaeuft) {
        e.gas = 0.0f;
        e.bremse = 1.0f;
        e.lenkung = 0.0f;
    }
    if (vorlauf > 0.0f) {
        Vec3 ort = wagen.ort;
        float gier = wagen.gier;
        wagen.schritt(strecke, e, dt);
        wagen.ort = Vec3(ort.x, wagen.ort.y, ort.z);
        wagen.gier = gier;
        wagen.fahrt = Vec3(0.0f, 0.0f, 0.0f);
        return;
    }
    wagen.schritt(strecke, e, dt);
    if (!rennenLaeuft) return;
    rennUhr += dt;
    if (++aufnahmeTakt >= 4) {
        aufnahmeTakt = 0;
        aufnahme.aufnehmen(wagen.lage());
    }
    float ueber = wagen.ort.y - wagen.bodenHoehe;
    if (wagen.bodenStueck >= 0 && ueber < 9.0f && std::fabs(wagen.bodenLz) < 3.5f) {
        int teil = wagen.bodenTeil;
        if (teil == KONTROLLE && std::find(erreicht.begin(), erreicht.end(), wagen.bodenStueck) == erreicht.end()) {
            erreicht.push_back(wagen.bodenStueck);
            const Stueck& s = strecke.stuecke[wagen.bodenStueck];
            kontrollOrt = lokalZuWelt(s, Vec3(0.0f, 0.0f, 0.0f));
            Vec3 vorne = richtungWelt(s.dreh, Vec3(0.0f, 0.0f, 1.0f));
            float stueckGier = std::atan2(vorne.x, vorne.z);
            kontrollGier = std::fabs(winkelDifferenz(wagen.gier, stueckGier)) < PI * 0.5f ? stueckGier : stueckGier + PI;
            kontrollZeit = rennUhr;
            if (tonAn) ton.ereignis(Klang::Glocke, 0.8f);
        }
        if (teil == ZIEL && static_cast<int>(erreicht.size()) >= strecke.kontrollZahl()) zielErreicht();
    }
    if (wagen.ort.y < strecke.tiefstes() - 40.0f) zurKontrolle();
    if (wagen.aufprall > 9.0f && tonAn) ton.ereignis(Klang::Hammer, std::min(1.2f, wagen.aufprall / 20.0f));
    if (wagen.wandstoss > 0.3f) wackeln = std::max(wackeln, wagen.wandstoss * 0.4f);
}

void Spiel::rennenSchritt(float dt) {
    if (pause) return;
    bool tippt = tippZiel != nullptr;
    Eingabe e;
    if (!tippt) {
        bool gas = fenster.taste('W') || fenster.taste(T_HOCH);
        bool bremse = fenster.taste('S') || fenster.taste(T_RUNTER);
        float links = (fenster.taste('A') || fenster.taste(T_LINKS)) ? 1.0f : 0.0f;
        float rechts = (fenster.taste('D') || fenster.taste(T_RECHTS)) ? 1.0f : 0.0f;
        e.gas = gas ? 1.0f : 0.0f;
        e.bremse = bremse ? 1.0f : 0.0f;
        e.lenkung = links - rechts;
        e.handbremse = fenster.taste(T_LEER);
    }
    if (autopilotAn && rennenLaeuft) e = pilot.lenken(strecke, wagen);
    eingabe = e;
    if (vorlauf > 0.0f) {
        vorlauf -= dt;
        int sekunde = static_cast<int>(std::ceil(vorlauf / (VORLAUF / 3.0f)));
        if (sekunde != letzterVorlaufTon && sekunde >= 1 && sekunde <= 3) {
            letzterVorlaufTon = sekunde;
            if (tonAn) ton.ereignis(Klang::Ernte, 0.7f);
        }
        if (vorlauf <= 0.0f) {
            vorlauf = 0.0f;
            rennenLaeuft = true;
            if (tonAn) ton.ereignis(Klang::Glocke, 1.0f);
        }
    }
    physikRest += dt;
    int schritte = 0;
    while (physikRest >= TICK && schritte < 24) {
        physikTick(TICK);
        physikRest -= TICK;
        ++schritte;
        if (rennenFertig) break;
    }
    teilchenPflegen(dt);
    if (rennenFertig) {
        physikRest = 0.0f;
        if (wagen.amBoden || wagen.luftzeit < 0.5f) {
            Eingabe aus;
            aus.bremse = 0.6f;
            wagen.schritt(strecke, aus, std::min(dt, 1.0f / 30.0f));
        } else {
            wagen.fahrt = Vec3(0.0f, 0.0f, 0.0f);
        }
    }
}

void Spiel::kameraFuehren(float dt) {
    Lage l = wagen.lage();
    Vec3 flach = normiert(Vec3(l.vorne.x, 0.0f, l.vorne.z));
    float v = wagen.tempo();
    if (profil.kamera == 1) {
        Vec3 auge = l.ort + l.oben * 1.15f + l.vorne * 0.3f;
        kameraOrt = auge;
        kameraZiel = auge + l.vorne * 10.0f;
    } else {
        Vec3 wunsch = l.ort - flach * (7.6f + v * 0.025f) + Vec3(0.0f, 2.7f + v * 0.008f, 0.0f);
        float k = 1.0f - std::exp(-dt * 7.5f);
        kameraOrt = mische(kameraOrt, wunsch, k);
        Boden unter = strecke.boden(kameraOrt + Vec3(0.0f, 2.0f, 0.0f), 0.0f);
        if (unter.da && kameraOrt.y < unter.hoehe + 1.0f) kameraOrt.y = unter.hoehe + 1.0f;
        Vec3 blickZiel = l.ort + Vec3(0.0f, 1.1f, 0.0f) + flach * 2.0f;
        kameraZiel = mische(kameraZiel, blickZiel, 1.0f - std::exp(-dt * 14.0f));
    }
    float zielFeld = bogen(68.0f) + klemme(v / 90.0f, 0.0f, 1.0f) * bogen(18.0f) + (wagen.schub > 0.0f ? bogen(4.0f) : 0.0f);
    sichtfeld = mische(sichtfeld, zielFeld, 1.0f - std::exp(-dt * 3.0f));
    wackeln = std::max(0.0f, wackeln - dt * 2.0f);
}

void Spiel::tonPflegen(float dt) {
    (void)dt;
    if (!tonAn) return;
    if (ansicht != Ansicht::Rennen || pause) {
        ton.motor(0.0f, 0.0f, ansicht == Ansicht::Haupt ? 0.25f : 0.0f);
        return;
    }
    float v = std::fabs(wagen.vorwaerts());
    static const float gaenge[] = {0.0f, 14.0f, 27.0f, 40.0f, 54.0f, 70.0f, 200.0f};
    float drehzahl = 0.25f;
    for (int i = 0; i < 6; ++i) {
        if (v < gaenge[i + 1]) {
            drehzahl = 0.28f + 0.72f * (v - gaenge[i]) / (gaenge[i + 1] - gaenge[i]);
            break;
        }
    }
    if (vorlauf > 0.0f) drehzahl = 0.3f + (eingabe.gas > 0.0f ? 0.5f : 0.0f);
    if (!wagen.amBoden) drehzahl = std::min(1.1f, drehzahl + eingabe.gas * 0.3f);
    ton.motor(drehzahl, eingabe.gas, 0.85f);
}

void Spiel::bild(float dt) {
    Vec2 maus = fenster.mausOrt();
    if (fenster.tasteGedrueckt(T_F11)) fenster.vollbildUmschalten();
    meldungZeit = std::max(0.0f, meldungZeit - dt);
    koopSchritt(dt);

    float seite = fenster.seitenverhaeltnis();
    if (ansicht == Ansicht::Rennen) {
        if (fenster.tasteGedrueckt(T_ESC) && tippZiel == nullptr) {
            if (rennenFertig) {
                if (testfahrt) editorStarten(strecke);
                else ansichtWechseln(Ansicht::Auswahl);
            } else {
                pause = !pause;
            }
        }
        if (!pause && tippZiel == nullptr) {
            if (fenster.tasteGedrueckt('R')) rennenNeu();
            if ((fenster.tasteGedrueckt(T_RUECK) || fenster.tasteGedrueckt('Q')) && rennenLaeuft) zurKontrolle();
            if (fenster.tasteGedrueckt('C')) profil.kamera = 1 - profil.kamera;
            if (fenster.tasteGedrueckt('G')) profil.geist = !profil.geist;
            if (fenster.tasteGedrueckt('P')) autopilotAn = !autopilotAn;
        }
        rennenSchritt(dt);
        if (ansicht != Ansicht::Rennen) return;
        kameraFuehren(dt);
        Vec3 ruetteln(std::sin(zeit * 53.0f) * wackeln * 0.3f, std::sin(zeit * 47.0f) * wackeln * 0.25f, 0.0f);
        Mat4 sicht = blickRichtung(kameraOrt + ruetteln, kameraZiel, Vec3(0.0f, 1.0f, 0.0f));
        Mat4 proj = perspektive(sichtfeld, seite, 0.3f, 9000.0f);
        schattenPass(wagen.ort, true);
        szeneZeichnen(sicht, proj, kameraOrt, true);
        if (profil.geist && !bester.leer() && !testfahrt) {
            Lage g = bester.bei(rennUhr);
            glDepthMask(GL_FALSE);
            autoZeichnen(g, rennUhr * 20.0f, 0.0f, 0.4f, Vec3(0.55f, 0.8f, 1.2f), 0.0f, true);
            glDepthMask(GL_TRUE);
        }
        koopZeichnen();
        schattenZeichnen(wagen);
        if (profil.kamera == 0) {
            autoZeichnen(wagen.lage(), wagen.radDrehung, wagen.lenkwinkel, 1.0f, Vec3(1.0f, 1.0f, 1.0f), wagen.schub, true);
        }
        teilchenZeichnen();
        tonPflegen(dt);
        rennenAnzeige();
        return;
    }

    if (ansicht == Ansicht::Editor) {
        editorSchritt(dt);
        if (ansicht != Ansicht::Editor) return;
        editorZeichnen();
        tonPflegen(dt);
        editorAnzeige();
        return;
    }

    if (ansicht == Ansicht::Garage) {
        garageSchritt(dt);
        tonPflegen(dt);
        garageAnzeige();
        mausVorher = maus;
        return;
    }

    hauptSchritt(dt);
    Mat4 sicht = blickRichtung(kameraOrt, kameraZiel, Vec3(0.0f, 1.0f, 0.0f));
    Mat4 proj = perspektive(bogen(62.0f), seite, 0.3f, 9000.0f);
    schattenPass(wagen.ort, true);
    szeneZeichnen(sicht, proj, kameraOrt, false);
    koopZeichnen();
    schattenZeichnen(wagen);
    autoZeichnen(wagen.lage(), wagen.radDrehung, wagen.lenkwinkel, 1.0f, Vec3(1.0f, 1.0f, 1.0f), wagen.schub, true);
    teilchenPflegen(dt);
    teilchenZeichnen();
    tonPflegen(dt);
    if (ansicht == Ansicht::Haupt) hauptAnzeige();
    else if (ansicht == Ansicht::Auswahl) auswahlAnzeige();
    else if (ansicht == Ansicht::Einstellungen) einstellungenAnzeige();
    else if (ansicht == Ansicht::Mehrspieler) mehrspielerAnzeige();
    mausVorher = maus;
}

void Spiel::hauptSchritt(float dt) {
    physikRest += dt;
    int schritte = 0;
    while (physikRest >= TICK && schritte < 20) {
        Eingabe e = pilot.lenken(strecke, wagen);
        wagen.schritt(strecke, e, TICK);
        physikRest -= TICK;
        ++schritte;
    }
    bool amEnde = wagen.bodenTeil == ZIEL || wagen.ort.y < strecke.tiefstes() - 40.0f ||
                  pilot.stand() >= static_cast<int>(strecke.stuecke.size()) - 1;
    if (amEnde) {
        Vec3 ort;
        float gier = 0.0f;
        strecke.startpunkt(ort, gier);
        wagen.setzen(ort, gier);
        pilot.neu();
    }
    float w = zeit * 0.18f;
    Lage l = wagen.lage();
    Vec3 wunsch = l.ort + Vec3(std::sin(w) * 22.0f, 9.0f + std::sin(zeit * 0.3f) * 2.5f, std::cos(w) * 22.0f);
    kameraOrt = mische(kameraOrt, wunsch, 1.0f - std::exp(-dt * 2.0f));
    kameraZiel = mische(kameraZiel, l.ort + Vec3(0.0f, 1.0f, 0.0f), 1.0f - std::exp(-dt * 6.0f));
}

bool Spiel::ueber(float x, float y, float b, float h) const {
    Vec2 m = fenster.mausOrt();
    return m.x >= x && m.x <= x + b && m.y >= y && m.y <= y + h;
}

void Spiel::tafel(float x, float y, float b, float h, float deck) {
    Farbe f = TAFEL;
    f.a = deck;
    schrift.flaeche(x, y, b, h, f);
    schrift.flaeche(x, y, 3.0f, h, Farbe(GOLD.r, GOLD.g, GOLD.b, 0.85f * deck));
}

void Spiel::schreiben(float x, float y, const std::string& text, Farbe farbe, int groesse) {
    Schrift& s = groesse >= 2 ? gross : schrift;
    s.text(x, y, latin(text), farbe, groesse == 3 ? 2.1f : 1.0f);
}

void Spiel::mittig(float x, float y, const std::string& text, Farbe farbe, int groesse) {
    Schrift& s = groesse >= 2 ? gross : schrift;
    s.textMittig(x, y, latin(text), farbe, groesse == 3 ? 2.1f : 1.0f);
}

float Spiel::breiteVon(const std::string& text, int groesse) {
    Schrift& s = groesse >= 2 ? gross : schrift;
    return s.textBreite(latin(text), groesse == 3 ? 2.1f : 1.0f);
}

bool Spiel::knopf(float x, float y, float b, float h, const std::string& text, bool hervor, bool aus) {
    bool drueber = !aus && ueber(x, y, b, h);
    Farbe grund = hervor ? Farbe(0.95f, 0.72f, 0.18f, 0.96f) : (drueber ? TAFEL_HELL : TAFEL);
    schrift.flaeche(x, y, b, h, grund);
    if (drueber && !hervor) schrift.flaeche(x, y + h - 3.0f, b, 3.0f, GOLD);
    Farbe schriftFarbe = hervor ? Farbe(0.06f, 0.07f, 0.12f) : (aus ? Farbe(0.5f, 0.52f, 0.6f) : HELL);
    mittig(x + b * 0.5f, y + (h - schrift.zeilenhoehe()) * 0.5f, text, schriftFarbe);
    if (drueber && fenster.mausGedrueckt(Maustaste::Links)) {
        if (tonAn) ton.ereignis(Klang::Schritt, 0.5f);
        return true;
    }
    return false;
}

bool Spiel::texteingabe(std::string& ziel, size_t laenge) {
    bool gross_ = fenster.taste(T_SHIFT);
    for (int c = 'A'; c <= 'Z'; ++c) {
        if (fenster.tasteGedrueckt(c) && ziel.size() < laenge) ziel.push_back(static_cast<char>(gross_ ? c : c + 32));
    }
    for (int c = '0'; c <= '9'; ++c) {
        if (fenster.tasteGedrueckt(c) && ziel.size() < laenge) ziel.push_back(static_cast<char>(c));
    }
    if (fenster.tasteGedrueckt(T_LEER) && ziel.size() < laenge && !ziel.empty()) ziel.push_back(' ');
    if (fenster.tasteGedrueckt(T_MINUS) && ziel.size() < laenge) ziel.push_back('-');
    if (fenster.tasteGedrueckt(T_RUECK) && !ziel.empty()) ziel.pop_back();
    return fenster.tasteGedrueckt(T_ENTER) || fenster.tasteGedrueckt(T_ESC);
}

void Spiel::meldung(const std::string& text, float dauer) {
    meldungText = text;
    meldungZeit = dauer;
}

bool Spiel::bildschirmPunkt(Vec3 welt, float& x, float& y) const {
    Mat4 m = projMatrix * sichtMatrix;
    float w = 1.0f;
    Vec3 p = nachVorn(m, welt, w);
    if (w <= 0.1f) return false;
    x = (p.x / w * 0.5f + 0.5f) * fenster.breite();
    y = (1.0f - (p.y / w * 0.5f + 0.5f)) * fenster.hoehe();
    return x > -50 && x < fenster.breite() + 50 && y > -50 && y < fenster.hoehe() + 50;
}

void Spiel::miniKarte(const Strecke& s, float x, float y, float b, float h) {
    schrift.flaeche(x, y, b, h, Farbe(0.03f, 0.05f, 0.1f, 0.9f));
    if (s.stuecke.empty()) return;
    int x0, z0, x1, z1;
    s.grenzen(x0, z0, x1, z1);
    float zellen = static_cast<float>(std::max(x1 - x0 + 1, z1 - z0 + 1));
    float g = std::min((b - 16.0f) / zellen, (h - 16.0f) / zellen);
    float ox = x + (b - g * (x1 - x0 + 1)) * 0.5f;
    float oy = y + (h - g * (z1 - z0 + 1)) * 0.5f;
    for (const Stueck& st : s.stuecke) {
        Farbe f(0.9f, 0.92f, 0.96f);
        if (st.teil == START) f = Farbe(0.35f, 0.7f, 1.0f);
        else if (st.teil == ZIEL) f = Farbe(1.0f, 0.35f, 0.3f);
        else if (st.teil == KONTROLLE) f = GOLD;
        else if (st.teil == SCHUB) f = Farbe(1.0f, 0.55f, 0.15f);
        float hell = 0.75f + std::min(0.25f, st.y * 0.05f);
        f.r *= hell;
        f.g *= hell;
        f.b *= hell;
        float px = ox + (x1 - st.x) * g;
        float py = oy + (z1 - st.z) * g;
        schrift.flaeche(px + 0.5f, py + 0.5f, std::max(1.0f, g - 1.0f), std::max(1.0f, g - 1.0f), f);
    }
}

void Spiel::hauptAnzeige() {
    float w = static_cast<float>(fenster.breite());
    float h = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    gross.beginnen(fenster.breite(), fenster.hoehe());
    riesig.beginnen(fenster.breite(), fenster.hoehe());
    schrift.flaeche(0, 0, w, h, Farbe(0.02f, 0.03f, 0.08f, 0.28f));
    mittig(w * 0.5f + 4.0f, h * 0.13f + 5.0f, "BLITZBAHN", Farbe(0.02f, 0.03f, 0.07f, 0.65f), 3);
    mittig(w * 0.5f, h * 0.13f, "BLITZBAHN", GOLD, 3);
    mittig(w * 0.5f, h * 0.13f + 118.0f, "Stuntrennen von FelWorks", HELL);
    const char* namen[] = {"Spielen", "Editor", "Garage", "Mehrspieler", "Einstellungen"};
    const char* unter[] = {"Strecken fahren", "Strecken bauen", "Auto lackieren", "Gegen Freunde", "Ton und Kamera"};
    float kb = std::min(200.0f, (w - 120.0f) / 5.0f - 14.0f);
    float kh = 150.0f;
    float gesamt = kb * 5 + 14.0f * 4;
    float x = (w - gesamt) * 0.5f;
    float y = h * 0.5f - 20.0f;
    for (int i = 0; i < 5; ++i) {
        float px = x + i * (kb + 14.0f);
        bool drueber = ueber(px, y, kb, kh);
        schrift.flaeche(px, y, kb, kh, drueber ? Farbe(0.98f, 0.76f, 0.22f, 0.97f) : TAFEL);
        schrift.flaeche(px, y, kb, 6.0f, i == 0 ? GRUEN : GOLD);
        Farbe tf = drueber ? Farbe(0.05f, 0.06f, 0.1f) : HELL;
        mittig(px + kb * 0.5f, y + 46.0f, namen[i], tf, 1);
        mittig(px + kb * 0.5f, y + 82.0f, unter[i], drueber ? Farbe(0.15f, 0.15f, 0.2f) : GEDAEMPFT);
        if (drueber && fenster.mausGedrueckt(Maustaste::Links)) {
            if (tonAn) ton.ereignis(Klang::Schritt, 0.5f);
            if (i == 0) ansichtWechseln(Ansicht::Auswahl);
            if (i == 1) editorStarten(Strecke());
            if (i == 2) ansichtWechseln(Ansicht::Garage);
            if (i == 3) ansichtWechseln(Ansicht::Mehrspieler);
            if (i == 4) ansichtWechseln(Ansicht::Einstellungen);
        }
    }
    if (knopf(24.0f, h - 64.0f, 150.0f, 42.0f, "Beenden")) fenster.schliessenAnfordern();
    std::string fahrer = "Fahrer: " + profil.name;
    schreiben(w - breiteVon(fahrer) - 28.0f, h - 56.0f, fahrer, GEDAEMPFT);
    mittig(w * 0.5f, h - 50.0f, "Eigenes Spiel von FelWorks  -  Enter startet sofort", GEDAEMPFT);
    if (fenster.tasteGedrueckt(T_ENTER) && !offizielle.empty()) rennenStarten(offizielle.front(), false);
    if (fenster.tasteGedrueckt(T_ESC)) fenster.schliessenAnfordern();
    if (meldungZeit > 0.0f) mittig(w * 0.5f, h * 0.5f + 160.0f, meldungText, GOLD);
    schrift.beenden();
    gross.beenden();
    riesig.beenden();
}

void Spiel::auswahlAnzeige() {
    float w = static_cast<float>(fenster.breite());
    float h = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    gross.beginnen(fenster.breite(), fenster.hoehe());
    riesig.beginnen(fenster.breite(), fenster.hoehe());
    schrift.flaeche(0, 0, w, h, Farbe(0.02f, 0.03f, 0.08f, 0.62f));
    schrift.flaeche(0, 0, w, 64.0f, TAFEL);
    if (knopf(16.0f, 12.0f, 120.0f, 40.0f, "Zurück") || fenster.tasteGedrueckt(T_ESC)) {
        ansichtWechseln(Ansicht::Haupt);
        schrift.beenden();
        gross.beenden();
        riesig.beenden();
        return;
    }
    if (knopf(150.0f, 12.0f, 230.0f, 40.0f, "Offizielle Strecken", auswahlReiter == 0)) {
        auswahlReiter = 0;
        auswahlRollen = 0.0f;
    }
    if (knopf(390.0f, 12.0f, 200.0f, 40.0f, "Eigene Strecken", auswahlReiter == 1)) {
        auswahlReiter = 1;
        auswahlRollen = 0.0f;
        eigeneLaden();
    }
    if (knopf(w - 420.0f, 12.0f, 190.0f, 40.0f, "Zufallsstrecke")) {
        Strecke z = zufallsStrecke(static_cast<unsigned>(jetzt() * 1000.0) & 0xFFFFu, 26);
        z.kennung = "zufall";
        rennenStarten(z, true);
        schrift.beenden();
        gross.beenden();
        riesig.beenden();
        return;
    }
    if (knopf(w - 220.0f, 12.0f, 200.0f, 40.0f, "Neue Strecke bauen")) {
        editorStarten(Strecke());
        schrift.beenden();
        gross.beenden();
        riesig.beenden();
        return;
    }
    const std::vector<Strecke>& liste = auswahlReiter == 0 ? offizielle : eigene;
    float kb = 220.0f;
    float kh = 230.0f;
    int spalten = std::max(1, static_cast<int>((w - 40.0f) / (kb + 18.0f)));
    float rand = (w - spalten * (kb + 18.0f) + 18.0f) * 0.5f;
    auswahlRollen = std::max(0.0f, auswahlRollen - fenster.radBewegung() * 60.0f);
    int zeilen = (static_cast<int>(liste.size()) + spalten - 1) / spalten;
    float maxRollen = std::max(0.0f, zeilen * (kh + 18.0f) + 100.0f - h);
    auswahlRollen = std::min(auswahlRollen, maxRollen);
    if (liste.empty()) {
        mittig(w * 0.5f, h * 0.45f, "Noch keine eigenen Strecken. Bau dir im Editor eine!", GEDAEMPFT, 2);
    }
    for (int i = 0; i < static_cast<int>(liste.size()); ++i) {
        const Strecke& s = liste[i];
        float x = rand + (i % spalten) * (kb + 18.0f);
        float y = 84.0f + (i / spalten) * (kh + 18.0f) - auswahlRollen;
        if (y + kh < 64.0f || y > h) continue;
        bool drueber = ueber(x, y, kb, kh) && fenster.mausOrt().y > 64.0f;
        schrift.flaeche(x, y, kb, kh, drueber ? TAFEL_HELL : TAFEL);
        schrift.flaeche(x, y, kb, 34.0f, Farbe(0.12f, 0.16f, 0.3f, 0.95f));
        mittig(x + kb * 0.5f, y + 6.0f, s.name, drueber ? GOLD : HELL);
        miniKarte(s, x + 10.0f, y + 42.0f, kb - 20.0f, 140.0f);
        std::string schluessel = schluesselVon(s);
        auto r = rekorde.find(schluessel);
        mittig(x + kb * 0.5f, y + kh - 38.0f, r != rekorde.end() ? "Bestzeit " + zeitText(r->second) : "Noch keine Zeit",
               r != rekorde.end() ? GRUEN : GEDAEMPFT);
        if (drueber && fenster.mausGedrueckt(Maustaste::Links)) {
            rennenStarten(s, false);
            schrift.beenden();
            gross.beenden();
            riesig.beenden();
            return;
        }
        if (drueber && fenster.mausGedrueckt(Maustaste::Rechts) && auswahlReiter == 1) {
            editorStarten(s);
            schrift.beenden();
            gross.beenden();
            riesig.beenden();
            return;
        }
    }
    if (auswahlReiter == 1 && !liste.empty()) mittig(w * 0.5f, h - 30.0f, "Linksklick fahren  -  Rechtsklick bearbeiten", GEDAEMPFT);
    schrift.beenden();
    gross.beenden();
    riesig.beenden();
}

void Spiel::rennenAnzeige() {
    float w = static_cast<float>(fenster.breite());
    float h = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    gross.beginnen(fenster.breite(), fenster.hoehe());
    riesig.beginnen(fenster.breite(), fenster.hoehe());

    tafel(16.0f, 16.0f, 300.0f, 74.0f);
    schreiben(30.0f, 22.0f, strecke.name, HELL);
    schreiben(30.0f, 52.0f, besterMs > 0 ? "Bestzeit " + zeitText(besterMs) : (testfahrt ? "Testfahrt" : "Noch keine Bestzeit"),
              besterMs > 0 ? GRUEN : GEDAEMPFT);

    int ms = static_cast<int>(rennUhr * 1000.0f);
    if (rennenFertig) ms = zielMs;
    float zb = 300.0f;
    tafel(w * 0.5f - zb * 0.5f, h - 92.0f, zb, 74.0f);
    mittig(w * 0.5f, h - 86.0f, zeitText(ms), HELL, 2);
    if (besterMs > 0 && !bester.leer() && rennenLaeuft && kontrollZeit > 0.0f) {
        mittig(w * 0.5f, h - 116.0f, "Kontrolle " + zeitText(static_cast<int>(kontrollZeit * 1000.0f)), GEDAEMPFT);
    }

    int gesamt = strecke.kontrollZahl();
    tafel(16.0f, h - 92.0f, 200.0f, 74.0f);
    schreiben(30.0f, h - 84.0f, "Kontrollpunkte", GEDAEMPFT);
    schreiben(30.0f, h - 58.0f, std::to_string(erreicht.size()) + " / " + std::to_string(gesamt),
              static_cast<int>(erreicht.size()) >= gesamt ? GRUEN : HELL);

    int kmh = static_cast<int>(std::lround(std::fabs(wagen.vorwaerts()) * 3.6f));
    tafel(w - 216.0f, h - 92.0f, 200.0f, 74.0f);
    std::string tempo = std::to_string(kmh);
    schreiben(w - 196.0f, h - 86.0f, tempo, wagen.schub > 0.0f ? GOLD : HELL, 2);
    schreiben(w - 196.0f + breiteVon(tempo, 2) + 8.0f, h - 58.0f, "km/h", GEDAEMPFT);

    if (vorlauf > 0.0f) {
        int zahl = static_cast<int>(std::ceil(vorlauf / (VORLAUF / 3.0f)));
        mittig(w * 0.5f, h * 0.32f, std::to_string(std::max(1, zahl)), GOLD, 3);
    } else if (rennenLaeuft && rennUhr < 0.8f) {
        mittig(w * 0.5f, h * 0.32f, "LOS!", GRUEN, 3);
    }
    if (autopilotAn) mittig(w * 0.5f, 24.0f, "Autopilot (P)", GOLD);
    if (rennUhr < 6.0f && !rennenFertig) {
        mittig(w * 0.5f, h - 140.0f,
               "W Gas  S Bremse  A D Lenken  Leertaste Driften  R Neustart  Q Kontrollpunkt  C Kamera  Esc Pause", GEDAEMPFT);
    }
    if (koop.spielt()) {
        float y = 110.0f;
        tafel(16.0f, y, 300.0f, 30.0f + 28.0f * static_cast<float>(koop.mitspieler().size() + 1));
        schreiben(30.0f, y + 6.0f, "Mitspieler", GOLD);
        y += 32.0f;
        for (const KoopFreund& f : koop.mitspieler()) {
            std::string z = "-";
            for (const Ergebnis& e : ergebnisse)
                if (e.name == f.name) z = zeitText(e.ms);
            schreiben(30.0f, y, f.name, HELL);
            schreiben(220.0f, y, z, GRUEN);
            y += 28.0f;
        }
        for (const KoopFreund& f : koop.mitspieler()) {
            if (!f.anwesend) continue;
            float sx = 0.0f;
            float sy = 0.0f;
            if (bildschirmPunkt(f.zeigeOrt + Vec3(0.0f, 2.6f, 0.0f), sx, sy)) {
                float tb = breiteVon(f.name) + 16.0f;
                schrift.flaeche(sx - tb * 0.5f, sy - 14.0f, tb, 28.0f, Farbe(0.05f, 0.07f, 0.14f, 0.75f));
                mittig(sx, sy - 11.0f, f.name, HELL);
            }
        }
    }

    if (rennenFertig) {
        float pb = 460.0f;
        float ph = 300.0f;
        float px = (w - pb) * 0.5f;
        float py = h * 0.24f;
        schrift.flaeche(px, py, pb, ph, Farbe(0.05f, 0.07f, 0.14f, 0.94f));
        schrift.flaeche(px, py, pb, 6.0f, neuerRekord ? GRUEN : GOLD);
        mittig(w * 0.5f, py + 24.0f, neuerRekord ? "Neue Bestzeit!" : "Ziel erreicht", neuerRekord ? GRUEN : GOLD, 2);
        mittig(w * 0.5f, py + 86.0f, zeitText(zielMs), HELL, 2);
        if (besterMs > 0 && !neuerRekord) {
            mittig(w * 0.5f, py + 146.0f, "Bestzeit " + zeitText(besterMs) + "   (" + differenzText(zielMs - besterMs) + ")", ROT);
        } else if (besterMs > 0) {
            mittig(w * 0.5f, py + 146.0f, "Alte Bestzeit " + zeitText(besterMs) + "   (" + differenzText(zielMs - besterMs) + ")", GRUEN);
        }
        float kb = 132.0f;
        float ky = py + ph - 64.0f;
        if (knopf(px + 18.0f, ky, kb, 44.0f, "Nochmal (R)", true)) rennenNeu();
        if (koop.spielt()) {
            if (koop.gastgeber() && knopf(px + 30.0f + kb, ky, kb, 44.0f, "Neue Runde")) koop.plaudern("#BB:NEU");
        } else if (testfahrt) {
            if (knopf(px + 30.0f + kb, ky, kb + 40.0f, 44.0f, "Zum Editor")) {
                editorStarten(strecke);
            }
        } else {
            int index = -1;
            for (int i = 0; i < static_cast<int>(offizielle.size()); ++i)
                if (offizielle[i].kennung == strecke.kennung) index = i;
            bool hatNaechste = index >= 0 && index + 1 < static_cast<int>(offizielle.size());
            if (knopf(px + 30.0f + kb, ky, kb, 44.0f, "Nächste", false, !hatNaechste) && hatNaechste) {
                rennenStarten(offizielle[index + 1], false);
            }
        }
        if (ansicht == Ansicht::Rennen && knopf(px + pb - kb - 18.0f, ky, kb, 44.0f, "Menü")) ansichtWechseln(Ansicht::Auswahl);
    }

    if (pause && !rennenFertig) {
        schrift.flaeche(0, 0, w, h, Farbe(0.02f, 0.03f, 0.08f, 0.55f));
        float pb = 340.0f;
        float px = (w - pb) * 0.5f;
        float py = h * 0.26f;
        schrift.flaeche(px, py, pb, 330.0f, Farbe(0.05f, 0.07f, 0.14f, 0.96f));
        mittig(w * 0.5f, py + 20.0f, "Pause", GOLD, 2);
        if (knopf(px + 30.0f, py + 90.0f, pb - 60.0f, 46.0f, "Weiter", true)) pause = false;
        if (knopf(px + 30.0f, py + 146.0f, pb - 60.0f, 46.0f, "Neustart")) rennenNeu();
        if (knopf(px + 30.0f, py + 202.0f, pb - 60.0f, 46.0f, testfahrt ? "Zurück zum Editor" : "Streckenwahl")) {
            if (testfahrt) editorStarten(strecke);
            else ansichtWechseln(Ansicht::Auswahl);
        }
        if (ansicht == Ansicht::Rennen && knopf(px + 30.0f, py + 258.0f, pb - 60.0f, 46.0f, "Hauptmenü")) ansichtWechseln(Ansicht::Haupt);
    }
    if (meldungZeit > 0.0f) mittig(w * 0.5f, 110.0f, meldungText, GOLD);
    schrift.beenden();
    gross.beenden();
    riesig.beenden();
}

void Spiel::garageSchritt(float dt) {
    garageDreh += dt * 0.35f;
    float seite = fenster.seitenverhaeltnis();
    Vec3 mitte(0.0f, 5000.0f, 0.0f);
    Vec3 auge = mitte + Vec3(std::sin(0.6f) * 7.6f, 2.6f, std::cos(0.6f) * 7.6f);
    Mat4 sicht = blickRichtung(auge, mitte + Vec3(-1.2f, 0.6f, 0.0f), Vec3(0.0f, 1.0f, 0.0f));
    Mat4 proj = perspektive(bogen(48.0f), seite, 0.1f, 9000.0f);
    sichtMatrix = sicht;
    projMatrix = proj;
    Lage l;
    l.ort = mitte + Vec3(0.0f, 0.03f, 0.0f);
    l.vorne = Vec3(std::sin(garageDreh), 0.0f, std::cos(garageDreh));
    l.oben = Vec3(0.0f, 1.0f, 0.0f);
    float lenk = std::sin(zeit * 0.8f) * 0.3f;
    if (profil.schatten && grafik.schattenMoeglich()) {
        grafik.schattenBeginnen(mitte, sonnenRichtung, 12.0f);
        autoSchatten(l, zeit * 2.0f, lenk, true);
        grafik.schattenBeenden(fenster.breite(), fenster.hoehe());
    }
    glViewport(0, 0, fenster.breite(), fenster.hoehe());
    glClearColor(0.1f, 0.12f, 0.2f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    grafik.beginnen(sicht, proj, auge, zeit, sonnenRichtung, profil.schatten);
    himmelZeichnen(auge);
    grafik.nebel(0.0f);
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    grafik.modell(verschiebung(mitte));
    grafik.zeichnen(bodenNetz);
    autoZeichnen(l, zeit * 2.0f, lenk, 1.0f, Vec3(1.0f, 1.0f, 1.0f), 0.2f, true);
}

void Spiel::garageAnzeige() {
    float w = static_cast<float>(fenster.breite());
    float h = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    gross.beginnen(fenster.breite(), fenster.hoehe());
    riesig.beginnen(fenster.breite(), fenster.hoehe());
    schrift.flaeche(0, 0, w, 64.0f, TAFEL);
    schreiben(160.0f, 12.0f, "Garage", GOLD, 2);
    bool zurueck = knopf(16.0f, 12.0f, 120.0f, 40.0f, "Zurück") || (tippZiel == nullptr && fenster.tasteGedrueckt(T_ESC));
    struct Reihe {
        const char* name;
        Vec3* ziel;
    };
    Reihe reihen[] = {{"Grundfarbe", &profil.farben.primaer},
                      {"Akzentfarbe", &profil.farben.sekundaer},
                      {"Felgen", &profil.farben.felgen},
                      {"Rahmen", &profil.farben.rahmen}};
    bool neu = false;
    float px = 24.0f;
    float py = 90.0f;
    float feld = 30.0f;
    for (Reihe& r : reihen) {
        tafel(px, py, feld * 8 + 40.0f, 118.0f);
        schreiben(px + 16.0f, py + 8.0f, r.name, HELL);
        for (int i = 0; i < PALETTE_ZAHL; ++i) {
            float x = px + 16.0f + (i % 8) * (feld + 2.0f);
            float y = py + 40.0f + (i / 8) * (feld + 2.0f);
            Vec3 f = PALETTE[i];
            bool gewaehlt = laenge(*r.ziel - f) < 0.01f;
            if (gewaehlt) schrift.flaeche(x - 3.0f, y - 3.0f, feld + 6.0f, feld + 6.0f, GOLD);
            schrift.flaeche(x, y, feld, feld, Farbe(f));
            if (ueber(x, y, feld, feld) && fenster.mausGedrueckt(Maustaste::Links)) {
                *r.ziel = f;
                neu = true;
            }
        }
        py += 130.0f;
    }
    if (knopf(px, py, 140.0f, 42.0f, "Zufall")) {
        Zufall z(static_cast<uint64_t>(jetzt() * 1000.0));
        for (Reihe& r : reihen) *r.ziel = PALETTE[z.ganz(0, PALETTE_ZAHL)];
        neu = true;
    }
    if (knopf(px + 152.0f, py, 140.0f, 42.0f, "Standard")) {
        profil.farben = Lackierung();
        neu = true;
    }
    float nx = w - 340.0f;
    tafel(nx, 90.0f, 316.0f, 100.0f);
    schreiben(nx + 16.0f, 98.0f, "Fahrername", HELL);
    bool tippt = tippZiel == &profil.name;
    schrift.flaeche(nx + 16.0f, 132.0f, 284.0f, 40.0f, tippt ? Farbe(0.2f, 0.25f, 0.42f, 1.0f) : Farbe(0.1f, 0.12f, 0.22f, 1.0f));
    schreiben(nx + 26.0f, 140.0f, profil.name + (tippt && std::fmod(zeit, 1.0f) < 0.5f ? "|" : ""), HELL);
    if (ueber(nx + 16.0f, 132.0f, 284.0f, 40.0f) && fenster.mausGedrueckt(Maustaste::Links)) tippZiel = &profil.name;
    if (tippt && texteingabe(profil.name, 18)) {
        tippZiel = nullptr;
        if (profil.name.empty()) profil.name = "Fahrer";
        profilSpeichern();
        koop.anlegen("blitzbahn", profil.name);
    }
    mittig(w * 0.62f, h - 50.0f, "Dein Auto in allen Rennen  -  auch Mitspieler sehen deinen Namen", GEDAEMPFT);
    if (neu) {
        autoNetzBauen();
        profilSpeichern();
    }
    schrift.beenden();
    gross.beenden();
    riesig.beenden();
    if (zurueck) {
        profilSpeichern();
        ansichtWechseln(Ansicht::Haupt);
    }
}

void Spiel::einstellungenAnzeige() {
    float w = static_cast<float>(fenster.breite());
    float h = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    gross.beginnen(fenster.breite(), fenster.hoehe());
    riesig.beginnen(fenster.breite(), fenster.hoehe());
    schrift.flaeche(0, 0, w, h, Farbe(0.02f, 0.03f, 0.08f, 0.6f));
    float pb = 520.0f;
    float px = (w - pb) * 0.5f;
    float py = h * 0.16f;
    schrift.flaeche(px, py, pb, 534.0f, Farbe(0.05f, 0.07f, 0.14f, 0.95f));
    mittig(w * 0.5f, py + 18.0f, "Einstellungen", GOLD, 2);
    float y = py + 96.0f;
    schreiben(px + 30.0f, y + 10.0f, "Lautstärke", HELL);
    if (knopf(px + 250.0f, y, 46.0f, 42.0f, "-")) profil.lautstaerke = std::max(0.0f, profil.lautstaerke - 0.1f);
    schrift.flaeche(px + 306.0f, y + 16.0f, 120.0f, 10.0f, Farbe(0.15f, 0.18f, 0.3f));
    schrift.flaeche(px + 306.0f, y + 16.0f, 120.0f * profil.lautstaerke, 10.0f, GOLD);
    if (knopf(px + 436.0f, y, 46.0f, 42.0f, "+")) profil.lautstaerke = std::min(1.0f, profil.lautstaerke + 0.1f);
    if (tonAn) ton.lautstaerke(profil.lautstaerke);
    y += 64.0f;
    schreiben(px + 30.0f, y + 10.0f, "Geist der Bestzeit", HELL);
    if (knopf(px + 250.0f, y, 232.0f, 42.0f, profil.geist ? "Sichtbar" : "Aus", profil.geist)) profil.geist = !profil.geist;
    y += 64.0f;
    schreiben(px + 30.0f, y + 10.0f, "Kamera", HELL);
    if (knopf(px + 250.0f, y, 232.0f, 42.0f, profil.kamera == 0 ? "Hinter dem Auto" : "Cockpit")) profil.kamera = 1 - profil.kamera;
    y += 64.0f;
    schreiben(px + 30.0f, y + 10.0f, "Echte Schatten", HELL);
    if (knopf(px + 250.0f, y, 232.0f, 42.0f, !grafik.schattenMoeglich() ? "Nicht verfügbar" : (profil.schatten ? "An" : "Aus"), profil.schatten && grafik.schattenMoeglich(), !grafik.schattenMoeglich())) profil.schatten = !profil.schatten;
    y += 64.0f;
    schreiben(px + 30.0f, y + 10.0f, "Vollbild (F11)", HELL);
    if (knopf(px + 250.0f, y, 232.0f, 42.0f, "Umschalten")) fenster.vollbildUmschalten();
    y += 84.0f;
    if (knopf(px + 30.0f, y, pb - 60.0f, 46.0f, "Speichern und zurück", true) || fenster.tasteGedrueckt(T_ESC)) {
        profilSpeichern();
        ansichtWechseln(Ansicht::Haupt);
    }
    schrift.beenden();
    gross.beenden();
    riesig.beenden();
}

void Spiel::koopStreckeSenden() {
    std::vector<const Strecke*> alle;
    for (const Strecke& s : offizielle) alle.push_back(&s);
    for (const Strecke& s : eigene) alle.push_back(&s);
    if (alle.empty()) return;
    koopWahl = ((koopWahl % static_cast<int>(alle.size())) + static_cast<int>(alle.size())) % static_cast<int>(alle.size());
    const Strecke& s = *alle[koopWahl];
    if (!s.kennung.empty() && s.kennung[0] == 'o') {
        koop.plaudern("#BB:BAHN:" + s.kennung);
        return;
    }
    std::string text = s.kompakt();
    const size_t stueck = 230;
    int teile = static_cast<int>((text.size() + stueck - 1) / stueck);
    for (int i = 0; i < teile; ++i) {
        koop.plaudern("#BB:TEIL:" + std::to_string(i) + "/" + std::to_string(teile) + ":" + text.substr(i * stueck, stueck));
    }
}

void Spiel::koopNachricht(const std::string& zeile) {
    size_t marke = zeile.find("#BB:");
    if (marke == std::string::npos) {
        meldung(zeile, 4.0f);
        return;
    }
    std::string name = marke >= 2 ? zeile.substr(0, marke - 2) : std::string();
    std::string inhalt = zeile.substr(marke + 4);
    if (inhalt.rfind("BAHN:", 0) == 0) {
        std::string kennung = inhalt.substr(5);
        for (const Strecke& s : offizielle) {
            if (s.kennung == kennung) {
                strecke = s;
                koopStreckeDa = true;
                weltLaden(strecke);
                meldung("Strecke: " + s.name);
            }
        }
    } else if (inhalt.rfind("TEIL:", 0) == 0) {
        int nummer = 0;
        int gesamt = 0;
        if (std::sscanf(inhalt.c_str() + 5, "%d/%d", &nummer, &gesamt) == 2) {
            size_t doppel = inhalt.find(':', 5);
            if (doppel != std::string::npos) {
                koopTeile[nummer] = inhalt.substr(doppel + 1);
                koopTeileGesamt = gesamt;
            }
            if (static_cast<int>(koopTeile.size()) >= koopTeileGesamt && koopTeileGesamt > 0) {
                std::string ganz;
                for (int i = 0; i < koopTeileGesamt; ++i) ganz += koopTeile[i];
                Strecke s;
                if (Strecke::ausKompakt(ganz, s)) {
                    s.kennung = "m_" + dateiname(s.name);
                    strecke = s;
                    koopStreckeDa = true;
                    weltLaden(strecke);
                    meldung("Strecke vom Gastgeber: " + s.name);
                }
                koopTeile.clear();
                koopTeileGesamt = 0;
            }
        }
    } else if (inhalt.rfind("ZEIT:", 0) == 0) {
        int ms = std::atoi(inhalt.c_str() + 5);
        bool gefunden = false;
        for (Ergebnis& e : ergebnisse) {
            if (e.name == name) {
                if (e.ms == 0 || ms < e.ms) e.ms = ms;
                gefunden = true;
            }
        }
        if (!gefunden) ergebnisse.push_back({name, ms});
        std::sort(ergebnisse.begin(), ergebnisse.end(), [](const Ergebnis& a, const Ergebnis& b) { return a.ms < b.ms; });
        meldung(name + " im Ziel: " + zeitText(ms), 3.5f);
    } else if (inhalt == "NEU") {
        if (ansicht == Ansicht::Rennen) rennenNeu();
    }
}

void Spiel::koopSchritt(float dt) {
    KoopZustand z;
    z.ort = wagen.ort;
    z.fahrt = wagen.fahrt;
    z.gierung = wagen.gier;
    z.neigung = wagen.nick;
    koop.eigenerZustand(z);
    koop.schritt(dt);
    koop.freundeBewegen(dt);
    std::string zeile;
    while (koop.spruchHolen(zeile)) koopNachricht(zeile);
    if (koop.spielt() && !koopRennenAktiv) {
        koopRennenAktiv = true;
        koop.geladenMelden();
        if (!strecke.stuecke.empty()) {
            rennenStarten(strecke, false);
            meldung("Rennen gegen " + std::to_string(koop.spielerzahl() - 1) + " Mitspieler");
        }
    }
    if (!koop.spielt()) koopRennenAktiv = false;
    if (start.koopStarten && koop.stand() == KOOP_LOBBY && koop.gastgeber() && koop.spielerzahl() >= 2) {
        start.koopStarten = false;
        koopStreckeSenden();
        koop.startBitten();
    }
    static int letzter = -1;
    if (koop.stand() != letzter) {
        letzter = koop.stand();
        notiz("Mehrspieler: Stand %d, Code %s, Spieler %d, %s", letzter, koop.code().empty() ? "-" : koop.code().c_str(),
              koop.spielerzahl(), koop.fehler().empty() ? koop.hinweis().c_str() : koop.fehler().c_str());
    }
}

void Spiel::koopZeichnen() {
    if (!koop.aktiv()) return;
    int platz = 0;
    for (const KoopFreund& f : koop.mitspieler()) {
        ++platz;
        if (!f.anwesend) continue;
        Lage l;
        l.ort = f.zeigeOrt;
        float c = std::cos(f.zeigeNeigung);
        l.vorne = Vec3(std::sin(f.zeigeGierung) * c, std::sin(f.zeigeNeigung), std::cos(f.zeigeGierung) * c);
        Boden b = strecke.boden(f.zeigeOrt + Vec3(0.0f, 0.5f, 0.0f), 0.2f);
        l.oben = (b.da && f.zeigeOrt.y - b.hoehe < 0.5f) ? b.normale : Vec3(0.0f, 1.0f, 0.0f);
        Vec3 farbe = SPIELERFARBEN[(platz - 1) % 6];
        autoZeichnen(l, zeit * 18.0f, 0.0f, 1.0f, farbe, 0.4f, false);
    }
}

void Spiel::mehrspielerAnzeige() {
    float w = static_cast<float>(fenster.breite());
    float h = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    gross.beginnen(fenster.breite(), fenster.hoehe());
    riesig.beginnen(fenster.breite(), fenster.hoehe());
    schrift.flaeche(0, 0, w, h, Farbe(0.02f, 0.03f, 0.08f, 0.6f));
    float pb = 640.0f;
    float px = (w - pb) * 0.5f;
    float py = h * 0.1f;
    schrift.flaeche(px, py, pb, 560.0f, Farbe(0.05f, 0.07f, 0.14f, 0.95f));
    mittig(w * 0.5f, py + 18.0f, "Mehrspieler", GOLD, 2);
    bool weg = false;
    if (!koop.aktiv()) {
        mittig(w * 0.5f, py + 84.0f, "Fahrt gegeneinander auf derselben Strecke. Jon verbindet euch,", GEDAEMPFT);
        mittig(w * 0.5f, py + 110.0f, "Freunde geben einfach deinen Code ein.", GEDAEMPFT);
        if (knopf(px + 40.0f, py + 160.0f, pb - 80.0f, 52.0f, "Rennen eröffnen", true)) {
            koop.anlegen("blitzbahn", profil.name);
            koop.gastgeben(4242ull, Vec3(0.0f, 0.0f, 0.0f));
        }
        schreiben(px + 40.0f, py + 250.0f, "Code eines Freundes", HELL);
        bool tippt = tippZiel == &koopCode;
        schrift.flaeche(px + 40.0f, py + 284.0f, pb - 260.0f, 48.0f, tippt ? Farbe(0.2f, 0.25f, 0.42f) : Farbe(0.1f, 0.12f, 0.22f));
        schreiben(px + 54.0f, py + 296.0f, koopCode + (tippt && std::fmod(zeit, 1.0f) < 0.5f ? "|" : ""), HELL);
        if (ueber(px + 40.0f, py + 284.0f, pb - 260.0f, 48.0f) && fenster.mausGedrueckt(Maustaste::Links)) tippZiel = &koopCode;
        if (tippt) {
            bool fertig = texteingabe(koopCode, 16);
            for (char& c : koopCode) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
            if (fertig) tippZiel = nullptr;
        }
        if (knopf(px + pb - 210.0f, py + 284.0f, 170.0f, 48.0f, "Beitreten", false, koopCode.size() < 4) && koopCode.size() >= 4) {
            tippZiel = nullptr;
            koop.anlegen("blitzbahn", profil.name);
            koop.beitreten(koopCode);
        }
        if (!koop.fehler().empty()) mittig(w * 0.5f, py + 360.0f, koop.fehler(), ROT);
        else if (!koop.hinweis().empty()) mittig(w * 0.5f, py + 360.0f, koop.hinweis(), GEDAEMPFT);
    } else {
        mittig(w * 0.5f, py + 76.0f, "Dein Code", GEDAEMPFT);
        mittig(w * 0.5f, py + 104.0f, koop.code().empty() ? "..." : koop.code(), GOLD, 2);
        float y = py + 176.0f;
        schreiben(px + 40.0f, y, profil.name + (koop.gastgeber() ? "  (Gastgeber)" : ""), HELL);
        y += 30.0f;
        for (const KoopFreund& f : koop.mitspieler()) {
            schreiben(px + 40.0f, y, f.name, f.online ? HELL : GEDAEMPFT);
            y += 30.0f;
        }
        std::vector<const Strecke*> alle;
        for (const Strecke& s : offizielle) alle.push_back(&s);
        for (const Strecke& s : eigene) alle.push_back(&s);
        if (koop.gastgeber() && !alle.empty()) {
            int n = static_cast<int>(alle.size());
            koopWahl = ((koopWahl % n) + n) % n;
            float sy = py + 360.0f;
            if (knopf(px + 40.0f, sy, 52.0f, 48.0f, "<")) koopWahl = (koopWahl + n - 1) % n;
            schrift.flaeche(px + 100.0f, sy, pb - 200.0f, 48.0f, Farbe(0.1f, 0.12f, 0.22f));
            mittig(w * 0.5f, sy + 12.0f, alle[koopWahl]->name, HELL);
            if (knopf(px + pb - 92.0f, sy, 52.0f, 48.0f, ">")) koopWahl = (koopWahl + 1) % n;
            bool genug = koop.spielerzahl() >= 2;
            if (knopf(px + 40.0f, py + 430.0f, pb - 80.0f, 52.0f, genug ? "Rennen starten" : "Warte auf Mitspieler ...", genug, !genug) && genug) {
                strecke = *alle[koopWahl];
                weltLaden(strecke);
                koopStreckeSenden();
                koop.startBitten();
            }
        } else {
            mittig(w * 0.5f, py + 380.0f, "Der Gastgeber wählt die Strecke und startet das Rennen.", GEDAEMPFT);
        }
        if (knopf(px + 40.0f, py + 496.0f, 200.0f, 44.0f, "Verlassen")) koop.verlassen();
    }
    if (knopf(px + pb - 240.0f, py + 496.0f, 200.0f, 44.0f, "Zurück") || (tippZiel == nullptr && fenster.tasteGedrueckt(T_ESC))) weg = true;
    if (meldungZeit > 0.0f) mittig(w * 0.5f, py + 580.0f, meldungText, GOLD);
    schrift.beenden();
    gross.beenden();
    riesig.beenden();
    if (weg) ansichtWechseln(Ansicht::Haupt);
}

void Spiel::editorStarten(const Strecke& s) {
    edit = s;
    if (edit.stuecke.empty()) {
        streckeBauen("GGLGGKGGRGGZ", edit);
        edit.name = "Meine Strecke";
        edit.kennung.clear();
    }
    edit.autor = profil.name;
    edit.kennung.clear();
    editRueck.clear();
    ansicht = Ansicht::Editor;
    tippZiel = nullptr;
    pause = false;
    rennenLaeuft = false;
    rennenFertig = false;
    strecke = edit;
    weltLaden(edit);
    int x0, z0, x1, z1;
    edit.grenzen(x0, z0, x1, z1);
    editZiel = Vec3((x0 + x1) * 0.5f * ZELLE, 0.0f, (z0 + z1) * 0.5f * ZELLE);
    editAbstand = std::max(120.0f, (std::max(x1 - x0, z1 - z0) + 4) * ZELLE * 0.9f);
    editGeaendert = false;
    editVorschauTeil = -1;
    rechtsStart = Vec2(-1.0f, -1.0f);
    rechtsZieht = false;
    Bauer g;
    gitterBauen(g, zelleVon(editZiel.x), zelleVon(editZiel.z), editEbene, 14);
    gitterNetz.hochladen(g);
}

void Spiel::editorMerken() {
    editRueck.push_back(edit);
    if (editRueck.size() > 80) editRueck.erase(editRueck.begin());
}

void Spiel::editorSetzen() {
    if (!editHover) return;
    editorMerken();
    if (editTeil == START) {
        for (int i = static_cast<int>(edit.stuecke.size()) - 1; i >= 0; --i)
            if (edit.stuecke[i].teil == START) edit.entfernen(i);
    }
    int alt = edit.belegt(editHoverX, editHoverZ, editEbene, editEbene + teilSpanne(editTeil));
    while (alt >= 0) {
        edit.entfernen(alt);
        alt = edit.belegt(editHoverX, editHoverZ, editEbene, editEbene + teilSpanne(editTeil));
    }
    Stueck s;
    s.teil = editTeil;
    s.x = editHoverX;
    s.y = editEbene;
    s.z = editHoverZ;
    s.dreh = editDreh;
    edit.setzen(s);
    editGeaendert = true;
    if (tonAn) ton.ereignis(Klang::Hammer, 0.4f);
}

void Spiel::editorEntfernen() {
    if (!editHover) return;
    int i = edit.belegt(editHoverX, editHoverZ, editEbene, editEbene);
    if (i < 0) return;
    editorMerken();
    edit.entfernen(i);
    editGeaendert = true;
    if (tonAn) ton.ereignis(Klang::Platsch, 0.4f);
}

bool Spiel::editorSpeichern() {
    if (edit.name.empty()) edit.name = "Meine Strecke";
    std::string pfad = ordnerNeben("saves/strecken/" + dateiname(edit.name) + ".bahn");
    bool ok = schreibeText(pfad, edit.speichern());
    meldung(ok ? "Gespeichert als \"" + edit.name + "\"" : "Speichern ging nicht");
    eigeneLaden();
    return ok;
}

void Spiel::editorVorschauBauen() {
    Strecke s;
    Stueck st;
    st.teil = editTeil;
    st.x = editHoverX;
    st.y = editEbene;
    st.z = editHoverZ;
    st.dreh = editDreh;
    s.stuecke.push_back(st);
    Bauer fest;
    Bauer leucht;
    streckeBauen(s, fest, leucht);
    vorschauNetz.hochladen(fest);
    vorschauLeucht.hochladen(leucht);
    editVorschauX = editHoverX;
    editVorschauZ = editHoverZ;
    editVorschauTeil = editTeil;
    editVorschauDreh = editDreh;
    editVorschauEbene = editEbene;
}

void Spiel::editorSchritt(float dt) {
    Vec2 maus = fenster.mausOrt();
    float w = static_cast<float>(fenster.breite());
    bool tippt = tippZiel != nullptr;
    bool ueberLeiste = maus.y < 64.0f || maus.x > w - 262.0f;
    if (!tippt) {
        if (fenster.tasteGedrueckt(T_ESC)) {
            if (editGeaendert) editorSpeichern();
            ansichtWechseln(Ansicht::Haupt);
            return;
        }
        bool strg = fenster.taste(T_STRG);
        if (strg && fenster.tasteGedrueckt('Z') && !editRueck.empty()) {
            edit = editRueck.back();
            editRueck.pop_back();
            editGeaendert = true;
        } else if (strg && fenster.tasteGedrueckt('S')) {
            editorSpeichern();
        } else {
            if (fenster.tasteGedrueckt('R')) editDreh = (editDreh + 1) % 4;
            if (fenster.tasteGedrueckt('E') || fenster.tasteGedrueckt(T_BILDAUF)) editEbene = std::min(30, editEbene + 1);
            if (fenster.tasteGedrueckt('Q') || fenster.tasteGedrueckt(T_BILDAB)) editEbene = std::max(-5, editEbene - 1);
            if (fenster.tasteGedrueckt(T_ENTF) || fenster.tasteGedrueckt('X')) editorEntfernen();
            for (int i = 1; i < TEIL_ANZAHL && i <= 9; ++i)
                if (fenster.tasteGedrueckt('0' + i)) editTeil = i;
            if (fenster.tasteGedrueckt('0')) editTeil = 10;
            if (fenster.tasteGedrueckt(T_F5) || fenster.tasteGedrueckt('T')) {
                if (!edit.hatStart()) meldung("Setz zuerst einen Start (Taste 4)");
                else if (!edit.hatZiel()) meldung("Setz noch ein Ziel (Taste 5)");
                else {
                    rennenStarten(edit, true);
                    return;
                }
            }
            float tempo = editAbstand * 0.9f * dt;
            Vec3 vor(std::sin(editGier), 0.0f, std::cos(editGier));
            Vec3 rechts(-vor.z, 0.0f, vor.x);
            if (fenster.taste('W') || fenster.taste(T_HOCH)) editZiel -= vor * tempo;
            if (fenster.taste('S') || fenster.taste(T_RUNTER)) editZiel += vor * tempo;
            if (fenster.taste('A') || fenster.taste(T_LINKS)) editZiel += rechts * tempo;
            if (fenster.taste('D') || fenster.taste(T_RECHTS)) editZiel -= rechts * tempo;
        }
    }
    if (!ueberLeiste) editAbstand = klemme(editAbstand * std::pow(0.88f, fenster.radBewegung()), 30.0f, 900.0f);
    if (fenster.mausGedrueckt(Maustaste::Rechts)) {
        rechtsStart = maus;
        rechtsZieht = false;
    }
    if (fenster.maus(Maustaste::Rechts)) {
        Vec2 d = maus - mausVorher;
        if (std::fabs(maus.x - rechtsStart.x) + std::fabs(maus.y - rechtsStart.y) > 6.0f) rechtsZieht = true;
        if (rechtsZieht) {
            editGier -= d.x * 0.006f;
            editNeigung = klemme(editNeigung + d.y * 0.005f, 0.25f, 1.45f);
        }
    }
    if (fenster.maus(Maustaste::Mitte)) {
        Vec2 d = maus - mausVorher;
        Vec3 vor(std::sin(editGier), 0.0f, std::cos(editGier));
        Vec3 rechts(-vor.z, 0.0f, vor.x);
        float f = editAbstand * 0.0016f;
        editZiel += rechts * (d.x * f) + vor * (-d.y * f);
    }
    bool rechtsLos = !fenster.maus(Maustaste::Rechts) && rechtsStart.x >= 0.0f;
    if (rechtsLos) {
        if (!rechtsZieht && !ueberLeiste) editorEntfernen();
        rechtsStart = Vec2(-1.0f, -1.0f);
        rechtsZieht = false;
    }

    float seite = fenster.seitenverhaeltnis();
    Vec3 ziel = Vec3(editZiel.x, editEbene * STUFE, editZiel.z);
    Vec3 auge = ziel + Vec3(std::sin(editGier) * std::cos(editNeigung), std::sin(editNeigung),
                            std::cos(editGier) * std::cos(editNeigung)) * editAbstand;
    kameraOrt = auge;
    kameraZiel = ziel;
    Mat4 sicht = blickRichtung(auge, ziel, Vec3(0.0f, 1.0f, 0.0f));
    float feld = bogen(55.0f);
    Mat4 proj = perspektive(feld, seite, 0.5f, 9000.0f);
    sichtMatrix = sicht;
    projMatrix = proj;

    editHover = false;
    if (!ueberLeiste) {
        float nx = maus.x / fenster.breite() * 2.0f - 1.0f;
        float ny = 1.0f - maus.y / fenster.hoehe() * 2.0f;
        Vec3 f = normiert(ziel - auge);
        Vec3 s = normiert(kreuz(f, Vec3(0.0f, 1.0f, 0.0f)));
        Vec3 u = kreuz(s, f);
        float t = std::tan(feld * 0.5f);
        Vec3 strahl = normiert(f + s * (nx * t * seite) + u * (ny * t));
        float ebeneY = editEbene * STUFE;
        if (std::fabs(strahl.y) > 1e-4f) {
            float k = (ebeneY - auge.y) / strahl.y;
            if (k > 0.0f) {
                Vec3 p = auge + strahl * k;
                editHover = true;
                editHoverX = zelleVon(p.x);
                editHoverZ = zelleVon(p.z);
            }
        }
    }
    if (editHover && fenster.mausGedrueckt(Maustaste::Links) && !tippt) editorSetzen();
    if (editGeaendert) {
        strecke = edit;
        weltLaden(edit);
        editGeaendert = false;
    }
    if (editHover && (editHoverX != editVorschauX || editHoverZ != editVorschauZ || editTeil != editVorschauTeil ||
                      editDreh != editVorschauDreh || editEbene != editVorschauEbene)) {
        editorVorschauBauen();
        Bauer g;
        gitterBauen(g, editHoverX, editHoverZ, editEbene, 12);
        gitterNetz.hochladen(g);
    }
    mausVorher = maus;
}

void Spiel::editorZeichnen() {
    Mat4 sicht = sichtMatrix;
    Mat4 proj = projMatrix;
    schattenPass(Vec3(editZiel.x, editEbene * STUFE, editZiel.z), false);
    szeneZeichnen(sicht, proj, kameraOrt, false);
    glDepthMask(GL_FALSE);
    grafik.leuchten(0.8f);
    grafik.deckkraft(0.5f);
    grafik.zeichnen(gitterNetz);
    grafik.deckkraft(1.0f);
    grafik.leuchten(0.0f);
    glDepthMask(GL_TRUE);
    if (editHover && editVorschauTeil >= 0) {
        grafik.deckkraft(0.62f);
        grafik.toenung(Vec3(0.75f, 1.05f, 1.25f));
        grafik.leuchten(0.25f);
        grafik.zeichnen(vorschauNetz);
        grafik.zeichnen(vorschauLeucht);
        Stueck st;
        st.x = editHoverX;
        st.z = editHoverZ;
        st.y = editEbene;
        st.dreh = editDreh;
        grafik.modell(verschiebung(lokalZuWelt(st, Vec3(0.0f, 0.0f, 0.0f))) * drehungY(editDreh * PI * 0.5f));
        grafik.leuchten(1.2f);
        grafik.zeichnen(zeigerNetz);
        grafik.modell(einheit());
        grafik.leuchten(0.0f);
        grafik.toenung(Vec3(1.0f, 1.0f, 1.0f));
        grafik.deckkraft(1.0f);
    }
}

void Spiel::editorAnzeige() {
    float w = static_cast<float>(fenster.breite());
    float h = static_cast<float>(fenster.hoehe());
    schrift.beginnen(fenster.breite(), fenster.hoehe());
    gross.beginnen(fenster.breite(), fenster.hoehe());
    riesig.beginnen(fenster.breite(), fenster.hoehe());
    schrift.flaeche(0, 0, w, 64.0f, TAFEL);
    bool beenden_ = false;
    if (knopf(12.0f, 12.0f, 110.0f, 40.0f, "Zurück")) beenden_ = true;
    if (knopf(132.0f, 12.0f, 120.0f, 40.0f, "Testen (T)", true)) {
        if (!edit.hatStart()) meldung("Setz zuerst einen Start (Taste 4)");
        else if (!edit.hatZiel()) meldung("Setz noch ein Ziel (Taste 5)");
        else {
            schrift.beenden();
            gross.beenden();
            riesig.beenden();
            rennenStarten(edit, true);
            return;
        }
    }
    if (knopf(262.0f, 12.0f, 130.0f, 40.0f, "Speichern")) editorSpeichern();
    if (knopf(402.0f, 12.0f, 90.0f, 40.0f, "Neu")) {
        editorMerken();
        edit.leeren();
        Stueck s;
        s.teil = START;
        edit.setzen(s);
        edit.name = "Meine Strecke";
        editGeaendert = true;
    }
    if (knopf(502.0f, 12.0f, 110.0f, 40.0f, "Zufall")) {
        editorMerken();
        Strecke z = zufallsStrecke(static_cast<unsigned>(jetzt() * 1000.0) & 0xFFFFu, 24);
        std::string name = edit.name;
        edit = z;
        edit.name = name;
        edit.kennung.clear();
        editGeaendert = true;
    }
    bool tippt = tippZiel == &edit.name;
    float nx = 624.0f;
    float nb = std::max(160.0f, w - 262.0f - nx - 12.0f);
    schrift.flaeche(nx, 12.0f, nb, 40.0f, tippt ? Farbe(0.2f, 0.25f, 0.42f) : Farbe(0.1f, 0.12f, 0.22f));
    schreiben(nx + 12.0f, 20.0f, edit.name + (tippt && std::fmod(zeit, 1.0f) < 0.5f ? "|" : ""), HELL);
    if (ueber(nx, 12.0f, nb, 40.0f) && fenster.mausGedrueckt(Maustaste::Links)) tippZiel = &edit.name;
    if (tippt && texteingabe(edit.name, 28)) tippZiel = nullptr;

    float px = w - 252.0f;
    schrift.flaeche(px, 64.0f, 252.0f, h - 64.0f, TAFEL);
    schreiben(px + 14.0f, 74.0f, "Bauteile", GOLD);
    for (int i = 1; i < TEIL_ANZAHL; ++i) {
        float y = 104.0f + (i - 1) * 40.0f;
        std::string taste = i <= 9 ? std::to_string(i) : (i == 10 ? "0" : "");
        if (knopf(px + 10.0f, y, 232.0f, 34.0f, taste.empty() ? teilName(i) : taste + "  " + teilName(i), editTeil == i)) editTeil = i;
    }
    float iy = 104.0f + (TEIL_ANZAHL - 1) * 40.0f + 10.0f;
    schreiben(px + 14.0f, iy, "Ebene " + std::to_string(editEbene) + "   Drehung " + std::to_string(editDreh * 90), HELL);
    schreiben(px + 14.0f, iy + 28.0f, std::to_string(edit.stuecke.size()) + " Teile", GEDAEMPFT);
    const char* hilfe[] = {"Linksklick: setzen", "Rechtsklick: weg", "Rechts ziehen: Blick", "Mausrad: Zoom",
                           "WASD: schieben", "R drehen, Q/E Ebene", "Strg+Z zurück", "T testen, Esc fertig"};
    for (int i = 0; i < 8; ++i) schreiben(px + 14.0f, iy + 64.0f + i * 24.0f, hilfe[i], GEDAEMPFT);
    if (meldungZeit > 0.0f) mittig((w - 252.0f) * 0.5f, 84.0f, meldungText, GOLD);
    schrift.beenden();
    gross.beenden();
    riesig.beenden();
    if (beenden_) {
        editorSpeichern();
        ansichtWechseln(Ansicht::Haupt);
    }
}

}
