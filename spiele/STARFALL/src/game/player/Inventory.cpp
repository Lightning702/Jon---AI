#include "Inventory.hpp"

#include "../../engine/math/Scalar.hpp"

namespace sf {

void Inventory::configure(InventoryKind kind, u32 slotCountValue, const std::string& label) {
    inventoryKind = kind;
    displayLabel = label;
    slots.assign(slotCountValue, ItemStack());
}

bool Inventory::expand(u32 additionalSlots, u32 maximumSlots) {
    if (slots.size() >= maximumSlots) return false;
    const u32 target = minValue(static_cast<u32>(slots.size()) + additionalSlots, maximumSlots);
    slots.resize(target);
    return true;
}

u32 Inventory::add(ItemId id, u32 amount) {
    if (id == ItemId::None || amount == 0) return 0;
    const ItemDefinition& definition = ItemDatabase::instance().definition(id);
    u32 remaining = amount;

    for (ItemStack& stack : slots) {
        if (remaining == 0) break;
        if (stack.id != id || stack.count >= definition.stackSize) continue;
        const u32 space = definition.stackSize - stack.count;
        const u32 transfer = minValue(space, remaining);
        stack.count += transfer;
        remaining -= transfer;
    }

    for (ItemStack& stack : slots) {
        if (remaining == 0) break;
        if (!stack.empty()) continue;
        const u32 transfer = minValue(definition.stackSize, remaining);
        stack.id = id;
        stack.count = transfer;
        remaining -= transfer;
    }
    return amount - remaining;
}

u32 Inventory::remove(ItemId id, u32 amount) {
    if (id == ItemId::None || amount == 0) return 0;
    u32 remaining = amount;
    for (usize index = slots.size(); index > 0; --index) {
        ItemStack& stack = slots[index - 1];
        if (stack.id != id || stack.count == 0) continue;
        const u32 transfer = minValue(stack.count, remaining);
        stack.count -= transfer;
        remaining -= transfer;
        if (stack.count == 0) stack.clear();
        if (remaining == 0) break;
    }
    return amount - remaining;
}

u32 Inventory::count(ItemId id) const {
    u32 total = 0;
    for (const ItemStack& stack : slots) {
        if (stack.id == id) total += stack.count;
    }
    return total;
}

bool Inventory::moveSlot(u32 fromIndex, Inventory& target, u32 toIndex) {
    if (fromIndex >= slots.size() || toIndex >= target.slots.size()) return false;
    ItemStack& source = slots[fromIndex];
    if (source.empty()) return false;

    ItemStack& destination = target.slots[toIndex];
    if (destination.empty()) {
        destination = source;
        source.clear();
        return true;
    }
    if (destination.id == source.id) {
        const ItemDefinition& definition = ItemDatabase::instance().definition(source.id);
        const u32 space = destination.count >= definition.stackSize ? 0 : definition.stackSize - destination.count;
        const u32 transfer = minValue(space, source.count);
        destination.count += transfer;
        source.count -= transfer;
        if (source.count == 0) source.clear();
        return transfer > 0;
    }
    const ItemStack swap = destination;
    destination = source;
    source = swap;
    return true;
}

void Inventory::clear() {
    for (ItemStack& stack : slots) stack.clear();
}

u32 Inventory::freeSlots() const {
    u32 total = 0;
    for (const ItemStack& stack : slots) {
        if (stack.empty()) ++total;
    }
    return total;
}

u32 Inventory::acceptableAmount(ItemId id) const {
    if (id == ItemId::None) return 0;
    const ItemDefinition& definition = ItemDatabase::instance().definition(id);
    u32 total = 0;
    for (const ItemStack& stack : slots) {
        if (stack.empty()) total += definition.stackSize;
        else if (stack.id == id && stack.count < definition.stackSize) total += definition.stackSize - stack.count;
    }
    return total;
}

f64 Inventory::totalValue() const {
    f64 total = 0.0;
    for (const ItemStack& stack : slots) {
        if (!stack.empty()) total += stack.value();
    }
    return total;
}

f64 Inventory::totalMassKilograms() const {
    f64 total = 0.0;
    for (const ItemStack& stack : slots) {
        if (!stack.empty()) total += stack.massKilograms();
    }
    return total;
}

f64 Inventory::fillFraction() const {
    if (slots.empty()) return 0.0;
    return 1.0 - static_cast<f64>(freeSlots()) / static_cast<f64>(slots.size());
}

std::vector<ItemId> Inventory::distinctItems() const {
    std::vector<ItemId> result;
    for (const ItemStack& stack : slots) {
        if (stack.empty()) continue;
        bool known = false;
        for (ItemId existing : result) {
            if (existing == stack.id) known = true;
        }
        if (!known) result.push_back(stack.id);
    }
    return result;
}

}
