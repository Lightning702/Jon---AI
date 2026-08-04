#pragma once

#include "../container/Array.hpp"
#include "Entity.hpp"

#include <cstdlib>
#include <cstring>

namespace sf {

class ComponentColumn {
public:
    ComponentColumn() = default;
    explicit ComponentColumn(ComponentId typeId) : componentType(typeId) {}

    ~ComponentColumn() { releaseAll(); }

    ComponentColumn(const ComponentColumn&) = delete;
    ComponentColumn& operator=(const ComponentColumn&) = delete;

    ComponentColumn(ComponentColumn&& other) noexcept
        : bytes(other.bytes), count(other.count), capacityValue(other.capacityValue),
          componentType(other.componentType) {
        other.bytes = nullptr;
        other.count = 0;
        other.capacityValue = 0;
    }

    ComponentColumn& operator=(ComponentColumn&& other) noexcept {
        if (this != &other) {
            releaseAll();
            bytes = other.bytes;
            count = other.count;
            capacityValue = other.capacityValue;
            componentType = other.componentType;
            other.bytes = nullptr;
            other.count = 0;
            other.capacityValue = 0;
        }
        return *this;
    }

    ComponentId type() const { return componentType; }
    usize size() const { return count; }
    void* elementAt(usize row) { return bytes + row * stride(); }
    const void* elementAt(usize row) const { return bytes + row * stride(); }

    usize appendDefault() {
        reserve(count + 1);
        const ComponentTypeInfo& typeInfo = ComponentRegistry::instance().info(componentType);
        typeInfo.defaultConstruct(elementAt(count));
        return count++;
    }

    void moveElementFrom(ComponentColumn& source, usize sourceRow) {
        reserve(count + 1);
        const ComponentTypeInfo& typeInfo = ComponentRegistry::instance().info(componentType);
        typeInfo.moveConstruct(elementAt(count), source.elementAt(sourceRow));
        ++count;
    }

    void removeAtSwap(usize row) {
        const ComponentTypeInfo& typeInfo = ComponentRegistry::instance().info(componentType);
        typeInfo.destruct(elementAt(row));
        const usize lastRow = count - 1;
        if (row != lastRow) {
            typeInfo.moveConstruct(elementAt(row), elementAt(lastRow));
        }
        --count;
    }

    void releaseAll() {
        if (bytes) {
            const ComponentTypeInfo& typeInfo = ComponentRegistry::instance().info(componentType);
            for (usize row = 0; row < count; ++row) typeInfo.destruct(elementAt(row));
            std::free(bytes);
        }
        bytes = nullptr;
        count = 0;
        capacityValue = 0;
    }

private:
    usize stride() const { return ComponentRegistry::instance().info(componentType).size; }

    void reserve(usize desired) {
        if (desired <= capacityValue) return;
        usize newCapacity = capacityValue == 0 ? 16 : capacityValue * 2;
        while (newCapacity < desired) newCapacity *= 2;
        const ComponentTypeInfo& typeInfo = ComponentRegistry::instance().info(componentType);
        u8* replacement = static_cast<u8*>(std::malloc(newCapacity * typeInfo.size));
        SF_ASSERT_MSG(replacement != nullptr, "Komponenten-Spalte konnte nicht wachsen");
        for (usize row = 0; row < count; ++row) {
            typeInfo.moveConstruct(replacement + row * typeInfo.size, bytes + row * typeInfo.size);
        }
        std::free(bytes);
        bytes = replacement;
        capacityValue = newCapacity;
    }

    u8* bytes = nullptr;
    usize count = 0;
    usize capacityValue = 0;
    ComponentId componentType = 0;
};

}
