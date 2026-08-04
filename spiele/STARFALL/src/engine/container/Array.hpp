#pragma once

#include "../core/Assert.hpp"
#include "../core/Types.hpp"

#include <cstdlib>
#include <cstring>
#include <new>
#include <utility>

namespace sf {

template <typename T>
class Array {
public:
    Array() = default;
    explicit Array(usize initialCapacity) { reserve(initialCapacity); }
    ~Array() { clearAndFree(); }

    Array(const Array& other) { copyFrom(other); }
    Array& operator=(const Array& other) {
        if (this != &other) {
            clearAndFree();
            copyFrom(other);
        }
        return *this;
    }

    Array(Array&& other) noexcept : items(other.items), count(other.count), capacityValue(other.capacityValue) {
        other.items = nullptr;
        other.count = 0;
        other.capacityValue = 0;
    }

    Array& operator=(Array&& other) noexcept {
        if (this != &other) {
            clearAndFree();
            items = other.items;
            count = other.count;
            capacityValue = other.capacityValue;
            other.items = nullptr;
            other.count = 0;
            other.capacityValue = 0;
        }
        return *this;
    }

    void reserve(usize desiredCapacity) {
        if (desiredCapacity <= capacityValue) return;
        T* replacement = static_cast<T*>(std::malloc(sizeof(T) * desiredCapacity));
        SF_ASSERT_MSG(replacement != nullptr, "Array konnte nicht wachsen");
        for (usize index = 0; index < count; ++index) {
            new (replacement + index) T(std::move(items[index]));
            items[index].~T();
        }
        std::free(items);
        items = replacement;
        capacityValue = desiredCapacity;
    }

    void resize(usize desiredCount) {
        if (desiredCount > count) {
            reserve(desiredCount);
            for (usize index = count; index < desiredCount; ++index) new (items + index) T();
        } else {
            for (usize index = desiredCount; index < count; ++index) items[index].~T();
        }
        count = desiredCount;
    }

    void push(const T& value) {
        growIfNeeded();
        new (items + count) T(value);
        ++count;
    }

    void push(T&& value) {
        growIfNeeded();
        new (items + count) T(std::move(value));
        ++count;
    }

    template <typename... Args>
    T& emplace(Args&&... args) {
        growIfNeeded();
        new (items + count) T(std::forward<Args>(args)...);
        return items[count++];
    }

    void pop() {
        if (count == 0) return;
        --count;
        items[count].~T();
    }

    void removeAtSwap(usize index) {
        if (index >= count) return;
        items[index].~T();
        --count;
        if (index != count) {
            new (items + index) T(std::move(items[count]));
            items[count].~T();
        }
    }

    void removeAtOrdered(usize index) {
        if (index >= count) return;
        for (usize position = index; position + 1 < count; ++position) {
            items[position] = std::move(items[position + 1]);
        }
        --count;
        items[count].~T();
    }

    void clear() {
        for (usize index = 0; index < count; ++index) items[index].~T();
        count = 0;
    }

    void clearAndFree() {
        clear();
        std::free(items);
        items = nullptr;
        capacityValue = 0;
    }

    T& operator[](usize index) { return items[index]; }
    const T& operator[](usize index) const { return items[index]; }
    T& front() { return items[0]; }
    T& back() { return items[count - 1]; }
    const T& back() const { return items[count - 1]; }

    T* data() { return items; }
    const T* data() const { return items; }
    T* begin() { return items; }
    T* end() { return items + count; }
    const T* begin() const { return items; }
    const T* end() const { return items + count; }

    usize size() const { return count; }
    usize capacity() const { return capacityValue; }
    bool empty() const { return count == 0; }

private:
    void growIfNeeded() {
        if (count < capacityValue) return;
        reserve(capacityValue == 0 ? 8 : capacityValue * 2);
    }

    void copyFrom(const Array& other) {
        reserve(other.count);
        for (usize index = 0; index < other.count; ++index) new (items + index) T(other.items[index]);
        count = other.count;
    }

    T* items = nullptr;
    usize count = 0;
    usize capacityValue = 0;
};

}
