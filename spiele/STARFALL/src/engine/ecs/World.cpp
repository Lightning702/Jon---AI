#include "World.hpp"

#include <algorithm>

namespace sf {

ComponentRegistry& ComponentRegistry::instance() {
    static ComponentRegistry registry;
    return registry;
}

ComponentId ComponentRegistry::registerType(const ComponentTypeInfo& info) {
    SF_ASSERT_MSG(count < kMaximumComponentTypes, "Zu viele Komponententypen registriert");
    const ComponentId assigned = count++;
    types[assigned] = info;
    types[assigned].id = assigned;
    return assigned;
}

const ComponentTypeInfo& ComponentRegistry::info(ComponentId id) const {
    SF_ASSERT_MSG(id < count, "Unbekannter Komponententyp");
    return types[id];
}

World::World() {
    archetypes.push_back(std::make_unique<Archetype>());
    archetypes.back()->configure(std::vector<ComponentId>());
}

Entity World::createEntity() {
    u32 index;
    if (!freeIndices.empty()) {
        index = freeIndices.back();
        freeIndices.pop_back();
    } else {
        index = static_cast<u32>(records.size());
        records.push_back(EntityRecord());
    }
    EntityRecord& entry = records[index];
    entry.alive = true;
    entry.archetypeIndex = 0;

    Entity entity;
    entity.index = index;
    entity.generation = entry.generation;
    entry.row = static_cast<u32>(archetypes[0]->appendEntity(entity));
    ++liveEntities;
    return entity;
}

void World::destroyEntity(Entity entity) {
    EntityRecord* entry = record(entity);
    if (!entry) return;
    Archetype& archetype = *archetypes[entry->archetypeIndex];
    Entity moved = Entity::invalid();
    archetype.removeRow(entry->row, moved);
    if (moved.valid()) {
        EntityRecord* movedEntry = record(moved);
        if (movedEntry) movedEntry->row = entry->row;
    }
    entry->alive = false;
    entry->generation += 1;
    if (entry->generation == 0) entry->generation = 1;
    entry->archetypeIndex = kInvalidIndex32;
    entry->row = kInvalidIndex32;
    freeIndices.push_back(entity.index);
    if (liveEntities > 0) --liveEntities;
}

bool World::alive(Entity entity) const {
    return record(entity) != nullptr;
}

World::EntityRecord* World::record(Entity entity) {
    if (!entity.valid() || entity.index >= records.size()) return nullptr;
    EntityRecord& entry = records[entity.index];
    if (!entry.alive || entry.generation != entity.generation) return nullptr;
    return &entry;
}

const World::EntityRecord* World::record(Entity entity) const {
    return const_cast<World*>(this)->record(entity);
}

u32 World::findOrCreateArchetype(const std::vector<ComponentId>& types) {
    std::vector<ComponentId> sorted = types;
    std::sort(sorted.begin(), sorted.end());
    sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());

    for (usize index = 0; index < archetypes.size(); ++index) {
        if (archetypes[index]->componentTypes() == sorted) return static_cast<u32>(index);
    }
    archetypes.push_back(std::make_unique<Archetype>());
    archetypes.back()->configure(sorted);
    return static_cast<u32>(archetypes.size() - 1);
}

void World::moveEntity(Entity entity, u32 targetArchetype) {
    EntityRecord* entry = record(entity);
    if (!entry || entry->archetypeIndex == targetArchetype) return;

    Archetype& source = *archetypes[entry->archetypeIndex];
    Archetype& target = *archetypes[targetArchetype];
    const usize newRow = target.appendEntity(entity);

    for (ComponentId type : source.componentTypes()) {
        if (!target.hasComponent(type)) continue;
        const ComponentTypeInfo& typeInfo = ComponentRegistry::instance().info(type);
        void* destination = target.componentPointer(type, newRow);
        void* origin = source.componentPointer(type, entry->row);
        if (destination && origin) {
            typeInfo.destruct(destination);
            typeInfo.moveConstruct(destination, origin);
            typeInfo.defaultConstruct(origin);
        }
    }

    Entity moved = Entity::invalid();
    source.removeRow(entry->row, moved);
    if (moved.valid()) {
        EntityRecord* movedEntry = record(moved);
        if (movedEntry) movedEntry->row = entry->row;
    }

    entry->archetypeIndex = targetArchetype;
    entry->row = static_cast<u32>(newRow);
}

void* World::addComponentRaw(Entity entity, ComponentId type) {
    EntityRecord* entry = record(entity);
    if (!entry) return nullptr;
    Archetype& current = *archetypes[entry->archetypeIndex];
    if (!current.hasComponent(type)) {
        std::vector<ComponentId> types = current.componentTypes();
        types.push_back(type);
        const u32 target = findOrCreateArchetype(types);
        moveEntity(entity, target);
        entry = record(entity);
        if (!entry) return nullptr;
    }
    return archetypes[entry->archetypeIndex]->componentPointer(type, entry->row);
}

void World::removeComponentRaw(Entity entity, ComponentId type) {
    EntityRecord* entry = record(entity);
    if (!entry) return;
    Archetype& current = *archetypes[entry->archetypeIndex];
    if (!current.hasComponent(type)) return;
    std::vector<ComponentId> types;
    for (ComponentId existing : current.componentTypes()) {
        if (existing != type) types.push_back(existing);
    }
    moveEntity(entity, findOrCreateArchetype(types));
}

void* World::componentRaw(Entity entity, ComponentId type) {
    EntityRecord* entry = record(entity);
    if (!entry) return nullptr;
    return archetypes[entry->archetypeIndex]->componentPointer(type, entry->row);
}

void World::clear() {
    records.clear();
    freeIndices.clear();
    archetypes.clear();
    liveEntities = 0;
    archetypes.push_back(std::make_unique<Archetype>());
    archetypes.back()->configure(std::vector<ComponentId>());
}

}
