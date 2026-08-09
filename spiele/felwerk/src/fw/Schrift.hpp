#pragma once

#include <string>
#include <vector>

#include "GL.hpp"
#include "Mathe.hpp"
#include "Shader.hpp"

namespace fw {

struct Farbe {
    float r = 1.0f;
    float g = 1.0f;
    float b = 1.0f;
    float a = 1.0f;
    Farbe() = default;
    Farbe(float ar, float ag, float ab, float aa = 1.0f) : r(ar), g(ag), b(ab), a(aa) {}
    Farbe(Vec3 v, float aa = 1.0f) : r(v.x), g(v.y), b(v.z), a(aa) {}
};

class Schrift {
public:
    ~Schrift();

    bool erstellen(const char* name, int hoehe, bool fett);
    void freigeben();

    void beginnen(int breite, int hoehe);
    void beenden();

    void flaeche(float x, float y, float breite, float hoehe, Farbe farbe);
    void rahmen(float x, float y, float breite, float hoehe, float staerke, Farbe farbe);
    void text(float x, float y, const std::string& inhalt, Farbe farbe, float mass = 1.0f);
    void textMittig(float mitteX, float y, const std::string& inhalt, Farbe farbe, float mass = 1.0f);
    float textBreite(const std::string& inhalt, float mass = 1.0f) const;
    float zeilenhoehe(float mass = 1.0f) const { return hoeheZeile * mass; }

private:
    struct Zeichen {
        float u0 = 0.0f;
        float v0 = 0.0f;
        float u1 = 0.0f;
        float v1 = 0.0f;
        float breite = 0.0f;
        float hoehe = 0.0f;
        float vorschub = 0.0f;
    };

    void ausgeben();
    void quad(float x, float y, float breite, float hoehe, float u0, float v0, float u1, float v1,
              Farbe farbe);

    Shader schattierer;
    unsigned atlas = 0;
    unsigned feld = 0;
    unsigned puffer = 0;
    std::vector<float> staffel;
    Zeichen zeichen[256];
    float hoeheZeile = 16.0f;
    float weissU = 0.999f;
    float weissV = 0.999f;
    int flaecheBreite = 0;
    int flaecheHoehe = 0;
    bool laeuft = false;
};

}
