#include "CommandLine.hpp"

#include <cstdlib>

namespace sf {
namespace {

std::string normalize(const std::string& token) {
    usize start = 0;
    while (start < token.size() && (token[start] == '-' || token[start] == '/')) ++start;
    std::string name = token.substr(start);
    for (char& c : name) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    }
    return name;
}

bool looksLikeOption(const std::string& token) {
    return token.size() > 1 && (token[0] == '-' || token[0] == '/');
}

}

void CommandLine::parse(int argumentCount, char** argumentValues) {
    values.clear();
    loose.clear();
    if (argumentCount > 0 && argumentValues && argumentValues[0]) {
        executable = argumentValues[0];
    }
    for (int i = 1; i < argumentCount; ++i) {
        if (!argumentValues[i]) continue;
        std::string token = argumentValues[i];
        if (!looksLikeOption(token)) {
            loose.push_back(token);
            continue;
        }
        std::string name = normalize(token);
        const usize equals = name.find('=');
        if (equals != std::string::npos) {
            values[name.substr(0, equals)] = name.substr(equals + 1);
            continue;
        }
        if (i + 1 < argumentCount && argumentValues[i + 1] && !looksLikeOption(argumentValues[i + 1])) {
            values[name] = argumentValues[i + 1];
            ++i;
        } else {
            values[name] = "1";
        }
    }
}

bool CommandLine::has(const std::string& name) const {
    return values.find(name) != values.end();
}

std::string CommandLine::text(const std::string& name, const std::string& fallback) const {
    auto found = values.find(name);
    return found == values.end() ? fallback : found->second;
}

i64 CommandLine::integer(const std::string& name, i64 fallback) const {
    auto found = values.find(name);
    if (found == values.end()) return fallback;
    return std::strtoll(found->second.c_str(), nullptr, 0);
}

u64 CommandLine::unsignedInteger(const std::string& name, u64 fallback) const {
    auto found = values.find(name);
    if (found == values.end()) return fallback;
    return std::strtoull(found->second.c_str(), nullptr, 0);
}

f64 CommandLine::number(const std::string& name, f64 fallback) const {
    auto found = values.find(name);
    if (found == values.end()) return fallback;
    return std::strtod(found->second.c_str(), nullptr);
}

bool CommandLine::flag(const std::string& name, bool fallback) const {
    auto found = values.find(name);
    if (found == values.end()) return fallback;
    const std::string& raw = found->second;
    return !(raw == "0" || raw == "false" || raw == "nein" || raw == "off");
}

CommandLine& globalCommandLine() {
    static CommandLine instance;
    return instance;
}

}
