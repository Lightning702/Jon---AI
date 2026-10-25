#pragma once

#include "Fahrzeug.hpp"
#include "Strecke.hpp"

namespace blitzbahn {

class Pilot {
public:
    void neu() { fortschritt = 0; }
    Eingabe lenken(const Strecke& strecke, const Fahrzeug& wagen);
    int stand() const { return fortschritt; }

private:
    int fortschritt = 0;
};

}
