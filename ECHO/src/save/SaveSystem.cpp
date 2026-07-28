#include "SaveSystem.h"
#include "../world/World.h"
#include "../game/Player.h"
#include "../game/Flashlight.h"
#include "../ai/Director.h"
#include "../core/FileSystem.h"
#include "../core/Log.h"

#include <ctime>

using namespace em;

namespace echo {

namespace {

const u32 kMagic = 0x4F484345;
const u32 kVersion = 3;

struct Writer {
    std::vector<u8> data;
    template <typename T> void put(const T& v) {
        const u8* p = (const u8*)&v;
        data.insert(data.end(), p, p + sizeof(T));
    }
    void putString(const std::string& s) {
        put((u32)s.size());
        data.insert(data.end(), s.begin(), s.end());
    }
    void putBytes(const std::vector<u8>& v) {
        put((u32)v.size());
        data.insert(data.end(), v.begin(), v.end());
    }
};

struct Reader {
    const std::vector<u8>* data = nullptr;
    size_t offset = 0;
    bool ok = true;
    template <typename T> T get() {
        T v{};
        if (!data || offset + sizeof(T) > data->size()) { ok = false; return v; }
        std::memcpy(&v, data->data() + offset, sizeof(T));
        offset += sizeof(T);
        return v;
    }
    std::string getString() {
        u32 n = get<u32>();
        if (!ok || offset + n > data->size()) { ok = false; return {}; }
        std::string s((const char*)data->data() + offset, n);
        offset += n;
        return s;
    }
    std::vector<u8> getBytes() {
        u32 n = get<u32>();
        if (!ok || offset + n > data->size()) { ok = false; return {}; }
        std::vector<u8> v(data->begin() + offset, data->begin() + offset + n);
        offset += n;
        return v;
    }
};

std::string nowString() {
    std::time_t t = std::time(nullptr);
    std::tm tmv;
    localtime_s(&tmv, &t);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%d.%m.%Y %H:%M", &tmv);
    return std::string(buf);
}

}

std::string SaveSystem::slotPath(const std::string& slot) {
    return "saves/" + slot + ".echo";
}

bool SaveSystem::exists(const std::string& slot) {
    return fs::exists(slotPath(slot));
}

bool SaveSystem::remove(const std::string& slot) {
    return fs::removeFile(slotPath(slot));
}

bool SaveSystem::save(const std::string& slot, const World& world, const Player& player,
                      const Flashlight& light, const Director& director, const GameProgress& progress) {
    fs::makeDir("saves");

    Writer w;
    w.put(kMagic);
    w.put(kVersion);
    w.put(progress.worldSeed);
    w.put(progress.playTime);
    w.putString(nowString());

    int roomId = world.roomAt(player.position() + Vec3(0, 0.6f, 0));
    int floorIndex = world.floorAt(player.position().y);
    w.put((i32)floorIndex);
    std::string label = "Unbekannt";
    if (roomId >= 0 && roomId < (int)world.rooms().size()) label = world.rooms()[(size_t)roomId].label;
    w.putString(label);

    w.put(player.position());
    w.put(player.yawAngle());
    w.put(player.pitchAngle());

    w.put(light.batteryLevel());
    w.put((i32)light.spareBatteries());
    w.put((u8)(light.isOn() ? 1 : 0));

    w.putBytes(progress.itemCounts);
    w.putBytes(progress.documentsFound);
    w.putBytes(progress.logsFound);
    w.put((i32)progress.endingSeen);

    const auto& doors = world.doors();
    w.put((u32)doors.size());
    for (const auto& d : doors) {
        u8 flags = 0;
        if (d.locked) flags |= 1;
        if (d.jammed) flags |= 2;
        if (d.removed) flags |= 4;
        if (d.wasOpened) flags |= 8;
        w.put(flags);
        w.put(d.targetOpen);
        w.put(d.openAmount);
    }

    const auto& lights = world.lights();
    w.put((u32)lights.size());
    for (const auto& l : lights) {
        u8 flags = 0;
        if (l.on) flags |= 1;
        if (l.broken) flags |= 2;
        w.put(flags);
        w.put(l.flickerAmount);
        w.put(l.flickerRate);
    }

    const auto& props = world.props();
    w.put((u32)props.size());
    for (const auto& p : props) {
        u8 moved = (p.position != p.originalPosition || p.yaw != p.originalYaw || p.hidden) ? 1 : 0;
        w.put(moved);
        if (moved) {
            w.put(p.position);
            w.put(p.yaw);
            w.put((u8)(p.hidden ? 1 : 0));
        }
    }

    const auto& interacts = world.interactables();
    w.put((u32)interacts.size());
    for (const auto& it : interacts) {
        u8 flags = 0;
        if (it.used) flags |= 1;
        if (it.hidden) flags |= 2;
        w.put(flags);
    }

    const auto& rooms = world.rooms();
    w.put((u32)rooms.size());
    for (const auto& r : rooms) {
        u8 flags = 0;
        if (r.visited) flags |= 1;
        if (r.mutated) flags |= 2;
        w.put(flags);
        w.put((i32)r.visitCount);
    }

    const BehaviorProfile& bp = director.tracker().profile();
    w.put(bp);
    w.put(director.tension());
    w.put(director.dread());
    w.put(director.sanity());

    if (!fs::writeBinary(slotPath(slot), w.data.data(), w.data.size())) {
        LOG_ERROR("Save failed: %s", slot.c_str());
        return false;
    }
    LOG_INFO("Saved %s (%zu bytes)", slot.c_str(), w.data.size());
    return true;
}

SaveMeta SaveSystem::peek(const std::string& slot) {
    SaveMeta meta;
    std::vector<u8> bytes;
    if (!fs::readBinary(slotPath(slot), bytes) || bytes.size() < 32) return meta;

    Reader r{ &bytes, 0, true };
    if (r.get<u32>() != kMagic) return meta;
    meta.version = r.get<u32>();
    if (meta.version != kVersion) return meta;
    r.get<u64>();
    meta.playTime = r.get<float>();
    meta.timestamp = r.getString();
    meta.floor = r.get<i32>();
    meta.roomLabel = r.getString();
    meta.valid = r.ok;
    return meta;
}

bool SaveSystem::load(const std::string& slot, World& world, Player& player,
                      Flashlight& light, Director& director, GameProgress& progress) {
    std::vector<u8> bytes;
    if (!fs::readBinary(slotPath(slot), bytes)) return false;

    Reader r{ &bytes, 0, true };
    if (r.get<u32>() != kMagic) return false;
    if (r.get<u32>() != kVersion) return false;

    progress.worldSeed = r.get<u64>();
    progress.playTime = r.get<float>();
    r.getString();
    r.get<i32>();
    r.getString();

    Vec3 pos = r.get<Vec3>();
    float yaw = r.get<float>();
    float pitch = r.get<float>();
    player.reset(pos, yaw);
    player.setOrientation(yaw, pitch);

    light.reset();
    light.setBattery(r.get<float>());
    light.addSpare(r.get<i32>() - light.spareBatteries());
    light.setOn(r.get<u8>() != 0);

    progress.itemCounts = r.getBytes();
    progress.documentsFound = r.getBytes();
    progress.logsFound = r.getBytes();
    progress.endingSeen = r.get<i32>();

    u32 doorCount = r.get<u32>();
    auto& doors = world.doors();
    for (u32 i = 0; i < doorCount && r.ok; i++) {
        u8 flags = r.get<u8>();
        float target = r.get<float>();
        float amount = r.get<float>();
        if (i < doors.size()) {
            doors[i].locked = (flags & 1) != 0;
            doors[i].jammed = (flags & 2) != 0;
            doors[i].removed = (flags & 4) != 0;
            doors[i].wasOpened = (flags & 8) != 0;
            doors[i].targetOpen = target;
            doors[i].openAmount = amount;
        }
    }

    u32 lightCount = r.get<u32>();
    auto& lights = world.lights();
    for (u32 i = 0; i < lightCount && r.ok; i++) {
        u8 flags = r.get<u8>();
        float amount = r.get<float>();
        float rate = r.get<float>();
        if (i < lights.size()) {
            lights[i].on = (flags & 1) != 0;
            lights[i].broken = (flags & 2) != 0;
            lights[i].flickerAmount = amount;
            lights[i].flickerRate = rate;
            lights[i].currentScale = lights[i].on && !lights[i].broken ? 1.0f : 0.0f;
        }
    }

    u32 propCount = r.get<u32>();
    auto& props = world.props();
    for (u32 i = 0; i < propCount && r.ok; i++) {
        u8 moved = r.get<u8>();
        if (!moved) continue;
        Vec3 p = r.get<Vec3>();
        float y = r.get<float>();
        u8 hidden = r.get<u8>();
        if (i < props.size()) {
            props[i].position = p;
            props[i].yaw = y;
            props[i].hidden = hidden != 0;
            world.refreshCollider((int)i);
        }
    }

    u32 interactCount = r.get<u32>();
    auto& interacts = world.interactables();
    for (u32 i = 0; i < interactCount && r.ok; i++) {
        u8 flags = r.get<u8>();
        if (i < interacts.size()) {
            interacts[i].used = (flags & 1) != 0;
            interacts[i].hidden = (flags & 2) != 0;
        }
    }

    u32 roomCount = r.get<u32>();
    auto& rooms = world.rooms();
    for (u32 i = 0; i < roomCount && r.ok; i++) {
        u8 flags = r.get<u8>();
        i32 visits = r.get<i32>();
        if (i < rooms.size()) {
            rooms[i].visited = (flags & 1) != 0;
            rooms[i].mutated = (flags & 2) != 0;
            rooms[i].visitCount = visits;
        }
    }

    if (!r.ok) {
        LOG_WARN("Save file truncated: %s", slot.c_str());
        return false;
    }

    LOG_INFO("Loaded %s", slot.c_str());
    return true;
}

}
