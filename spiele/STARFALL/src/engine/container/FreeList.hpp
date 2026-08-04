#pragma once

#include "Array.hpp"

namespace sf {

template <typename T>
class FreeList {
public:
    struct Slot {
        T value = T();
        u32 generation = 1;
        bool alive = false;
    };

    u32 allocateSlot(const T& value, u32& generationOut) {
        u32 index;
        if (!freeIndices.empty()) {
            index = freeIndices.back();
            freeIndices.pop();
        } else {
            index = static_cast<u32>(slots.size());
            slots.emplace();
        }
        Slot& slot = slots[index];
        slot.value = value;
        slot.alive = true;
        generationOut = slot.generation;
        ++liveCount;
        return index;
    }

    bool releaseSlot(u32 index, u32 generation) {
        if (index >= slots.size()) return false;
        Slot& slot = slots[index];
        if (!slot.alive || slot.generation != generation) return false;
        slot.alive = false;
        slot.generation += 1;
        if (slot.generation == 0) slot.generation = 1;
        freeIndices.push(index);
        if (liveCount > 0) --liveCount;
        return true;
    }

    T* resolve(u32 index, u32 generation) {
        if (index >= slots.size()) return nullptr;
        Slot& slot = slots[index];
        if (!slot.alive || slot.generation != generation) return nullptr;
        return &slot.value;
    }

    const T* resolve(u32 index, u32 generation) const {
        return const_cast<FreeList*>(this)->resolve(index, generation);
    }

    bool aliveAt(u32 index) const { return index < slots.size() && slots[index].alive; }
    T& valueAt(u32 index) { return slots[index].value; }
    const T& valueAt(u32 index) const { return slots[index].value; }
    u32 generationAt(u32 index) const { return slots[index].generation; }

    usize slotCount() const { return slots.size(); }
    usize live() const { return liveCount; }

    void clear() {
        slots.clear();
        freeIndices.clear();
        liveCount = 0;
    }

private:
    Array<Slot> slots;
    Array<u32> freeIndices;
    usize liveCount = 0;
};

}
