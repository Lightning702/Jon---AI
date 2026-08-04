#pragma once

#include "Array.hpp"

namespace sf {

class BitSet {
public:
    BitSet() = default;
    explicit BitSet(usize bitCount) { resize(bitCount); }

    void resize(usize bitCount) {
        bits = bitCount;
        words.resize((bitCount + 63) / 64);
        for (usize index = 0; index < words.size(); ++index) words[index] = 0;
    }

    void set(usize index) {
        if (index >= bits) return;
        words[index >> 6] |= (1ull << (index & 63));
    }

    void clear(usize index) {
        if (index >= bits) return;
        words[index >> 6] &= ~(1ull << (index & 63));
    }

    void assign(usize index, bool value) {
        if (value) set(index); else clear(index);
    }

    bool test(usize index) const {
        if (index >= bits) return false;
        return (words[index >> 6] & (1ull << (index & 63))) != 0;
    }

    void clearAll() {
        for (usize index = 0; index < words.size(); ++index) words[index] = 0;
    }

    bool anySet() const {
        for (usize index = 0; index < words.size(); ++index) {
            if (words[index] != 0) return true;
        }
        return false;
    }

    usize countSet() const {
        usize total = 0;
        for (usize index = 0; index < words.size(); ++index) {
            u64 word = words[index];
            while (word) {
                word &= word - 1;
                ++total;
            }
        }
        return total;
    }

    bool intersects(const BitSet& other) const {
        const usize shared = words.size() < other.words.size() ? words.size() : other.words.size();
        for (usize index = 0; index < shared; ++index) {
            if ((words[index] & other.words[index]) != 0) return true;
        }
        return false;
    }

    bool containsAll(const BitSet& other) const {
        for (usize index = 0; index < other.words.size(); ++index) {
            const u64 required = other.words[index];
            const u64 present = index < words.size() ? words[index] : 0ull;
            if ((present & required) != required) return false;
        }
        return true;
    }

    usize size() const { return bits; }

private:
    Array<u64> words;
    usize bits = 0;
};

}
