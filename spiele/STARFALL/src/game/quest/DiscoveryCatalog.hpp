#pragma once

#include "../../engine/core/Types.hpp"
#include "../universe/NameGenerator.hpp"

#include <string>
#include <vector>

namespace sf {

enum class DiscoveryKind : u32 {
    System = 0,
    Planet,
    Moon,
    Flora,
    Fauna,
    Mineral,
    Anomaly,
    Station,
    Count
};

struct DiscoveryEntry {
    u64 key = 0;
    DiscoveryKind kind = DiscoveryKind::Planet;
    std::string generatedName;
    std::string customName;
    std::string systemName;
    std::string detail;
    f64 rewardCredits = 0.0;
    bool uploaded = false;

    const std::string& displayName() const { return customName.empty() ? generatedName : customName; }
};

class DiscoveryCatalog {
public:
    bool record(DiscoveryKind kind, u64 key, const std::string& generatedName, const std::string& systemName,
                const std::string& detail, f64 rewardCredits);
    bool rename(u64 key, const std::string& customName);
    bool upload(u64 key, f64& creditsAwarded);
    f64 uploadAll();

    bool known(u64 key) const;
    const DiscoveryEntry* find(u64 key) const;
    const std::vector<DiscoveryEntry>& entries() const { return records; }
    u32 countOfKind(DiscoveryKind kind) const;
    u32 uploadedCount() const;
    f64 pendingRewardValue() const;

    u32 speciesCatalogued() const { return countOfKind(DiscoveryKind::Fauna) + countOfKind(DiscoveryKind::Flora); }
    u32 planetsMapped() const { return countOfKind(DiscoveryKind::Planet) + countOfKind(DiscoveryKind::Moon); }
    u32 systemsVisited() const { return countOfKind(DiscoveryKind::System); }

    static const char* kindName(DiscoveryKind kind);
    static std::string generateCreatureName(u64 seed, u32 speciesIndex);
    static std::string generatePlantName(u64 seed, u32 kind);

private:
    std::vector<DiscoveryEntry> records;
};

}
