#include "Strecke.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <sstream>
#include <tuple>

#include "fw/Werkzeug.hpp"
#include "fw/Zufall.hpp"

namespace blitzbahn {

using namespace fw;

namespace {

int drehung(int d) { return ((d % 4) + 4) % 4; }

float drehSinus(int d) {
    int r = drehung(d);
    return r == 1 ? 1.0f : (r == 3 ? -1.0f : 0.0f);
}

float drehKosinus(int d) {
    int r = drehung(d);
    return r == 0 ? 1.0f : (r == 2 ? -1.0f : 0.0f);
}

int schrittX(int richtung) {
    int r = drehung(richtung);
    return r == 1 ? 1 : (r == 3 ? -1 : 0);
}

int schrittZ(int richtung) {
    int r = drehung(richtung);
    return r == 0 ? 1 : (r == 2 ? -1 : 0);
}

}

const char* teilName(int teil) {
    static const char* namen[] = {"Leer",    "Gerade", "Kurve",   "Rampe",  "Start",      "Ziel",
                                  "Kontrolle", "Turbo", "Schanze", "Platte", "Steilrampe", "Wellen"};
    return teil >= 0 && teil < TEIL_ANZAHL ? namen[teil] : "?";
}

int teilSpanne(int teil) {
    if (teil == RAMPE) return 1;
    if (teil == STEIL) return 2;
    return 0;
}

bool teilHatWand(int teil) { return teil != PLATTE && teil != LEER; }

bool teilIstTor(int teil) { return teil == START || teil == ZIEL || teil == KONTROLLE; }

int zelleVon(float wert) { return static_cast<int>(std::floor((wert + ZELLE * 0.5f) / ZELLE)); }

Vec3 richtungWelt(int dreh, Vec3 lokal) {
    float s = drehSinus(dreh);
    float c = drehKosinus(dreh);
    return Vec3(lokal.x * c + lokal.z * s, lokal.y, -lokal.x * s + lokal.z * c);
}

Vec3 lokalZuWelt(const Stueck& stueck, Vec3 lokal) {
    Vec3 w = richtungWelt(stueck.dreh, lokal);
    return Vec3(stueck.x * ZELLE + w.x, stueck.y * STUFE + w.y, stueck.z * ZELLE + w.z);
}

Vec3 weltZuLokal(const Stueck& stueck, Vec3 welt) {
    float dx = welt.x - stueck.x * ZELLE;
    float dz = welt.z - stueck.z * ZELLE;
    float s = drehSinus(stueck.dreh);
    float c = drehKosinus(stueck.dreh);
    return Vec3(dx * c - dz * s, welt.y - stueck.y * STUFE, dx * s + dz * c);
}

float teilHoehe(int teil, float lx, float lz, bool& drin, Vec3& normaleLokal) {
    const float rand = 0.002f;
    normaleLokal = Vec3(0.0f, 1.0f, 0.0f);
    if (teil == LEER) {
        drin = false;
        return 0.0f;
    }
    if (teil == PLATTE) {
        drin = std::fabs(lx) <= ZELLE * 0.5f + rand && std::fabs(lz) <= ZELLE * 0.5f + rand;
        return 0.0f;
    }
    if (teil == KURVE) {
        float dx = lx - ZELLE * 0.5f;
        float dz = lz + ZELLE * 0.5f;
        float d = std::sqrt(dx * dx + dz * dz);
        drin = d >= KURVE_INNEN && d <= KURVE_AUSSEN && lx <= ZELLE * 0.5f + rand &&
               lz >= -ZELLE * 0.5f - rand;
        return 0.0f;
    }
    drin = std::fabs(lx) <= HALBE_BREITE + rand && std::fabs(lz) <= ZELLE * 0.5f + rand;
    float hoehe = 0.0f;
    float steigung = 0.0f;
    float t = klemme((lz + ZELLE * 0.5f) / ZELLE, 0.0f, 1.0f);
    if (teil == RAMPE) {
        hoehe = t * STUFE;
        steigung = STUFE / ZELLE;
    } else if (teil == STEIL) {
        hoehe = t * STUFE * 2.0f;
        steigung = STUFE * 2.0f / ZELLE;
    } else if (teil == SCHANZE) {
        if (lz > 0.0f) {
            float u = klemme(lz / (ZELLE * 0.5f), 0.0f, 1.0f);
            hoehe = SCHANZE_HOEHE * u * u;
            steigung = SCHANZE_HOEHE * 2.0f * u / (ZELLE * 0.5f);
        }
    } else if (teil == WELLEN) {
        float w = t * TAU * 2.0f;
        hoehe = 0.45f * (1.0f - std::cos(w));
        steigung = 0.45f * std::sin(w) * TAU * 2.0f / ZELLE;
    }
    normaleLokal = normiert(Vec3(0.0f, 1.0f, -steigung));
    return hoehe;
}

void Strecke::indizieren() const {
    if (!indexAlt) return;
    raster.clear();
    for (int i = 0; i < static_cast<int>(stuecke.size()); ++i) {
        raster[schluessel(stuecke[i].x, stuecke[i].z)].push_back(i);
    }
    indexAlt = false;
}

int Strecke::finden(int x, int y, int z) const {
    for (int i = 0; i < static_cast<int>(stuecke.size()); ++i) {
        const Stueck& s = stuecke[i];
        if (s.x == x && s.y == y && s.z == z) return i;
    }
    return -1;
}

int Strecke::belegt(int x, int z, int y0, int y1) const {
    for (int i = 0; i < static_cast<int>(stuecke.size()); ++i) {
        const Stueck& s = stuecke[i];
        if (s.x != x || s.z != z) continue;
        int a = s.y;
        int b = s.y + teilSpanne(s.teil);
        if (a <= y1 + 1 && b >= y0 - 1) return i;
    }
    return -1;
}

void Strecke::setzen(const Stueck& stueck) {
    int alt = finden(stueck.x, stueck.y, stueck.z);
    if (alt >= 0) {
        stuecke[alt] = stueck;
    } else {
        stuecke.push_back(stueck);
    }
    indexAlt = true;
}

bool Strecke::entfernen(int index) {
    if (index < 0 || index >= static_cast<int>(stuecke.size())) return false;
    stuecke.erase(stuecke.begin() + index);
    indexAlt = true;
    return true;
}

void Strecke::leeren() {
    stuecke.clear();
    indexAlt = true;
}

Boden Strecke::boden(Vec3 ort, float spielraum) const {
    indizieren();
    Boden bester;
    auto treffer = raster.find(schluessel(zelleVon(ort.x), zelleVon(ort.z)));
    if (treffer == raster.end()) return bester;
    for (int i : treffer->second) {
        const Stueck& s = stuecke[i];
        Vec3 lokal = weltZuLokal(s, ort);
        bool drin = false;
        Vec3 normale;
        float h = teilHoehe(s.teil, lokal.x, lokal.z, drin, normale);
        if (!drin) continue;
        float welt = s.y * STUFE + h;
        if (welt > ort.y + spielraum) continue;
        if (bester.da && welt <= bester.hoehe) continue;
        bester.da = true;
        bester.hoehe = welt;
        bester.normale = normiert(richtungWelt(s.dreh, normale));
        bester.stueck = i;
        bester.teil = s.teil;
        bester.lx = lokal.x;
        bester.lz = lokal.z;
    }
    return bester;
}

float Strecke::wand(Vec3 vorher, Vec3& ort, Vec3& fahrt, float radius) const {
    indizieren();
    float wucht = 0.0f;
    auto treffer = raster.find(schluessel(zelleVon(ort.x), zelleVon(ort.z)));
    if (treffer == raster.end()) return 0.0f;
    for (int i : treffer->second) {
        const Stueck& s = stuecke[i];
        if (!teilHatWand(s.teil)) continue;
        Vec3 lokal = weltZuLokal(s, ort);
        Vec3 lokalVorher = weltZuLokal(s, vorher);
        bool drin = false;
        Vec3 n;
        float flaeche = 0.0f;
        Vec3 wandNormale;
        bool stoss = false;
        if (s.teil == KURVE) {
            float dx = lokal.x - ZELLE * 0.5f;
            float dz = lokal.z + ZELLE * 0.5f;
            float d = std::sqrt(dx * dx + dz * dz);
            float dxv = lokalVorher.x - ZELLE * 0.5f;
            float dzv = lokalVorher.z + ZELLE * 0.5f;
            float dv = std::sqrt(dxv * dxv + dzv * dzv);
            if (lokal.x > ZELLE * 0.5f + 0.5f || lokal.z < -ZELLE * 0.5f - 0.5f) continue;
            if (dv < KURVE_INNEN - 0.2f || dv > KURVE_AUSSEN + 0.2f) continue;
            if (lokal.y - flaeche > WAND_HOEHE + 0.2f) continue;
            if (lokal.y < -2.0f) continue;
            Vec3 radial = d > 1e-4f ? Vec3(dx / d, 0.0f, dz / d) : Vec3(1.0f, 0.0f, 0.0f);
            if (d < KURVE_INNEN + radius) {
                float ziel = KURVE_INNEN + radius;
                lokal.x = ZELLE * 0.5f + radial.x * ziel;
                lokal.z = -ZELLE * 0.5f + radial.z * ziel;
                wandNormale = radial;
                stoss = true;
            } else if (d > KURVE_AUSSEN - radius) {
                float ziel = KURVE_AUSSEN - radius;
                lokal.x = ZELLE * 0.5f + radial.x * ziel;
                lokal.z = -ZELLE * 0.5f + radial.z * ziel;
                wandNormale = -radial;
                stoss = true;
            }
        } else {
            if (std::fabs(lokal.z) > ZELLE * 0.5f + 0.01f) continue;
            if (std::fabs(lokalVorher.x) > HALBE_BREITE + 0.2f) continue;
            flaeche = teilHoehe(s.teil, 0.0f, lokal.z, drin, n);
            if (lokal.y - flaeche > WAND_HOEHE + 0.2f) continue;
            if (lokal.y - flaeche < -2.0f) continue;
            if (lokal.x > HALBE_BREITE - radius) {
                lokal.x = HALBE_BREITE - radius;
                wandNormale = Vec3(-1.0f, 0.0f, 0.0f);
                stoss = true;
            } else if (lokal.x < -HALBE_BREITE + radius) {
                lokal.x = -HALBE_BREITE + radius;
                wandNormale = Vec3(1.0f, 0.0f, 0.0f);
                stoss = true;
            }
        }
        if (!stoss) continue;
        Vec3 neu = lokalZuWelt(s, lokal);
        ort.x = neu.x;
        ort.z = neu.z;
        Vec3 wn = normiert(richtungWelt(s.dreh, wandNormale));
        float vn = punkt(fahrt, wn);
        if (vn < 0.0f) {
            fahrt -= wn * (vn * 1.3f);
            Vec3 tangential = fahrt - wn * punkt(fahrt, wn);
            fahrt = fahrt - tangential * 0.04f;
            wucht = std::max(wucht, -vn);
        }
    }
    return wucht;
}

bool Strecke::startpunkt(Vec3& ort, float& gier) const {
    for (const Stueck& s : stuecke) {
        if (s.teil != START) continue;
        ort = lokalZuWelt(s, Vec3(0.0f, 0.0f, -4.0f));
        Vec3 vorne = richtungWelt(s.dreh, Vec3(0.0f, 0.0f, 1.0f));
        gier = std::atan2(vorne.x, vorne.z);
        return true;
    }
    ort = Vec3(0.0f, 0.0f, 0.0f);
    gier = 0.0f;
    return false;
}

int Strecke::kontrollZahl() const {
    int n = 0;
    for (const Stueck& s : stuecke) n += s.teil == KONTROLLE ? 1 : 0;
    return n;
}

bool Strecke::hatStart() const {
    for (const Stueck& s : stuecke)
        if (s.teil == START) return true;
    return false;
}

bool Strecke::hatZiel() const {
    for (const Stueck& s : stuecke)
        if (s.teil == ZIEL) return true;
    return false;
}

float Strecke::tiefstes() const {
    float t = 0.0f;
    bool erstes = true;
    for (const Stueck& s : stuecke) {
        float y = s.y * STUFE;
        if (erstes || y < t) t = y;
        erstes = false;
    }
    return t;
}

void Strecke::grenzen(int& x0, int& z0, int& x1, int& z1) const {
    x0 = z0 = 0;
    x1 = z1 = 0;
    bool erstes = true;
    for (const Stueck& s : stuecke) {
        if (erstes) {
            x0 = x1 = s.x;
            z0 = z1 = s.z;
            erstes = false;
            continue;
        }
        x0 = std::min(x0, s.x);
        x1 = std::max(x1, s.x);
        z0 = std::min(z0, s.z);
        z1 = std::max(z1, s.z);
    }
}

std::string Strecke::speichern() const {
    std::ostringstream aus;
    aus << "BLITZBAHN 1\n";
    aus << "name " << name << "\n";
    aus << "autor " << autor << "\n";
    for (const Stueck& s : stuecke) {
        aus << "teil " << s.teil << " " << s.x << " " << s.y << " " << s.z << " " << drehung(s.dreh) << "\n";
    }
    return aus.str();
}

bool Strecke::laden(const std::string& text, Strecke& ziel) {
    std::istringstream ein(text);
    std::string zeile;
    if (!std::getline(ein, zeile) || zeile.rfind("BLITZBAHN", 0) != 0) return false;
    Strecke neu;
    while (std::getline(ein, zeile)) {
        if (!zeile.empty() && zeile.back() == '\r') zeile.pop_back();
        if (zeile.rfind("name ", 0) == 0) {
            neu.name = zeile.substr(5);
        } else if (zeile.rfind("autor ", 0) == 0) {
            neu.autor = zeile.substr(6);
        } else if (zeile.rfind("teil ", 0) == 0) {
            Stueck s;
            if (std::sscanf(zeile.c_str() + 5, "%d %d %d %d %d", &s.teil, &s.x, &s.y, &s.z, &s.dreh) == 5 &&
                s.teil > LEER && s.teil < TEIL_ANZAHL) {
                s.dreh = drehung(s.dreh);
                neu.stuecke.push_back(s);
            }
        }
    }
    neu.kennung = ziel.kennung;
    neu.geaendert();
    ziel = neu;
    return true;
}

std::string Strecke::kompakt() const {
    std::ostringstream aus;
    std::string sauber;
    for (char c : name) sauber += (c == '~' || c == '|') ? '-' : c;
    aus << sauber << "~";
    for (const Stueck& s : stuecke) {
        aus << s.teil << "." << s.x << "." << s.y << "." << s.z << "." << drehung(s.dreh) << "_";
    }
    return aus.str();
}

bool Strecke::ausKompakt(const std::string& text, Strecke& ziel) {
    size_t trenner = text.find('~');
    if (trenner == std::string::npos) return false;
    Strecke neu;
    neu.name = text.substr(0, trenner);
    neu.autor = "Mitspieler";
    for (const std::string& teil : zerlegen(text.substr(trenner + 1), '_')) {
        if (teil.empty()) continue;
        Stueck s;
        if (std::sscanf(teil.c_str(), "%d.%d.%d.%d.%d", &s.teil, &s.x, &s.y, &s.z, &s.dreh) == 5 && s.teil > LEER &&
            s.teil < TEIL_ANZAHL) {
            neu.stuecke.push_back(s);
        }
    }
    if (neu.stuecke.empty()) return false;
    neu.geaendert();
    ziel = neu;
    return true;
}

bool streckeBauen(const std::string& befehle, Strecke& ziel, std::string* fehler) {
    int x = 0;
    int y = 0;
    int z = 0;
    int h = 0;
    ziel.leeren();
    std::set<std::tuple<int, int, int>> belegt;
    auto platz = [&](int teil, int stufe, int dreh) -> bool {
        int oben = stufe + teilSpanne(teil);
        for (int lage = stufe - 1; lage <= oben + 1; ++lage) {
            if (belegt.count({x, lage, z})) {
                if (fehler) {
                    char text[120];
                    std::snprintf(text, sizeof(text), "Feld %d,%d,%d doppelt belegt", x, stufe, z);
                    *fehler = text;
                }
                return false;
            }
        }
        for (int lage = stufe; lage <= oben; ++lage) belegt.insert({x, lage, z});
        Stueck s;
        s.teil = teil;
        s.x = x;
        s.y = stufe;
        s.z = z;
        s.dreh = drehung(dreh);
        ziel.stuecke.push_back(s);
        return true;
    };
    auto vor = [&]() {
        x += schrittX(h);
        z += schrittZ(h);
    };
    if (!platz(START, y, h)) return false;
    vor();
    for (char c : befehle) {
        bool ok = true;
        switch (c) {
            case 'G': ok = platz(GERADE, y, h); vor(); break;
            case 'L': ok = platz(KURVE, y, h); h = drehung(h + 1); vor(); break;
            case 'R': ok = platz(KURVE, y, h + 1); h = drehung(h + 3); vor(); break;
            case 'H': ok = platz(RAMPE, y, h); y += 1; vor(); break;
            case 'T': y -= 1; ok = platz(RAMPE, y, h + 2); vor(); break;
            case 'U': ok = platz(STEIL, y, h); y += 2; vor(); break;
            case 'D': y -= 2; ok = platz(STEIL, y, h + 2); vor(); break;
            case 'S': ok = platz(SCHUB, y, h); vor(); break;
            case 'K': ok = platz(KONTROLLE, y, h); vor(); break;
            case 'J': ok = platz(SCHANZE, y, h); vor(); break;
            case 'W': ok = platz(WELLEN, y, h); vor(); break;
            case 'P': ok = platz(PLATTE, y, h); vor(); break;
            case 'Z': ok = platz(ZIEL, y, h); vor(); break;
            case '_': vor(); break;
            case 'v': y -= 1; break;
            case 'u': y += 1; break;
            default: break;
        }
        if (!ok) return false;
    }
    ziel.geaendert();
    return true;
}

std::vector<Strecke> offizielleStrecken() {
    struct Vorlage {
        const char* kennung;
        const char* name;
        const char* befehle;
    };
    static const Vorlage vorlagen[] = {
        {"o1", "Auftakt", "GGGGGLGGGGKGGGRGGGGSGGGGRGGGGKGGGLGGGGSGGGGGZGGG"},
        {"o2", "Doppelkehre", "GGGRGLLGGKGRRGGSGGLGGRGGKGLGGRRGGSGLLGGZGGG"},
        {"o3", "Sprungbrett", "GGSGJ____GGGGKGLGGSSGJ____GGGGRGGKGGSGJ_____GGGGZGGG"},
        {"o4", "Hochbahn", "GGHHGGLGGKGGHGGRGGGTGGLSGGKGGTTGGRGGHGGSGTGGZGGG"},
        {"o5", "Wellenreiter", "GGWWGGLWWWGKGGRGWWWGGSGGLGWWGKGGRWWWGGZGGG"},
        {"o6", "Turbotal", "SSGTTGGRGSGKGGLGGHHGGSSGKGGRGTTGGLGSSGGZGGG"},
        {"o7", "Himmelsleiter", "GUGUGLGGKGRSGJ____vGGGRGKGDGGLGUGGRSGJ___vGGGKGLGDGGZGGG"},
        {"o8", "Grosser Preis", "GSGGLGHGGKGRSGJ____GGGLGWWGGKGRGUGLGGSGGDGRGTGGKGGLSGGHGGRGGJ___GGGKGLGWWGGTGGZGGG"},
    };
    std::vector<Strecke> liste;
    for (const Vorlage& v : vorlagen) {
        Strecke s;
        std::string fehler;
        if (!streckeBauen(v.befehle, s, &fehler)) continue;
        s.kennung = v.kennung;
        s.name = v.name;
        s.autor = "FelWorks";
        liste.push_back(s);
    }
    return liste;
}

Strecke zufallsStrecke(unsigned saat, int laenge) {
    Zufall zufall(0x5EED0000ull + saat * 2654435761ull);
    for (int versuch = 0; versuch < 400; ++versuch) {
        std::string befehle;
        int hoehe = 0;
        int seitKontrolle = 0;
        for (int i = 0; i < laenge; ++i) {
            float w = zufall.einheit();
            char c = 'G';
            if (w < 0.17f) c = 'L';
            else if (w < 0.34f) c = 'R';
            else if (w < 0.42f) c = 'S';
            else if (w < 0.5f) c = 'H';
            else if (w < 0.57f && hoehe > 0) c = 'T';
            else if (w < 0.62f) c = 'W';
            else if (w < 0.66f && hoehe > 1) c = 'D';
            else if (w < 0.7f) c = 'U';
            else if (w < 0.74f) {
                befehle += "SJ__GG";
                i += 5;
                continue;
            }
            if (c == 'H') hoehe += 1;
            if (c == 'T') hoehe -= 1;
            if (c == 'U') hoehe += 2;
            if (c == 'D') hoehe -= 2;
            befehle += c;
            if (++seitKontrolle >= 7) {
                befehle += 'K';
                seitKontrolle = 0;
            }
        }
        befehle += "GZ";
        Strecke s;
        if (!streckeBauen("G" + befehle, s)) continue;
        s.name = "Zufallsbahn " + std::to_string(saat % 10000);
        s.autor = "Zufall";
        return s;
    }
    Strecke s;
    streckeBauen("GGGLGGKGGRGGZ", s);
    s.name = "Zufallsbahn";
    return s;
}

}
