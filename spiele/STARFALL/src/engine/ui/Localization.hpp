#pragma once

#include "../core/Types.hpp"

#include <string>
#include <unordered_map>

namespace sf {

enum class Language : u32 {
    German = 0,
    English = 1,
    Count
};

class Localization {
public:
    static Localization& instance();

    void setLanguage(Language language);
    Language language() const { return activeLanguage; }
    const std::string& text(const std::string& key) const;
    std::string formatted(const std::string& key, f64 value, u32 decimals) const;

private:
    Localization();
    std::unordered_map<std::string, std::string> tables[static_cast<usize>(Language::Count)];
    Language activeLanguage = Language::German;
    std::string missing;
};

const std::string& translate(const std::string& key);

}
