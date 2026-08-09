#include "Welt.hpp"

#include <algorithm>
#include <cstdio>

#include "fw/Werkzeug.hpp"
#include "fw/Zufall.hpp"

namespace blockwelt {
namespace {

using namespace fw;

int stelle(int x, int y, int z) { return (y * WEITE + z) * WEITE + x; }

float hoehenfeld(float x, float z, unsigned saat) {
    int s = static_cast<int>(saat);
    float grob = bergRauschen(x * 0.012f, z * 0.012f, s, 4);
    float mittel = bergRauschen(x * 0.045f, z * 0.045f, s + 71, 3);
    float fein = bergRauschen(x * 0.13f, z * 0.13f, s + 211, 2);
    float berge = bergRauschen(x * 0.006f, z * 0.006f, s + 331, 3);
    float form = grob * 0.55f + mittel * 0.3f + fein * 0.15f;
    float huegel = std::pow(klemme(berge, 0.0f, 1.0f), 2.2f);
    return 15.0f + form * 21.0f + huegel * 26.0f;
}

bool hoehle(int x, int y, int z, unsigned saat) {
    if (y < 3 || y > 40) return false;
    float wert = bergRauschen(static_cast<float>(x) * 0.08f + static_cast<float>(y) * 0.05f,
                              static_cast<float>(z) * 0.08f - static_cast<float>(y) * 0.03f,
                              static_cast<int>(saat) + 907, 3);
    float zweit = bergRauschen(static_cast<float>(x) * 0.05f - static_cast<float>(y) * 0.09f,
                               static_cast<float>(z) * 0.05f + static_cast<float>(y) * 0.07f,
                               static_cast<int>(saat) + 1301, 2);
    return wert > 0.63f && zweit > 0.55f;
}

}

void Welt::erzeugen(unsigned saat) {
    saatwert = saat;
    bloecke.assign(static_cast<size_t>(WEITE) * WEITE * HOEHE, LUFT);
    geaendert.clear();

    for (int z = 0; z < WEITE; ++z) {
        for (int x = 0; x < WEITE; ++x) {
            int gipfel = static_cast<int>(hoehenfeld(static_cast<float>(x), static_cast<float>(z), saat));
            gipfel = static_cast<int>(klemme(static_cast<float>(gipfel), 4.0f, HOEHE - 8.0f));
            for (int y = 0; y <= gipfel; ++y) {
                unsigned char id = STEIN;
                if (y > gipfel - 4) id = ERDE;
                if (y == gipfel) {
                    if (gipfel <= MEERESHOEHE + 1) id = SAND;
                    else if (gipfel > 44) id = SCHNEE;
                    else id = GRAS;
                }
                if (y < 3) id = STEIN;
                if (id != STEIN && y < gipfel - 6) id = STEIN;
                if (hoehle(x, y, z, saat) && y < gipfel - 2) id = LUFT;
                bloecke[stelle(x, y, z)] = id;
            }
            for (int y = gipfel + 1; y <= MEERESHOEHE; ++y) bloecke[stelle(x, y, z)] = WASSER;
        }
    }

    Zufall wuerfel(saat * 6364136223846793005ull + 17u);
    for (int versuch = 0; versuch < WEITE * WEITE / 72; ++versuch) {
        int x = wuerfel.ganz(3, WEITE - 3);
        int z = wuerfel.ganz(3, WEITE - 3);
        int y = hoeheBei(x, z);
        if (y <= MEERESHOEHE + 1 || y > 44) continue;
        if (block(x, y, z) != GRAS) continue;
        int stamm = wuerfel.ganz(4, 7);
        for (int i = 1; i <= stamm; ++i) bloecke[stelle(x, y + i, z)] = HOLZ;
        int krone = y + stamm;
        for (int dy = -2; dy <= 2; ++dy) {
            int radius = dy <= 0 ? 2 : (dy == 1 ? 2 : 1);
            for (int dz = -radius; dz <= radius; ++dz) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    if (dx * dx + dz * dz + dy * dy > radius * radius + 2) continue;
                    int bx = x + dx;
                    int by = krone + dy;
                    int bz = z + dz;
                    if (!innen(bx, by, bz)) continue;
                    if (bloecke[stelle(bx, by, bz)] == LUFT) bloecke[stelle(bx, by, bz)] = LAUB;
                }
            }
        }
    }

    for (int versuch = 0; versuch < 90; ++versuch) {
        int x = wuerfel.ganz(2, WEITE - 2);
        int z = wuerfel.ganz(2, WEITE - 2);
        int y = wuerfel.ganz(4, 18);
        if (block(x, y, z) == STEIN) bloecke[stelle(x, y, z)] = LEUCHTSTEIN;
    }

    felder.clear();
    felder.resize(static_cast<size_t>(CHUNKS) * CHUNKS);
    for (int cz = 0; cz < CHUNKS; ++cz) {
        for (int cx = 0; cx < CHUNKS; ++cx) {
            Feld& feld = felder[static_cast<size_t>(cz) * CHUNKS + cx];
            feld.mitte = Vec3(static_cast<float>(cx * CHUNK + CHUNK / 2), 30.0f,
                              static_cast<float>(cz * CHUNK + CHUNK / 2));
            feld.schmutzig = true;
        }
    }
}

