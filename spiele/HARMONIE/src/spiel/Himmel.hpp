#pragma once

#include "fw/Mathe.hpp"
#include "fw/Shader.hpp"

namespace harmonie {

class Himmel {
public:
    ~Himmel();

    bool erstellen();
    void freigeben();
    void zeichnen(float zeit, float drehung, float regenbogen, fw::Vec2 flaeche);

private:
    fw::Shader schattierer;
    unsigned feld = 0;
    unsigned puffer = 0;
};

}
