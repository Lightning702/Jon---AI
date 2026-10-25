#include <cstdlib>
#include <string>

#include "spiel/Spiel.hpp"
#include "fw/Protokoll.hpp"
#include "fw/Werkzeug.hpp"

namespace blitzbahn {
int pruefungenLaufen();
}

int main(int anzahl, char** werte) {
    blitzbahn::Startwerte start;
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
        } else if (schalter == "-ansicht") {
            start.ansicht = folgt(1);
            ++i;
        } else if (schalter == "-strecke") {
            start.strecke = folgt(1);
            ++i;
        } else if (schalter == "-autopilot") {
            start.autopilot = true;
        } else if (schalter == "-koop") {
            start.koopWunsch = folgt(1);
            ++i;
        } else if (schalter == "-koopstart") {
            start.koopStarten = true;
        }
    }

    fw::protokollDatei(fw::ordnerNeben("blitzbahn.log"));
    if (tests) {
        int fehler = blitzbahn::pruefungenLaufen();
        fw::protokollSchliessen();
        return fehler;
    }
    if (start.breite < 800) start.breite = 800;
    if (start.hoehe < 560) start.hoehe = 560;

    blitzbahn::Spiel spiel;
    if (!spiel.starten(start)) {
        fw::warnung("Start fehlgeschlagen, siehe blitzbahn.log");
        fw::protokollSchliessen();
        return 2;
    }
    spiel.laufen();
    spiel.beenden();
    fw::protokollSchliessen();
    return 0;
}
