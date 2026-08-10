#pragma once

#include <array>
#include <string>
#include <unordered_map>
#include <vector>

#include "Leitung.hpp"
#include "Mathe.hpp"

namespace fw {

enum KoopStand {
    KOOP_AUS = 0,
    KOOP_VERBINDET,
    KOOP_LOBBY,
    KOOP_LAEDT,
    KOOP_SPIELT,
    KOOP_FEHLER
};

struct KoopProbe {
    double stempel = 0.0;
    Vec3 ort;
    float gierung = 0.0f;
    float neigung = 0.0f;
};

struct KoopFreund {
    std::string kennung;
    std::string name;
    int platz = 0;
    float ping = 0.0f;
    bool online = true;
    bool anwesend = false;
    Vec3 zeigeOrt;
    float zeigeGierung = 0.0f;
    float zeigeNeigung = 0.0f;
    float schrittTakt = 0.0f;
    std::vector<KoopProbe> puffer;
};

struct KoopEreignis {
    std::string art;
    std::string kennung;
    double wert = 0.0;
    Vec3 ort;
};

struct KoopZustand {
    Vec3 ort;
    Vec3 fahrt;
    float gierung = 0.0f;
    float neigung = 0.0f;
};

class Koop {
public:
    void anlegen(const std::string& spiel, const std::string& name);
    void beenden();

    void gastgeben(unsigned long long saat, Vec3 start);
    void beitreten(const std::string& einladung);
    void verlassen();
    void serverSetzen(const std::string& rechner, int tor);

    void bereitMelden(bool wert);
    void startBitten();
    void geladenMelden();
    void plaudern(const std::string& text);

    void eigenerZustand(const KoopZustand& zustand) { eigen = zustand; }
    void handlungSenden(const std::string& art, const std::string& kennung, double wert, Vec3 ort);
    void blockSenden(int x, int y, int z, int block, Vec3 ort);

    void schritt(float dt);
    void freundeBewegen(float dt);

    int stand() const { return phase; }
    bool aktiv() const { return phase == KOOP_LOBBY || phase == KOOP_LAEDT || phase == KOOP_SPIELT; }
    bool spielt() const { return phase == KOOP_SPIELT; }
    bool gastgeber() const;
    const std::string& code() const { return lobbyCode; }
    const std::string& einladung() const { return einladungText; }
    const std::string& fehler() const { return fehlerText; }
    const std::string& hinweis() const { return standText; }
    unsigned long long saat() const { return weltSaat; }
    Vec3 startpunkt() const { return startOrt; }
    bool startpunktFrisch();
    float ping() const { return eigenPing; }
    int spielerzahl() const { return static_cast<int>(freunde.size()) + 1; }
    const std::vector<KoopFreund>& mitspieler() const { return freunde; }

    bool ereignisHolen(KoopEreignis& ziel);
    bool blockHolen(int& x, int& y, int& z, int& block);
    bool spruchHolen(std::string& zeile);
    double weltwert(const std::string& schluessel, double ersatz = 0.0) const;

private:
    void empfangen(const js::Value& nachricht);
    void schnappschuss(const js::Value& nachricht);
    void spielerFlicken(const std::string& kennung, const js::Value& flicken, double stempel);
    void rundeLesen(const js::Value& lobby);
    void weltLesen(const js::Value& welt);
    void ereignisLesen(const js::Value& ereignis);
    KoopFreund* freundSuchen(const std::string& kennung);
    void freundLoeschen(const std::string& kennung);
    void handschlagSenden();
    void verbindenBeginnen();
    bool umleitungPruefen();
    double netzZeit() const;
    static Vec3 ortLesen(const js::Value& wert);

    Leitung leitung;
    std::string spielName = "harmonie";
    std::string rechner = "127.0.0.1";
    int tor = 8759;
    std::string heimRechner = "127.0.0.1";
    int heimTor = 8759;
    std::string spielerName = "Spieler";
    std::string eigeneKennung;
    std::string sitzungsmarke;
    std::string lobbyCode;
    std::string einladungText;
    std::string fehlerText;
    std::string standText;
    std::string wunschCode;

    std::vector<KoopFreund> freunde;
    std::vector<KoopEreignis> ereignisse;
    std::vector<std::string> sprueche;
    std::unordered_map<std::string, double> weltwerte;
    std::vector<std::array<int, 4>> blockliste;

    std::string umleitRechner;
    int umleitTor = 0;
    bool hatUmleitung = false;
    int umleitSpruenge = 0;

    int phase = KOOP_AUS;
    int absicht = 0;
    unsigned long long weltSaat = 0;
    Vec3 startOrt;
    bool startFrisch = false;
    bool willGastgeben = false;
    double zeitversatz = 0.0;
    double uhr = 0.0;
    float sendeUhr = 0.0f;
    float neuUhr = 0.0f;
    int neuVersuche = 0;
    float eigenPing = 0.0f;
    int letzterSchnappschuss = 0;
    int ereignisZeiger = 0;
    KoopZustand eigen;
    KoopZustand zuletzt;
    bool handschlagRaus = false;
    bool geladenRaus = false;
    bool sendenErzwingen = false;
};

}