unsigned char Welt::block(int x, int y, int z) const {
    if (!innen(x, y, z)) return LUFT;
    return bloecke[stelle(x, y, z)];
}

void Welt::setzeBlock(int x, int y, int z, unsigned char id) {
    if (!innen(x, y, z)) return;
    int index = stelle(x, y, z);
    if (bloecke[index] == id) return;
    bloecke[index] = id;
    geaendert.push_back({index, id});
    int cx = x / CHUNK;
    int cz = z / CHUNK;
    for (int dz = -1; dz <= 1; ++dz) {
        for (int dx = -1; dx <= 1; ++dx) {
            int nx = cx + dx;
            int nz = cz + dz;
            if (nx < 0 || nz < 0 || nx >= CHUNKS || nz >= CHUNKS) continue;
            felder[static_cast<size_t>(nz) * CHUNKS + nx].schmutzig = true;
        }
    }
}

int Welt::hoeheBei(int x, int z) const {
    for (int y = HOEHE - 1; y >= 0; --y) {
        unsigned char id = block(x, y, z);
        if (id != LUFT && id != WASSER) return y;
    }
    return 0;
}

float Welt::lichtEcke(int x, int y, int z, int dx, int dy, int dz, int achse) const {
    int seiteA[3] = {0, 0, 0};
    int seiteB[3] = {0, 0, 0};
    if (achse == 0) {
        seiteA[1] = dy;
        seiteB[2] = dz;
    } else if (achse == 1) {
        seiteA[0] = dx;
        seiteB[2] = dz;
    } else {
        seiteA[0] = dx;
        seiteB[1] = dy;
    }
    bool a = istFest(block(x + seiteA[0], y + seiteA[1], z + seiteA[2]));
    bool b = istFest(block(x + seiteB[0], y + seiteB[1], z + seiteB[2]));
    bool ecke = istFest(block(x + seiteA[0] + seiteB[0], y + seiteA[1] + seiteB[1],
                              z + seiteA[2] + seiteB[2]));
    int summe = (a ? 1 : 0) + (b ? 1 : 0) + ((a && b) ? 1 : (ecke ? 1 : 0));
    return 1.0f - static_cast<float>(summe) * 0.19f;
}

