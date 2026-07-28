#pragma once

#include "../core/Common.h"
#include "../core/Math.h"

namespace echo {

class World;
class Player;
class Director;
class Flashlight;

struct SaveMeta {
    bool valid = false;
    u32 version = 0;
    float playTime = 0.0f;
    int floor = 0;
    std::string roomLabel;
    std::string timestamp;
    int documentsRead = 0;
    int logsHeard = 0;
};

struct GameProgress {
    std::vector<u8> itemCounts;
    std::vector<u8> documentsFound;
    std::vector<u8> logsFound;
    int currentDocument = -1;
    float playTime = 0.0f;
    u64 worldSeed = 0;
    int endingSeen = -1;
};

class SaveSystem {
public:
    static bool save(const std::string& slot, const World& world, const Player& player,
                     const Flashlight& light, const Director& director, const GameProgress& progress);
    static bool load(const std::string& slot, World& world, Player& player,
                     Flashlight& light, Director& director, GameProgress& progress);
    static SaveMeta peek(const std::string& slot);
    static bool exists(const std::string& slot);
    static bool remove(const std::string& slot);
    static std::string slotPath(const std::string& slot);
};

}
