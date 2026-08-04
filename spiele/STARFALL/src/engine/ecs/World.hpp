#pragma once

#include "Archetype.hpp"

#include <memory>
#include <vector>

namespace sf {

class World {
public:
    World();

    Entity createEntity();
    void destroyEntity(Entity entity);
    bool alive(Entity entity) const;
    usize entityCount() const { return liveEntities; }

    template <typename T>
    T& addComponent(Entity entity, const T& value) {
        void* storage = addComponentRaw(entity, ComponentTraits<T>::id());
        SF_ASSERT_MSG(storage != nullptr, "Komponente konnte nicht angelegt werden");
        *static_cast<T*>(storage) = value;
        return *static_cast<T*>(storage);
    }

    template <typename T>
    void removeComponent(Entity entity) {
        removeComponentRaw(entity, ComponentTraits<T>::id());
    }

    template <typename T>
    T* component(Entity entity) {
        return static_cast<T*>(componentRaw(entity, ComponentTraits<T>::id()));
    }

    template <typename T>
    const T* component(Entity entity) const {
        return static_cast<const T*>(const_cast<World*>(this)->componentRaw(entity, ComponentTraits<T>::id()));
    }

    template <typename T>
    bool hasComponent(Entity entity) const {
        return const_cast<World*>(this)->componentRaw(entity, ComponentTraits<T>::id()) != nullptr;
    }

    usize archetypeCount() const { return archetypes.size(); }
    Archetype& archetypeAt(usize index) { return *archetypes[index]; }
    const Archetype& archetypeAt(usize index) const { return *archetypes[index]; }

    void clear();

private:
    struct EntityRecord {
        u32 generation = 1;
        bool alive = false;
        u32 archetypeIndex = kInvalidIndex32;
        u32 row = kInvalidIndex32;
    };

    void* addComponentRaw(Entity entity, ComponentId type);
    void removeComponentRaw(Entity entity, ComponentId type);
    void* componentRaw(Entity entity, ComponentId type);
    u32 findOrCreateArchetype(const std::vector<ComponentId>& types);
    void moveEntity(Entity entity, u32 targetArchetype);
    EntityRecord* record(Entity entity);
    const EntityRecord* record(Entity entity) const;

    std::vector<EntityRecord> records;
    std::vector<u32> freeIndices;
    std::vector<std::unique_ptr<Archetype>> archetypes;
    usize liveEntities = 0;
};

}
