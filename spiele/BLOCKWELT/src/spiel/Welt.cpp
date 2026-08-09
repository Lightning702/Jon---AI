#include "Welt.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

#include "Atlas.hpp"
#include "fw/Werkzeug.hpp"

namespace blockwelt {
namespace {

using namespace fw;

unsigned char misch[512];
unsigned aktiveSaat = 0;

void rauschenSaat(unsigned saat) {
    if (aktiveSaat == saat && saat != 0) return;
    aktiveSaat = saat;
    unsigned char p[256];
    for (int i = 0; i < 256; ++i) p[i] = static_cast<unsigned char>(i);
    long long s = static_cast<long long>(saat) % 2147483647ll;
    if (s <= 0) s += 2147483646ll;
    auto wurf = [&]() {
        s = (s * 16807ll) % 2147483647ll;
        return static_cast<double>(s) / 2147483647.0;
    };
    for (int i = 255; i > 0; --i) {
        int j = static_cast<int>(wurf() * (i + 1));
        unsigned char t = p[i];
        p[i] = p[j];
        p[j] = t;
    }
    for (int i = 0; i < 512; ++i) misch[i] = p[i & 255];
}

float verlauf(float t) { return t * t * t * (t * (t * 6.0f - 15.0f) + 10.0f); }

float steigung(int h, float x, float y) {
    switch (h & 3) {
        case 0: return x + y;
        case 1: return -x + y;
        case 2: return x - y;
        default: return -x - y;
    }
}

float rauschen2(float x, float y) {
    int X = static_cast<int>(std::floor(x)) & 255;
    int Y = static_cast<int>(std::floor(y)) & 255;
    x -= std::floor(x);
    y -= std::floor(y);
    float u = verlauf(x);
    float v = verlauf(y);
    int A = misch[X] + Y;
    int B = misch[X + 1] + Y;
    float a = mische(steigung(misch[A & 511], x, y), steigung(misch[B & 511], x - 1.0f, y), u);
    float b = mische(steigung(misch[(A + 1) & 511], x, y - 1.0f),
                     steigung(misch[(B + 1) & 511], x - 1.0f, y - 1.0f), u);
    return mische(a, b, v);
}

float berge(float x, float y, int lagen) {
    float staerke = 1.0f;
    float weite = 1.0f;
    float summe = 0.0f;
    float gewicht = 0.0f;
    for (int i = 0; i < lagen; ++i) {
        summe += staerke * rauschen2(x * weite, y * weite);
        gewicht += staerke;
        staerke *= 0.5f;
        weite *= 2.0f;
    }
    return klemme(summe / gewicht * 1.85f, -1.0f, 1.0f);
}

float streu2(int x, int z, unsigned saat) {
    unsigned h = static_cast<unsigned>(x * 374761393 + z * 668265263) + saat * 2246822519u;
    h = (h ^ (h >> 13)) * 1274126177u;
    return static_cast<float>((h ^ (h >> 16))) / 4294967296.0f;
}

int stelleIn(int lx, int y, int lz) { return y * 256 + lz * 16 + lx; }

int teilenAb(int a, int b) { return a >= 0 ? a / b : -(((-a) + b - 1) / b); }

int restVon(int a, int b) {
    int r = a % b;
    return r < 0 ? r + b : r;
}

}

int hoeheAn(int x, int z, unsigned saat) {
    rauschenSaat(saat);
    float fx = static_cast<float>(x);
    float fz = static_cast<float>(z);
    float c = berge(fx * 0.0018f, fz * 0.0018f, 4);
    float e = berge(fx * 0.01f + 500.0f, fz * 0.01f + 500.0f, 3);
    float mo = berge(fx * 0.004f - 900.0f, fz * 0.004f + 900.0f, 4);
    float h = 40.0f + c * 22.0f + e * 6.0f;
    if (mo > 0.22f) {
        float m = (mo - 0.22f) / 0.78f;
        h += m * m * 58.0f;
    }
    int ganz = static_cast<int>(std::floor(h));
    if (ganz < 3) ganz = 3;
    if (ganz > 84) ganz = 84;
    return ganz;
}

int bezirkAn(int x, int z, unsigned saat) {
    rauschenSaat(saat);
    float fx = static_cast<float>(x);
    float fz = static_cast<float>(z);
    float t = berge(fx * 0.0016f + 800.0f, fz * 0.0016f - 800.0f, 3);
    float m = berge(fx * 0.0021f - 443.0f, fz * 0.0021f + 271.0f, 3);
    if (t > 0.22f && m < 0.05f) return 2;
    if (t < -0.26f) return 3;
    if (m > 0.08f) return 1;
    return 0;
}

const char* bezirkText(int bezirk) {
    switch (bezirk) {
        case 1: return "Wald";
        case 2: return "Wueste";
        case 3: return "Schneeland";
        case 4: return "Gebirge";
        default: return "Ebene";
    }
}

void Welt::beginnen(unsigned saat) {
    saatwert = saat ? saat : 1337u;
    rauschenSaat(saatwert);
    freigeben();
}

void Welt::freigeben() {
    for (auto& eintrag : felder) {
        eintrag.second->fest.freigeben();
        eintrag.second->fluessig.freigeben();
    }
    felder.clear();
}

Feld* Welt::feldSuchen(int cx, int cz) {
    auto es = felder.find(schluessel(cx, cz));
    return es == felder.end() ? nullptr : es->second.get();
}

const Feld* Welt::feldSuchen(int cx, int cz) const {
    auto es = felder.find(schluessel(cx, cz));
    return es == felder.end() ? nullptr : es->second.get();
}

bool Welt::geladen(int x, int z) const {
    return feldSuchen(teilenAb(x, CHUNK), teilenAb(z, CHUNK)) != nullptr;
}

void Welt::feldFuellen(Feld& feld) {
    feld.daten.assign(static_cast<size_t>(CHUNK) * CHUNK * HOEHE, LUFT);
    int hoechste = 0;
    for (int lz = 0; lz < CHUNK; ++lz) {
        for (int lx = 0; lx < CHUNK; ++lx) {
            int wx = feld.cx * CHUNK + lx;
            int wz = feld.cz * CHUNK + lz;
            int h = hoeheAn(wx, wz, saatwert);
            int bezirk = h > 62 ? 4 : bezirkAn(wx, wz, saatwert);
            bool strand = h <= MEER + 1;
            for (int y = 0; y <= h; ++y) {
                int d = h - y;
                unsigned char id;
                if (y == 0) {
                    id = STEIN;
                } else if (bezirk == 4) {
                    id = (d == 0 && h > 72) ? SCHNEE : STEIN;
                } else if (strand) {
                    id = d < 4 ? SAND : (d < 7 ? SANDSTEIN : STEIN);
                } else if (bezirk == 2) {
                    id = d < 4 ? SAND : (d < 8 ? SANDSTEIN : STEIN);
                } else if (bezirk == 3) {
                    id = d == 0 ? SCHNEE : (d < 4 ? ERDE : STEIN);
                } else {
                    id = d == 0 ? GRAS : (d < 4 ? ERDE : STEIN);
                }
                feld.daten[stelleIn(lx, y, lz)] = id;
            }
            for (int y = h + 1; y <= MEER; ++y) feld.daten[stelleIn(lx, y, lz)] = WASSER;
            if (h > hoechste) hoechste = h;
            if (MEER > hoechste) hoechste = MEER;

            if (lx < 2 || lx > 13 || lz < 2 || lz > 13) continue;
            if (h <= MEER + 1 || h >= HOEHE - 12 || bezirk == 4) continue;
            float r = streu2(wx, wz, saatwert);
            if ((bezirk == 1 && r < 0.02f) || (bezirk == 0 && r < 0.003f) ||
                (bezirk == 3 && r < 0.006f)) {
                int stammHoehe = 4 + static_cast<int>(streu2(wx + 31, wz + 77, saatwert) * 3.0f);
                for (int i = 1; i <= stammHoehe; ++i) feld.daten[stelleIn(lx, h + i, lz)] = STAMM;
                for (int dy = stammHoehe - 2; dy <= stammHoehe + 1; ++dy) {
                    int rad = dy >= stammHoehe ? 1 : 2;
                    for (int ax = -rad; ax <= rad; ++ax) {
                        for (int az = -rad; az <= rad; ++az) {
                            if (dy == stammHoehe + 1 && std::abs(ax) + std::abs(az) > 1) continue;
                            if (std::abs(ax) == rad && std::abs(az) == rad &&
                                streu2(wx + ax * 13, wz + az * 7 + dy, saatwert) < 0.4f) {
                                continue;
                            }
                            int y = h + dy;
                            if (y < 0 || y >= HOEHE) continue;
                            int i = stelleIn(lx + ax, y, lz + az);
                            if (feld.daten[i] == LUFT) feld.daten[i] = LAUB;
                            if (y > hoechste) hoechste = y;
                        }
                    }
                }
            } else if (bezirk == 2 && r < 0.005f) {
                int kaktusHoehe = 2 + static_cast<int>(streu2(wx + 5, wz + 9, saatwert) * 3.0f);
                for (int i = 1; i <= kaktusHoehe; ++i) feld.daten[stelleIn(lx, h + i, lz)] = KAKTUS;
                if (h + kaktusHoehe > hoechste) hoechste = h + kaktusHoehe;
            }
        }
    }
    feld.gipfel = hoechste + 1 < HOEHE ? hoechste + 1 : HOEHE - 1;

    auto es = notizen.find(schluessel(feld.cx, feld.cz));
    if (es != notizen.end()) {
        for (const auto& notiz : es->second) {
            if (notiz.first < 0 || notiz.first >= static_cast<int>(feld.daten.size())) continue;
            feld.daten[notiz.first] = notiz.second;
            int y = notiz.first / 256;
            if (notiz.second != LUFT && y > feld.gipfel) feld.gipfel = y;
        }
    }
}

Feld* Welt::feldErzeugen(int cx, int cz) {
    Feld* schon = feldSuchen(cx, cz);
    if (schon) return schon;
    auto feld = std::make_unique<Feld>();
    feld->cx = cx;
    feld->cz = cz;
    feldFuellen(*feld);
    Feld* zeiger = feld.get();
    felder.emplace(schluessel(cx, cz), std::move(feld));
    return zeiger;
}

unsigned char Welt::block(int x, int y, int z) const {
    if (y < 0 || y >= HOEHE) return LUFT;
    const Feld* feld = feldSuchen(teilenAb(x, CHUNK), teilenAb(z, CHUNK));
    if (!feld) return LUFT;
    return feld->daten[stelleIn(restVon(x, CHUNK), y, restVon(z, CHUNK))];
}

void Welt::schmutzigMachen(int x, int z) {
    int cx = teilenAb(x, CHUNK);
    int cz = teilenAb(z, CHUNK);
    for (int dz = -1; dz <= 1; ++dz) {
        for (int dx = -1; dx <= 1; ++dx) {
            Feld* feld = feldSuchen(cx + dx, cz + dz);
            if (feld) feld->schmutzig = true;
        }
    }
}

void Welt::setzeBlock(int x, int y, int z, unsigned char id) {
    if (y < 0 || y >= HOEHE) return;
    Feld* feld = feldSuchen(teilenAb(x, CHUNK), teilenAb(z, CHUNK));
    if (!feld) return;
    int i = stelleIn(restVon(x, CHUNK), y, restVon(z, CHUNK));
    if (feld->daten[i] == id) return;
    feld->daten[i] = id;
    if (id != LUFT && y > feld->gipfel) feld->gipfel = y;
    std::vector<std::pair<int, unsigned char>>& liste = notizen[schluessel(teilenAb(x, CHUNK),
                                                                           teilenAb(z, CHUNK))];
    bool gefunden = false;
    for (auto& eintrag : liste) {
        if (eintrag.first == i) {
            eintrag.second = id;
            gefunden = true;
            break;
        }
    }
    if (!gefunden) liste.push_back({i, id});
    schmutzigMachen(x, z);
}

int Welt::hoeheBei(int x, int z) const {
    const Feld* feld = feldSuchen(teilenAb(x, CHUNK), teilenAb(z, CHUNK));
    if (!feld) return hoeheAn(x, z, saatwert);
    int lx = restVon(x, CHUNK);
    int lz = restVon(z, CHUNK);
    for (int y = HOEHE - 1; y >= 0; --y) {
        unsigned char id = feld->daten[stelleIn(lx, y, lz)];
        if (id != LUFT && id != WASSER) return y;
    }
    return 0;
}

std::string Welt::bezirkName(int x, int z) const {
    int h = hoeheAn(x, z, saatwert);
    return bezirkText(h > 62 ? 4 : bezirkAn(x, z, saatwert));
}

float Welt::eckenLicht(int x, int y, int z, int dx, int dy, int dz, int achse) const {
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
    return 1.0f - static_cast<float>(summe) * 0.17f;
}

void Welt::netzBauen(Feld& feld) {
    Bauer fest;
    Bauer nass;
    const int basisX = feld.cx * CHUNK;
    const int basisZ = feld.cz * CHUNK;
    const int nachbarn[6][3] = {{0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}, {1, 0, 0}, {-1, 0, 0}};

    for (int y = 0; y <= feld.gipfel; ++y) {
        for (int lz = 0; lz < CHUNK; ++lz) {
            for (int lx = 0; lx < CHUNK; ++lx) {
                unsigned char id = feld.daten[stelleIn(lx, y, lz)];
                if (id == LUFT) continue;
                const Blockart& art = blockart(id);
                int x = basisX + lx;
                int z = basisZ + lz;

                if (id == WASSER) {
                    if (block(x, y + 1, z) == WASSER) continue;
                    float hoehe = static_cast<float>(y) + 0.88f;
                    Vec3 a(static_cast<float>(x), hoehe, static_cast<float>(z));
                    Vec3 b(static_cast<float>(x) + 1.0f, hoehe, static_cast<float>(z));
                    Vec3 c(static_cast<float>(x) + 1.0f, hoehe, static_cast<float>(z) + 1.0f);
                    Vec3 d(static_cast<float>(x), hoehe, static_cast<float>(z) + 1.0f);
                    Vec3 oben(0.0f, 1.0f, 0.0f);
                    Vec3 weiss(1.0f, 1.0f, 1.0f);
                    nass.ecke(a, oben, weiss, 0.85f, Atlas::bildpunkt(art.oben, 0.0f, 0.0f));
                    nass.ecke(d, oben, weiss, 0.85f, Atlas::bildpunkt(art.oben, 0.0f, 1.0f));
                    nass.ecke(c, oben, weiss, 0.85f, Atlas::bildpunkt(art.oben, 1.0f, 1.0f));
                    nass.ecke(a, oben, weiss, 0.85f, Atlas::bildpunkt(art.oben, 0.0f, 0.0f));
                    nass.ecke(c, oben, weiss, 0.85f, Atlas::bildpunkt(art.oben, 1.0f, 1.0f));
                    nass.ecke(b, oben, weiss, 0.85f, Atlas::bildpunkt(art.oben, 1.0f, 0.0f));
                    continue;
                }

                for (int seite = 0; seite < 6; ++seite) {
                    int nx = x + nachbarn[seite][0];
                    int ny = y + nachbarn[seite][1];
                    int nz = z + nachbarn[seite][2];
                    unsigned char nachbar = block(nx, ny, nz);
                    if (nachbar == id) continue;
                    if (istFest(nachbar) && !istDurchsichtig(nachbar)) continue;

                    int kachel = seite == 0 ? art.oben : (seite == 1 ? art.unten : art.seite);
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
                        schatten[0] = eckenLicht(x, y + 1, z, -1, 0, -1, 1);
                        schatten[1] = eckenLicht(x, y + 1, z, -1, 0, 1, 1);
                        schatten[2] = eckenLicht(x, y + 1, z, 1, 0, 1, 1);
                        schatten[3] = eckenLicht(x, y + 1, z, 1, 0, -1, 1);
                    } else if (seite == 1) {
                        normale = Vec3(0.0f, -1.0f, 0.0f);
                        ecken[0] = Vec3(fx, fy, fz);
                        ecken[1] = Vec3(fx + 1.0f, fy, fz);
                        ecken[2] = Vec3(fx + 1.0f, fy, fz + 1.0f);
                        ecken[3] = Vec3(fx, fy, fz + 1.0f);
                        for (int i = 0; i < 4; ++i) schatten[i] = 0.7f;
                    } else if (seite == 2) {
                        normale = Vec3(0.0f, 0.0f, 1.0f);
                        ecken[0] = Vec3(fx, fy, fz + 1.0f);
                        ecken[1] = Vec3(fx + 1.0f, fy, fz + 1.0f);
                        ecken[2] = Vec3(fx + 1.0f, fy + 1.0f, fz + 1.0f);
                        ecken[3] = Vec3(fx, fy + 1.0f, fz + 1.0f);
                        schatten[0] = eckenLicht(x, y, z + 1, -1, -1, 0, 2);
                        schatten[1] = eckenLicht(x, y, z + 1, 1, -1, 0, 2);
                        schatten[2] = eckenLicht(x, y, z + 1, 1, 1, 0, 2);
                        schatten[3] = eckenLicht(x, y, z + 1, -1, 1, 0, 2);
                    } else if (seite == 3) {
                        normale = Vec3(0.0f, 0.0f, -1.0f);
                        ecken[0] = Vec3(fx + 1.0f, fy, fz);
                        ecken[1] = Vec3(fx, fy, fz);
                        ecken[2] = Vec3(fx, fy + 1.0f, fz);
                        ecken[3] = Vec3(fx + 1.0f, fy + 1.0f, fz);
                        schatten[0] = eckenLicht(x, y, z - 1, 1, -1, 0, 2);
                        schatten[1] = eckenLicht(x, y, z - 1, -1, -1, 0, 2);
                        schatten[2] = eckenLicht(x, y, z - 1, -1, 1, 0, 2);
                        schatten[3] = eckenLicht(x, y, z - 1, 1, 1, 0, 2);
                    } else if (seite == 4) {
                        normale = Vec3(1.0f, 0.0f, 0.0f);
                        ecken[0] = Vec3(fx + 1.0f, fy, fz + 1.0f);
                        ecken[1] = Vec3(fx + 1.0f, fy, fz);
                        ecken[2] = Vec3(fx + 1.0f, fy + 1.0f, fz);
                        ecken[3] = Vec3(fx + 1.0f, fy + 1.0f, fz + 1.0f);
                        schatten[0] = eckenLicht(x + 1, y, z, 0, -1, 1, 0);
                        schatten[1] = eckenLicht(x + 1, y, z, 0, -1, -1, 0);
                        schatten[2] = eckenLicht(x + 1, y, z, 0, 1, -1, 0);
                        schatten[3] = eckenLicht(x + 1, y, z, 0, 1, 1, 0);
                    } else {
                        normale = Vec3(-1.0f, 0.0f, 0.0f);
                        ecken[0] = Vec3(fx, fy, fz);
                        ecken[1] = Vec3(fx, fy, fz + 1.0f);
                        ecken[2] = Vec3(fx, fy + 1.0f, fz + 1.0f);
                        ecken[3] = Vec3(fx, fy + 1.0f, fz);
                        schatten[0] = eckenLicht(x - 1, y, z, 0, -1, -1, 0);
                        schatten[1] = eckenLicht(x - 1, y, z, 0, -1, 1, 0);
                        schatten[2] = eckenLicht(x - 1, y, z, 0, 1, 1, 0);
                        schatten[3] = eckenLicht(x - 1, y, z, 0, 1, -1, 0);
                    }
                    const Vec2 bilder[4] = {Atlas::bildpunkt(kachel, 0.0f, 1.0f),
                                            Atlas::bildpunkt(kachel, 1.0f, 1.0f),
                                            Atlas::bildpunkt(kachel, 1.0f, 0.0f),
                                            Atlas::bildpunkt(kachel, 0.0f, 0.0f)};
                    float glanz = id == GLAS ? 0.6f : (id == SCHNEE ? 0.2f : 0.0f);
                    const int reihe[6] = {0, 1, 2, 0, 2, 3};
                    for (int k = 0; k < 6; ++k) {
                        int e = reihe[k];
                        Vec3 farbe(schatten[e], schatten[e], schatten[e]);
                        fest.ecke(ecken[e], normale, farbe, glanz, bilder[e]);
                    }
                }
            }
        }
    }
    feld.fest.hochladen(fest);
    feld.fluessig.hochladen(nass);
    feld.schmutzig = false;
    feld.gebaut = true;
}

