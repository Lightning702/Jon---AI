#pragma once

#include "Types.hpp"

#include <string>
#include <unordered_map>
#include <vector>

namespace sf {

class CommandLine {
public:
    void parse(int argumentCount, char** argumentValues);

    bool has(const std::string& name) const;
    std::string text(const std::string& name, const std::string& fallback) const;
    i64 integer(const std::string& name, i64 fallback) const;
    u64 unsignedInteger(const std::string& name, u64 fallback) const;
    f64 number(const std::string& name, f64 fallback) const;
    bool flag(const std::string& name, bool fallback) const;

    const std::vector<std::string>& positional() const { return loose; }
    const std::string& executablePath() const { return executable; }

private:
    std::unordered_map<std::string, std::string> values;
    std::vector<std::string> loose;
    std::string executable;
};

CommandLine& globalCommandLine();

}
