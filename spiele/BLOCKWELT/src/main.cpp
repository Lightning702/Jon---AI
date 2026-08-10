#include <cstdlib>
#include <string>

#include "spiel/Spiel.hpp"
#include "fw/Protokoll.hpp"
#include "fw/Werkzeug.hpp"

namespace blockwelt {
int pruefungenLaufen();
}

int main(int anzahl, char** werte) {
    blockwelt::Startwerte start;
    bool tests = false;

    for (int i = 1; i < anzahl; ++i) {
        std::string schalter = werte[i];
        auto folgt = [&](int versatz) -> std::string {
            return (i + versatz) < anzahl ? std::string(werte[i + versatz]) : std::string();
        };
        if (schalter == "-tests") {
            tests = true;
        } else if (schalter == "-vollbild") {
            start.vollbild = true;
        } else if (schalter == "-fenster") {
            start.vollbild = false;
        } else if (schalter == "-schnell") {
            start.schnellstart = true;
        } else if (schalter == "-ohneanzeige") {
            start.ohneAnzeige = true;
        } else if (schalter == "-neu") {
            start.frisch = true;
        } else if (schalter == "-breite") {
            start.breite = std::atoi(folgt(1).c_str());
            ++i;
        } else if (schalter == "-hoehe") {
            start.hoehe = std::atoi(folgt(1).c_str());
            ++i;
        } else if (schalter == "-bilder") {
            start.bilder = std::atoi(folgt(1).c_str());
            ++i;
        } else if (schalter == "-bild") {
            start.bilddatei = folgt(1);
            ++i;
        } else if (schalter == "-saat") {
            start.saat = static_cast<unsigned>(std::atoi(folgt(1).c_str()));
            ++i;
        } else if (schalter == "-zeit") {
            start.tageszeit = static_cast<float>(std::atof(folgt(1).c_str()));
            ++i;
        } else if (schalter == "-blick") {
            start.gierung = static_cast<float>(std::atof(folgt(1).c_str()));
            start.neigung = static_cast<float>(std::atof(folgt(2).c_str()));
            start.blickGesetzt = true;
            i += 2;
        } else if (schalter == "-baue") {
            start.sofortBau = std::atoi(folgt(1).c_str());
            ++i;
        } else if (schalter == "-koopstart") {
            start.koopStarten = true;
        } else if (schalter == "-koop") {
            start.koopWunsch = folgt(1);
            ++i;
        } else if (schalter == "-grafik") {
            start.qualitaet = std::atoi(folgt(1).c_str());
            ++i;
        }
    }

    fw::protokollDatei(fw::ordnerNeben("blockwelt.log"));
    if (tests) {
        int fehler = blockwelt::pruefungenLaufen();
        fw::protokollSchliessen();
        return fehler;
    }

    if (start.breite < 640) start.breite = 640;
    if (start.hoehe < 480) start.hoehe = 480;

    blockwelt::Spiel spiel;
    if (!spiel.starten(start)) {
        fw::warnung("Start fehlgeschlagen, siehe blockwelt.log");
        fw::protokollSchliessen();
        return 2;
    }
    spiel.laufen();
    spiel.beenden();
    fw::protokollSchliessen();
    return 0;
}
