#include "Partikel.hpp"

#include "Farben.hpp"

namespace harmonie {

using namespace fw;

void Funken::erstellen() {
    teilchen.clear();
    teilchen.reserve(hoechstzahl);
}

void Funken::freigeben() { netz.freigeben(); }

void Funken::streuen(Funke art, Vec3 ort, int anzahl, float wucht) {
    for (int i = 0; i < anzahl; ++i) {
        if (teilchen.size() >= hoechstzahl) return;
        Teilchen stueck;
        stueck.art = art;
        stueck.ort = ort;
        stueck.dreh = wuerfel.bereich(0.0f, TAU);
        float winkel = wuerfel.bereich(0.0f, TAU);
        float schwung = wuerfel.bereich(0.5f, 1.6f) * wucht;
        switch (art) {
            case Funke::Blatt:
                stueck.fahrt = Vec3(std::cos(winkel) * 0.5f, wuerfel.bereich(-0.15f, 0.25f),
                                    std::sin(winkel) * 0.5f);
                stueck.farbe = mische(FARBE_LAUB_WARM, FARBE_BLUETE[1], wuerfel.einheit());
                stueck.dauer = wuerfel.bereich(5.0f, 10.0f);
                stueck.mass = wuerfel.bereich(0.07f, 0.13f);
                break;
            case Funke::Gischt:
                stueck.fahrt = Vec3(std::cos(winkel) * 0.7f, wuerfel.bereich(0.4f, 1.3f) * schwung,
                                    std::sin(winkel) * 0.7f);
                stueck.farbe = FARBE_SCHAUM;
                stueck.dauer = wuerfel.bereich(0.7f, 1.5f);
                stueck.mass = wuerfel.bereich(0.05f, 0.12f);
                break;
            case Funke::Herz:
                stueck.fahrt = Vec3(std::cos(winkel) * 0.25f, wuerfel.bereich(0.8f, 1.4f),
                                    std::sin(winkel) * 0.25f);
                stueck.farbe = FARBE_BLUETE[0];
                stueck.dauer = wuerfel.bereich(1.2f, 2.0f);
                stueck.mass = wuerfel.bereich(0.09f, 0.15f);
                break;
            case Funke::Glanz:
                stueck.fahrt = Vec3(std::cos(winkel) * schwung, wuerfel.bereich(1.2f, 2.6f) * wucht,
                                    std::sin(winkel) * schwung);
                stueck.farbe = mische(FARBE_LICHT, FARBE_BLUETE[wuerfel.ganz(0, 4)], 0.45f);
                stueck.dauer = wuerfel.bereich(1.1f, 2.4f);
                stueck.mass = wuerfel.bereich(0.06f, 0.14f);
                break;
            case Funke::Staub:
                stueck.fahrt = Vec3(std::cos(winkel) * 0.12f, wuerfel.bereich(0.02f, 0.14f),
                                    std::sin(winkel) * 0.12f);
                stueck.farbe = mische(FARBE_SCHAUM, FARBE_LICHT, wuerfel.einheit());
                stueck.dauer = wuerfel.bereich(6.0f, 12.0f);
                stueck.mass = wuerfel.bereich(0.03f, 0.07f);
                break;
        }
        teilchen.push_back(stueck);
    }
}

void Funken::aktualisieren(float dt, float zeit) {
    for (size_t i = 0; i < teilchen.size();) {
        Teilchen& stueck = teilchen[i];
        stueck.alter += dt;
        if (stueck.alter >= stueck.dauer) {
            teilchen[i] = teilchen.back();
            teilchen.pop_back();
            continue;
        }
        switch (stueck.art) {
            case Funke::Blatt:
                stueck.fahrt.y -= 0.55f * dt;
                stueck.fahrt.y = klemme(stueck.fahrt.y, -0.55f, 0.6f);
                stueck.ort.x += std::sin(zeit * 1.7f + stueck.dreh) * 0.5f * dt;
                stueck.ort.z += std::cos(zeit * 1.4f + stueck.dreh) * 0.4f * dt;
                break;
            case Funke::Gischt:
                stueck.fahrt.y -= 3.4f * dt;
                break;
            case Funke::Herz:
                stueck.fahrt.y = mische(stueck.fahrt.y, 0.9f, dt * 2.0f);
                stueck.ort.x += std::sin(zeit * 5.0f + stueck.dreh) * 0.35f * dt;
                break;
            case Funke::Glanz:
                stueck.fahrt.y -= 2.6f * dt;
                break;
            case Funke::Staub:
                stueck.ort.x += std::sin(zeit * 0.6f + stueck.dreh) * 0.22f * dt;
                stueck.ort.z += std::cos(zeit * 0.5f + stueck.dreh) * 0.22f * dt;
                break;
        }
        stueck.ort += stueck.fahrt * dt;
        stueck.ort += luft * (dt * (stueck.art == Funke::Blatt ? 0.6f : 0.18f));
        stueck.dreh += dt * 1.6f;
        ++i;
    }
}

void Funken::zeichnen(Maler& maler, Vec3 rechts, Vec3 oben) {
    if (teilchen.empty()) return;
    bauer.leeren();
    for (const Teilchen& stueck : teilchen) {
        float leben = stueck.alter / stueck.dauer;
        float schwund = stueck.art == Funke::Staub ? std::sin(leben * PI)
                                                   : klemme(1.0f - leben * leben, 0.0f, 1.0f);
        float mass = stueck.mass * (0.5f + schwund * 0.8f);
        Vec3 r = rechts * mass;
        Vec3 o = oben * mass;
        Vec3 mitte = stueck.ort;
        Vec3 farbe = stueck.farbe * (0.55f + schwund * 0.65f);
        if (stueck.art == Funke::Herz) {
            bauer.viereck(mitte - r - o, mitte + r - o, mitte + r * 0.2f + o * 1.4f,
                          mitte - r * 0.2f + o * 1.4f, farbe, 0.2f);
            bauer.viereck(mitte - r * 1.2f + o * 0.6f, mitte + r * 1.2f + o * 0.6f,
                          mitte + r * 0.8f + o * 1.5f, mitte - r * 0.8f + o * 1.5f, farbe, 0.2f);
        } else {
            bauer.viereck(mitte - r - o, mitte + r - o, mitte + r + o, mitte - r + o, farbe, 0.15f);
        }
    }
    netz.hochladen(bauer, true);
    maler.modell(einheit());
    maler.leuchten(0.55f);
    maler.zeichnen(netz);
    maler.leuchten(0.0f);
}

}
