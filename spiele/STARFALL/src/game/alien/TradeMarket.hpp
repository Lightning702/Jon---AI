#pragma once

#include "../crafting/ItemDatabase.hpp"
#include "../player/Inventory.hpp"
#include "../universe/NameGenerator.hpp"

#include <string>
#include <vector>

namespace sf {

enum class MarketSpecialisation : u32 {
    Mining = 0,
    Manufacturing,
    Agriculture,
    Research,
    Trading,
    Count
};

struct MarketEntry {
    ItemId id = ItemId::None;
    f64 stock = 0.0;
    f64 demand = 1.0;
    f64 priceMultiplier = 1.0;
    f64 marketImpact = 0.0;

    f64 buyPrice() const;
    f64 sellPrice() const;
};

class TradeMarket {
public:
    void configure(u64 seed, const std::string& stationName, NameCulture owner);
    void step(f64 stepSeconds);

    const std::string& name() const { return displayName; }
    NameCulture ownerCulture() const { return culture; }
    MarketSpecialisation specialisation() const { return focus; }
    const std::vector<MarketEntry>& entries() const { return offers; }
    const MarketEntry* find(ItemId id) const;

    bool buy(ItemId id, u32 amount, Inventory& inventory, f64& creditsAvailable);
    bool sell(ItemId id, u32 amount, Inventory& inventory, f64& creditsAvailable);
    f64 quoteBuy(ItemId id, u32 amount) const;
    f64 quoteSell(ItemId id, u32 amount) const;

    f64 reputationBonus() const { return reputation; }
    void adjustReputation(f64 delta);

    static const char* specialisationName(MarketSpecialisation value);

private:
    MarketEntry* mutableFind(ItemId id);

    std::vector<MarketEntry> offers;
    std::string displayName = "HANDELSPOSTEN";
    NameCulture culture = NameCulture::Human;
    MarketSpecialisation focus = MarketSpecialisation::Trading;
    f64 reputation = 0.0;
    u64 marketSeed = 1;
};

}
