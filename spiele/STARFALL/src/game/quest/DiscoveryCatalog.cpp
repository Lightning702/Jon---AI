#include "DiscoveryCatalog.hpp"

#include "../../engine/math/Random.hpp"

namespace sf {
namespace {

const char* const kCreatureSuffixes[] = {"idae", "opsis", "ranx", "veth", "ulon", "arix", "thys", "omor"};
const char* const kPlantSuffixes[] = {"flora", "spina", "lumen", "radix", "vitis", "morphae"};

}

bool DiscoveryCatalog::record(DiscoveryKind kind, u64 key, const std::string& generatedName,
                              const std::string& systemName, const std::string& detail, f64 rewardCredits) {
    if (known(key)) return false;
    DiscoveryEntry entry;
    entry.key = key;
    entry.kind = kind;
    entry.generatedName = generatedName;
    entry.systemName = systemName;
    entry.detail = detail;
    entry.rewardCredits = rewardCredits;
    records.push_back(entry);
    return true;
}

bool DiscoveryCatalog::rename(u64 key, const std::string& customName) {
    for (DiscoveryEntry& entry : records) {
        if (entry.key != key) continue;
        if (entry.uploaded) return false;
        entry.customName = customName;
        return true;
    }
    return false;
}

bool DiscoveryCatalog::upload(u64 key, f64& creditsAwarded) {
    creditsAwarded = 0.0;
    for (DiscoveryEntry& entry : records) {
        if (entry.key != key || entry.uploaded) continue;
        entry.uploaded = true;
        creditsAwarded = entry.rewardCredits;
        return true;
    }
    return false;
}

f64 DiscoveryCatalog::uploadAll() {
    f64 total = 0.0;
    for (DiscoveryEntry& entry : records) {
        if (entry.uploaded) continue;
        entry.uploaded = true;
        total += entry.rewardCredits;
    }
    return total;
}

bool DiscoveryCatalog::known(u64 key) const {
    return find(key) != nullptr;
}

const DiscoveryEntry* DiscoveryCatalog::find(u64 key) const {
    for (const DiscoveryEntry& entry : records) {
        if (entry.key == key) return &entry;
    }
    return nullptr;
}

u32 DiscoveryCatalog::countOfKind(DiscoveryKind kind) const {
    u32 total = 0;
    for (const DiscoveryEntry& entry : records) {
        if (entry.kind == kind) ++total;
    }
    return total;
}

u32 DiscoveryCatalog::uploadedCount() const {
    u32 total = 0;
    for (const DiscoveryEntry& entry : records) {
        if (entry.uploaded) ++total;
    }
    return total;
}

f64 DiscoveryCatalog::pendingRewardValue() const {
    f64 total = 0.0;
    for (const DiscoveryEntry& entry : records) {
        if (!entry.uploaded) total += entry.rewardCredits;
    }
    return total;
}

const char* DiscoveryCatalog::kindName(DiscoveryKind kind) {
    switch (kind) {
        case DiscoveryKind::System: return "SYSTEM";
        case DiscoveryKind::Planet: return "PLANET";
        case DiscoveryKind::Moon: return "MOND";
        case DiscoveryKind::Flora: return "FLORA";
        case DiscoveryKind::Fauna: return "FAUNA";
        case DiscoveryKind::Mineral: return "MINERAL";
        case DiscoveryKind::Anomaly: return "ANOMALIE";
        case DiscoveryKind::Station: return "STATION";
        default: return "";
    }
}

std::string DiscoveryCatalog::generateCreatureName(u64 seed, u32 speciesIndex) {
    Random random(hashCombine(seed, speciesIndex + 0x4641554Eull));
    std::string stem = generateName(hashCombine(seed, speciesIndex), NameCulture::Thuln, 2, 3);
    stem += kCreatureSuffixes[random.nextUnsigned32() % 8];
    return stem;
}

std::string DiscoveryCatalog::generatePlantName(u64 seed, u32 kind) {
    Random random(hashCombine(seed, kind + 0x464C4F52ull));
    std::string stem = generateName(hashCombine(seed, kind + 91u), NameCulture::Mycel, 2, 3);
    stem += kPlantSuffixes[random.nextUnsigned32() % 6];
    return stem;
}

}
