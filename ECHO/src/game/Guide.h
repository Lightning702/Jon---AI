#pragma once

#include "../world/World.h"
#include "Player.h"

namespace echo {

struct GuideNode {
    em::Vec3 position;
    int room = -1;
    int door = -1;
    bool stairs = false;
    bool elevator = false;
};

class RouteGuide {
public:
    void init(World* world);
    void reset();

    void toggle();
    bool visible() const { return shown; }
    void setTarget(const em::Vec3& position, const std::string& label);
    void clearTarget();
    bool hasTarget() const { return targetValid; }

    void update(const Player& player, float dt, float time);

    const std::vector<GuideNode>& nodes() const { return path; }
    int nextIndex() const { return cursor; }
    float remainingDistance() const { return remaining; }
    const std::string& label() const { return targetLabel; }
    const std::string& status() const { return statusText; }
    bool reachable() const { return pathValid; }
    float pulse() const { return pulseValue; }

private:
    bool rebuild(const em::Vec3& from);
    bool buildRoomPath(int fromRoom, int toRoom, std::vector<int>& outRooms) const;
    em::Vec3 doorWaypoint(const Door& door, int fromRoom) const;

    World* world = nullptr;
    std::vector<GuideNode> path;
    std::vector<int> roomChain;
    em::Vec3 target;
    std::string targetLabel;
    std::string statusText;
    bool shown = false;
    bool targetValid = false;
    bool pathValid = false;
    int cursor = 0;
    int fromRoomCache = -2;
    int targetRoomCache = -2;
    float refreshTimer = 0.0f;
    float remaining = 0.0f;
    float pulseValue = 0.0f;
};

}
