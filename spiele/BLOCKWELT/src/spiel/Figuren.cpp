#include "Figuren.hpp"

#include <algorithm>

namespace blockwelt {

using namespace fw;

namespace {

constexpr float BREITE = 0.31f;
constexpr float KOERPER = 1.78f;

}

const char* bauwerkName(Bauwerk werk) {
    switch (werk) {
        case Bauwerk::Haus: return "Haus";
        case Bauwerk::Turm: return "Turm";
        case Bauwerk::Bruecke: return "Bruecke";
        case Bauwerk::Baum: return "Baum";
        case Bauwerk::Leuchtfeuer: return "Leuchtfeuer";
    }
    return "";
}

void Spieler::setzen(Vec3 neu) {
    ort = neu;
    fahrt = Vec3(0.0f, 0.0f, 0.0f);
}

void Spieler::blickSetzen(float gierung, float neigung) {
    gier = gierung;
    neig = klemme(neigung, -1.52f, 1.52f);
}

Vec3 Spieler::blick() const {
    return Vec3(std::sin(gier) * std::cos(neig), std::sin(neig), std::cos(gier) * std::cos(neig));
}

void Spieler::umsehen(float dx, float dy) {
    gier -= dx * 0.0032f;
    neig = klemme(neig - dy * 0.0032f, -1.52f, 1.52f);
}

void Spieler::springen() {
    if (amBoden || schwimmt) fahrt.y = schwimmt ? 4.4f : 8.1f;
}

bool Spieler::trifft(const Welt& welt, Vec3 pruefOrt) const {
    int x0 = static_cast<int>(std::floor(pruefOrt.x - BREITE));
    int x1 = static_cast<int>(std::floor(pruefOrt.x + BREITE));
    int y0 = static_cast<int>(std::floor(pruefOrt.y));
    int y1 = static_cast<int>(std::floor(pruefOrt.y + KOERPER));
    int z0 = static_cast<int>(std::floor(pruefOrt.z - BREITE));
    int z1 = static_cast<int>(std::floor(pruefOrt.z + BREITE));
    for (int y = y0; y <= y1; ++y) {
        for (int z = z0; z <= z1; ++z) {
            for (int x = x0; x <= x1; ++x) {
                if (welt.festBei(x, y, z)) return true;
            }
        }
    }
    return false;
}

void Spieler::schritt(float dt, const Welt& welt, Fenster& fenster, bool eingabeAn) {
    Vec3 vorne(std::sin(gier), 0.0f, std::cos(gier));
    Vec3 rechts(vorne.z, 0.0f, -vorne.x);
    Vec3 wunsch(0.0f, 0.0f, 0.0f);
    if (eingabeAn) {
        if (fenster.taste('W')) wunsch += vorne;
        if (fenster.taste('S')) wunsch -= vorne;
        if (fenster.taste('D')) wunsch += rechts;
        if (fenster.taste('A')) wunsch -= rechts;
    }
    float laenge2 = laenge(wunsch);
    if (laenge2 > 0.01f) {
        wunsch = wunsch * (1.0f / laenge2);
        laufTakt += dt * 7.0f;
    } else {
        laufTakt = 0.0f;
    }

    unsigned char kopfBlock = welt.block(static_cast<int>(std::floor(ort.x)),
                                         static_cast<int>(std::floor(ort.y + 0.9f)),
                                         static_cast<int>(std::floor(ort.z)));
    schwimmt = istFluessig(kopfBlock);

    float tempo = fenster.taste(VK_SHIFT) ? 8.6f : 5.0f;
    if (schwimmt) tempo *= 0.55f;
    if (fliegt) tempo *= fenster.taste(VK_SHIFT) ? 2.4f : 1.7f;

    fahrt.x = wunsch.x * tempo;
    fahrt.z = wunsch.z * tempo;

    if (fliegt) {
        float steig = 0.0f;
        if (eingabeAn && fenster.taste(VK_SPACE)) steig += 1.0f;
        if (eingabeAn && fenster.taste(VK_CONTROL)) steig -= 1.0f;
        fahrt.y = steig * tempo * 0.8f;
    } else {
        float schwere = schwimmt ? 6.5f : 25.0f;
        fahrt.y -= schwere * dt;
        if (schwimmt) fahrt.y = klemme(fahrt.y, -2.4f, 5.0f);
        if (fahrt.y < -55.0f) fahrt.y = -55.0f;
    }

    Vec3 versuch = ort;
    versuch.x += fahrt.x * dt;
    if (trifft(welt, versuch)) versuch.x = ort.x;
    versuch.z += fahrt.z * dt;
    if (trifft(welt, versuch)) versuch.z = ort.z;

    amBoden = false;
    float schrittY = fahrt.y * dt;
    Vec3 hochRunter = versuch;
    hochRunter.y += schrittY;
    if (trifft(welt, hochRunter)) {
        if (schrittY < 0.0f) amBoden = true;
        fahrt.y = 0.0f;
    } else {
        versuch.y = hochRunter.y;
    }

    if (!fliegt && amBoden) {
        Vec3 stufe = versuch;
        stufe.y += 0.02f;
        (void)stufe;
    }

    ort = versuch;
    if (ort.y < -8.0f) {
        ort.y = 50.0f;
        fahrt.y = 0.0f;
    }
    ort.x = klemme(ort.x, 1.0f, static_cast<float>(WEITE - 1));
    ort.z = klemme(ort.z, 1.0f, static_cast<float>(WEITE - 1));
}

void MiniJon::erstellen() {
    Bauer bauer;
    Vec3 dunkel(0.06f, 0.06f, 0.08f);
    Vec3 gold(0.83f, 0.69f, 0.22f);
    bauer.kugel(Vec3(0.0f, 0.0f, 0.0f), Vec3(0.34f, 0.34f, 0.34f), dunkel, 10, 14, 0.2f);
    for (int i = 0; i < 30; ++i) {
        float w0 = static_cast<float>(i) / 30.0f * TAU;
        float w1 = static_cast<float>(i + 1) / 30.0f * TAU;
        Vec3 a(std::cos(w0) * 0.35f, std::sin(w0) * 0.35f, 0.0f);
        Vec3 b(std::cos(w1) * 0.35f, std::sin(w1) * 0.35f, 0.0f);
        bauer.band(a, b, 0.05f, 0.05f, gold);
    }
    for (float sx : {-1.0f, 1.0f}) {
        bauer.kugel(Vec3(sx * 0.12f, 0.05f, -0.3f), Vec3(0.055f, 0.07f, 0.04f), gold, 6, 8, 0.6f);
        bauer.kugel(Vec3(sx * 0.108f, 0.072f, -0.325f), Vec3(0.02f, 0.02f, 0.015f),
                    Vec3(1.0f, 1.0f, 1.0f), 4, 6);
    }
    for (int i = 0; i < 7; ++i) {
        float t = static_cast<float>(i) / 6.0f;
        float x = mische(-0.12f, 0.12f, t);
        float y = -0.1f - std::sin(t * PI) * 0.06f;
        bauer.kugel(Vec3(x, y, -0.31f), Vec3(0.026f, 0.026f, 0.02f), gold, 4, 6);
    }
    netz.hochladen(bauer);
}

void MiniJon::freigeben() { netz.freigeben(); }

void MiniJon::setzen(Vec3 neu) {
    stelle = neu;
    ziel = neu;
}

void MiniJon::planFuer(Bauwerk werk, const Welt& welt, int mx, int my, int mz) {
    plan.clear();
    auto lege = [&](int x, int y, int z, unsigned char id) {
        if (!welt.innen(x, y, z)) return;
        plan.push_back({x, y, z, id});
    };
    if (werk == Bauwerk::Haus) {
        const int b = 3;
        for (int y = 0; y < 4; ++y) {
            for (int dz = -b; dz <= b; ++dz) {
                for (int dx = -b; dx <= b; ++dx) {
                    bool rand = std::abs(dx) == b || std::abs(dz) == b;
                    if (!rand) continue;
                    if (y == 1 && dz == b && std::abs(dx) <= 1) continue;
                    if (y == 2 && dz == b && std::abs(dx) <= 1) continue;
                    unsigned char id = BRETT;
                    if (y == 2 && (std::abs(dx) == 2 || std::abs(dz) == 2)) id = GLAS;
                    lege(mx + dx, my + y, mz + dz, id);
                }
            }
        }
        for (int dz = -b; dz <= b; ++dz) {
            for (int dx = -b; dx <= b; ++dx) lege(mx + dx, my - 1, mz + dz, BRETT);
        }
        for (int lage = 0; lage <= b; ++lage) {
            int weite = b - lage;
            for (int dz = -weite; dz <= weite; ++dz) {
                for (int dx = -weite; dx <= weite; ++dx) {
                    if (std::abs(dx) != weite && std::abs(dz) != weite && lage != b) continue;
                    lege(mx + dx, my + 4 + lage, mz + dz, ZIEGEL);
                }
            }
        }
        lege(mx, my + 1, mz, LEUCHTSTEIN);
    } else if (werk == Bauwerk::Turm) {
        for (int y = 0; y < 16; ++y) {
            for (int i = 0; i < 12; ++i) {
                float w = static_cast<float>(i) / 12.0f * TAU;
                int dx = static_cast<int>(std::round(std::cos(w) * 2.2f));
                int dz = static_cast<int>(std::round(std::sin(w) * 2.2f));
                lege(mx + dx, my + y, mz + dz, y % 4 == 3 ? ZIEGEL : STEIN);
            }
        }
        for (int dz = -2; dz <= 2; ++dz) {
            for (int dx = -2; dx <= 2; ++dx) lege(mx + dx, my + 16, mz + dz, BRETT);
        }
        lege(mx, my + 17, mz, LEUCHTSTEIN);
    } else if (werk == Bauwerk::Bruecke) {
        for (int i = 0; i < 24; ++i) {
            for (int dz = -1; dz <= 1; ++dz) {
                lege(mx + i, my, mz + dz, BRETT);
            }
            if (i % 4 == 0) {
                lege(mx + i, my + 1, mz - 2, HOLZ);
                lege(mx + i, my + 1, mz + 2, HOLZ);
                lege(mx + i, my + 2, mz - 2, HOLZ);
                lege(mx + i, my + 2, mz + 2, HOLZ);
            }
        }
    } else if (werk == Bauwerk::Baum) {
        for (int y = 0; y < 6; ++y) lege(mx, my + y, mz, HOLZ);
        for (int dy = -2; dy <= 2; ++dy) {
            int radius = dy <= 0 ? 3 : 2;
            for (int dz = -radius; dz <= radius; ++dz) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    if (dx * dx + dz * dz + dy * dy > radius * radius + 2) continue;
                    if (dx == 0 && dz == 0 && dy < 1) continue;
                    lege(mx + dx, my + 6 + dy, mz + dz, LAUB);
                }
            }
        }
    } else {
        for (int y = 0; y < 5; ++y) {
            int weite = 2 - y / 2;
            for (int dz = -weite; dz <= weite; ++dz) {
                for (int dx = -weite; dx <= weite; ++dx) {
                    lege(mx + dx, my + y, mz + dz, y == 4 ? LEUCHTSTEIN : STEIN);
                }
            }
        }
    }
    std::stable_sort(plan.begin(), plan.end(),
                     [](const Bauschritt& a, const Bauschritt& b) { return a.y < b.y; });
}

