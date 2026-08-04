#pragma once

#include "World.hpp"

namespace sf {

class Query {
public:
    Query() {
        required.resize(kMaximumComponentTypes);
        excluded.resize(kMaximumComponentTypes);
    }

    template <typename T>
    Query& with() {
        required.set(ComponentTraits<T>::id());
        return *this;
    }

    template <typename T>
    Query& without() {
        excluded.set(ComponentTraits<T>::id());
        return *this;
    }

    template <typename Body>
    void each(World& world, Body body) const {
        for (usize index = 0; index < world.archetypeCount(); ++index) {
            Archetype& archetype = world.archetypeAt(index);
            if (!archetype.matchesSignature(required, excluded)) continue;
            for (usize row = 0; row < archetype.entityCount(); ++row) {
                body(archetype.entityAt(row), archetype, row);
            }
        }
    }

    template <typename T>
    static T* fetch(Archetype& archetype, usize row) {
        return static_cast<T*>(archetype.componentPointer(ComponentTraits<T>::id(), row));
    }

    usize countMatches(World& world) const {
        usize total = 0;
        for (usize index = 0; index < world.archetypeCount(); ++index) {
            Archetype& archetype = world.archetypeAt(index);
            if (archetype.matchesSignature(required, excluded)) total += archetype.entityCount();
        }
        return total;
    }

private:
    BitSet required;
    BitSet excluded;
};

}
