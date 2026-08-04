#pragma once

#include "Array.hpp"

namespace sf {

template <typename T>
class SparseSet {
public:
    void reserveDense(usize capacityValue) {
        dense.reserve(capacityValue);
        values.reserve(capacityValue);
    }

    bool contains(u32 key) const {
        return key < sparse.size() && sparse[key] != kInvalidIndex32 && sparse[key] < dense.size() &&
               dense[sparse[key]] == key;
    }

    T& insert(u32 key, const T& value) {
        if (contains(key)) {
            values[sparse[key]] = value;
            return values[sparse[key]];
        }
        if (key >= sparse.size()) {
            const usize previous = sparse.size();
            sparse.resize(key + 1);
            for (usize index = previous; index < sparse.size(); ++index) sparse[index] = kInvalidIndex32;
        }
        sparse[key] = static_cast<u32>(dense.size());
        dense.push(key);
        values.push(value);
        return values.back();
    }

    void remove(u32 key) {
        if (!contains(key)) return;
        const u32 slot = sparse[key];
        const u32 lastKey = dense.back();
        dense[slot] = lastKey;
        values[slot] = std::move(values[values.size() - 1]);
        sparse[lastKey] = slot;
        dense.pop();
        values.pop();
        sparse[key] = kInvalidIndex32;
    }

    T* find(u32 key) {
        return contains(key) ? &values[sparse[key]] : nullptr;
    }

    const T* find(u32 key) const {
        return contains(key) ? &values[sparse[key]] : nullptr;
    }

    T& valueAtDense(usize index) { return values[index]; }
    const T& valueAtDense(usize index) const { return values[index]; }
    u32 keyAtDense(usize index) const { return dense[index]; }

    usize size() const { return dense.size(); }
    bool empty() const { return dense.empty(); }

    void clear() {
        for (usize index = 0; index < dense.size(); ++index) sparse[dense[index]] = kInvalidIndex32;
        dense.clear();
        values.clear();
    }

    const Array<u32>& keys() const { return dense; }
    Array<T>& data() { return values; }
    const Array<T>& data() const { return values; }

private:
    Array<u32> sparse;
    Array<u32> dense;
    Array<T> values;
};

}
