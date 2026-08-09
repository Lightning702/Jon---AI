#pragma once

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "Bloecke.hpp"
#include "fw/Maler.hpp"
#include "fw/Netz.hpp"

namespace blockwelt {

constexpr int CHUNK = 16;
constexpr int HOEHE = 100;
constexpr int MEER = 32;

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

struct Feld {
    int cx = 0;
    int cz = 0;
    int gipfel = 0;
    std::vector<unsigned char> daten;
    fw::Netz fest;
    fw::Netz fluessig;
    bool gebaut = false;
    bool schmutzig = true;
};

class Welt {
public:
    void beginnen(unsigned saat);
    void freigeben();

    unsigned char block(int x, int y, int z) const;
    void setzeBlock(int x, int y, int z, unsigned char id);
    bool festBei(int x, int y, int z) const { return istFest(block(x, y, z)); }
    int hoeheBei(int x, int z) const;
    bool geladen(int x, int z) const;

    void umgebungPflegen(fw::Vec3 spieler, int radius, int erzeugeJeBild, int netzeJeBild);
    void zeichnen(fw::Maler& maler, fw::Vec3 auge, float sichtweite) const;
    void zeichnenWasser(fw::Maler& maler, fw::Vec3 auge, float sichtweite) const;

    Treffer strahl(fw::Vec3 start, fw::Vec3 richtung, float weite) const;

    bool speichern(const std::string& pfad) const;
    bool laden(const std::string& pfad);

    unsigned saat() const { return saatwert; }
    size_t felderZahl() const { return felder.size(); }
    size_t aenderungen() const;
    int sichtbareNetze() const { return gezeichnet; }
    std::string bezirkName(int x, int z) const;

    static long long schluessel(int cx, int cz) {
        return (static_cast<long long>(cx) << 32) | static_cast<unsigned int>(cz);
    }
    static int feldX(long long wert) { return static_cast<int>(wert >> 32); }
    static int feldZ(long long wert) { return static_cast<int>(static_cast<unsigned int>(wert)); }

private:
    Feld* feldSuchen(int cx, int cz);
    const Feld* feldSuchen(int cx, int cz) const;
    Feld* feldErzeugen(int cx, int cz);
    void feldFuellen(Feld& feld);
    void netzBauen(Feld& feld);
    void schmutzigMachen(int x, int z);
    float eckenLicht(int x, int y, int z, int dx, int dy, int dz, int achse) const;

    std::unordered_map<long long, std::unique_ptr<Feld>> felder;
    std::unordered_map<long long, std::vector<std::pair<int, unsigned char>>> notizen;
    unsigned saatwert = 1337;
    mutable int gezeichnet = 0;
};

int hoeheAn(int x, int z, unsigned saat);
int bezirkAn(int x, int z, unsigned saat);
const char* bezirkText(int bezirk);

}
