#include "Guide.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

void RouteGuide::init(World* w) {
    world = w;
    reset();
}

void RouteGuide::reset() {
    path.clear();
    roomChain.clear();
    targetValid = false;
    pathValid = false;
    shown = false;
    cursor = 0;
    fromRoomCache = -2;
    targetRoomCache = -2;
    refreshTimer = 0.0f;
    remaining = 0.0f;
    pulseValue = 0.0f;
    targetLabel.clear();
    statusText.clear();
}

void RouteGuide::toggle() {
    shown = !shown;
    if (shown) {
        refreshTimer = 0.0f;
        fromRoomCache = -2;
    }
}

void RouteGuide::setTarget(const Vec3& position, const std::string& text) {
    target = position;
    targetLabel = text;
    targetValid = true;
    fromRoomCache = -2;
    targetRoomCache = -2;
    refreshTimer = 0.0f;
}

void RouteGuide::clearTarget() {
    targetValid = false;
    pathValid = false;
    path.clear();
    targetLabel.clear();
}

Vec3 RouteGuide::doorWaypoint(const Door& door, int fromRoom) const {
    Vec3 point = door.center;
    if (world != nullptr) {
        int other = door.roomA == fromRoom ? door.roomB : door.roomA;
        if (other >= 0 && other < (int)world->rooms().size()) {
            point.y = world->rooms()[(size_t)other].floorY;
        }
    }
    return point;
}

bool RouteGuide::buildRoomPath(int fromRoom, int toRoom, std::vector<int>& outRooms) const {
    outRooms.clear();
    if (world == nullptr) return false;
    int count = (int)world->rooms().size();
    if (fromRoom < 0 || toRoom < 0 || fromRoom >= count || toRoom >= count) return false;
    if (fromRoom == toRoom) {
        outRooms.push_back(fromRoom);
        return true;
    }

    std::vector<int> prev((size_t)count, -1);
    std::vector<char> seen((size_t)count, 0);
    std::vector<int> queue;
    queue.reserve((size_t)count);
    queue.push_back(fromRoom);
    seen[(size_t)fromRoom] = 1;

    size_t head = 0;
    bool found = false;
    while (head < queue.size()) {
        int current = queue[head++];
        if (current == toRoom) {
            found = true;
            break;
        }
        const Room& room = world->rooms()[(size_t)current];
        for (int doorId : room.doors) {
            if (doorId < 0 || doorId >= (int)world->doors().size()) continue;
            const Door& door = world->doors()[(size_t)doorId];
            if (door.removed) continue;
            int other = door.roomA == current ? door.roomB : door.roomA;
            if (other < 0 || other >= count) continue;
            if (seen[(size_t)other]) continue;
            if (world->rooms()[(size_t)other].sealed) continue;
            seen[(size_t)other] = 1;
            prev[(size_t)other] = current;
            queue.push_back(other);
        }
    }

    if (!found) return false;

    std::vector<int> reverse;
    int walk = toRoom;
    while (walk >= 0) {
        reverse.push_back(walk);
        if (walk == fromRoom) break;
        walk = prev[(size_t)walk];
    }
    if (reverse.empty() || reverse.back() != fromRoom) return false;
    for (size_t i = reverse.size(); i > 0; i--) outRooms.push_back(reverse[i - 1]);
    return true;
}

bool RouteGuide::rebuild(const Vec3& from) {
    path.clear();
    pathValid = false;
    if (world == nullptr || !targetValid) {
        statusText = "Kein Ziel";
        return false;
    }

    int fromRoom = world->roomAt(from + Vec3(0, 0.6f, 0));
    int toRoom = world->roomAt(target + Vec3(0, 0.6f, 0));
    if (toRoom < 0) toRoom = world->roomAt(target + Vec3(0, 1.4f, 0));
    if (fromRoom < 0 || toRoom < 0) {
        statusText = "Position unklar";
        return false;
    }

    fromRoomCache = fromRoom;
    targetRoomCache = toRoom;

    if (!buildRoomPath(fromRoom, toRoom, roomChain)) {
        statusText = "Kein offener Weg";
        return false;
    }

    for (size_t i = 0; i + 1 < roomChain.size(); i++) {
        int a = roomChain[i];
        int b = roomChain[i + 1];
        int doorId = world->doorBetween(a, b);
        GuideNode node;
        node.room = b;
        node.door = doorId;
        if (doorId >= 0 && doorId < (int)world->doors().size()) {
            const Door& door = world->doors()[(size_t)doorId];
            node.position = doorWaypoint(door, a);
            node.elevator = door.kind == DOOR_ELEVATOR;
        } else {
            node.position = world->roomCenter(b);
        }
        const Room& next = world->rooms()[(size_t)b];
        node.stairs = next.type == ROOM_STAIRWELL;
        if (next.type == ROOM_ELEVATOR) node.elevator = true;
        path.push_back(node);
    }

    GuideNode last;
    last.position = target;
    last.room = toRoom;
    path.push_back(last);

    cursor = 0;
    pathValid = true;
    statusText = targetLabel.empty() ? "Ziel" : targetLabel;
    return true;
}

void RouteGuide::update(const Player& player, float dt, float time) {
    pulseValue = 0.5f + 0.5f * std::sin(time * 3.4f);
    if (!shown || !targetValid || world == nullptr) return;

    refreshTimer -= dt;
    Vec3 pos = player.position();
    int room = world->roomAt(pos + Vec3(0, 0.6f, 0));
    bool needRebuild = refreshTimer <= 0.0f || room != fromRoomCache || !pathValid;
    if (needRebuild) {
        refreshTimer = 1.25f;
        rebuild(pos);
    }
    if (!pathValid) {
        remaining = 0.0f;
        return;
    }

    while (cursor < (int)path.size() - 1) {
        Vec3 flat = path[(size_t)cursor].position;
        float dx = flat.x - pos.x;
        float dz = flat.z - pos.z;
        float dy = std::fabs(flat.y - pos.y);
        if (dx * dx + dz * dz < 2.6f * 2.6f && dy < 2.4f) cursor++;
        else break;
    }
    if (cursor >= (int)path.size()) cursor = (int)path.size() - 1;

    remaining = 0.0f;
    Vec3 walk = pos;
    for (size_t i = (size_t)cursor; i < path.size(); i++) {
        remaining += distance(walk, path[i].position);
        walk = path[i].position;
    }
}

}
