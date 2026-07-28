#pragma once

#include "../core/Common.h"

namespace echo {

enum ItemId {
    ITEM_NONE = -1,
    ITEM_FLASHLIGHT = 0,
    ITEM_BATTERY,
    ITEM_KEY_WARD,
    ITEM_KEY_BASEMENT,
    ITEM_KEY_OR,
    ITEM_KEY_ARCHIVE,
    ITEM_KEYCARD,
    ITEM_TAPE_RECORDER,
    ITEM_LIGHTER,
    ITEM_BOLT_CUTTER,
    ITEM_FUSE,
    ITEM_PHOTO,
    ITEM_WRISTBAND,
    ITEM_COUNT
};

struct ItemDef {
    const char* name;
    const char* description;
    bool stackable;
    bool key;
};

const ItemDef& itemDef(int id);

struct Document {
    int id = 0;
    std::string title;
    std::string author;
    std::string date;
    std::vector<std::string> pages;
    int truthLayer = 0;
};

struct AudioLog {
    int id = 0;
    std::string title;
    std::string speaker;
    std::vector<std::string> lines;
    std::vector<float> lineDurations;
    int truthLayer = 0;
};

enum EndingId {
    ENDING_NONE = -1,
    ENDING_RELEASE = 0,
    ENDING_DENIAL,
    ENDING_LOOP,
    ENDING_DISSOLUTION,
    ENDING_WITNESS,
    ENDING_COUNT
};

struct Ending {
    const char* codename;
    const char* title;
    const char* condition;
    const char* text[6];
};

class StoryDatabase {
public:
    void build();
    const std::vector<Document>& documents() const { return docs; }
    const std::vector<AudioLog>& audioLogs() const { return logs; }
    const Document* document(int id) const;
    const AudioLog* audioLog(int id) const;
    static const Ending& ending(int id);
    int documentCount() const { return (int)docs.size(); }
    int audioLogCount() const { return (int)logs.size(); }

private:
    std::vector<Document> docs;
    std::vector<AudioLog> logs;
};

}
