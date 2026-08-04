#include "NameGenerator.hpp"

#include "../../engine/math/Random.hpp"

#include <cstdio>
#include <vector>

namespace sf {
namespace {

struct Phonotactics {
    const char* const* onsets;
    u32 onsetCount;
    const char* const* nuclei;
    u32 nucleusCount;
    const char* const* codas;
    u32 codaCount;
    f32 codaProbability;
};

const char* const kHumanOnsets[] = {"k", "t", "s", "m", "n", "r", "l", "v", "b", "d", "g", "h", "p", "f", "th", "st", "br", "tr"};
const char* const kHumanNuclei[] = {"a", "e", "i", "o", "u", "ae", "ei", "ou", "ia"};
const char* const kHumanCodas[] = {"n", "s", "r", "l", "m", "th", "rn", "ns"};

const char* const kKethOnsets[] = {"k", "kh", "ts", "z", "sk", "gr", "dr", "vr", "th"};
const char* const kKethNuclei[] = {"e", "u", "o", "ue", "ai", "eo"};
const char* const kKethCodas[] = {"th", "sk", "rk", "z", "n"};

const char* const kAvariOnsets[] = {"a", "s", "v", "y", "l", "shi", "ri", "tha", "ny"};
const char* const kAvariNuclei[] = {"i", "a", "ia", "ei", "ii", "ae"};
const char* const kAvariCodas[] = {"l", "n", "r", "sh"};

const char* const kThulnOnsets[] = {"th", "gr", "mor", "dol", "kh", "sul", "vrak"};
const char* const kThulnNuclei[] = {"o", "u", "au", "uo", "a"};
const char* const kThulnCodas[] = {"n", "r", "m", "th", "lk"};

const char* const kSorvekOnsets[] = {"s", "k", "dr", "vr", "gr", "tz", "kr"};
const char* const kSorvekNuclei[] = {"o", "e", "a", "ov", "ek"};
const char* const kSorvekCodas[] = {"k", "v", "r", "sk", "n"};

const char* const kMycelOnsets[] = {"m", "sh", "l", "ph", "wh", "sy"};
const char* const kMycelNuclei[] = {"y", "e", "oo", "ee", "ei"};
const char* const kMycelCodas[] = {"l", "m", "sh", "n"};

const char* const kVesskOnsets[] = {"v", "ss", "th", "shl", "kl", "nn"};
const char* const kVesskNuclei[] = {"e", "i", "ee", "ia", "ae"};
const char* const kVesskCodas[] = {"ss", "sk", "th", "l"};

const char* const kDraalOnsets[] = {"dr", "br", "vaa", "kaa", "n", "gh"};
const char* const kDraalNuclei[] = {"aa", "a", "o", "oa"};
const char* const kDraalCodas[] = {"l", "r", "n", "gh"};

const char* const kIlunOnsets[] = {"i", "l", "n", "s", "ver", "syn", "ax"};
const char* const kIlunNuclei[] = {"u", "i", "e", "ui", "ia"};
const char* const kIlunCodas[] = {"n", "x", "s", "l"};

const char* const kOkraOnsets[] = {"o", "kr", "tk", "zz", "chk", "rr"};
const char* const kOkraNuclei[] = {"a", "i", "u", "ai"};
const char* const kOkraCodas[] = {"k", "t", "kt", "rr"};

const char* const kNebrisOnsets[] = {"n", "hs", "wh", "vh", "fl", "s"};
const char* const kNebrisNuclei[] = {"e", "ae", "ii", "ou", "ea"};
const char* const kNebrisCodas[] = {"s", "sh", "h", "n"};

const char* const kTarshOnsets[] = {"t", "sh", "r", "kv", "j", "bl"};
const char* const kTarshNuclei[] = {"a", "o", "u", "ar", "or"};
const char* const kTarshCodas[] = {"sh", "rt", "k", "n"};

const char* const kPrecursorOnsets[] = {"ael", "yth", "ora", "sel", "vaen", "thal", "iri"};
const char* const kPrecursorNuclei[] = {"ae", "ei", "io", "ua", "y"};
const char* const kPrecursorCodas[] = {"th", "l", "n", "r", "s"};

template <usize OnsetCount, usize NucleusCount, usize CodaCount>
Phonotactics makeSet(const char* const (&onsets)[OnsetCount], const char* const (&nuclei)[NucleusCount],
                     const char* const (&codas)[CodaCount], f32 codaProbability) {
    Phonotactics set;
    set.onsets = onsets;
    set.onsetCount = static_cast<u32>(OnsetCount);
    set.nuclei = nuclei;
    set.nucleusCount = static_cast<u32>(NucleusCount);
    set.codas = codas;
    set.codaCount = static_cast<u32>(CodaCount);
    set.codaProbability = codaProbability;
    return set;
}

Phonotactics phonotacticsFor(NameCulture culture) {
    switch (culture) {
        case NameCulture::Keth: return makeSet(kKethOnsets, kKethNuclei, kKethCodas, 0.62f);
        case NameCulture::Avari: return makeSet(kAvariOnsets, kAvariNuclei, kAvariCodas, 0.34f);
        case NameCulture::Thuln: return makeSet(kThulnOnsets, kThulnNuclei, kThulnCodas, 0.70f);
        case NameCulture::Sorvek: return makeSet(kSorvekOnsets, kSorvekNuclei, kSorvekCodas, 0.74f);
        case NameCulture::Mycel: return makeSet(kMycelOnsets, kMycelNuclei, kMycelCodas, 0.28f);
        case NameCulture::Vessk: return makeSet(kVesskOnsets, kVesskNuclei, kVesskCodas, 0.55f);
        case NameCulture::Draal: return makeSet(kDraalOnsets, kDraalNuclei, kDraalCodas, 0.48f);
        case NameCulture::Ilun: return makeSet(kIlunOnsets, kIlunNuclei, kIlunCodas, 0.52f);
        case NameCulture::Okra: return makeSet(kOkraOnsets, kOkraNuclei, kOkraCodas, 0.80f);
        case NameCulture::Nebris: return makeSet(kNebrisOnsets, kNebrisNuclei, kNebrisCodas, 0.30f);
        case NameCulture::Tarsh: return makeSet(kTarshOnsets, kTarshNuclei, kTarshCodas, 0.58f);
        case NameCulture::Precursor: return makeSet(kPrecursorOnsets, kPrecursorNuclei, kPrecursorCodas, 0.40f);
        default: return makeSet(kHumanOnsets, kHumanNuclei, kHumanCodas, 0.45f);
    }
}

}

std::string generateName(u64 seed, NameCulture culture, u32 minimumSyllables, u32 maximumSyllables) {
    Random random(seed);
    const Phonotactics set = phonotacticsFor(culture);
    const u32 low = minimumSyllables < 1 ? 1 : minimumSyllables;
    const u32 high = maximumSyllables < low ? low : maximumSyllables;
    const u32 syllables = static_cast<u32>(random.rangeInt(static_cast<i32>(low), static_cast<i32>(high) + 1));

    std::string name;
    for (u32 index = 0; index < syllables; ++index) {
        name += set.onsets[random.nextUnsigned32() % set.onsetCount];
        name += set.nuclei[random.nextUnsigned32() % set.nucleusCount];
        const bool lastSyllable = index + 1 == syllables;
        if (random.chance(lastSyllable ? set.codaProbability : set.codaProbability * 0.45f)) {
            name += set.codas[random.nextUnsigned32() % set.codaCount];
        }
    }
    if (!name.empty() && name[0] >= 'a' && name[0] <= 'z') {
        name[0] = static_cast<char>(name[0] - 'a' + 'A');
    }
    return name;
}

std::string generateStarDesignation(u64 seed) {
    Random random(seed ^ 0xA5A5A5A5A5A5A5A5ull);
    std::string name = generateName(seed, NameCulture::Human, 2, 3);
    if (random.chance(0.34f)) {
        char suffix[16];
        std::snprintf(suffix, sizeof(suffix), "-%u", static_cast<u32>(random.rangeInt(11, 9999)));
        name += suffix;
    }
    return name;
}

std::string generatePlanetDesignation(const std::string& starName, u32 planetIndex) {
    static const char* const romanNumerals[13] = {"I", "II", "III", "IV", "V", "VI", "VII",
                                                  "VIII", "IX", "X", "XI", "XII", "XIII"};
    const u32 clamped = planetIndex < 13 ? planetIndex : 12;
    return starName + " " + romanNumerals[clamped];
}

std::string generateMoonDesignation(const std::string& planetName, u32 moonIndex) {
    static const char* const letters = "abcdefghijkl";
    const u32 clamped = moonIndex < 12 ? moonIndex : 11;
    return planetName + " " + std::string(1, letters[clamped]);
}

const char* cultureName(NameCulture culture) {
    switch (culture) {
        case NameCulture::Keth: return "KETH";
        case NameCulture::Avari: return "AVARI";
        case NameCulture::Thuln: return "THULN";
        case NameCulture::Sorvek: return "SORVEK";
        case NameCulture::Mycel: return "MYCEL";
        case NameCulture::Vessk: return "VESSK";
        case NameCulture::Draal: return "DRAAL";
        case NameCulture::Ilun: return "ILUN";
        case NameCulture::Okra: return "OKRA";
        case NameCulture::Nebris: return "NEBRIS";
        case NameCulture::Tarsh: return "TARSH";
        case NameCulture::Precursor: return "VORLAEUFER";
        default: return "MENSCH";
    }
}

}
