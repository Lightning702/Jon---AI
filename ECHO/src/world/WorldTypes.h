#pragma once

#include "../core/Math.h"
#include "../core/Random.h"
#include "../render/Mesh.h"
#include "../render/Material.h"
#include "Props.h"

namespace echo {

enum RoomType {
    ROOM_CORRIDOR = 0,
    ROOM_WARD,
    ROOM_ICU,
    ROOM_OR,
    ROOM_ER,
    ROOM_RADIOLOGY,
    ROOM_PEDIATRIC,
    ROOM_PSYCH,
    ROOM_MORGUE,
    ROOM_SERVER,
    ROOM_OFFICE,
    ROOM_STORAGE,
    ROOM_BATHROOM,
    ROOM_STAIRWELL,
    ROOM_ELEVATOR,
    ROOM_RECEPTION,
    ROOM_LAUNDRY,
    ROOM_PHARMACY,
    ROOM_CHAPEL,
    ROOM_UTILITY,
    ROOM_VENT,
    ROOM_NURSE_STATION,
    ROOM_TYPE_COUNT
};

const char* roomTypeName(int type);
const char* roomTypeLabel(int type);

struct Rect2 {
    float x = 0, z = 0, w = 0, d = 0;
    float x1() const { return x + w; }
    float z1() const { return z + d; }
    em::Vec2 center() const { return em::Vec2(x + w * 0.5f, z + d * 0.5f); }
    float area() const { return w * d; }
    bool contains(const em::Vec2& p) const { return p.x >= x && p.x <= x1() && p.y >= z && p.y <= z1(); }
    bool overlaps(const Rect2& o) const { return x < o.x1() && x1() > o.x && z < o.z1() && z1() > o.z; }
};

struct Room {
    int id = -1;
    int type = ROOM_CORRIDOR;
    int floor = 0;
    Rect2 rect;
    em::AABB bounds;
    float floorY = 0.0f;
    float ceilY = 3.1f;
    std::vector<int> doors;
    std::vector<int> neighbors;
    std::vector<std::pair<int, int>> portals;
    std::vector<int> lights;
    std::vector<int> props;
    std::vector<int> interactables;
    int meshIndex = -1;
    u32 seed = 0;
    bool visited = false;
    float visitTime = 0.0f;
    int visitCount = 0;
    float lastSeen = -1000.0f;
    std::string label;
    int floorMaterial = MAT_FLOOR_LINO;
    int wallMaterial = MAT_TILE_WALL;
    int ceilMaterial = MAT_CEILING_TILE;
    bool sealed = false;
    bool mutated = false;
    int elevatorShaft = -1;
};

struct ElevatorCab {
    int id = -1;
    int room = -1;
    int floor = 0;
    int shaft = 0;
    int doorId = -1;
    em::Vec3 interior;
    em::Vec3 doorCenter;
    float width = 1.9f;
    float depth = 2.1f;
};

enum DoorKind { DOOR_SINGLE, DOOR_DOUBLE, DOOR_SLIDING, DOOR_ELEVATOR };

struct Door {
    int id = -1;
    int roomA = -1, roomB = -1;
    int floor = 0;
    em::Vec3 hinge;
    em::Vec3 center;
    float yaw = 0.0f;
    float width = 0.95f;
    float height = 2.10f;
    int kind = DOOR_SINGLE;
    int material = MAT_DOOR_GREEN;
    float openAmount = 0.0f;
    float targetOpen = 0.0f;
    float swingSign = 1.0f;
    bool locked = false;
    bool jammed = false;
    bool removed = false;
    bool wasOpened = false;
    bool autoCloses = false;
    int keyId = -1;
    int colliderIndex = -1;
    int meshIndex = -1;
    int interactId = -1;
    float creakTimer = 0.0f;
    float rattleTimer = 0.0f;
};

struct LightFixture {
    int id = -1;
    int room = -1;
    int floor = 0;
    em::Vec3 position;
    em::Vec3 direction = em::Vec3(0, -1, 0);
    em::Vec3 color = em::Vec3(0.86f, 0.92f, 1.0f);
    float intensity = 6.0f;
    float range = 8.5f;
    float innerAngle = 0.45f;
    float outerAngle = 1.25f;
    bool spot = true;
    bool on = true;
    bool broken = false;
    bool switchable = true;
    bool emergency = false;
    float flickerPhase = 0.0f;
    float flickerRate = 0.0f;
    float flickerAmount = 0.0f;
    float currentScale = 1.0f;
    float buzz = 0.0f;
    int propType = PROP_CEILING_LAMP;
    float propYaw = 0.0f;
    int switchId = -1;
    float volumetric = 1.0f;
    bool pendingOn = true;
    bool pendingBroken = false;
    bool hasPending = false;
    bool latchedOff = false;
    bool observed = false;
    float unobservedTime = 0.0f;
};

struct PropInstance {
    int id = -1;
    int type = PROP_BED;
    int room = -1;
    int floor = 0;
    em::Vec3 position;
    float yaw = 0.0f;
    em::Vec3 scale = em::Vec3(1, 1, 1);
    em::Vec4 tint = em::Vec4(1, 1, 1, 1);
    int colliderIndex = -1;
    em::AABB bounds;
    bool movable = false;
    bool hidden = false;
    em::Vec3 originalPosition;
    float originalYaw = 0.0f;
};

enum InteractKind {
    INTERACT_DOOR = 0,
    INTERACT_SWITCH,
    INTERACT_DRAWER,
    INTERACT_CABINET,
    INTERACT_PICKUP,
    INTERACT_DOCUMENT,
    INTERACT_AUDIOLOG,
    INTERACT_KEYPAD,
    INTERACT_ELEVATOR,
    INTERACT_VALVE,
    INTERACT_NOTE,
    INTERACT_BREAKER
};

struct Interactable {
    int id = -1;
    int kind = INTERACT_PICKUP;
    int room = -1;
    int floor = 0;
    em::Vec3 position;
    float yaw = 0.0f;
    float radius = 0.55f;
    int targetId = -1;
    int itemId = -1;
    int contentId = -1;
    int propType = -1;
    int propId = -1;
    bool used = false;
    bool oneShot = false;
    bool hidden = false;
    bool requiresKey = false;
    int keyId = -1;
    std::string prompt;
    std::string lockedPrompt;
};

struct Sector {
    int room = -1;
    em::AABB bounds;
    Ref<Mesh> mesh;
    std::vector<int> transparentSubs;
    bool built = false;
};

struct FloorPlan {
    int index = 0;
    float baseY = 0.0f;
    float height = 3.15f;
    std::string name;
    std::vector<int> rooms;
    Rect2 extent;
};

}
