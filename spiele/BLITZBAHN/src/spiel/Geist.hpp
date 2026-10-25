#pragma once

#include <string>
#include <vector>

#include "Fahrzeug.hpp"

namespace blitzbahn {

constexpr float GEIST_TAKT = 1.0f / 30.0f;

class Geist {
public:
    void leeren();
    void aufnehmen(const Lage& lage);
    bool leer() const { return proben.empty(); }
    float dauer() const { return proben.empty() ? 0.0f : (proben.size() - 1) * GEIST_TAKT; }
    Lage bei(float zeit) const;

    std::string speichern(int zeitMs) const;
    static bool laden(const std::string& text, Geist& ziel, int& zeitMs);

private:
    std::vector<Lage> proben;
};

}
