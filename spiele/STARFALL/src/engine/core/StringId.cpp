#include "StringId.hpp"

#include <mutex>
#include <unordered_map>

namespace sf {
namespace {

struct StringTable {
    std::mutex mutex;
    std::unordered_map<u64, std::string> entries;
};

StringTable& table() {
    static StringTable instance;
    return instance;
}

}

void StringId::registerText(const char* text) {
    if (!text || !*text) return;
    StringTable& store = table();
    u64 key = hashString(text);
    std::lock_guard<std::mutex> lock(store.mutex);
    auto found = store.entries.find(key);
    if (found == store.entries.end()) {
        store.entries.emplace(key, std::string(text));
    }
}

const char* StringId::text() const {
    StringTable& store = table();
    std::lock_guard<std::mutex> lock(store.mutex);
    auto found = store.entries.find(hashValue);
    return found == store.entries.end() ? "" : found->second.c_str();
}

}