void Welt::umgebungPflegen(Vec3 spieler, int radius, int erzeugeJeBild, int netzeJeBild) {
    int mx = teilenAb(static_cast<int>(std::floor(spieler.x)), CHUNK);
    int mz = teilenAb(static_cast<int>(std::floor(spieler.z)), CHUNK);

    int erzeugt = 0;
    for (int ring = 0; ring <= radius && erzeugt < erzeugeJeBild; ++ring) {
        for (int dz = -ring; dz <= ring && erzeugt < erzeugeJeBild; ++dz) {
            for (int dx = -ring; dx <= ring && erzeugt < erzeugeJeBild; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) != ring) continue;
                if (feldSuchen(mx + dx, mz + dz)) continue;
                feldErzeugen(mx + dx, mz + dz);
                ++erzeugt;
            }
        }
    }

    int gebaut = 0;
    for (int ring = 0; ring <= radius && gebaut < netzeJeBild; ++ring) {
        for (int dz = -ring; dz <= ring && gebaut < netzeJeBild; ++dz) {
            for (int dx = -ring; dx <= ring && gebaut < netzeJeBild; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) != ring) continue;
                Feld* feld = feldSuchen(mx + dx, mz + dz);
                if (!feld || !feld->schmutzig) continue;
                if (!feldSuchen(feld->cx - 1, feld->cz) || !feldSuchen(feld->cx + 1, feld->cz) ||
                    !feldSuchen(feld->cx, feld->cz - 1) || !feldSuchen(feld->cx, feld->cz + 1)) {
                    continue;
                }
                netzBauen(*feld);
                ++gebaut;
            }
        }
    }

    const int grenze = radius + 3;
    for (auto es = felder.begin(); es != felder.end();) {
        int dx = std::abs(es->second->cx - mx);
        int dz = std::abs(es->second->cz - mz);
        if (std::max(dx, dz) > grenze) {
            es->second->fest.freigeben();
            es->second->fluessig.freigeben();
            es = felder.erase(es);
        } else {
            ++es;
        }
    }
}

