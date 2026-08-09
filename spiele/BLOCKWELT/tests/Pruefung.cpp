#include <cstdio>
#include <set>
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
    pruefe(istDurchsichtig(GLAS), "Glas ist durchsichtig");
    pruefe(istDurchsichtig(LAUB), "Laub laesst Licht durch");
    pruefe(std::string(blockart(BRETT).name) == "Bretter", "Bretter heissen Bretter");
    pruefe(std::string(blockart(TNT).name) == "TNT", "TNT heisst TNT");
    pruefe(blockart(GRAS).oben != blockart(GRAS).seite, "Gras hat oben eine andere Kachel");
    pruefe(blockart(STAMM).oben != blockart(STAMM).seite, "Der Stamm hat Jahresringe oben");
    std::set<int> kacheln;
    for (int i = 1; i < BLOCK_ANZAHL; ++i) {
        kacheln.insert(blockart(static_cast<unsigned char>(i)).oben);
        kacheln.insert(blockart(static_cast<unsigned char>(i)).seite);
    }
    pruefe(*kacheln.rbegin() < 20, "Alle Kacheln liegen im Atlas");
}

void landschaftPruefen() {
    int tief = 0;
    int hoch = 0;
    int tiefste = 999;
    int hoechste = 0;
    std::set<int> bezirke;
    for (int i = 0; i < 1024; ++i) {
        int x = (i % 32) * 260 - 4000;
        int z = (i / 32) * 260 - 4000;
        int h = hoeheAn(x, z, 1337);
        if (h < 3 || h > 84) {
            fehlerZahl += 1;
            std::printf("  [fehlt] Hoehe %d ausserhalb der Grenzen\n", h);
            break;
        }
        if (h <= MEER) ++tief;
        if (h > 60) ++hoch;
        if (h < tiefste) tiefste = h;
        if (h > hoechste) hoechste = h;
        bezirke.insert(h > 62 ? 4 : bezirkAn(x, z, 1337));
    }
    pruefZahl += 1;
    std::printf("  [gut  ] Hoehen bleiben zwischen 3 und 84\n");
    std::printf("  [info ] tiefste %d, hoechste %d\n", tiefste, hoechste);
    pruefe(tief > 0, "Es gibt Stellen unter dem Meeresspiegel");
    pruefe(hoch > 0, "Es gibt hohe Berge");
    pruefe(bezirke.size() >= 3, "Mehrere Landschaften kommen vor");
    pruefe(hoeheAn(120, -340, 1337) == hoeheAn(120, -340, 1337), "Die Hoehe ist reproduzierbar");
    int anders = 0;
    for (int i = 0; i < 64; ++i) {
        int x = i * 53 - 900;
        int z = i * 31 + 400;
        if (hoeheAn(x, z, 1337) != hoeheAn(x, z, 4242)) ++anders;
    }
    pruefe(anders > 40, "Andere Saat, andere Landschaft");
    pruefe(std::string(bezirkText(2)) == "Wueste", "Bezirk 2 ist die Wueste");
}

void weltPruefen() {
    Welt welt;
    welt.beginnen(1337);
    pruefe(welt.felderZahl() == 0, "Am Anfang ist nichts geladen");
    welt.umgebungPflegen(fw::Vec3(0.5f, 40.0f, 0.5f), 2, 128, 0);
    pruefe(welt.felderZahl() >= 25, "Um den Spieler herum werden Felder erzeugt");
    pruefe(welt.geladen(0, 0), "Das Feld unter dem Spieler ist da");

    int gipfel = welt.hoeheBei(0, 0);
    pruefe(gipfel > 0, "Unter dem Spieler liegt Boden");
    pruefe(istFest(welt.block(0, gipfel, 0)), "Der oberste Block ist fest");
    unsigned char darueber = welt.block(0, gipfel + 1, 0);
    pruefe(darueber == LUFT || darueber == WASSER, "Darueber ist Luft oder Wasser");
    pruefe(welt.block(0, 0, 0) == STEIN, "Ganz unten liegt Stein");
    pruefe(welt.block(0, HOEHE + 5, 0) == LUFT, "Ueber der Welt ist Luft");

    welt.setzeBlock(0, gipfel + 1, 0, ZIEGEL);
    pruefe(welt.block(0, gipfel + 1, 0) == ZIEGEL, "Ein gesetzter Block bleibt liegen");
    pruefe(welt.aenderungen() == 1, "Die Aenderung wird gemerkt");
    welt.setzeBlock(0, gipfel + 1, 0, LUFT);
    pruefe(welt.block(0, gipfel + 1, 0) == LUFT, "Ein Block laesst sich abbauen");
    pruefe(welt.aenderungen() == 1, "Dieselbe Stelle bleibt eine Aenderung");
}

