#include "Koop.hpp"

#include <algorithm>
#include <cstdio>

#include "Protokoll.hpp"
#include "Werkzeug.hpp"

namespace fw {
namespace {

constexpr int ABSICHT_GAST = 1;
constexpr int ABSICHT_BEITRITT = 2;
constexpr int ABSICHT_ZURUECK = 3;
constexpr float SENDERATE = 15.0f;
constexpr double VERZOEGERUNG = 0.12;

std::string grossbuchstaben(const std::string& text) {
    std::string aus = text;
    for (char& c : aus) {
        if (c >= 'a' && c <= 'z') c = static_cast<char>(c - 'a' + 'A');
    }
    return aus;
}

}

void Koop::anlegen(const std::string& spiel, const std::string& name) {
    spielName = spiel;
    if (!name.empty()) spielerName = name;
    phase = KOOP_AUS;
}

void Koop::beenden() {
    leitung.disconnect();
    phase = KOOP_AUS;
}

void Koop::serverSetzen(const std::string& neuerRechner, int neuesTor) {
    rechner = neuerRechner;
    tor = neuesTor > 0 ? neuesTor : 8759;
    heimRechner = rechner;
    heimTor = tor;
}

void Koop::verbindenBeginnen() {
    leitung.disconnect();
    handschlagRaus = false;
    freunde.clear();
    weltwerte.clear();
    ereignisse.clear();
    blockliste.clear();
    letzterSchnappschuss = 0;
    ereignisZeiger = 0;
    phase = KOOP_VERBINDET;
    standText = "Verbinde ...";
    fehlerText.clear();
    if (!leitung.connect(rechner, tor)) {
        fehlerText = "Der Koop-Server laeuft nicht";
        phase = KOOP_FEHLER;
    }
}

void Koop::gastgeben(unsigned long long saat, Vec3 start) {
    absicht = ABSICHT_GAST;
    willGastgeben = true;
    weltSaat = saat;
    startOrt = start;
    lobbyCode.clear();
    einladungText.clear();
    umleitSpruenge = 0;
    verbindenBeginnen();
}

void Koop::beitreten(const std::string& einladung) {
    absicht = ABSICHT_BEITRITT;
    willGastgeben = false;
    wunschCode = grossbuchstaben(putzen(einladung));
    umleitSpruenge = 0;
    rechner = heimRechner;
    tor = heimTor;
    verbindenBeginnen();
}

void Koop::verlassen() {
    if (leitung.online()) {
        js::Value nachricht = js::Value::object();
        nachricht.set("t", "leave");
        leitung.send(nachricht);
    }
    leitung.disconnect();
    phase = KOOP_AUS;
    freunde.clear();
    lobbyCode.clear();
    einladungText.clear();
    standText.clear();
    sitzungsmarke.clear();
    absicht = 0;
}

bool Koop::gastgeber() const { return willGastgeben; }

bool Koop::startpunktFrisch() {
    if (!startFrisch) return false;
    startFrisch = false;
    return true;
}

void Koop::handschlagSenden() {
    handschlagRaus = true;
    js::Value nachricht = js::Value::object();
    nachricht.set("name", spielerName);
    nachricht.set("model", std::string("default"));
    nachricht.set("game", spielName);
    if (absicht == ABSICHT_ZURUECK && !sitzungsmarke.empty()) {
        nachricht.set("t", "hello");
        nachricht.set("token", sitzungsmarke);
    } else if (absicht == ABSICHT_GAST) {
        nachricht.set("t", "create");
        nachricht.set("seed", static_cast<double>(weltSaat & 0x7FFFFFFFull));
        nachricht.set("max_players", 4);
        js::Value punkt = js::Value::object();
        punkt.set("x", startOrt.x);
        punkt.set("y", startOrt.y);
        punkt.set("z", startOrt.z);
        nachricht.set("spawn", punkt);
    } else {
        nachricht.set("t", "join");
        nachricht.set("code", wunschCode);
    }
    leitung.send(nachricht);
}

void Koop::bereitMelden(bool wert) {
    js::Value nachricht = js::Value::object();
    nachricht.set("t", "ready");
    nachricht.set("value", wert);
    leitung.send(nachricht);
}

void Koop::startBitten() {
    js::Value nachricht = js::Value::object();
    nachricht.set("t", "start");
    leitung.send(nachricht);
}

void Koop::geladenMelden() {
    js::Value nachricht = js::Value::object();
    nachricht.set("t", "scene");
    nachricht.set("phase", std::string("ready"));
    nachricht.set("scene", std::string("world"));
    leitung.send(nachricht);
}

void Koop::plaudern(const std::string& text) {
    if (text.empty()) return;
    js::Value nachricht = js::Value::object();
    nachricht.set("t", "chat");
    nachricht.set("text", text);
    leitung.send(nachricht);
}

void Koop::handlungSenden(const std::string& art, const std::string& kennung, double wert, Vec3 ort) {
    if (!spielt()) return;
    js::Value nachricht = js::Value::object();
    nachricht.set("t", "act");
    nachricht.set("kind", art);
    nachricht.set("id", kennung);
    nachricht.set("value", wert);
    nachricht.set("x", ort.x);
    nachricht.set("y", ort.y);
    nachricht.set("z", ort.z);
    leitung.send(nachricht);
}

void Koop::blockSenden(int x, int y, int z, int block, Vec3 ort) {
    if (!spielt()) return;
    js::Value nachricht = js::Value::object();
    nachricht.set("t", "act");
    nachricht.set("kind", std::string("block"));
    nachricht.set("x", x);
    nachricht.set("y", y);
    nachricht.set("z", z);
    nachricht.set("id", block);
    (void)ort;
    leitung.send(nachricht);
}

double Koop::netzZeit() const { return uhr + zeitversatz; }

Vec3 Koop::ortLesen(const js::Value& wert) {
    return Vec3(wert.get("x").asFloat(0.0f), wert.get("y").asFloat(0.0f), wert.get("z").asFloat(0.0f));
}

KoopFreund* Koop::freundSuchen(const std::string& kennung) {
    for (KoopFreund& freund : freunde) {
        if (freund.kennung == kennung) return &freund;
    }
    return nullptr;
}

void Koop::freundLoeschen(const std::string& kennung) {
    for (size_t i = 0; i < freunde.size(); ++i) {
        if (freunde[i].kennung != kennung) continue;
        freunde.erase(freunde.begin() + static_cast<long long>(i));
        return;
    }
}

void Koop::rundeLesen(const js::Value& lobby) {
    if (!lobby.isObject()) return;
    if (lobby.has("code")) lobbyCode = lobby.get("code").asString(lobbyCode);
    if (lobby.has("invite_tcp")) einladungText = lobby.get("invite_tcp").asString(einladungText);
    const js::Value& liste = lobby.get("players");
    for (size_t i = 0; i < liste.size(); ++i) {
        const js::Value& eintrag = liste.at(i);
        std::string kennung = eintrag.get("id").asString();
        if (kennung.empty() || kennung == eigeneKennung) continue;
        KoopFreund* freund = freundSuchen(kennung);
        if (freund == nullptr) {
            KoopFreund frisch;
            frisch.kennung = kennung;
            frisch.name = eintrag.get("name").asString("Spieler");
            frisch.platz = static_cast<int>(freunde.size()) + 1;
            freunde.push_back(frisch);
            freund = &freunde.back();
        }
        freund->name = eintrag.get("name").asString(freund->name);
        freund->online = eintrag.get("online").asBool(true);
        freund->ping = eintrag.get("ping").asFloat(freund->ping);
    }
}

void Koop::weltLesen(const js::Value& welt) {
    if (!welt.isObject()) return;
    for (const auto& eintrag : welt.members()) {
        const std::string& schluessel = eintrag.first;
        if (schluessel.size() > 2 && schluessel[0] == 'b' && schluessel[1] == ':') {
            int x = 0;
            int y = 0;
            int z = 0;
            if (std::sscanf(schluessel.c_str() + 2, "%d,%d,%d", &x, &y, &z) == 3) {
                int block = static_cast<int>(eintrag.second.asNumber(0.0));
                blockliste.push_back({x, y, z, block});
            }
        }
        weltwerte[schluessel] = eintrag.second.asNumber(0.0);
    }
}

void Koop::ereignisLesen(const js::Value& ereignis) {
    std::string art = ereignis.get("kind").asString();
    if (art.empty()) art = ereignis.get("t").asString();
    KoopEreignis eintrag;
    eintrag.art = art;
    eintrag.kennung = ereignis.get("id").asString();
    eintrag.wert = ereignis.get("value").asNumber(0.0);
    eintrag.ort = ortLesen(ereignis);
    ereignisse.push_back(eintrag);
}

void Koop::spielerFlicken(const std::string& kennung, const js::Value& flicken, double stempel) {
    if (kennung == eigeneKennung) {
        if (flicken.has("ping")) eigenPing = flicken.get("ping").asFloat(eigenPing);
        return;
    }
    KoopFreund* freund = freundSuchen(kennung);
    if (freund == nullptr) {
        KoopFreund frisch;
        frisch.kennung = kennung;
        frisch.name = flicken.get("name").asString("Spieler");
        frisch.platz = static_cast<int>(freunde.size()) + 1;
        freunde.push_back(frisch);
        freund = &freunde.back();
    }
    if (flicken.has("name")) freund->name = flicken.get("name").asString(freund->name);
    if (flicken.has("ping")) freund->ping = flicken.get("ping").asFloat(freund->ping);
    if (flicken.has("online")) freund->online = flicken.get("online").asBool(true);

    KoopProbe probe;
    if (!freund->puffer.empty()) probe = freund->puffer.back();
    probe.stempel = stempel;
    if (flicken.has("x")) probe.ort.x = flicken.get("x").asFloat(probe.ort.x);
    if (flicken.has("y")) probe.ort.y = flicken.get("y").asFloat(probe.ort.y);
    if (flicken.has("z")) probe.ort.z = flicken.get("z").asFloat(probe.ort.z);
    if (flicken.has("yaw")) probe.gierung = flicken.get("yaw").asFloat(probe.gierung);
    if (flicken.has("pitch")) probe.neigung = flicken.get("pitch").asFloat(probe.neigung);
    freund->puffer.push_back(probe);
    if (freund->puffer.size() > 24) freund->puffer.erase(freund->puffer.begin());
    if (freund->puffer.size() == 1) {
        freund->zeigeOrt = probe.ort;
        freund->zeigeGierung = probe.gierung;
    }
}

void Koop::schnappschuss(const js::Value& nachricht) {
    if (nachricht.has("time")) {
        double serverZeit = nachricht.get("time").asNumber(0.0) / 1000.0;
        double versatz = serverZeit - uhr;
        zeitversatz = zeitversatz == 0.0 ? versatz : zeitversatz * 0.9 + versatz * 0.1;
    }
    letzterSchnappschuss = nachricht.get("id").asInt(0);
    double stempel = netzZeit();

    if (nachricht.get("base").asInt(0) == 0) {
        for (KoopFreund& freund : freunde) freund.anwesend = false;
    }

    const js::Value& spieler = nachricht.get("players");
    if (spieler.isObject()) {
        for (const auto& eintrag : spieler.members()) {
            spielerFlicken(eintrag.first, eintrag.second, stempel);
            KoopFreund* freund = freundSuchen(eintrag.first);
            if (freund != nullptr) freund->anwesend = true;
        }
    }

    if (nachricht.has("world")) weltLesen(nachricht.get("world"));

    const js::Value& weg = nachricht.get("gone");
    for (size_t i = 0; i < weg.size(); ++i) freundLoeschen(weg.at(i).asString());

    const js::Value& liste = nachricht.get("ev");
    for (size_t i = 0; i < liste.size(); ++i) {
        const js::Value& ereignis = liste.at(i);
        int nummer = ereignis.get("eid").asInt(0);
        if (nummer <= ereignisZeiger) continue;
        ereignisZeiger = nummer;
        ereignisLesen(ereignis);
    }

    js::Value antwort = js::Value::object();
    antwort.set("t", "ack");
    antwort.set("snap", letzterSchnappschuss);
    antwort.set("ev", ereignisZeiger);
    leitung.send(antwort);
}

void Koop::empfangen(const js::Value& nachricht) {
    std::string art = nachricht.get("t").asString();

    if (art == "redirect") {
        if (umleitSpruenge >= 3) {
            fehlerText = "Gastgeber nicht erreichbar";
            phase = KOOP_FEHLER;
            return;
        }
        std::string ziel = nachricht.get("host").asString();
        if (ziel.empty()) {
            fehlerText = "Gastgeber nicht erreichbar";
            phase = KOOP_FEHLER;
            return;
        }
        std::string neuerCode = nachricht.get("code").asString(wunschCode);
        if (!neuerCode.empty()) wunschCode = grossbuchstaben(neuerCode);
        umleitSpruenge += 1;
        umleitRechner = ziel;
        int zielTor = nachricht.get("tcp_port").asInt(0);
        umleitTor = zielTor > 0 ? zielTor : tor;
        hatUmleitung = true;
        standText = "Gastgeber gefunden, verbinde ...";
        return;
    }

    if (art == "welcome") {
        eigeneKennung = nachricht.get("player_id").asString();
        sitzungsmarke = nachricht.get("token").asString(sitzungsmarke);
        einladungText = nachricht.get("invite_tcp").asString(einladungText);
        umleitSpruenge = 0;
        neuVersuche = 0;
        rundeLesen(nachricht.get("lobby"));
        if (nachricht.has("spawn")) {
            startOrt = ortLesen(nachricht.get("spawn"));
            startFrisch = true;
        }
        const js::Value& zustand = nachricht.get("state");
        if (zustand.isObject()) {
            weltwerte.clear();
            weltLesen(zustand.get("world"));
        }
        std::string rundenPhase = nachricht.get("lobby").get("phase").asString("lobby");
        if (rundenPhase == "playing" || rundenPhase == "paused") {
            phase = KOOP_LAEDT;
            standText = "Sitzung wird fortgesetzt ...";
        } else {
            phase = KOOP_LOBBY;
            standText = willGastgeben ? "Warte auf Mitspieler" : "In der Lobby, bereit";
            if (!willGastgeben) bereitMelden(true);
        }
        absicht = ABSICHT_ZURUECK;
        return;
    }
    if (art == "lobby") {
        rundeLesen(nachricht.get("lobby"));
        if (phase == KOOP_VERBINDET) phase = KOOP_LOBBY;
        return;
    }
    if (art == "start") {
        weltSaat = static_cast<unsigned long long>(nachricht.get("seed").asNumber(
            static_cast<double>(weltSaat)));
        const js::Value& punkte = nachricht.get("spawns");
        if (punkte.has(eigeneKennung)) {
            startOrt = ortLesen(punkte.get(eigeneKennung));
            startFrisch = true;
        }
        rundeLesen(nachricht.get("lobby"));
        phase = KOOP_LAEDT;
        geladenRaus = false;
        standText = "Welt wird geladen ...";
        return;
    }
    if (art == "sync") {
        char text[64];
        std::snprintf(text, sizeof(text), "Warte auf Mitspieler (%d/%d)",
                      static_cast<int>(nachricht.get("loaded").size()),
                      nachricht.get("total").asInt(1));
        standText = text;
        return;
    }
    if (art == "spawn") {
        const js::Value& punkte = nachricht.get("spawns");
        if (punkte.has(eigeneKennung)) {
            startOrt = ortLesen(punkte.get(eigeneKennung));
            startFrisch = true;
        }
        const js::Value& zustand = nachricht.get("state");
        if (zustand.isObject()) weltLesen(zustand.get("world"));
        phase = KOOP_SPIELT;
        standText = "Koop laeuft";
        sendenErzwingen = true;
        return;
    }
    if (art == "snap") {
        schnappschuss(nachricht);
        return;
    }
    if (art == "ping") {
        js::Value antwort = js::Value::object();
        antwort.set("t", "pong");
        antwort.set("s", nachricht.get("s").asInt(0));
        leitung.send(antwort);
        return;
    }
    if (art == "chat") {
        sprueche.push_back(nachricht.get("name").asString("Spieler") + ": " +
                           nachricht.get("text").asString());
        return;
    }
    if (art == "event") {
        ereignisLesen(nachricht);
        return;
    }
    if (art == "kick" || art == "closed") {
        fehlerText = nachricht.get("msg").asString("Die Runde wurde beendet");
        phase = KOOP_FEHLER;
        return;
    }
    if (art == "error" || art == "reject") {
        std::string text = nachricht.get("msg").asString("Fehler");
        if (phase == KOOP_LOBBY || phase == KOOP_LAEDT || phase == KOOP_SPIELT) {
            standText = text;
            return;
        }
        fehlerText = text;
        phase = KOOP_FEHLER;
        return;
    }
}

bool Koop::umleitungPruefen() {
    if (!hatUmleitung) return false;
    hatUmleitung = false;
    rechner = umleitRechner;
    tor = umleitTor;
    absicht = ABSICHT_BEITRITT;
    verbindenBeginnen();
    return true;
}

void Koop::schritt(float dt) {
    if (phase == KOOP_AUS) return;
    uhr += dt;
    leitung.update();

    if (leitung.state() == LEITUNG_FEHLER && phase != KOOP_FEHLER) {
        fehlerText = leitung.lastError().empty() ? "Verbindung verloren" : leitung.lastError();
        phase = KOOP_FEHLER;
    }
    if (leitung.online() && !handschlagRaus) handschlagSenden();

    js::Value nachricht;
    while (leitung.poll(nachricht)) empfangen(nachricht);

    if (umleitungPruefen()) return;
    if (phase == KOOP_LAEDT && !geladenRaus) {
        geladenRaus = true;
        geladenMelden();
    }
    if (phase != KOOP_LAEDT) geladenRaus = phase == KOOP_SPIELT ? geladenRaus : false;
    if (phase != KOOP_SPIELT) return;

    sendeUhr += dt;
    if (sendeUhr < 1.0f / SENDERATE) return;
    sendeUhr = 0.0f;

    bool geaendert = sendenErzwingen;
    sendenErzwingen = false;
    if (laengeQuadrat(eigen.ort - zuletzt.ort) > 0.000004f) geaendert = true;
    if (std::fabs(winkelDifferenz(eigen.gierung, zuletzt.gierung)) > 0.004f) geaendert = true;
    if (std::fabs(eigen.neigung - zuletzt.neigung) > 0.004f) geaendert = true;
    if (!geaendert) return;

    zuletzt = eigen;
    js::Value paket = js::Value::object();
    paket.set("t", "input");
    paket.set("x", eigen.ort.x);
    paket.set("y", eigen.ort.y);
    paket.set("z", eigen.ort.z);
    paket.set("vx", eigen.fahrt.x);
    paket.set("vy", eigen.fahrt.y);
    paket.set("vz", eigen.fahrt.z);
    paket.set("yaw", eigen.gierung);
    paket.set("pitch", eigen.neigung);
    leitung.send(paket);
}

void Koop::freundeBewegen(float dt) {
    double ziel = netzZeit() - VERZOEGERUNG;
    for (KoopFreund& freund : freunde) {
        if (freund.puffer.empty()) continue;
        Vec3 wunschOrt = freund.puffer.back().ort;
        float wunschGierung = freund.puffer.back().gierung;
        float wunschNeigung = freund.puffer.back().neigung;
        for (size_t i = 0; i + 1 < freund.puffer.size(); ++i) {
            const KoopProbe& a = freund.puffer[i];
            const KoopProbe& b = freund.puffer[i + 1];
            if (ziel < a.stempel || ziel > b.stempel) continue;
            float spanne = static_cast<float>(b.stempel - a.stempel);
            float t = spanne > 1e-5f ? static_cast<float>(ziel - a.stempel) / spanne : 1.0f;
            wunschOrt = mische(a.ort, b.ort, t);
            wunschGierung = a.gierung + winkelDifferenz(a.gierung, b.gierung) * t;
            wunschNeigung = mische(a.neigung, b.neigung, t);
            break;
        }
        Vec3 vorher = freund.zeigeOrt;
        float glaette = klemme(dt * 12.0f, 0.0f, 1.0f);
        freund.zeigeOrt = mische(freund.zeigeOrt, wunschOrt, glaette);
        freund.zeigeGierung += winkelDifferenz(freund.zeigeGierung, wunschGierung) * glaette;
        freund.zeigeNeigung = mische(freund.zeigeNeigung, wunschNeigung, glaette);
        Vec3 schritt = freund.zeigeOrt - vorher;
        schritt.y = 0.0f;
        freund.schrittTakt += laenge(schritt) * 3.4f;
    }
}

bool Koop::ereignisHolen(KoopEreignis& ziel) {
    if (ereignisse.empty()) return false;
    ziel = ereignisse.front();
    ereignisse.erase(ereignisse.begin());
    return true;
}

bool Koop::blockHolen(int& x, int& y, int& z, int& block) {
    if (blockliste.empty()) return false;
    std::array<int, 4> eintrag = blockliste.front();
    blockliste.erase(blockliste.begin());
    x = eintrag[0];
    y = eintrag[1];
    z = eintrag[2];
    block = eintrag[3];
    return true;
}

bool Koop::spruchHolen(std::string& zeile) {
    if (sprueche.empty()) return false;
    zeile = sprueche.front();
    sprueche.erase(sprueche.begin());
    return true;
}

double Koop::weltwert(const std::string& schluessel, double ersatz) const {
    auto es = weltwerte.find(schluessel);
    return es == weltwerte.end() ? ersatz : es->second;
}

}
