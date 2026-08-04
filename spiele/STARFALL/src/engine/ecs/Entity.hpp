#pragma once

#include "../core/Types.hpp"

#include <new>

namespace sf {

struct Entity {
    u32 index = kInvalidIndex32;
    u32 generation = 0;

    bool valid() const { return index != kInvalidIndex32; }
    bool operator==(const Entity& other) const {
        return index == other.index && generation == other.generation;
    }
    bool operator!=(const Entity& other) const { return !(*this == other); }
    u64 packed() const { return (static_cast<u64>(generation) << 32) | index; }

    static Entity invalid() { return Entity(); }
};

using ComponentId = u32;
constexpr ComponentId kMaximumComponentTypes = 128;

struct ComponentTypeInfo {
    ComponentId id = kInvalidIndex32;
    usize size = 0;
    usize alignment = 0;
    const char* name = "";
    void (*defaultConstruct)(void*) = nullptr;
    void (*destruct)(void*) = nullptr;
    void (*moveConstruct)(void*, void*) = nullptr;
};

class ComponentRegistry {
public:
    static ComponentRegistry& instance();

    ComponentId registerType(const ComponentTypeInfo& info);
    const ComponentTypeInfo& info(ComponentId id) const;
    u32 registeredCount() const { return count; }

private:
    ComponentTypeInfo types[kMaximumComponentTypes];
    u32 count = 0;
};

template <typename T>
struct ComponentTraits {
    static ComponentId id() {
        static const ComponentId value = registerSelf();
        return value;
    }

private:
    static ComponentId registerSelf() {
        ComponentTypeInfo info;
        info.size = sizeof(T);
        info.alignment = alignof(T);
        info.name = "component";
        info.defaultConstruct = [](void* target) { new (target) T(); };
        info.destruct = [](void* target) { static_cast<T*>(target)->~T(); };
        info.moveConstruct = [](void* target, void* source) {
            new (target) T(static_cast<T&&>(*static_cast<T*>(source)));
            static_cast<T*>(source)->~T();
        };
        return ComponentRegistry::instance().registerType(info);
    }
};

}