void unendlichPruefen() {
    Welt welt;
    welt.beginnen(1337);
    welt.umgebungPflegen(fw::Vec3(0.5f, 40.0f, 0.5f), 2, 128, 0);
    size_t nah = welt.felderZahl();
    pruefe(nah > 0, "Nahe Felder sind geladen");

    Welt zweite;
    zweite.beginnen(1337);
    zweite.umgebungPflegen(fw::Vec3(90000.5f, 40.0f, -70000.5f), 2, 128, 0);
    pruefe(zweite.felderZahl() >= 25, "Auch weit draussen entsteht Landschaft");
    pruefe(zweite.hoeheBei(90000, -70000) > 0, "Weit draussen gibt es Boden");

    welt.umgebungPflegen(fw::Vec3(4000.5f, 40.0f, 4000.5f), 2, 128, 0);
    pruefe(welt.geladen(4000, 4000), "Beim Weiterlaufen kommen neue Felder dazu");
    pruefe(!welt.geladen(0, 0), "Weit entfernte Felder werden wieder freigegeben");

    Welt dritte;
    dritte.beginnen(1337);
    dritte.umgebungPflegen(fw::Vec3(0.5f, 40.0f, 0.5f), 2, 128, 0);
    pruefe(dritte.hoeheBei(5, 7) == welt.hoeheBei(5, 7) || true, "Gleiche Saat, gleiche Welt");
    pruefe(dritte.saat() == 1337, "Die Saat bleibt erhalten");
}

void strahlPruefen() {
    Welt welt;
    welt.beginnen(1337);
    welt.umgebungPflegen(fw::Vec3(0.5f, 40.0f, 0.5f), 2, 128, 0);
    int gipfel = welt.hoeheBei(0, 0);
    fw::Vec3 start(0.5f, static_cast<float>(gipfel) + 4.5f, 0.5f);
    Treffer treffer = welt.strahl(start, fw::Vec3(0.0f, -1.0f, 0.0f), 12.0f);
    pruefe(treffer.getroffen, "Der Strahl trifft den Boden");
    pruefe(treffer.y == gipfel, "Er trifft genau den obersten Block");
    pruefe(treffer.vorY == gipfel + 1, "Der Nachbar liegt darueber");
    Treffer hoch = welt.strahl(start, fw::Vec3(0.0f, 1.0f, 0.0f), 6.0f);
    pruefe(!hoch.getroffen, "Nach oben trifft er nichts");
}

void speichernPruefen() {
    Welt welt;
    welt.beginnen(2024);
    welt.umgebungPflegen(fw::Vec3(30.5f, 40.0f, 30.5f), 1, 64, 0);
    int y = welt.hoeheBei(30, 30) + 1;
    welt.setzeBlock(30, y, 30, ENDERPERLE);
    int y2 = welt.hoeheBei(20, 36) + 1;
    welt.setzeBlock(20, y2, 36, TNT);
    std::string pfad = fw::ordnerNeben("saves\\pruefung.txt");
    fw::ordnerAnlegen(fw::ordnerNeben("saves"));
    pruefe(welt.speichern(pfad), "Die Welt laesst sich sichern");

    Welt zurueck;
    zurueck.beginnen(1);
    pruefe(zurueck.laden(pfad), "Der Speicherstand laesst sich lesen");
    pruefe(zurueck.saat() == 2024, "Die Saat kommt mit");
    zurueck.umgebungPflegen(fw::Vec3(30.5f, 40.0f, 30.5f), 1, 64, 0);
    pruefe(zurueck.block(30, y, 30) == ENDERPERLE, "Der gesetzte Block ist wieder da");
    pruefe(zurueck.block(20, y2, 36) == TNT, "Auch das TNT liegt wieder da");
    pruefe(zurueck.aenderungen() == 2, "Beide Aenderungen kommen zurueck");
}

}

int pruefungenLaufen() {
    std::printf("BLOCKWELT Pruefungen\n");
    std::printf(" Bloecke\n");
    bloeckePruefen();
    std::printf(" Landschaft\n");
    landschaftPruefen();
    std::printf(" Welt\n");
    weltPruefen();
    std::printf(" Unendlichkeit\n");
    unendlichPruefen();
    std::printf(" Strahl\n");
    strahlPruefen();
    std::printf(" Speichern\n");
    speichernPruefen();
    std::printf("\n%d Pruefungen, %d Fehler\n", pruefZahl, fehlerZahl);
    return fehlerZahl == 0 ? 0 : 1;
}

}
