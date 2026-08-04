#pragma once

#include "../container/BitSet.hpp"
#include "ComponentStorage.hpp"

#include <vector>

namespace sf {

class Archetype {
public:
    Archetype() { signatureBits.resize(kMaximumComponentTypes); }

    void configure(const std::vector<ComponentId>& types);

    bool matchesSignature(const BitSet& required, const BitSet& excluded) const;
    bool hasComponent(ComponentId type) const { return signatureBits.test(type); }
    const BitSet& signature() const { return signatureBits; }
    const std::vector<ComponentId>& componentTypes() const { return typeList; }

    usize appendEntity(Entity entity);
    Entity removeRow(usize row, Entity& movedEntityOut);

    ComponentColumn* column(ComponentId type);
    const ComponentColumn* column(ComponentId type) const;

    void* componentPointer(ComponentId type, usize row);

    usize entityCount() const { return entities.size(); }
    Entity entityAt(usize row) const { return entities[row]; }

private:
    std::vector<ComponentId> typeList;
    std::vector<ComponentColumn> columns;
    std::vector<Entity> entities;
    BitSet signatureBits;
};

}
