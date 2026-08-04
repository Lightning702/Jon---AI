#pragma once

#include "../../engine/core/Types.hpp"

#include <string>

namespace sf {

enum class NameCulture : u32 {
    Human = 0,
    Keth,
    Avari,
    Thuln,
    Sorvek,
    Mycel,
    Vessk,
    Draal,
    Ilun,
    Okra,
    Nebris,
    Tarsh,
    Precursor,
    Count
};

std::string generateName(u64 seed, NameCulture culture, u32 minimumSyllables, u32 maximumSyllables);
std::string generateStarDesignation(u64 seed);
std::string generatePlanetDesignation(const std::string& starName, u32 planetIndex);
std::string generateMoonDesignation(const std::string& planetName, u32 moonIndex);
const char* cultureName(NameCulture culture);

}
