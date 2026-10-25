#pragma once

#include <string>
#include <unordered_map>
#include <vector>

#include "fw/Mathe.hpp"

namespace blitzbahn {

constexpr float ZELLE = 20.0f;
constexpr float STUFE = 4.0f;
constexpr float HALBE_BREITE = 7.0f;
constexpr float WAND_HOEHE = 1.1f;
constexpr float KURVE_INNEN = 3.0f;
constexpr float KURVE_AUSSEN = 17.0f;
constexpr float SCHANZE_HOEHE = 1.8f;

enum Teil : int {
    LEER = 0,
    GERADE,
    KURVE,
    RAMPE,
    START,
    ZIEL,
    KONTROLLE,
    SCHUB,
    SCHANZE,
    PLATTE,
    STEIL,
    WELLEN,
    TEIL_ANZAHL
};

const char* teilName(int teil);
int teilSpanne(int teil);
bool teilHatWand(int teil);
bool teilIstTor(int teil);

struct Stueck {
    int teil = GERADE;
    int x = 0;
    int y = 0;
    int z = 0;
    int dreh = 0;
};

struct Boden {
    bool da = false;
    float hoehe = 0.0f;
    fw::Vec3 normale = fw::Vec3(0.0f, 1.0f, 0.0f);
    int stueck = -1;
    int teil = LEER;
    float lx = 0.0f;
    float lz = 0.0f;
};

fw::Vec3 richtungWelt(int dreh, fw::Vec3 lokal);
fw::Vec3 lokalZuWelt(const Stueck& stueck, fw::Vec3 lokal);
fw::Vec3 weltZuLokal(const Stueck& stueck, fw::Vec3 welt);
float teilHoehe(int teil, float lx, float lz, bool& drin, fw::Vec3& normaleLokal);
int zelleVon(float wert);

class Strecke {
public:
    std::string name = "Neue Strecke";
    std::string kennung;
    std::string autor = "FelWorks";
    std::vector<Stueck> stuecke;

    int finden(int x, int y, int z) const;
    int belegt(int x, int z, int y0, int y1) const;
    void setzen(const Stueck& stueck);
    bool entfernen(int index);
    void leeren();
    void geaendert() { indexAlt = true; }

    Boden boden(fw::Vec3 ort, float spielraum) const;
    float wand(fw::Vec3 vorher, fw::Vec3& ort, fw::Vec3& fahrt, float radius) const;
    bool startpunkt(fw::Vec3& ort, float& gier) const;
    int kontrollZahl() const;
    bool hatStart() const;
    bool hatZiel() const;
    float tiefstes() const;
    void grenzen(int& x0, int& z0, int& x1, int& z1) const;

    std::string speichern() const;
    static bool laden(const std::string& text, Strecke& ziel);
    std::string kompakt() const;
    static bool ausKompakt(const std::string& text, Strecke& ziel);

private:
    void indizieren() const;
    static long long schluessel(int x, int z) {
        return (static_cast<long long>(x) << 32) ^ static_cast<long long>(static_cast<unsigned>(z));
    }

    mutable std::unordered_map<long long, std::vector<int>> raster;
    mutable bool indexAlt = true;
};

struct Bauplan {
    int x = 0;
    int y = 0;
    int z = 0;
    int richtung = 0;
};

bool streckeBauen(const std::string& befehle, Strecke& ziel, std::string* fehler = nullptr);
std::vector<Strecke> offizielleStrecken();
Strecke zufallsStrecke(unsigned saat, int laenge);

}
