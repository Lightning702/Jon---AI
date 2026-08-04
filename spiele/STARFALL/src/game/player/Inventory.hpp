#pragma once

#include "../crafting/ItemDatabase.hpp"

#include <string>
#include <vector>

namespace sf {

enum class InventoryKind : u32 {
    Suit = 0,
    Ship,
    Freighter,
    Container,
    Count
};

class Inventory {
public:
    void configure(InventoryKind kind, u32 slotCount, const std::string& label);

    u32 slotCount() const { return static_cast<u32>(slots.size()); }
    const ItemStack& slot(u32 index) const { return slots[index]; }
    ItemStack& mutableSlot(u32 index) { return slots[index]; }
    InventoryKind kind() const { return inventoryKind; }
    const std::string& label() const { return displayLabel; }

    bool expand(u32 additionalSlots, u32 maximumSlots);
    u32 add(ItemId id, u32 amount);
    u32 remove(ItemId id, u32 amount);
    u32 count(ItemId id) const;
    bool has(ItemId id, u32 amount) const { return count(id) >= amount; }
    bool moveSlot(u32 fromIndex, Inventory& target, u32 toIndex);
    void clear();

    u32 freeSlots() const;
    u32 acceptableAmount(ItemId id) const;
    f64 totalValue() const;
    f64 totalMassKilograms() const;
    f64 fillFraction() const;
    std::vector<ItemId> distinctItems() const;

private:
    std::vector<ItemStack> slots;
    InventoryKind inventoryKind = InventoryKind::Suit;
    std::string displayLabel = "ANZUG";
};

}
