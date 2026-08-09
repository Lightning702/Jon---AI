#pragma once

#include <string>
#include <vector>

#include "Bloecke.hpp"
#include "fw/Maler.hpp"
#include "fw/Netz.hpp"

namespace blockwelt {

constexpr int CHUNK = 16;
constexpr int HOEHE = 64;
constexpr int CHUNKS = 12;
constexpr int WEITE = CHUNK * CHUNKS;
constexpr int MEERESHOEHE = 26;

struct Treffer {
    bool getroffen = false;
    int x = 0;
    int y = 0;
    int z = 0;
    int vorX = 0;
    int vorY = 0;
    int vorZ = 0;
    unsigned char block = LUFT;
};

class Welt {
public:
    void erzeugen(unsigned saat);
    void netzeBauen();
    void freigeben();

    unsigned char block(int x, int y, int z) const;
    void setzeBlock(int x, int y, int z, unsigned char id);
    bool innen(int x, int y, int z) const {
        return x >= 0 && z >= 0 && y >= 0 && x < WEITE && z < WEITE && y < HOEHE;
    }
    bool festBei(int x, int y, int z) const { return istFest(block(x, y, z)); }
    int hoeheBei(int x, int z) const;

    Treffer strahl(fw::Vec3 start, fw::Vec3 richtung, float weite) const;

    void netzeAuffrischen();
    void zeichnen(fw::Maler& maler, fw::Vec3 auge, float sichtweite) const;
    void zeichnenWasser(fw::Maler& maler, fw::Vec3 auge, float sichtweite) const;

    bool speichern(const std::string& pfad) const;
    bool laden(const std::string& pfad);

    unsigned saat() const { return saatwert; }
    int chunkZahl() const { return CHUNKS * CHUNKS; }
    size_t aenderungen() const { return geaendert.size(); }

private:
    struct Feld {
        fw::Netz fest;
        fw::Netz fluessig;
        fw::Vec3 mitte;
        bool schmutzig = true;
    };

    void chunkBauen(int cx, int cz);
    float lichtEcke(int x, int y, int z, int dx, int dy, int dz, int achse) const;

    std::vector<unsigned char> bloecke;
    std::vector<Feld> felder;
    std::vector<std::pair<int, unsigned char>> geaendert;
    unsigned saatwert = 5;
};

}
