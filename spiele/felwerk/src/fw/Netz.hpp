#pragma once

#include <cstdint>
#include <vector>

#include "GL.hpp"
#include "Mathe.hpp"

namespace fw {

struct Ecke {
    Vec3 ort;
    Vec3 normale;
    Vec3 farbe;
    float rauheit = 0.0f;
};

class Bauer {
public:
    void leeren();
    bool leer() const { return ecken.empty(); }
    size_t eckenZahl() const { return ecken.size(); }
    size_t dreieckZahl() const { return indizes.size() / 3; }

    void ecke(Vec3 ort, Vec3 normale, Vec3 farbe, float rauheit = 0.0f);
    void dreieck(Vec3 a, Vec3 b, Vec3 c, Vec3 farbe, float rauheit = 0.0f);
    void viereck(Vec3 a, Vec3 b, Vec3 c, Vec3 d, Vec3 farbe, float rauheit = 0.0f);

    void quader(Vec3 mitte, Vec3 halb, Vec3 farbe, float drehung = 0.0f, float rauheit = 0.0f);
    void kugel(Vec3 mitte, Vec3 radien, Vec3 farbe, int ringe = 10, int segmente = 14,
               float rauheit = 0.0f);
    void halbkugel(Vec3 mitte, Vec3 radien, Vec3 farbe, int ringe = 6, int segmente = 14,
                   float rauheit = 0.0f);
    void roehre(Vec3 fuss, float radiusUnten, float radiusOben, float hoehe, Vec3 farbe,
                int segmente = 10, float rauheit = 0.0f);
    void scheibe(Vec3 mitte, float radius, Vec3 farbe, int segmente = 16, float rauheit = 0.0f);
    void band(Vec3 von, Vec3 bis, float breite, float dicke, Vec3 farbe);

    void anhaengen(const Bauer& anderer, Vec3 versatz, float drehung = 0.0f, float skalierung = 1.0f);

    const std::vector<Ecke>& daten() const { return ecken; }
    const std::vector<uint32_t>& reihenfolge() const { return indizes; }

private:
    std::vector<Ecke> ecken;
    std::vector<uint32_t> indizes;
};

class Netz {
public:
    ~Netz();

    void hochladen(const Bauer& bauer, bool dynamisch = false);
    void zeichnen() const;
    void freigeben();
    bool gueltig() const { return feld != 0 && anzahl > 0; }
    int dreiecke() const { return anzahl / 3; }

private:
    unsigned feld = 0;
    unsigned puffer = 0;
    unsigned reihung = 0;
    int anzahl = 0;
    int kapazitaetEcken = 0;
    int kapazitaetIndizes = 0;
};

}