void Welt::zeichnen(Maler& maler, Vec3 auge, float sichtweite) const {
    maler.modell(einheit());
    gezeichnet = 0;
    for (const auto& eintrag : felder) {
        const Feld& feld = *eintrag.second;
        if (!feld.gebaut) continue;
        float mx = static_cast<float>(feld.cx * CHUNK + CHUNK / 2) - auge.x;
        float mz = static_cast<float>(feld.cz * CHUNK + CHUNK / 2) - auge.z;
        if (std::sqrt(mx * mx + mz * mz) > sichtweite + CHUNK) continue;
        maler.zeichnen(feld.fest);
        ++gezeichnet;
    }
}

void Welt::zeichnenWasser(Maler& maler, Vec3 auge, float sichtweite) const {
    maler.modell(einheit());
    for (const auto& eintrag : felder) {
        const Feld& feld = *eintrag.second;
        if (!feld.gebaut) continue;
        float mx = static_cast<float>(feld.cx * CHUNK + CHUNK / 2) - auge.x;
        float mz = static_cast<float>(feld.cz * CHUNK + CHUNK / 2) - auge.z;
        if (std::sqrt(mx * mx + mz * mz) > sichtweite + CHUNK) continue;
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
    for (int schritt = 0; schritt < 320 && gelaufen <= weite; ++schritt) {
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

size_t Welt::aenderungen() const {
    size_t summe = 0;
    for (const auto& eintrag : notizen) summe += eintrag.second.size();
    return summe;
}

bool Welt::speichern(const std::string& pfad) const {
    std::string text = "saat " + std::to_string(saatwert) + "\n";
    char zeile[80];
    for (const auto& eintrag : notizen) {
        int cx = feldX(eintrag.first);
        int cz = feldZ(eintrag.first);
        for (const auto& notiz : eintrag.second) {
            int y = notiz.first / 256;
            int rest = notiz.first % 256;
            int x = cx * CHUNK + (rest % 16);
            int z = cz * CHUNK + (rest / 16);
            std::snprintf(zeile, sizeof(zeile), "b %d %d %d %d\n", x, y, z,
                          static_cast<int>(notiz.second));
            text += zeile;
        }
    }
    return fw::schreibeText(pfad, text);
}

bool Welt::laden(const std::string& pfad) {
    std::string inhalt = fw::leseText(pfad);
    if (inhalt.empty()) return false;
    std::vector<std::string> zeilen = fw::zerlegen(inhalt, '\n');
    unsigned gespeichert = saatwert;
    for (const std::string& roh : zeilen) {
        std::string zeile = fw::putzen(roh);
        if (zeile.rfind("saat", 0) == 0) {
            gespeichert = static_cast<unsigned>(std::atoi(zeile.c_str() + 4));
        }
    }
    beginnen(gespeichert);
    notizen.clear();
    for (const std::string& roh : zeilen) {
        std::string zeile = fw::putzen(roh);
        if (zeile.rfind("b ", 0) != 0) continue;
        int x = 0;
        int y = 0;
        int z = 0;
        int id = 0;
        if (std::sscanf(zeile.c_str() + 2, "%d %d %d %d", &x, &y, &z, &id) != 4) continue;
        if (y < 0 || y >= HOEHE) continue;
        notizen[schluessel(teilenAb(x, CHUNK), teilenAb(z, CHUNK))].push_back(
            {stelleIn(restVon(x, CHUNK), y, restVon(z, CHUNK)), static_cast<unsigned char>(id)});
    }
    return true;
}

}
