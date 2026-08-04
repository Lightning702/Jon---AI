#include "ConfigStore.hpp"

#include <cstdio>
#include <cstdlib>

namespace sf {
namespace {

std::string trim(const std::string& text) {
    usize begin = 0;
    usize end = text.size();
    while (begin < end && (text[begin] == ' ' || text[begin] == '\t' || text[begin] == '\r')) ++begin;
    while (end > begin && (text[end - 1] == ' ' || text[end - 1] == '\t' || text[end - 1] == '\r')) --end;
    return text.substr(begin, end - begin);
}

}

Status ConfigStore::load(const std::string& path) {
    std::FILE* file = std::fopen(path.c_str(), "rb");
    if (!file) {
        return statusError(StatusCode::NotFound, "Konfiguration nicht gefunden: " + path);
    }
    std::string section;
    char line[1024];
    while (std::fgets(line, sizeof(line), file)) {
        std::string entry = trim(line);
        if (entry.empty()) continue;
        if (entry[0] == '#' || entry[0] == ';') continue;
        if (entry.front() == '[' && entry.back() == ']') {
            section = trim(entry.substr(1, entry.size() - 2));
            continue;
        }
        const usize separator = entry.find('=');
        if (separator == std::string::npos) continue;
        std::string key = trim(entry.substr(0, separator));
        std::string value = trim(entry.substr(separator + 1));
        if (value.size() >= 2 && value.front() == '"' && value.back() == '"') {
            value = value.substr(1, value.size() - 2);
        }
        if (!section.empty()) key = section + "." + key;
        values[key] = value;
    }
    std::fclose(file);
    return statusOk();
}

Status ConfigStore::save(const std::string& path) const {
    std::FILE* file = std::fopen(path.c_str(), "wb");
    if (!file) {
        return statusError(StatusCode::IoFailure, "Konfiguration nicht schreibbar: " + path);
    }
    std::string currentSection;
    for (const auto& pair : values) {
        const usize dot = pair.first.find('.');
        std::string section = dot == std::string::npos ? std::string() : pair.first.substr(0, dot);
        std::string key = dot == std::string::npos ? pair.first : pair.first.substr(dot + 1);
        if (section != currentSection) {
            currentSection = section;
            if (!currentSection.empty()) {
                std::fprintf(file, "\n[%s]\n", currentSection.c_str());
            }
        }
        std::fprintf(file, "%s = %s\n", key.c_str(), pair.second.c_str());
    }
    std::fclose(file);
    return statusOk();
}

bool ConfigStore::has(const std::string& key) const {
    return values.find(key) != values.end();
}

std::string ConfigStore::text(const std::string& key, const std::string& fallback) const {
    auto found = values.find(key);
    return found == values.end() ? fallback : found->second;
}

i64 ConfigStore::integer(const std::string& key, i64 fallback) const {
    auto found = values.find(key);
    return found == values.end() ? fallback : std::strtoll(found->second.c_str(), nullptr, 0);
}

u64 ConfigStore::unsignedInteger(const std::string& key, u64 fallback) const {
    auto found = values.find(key);
    return found == values.end() ? fallback : std::strtoull(found->second.c_str(), nullptr, 0);
}

f64 ConfigStore::number(const std::string& key, f64 fallback) const {
    auto found = values.find(key);
    return found == values.end() ? fallback : std::strtod(found->second.c_str(), nullptr);
}

bool ConfigStore::boolean(const std::string& key, bool fallback) const {
    auto found = values.find(key);
    if (found == values.end()) return fallback;
    const std::string& raw = found->second;
    return !(raw == "0" || raw == "false" || raw == "nein" || raw == "off");
}

void ConfigStore::setText(const std::string& key, const std::string& value) {
    values[key] = value;
}

void ConfigStore::setInteger(const std::string& key, i64 value) {
    char buffer[32];
    std::snprintf(buffer, sizeof(buffer), "%lld", static_cast<long long>(value));
    values[key] = buffer;
}

void ConfigStore::setUnsignedInteger(const std::string& key, u64 value) {
    char buffer[32];
    std::snprintf(buffer, sizeof(buffer), "%llu", static_cast<unsigned long long>(value));
    values[key] = buffer;
}

void ConfigStore::setNumber(const std::string& key, f64 value) {
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%.9g", value);
    values[key] = buffer;
}

void ConfigStore::setBoolean(const std::string& key, bool value) {
    values[key] = value ? "true" : "false";
}

}
