#include "TradeMarket.hpp"

#include "../../engine/math/Random.hpp"
#include "../../engine/math/Scalar.hpp"

namespace sf {
namespace {

constexpr f64 kBuyMargin = 1.18;
constexpr f64 kSellMargin = 0.82;

}

f64 MarketEntry::buyPrice() const {
    const f64 base = ItemDatabase::instance().definition(id).baseValue;
    return base * priceMultiplier * kBuyMargin * (1.0 + marketImpact);
}

f64 MarketEntry::sellPrice() const {
    const f64 base = ItemDatabase::instance().definition(id).baseValue;
    return base * priceMultiplier * kSellMargin * (1.0 + marketImpact);
}

void TradeMarket::configure(u64 seed, const std::string& stationName, NameCulture owner) {
    marketSeed = seed;
    displayName = stationName;
    culture = owner;
    reputation = 0.0;

    Random random(seed);
    focus = static_cast<MarketSpecialisation>(random.rangeInt(0, static_cast<i32>(MarketSpecialisation::Count)));

    offers.clear();
    const ItemDatabase& database = ItemDatabase::instance();
    for (const ItemDefinition& definition : database.all()) {
        if (definition.id == ItemId::None) continue;
        if (definition.category == ItemCategory::Exotic && !random.chance(0.25f)) continue;

        MarketEntry entry;
        entry.id = definition.id;
        entry.stock = random.rangeDouble(0.0, 600.0);
        entry.demand = random.rangeDouble(0.4, 1.6);
        entry.priceMultiplier = random.rangeDouble(0.72, 1.38);

        switch (focus) {
            case MarketSpecialisation::Mining:
                if (definition.category == ItemCategory::Element) {
                    entry.priceMultiplier *= 0.74;
                    entry.stock *= 2.2;
                } else if (definition.category == ItemCategory::Component) {
                    entry.priceMultiplier *= 1.22;
                }
                break;
            case MarketSpecialisation::Manufacturing:
                if (definition.category == ItemCategory::Component) {
                    entry.priceMultiplier *= 0.76;
                    entry.stock *= 1.8;
                } else if (definition.category == ItemCategory::Element) {
                    entry.priceMultiplier *= 1.24;
                }
                break;
            case MarketSpecialisation::Agriculture:
                if (definition.category == ItemCategory::Consumable) {
                    entry.priceMultiplier *= 0.70;
                    entry.stock *= 2.4;
                }
                break;
            case MarketSpecialisation::Research:
                if (definition.category == ItemCategory::Technology ||
                    definition.category == ItemCategory::Exotic) {
                    entry.priceMultiplier *= 1.34;
                    entry.demand *= 1.5;
                }
                break;
            default:
                break;
        }
        offers.push_back(entry);
    }
}

void TradeMarket::step(f64 stepSeconds) {
    for (MarketEntry& entry : offers) {
        entry.marketImpact = exponentialApproach(entry.marketImpact, 0.0, 0.06, stepSeconds);
        const f64 production = entry.demand * 0.6;
        entry.stock = clampValue(entry.stock + (production - entry.stock * 0.01) * stepSeconds * 0.02, 0.0, 4000.0);
    }
}

const MarketEntry* TradeMarket::find(ItemId id) const {
    for (const MarketEntry& entry : offers) {
        if (entry.id == id) return &entry;
    }
    return nullptr;
}

MarketEntry* TradeMarket::mutableFind(ItemId id) {
    for (MarketEntry& entry : offers) {
        if (entry.id == id) return &entry;
    }
    return nullptr;
}

f64 TradeMarket::quoteBuy(ItemId id, u32 amount) const {
    const MarketEntry* entry = find(id);
    if (!entry) return 0.0;
    return entry->buyPrice() * static_cast<f64>(amount) * (1.0 - clampValue(reputation, 0.0, 0.25));
}

f64 TradeMarket::quoteSell(ItemId id, u32 amount) const {
    const MarketEntry* entry = find(id);
    if (!entry) return 0.0;
    return entry->sellPrice() * static_cast<f64>(amount) * (1.0 + clampValue(reputation, 0.0, 0.25));
}

bool TradeMarket::buy(ItemId id, u32 amount, Inventory& inventory, f64& creditsAvailable) {
    MarketEntry* entry = mutableFind(id);
    if (!entry || amount == 0) return false;
    if (entry->stock < static_cast<f64>(amount)) return false;

    const f64 cost = quoteBuy(id, amount);
    if (creditsAvailable < cost) return false;
    if (inventory.acceptableAmount(id) < amount) return false;

    creditsAvailable -= cost;
    inventory.add(id, amount);
    entry->stock -= static_cast<f64>(amount);
    entry->marketImpact = clampValue(entry->marketImpact + static_cast<f64>(amount) * 0.0016, -0.6, 1.4);
    adjustReputation(cost * 1.0e-6);
    return true;
}

bool TradeMarket::sell(ItemId id, u32 amount, Inventory& inventory, f64& creditsAvailable) {
    MarketEntry* entry = mutableFind(id);
    if (!entry || amount == 0) return false;
    if (inventory.count(id) < amount) return false;

    const f64 revenue = quoteSell(id, amount);
    inventory.remove(id, amount);
    creditsAvailable += revenue;
    entry->stock += static_cast<f64>(amount);
    entry->marketImpact = clampValue(entry->marketImpact - static_cast<f64>(amount) * 0.0014, -0.6, 1.4);
    adjustReputation(revenue * 1.0e-6);
    return true;
}

void TradeMarket::adjustReputation(f64 delta) {
    reputation = clampValue(reputation + delta, -0.4, 0.4);
}

const char* TradeMarket::specialisationName(MarketSpecialisation value) {
    switch (value) {
        case MarketSpecialisation::Mining: return "BERGBAU";
        case MarketSpecialisation::Manufacturing: return "FERTIGUNG";
        case MarketSpecialisation::Agriculture: return "LANDWIRTSCHAFT";
        case MarketSpecialisation::Research: return "FORSCHUNG";
        case MarketSpecialisation::Trading: return "HANDEL";
        default: return "";
    }
}

}
