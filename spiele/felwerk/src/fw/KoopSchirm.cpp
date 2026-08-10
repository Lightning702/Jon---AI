#include "KoopSchirm.hpp"

namespace fw {
namespace {

const char* standName(int stand) {
    switch (stand) {
        case KOOP_VERBINDET: return "verbindet";
        case KOOP_LOBBY: return "Lobby";
        case KOOP_LAEDT: return "laedt";
        case KOOP_SPIELT: return "laeuft";
        case KOOP_FEHLER: return "Fehler";
        default: return "aus";
    }
}

}

void KoopSchirm::tasten(Fenster& fenster, Koop& koop, unsigned long long saat, Vec3 start) {
    if (!sichtbar) return;

    if (fenster.tasteGedrueckt(VK_ESCAPE)) {
        if (tippt) {
            tippt = false;
            eingabe.clear();
        } else {
            sichtbar = false;
        }
        return;
    }

    if (tippt) {
        for (int taste = '0'; taste <= 'Z'; ++taste) {
            bool ziffer = taste >= '0' && taste <= '9';
            bool buchstabe = taste >= 'A' && taste <= 'Z';
            if (!ziffer && !buchstabe) continue;
            if (fenster.tasteGedrueckt(taste) && eingabe.size() < 6) {
                eingabe.push_back(static_cast<char>(taste));
            }
        }
        if (fenster.tasteGedrueckt(VK_BACK) && !eingabe.empty()) eingabe.pop_back();
        if (fenster.tasteGedrueckt(VK_RETURN) && eingabe.size() >= 4) {
            koop.beitreten(eingabe);
            tippt = false;
            eingabe.clear();
        }
        return;
    }

    if (koop.stand() == KOOP_AUS || koop.stand() == KOOP_FEHLER) {
        if (fenster.tasteGedrueckt('1')) koop.gastgeben(saat, start);
        if (fenster.tasteGedrueckt('2')) {
            tippt = true;
            eingabe.clear();
        }
        return;
    }

    if (koop.stand() == KOOP_LOBBY) {
        if (fenster.tasteGedrueckt(VK_RETURN) && koop.gastgeber()) koop.startBitten();
        if (fenster.tasteGedrueckt('B')) koop.bereitMelden(true);
    }
    if (fenster.tasteGedrueckt('L')) koop.verlassen();
}

void KoopSchirm::zeichnen(Schrift& schrift, const Koop& koop, int breite, int hoehe) {
    if (!sichtbar) return;
    const float w = 460.0f;
    const float zeile = schrift.zeilenhoehe();
    const float h = zeile * 11.0f + 44.0f;
    float x = breite * 0.5f - w * 0.5f;
    float y = hoehe * 0.5f - h * 0.5f;
    const Farbe grund(0.05f, 0.05f, 0.07f, 0.9f);
    const Farbe gold(0.98f, 0.86f, 0.42f, 1.0f);
    const Farbe tinte(0.95f, 0.94f, 0.93f, 0.96f);
    const Farbe blass(0.78f, 0.77f, 0.76f, 0.85f);

    schrift.flaeche(x, y, w, h, grund);
    schrift.rahmen(x, y, w, h, 1.5f, Farbe(0.83f, 0.69f, 0.22f, 0.85f));
    schrift.textMittig(breite * 0.5f, y + 14.0f, "Zusammen spielen", gold, 1.15f);

    float zy = y + 20.0f + zeile * 1.8f;
    auto schreib = [&](const std::string& text, Farbe farbe, float mass) {
        schrift.text(x + 26.0f, zy, text, farbe, mass);
        zy += zeile * 1.25f * mass;
    };

    if (tippt) {
        schreib("Freundschaftscode eingeben:", tinte, 1.0f);
        std::string sicht = eingabe;
        while (sicht.size() < 6) sicht.push_back('_');
        schrift.textMittig(breite * 0.5f, zy, sicht, gold, 2.0f);
        zy += zeile * 2.6f;
        schreib("Buchstaben und Ziffern tippen", blass, 0.9f);
        schreib("Enter verbindet, Esc bricht ab", blass, 0.9f);
        return;
    }

    int stand = koop.stand();
    if (stand == KOOP_AUS || stand == KOOP_FEHLER) {
        if (stand == KOOP_FEHLER && !koop.fehler().empty()) {
            schreib(koop.fehler(), Farbe(1.0f, 0.62f, 0.58f, 0.95f), 1.0f);
            zy += zeile * 0.3f;
        }
        schreib("1   Spiel erstellen", tinte, 1.05f);
        schreib("2   Einem Spiel beitreten", tinte, 1.05f);
        zy += zeile * 0.4f;
        schreib("Der Gastgeber bekommt einen Code aus sechs", blass, 0.88f);
        schreib("Zeichen. Wer beitritt, tippt ihn ein.", blass, 0.88f);
        schreib("Jon muss dafuer laufen.", blass, 0.88f);
        zy += zeile * 0.3f;
        schreib("Esc schliesst", blass, 0.88f);
        return;
    }

    schreib(std::string("Zustand: ") + standName(stand), tinte, 1.0f);
    if (!koop.hinweis().empty()) schreib(koop.hinweis(), blass, 0.95f);
    if (!koop.code().empty()) {
        zy += zeile * 0.2f;
        schrift.text(x + 26.0f, zy, "Code:", blass, 0.95f);
        schrift.text(x + 26.0f + schrift.textBreite("Code:  ", 0.95f), zy - zeile * 0.35f,
                     koop.code(), gold, 1.7f);
        zy += zeile * 1.9f;
    }
    if (!koop.einladung().empty()) schreib(std::string("Einladung: ") + koop.einladung(), blass, 0.82f);

    zy += zeile * 0.3f;
    schreib(std::string("Spieler: ") + std::to_string(koop.spielerzahl()), tinte, 0.95f);
    for (const KoopFreund& freund : koop.mitspieler()) {
        std::string zeileText = "  " + freund.name;
        if (freund.ping > 0.0f) zeileText += "   " + std::to_string(static_cast<int>(freund.ping)) + " ms";
        if (!freund.online) zeileText += "   (weg)";
        schreib(zeileText, blass, 0.9f);
    }

    zy += zeile * 0.3f;
    if (stand == KOOP_LOBBY && koop.gastgeber()) schreib("Enter startet die Runde", gold, 0.95f);
    if (stand == KOOP_LOBBY && !koop.gastgeber()) schreib("B meldet dich bereit", gold, 0.95f);
    schreib("L verlaesst  -  Esc schliesst", blass, 0.88f);
}

void KoopSchirm::randzeile(Schrift& schrift, const Koop& koop, int breite, int hoehe) {
    if (!koop.aktiv()) return;
    const float zeile = schrift.zeilenhoehe();
    std::string text = "Koop " + koop.code();
    if (koop.spielt()) {
        text += "   " + std::to_string(koop.spielerzahl()) + " Spieler";
        if (koop.ping() > 0.0f) text += "   " + std::to_string(static_cast<int>(koop.ping())) + " ms";
    } else if (!koop.hinweis().empty()) {
        text += "   " + koop.hinweis();
    }
    float w = schrift.textBreite(text, 0.85f) + 22.0f;
    float x = breite - w - 16.0f;
    float y = hoehe - zeile - 18.0f;
    schrift.flaeche(x, y, w, zeile + 10.0f, Farbe(0.05f, 0.05f, 0.07f, 0.5f));
    schrift.text(x + 11.0f, y + 5.0f, text, Farbe(0.96f, 0.9f, 0.72f, 0.9f), 0.85f);
}

}
