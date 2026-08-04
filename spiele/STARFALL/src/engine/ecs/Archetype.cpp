#include "Archetype.hpp"

#include <algorithm>

namespace sf {

void Archetype::configure(const std::vector<ComponentId>& types) {
    typeList = types;
    std::sort(typeList.begin(), typeList.end());
    typeList.erase(std::unique(typeList.begin(), typeList.end()), typeList.end());
    columns.clear();
    columns.reserve(typeList.size());
    signatureBits.resize(kMaximumComponentTypes);
    for (ComponentId type : typeList) {
        columns.emplace_back(type);
        signatureBits.set(type);
    }
}

bool Archetype::matchesSignature(const BitSet& required, const BitSet& excluded) const {
    if (!signatureBits.containsAll(required)) return false;
    if (excluded.anySet() && signatureBits.intersects(excluded)) return false;
    return true;
}

usize Archetype::appendEntity(Entity entity) {
    const usize row = entities.size();
    entities.push_back(entity);
    for (ComponentColumn& column : columns) column.appendDefault();
    return row;
}

Entity Archetype::removeRow(usize row, Entity& movedEntityOut) {
    movedEntityOut = Entity::invalid();
    if (row >= entities.size()) return Entity::invalid();
    const Entity removed = entities[row];
    const usize lastRow = entities.size() - 1;
    for (ComponentColumn& column : columns) column.removeAtSwap(row);
    if (row != lastRow) {
        entities[row] = entities[lastRow];
        movedEntityOut = entities[row];
    }
    entities.pop_back();
    return removed;
}

ComponentColumn* Archetype::column(ComponentId type) {
    for (ComponentColumn& candidate : columns) {
        if (candidate.type() == type) return &candidate;
    }
    return nullptr;
}

const ComponentColumn* Archetype::column(ComponentId type) const {
    for (const ComponentColumn& candidate : columns) {
        if (candidate.type() == type) return &candidate;
    }
    return nullptr;
}

void* Archetype::componentPointer(ComponentId type, usize row) {
    ComponentColumn* target = column(type);
    return target ? target->elementAt(row) : nullptr;
}

}
