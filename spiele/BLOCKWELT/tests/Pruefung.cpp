#include <cstdio>
#include <string>

#include "spiel/Bloecke.hpp"
#include "spiel/Welt.hpp"
#include "fw/Werkzeug.hpp"

namespace blockwelt {
namespace {

int fehlerZahl = 0;
int pruefZahl = 0;

void pruefe(bool bedingung, const char* was) {
    pruefZahl += 1;
    if (!bedingung) {
        fehlerZahl += 1;
        std::printf("  [fehlt] %s\n", was);
    } else {
        std::printf("  [gut  ] %s\n", was);
    }
}

void bloeckePruefen() {
    pruefe(istFest(STEIN), "Stein ist fest");
    pruefe(!istFest(LUFT), "Luft ist nicht fest");
    pruefe(!istFest(WASSER), "Durch Wasser laeuft man hindurch");
    pruefe(istFluessig(WASSER), "Wasser ist fluessig");
    pruefe(blockart(GLAS).sichtdurch, "Glas ist durchsichtig");
    pruefe(blockart(LEUCHTSTEIN).leuchten > 0.0f, "Leuchtstein leuchtet");
    pruefe(std::string(blockart(BRETT).name) == "Bretter", "Bretter heissen Bretter");
}

void weltPruefen() {
    Welt welt;
    welt.erzeugen(5);
    pruefe(welt.chunkZahl() == CHUNKS * CHUNKS, "Alle Felder sind angelegt");
    pruefe(!welt.innen(-1, 0, 0), "Ausserhalb ist ausserhalb");
    pruefe(welt.innen(WEITE - 1, HOEHE - 1, WEITE - 1), "Die letzte Ecke liegt drin");
    pruefe(welt.block(-5, 3, 2) == LUFT, "Ausserhalb liefert Luft");

    int mitteX = WEITE / 2;
    int mitteZ = WEITE / 2;
    int gipfel = welt.hoeheBei(mitteX, mitteZ);
    pruefe(gipfel > 3 && gipfel < HOEHE - 4, "Der Boden liegt in vernuenftiger Hoehe");
    pruefe(istFest(welt.block(mitteX, gipfel, mitteZ)), "Auf dem Gipfel steht ein fester Block");
    pruefe(welt.block(mitteX, gipfel + 1, mitteZ) == LUFT ||
               welt.block(mitteX, gipfel + 1, mitteZ) == WASSER,
           "Ueber dem Gipfel ist Luft oder Wasser");
    pruefe(welt.block(mitteX, 0, mitteZ) == STEIN, "Ganz unten liegt Stein");

    welt.setzeBlock(mitteX, gipfel + 1, mitteZ, ZIEGEL);
    pruefe(welt.block(mitteX, gipfel + 1, mitteZ) == ZIEGEL, "Ein gesetzter Block bleibt liegen");
    pruefe(welt.aenderungen() == 1, "Die Aenderung wird gemerkt");
    welt.setzeBlock(mitteX, gipfel + 1, mitteZ, LUFT);
    pruefe(welt.block(mitteX, gipfel + 1, mitteZ) == LUFT, "Ein Block laesst sich abbauen");

    Welt zweite;
    zweite.erzeugen(5);
    pruefe(zweite.hoeheBei(mitteX, mitteZ) == gipfel, "Gleiche Saat ergibt die gleiche Welt");
    Welt dritte;
    dritte.erzeugen(6);
    bool anders = false;
    for (int i = 0; i < 40 && !anders; ++i) {
        if (dritte.hoeheBei(10 + i, 10 + i) != welt.hoeheBei(10 + i, 10 + i)) anders = true;
    }
    pruefe(anders, "Eine andere Saat ergibt eine andere Welt");
}

void strahlPruefen() {
    Welt welt;
    welt.erzeugen(5);
    int x = WEITE / 2;
    int z = WEITE / 2;
    int y = welt.hoeheBei(x, z);
    fw::Vec3 start(static_cast<float>(x) + 0.5f, static_cast<float>(y) + 4.5f,
                   static_cast<float>(z) + 0.5f);
    Treffer treffer = welt.strahl(start, fw::Vec3(0.0f, -1.0f, 0.0f), 12.0f);
    pruefe(treffer.getroffen, "Der Strahl trifft den Boden");
    pruefe(treffer.y == y, "Er trifft genau den obersten Block");
    pruefe(treffer.vorY == y + 1, "Der Nachbar liegt darueber");

    Treffer daneben = welt.strahl(start, fw::Vec3(0.0f, 1.0f, 0.0f), 6.0f);
    pruefe(!daneben.getroffen || daneben.y > y, "Nach oben trifft er den Boden nicht");
}

void speichernPruefen() {
    Welt welt;
    welt.erzeugen(9);
    int x = 30;
    int z = 30;
    int y = welt.hoeheBei(x, z) + 1;
    welt.setzeBlock(x, y, z, LEUCHTSTEIN);
    std::string pfad = fw::ordnerNeben("saves\\pruefung.txt");
    fw::ordnerAnlegen(fw::ordnerNeben("saves"));
    pruefe(welt.speichern(pfad), "Die Welt laesst sich sichern");

    Welt zurueck;
    zurueck.erzeugen(9);
    pruefe(zurueck.laden(pfad), "Der Speicherstand laesst sich lesen");
    pruefe(zurueck.block(x, y, z) == LEUCHTSTEIN, "Der gesetzte Block ist wieder da");
    pruefe(zurueck.saat() == 9, "Die Saat kommt mit");
}

}

int pruefungenLaufen() {
    std::printf("BLOCKWELT Pruefungen\n");
    std::printf(" Bloecke\n");
    bloeckePruefen();
    std::printf(" Welt\n");
    weltPruefen();
    std::printf(" Strahl\n");
    strahlPruefen();
    std::printf(" Speichern\n");
    speichernPruefen();
    std::printf("\n%d Pruefungen, %d Fehler\n", pruefZahl, fehlerZahl);
    return fehlerZahl == 0 ? 0 : 1;
}

}
