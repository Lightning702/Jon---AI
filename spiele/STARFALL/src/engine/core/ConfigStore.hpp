#pragma once

#include "Result.hpp"
#include "Types.hpp"

#include <map>
#include <string>

namespace sf {

class ConfigStore {
public:
    Status load(const std::string& path);
    Status save(const std::string& path) const;

    bool has(const std::string& key) const;
    std::string text(const std::string& key, const std::string& fallback) const;
    i64 integer(const std::string& key, i64 fallback) const;
    u64 unsignedInteger(const std::string& key, u64 fallback) const;
    f64 number(const std::string& key, f64 fallback) const;
    bool boolean(const std::string& key, bool fallback) const;

    void setText(const std::string& key, const std::string& value);
    void setInteger(const std::string& key, i64 value);
    void setUnsignedInteger(const std::string& key, u64 value);
    void setNumber(const std::string& key, f64 value);
    void setBoolean(const std::string& key, bool value);

    const std::map<std::string, std::string>& entries() const { return values; }

private:
    std::map<std::string, std::string> values;
};

}
