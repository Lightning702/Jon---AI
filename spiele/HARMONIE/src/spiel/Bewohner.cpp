#include "Bewohner.hpp"

#include "Farben.hpp"

namespace harmonie {
namespace {

using namespace fw;

void tierBauen(Bauer& bauer, int art) {
    Vec3 fell = FARBE_TIER[art % 3];
    if (art == 0) {
        bauer.kugel(Vec3(0.0f, 0.85f, 0.0f), Vec3(0.42f, 0.4f, 0.62f), fell, 7, 10);
        bauer.roehre(Vec3(0.0f, 1.05f, -0.35f), 0.15f, 0.13f, 0.72f, fell * 1.02f, 8);
        bauer.kugel(Vec3(0.0f, 1.92f, -0.4f), Vec3(0.22f, 0.24f, 0.26f), fell * 1.05f, 6, 9);
        for (float sx : {-1.0f, 1.0f}) {
            bauer.roehre(Vec3(sx * 0.1f, 2.08f, -0.42f), 0.06f, 0.0f, 0.28f, fell * 0.9f, 5);
        }
        for (float sx : {-1.0f, 1.0f}) {
            for (float sz : {-1.0f, 1.0f}) {
                bauer.roehre(Vec3(sx * 0.24f, 0.0f, sz * 0.34f), 0.09f, 0.08f, 0.55f, fell * 0.85f, 6);
            }
        }
    } else if (art == 1) {
        bauer.kugel(Vec3(0.0f, 0.55f, 0.0f), Vec3(0.5f, 0.44f, 0.6f), fell, 7, 10);
        bauer.kugel(Vec3(0.0f, 0.62f, -0.55f), Vec3(0.24f, 0.24f, 0.24f), fell * 0.82f, 6, 9);
        for (float sx : {-1.0f, 1.0f}) {
            bauer.kugel(Vec3(sx * 0.22f, 0.66f, -0.6f), Vec3(0.1f, 0.07f, 0.1f), fell * 0.7f, 4, 6);
        }
        for (float sx : {-1.0f, 1.0f}) {
            for (float sz : {-1.0f, 1.0f}) {
                bauer.roehre(Vec3(sx * 0.26f, 0.0f, sz * 0.3f), 0.08f, 0.07f, 0.3f, fell * 0.6f, 6);
            }
        }
    } else {
        bauer.kugel(Vec3(0.0f, 0.42f, 0.0f), Vec3(0.46f, 0.34f, 0.66f), fell, 7, 10);
        bauer.kugel(Vec3(0.0f, 0.46f, -0.62f), Vec3(0.3f, 0.26f, 0.28f), fell * 1.04f, 6, 9);
        for (float sx : {-1.0f, 1.0f}) {
            bauer.kugel(Vec3(sx * 0.16f, 0.66f, -0.6f), Vec3(0.08f, 0.08f, 0.06f), fell * 0.75f, 4, 6);
        }
        for (float sx : {-1.0f, 1.0f}) {
            for (float sz : {-1.0f, 1.0f}) {
                bauer.roehre(Vec3(sx * 0.26f, 0.0f, sz * 0.32f), 0.09f, 0.08f, 0.18f, fell * 0.7f, 6);
            }
        }
    }
    bauer.kugel(Vec3(-0.09f, art == 0 ? 1.96f : 0.58f, art == 0 ? -0.6f : -0.8f),
                Vec3(0.035f, 0.045f, 0.035f), Vec3(0.1f, 0.09f, 0.12f), 4, 6);
    bauer.kugel(Vec3(0.09f, art == 0 ? 1.96f : 0.58f, art == 0 ? -0.6f : -0.8f),
                Vec3(0.035f, 0.045f, 0.035f), Vec3(0.1f, 0.09f, 0.12f), 4, 6);
}

void begleiterBauen(Bauer& bauer, int art) {
    Vec3 fell = art == 0 ? ausByte(212, 176, 140) : ausByte(126, 126, 142);
    bauer.kugel(Vec3(0.0f, 0.3f, 0.0f), Vec3(0.2f, 0.17f, 0.3f), fell, 6, 9);
    bauer.kugel(Vec3(0.0f, 0.42f, -0.28f), Vec3(0.16f, 0.15f, 0.15f), fell * 1.05f, 6, 9);
    for (float sx : {-1.0f, 1.0f}) {
        bauer.roehre(Vec3(sx * 0.08f, 0.5f, -0.28f), 0.05f, 0.0f, 0.14f, fell * 0.85f, 5);
        bauer.kugel(Vec3(sx * 0.055f, 0.44f, -0.4f), Vec3(0.025f, 0.03f, 0.025f),
                    Vec3(0.08f, 0.08f, 0.1f), 4, 6);
    }
    for (float sx : {-1.0f, 1.0f}) {
        for (float sz : {-1.0f, 1.0f}) {
            bauer.roehre(Vec3(sx * 0.12f, 0.0f, sz * 0.16f), 0.05f, 0.045f, 0.16f, fell * 0.8f, 5);
        }
    }
    bauer.roehre(Vec3(0.0f, 0.34f, 0.28f), 0.045f, 0.02f, 0.3f, fell * 0.9f, 5);
}

}

void Volk::gestaltBauen(Bauer& bauer, Vec3 haut, Vec3 haar, Vec3 kleid, int frisur, bool hut) {
    Vec3 hose = kleid * 0.72f;
    Vec3 schuh = Vec3(0.28f, 0.22f, 0.24f);

    for (float sx : {-1.0f, 1.0f}) {
        bauer.roehre(Vec3(sx * 0.13f, 0.0f, 0.0f), 0.11f, 0.1f, 0.34f, hose, 7);
        bauer.kugel(Vec3(sx * 0.13f, 0.06f, 0.04f), Vec3(0.13f, 0.08f, 0.17f), schuh, 5, 7);
    }
    bauer.kugel(Vec3(0.0f, 0.62f, 0.0f), Vec3(0.29f, 0.3f, 0.24f), kleid, 8, 11);
    bauer.roehre(Vec3(0.0f, 0.32f, 0.0f), 0.27f, 0.3f, 0.28f, kleid * 0.95f, 10);
    for (float sx : {-1.0f, 1.0f}) {
        bauer.kugel(Vec3(sx * 0.3f, 0.6f, 0.0f), Vec3(0.09f, 0.19f, 0.09f), kleid * 1.04f, 6, 8);
        bauer.kugel(Vec3(sx * 0.31f, 0.44f, 0.02f), Vec3(0.075f, 0.075f, 0.075f), haut, 5, 7);
    }
    bauer.kugel(Vec3(0.0f, 1.06f, 0.0f), Vec3(0.31f, 0.32f, 0.3f), haut, 10, 13);
    bauer.kugel(Vec3(0.0f, 0.85f, 0.0f), Vec3(0.1f, 0.07f, 0.1f), haut * 0.95f, 5, 7);

    Vec3 augenfarbe(0.14f, 0.12f, 0.18f);
    for (float sx : {-1.0f, 1.0f}) {
        bauer.kugel(Vec3(sx * 0.11f, 1.09f, -0.26f), Vec3(0.043f, 0.055f, 0.03f), augenfarbe, 5, 7);
        bauer.kugel(Vec3(sx * 0.098f, 1.105f, -0.288f), Vec3(0.016f, 0.016f, 0.012f),
                    Vec3(1.0f, 1.0f, 1.0f), 4, 5);
        bauer.kugel(Vec3(sx * 0.2f, 1.0f, -0.235f), Vec3(0.055f, 0.032f, 0.03f),
                    ausByte(246, 172, 172), 4, 6);
    }
    bauer.kugel(Vec3(0.0f, 0.985f, -0.29f), Vec3(0.032f, 0.02f, 0.02f), ausByte(196, 106, 106), 4, 6);

    if (frisur == 0) {
        bauer.halbkugel(Vec3(0.0f, 1.09f, 0.0f), Vec3(0.335f, 0.3f, 0.325f), haar, 6, 12);
        bauer.kugel(Vec3(0.0f, 1.14f, 0.2f), Vec3(0.24f, 0.2f, 0.2f), haar * 0.96f, 6, 9);
    } else if (frisur == 1) {
        bauer.halbkugel(Vec3(0.0f, 1.08f, 0.0f), Vec3(0.34f, 0.34f, 0.33f), haar, 6, 12);
        for (float sx : {-1.0f, 1.0f}) {
            bauer.kugel(Vec3(sx * 0.3f, 1.0f, 0.06f), Vec3(0.13f, 0.24f, 0.15f), haar * 0.98f, 6, 8);
        }
    } else if (frisur == 2) {
        bauer.halbkugel(Vec3(0.0f, 1.1f, 0.0f), Vec3(0.33f, 0.26f, 0.32f), haar, 5, 12);
        bauer.kugel(Vec3(0.0f, 1.34f, 0.06f), Vec3(0.15f, 0.15f, 0.15f), haar * 1.05f, 6, 8);
    } else {
        bauer.halbkugel(Vec3(0.0f, 1.09f, 0.0f), Vec3(0.335f, 0.32f, 0.33f), haar, 6, 12);
        bauer.kugel(Vec3(0.0f, 1.02f, 0.24f), Vec3(0.26f, 0.3f, 0.16f), haar * 0.94f, 6, 9);
    }
    if (hut) {
        bauer.roehre(Vec3(0.0f, 1.3f, 0.0f), 0.5f, 0.44f, 0.05f, FARBE_STAND[2], 14);
        bauer.roehre(Vec3(0.0f, 1.34f, 0.0f), 0.28f, 0.24f, 0.26f, FARBE_STAND[2] * 1.05f, 12);
    }
}

void Volk::erstellen(const Welt& welt, unsigned saat, int anzahl) {
    wuerfel = Zufall(saat * 48271u + 11u);
    for (int i = 0; i < 6; ++i) {
        Bauer bauer;
        Vec3 haut = FARBE_HAUT[i % 4];
        Vec3 haar = FARBE_HAAR[i % 6];
        Vec3 kleid = FARBE_KLEID[i % 6];
        gestaltBauen(bauer, haut, haar, kleid, i % 4, i == 3);
        gestalten[i].netz.hochladen(bauer);
        gestalten[i].haar = haar;
        gestalten[i].kleid = kleid;
    }
    for (int i = 0; i < 3; ++i) {
        Bauer bauer;
        tierBauen(bauer, i);
        tierNetze[i].hochladen(bauer);
    }
    for (int i = 0; i < 2; ++i) {
        Bauer bauer;
        begleiterBauen(bauer, i);
        begleiterNetze[i].hochladen(bauer);
    }
    {
        Bauer bauer;
        bauer.quader(Vec3(0.0f, 0.0f, 0.0f), Vec3(0.34f, 0.06f, 0.16f), FARBE_HOLZ_HELL);
        bauer.quader(Vec3(0.0f, 0.12f, 0.0f), Vec3(0.3f, 0.05f, 0.14f), FARBE_HOLZ);
        brett.hochladen(bauer);
    }
    {
        Bauer bauer;
        bauer.scheibe(Vec3(0.0f, 0.0f, 0.0f), 1.0f, Vec3(0.16f, 0.14f, 0.2f), 18);
        schatten.hochladen(bauer);
    }
    {
        Bauer bauer;
        bauer.kugel(Vec3(0.0f, 0.12f, 0.0f), Vec3(0.3f, 0.34f, 0.3f), Vec3(1.0f, 1.0f, 1.0f), 8, 11,
                    0.25f);
        bauer.roehre(Vec3(0.0f, -0.34f, 0.0f), 0.0f, 0.16f, 0.34f, Vec3(1.0f, 1.0f, 1.0f), 8, 0.25f);
        bauer.kugel(Vec3(-0.1f, 0.24f, -0.2f), Vec3(0.07f, 0.07f, 0.05f), Vec3(2.2f, 2.2f, 2.2f), 5,
                    7, 0.5f);
        zeiger.hochladen(bauer);
    }

    volk.clear();
    begleiter.clear();
    const Bezirk heimaten[4] = {Bezirk::Herz, Bezirk::Herz, Bezirk::Farm, Bezirk::Werft};
    for (int i = 0; i < anzahl; ++i) {
        Bewohner person;
        person.heimat = i % 8 == 0 ? Bezirk::Berg : heimaten[i % 4];
        unsigned streuer = static_cast<unsigned>(i * 977 + 13);
        person.ort = zufallszielAuf(welt, person.heimat, streuer);
        person.ziel = person.ort;
        person.gestalt = wuerfel.ganz(0, 6);
        person.tempo = wuerfel.bereich(1.15f, 1.95f);
        person.takt = wuerfel.bereich(0.0f, TAU);
        person.warten = wuerfel.bereich(0.0f, 3.0f);
        person.wunschUhr = wuerfel.bereich(4.0f, 150.0f);
        person.unterwegsNach = person.heimat;
        volk.push_back(person);
    }
    for (int i = 0; i < 4 && i < static_cast<int>(volk.size()); ++i) {
        Begleiter tier;
        tier.folgt = i * 3;
        tier.art = i % 2;
        tier.ort = volk[tier.folgt].ort;
        begleiter.push_back(tier);
        volk[tier.folgt].haustier = i;
    }
}

void Volk::freigeben() {
    for (Gestalt& gestalt : gestalten) gestalt.netz.freigeben();
    for (Netz& netz : tierNetze) netz.freigeben();
    for (Netz& netz : begleiterNetze) netz.freigeben();
    brett.freigeben();
    schatten.freigeben();
    zeiger.freigeben();
}

int Volk::wuenscheZaehlen() const {
    int summe = 0;
    for (const Bewohner& person : volk) {
        if (person.wunsch != Gabe::Keine) summe += 1;
    }
    return summe;
}

Bewohner* Volk::naechsterBewohner(Vec3 ort, float weite) {
    Bewohner* beste = nullptr;
    float besteWeite = weite;
    for (Bewohner& person : volk) {
        Vec3 nach = person.ort - ort;
        nach.y = 0.0f;
        float abstand = laenge(nach);
        if (abstand < besteWeite) {
            besteWeite = abstand;
            beste = &person;
        }
    }
    return beste;
}

void Volk::wunschErfuellen(Bewohner& person) {
    person.wunsch = Gabe::Keine;
    person.wunschUhr = wuerfel.bereich(40.0f, 90.0f);
    person.beschenkt = true;
    person.jubel = 1.0f;
    person.warten = 1.4f;
}

void Volk::feiernLassen(Vec3 sammelpunkt) {
    festLaeuft = true;
    festOrt = sammelpunkt;
    for (Bewohner& person : volk) {
        person.laune = Laune::Jubeln;
        person.warten = 0.0f;
    }
}

Vec3 Volk::zufallszielAuf(const Welt& welt, Bezirk bezirk, unsigned& streuer) const {
    const Insel& stueck = welt.insel(bezirk);
    for (int versuch = 0; versuch < 24; ++versuch) {
        streuer = streuer * 1664525u + 1013904223u;
        float w = static_cast<float>(streuer % 10000u) / 10000.0f * TAU;
        streuer = streuer * 1664525u + 1013904223u;
        float r = std::sqrt(static_cast<float>(streuer % 10000u) / 10000.0f) * stueck.radius * 0.78f;
        float x = stueck.mitte.x + std::cos(w) * r;
        float z = stueck.mitte.y + std::sin(w) * r;
        if (welt.aufLand(x, z, 1.5f)) return Vec3(x, welt.bodenBei(x, z), z);
    }
    return welt.mittelpunkt(bezirk);
}

void Volk::neuesZiel(Bewohner& person, const Welt& welt) {
    unsigned streuer = static_cast<unsigned>(wuerfel.naechste());
    if (person.laune == Laune::Wandern) {
        const Insel& herz = welt.insel(Bezirk::Herz);
        const Insel& ziel = welt.insel(person.unterwegsNach);
        Vec2 richtung(ziel.mitte.x - herz.mitte.x, ziel.mitte.y - herz.mitte.y);
        float weite = laenge(richtung);
        Vec2 einheit = weite > 0.001f ? richtung * (1.0f / weite) : Vec2(1.0f, 0.0f);
        if (person.wegPunkt == 0) {
            float d = herz.radius * 0.84f;
            person.ziel = Vec3(herz.mitte.x + einheit.x * d, 0.0f, herz.mitte.y + einheit.y * d);
        } else if (person.wegPunkt == 1) {
            float d = weite - ziel.radius * 0.84f;
            person.ziel = Vec3(herz.mitte.x + einheit.x * d, 0.0f, herz.mitte.y + einheit.y * d);
        } else {
            person.laune = Laune::Schlendern;
            person.heimat = person.unterwegsNach;
            person.ziel = zufallszielAuf(welt, person.heimat, streuer);
        }
        person.ziel.y = welt.bodenBei(person.ziel.x, person.ziel.z);
        person.wegPunkt += 1;
        return;
    }
    if (person.laune == Laune::Helfen) {
        person.ziel = welt.leuchtturmFuss() + Vec3(std::cos(static_cast<float>(streuer % 628) * 0.01f) * 4.2f,
                                                   0.0f,
                                                   std::sin(static_cast<float>(streuer % 628) * 0.01f) * 4.2f);
        person.ziel.y = welt.bodenBei(person.ziel.x, person.ziel.z);
        return;
    }
    person.ziel = zufallszielAuf(welt, person.heimat, streuer);
}

void Volk::aktualisieren(float dt, const Welt& welt, Vec3 spieler, bool feiern) {
    if (feiern) feierZeit = 4.0f;
    if (feierZeit > 0.0f) feierZeit -= dt;
    if (festLaeuft) {
        for (Bewohner& person : volk) {
            Vec3 nach = festOrt - person.ort;
            nach.y = 0.0f;
            float weite = laenge(nach);
            person.takt += dt * 2.0f;
            if (weite > 7.0f) {
                Vec3 schritt = nach * (1.0f / weite) * (person.tempo * 1.3f * dt);
                Vec3 versuch = person.ort + schritt;
                float boden = welt.bodenBei(versuch.x, versuch.z);
                if (boden > 0.05f) {
                    versuch.y = boden;
                    person.ort = versuch;
                }
                person.richtung += winkelDifferenz(person.richtung, std::atan2(nach.x, nach.z)) *
                                   klemme(dt * 6.0f, 0.0f, 1.0f);
                person.jubel = 0.0f;
            } else {
                person.jubel = 1.0f;
            }
        }
        for (Begleiter& tier : begleiter) {
            if (tier.folgt < 0 || tier.folgt >= static_cast<int>(volk.size())) continue;
            const Bewohner& herrchen = volk[tier.folgt];
            tier.ort = mische(tier.ort, herrchen.ort, klemme(dt * 2.0f, 0.0f, 1.0f));
            tier.ort.y = welt.bodenBei(tier.ort.x, tier.ort.z);
            tier.takt += dt * 6.0f;
        }
        return;
    }

    for (Bewohner& person : volk) {
        person.takt += dt * (1.4f + person.tempo * 0.5f);
        if (person.wunsch == Gabe::Keine) {
            person.wunschUhr -= dt;
            if (person.wunschUhr <= 0.0f) {
                const Gabe gaben[3] = {Gabe::Korn, Gabe::Stein, Gabe::Brett};
                person.wunsch = gaben[wuerfel.ganz(0, 3)];
                person.wunschUhr = 0.0f;
            }
        }
        if (feierZeit > 0.0f) {
            person.jubel = klemme(person.jubel + dt * 3.0f, 0.0f, 1.0f);
        } else {
            person.jubel = klemme(person.jubel - dt * 2.0f, 0.0f, 1.0f);
        }
        if (person.jubel > 0.5f) continue;

        if (person.warten > 0.0f) {
            person.warten -= dt;
            continue;
        }
        Vec3 nach = person.ziel - person.ort;
        nach.y = 0.0f;
        float weite = laenge(nach);
        if (weite < 0.7f) {
            if (person.laune == Laune::Helfen && person.traegtBrett) {
                person.traegtBrett = false;
                offeneLieferungen += 1;
                person.laune = Laune::Wandern;
                person.unterwegsNach = Bezirk::Herz;
                person.wegPunkt = 0;
                person.warten = 1.2f;
                neuesZiel(person, welt);
                continue;
            }
            person.warten = wuerfel.bereich(0.8f, 3.6f);
            if (person.laune == Laune::Schlendern && wuerfel.chance(0.32f)) {
                person.laune = Laune::Wandern;
                person.wegPunkt = 0;
                const Bezirk ziele[4] = {Bezirk::Herz, Bezirk::Farm, Bezirk::Berg, Bezirk::Werft};
                person.unterwegsNach = ziele[wuerfel.ganz(0, 4)];
                if (person.unterwegsNach == person.heimat) person.laune = Laune::Schlendern;
                if (person.heimat != Bezirk::Herz && person.unterwegsNach != Bezirk::Herz) {
                    person.unterwegsNach = Bezirk::Herz;
                }
            } else if (person.laune == Laune::Schlendern && person.heimat == Bezirk::Herz &&
                       wuerfel.chance(0.22f)) {
                person.laune = Laune::Helfen;
                person.traegtBrett = true;
                person.unterwegsNach = Bezirk::Werft;
                person.wegPunkt = 0;
                person.laune = Laune::Wandern;
            }
            neuesZiel(person, welt);
            if (person.traegtBrett && person.laune == Laune::Wandern &&
                person.unterwegsNach == Bezirk::Werft && person.wegPunkt > 2) {
                person.laune = Laune::Helfen;
            }
            continue;
        }

        Vec3 richtung = nach * (1.0f / weite);
        float ziehen = 1.0f;
        Vec3 zumSpieler = spieler - person.ort;
        zumSpieler.y = 0.0f;
        if (laenge(zumSpieler) < 2.2f) ziehen = 0.35f;
        Vec3 schritt = richtung * (person.tempo * ziehen * dt);
        Vec3 versuch = person.ort + schritt;
        float boden = welt.bodenBei(versuch.x, versuch.z);
        if (boden < 0.05f) {
            person.warten = 0.4f;
            neuesZiel(person, welt);
            continue;
        }
        versuch.y = boden;
        person.ort = versuch;
        float wunsch = std::atan2(richtung.x, richtung.z);
        person.richtung += winkelDifferenz(person.richtung, wunsch) * klemme(dt * 6.0f, 0.0f, 1.0f);
    }

    for (Begleiter& tier : begleiter) {
        if (tier.folgt < 0 || tier.folgt >= static_cast<int>(volk.size())) continue;
        const Bewohner& herrchen = volk[tier.folgt];
        Vec3 wunsch = herrchen.ort - Vec3(std::sin(herrchen.richtung), 0.0f, std::cos(herrchen.richtung)) * 0.9f;
        Vec3 nach = wunsch - tier.ort;
        nach.y = 0.0f;
        float weite = laenge(nach);
        if (weite > 0.35f) {
            Vec3 schritt = nach * (1.0f / weite) * klemme(weite * 2.4f, 0.4f, 3.4f) * dt;
            tier.ort += schritt;
            tier.ort.y = welt.bodenBei(tier.ort.x, tier.ort.z);
            tier.richtung += winkelDifferenz(tier.richtung, std::atan2(nach.x, nach.z)) *
                             klemme(dt * 7.0f, 0.0f, 1.0f);
        }
        tier.takt += dt * 5.0f;
    }
}

int Volk::lieferungenAbholen() {
    int wert = offeneLieferungen;
    offeneLieferungen = 0;
    return wert;
}

void Volk::zeichnenLeute(Maler& maler, float zeit) {
    for (const Bewohner& person : volk) {
        bool geht = person.warten <= 0.0f && person.jubel < 0.5f;
        float wippen = geht ? std::sin(person.takt * 2.2f) : std::sin(zeit * 1.6f + person.takt) * 0.25f;
        float hub = geht ? std::fabs(std::sin(person.takt * 2.2f)) * 0.09f : 0.0f;
        float sprung = person.jubel * (0.35f + std::fabs(std::sin(zeit * 7.0f)) * 0.35f);
        float stauchen = 1.0f - hub * 0.55f + person.jubel * 0.06f;
        Mat4 modell = verschiebung(person.ort + Vec3(0.0f, hub + sprung, 0.0f)) *
                      drehungY(person.richtung + wippen * 0.06f) *
                      skalierung(Vec3(FIGUR_MASS / stauchen, FIGUR_MASS * stauchen,
                                      FIGUR_MASS / stauchen)) *
                      drehungZ(wippen * 0.05f);
        maler.modell(modell);
        maler.zeichnen(gestalten[person.gestalt % 6].netz);
        if (person.wunsch != Gabe::Keine && person.jubel < 0.5f) {
            Vec3 farbe = person.wunsch == Gabe::Korn
                             ? FARBE_KORN
                             : (person.wunsch == Gabe::Stein ? FARBE_FELS_HELL : FARBE_HOLZ_HELL);
            float schweben = std::sin(zeit * 2.4f + person.takt) * 0.09f;
            Mat4 blase = verschiebung(person.ort +
                                      Vec3(0.0f, 2.35f * FIGUR_MASS + hub + schweben, 0.0f)) *
                         drehungY(zeit * 0.8f);
            maler.modell(blase);
            maler.toenung(farbe);
            maler.leuchten(0.12f);
            maler.zeichnen(zeiger);
            maler.leuchten(0.0f);
            maler.toenung(Vec3(1.0f, 1.0f, 1.0f));
        }
        if (person.traegtBrett) {
            Mat4 last = verschiebung(person.ort +
                                     Vec3(0.0f, 1.02f * FIGUR_MASS + hub + sprung, 0.0f)) *
                        drehungY(person.richtung) * verschiebung(Vec3(0.0f, 0.0f, -0.38f));
            maler.modell(last);
            maler.zeichnen(brett);
        }
    }
    for (const Begleiter& tier : begleiter) {
        float hub = std::fabs(std::sin(tier.takt)) * 0.06f;
        Mat4 modell = verschiebung(tier.ort + Vec3(0.0f, hub, 0.0f)) * drehungY(tier.richtung);
        maler.modell(modell);
        maler.zeichnen(begleiterNetze[tier.art % 2]);
    }
    maler.modell(einheit());
}

void Volk::zeichnenTiere(Maler& maler, const Welt& welt, float zeit) {
    for (const Tier& tier : welt.tiere()) {
        float hub = std::sin(zeit * 1.3f + tier.takt) * 0.04f;
        Mat4 modell = verschiebung(tier.ort + Vec3(0.0f, hub, 0.0f)) *
                      drehungY(tier.richtung + std::sin(zeit * 0.7f + tier.takt) * 0.12f);
        maler.modell(modell);
        maler.zeichnen(tierNetze[tier.art % 3]);
    }
    maler.modell(einheit());
}

void Volk::zeichnenSchatten(Maler& maler, const Welt& welt) {
    maler.deckkraft(0.24f);
    for (const Bewohner& person : volk) {
        float boden = welt.bodenBei(person.ort.x, person.ort.z);
        Mat4 modell = verschiebung(Vec3(person.ort.x, boden + 0.05f, person.ort.z)) *
                      skalierung(Vec3(0.42f * FIGUR_MASS, 1.0f, 0.32f * FIGUR_MASS));
        maler.modell(modell);
        maler.zeichnen(schatten);
    }
    for (const Tier& tier : welt.tiere()) {
        Mat4 modell = verschiebung(Vec3(tier.ort.x, tier.ort.y + 0.05f, tier.ort.z)) *
                      skalierung(Vec3(0.55f, 1.0f, 0.62f));
        maler.modell(modell);
        maler.zeichnen(schatten);
    }
    maler.deckkraft(1.0f);
    maler.modell(einheit());
}

}
