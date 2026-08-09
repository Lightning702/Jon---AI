#pragma once

#include "fw/Mathe.hpp"
#include "fw/Shader.hpp"

namespace blockwelt {

class Himmel {
public:
    ~Himmel();

    bool erstellen();
    void freigeben();
    void zeichnen(fw::Vec3 blick, fw::Vec3 rechts, fw::Vec3 oben, fw::Vec3 sonne, float tag,
                  float sichtfeld, float seite);

private:
    fw::Shader schattierer;
    unsigned feld = 0;
    unsigned puffer = 0;
};

}