void Welt::chunkBauen(int cx, int cz) {
    Feld& feld = felder[static_cast<size_t>(cz) * CHUNKS + cx];
    Bauer fest;
    Bauer nass;
    const int basisX = cx * CHUNK;
    const int basisZ = cz * CHUNK;

    for (int y = 0; y < HOEHE; ++y) {
        for (int z = basisZ; z < basisZ + CHUNK; ++z) {
            for (int x = basisX; x < basisX + CHUNK; ++x) {
                unsigned char id = block(x, y, z);
                if (id == LUFT) continue;
                const Blockart& art = blockart(id);
                float wackeln = 0.92f + streu(x, y * 31 + z, 5) * 0.16f;

                if (id == WASSER) {
                    if (block(x, y + 1, z) == WASSER) continue;
                    float hoehe = static_cast<float>(y) + 0.86f;
                    Vec3 a(static_cast<float>(x), hoehe, static_cast<float>(z));
                    Vec3 b(static_cast<float>(x) + 1.0f, hoehe, static_cast<float>(z));
                    Vec3 c(static_cast<float>(x) + 1.0f, hoehe, static_cast<float>(z) + 1.0f);
                    Vec3 d(static_cast<float>(x), hoehe, static_cast<float>(z) + 1.0f);
                    nass.viereck(a, d, c, b, art.oben, 0.85f);
                    continue;
                }

                const int nachbarn[6][3] = {{0, 1, 0},  {0, -1, 0}, {0, 0, 1},
                                            {0, 0, -1}, {1, 0, 0},  {-1, 0, 0}};
                for (int seite = 0; seite < 6; ++seite) {
                    int nx = x + nachbarn[seite][0];
                    int ny = y + nachbarn[seite][1];
                    int nz = z + nachbarn[seite][2];
                    unsigned char nachbar = block(nx, ny, nz);
                    if (istFest(nachbar) && !blockart(nachbar).sichtdurch) continue;
                    if (nachbar == id) continue;

                    Vec3 farbe = seite == 0 ? art.oben : (seite == 1 ? art.unten : art.seite);
                    farbe = farbe * wackeln;
                    float fx = static_cast<float>(x);
                    float fy = static_cast<float>(y);
                    float fz = static_cast<float>(z);
                    Vec3 ecken[4];
                    Vec3 normale;
                    float schatten[4];
                    if (seite == 0) {
                        normale = Vec3(0.0f, 1.0f, 0.0f);
                        ecken[0] = Vec3(fx, fy + 1.0f, fz);
                        ecken[1] = Vec3(fx, fy + 1.0f, fz + 1.0f);
                        ecken[2] = Vec3(fx + 1.0f, fy + 1.0f, fz + 1.0f);
                        ecken[3] = Vec3(fx + 1.0f, fy + 1.0f, fz);
                        schatten[0] = lichtEcke(x, y + 1, z, -1, 0, -1, 1);
                        schatten[1] = lichtEcke(x, y + 1, z, -1, 0, 1, 1);
                        schatten[2] = lichtEcke(x, y + 1, z, 1, 0, 1, 1);
                        schatten[3] = lichtEcke(x, y + 1, z, 1, 0, -1, 1);
                    } else if (seite == 1) {
                        normale = Vec3(0.0f, -1.0f, 0.0f);
                        ecken[0] = Vec3(fx, fy, fz);
                        ecken[1] = Vec3(fx + 1.0f, fy, fz);
                        ecken[2] = Vec3(fx + 1.0f, fy, fz + 1.0f);
                        ecken[3] = Vec3(fx, fy, fz + 1.0f);
                        for (int i = 0; i < 4; ++i) schatten[i] = 0.72f;
                    } else if (seite == 2) {
                        normale = Vec3(0.0f, 0.0f, 1.0f);
                        ecken[0] = Vec3(fx, fy, fz + 1.0f);
                        ecken[1] = Vec3(fx + 1.0f, fy, fz + 1.0f);
                        ecken[2] = Vec3(fx + 1.0f, fy + 1.0f, fz + 1.0f);
                        ecken[3] = Vec3(fx, fy + 1.0f, fz + 1.0f);
                        schatten[0] = lichtEcke(x, y, z + 1, -1, -1, 0, 2);
                        schatten[1] = lichtEcke(x, y, z + 1, 1, -1, 0, 2);
                        schatten[2] = lichtEcke(x, y, z + 1, 1, 1, 0, 2);
                        schatten[3] = lichtEcke(x, y, z + 1, -1, 1, 0, 2);
                    } else if (seite == 3) {
                        normale = Vec3(0.0f, 0.0f, -1.0f);
                        ecken[0] = Vec3(fx + 1.0f, fy, fz);
                        ecken[1] = Vec3(fx, fy, fz);
                        ecken[2] = Vec3(fx, fy + 1.0f, fz);
                        ecken[3] = Vec3(fx + 1.0f, fy + 1.0f, fz);
                        schatten[0] = lichtEcke(x, y, z - 1, 1, -1, 0, 2);
                        schatten[1] = lichtEcke(x, y, z - 1, -1, -1, 0, 2);
                        schatten[2] = lichtEcke(x, y, z - 1, -1, 1, 0, 2);
                        schatten[3] = lichtEcke(x, y, z - 1, 1, 1, 0, 2);
                    } else if (seite == 4) {
                        normale = Vec3(1.0f, 0.0f, 0.0f);
                        ecken[0] = Vec3(fx + 1.0f, fy, fz + 1.0f);
                        ecken[1] = Vec3(fx + 1.0f, fy, fz);
                        ecken[2] = Vec3(fx + 1.0f, fy + 1.0f, fz);
                        ecken[3] = Vec3(fx + 1.0f, fy + 1.0f, fz + 1.0f);
                        schatten[0] = lichtEcke(x + 1, y, z, 0, -1, 1, 0);
                        schatten[1] = lichtEcke(x + 1, y, z, 0, -1, -1, 0);
                        schatten[2] = lichtEcke(x + 1, y, z, 0, 1, -1, 0);
                        schatten[3] = lichtEcke(x + 1, y, z, 0, 1, 1, 0);
                    } else {
                        normale = Vec3(-1.0f, 0.0f, 0.0f);
                        ecken[0] = Vec3(fx, fy, fz);
                        ecken[1] = Vec3(fx, fy, fz + 1.0f);
                        ecken[2] = Vec3(fx, fy + 1.0f, fz + 1.0f);
                        ecken[3] = Vec3(fx, fy + 1.0f, fz);
                        schatten[0] = lichtEcke(x - 1, y, z, 0, -1, -1, 0);
                        schatten[1] = lichtEcke(x - 1, y, z, 0, -1, 1, 0);
                        schatten[2] = lichtEcke(x - 1, y, z, 0, 1, 1, 0);
                        schatten[3] = lichtEcke(x - 1, y, z, 0, 1, -1, 0);
                    }
                    float glanz = id == GLAS ? 0.7f : (id == SCHNEE ? 0.25f : 0.0f);
                    fest.ecke(ecken[0], normale, farbe * schatten[0], glanz);
                    fest.ecke(ecken[1], normale, farbe * schatten[1], glanz);
                    fest.ecke(ecken[2], normale, farbe * schatten[2], glanz);
                    fest.ecke(ecken[0], normale, farbe * schatten[0], glanz);
                    fest.ecke(ecken[2], normale, farbe * schatten[2], glanz);
                    fest.ecke(ecken[3], normale, farbe * schatten[3], glanz);
                }
            }
        }
    }
    feld.fest.hochladen(fest);
    feld.fluessig.hochladen(nass);
    feld.schmutzig = false;
}

