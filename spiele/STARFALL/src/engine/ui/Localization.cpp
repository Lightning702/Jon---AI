#include "Localization.hpp"

#include <cstdio>

namespace sf {
namespace {

struct Phrase {
    const char* key;
    const char* german;
    const char* english;
};

const Phrase kPhrases[] = {
    {"menu.continue", "FORTSETZEN", "CONTINUE"},
    {"menu.newgame", "NEUES SPIEL", "NEW GAME"},
    {"menu.multiplayer", "MULTIPLAYER", "MULTIPLAYER"},
    {"menu.catalog", "GALAXIENKATALOG", "GALAXY CATALOGUE"},
    {"menu.settings", "EINSTELLUNGEN", "SETTINGS"},
    {"menu.quit", "BEENDEN", "QUIT"},
    {"menu.title", "STARFALL", "STARFALL"},
    {"menu.subtitle", "BEYOND THE VOID", "BEYOND THE VOID"},
    {"hud.hull", "RUMPF", "HULL"},
    {"hud.shield", "SCHILD", "SHIELD"},
    {"hud.power", "ENERGIE", "POWER"},
    {"hud.fuel", "TREIBSTOFF", "FUEL"},
    {"hud.heat", "HITZE", "HEAT"},
    {"hud.speed", "GESCHWINDIGKEIT", "VELOCITY"},
    {"hud.mode", "FLUGMODUS", "FLIGHT MODE"},
    {"hud.target", "ZIEL", "TARGET"},
    {"hud.oxygen", "SAUERSTOFF", "OXYGEN"},
    {"hud.dilation", "ZEITFAKTOR", "TIME FACTOR"},
    {"map.title", "GALAXIEKARTE", "GALAXY MAP"},
    {"map.route", "ROUTE", "ROUTE"},
    {"map.jump", "SPRUNG EINLEITEN", "INITIATE JUMP"},
    {"map.filter", "FILTER", "FILTER"},
    {"void.zone5", "FERNFELD", "FAR FIELD"},
    {"void.zone4", "GRAVITATIONSDRIFT", "GRAVITY DRIFT"},
    {"void.zone3", "VERZERRUNGSZONE", "DISTORTION ZONE"},
    {"void.zone2", "ERGOSPHAERE", "ERGOSPHERE"},
    {"void.zone1", "HORIZONTNAEHE", "HORIZON PROXIMITY"},
    {"void.zone0", "EREIGNISHORIZONT", "EVENT HORIZON"},
    {"jon.name", "JON", "JON"},
    {"flight.newtonian", "NEWTONISCH", "NEWTONIAN"},
    {"flight.assisted", "ASSISTIERT", "ASSISTED"},
    {"flight.atmospheric", "ATMOSPHAERISCH", "ATMOSPHERIC"},
    {"flight.docking", "ANDOCKEN", "DOCKING"},
    {"common.loading", "LADEN", "LOADING"},
    {"common.online", "ONLINE", "ONLINE"},
    {"common.offline", "OFFLINE", "OFFLINE"}};

}

Localization::Localization() {
    for (const Phrase& phrase : kPhrases) {
        tables[static_cast<usize>(Language::German)][phrase.key] = phrase.german;
        tables[static_cast<usize>(Language::English)][phrase.key] = phrase.english;
    }
}

Localization& Localization::instance() {
    static Localization store;
    return store;
}

void Localization::setLanguage(Language language) {
    activeLanguage = language;
}

const std::string& Localization::text(const std::string& key) const {
    const auto& table = tables[static_cast<usize>(activeLanguage)];
    auto found = table.find(key);
    if (found != table.end()) return found->second;
    const auto& fallback = tables[static_cast<usize>(Language::German)];
    auto fallbackFound = fallback.find(key);
    if (fallbackFound != fallback.end()) return fallbackFound->second;
    return missing;
}

std::string Localization::formatted(const std::string& key, f64 value, u32 decimals) const {
    char buffer[128];
    std::snprintf(buffer, sizeof(buffer), "%s %.*f", text(key).c_str(), static_cast<int>(decimals), value);
    return buffer;
}

const std::string& translate(const std::string& key) {
    return Localization::instance().text(key);
}

}
