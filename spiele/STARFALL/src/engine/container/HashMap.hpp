#pragma once

#include "Array.hpp"

namespace sf {

template <typename Key, typename Value>
class HashMap {
public:
    struct Entry {
        Key key = Key();
        Value value = Value();
        u64 hash = 0;
        bool occupied = false;
        bool tombstone = false;
    };

    HashMap() { entries.resize(16); }

    void insert(const Key& key, const Value& value) {
        if (static_cast<f32>(count + 1) > static_cast<f32>(entries.size()) * 0.7f) rehash(entries.size() * 2);
        const u64 hash = hashKey(key);
        usize slot = static_cast<usize>(hash) & (entries.size() - 1);
        usize firstTombstone = kInvalidIndex64;
        while (entries[slot].occupied || entries[slot].tombstone) {
            if (entries[slot].occupied && entries[slot].hash == hash && entries[slot].key == key) {
                entries[slot].value = value;
                return;
            }
            if (entries[slot].tombstone && firstTombstone == kInvalidIndex64) firstTombstone = slot;
            slot = (slot + 1) & (entries.size() - 1);
        }
        if (firstTombstone != kInvalidIndex64) slot = firstTombstone;
        entries[slot].key = key;
        entries[slot].value = value;
        entries[slot].hash = hash;
        entries[slot].occupied = true;
        entries[slot].tombstone = false;
        ++count;
    }

    Value* find(const Key& key) {
        if (count == 0) return nullptr;
        const u64 hash = hashKey(key);
        usize slot = static_cast<usize>(hash) & (entries.size() - 1);
        usize probes = 0;
        while ((entries[slot].occupied || entries[slot].tombstone) && probes < entries.size()) {
            if (entries[slot].occupied && entries[slot].hash == hash && entries[slot].key == key) {
                return &entries[slot].value;
            }
            slot = (slot + 1) & (entries.size() - 1);
            ++probes;
        }
        return nullptr;
    }

    const Value* find(const Key& key) const {
        return const_cast<HashMap*>(this)->find(key);
    }

    bool contains(const Key& key) const { return find(key) != nullptr; }

    Value& operator[](const Key& key) {
        Value* existing = find(key);
        if (existing) return *existing;
        insert(key, Value());
        return *find(key);
    }

    void remove(const Key& key) {
        if (count == 0) return;
        const u64 hash = hashKey(key);
        usize slot = static_cast<usize>(hash) & (entries.size() - 1);
        usize probes = 0;
        while ((entries[slot].occupied || entries[slot].tombstone) && probes < entries.size()) {
            if (entries[slot].occupied && entries[slot].hash == hash && entries[slot].key == key) {
                entries[slot].occupied = false;
                entries[slot].tombstone = true;
                --count;
                return;
            }
            slot = (slot + 1) & (entries.size() - 1);
            ++probes;
        }
    }

    void clear() {
        for (usize index = 0; index < entries.size(); ++index) {
            entries[index].occupied = false;
            entries[index].tombstone = false;
        }
        count = 0;
    }

    usize size() const { return count; }
    bool empty() const { return count == 0; }
    usize slots() const { return entries.size(); }
    const Entry& slotAt(usize index) const { return entries[index]; }

private:
    static u64 hashKey(const Key& key) {
        u64 value = static_cast<u64>(key);
        value ^= value >> 33;
        value *= 0xFF51AFD7ED558CCDull;
        value ^= value >> 33;
        value *= 0xC4CEB9FE1A85EC53ull;
        value ^= value >> 33;
        return value;
    }

    void rehash(usize desiredSlots) {
        Array<Entry> previous = entries;
        entries.clear();
        entries.resize(desiredSlots < 16 ? 16 : desiredSlots);
        count = 0;
        for (usize index = 0; index < previous.size(); ++index) {
            if (previous[index].occupied) insert(previous[index].key, previous[index].value);
        }
    }

    Array<Entry> entries;
    usize count = 0;
};

}