void MiniJon::auftrag(Bauwerk werk, Welt& welt, Vec3 spieler, float gierung) {
    Vec3 vorne(std::sin(gierung), 0.0f, std::cos(gierung));
    Vec3 mitte = spieler + vorne * 14.0f;
    int mx = static_cast<int>(std::floor(mitte.x));
    int mz = static_cast<int>(std::floor(mitte.z));
    mx = static_cast<int>(klemme(static_cast<float>(mx), 6.0f, static_cast<float>(WEITE - 30)));
    mz = static_cast<int>(klemme(static_cast<float>(mz), 6.0f, static_cast<float>(WEITE - 30)));
    int my = welt.hoeheBei(mx, mz) + 1;
    planFuer(werk, welt, mx, my, mz);
    ziel = Vec3(static_cast<float>(mx) + 0.5f, static_cast<float>(my) + 1.6f,
                static_cast<float>(mz) + 4.5f);
    sagt = std::string("Ich baue dir ein ") + bauwerkName(werk);
    sagtZeit = 3.4f;
    legeUhr = 0.0f;
}

void MiniJon::schritt(float dt, Welt& welt, Vec3 spieler, float spielerGierung) {
    takt += dt;
    if (sagtZeit > 0.0f) sagtZeit -= dt;

    if (plan.empty()) {
        Vec3 vorne(std::sin(spielerGierung), 0.0f, std::cos(spielerGierung));
        Vec3 rechts(vorne.z, 0.0f, -vorne.x);
        ziel = spieler + Vec3(0.0f, 1.4f, 0.0f) + vorne * 3.1f + rechts * 2.4f;
    }

    Vec3 nach = ziel - stelle;
    float weite = laenge(nach);
    if (weite > 0.05f) {
        float tempo = klemme(weite * 3.4f, 0.6f, plan.empty() ? 9.0f : 14.0f);
        stelle += nach * (1.0f / weite) * (tempo * dt);
        if (weite > 0.4f) richtung += winkelDifferenz(richtung, std::atan2(nach.x, nach.z)) *
                                      klemme(dt * 6.0f, 0.0f, 1.0f);
    }

    if (plan.empty()) return;
    if (weite > 6.0f) return;
    legeUhr -= dt;
    if (legeUhr > 0.0f) return;
    legeUhr = 0.07f;
    Bauschritt schrittDaten = plan.front();
    plan.erase(plan.begin());
    welt.setzeBlock(schrittDaten.x, schrittDaten.y, schrittDaten.z, schrittDaten.block);
    eben = true;
    ziel = Vec3(static_cast<float>(schrittDaten.x) + 0.5f, static_cast<float>(schrittDaten.y) + 2.2f,
                static_cast<float>(schrittDaten.z) + 0.5f);
    if (plan.empty()) {
        sagt = "Fertig! Gefaellt es dir?";
        sagtZeit = 4.0f;
    }
}

void MiniJon::zeichnen(Maler& maler, float zeit) const {
    float schweben = std::sin(zeit * 1.9f + takt) * 0.08f;
    Mat4 modell = verschiebung(stelle + Vec3(0.0f, schweben, 0.0f)) * drehungY(richtung) *
                  drehungZ(std::sin(zeit * 1.3f) * 0.06f);
    maler.modell(modell);
    maler.leuchten(0.22f);
    maler.zeichnen(netz);
    maler.leuchten(0.0f);
    maler.modell(einheit());
}

}