void Welt::netzeBauen() {
    for (int cz = 0; cz < CHUNKS; ++cz) {
        for (int cx = 0; cx < CHUNKS; ++cx) chunkBauen(cx, cz);
    }
}

void Welt::netzeAuffrischen() {
    for (int cz = 0; cz < CHUNKS; ++cz) {
        for (int cx = 0; cx < CHUNKS; ++cx) {
            if (felder[static_cast<size_t>(cz) * CHUNKS + cx].schmutzig) chunkBauen(cx, cz);
        }
    }
}

void Welt::freigeben() {
    for (Feld& feld : felder) {
        feld.fest.freigeben();
        feld.fluessig.freigeben();
    }
    felder.clear();
}

void Welt::zeichnen(Maler& maler, Vec3 auge, float sichtweite) const {
    maler.modell(einheit());
    for (const Feld& feld : felder) {
        float dx = feld.mitte.x - auge.x;
        float dz = feld.mitte.z - auge.z;
        if (std::sqrt(dx * dx + dz * dz) > sichtweite) continue;
        maler.zeichnen(feld.fest);
    }
}

void Welt::zeichnenWasser(Maler& maler, Vec3 auge, float sichtweite) const {
    maler.modell(einheit());
    for (const Feld& feld : felder) {
        float dx = feld.mitte.x - auge.x;
        float dz = feld.mitte.z - auge.z;
        if (std::sqrt(dx * dx + dz * dz) > sichtweite) continue;
        maler.zeichnen(feld.fluessig);
    }
}

Treffer Welt::strahl(Vec3 start, Vec3 richtung, float weite) const {
    Treffer treffer;
    Vec3 dir = normiert(richtung);
    int x = static_cast<int>(std::floor(start.x));
    int y = static_cast<int>(std::floor(start.y));
    int z = static_cast<int>(std::floor(start.z));
    int schrittX = dir.x > 0.0f ? 1 : -1;
    int schrittY = dir.y > 0.0f ? 1 : -1;
    int schrittZ = dir.z > 0.0f ? 1 : -1;
    float weiteX = std::fabs(dir.x) < 1e-6f ? 1e9f : std::fabs(1.0f / dir.x);
    float weiteY = std::fabs(dir.y) < 1e-6f ? 1e9f : std::fabs(1.0f / dir.y);
    float weiteZ = std::fabs(dir.z) < 1e-6f ? 1e9f : std::fabs(1.0f / dir.z);
    float naechsteX = dir.x > 0.0f ? (static_cast<float>(x + 1) - start.x) / (dir.x + 1e-9f)
                                   : (start.x - static_cast<float>(x)) / (-dir.x + 1e-9f);
    float naechsteY = dir.y > 0.0f ? (static_cast<float>(y + 1) - start.y) / (dir.y + 1e-9f)
                                   : (start.y - static_cast<float>(y)) / (-dir.y + 1e-9f);
    float naechsteZ = dir.z > 0.0f ? (static_cast<float>(z + 1) - start.z) / (dir.z + 1e-9f)
                                   : (start.z - static_cast<float>(z)) / (-dir.z + 1e-9f);
    int vorX = x;
    int vorY = y;
    int vorZ = z;
    float gelaufen = 0.0f;
    for (int schritt = 0; schritt < 256 && gelaufen <= weite; ++schritt) {
        unsigned char id = block(x, y, z);
        if (istFest(id)) {
            treffer.getroffen = true;
            treffer.x = x;
            treffer.y = y;
            treffer.z = z;
            treffer.vorX = vorX;
            treffer.vorY = vorY;
            treffer.vorZ = vorZ;
            treffer.block = id;
            return treffer;
        }
        vorX = x;
        vorY = y;
        vorZ = z;
        if (naechsteX < naechsteY && naechsteX < naechsteZ) {
            gelaufen = naechsteX;
            naechsteX += weiteX;
            x += schrittX;
        } else if (naechsteY < naechsteZ) {
            gelaufen = naechsteY;
            naechsteY += weiteY;
            y += schrittY;
        } else {
            gelaufen = naechsteZ;
            naechsteZ += weiteZ;
            z += schrittZ;
        }
    }
    return treffer;
}

bool Welt::speichern(const std::string& pfad) const {
    std::string text = "saat " + std::to_string(saatwert) + "\n";
    char zeile[64];
    for (const auto& eintrag : geaendert) {
        int index = eintrag.first;
        int x = index % WEITE;
        int z = (index / WEITE) % WEITE;
        int y = index / (WEITE * WEITE);
        std::snprintf(zeile, sizeof(zeile), "b %d %d %d %d\n", x, y, z, static_cast<int>(eintrag.second));
        text += zeile;
    }
    return fw::schreibeText(pfad, text);
}

bool Welt::laden(const std::string& pfad) {
    std::string inhalt = fw::leseText(pfad);
    if (inhalt.empty()) return false;
    unsigned gespeicherteSaat = saatwert;
    std::vector<std::string> zeilen = fw::zerlegen(inhalt, '\n');
    for (const std::string& roh : zeilen) {
        std::string zeile = fw::putzen(roh);
        if (zeile.rfind("saat", 0) == 0) {
            gespeicherteSaat = static_cast<unsigned>(std::atoi(zeile.c_str() + 4));
        }
    }
    if (gespeicherteSaat != saatwert) {
        saatwert = gespeicherteSaat;
        erzeugen(saatwert);
    }
    for (const std::string& roh : zeilen) {
        std::string zeile = fw::putzen(roh);
        if (zeile.rfind("b ", 0) != 0) continue;
        int x = 0;
        int y = 0;
        int z = 0;
        int id = 0;
        if (std::sscanf(zeile.c_str() + 2, "%d %d %d %d", &x, &y, &z, &id) == 4) {
            setzeBlock(x, y, z, static_cast<unsigned char>(id));
        }
    }
    return true;
}

}
