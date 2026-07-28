#include "World.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

namespace {

struct Interval {
    float a, b;
};

void subtractIntervals(float start, float end, const std::vector<Interval>& gaps, std::vector<Interval>& out) {
    out.clear();
    float cursor = start;
    std::vector<Interval> sorted = gaps;
    std::sort(sorted.begin(), sorted.end(), [](const Interval& x, const Interval& y) { return x.a < y.a; });
    for (const Interval& g : sorted) {
        if (g.b <= cursor) continue;
        if (g.a > cursor) out.push_back({ cursor, std::min(g.a, end) });
        cursor = std::max(cursor, g.b);
        if (cursor >= end) break;
    }
    if (cursor < end) out.push_back({ cursor, end });
}

}

void World::placeLights(int roomId, Rng& rng) {
    Room& room = roomList[(size_t)roomId];
    const FloorPlan& plan = floorList[(size_t)room.floor];
    float ceil = room.ceilY;

    auto addLight = [&](const Vec3& pos, float intensity, float range, const Vec3& color,
                        float inner, float outer, int propType, float propYaw, bool spot) {
        LightFixture l;
        l.id = (int)lightList.size();
        l.room = roomId;
        l.floor = room.floor;
        l.position = pos - Vec3(0, 0.22f, 0);
        l.direction = Vec3(0, -1, 0);
        l.color = color;
        l.intensity = intensity;
        l.range = range;
        l.innerAngle = inner;
        l.outerAngle = outer;
        l.spot = spot;
        l.propType = propType;
        l.propYaw = propYaw;
        l.flickerPhase = rng.range(0.0f, 100.0f);
        l.flickerRate = rng.range(0.6f, 2.4f);

        float roll = rng.nextFloat();
        if (roll > 0.93f) { l.broken = true; l.on = false; }
        else if (roll > 0.80f) l.flickerAmount = rng.range(0.30f, 0.85f);
        else if (roll > 0.58f) l.flickerAmount = rng.range(0.04f, 0.16f);

        if (room.floor == 0) l.color = Vec3(0.95f, 0.86f, 0.66f);
        l.currentScale = l.on && !l.broken ? 1.0f : 0.0f;
        l.buzz = l.flickerAmount;

        lightList.push_back(l);
        room.lights.push_back(l.id);

        if (propType >= 0) {
            PropInstance p;
            p.id = (int)propList.size();
            p.type = propType;
            p.room = roomId;
            p.floor = room.floor;
            p.position = pos;
            p.yaw = propYaw;
            p.originalPosition = p.position;
            p.originalYaw = p.yaw;
            p.bounds = propLib->get(propType).bounds;
            propList.push_back(p);
            room.props.push_back(p.id);
        }
        return l.id;
    };

    Vec2 c = room.rect.center();

    if (room.type == ROOM_CORRIDOR) {
        bool alongX = room.rect.w > room.rect.d;
        float length = alongX ? room.rect.w : room.rect.d;
        int count = std::max(1, (int)(length / 4.2f));
        for (int i = 0; i < count; i++) {
            float t = (i + 0.5f) / count;
            Vec3 pos = alongX ? Vec3(room.rect.x + room.rect.w * t, ceil - 0.12f, c.y)
                              : Vec3(c.x, ceil - 0.12f, room.rect.z + room.rect.d * t);
            addLight(pos, rng.range(24.0f, 30.0f), 12.5f, Vec3(0.80f, 0.90f, 1.0f), 1.02f, 1.53f,
                     PROP_CEILING_LAMP, alongX ? 0.0f : HALF_PI, true);
        }
        if (rng.chance(0.55f)) {
            Vec3 signPos = alongX ? Vec3(room.rect.x + 0.35f, ceil - 0.55f, c.y) : Vec3(c.x, ceil - 0.55f, room.rect.z + 0.35f);
            LightFixture l;
            l.id = (int)lightList.size();
            l.room = roomId;
            l.floor = room.floor;
            l.position = signPos;
            l.direction = Vec3(0, -1, 0);
            l.color = Vec3(0.25f, 1.0f, 0.42f);
            l.intensity = 3.2f;
            l.range = 4.6f;
            l.spot = false;
            l.switchable = false;
            l.emergency = true;
            l.volumetric = 0.55f;
            l.propType = -1;
            l.currentScale = 1.0f;
            lightList.push_back(l);
            room.lights.push_back(l.id);

            PropInstance p;
            p.id = (int)propList.size();
            p.type = PROP_EXIT_SIGN;
            p.room = roomId;
            p.floor = room.floor;
            p.position = signPos;
            p.yaw = alongX ? HALF_PI : 0.0f;
            p.originalPosition = p.position;
            p.originalYaw = p.yaw;
            propList.push_back(p);
            room.props.push_back(p.id);
        }
        return;
    }

    if (room.type == ROOM_OR) {
        addLight(Vec3(c.x, ceil - 0.60f, c.y - 0.6f), 60.0f, 12.0f, Vec3(1.0f, 0.98f, 0.94f), 0.45f, 0.95f, PROP_OR_LAMP, rng.range(0, TAU), true);
        addLight(Vec3(c.x, ceil - 0.12f, c.y + 1.4f), 20.0f, 10.0f, Vec3(0.86f, 0.93f, 1.0f), 1.02f, 1.53f, PROP_CEILING_LAMP, 0.0f, true);
        return;
    }

    if (room.type == ROOM_STAIRWELL) {
        for (int i = 0; i < 2; i++) {
            Vec3 pos(room.rect.x + room.rect.w * (0.3f + i * 0.4f), ceil - 0.35f, room.rect.z + room.rect.d * (0.25f + i * 0.5f));
            addLight(pos, rng.range(16.0f, 22.0f), 10.5f, Vec3(0.92f, 0.88f, 0.78f), 0.95f, 1.48f, PROP_WALL_LAMP, rng.range(0, TAU), true);
        }
        return;
    }

    if (room.type == ROOM_SERVER) {
        addLight(Vec3(c.x, ceil - 0.12f, c.y), 15.0f, 10.0f, Vec3(0.55f, 0.80f, 1.0f), 1.02f, 1.53f, PROP_CEILING_LAMP, 0.0f, true);
        return;
    }

    int lampCount = clampi((int)(room.rect.area() / 13.0f), 2, 6);
    for (int i = 0; i < lampCount; i++) {
        float fx = lampCount == 1 ? 0.5f : (0.28f + 0.44f * (i % 2));
        float fz = lampCount <= 2 ? 0.5f : (0.22f + 0.56f * ((i / 2) % 3) * 0.5f);
        Vec3 pos(room.rect.x + room.rect.w * fx, ceil - 0.12f, room.rect.z + room.rect.d * fz);
        addLight(pos, rng.range(20.0f, 26.0f), 11.5f, Vec3(0.84f, 0.90f, 0.98f), 1.02f, 1.53f, PROP_CEILING_LAMP, rng.chance(0.5f) ? 0.0f : HALF_PI, true);
    }
}

void World::populateRoom(int roomId, PropLibrary& props, Rng& rng) {
    Room& room = roomList[(size_t)roomId];
    const Rect2& r = room.rect;
    float y = room.floorY;

    auto add = [&](int type, const Vec3& pos, float yaw, bool movable = false) {
        PropInstance p;
        p.id = (int)propList.size();
        p.type = type;
        p.room = roomId;
        p.floor = room.floor;
        p.position = pos;
        p.yaw = yaw;
        p.movable = movable;
        p.originalPosition = pos;
        p.originalYaw = yaw;
        p.bounds = props.get(type).bounds;
        propList.push_back(p);
        room.props.push_back(p.id);
        return p.id;
    };

    auto addInteract = [&](int kind, const Vec3& pos, float yaw, int target, const std::string& prompt) {
        Interactable it;
        it.id = (int)interactList.size();
        it.kind = kind;
        it.room = roomId;
        it.floor = room.floor;
        it.position = pos;
        it.yaw = yaw;
        it.targetId = target;
        it.prompt = prompt;
        interactList.push_back(it);
        room.interactables.push_back(it.id);
        return it.id;
    };

    float inset = 0.55f;
    float x0 = r.x + inset, x1 = r.x1() - inset;
    float z0 = r.z + inset, z1 = r.z1() - inset;
    if (x1 <= x0 || z1 <= z0) return;

    switch (room.type) {
    case ROOM_CORRIDOR: {
        bool alongX = r.w > r.d;
        float length = alongX ? r.w : r.d;
        int clutter = (int)(length / 7.0f);
        for (int i = 0; i < clutter; i++) {
            float t = rng.range(0.1f, 0.9f);
            Vec3 pos = alongX ? Vec3(r.x + r.w * t, y, rng.chance(0.5f) ? z0 + 0.1f : z1 - 0.1f)
                              : Vec3(rng.chance(0.5f) ? x0 + 0.1f : x1 - 0.1f, y, r.z + r.d * t);
            float roll = rng.nextFloat();
            if (roll < 0.22f) add(PROP_GURNEY, pos, alongX ? 0.0f : HALF_PI, true);
            else if (roll < 0.38f) add(PROP_TROLLEY, pos, rng.range(0, TAU), true);
            else if (roll < 0.50f) add(PROP_WHEELCHAIR, pos, rng.range(0, TAU), true);
            else if (roll < 0.62f) add(PROP_BENCH, pos, alongX ? 0.0f : HALF_PI);
            else if (roll < 0.74f) add(PROP_BIN, pos, rng.range(0, TAU));
            else if (roll < 0.86f) add(PROP_DEBRIS, pos, rng.range(0, TAU));
            else add(PROP_DEAD_PLANT, pos, rng.range(0, TAU));
        }
        if (rng.chance(0.5f)) {
            float t = rng.range(0.2f, 0.8f);
            Vec3 pos = alongX ? Vec3(r.x + r.w * t, y + 2.5f, r.z + 0.12f) : Vec3(r.x + 0.12f, y + 2.5f, r.z + r.d * t);
            add(PROP_SPEAKER, pos, alongX ? 0.0f : HALF_PI);
        }
        break;
    }
    case ROOM_WARD:
    case ROOM_ICU: {
        int beds = clampi((int)(r.area() / 12.0f), 1, 6);
        bool alongX = r.w > r.d;
        for (int i = 0; i < beds; i++) {
            float t = (i + 0.5f) / beds;
            Vec3 pos = alongX ? Vec3(r.x + r.w * t, y, z0 + 1.1f) : Vec3(x0 + 1.1f, y, r.z + r.d * t);
            float yaw = alongX ? 0.0f : HALF_PI;
            add(PROP_BED, pos, yaw, true);
            if (rng.chance(0.72f)) add(PROP_IV_STAND, pos + Vec3(alongX ? 0.75f : 0.0f, 0, alongX ? 0.0f : 0.75f), rng.range(0, TAU), true);
            if (room.type == ROOM_ICU && rng.chance(0.65f)) add(PROP_MONITOR_CART, pos + Vec3(alongX ? -0.8f : 0.0f, 0, alongX ? 0.0f : -0.8f), yaw, true);
            if (rng.chance(0.45f)) add(PROP_CURTAIN, Vec3(pos.x, y + 2.30f, pos.z + (alongX ? 0.95f : 0.0f)), yaw + HALF_PI);
        }
        if (rng.chance(0.7f)) add(PROP_CABINET, Vec3(x1 - 0.3f, y, z1 - 0.3f), -HALF_PI);
        if (rng.chance(0.5f)) add(PROP_SINK, Vec3(x0 + 0.3f, y, z1 - 0.3f), 0.0f);
        break;
    }
    case ROOM_OR: {
        Vec2 c = r.center();
        add(PROP_OR_TABLE, Vec3(c.x, y, c.y), rng.chance(0.5f) ? 0.0f : HALF_PI);
        add(PROP_TROLLEY, Vec3(c.x + 1.4f, y, c.y - 0.6f), rng.range(0, TAU), true);
        add(PROP_MONITOR_CART, Vec3(c.x - 1.5f, y, c.y + 0.5f), rng.range(0, TAU), true);
        add(PROP_CABINET, Vec3(x1 - 0.3f, y, z0 + 1.0f), -HALF_PI);
        add(PROP_SINK, Vec3(x0 + 0.35f, y, z1 - 0.8f), 0.0f);
        if (rng.chance(0.6f)) add(PROP_DEFIBRILLATOR, Vec3(x0 + 0.8f, y + 0.75f, z0 + 0.5f), 0.0f);
        break;
    }
    case ROOM_ER: {
        int bays = clampi((int)(r.w / 3.2f), 1, 4);
        for (int i = 0; i < bays; i++) {
            float t = (i + 0.5f) / bays;
            Vec3 pos(r.x + r.w * t, y, z0 + 1.2f);
            add(PROP_GURNEY, pos, 0.0f, true);
            add(PROP_CURTAIN, Vec3(pos.x - 1.1f, y + 2.30f, pos.z), HALF_PI);
            if (rng.chance(0.6f)) add(PROP_MONITOR_CART, pos + Vec3(0.9f, 0, -0.4f), 0.0f, true);
        }
        add(PROP_DESK, Vec3(x1 - 1.2f, y, z1 - 0.8f), PI);
        add(PROP_CHAIR, Vec3(x1 - 1.2f, y, z1 - 1.6f), 0.0f, true);
        break;
    }
    case ROOM_RADIOLOGY: {
        Vec2 c = r.center();
        add(PROP_XRAY_MACHINE, Vec3(c.x, y, c.y + 0.5f), rng.chance(0.5f) ? 0.0f : PI);
        add(PROP_DESK, Vec3(x0 + 1.0f, y, z0 + 0.7f), 0.0f);
        add(PROP_CHAIR, Vec3(x0 + 1.0f, y, z0 + 1.5f), PI, true);
        add(PROP_SHELF, Vec3(x1 - 0.4f, y, z1 - 1.5f), -HALF_PI);
        break;
    }
    case ROOM_PEDIATRIC: {
        int cribs = clampi((int)(r.area() / 10.0f), 2, 6);
        for (int i = 0; i < cribs; i++) {
            float fx = 0.2f + 0.6f * ((i % 3) / 2.0f);
            float fz = 0.25f + 0.5f * (i / 3);
            add(PROP_CRIB, Vec3(r.x + r.w * fx, y, r.z + r.d * fz), rng.chance(0.5f) ? 0.0f : HALF_PI, true);
        }
        if (rng.chance(0.6f)) add(PROP_TV, Vec3(x1 - 0.4f, y + 1.9f, r.center().y), -HALF_PI);
        add(PROP_DEBRIS, Vec3(rng.range(x0, x1), y, rng.range(z0, z1)), rng.range(0, TAU));
        break;
    }
    case ROOM_PSYCH: {
        add(PROP_BED, Vec3(x0 + 1.0f, y, r.center().y), HALF_PI, true);
        add(PROP_CHAIR, Vec3(x1 - 1.0f, y, z0 + 1.0f), rng.range(0, TAU), true);
        if (rng.chance(0.7f)) add(PROP_NOTICE_BOARD, Vec3(r.center().x, y + 1.55f, z0 + 0.14f), 0.0f);
        add(PROP_PAPER_PILE, Vec3(rng.range(x0, x1), y, rng.range(z0, z1)), rng.range(0, TAU));
        break;
    }
    case ROOM_MORGUE: {
        int walls = clampi((int)(r.w / 2.6f), 1, 4);
        for (int i = 0; i < walls; i++) {
            float t = (i + 0.5f) / walls;
            add(PROP_MORGUE_WALL, Vec3(r.x + r.w * t, y, z0 - 0.1f), 0.0f);
        }
        add(PROP_STRETCHER, Vec3(r.center().x, y, r.center().y + 1.0f), 0.0f, true);
        add(PROP_SINK, Vec3(x1 - 0.4f, y, z1 - 0.6f), -HALF_PI);
        add(PROP_TROLLEY, Vec3(x0 + 0.9f, y, z1 - 1.0f), rng.range(0, TAU), true);
        break;
    }
    case ROOM_SERVER: {
        int racks = clampi((int)(r.w / 1.1f), 2, 8);
        for (int i = 0; i < racks; i++) {
            float t = (i + 0.5f) / racks;
            add(PROP_SERVER_RACK, Vec3(r.x + r.w * t, y, z0 + 0.9f), 0.0f);
        }
        add(PROP_DESK, Vec3(x1 - 1.0f, y, z1 - 0.8f), PI);
        break;
    }
    case ROOM_OFFICE: {
        add(PROP_DESK, Vec3(r.center().x, y, z0 + 1.0f), 0.0f);
        add(PROP_CHAIR, Vec3(r.center().x, y, z0 + 1.9f), PI, true);
        add(PROP_FILE_CABINET, Vec3(x1 - 0.4f, y, z0 + 0.8f), -HALF_PI);
        if (rng.chance(0.6f)) add(PROP_FILE_CABINET, Vec3(x1 - 0.4f, y, z0 + 1.7f), -HALF_PI);
        add(PROP_PAPER_PILE, Vec3(r.center().x + rng.range(-0.3f, 0.3f), y + 0.76f, z0 + 1.0f), rng.range(0, TAU));
        if (rng.chance(0.5f)) add(PROP_NOTICE_BOARD, Vec3(r.center().x, y + 1.6f, z0 + 0.14f), 0.0f);
        break;
    }
    case ROOM_STORAGE: {
        int shelves = clampi((int)(r.d / 1.6f), 1, 5);
        for (int i = 0; i < shelves; i++) {
            float t = (i + 0.5f) / shelves;
            add(PROP_SHELF, Vec3(x0 + 0.6f, y, r.z + r.d * t), HALF_PI);
            if (rng.chance(0.7f)) add(PROP_SHELF, Vec3(x1 - 0.6f, y, r.z + r.d * t), -HALF_PI);
        }
        for (int i = 0; i < 4; i++) add(PROP_BOX, Vec3(rng.range(x0, x1), y, rng.range(z0, z1)), rng.range(0, TAU), true);
        break;
    }
    case ROOM_BATHROOM: {
        int stalls = clampi((int)(r.w / 1.2f), 1, 4);
        for (int i = 0; i < stalls; i++) {
            float t = (i + 0.5f) / stalls;
            add(PROP_TOILET, Vec3(r.x + r.w * t, y, z0 + 0.5f), 0.0f);
        }
        add(PROP_SINK, Vec3(r.center().x - 0.5f, y, z1 - 0.35f), PI);
        add(PROP_SINK, Vec3(r.center().x + 0.5f, y, z1 - 0.35f), PI);
        add(PROP_MIRROR, Vec3(r.center().x, y + 1.55f, z1 - 0.10f), PI);
        break;
    }
    case ROOM_LAUNDRY:
    case ROOM_UTILITY: {
        add(PROP_PIPES, Vec3(x0 + 0.5f, y + 2.4f, r.center().y), rng.chance(0.5f) ? 0.0f : HALF_PI);
        add(PROP_SHELF, Vec3(x1 - 0.6f, y, r.center().y), -HALF_PI);
        for (int i = 0; i < 3; i++) add(PROP_BOX, Vec3(rng.range(x0, x1), y, rng.range(z0, z1)), rng.range(0, TAU), true);
        add(PROP_DEBRIS, Vec3(rng.range(x0, x1), y, rng.range(z0, z1)), rng.range(0, TAU));
        break;
    }
    case ROOM_PHARMACY: {
        int shelves = clampi((int)(r.w / 1.4f), 1, 4);
        for (int i = 0; i < shelves; i++) add(PROP_SHELF, Vec3(r.x + r.w * (i + 0.5f) / shelves, y, z0 + 0.5f), 0.0f);
        add(PROP_CABINET, Vec3(x1 - 0.35f, y, z1 - 1.0f), -HALF_PI);
        break;
    }
    case ROOM_RECEPTION: {
        add(PROP_DESK, Vec3(r.center().x, y, r.center().y), rng.chance(0.5f) ? 0.0f : PI);
        add(PROP_CHAIR, Vec3(r.center().x, y, r.center().y + 0.9f), 0.0f, true);
        for (int i = 0; i < 3; i++) add(PROP_BENCH, Vec3(x0 + 1.2f, y, r.z + r.d * (0.25f + i * 0.25f)), HALF_PI);
        add(PROP_VENDING, Vec3(x1 - 0.5f, y, z0 + 1.0f), -HALF_PI);
        add(PROP_CLOCK, Vec3(r.center().x, y + 2.4f, z0 + 0.14f), 0.0f);
        break;
    }
    case ROOM_CHAPEL: {
        for (int i = 0; i < 5; i++) add(PROP_BENCH, Vec3(r.center().x, y, r.z + 1.2f + i * 1.1f), 0.0f);
        add(PROP_TABLE, Vec3(r.center().x, y, z1 - 0.8f), 0.0f);
        break;
    }
    case ROOM_NURSE_STATION: {
        add(PROP_DESK, Vec3(r.center().x, y, r.center().y), 0.0f);
        add(PROP_DESK, Vec3(r.center().x + 1.45f, y, r.center().y), 0.0f);
        add(PROP_STOOL, Vec3(r.center().x, y, r.center().y + 0.9f), 0.0f, true);
        add(PROP_FILE_CABINET, Vec3(x1 - 0.4f, y, z0 + 0.8f), -HALF_PI);
        add(PROP_NOTICE_BOARD, Vec3(r.center().x, y + 1.6f, z0 + 0.14f), 0.0f);
        break;
    }
    default:
        break;
    }

    if (room.type != ROOM_CORRIDOR && room.type != ROOM_STAIRWELL && room.type != ROOM_ELEVATOR) {
        if (rng.chance(0.45f)) add(PROP_RADIATOR, Vec3(rng.range(x0 + 0.6f, x1 - 0.6f), y, r.z + 0.16f), 0.0f);
        if (rng.chance(0.35f)) add(PROP_DEBRIS, Vec3(rng.range(x0, x1), y, rng.range(z0, z1)), rng.range(0, TAU));
        if (rng.chance(0.30f)) add(PROP_PAPER_PILE, Vec3(rng.range(x0, x1), y, rng.range(z0, z1)), rng.range(0, TAU));
    }

    resolveProps(roomId, props, rng);

    for (int doorId : room.doors) {
        const Door& d = doorList[(size_t)doorId];
        if (d.kind == DOOR_ELEVATOR) continue;
        Vec3 toRoom = normalize(Vec3(r.center().x, 0, r.center().y) - Vec3(d.center.x, 0, d.center.z));
        Vec3 side = Vec3(std::cos(d.yaw), 0, -std::sin(d.yaw));
        Vec3 switchPos = d.center + side * (d.width * 0.5f + 0.28f) + toRoom * 0.09f + Vec3(0, 1.18f, 0);
        int sw = -1;
        if (!room.lights.empty()) {
            PropInstance p;
            p.id = (int)propList.size();
            p.type = PROP_LIGHT_SWITCH;
            p.room = roomId;
            p.floor = room.floor;
            p.position = switchPos;
            p.yaw = d.yaw + (dot(toRoom, Vec3(-std::sin(d.yaw), 0, -std::cos(d.yaw))) > 0 ? PI : 0.0f);
            p.originalPosition = p.position;
            p.originalYaw = p.yaw;
            propList.push_back(p);
            room.props.push_back(p.id);
            sw = addInteract(INTERACT_SWITCH, switchPos, p.yaw, roomId, "Lichtschalter");
        }
        break;
    }
}

void World::resolveProps(int roomId, PropLibrary& props, Rng& rng) {
    Room& room = roomList[(size_t)roomId];
    const float margin = config.wallThickness + 0.05f;

    auto footprint = [&](const PropInstance& p, float& ex, float& ez) {
        Vec3 h = props.get(p.type).colliderHalf * p.scale;
        float c = std::fabs(std::cos(p.yaw));
        float s = std::fabs(std::sin(p.yaw));
        ex = h.x * c + h.z * s;
        ez = h.x * s + h.z * c;
    };

    std::vector<int> placed;

    for (int id : room.props) {
        if (id < 0 || id >= (int)propList.size()) continue;
        PropInstance& p = propList[(size_t)id];
        const PropMesh& pm = props.get(p.type);
        if (!pm.solid) continue;
        if (p.position.y > room.floorY + 0.30f) continue;

        float ex, ez;
        footprint(p, ex, ez);

        float minX = room.rect.x + margin + ex;
        float maxX = room.rect.x1() - margin - ex;
        float minZ = room.rect.z + margin + ez;
        float maxZ = room.rect.z1() - margin - ez;

        if (maxX < minX || maxZ < minZ) {
            p.hidden = true;
            continue;
        }

        p.position.y = room.floorY;
        p.position.x = clampf(p.position.x, minX, maxX);
        p.position.z = clampf(p.position.z, minZ, maxZ);

        bool ok = false;
        for (int attempt = 0; attempt < 10 && !ok; attempt++) {
            ok = true;
            for (int other : placed) {
                const PropInstance& q = propList[(size_t)other];
                float qx, qz;
                footprint(q, qx, qz);
                float dx = std::fabs(p.position.x - q.position.x);
                float dz = std::fabs(p.position.z - q.position.z);
                if (dx < ex + qx - 0.03f && dz < ez + qz - 0.03f) { ok = false; break; }
            }
            if (ok) {
                for (int doorId : room.doors) {
                    const Door& d = doorList[(size_t)doorId];
                    float dx = std::fabs(p.position.x - d.center.x);
                    float dz = std::fabs(p.position.z - d.center.z);
                    if (dx < ex + d.width * 0.5f + 0.55f && dz < ez + d.width * 0.5f + 0.55f) { ok = false; break; }
                }
            }
            if (!ok) {
                p.position.x = clampf(rng.range(minX, maxX), minX, maxX);
                p.position.z = clampf(rng.range(minZ, maxZ), minZ, maxZ);
            }
        }

        if (!ok) {
            p.hidden = true;
            continue;
        }

        p.originalPosition = p.position;
        p.originalYaw = p.yaw;
        placed.push_back(id);
    }
}

void World::buildSectorMesh(int roomId, PropLibrary& props, Rng& rng) {
    Room& room = roomList[(size_t)roomId];
    const Rect2& r = room.rect;
    const float t = config.wallThickness * 0.5f;
    const float y0 = room.floorY;
    const float y1 = room.ceilY;
    const float h = y1 - y0;
    const bool isStair = room.type == ROOM_STAIRWELL;
    const bool topFloor = room.floor == config.floors - 1;
    const bool bottomFloor = room.floor == 0;

    MeshBuilder mb;
    Sector& sector = sectors[(size_t)roomId];
    sector.room = roomId;
    sector.bounds = room.bounds;

    Rect2 opening = { 0, 0, 0, 0 };
    bool hasOpening = false;
    if (isStair) {
        float wallIn = config.wallThickness + 0.05f;
        float shaftW = clampf(r.w * 0.30f, 1.30f, 1.90f);
        float landing = 1.30f;
        if (r.d - landing * 2.0f < 3.0f) landing = std::max((r.d - 3.0f) * 0.5f, 0.60f);
        float shaftD = std::max(r.d - landing * 2.0f, 2.2f);
        opening = { r.x + wallIn, r.z + landing, shaftW, shaftD };
        hasOpening = true;
    }

    mb.setMaterial(room.floorMaterial);
    if (!isStair || bottomFloor) {
        mb.addPlane(Vec3(r.center().x, y0, r.center().y), Vec2(r.w, r.d), Vec3(0, 1, 0), std::max(1, (int)(std::max(r.w, r.d) / 6.0f)));
    } else {
        float ox0 = opening.x, ox1 = opening.x1(), oz0 = opening.z, oz1 = opening.z1();
        auto slab = [&](float ax, float az, float bx, float bz) {
            if (bx - ax < 0.05f || bz - az < 0.05f) return;
            mb.addPlane(Vec3((ax + bx) * 0.5f, y0, (az + bz) * 0.5f), Vec2(bx - ax, bz - az), Vec3(0, 1, 0), 1);
        };
        slab(r.x, r.z, r.x1(), oz0);
        slab(r.x, oz1, r.x1(), r.z1());
        slab(r.x, oz0, ox0, oz1);
        slab(ox1, oz0, r.x1(), oz1);
    }
    mb.finishSubMesh();

    if (!isStair || topFloor) {
        mb.setMaterial(room.ceilMaterial);
        mb.addPlane(Vec3(r.center().x, y1, r.center().y), Vec2(r.w, r.d), Vec3(0, -1, 0), std::max(1, (int)(std::max(r.w, r.d) / 6.0f)));
        mb.finishSubMesh();
    }

    auto addSlabCollider = [&](float ax, float az, float bx, float bz, float cy) {
        if (bx - ax < 0.04f || bz - az < 0.04f) return;
        Collider c;
        c.center = Vec3((ax + bx) * 0.5f, cy, (az + bz) * 0.5f);
        c.half = Vec3((bx - ax) * 0.5f, 0.16f, (bz - az) * 0.5f);
        c.flags = COL_STATIC;
        phys.addCollider(c);
    };

    if (!isStair || bottomFloor) {
        addSlabCollider(r.x, r.z, r.x1(), r.z1(), y0 - 0.16f);
    } else {
        addSlabCollider(r.x, r.z, r.x1(), opening.z, y0 - 0.16f);
        addSlabCollider(r.x, opening.z1(), r.x1(), r.z1(), y0 - 0.16f);
        addSlabCollider(r.x, opening.z, opening.x, opening.z1(), y0 - 0.16f);
        addSlabCollider(opening.x1(), opening.z, r.x1(), opening.z1(), y0 - 0.16f);
    }

    if (!isStair || topFloor) {
        addSlabCollider(r.x, r.z, r.x1(), r.z1(), y1 + 0.16f);
    } else {
        addSlabCollider(r.x, r.z, r.x1(), opening.z, y1 + 0.16f);
        addSlabCollider(r.x, opening.z1(), r.x1(), r.z1(), y1 + 0.16f);
        addSlabCollider(r.x, opening.z, opening.x, opening.z1(), y1 + 0.16f);
        addSlabCollider(opening.x1(), opening.z, r.x1(), opening.z1(), y1 + 0.16f);
    }

    mb.setMaterial(room.wallMaterial);

    struct SideDef {
        int axis;
        float fixed;
        float inward;
        float start, end;
    };
    SideDef sides[4] = {
        { 0, r.x, 1.0f, r.z, r.z1() },
        { 0, r.x1(), -1.0f, r.z, r.z1() },
        { 1, r.z, 1.0f, r.x, r.x1() },
        { 1, r.z1(), -1.0f, r.x, r.x1() }
    };

    std::vector<Interval> gaps;
    std::vector<Interval> segs;
    std::vector<std::pair<Interval, float>> doorGaps;

    for (int s = 0; s < 4; s++) {
        const SideDef& sd = sides[s];
        gaps.clear();
        doorGaps.clear();

        for (int doorId : room.doors) {
            const Door& d = doorList[(size_t)doorId];
            if (d.removed) continue;
            float dFixed = sd.axis == 0 ? d.center.x : d.center.z;
            float dAlong = sd.axis == 0 ? d.center.z : d.center.x;
            if (std::fabs(dFixed - sd.fixed) > 0.12f) continue;
            if (dAlong < sd.start - 0.1f || dAlong > sd.end + 0.1f) continue;
            float hw = d.width * 0.5f;
            gaps.push_back({ dAlong - hw, dAlong + hw });
            doorGaps.push_back({ { dAlong - hw, dAlong + hw }, d.height });
        }

        bool exterior = std::fabs(sd.fixed) < 0.01f || std::fabs(sd.fixed - config.floorWidth) < 0.01f ||
                        (sd.axis == 1 && (std::fabs(sd.fixed) < 0.01f || std::fabs(sd.fixed - config.floorDepth) < 0.01f));
        bool windowWall = exterior && room.type != ROOM_STAIRWELL && room.type != ROOM_MORGUE &&
                          room.type != ROOM_SERVER && room.floor > 0 && (sd.end - sd.start) > 3.0f;

        std::vector<std::pair<float, float>> windows;
        if (windowWall && rng.chance(0.75f)) {
            int count = clampi((int)((sd.end - sd.start) / 2.6f), 1, 3);
            for (int i = 0; i < count; i++) {
                float center = sd.start + (sd.end - sd.start) * (i + 0.5f) / count;
                windows.push_back({ center, 0.78f });
            }
        }

        subtractIntervals(sd.start, sd.end, gaps, segs);

        for (const Interval& iv : segs) {
            float len = iv.b - iv.a;
            if (len < 0.02f) continue;
            float mid = (iv.a + iv.b) * 0.5f;

            std::vector<Interval> winGaps;
            for (auto& w : windows) {
                if (w.first - w.second > iv.a && w.first + w.second < iv.b) winGaps.push_back({ w.first - w.second, w.first + w.second });
            }

            std::vector<Interval> subSegs;
            subtractIntervals(iv.a, iv.b, winGaps, subSegs);

            auto emitWall = [&](float a, float b, float yLo, float yHi) {
                if (b - a < 0.02f || yHi - yLo < 0.02f) return;
                float m = (a + b) * 0.5f;
                Vec3 center, half;
                if (sd.axis == 0) {
                    center = Vec3(sd.fixed + sd.inward * t, (yLo + yHi) * 0.5f, m);
                    half = Vec3(t, (yHi - yLo) * 0.5f, (b - a) * 0.5f);
                } else {
                    center = Vec3(m, (yLo + yHi) * 0.5f, sd.fixed + sd.inward * t);
                    half = Vec3((b - a) * 0.5f, (yHi - yLo) * 0.5f, t);
                }
                mb.addBox(center, half);
                Collider c;
                c.center = center;
                c.half = half + Vec3(0.005f);
                c.flags = COL_STATIC | COL_BLOCKS_SIGHT;
                phys.addCollider(c);
            };

            for (const Interval& sub : subSegs) emitWall(sub.a, sub.b, y0, y1);
            for (const Interval& w : winGaps) {
                emitWall(w.a, w.b, y0, y0 + 0.95f);
                emitWall(w.a, w.b, y0 + 2.72f, y1);
            }
        }

        for (auto& dg : doorGaps) {
            float a = dg.first.a, b = dg.first.b;
            float lintelLo = y0 + dg.second;
            if (lintelLo < y1 - 0.02f) {
                float m = (a + b) * 0.5f;
                Vec3 center, half;
                if (sd.axis == 0) {
                    center = Vec3(sd.fixed + sd.inward * t, (lintelLo + y1) * 0.5f, m);
                    half = Vec3(t, (y1 - lintelLo) * 0.5f, (b - a) * 0.5f);
                } else {
                    center = Vec3(m, (lintelLo + y1) * 0.5f, sd.fixed + sd.inward * t);
                    half = Vec3((b - a) * 0.5f, (y1 - lintelLo) * 0.5f, t);
                }
                mb.addBox(center, half);
                Collider c;
                c.center = center;
                c.half = half + Vec3(0.005f);
                c.flags = COL_STATIC | COL_BLOCKS_SIGHT;
                phys.addCollider(c);
            }
        }

        for (auto& w : windows) {
            Vec3 pos;
            float yaw;
            if (sd.axis == 0) {
                pos = Vec3(sd.fixed + sd.inward * t, y0 + 1.84f, w.first);
                yaw = HALF_PI;
            } else {
                pos = Vec3(w.first, y0 + 1.84f, sd.fixed + sd.inward * t);
                yaw = 0.0f;
            }
            PropInstance p;
            p.id = (int)propList.size();
            p.type = PROP_WINDOW;
            p.room = roomId;
            p.floor = room.floor;
            p.position = pos;
            p.yaw = yaw;
            p.scale = Vec3(w.second / 0.72f, 0.94f, 1.0f);
            p.originalPosition = pos;
            p.originalYaw = yaw;
            propList.push_back(p);
            room.props.push_back(p.id);
        }
    }
    mb.finishSubMesh();

    if (room.type != ROOM_STAIRWELL) {
        mb.setMaterial(MAT_RUBBER);
        float sb = 0.11f;
        for (int s = 0; s < 4; s++) {
            const SideDef& sd = sides[s];
            gaps.clear();
            for (int doorId : room.doors) {
                const Door& d = doorList[(size_t)doorId];
                float dFixed = sd.axis == 0 ? d.center.x : d.center.z;
                float dAlong = sd.axis == 0 ? d.center.z : d.center.x;
                if (std::fabs(dFixed - sd.fixed) > 0.12f) continue;
                gaps.push_back({ dAlong - d.width * 0.5f, dAlong + d.width * 0.5f });
            }
            subtractIntervals(sd.start, sd.end, gaps, segs);
            for (const Interval& iv : segs) {
                if (iv.b - iv.a < 0.05f) continue;
                float m = (iv.a + iv.b) * 0.5f;
                if (sd.axis == 0)
                    mb.addBox(Vec3(sd.fixed + sd.inward * (t + 0.012f), y0 + sb, m), Vec3(0.014f, sb, (iv.b - iv.a) * 0.5f));
                else
                    mb.addBox(Vec3(m, y0 + sb, sd.fixed + sd.inward * (t + 0.012f)), Vec3((iv.b - iv.a) * 0.5f, sb, 0.014f));
            }
        }
        mb.finishSubMesh();
    }

    mb.setMaterial(MAT_DOOR_METAL);
    for (int doorId : room.doors) {
        const Door& d = doorList[(size_t)doorId];
        if (d.removed) continue;

        Vec3 along(std::cos(d.yaw), 0, -std::sin(d.yaw));
        Vec3 normal(-std::sin(d.yaw), 0, -std::cos(d.yaw));
        Vec3 toRoom = Vec3(r.center().x, 0, r.center().y) - Vec3(d.center.x, 0, d.center.z);
        float inward = dot(toRoom, normal) >= 0.0f ? 1.0f : -1.0f;

        bool alongX = std::fabs(along.x) > 0.5f;
        float hw = d.width * 0.5f;
        float jamb = 0.055f;
        Vec3 base = d.center + normal * (inward * t);

        Vec3 jambHalf = alongX ? Vec3(jamb, d.height * 0.5f, t * 1.05f) : Vec3(t * 1.05f, d.height * 0.5f, jamb);
        Vec3 lintelHalf = alongX ? Vec3(hw + jamb * 2.0f, jamb, t * 1.05f) : Vec3(t * 1.05f, jamb, hw + jamb * 2.0f);

        mb.addBox(base + along * (hw + jamb) + Vec3(0, d.height * 0.5f, 0), jambHalf);
        mb.addBox(base - along * (hw + jamb) + Vec3(0, d.height * 0.5f, 0), jambHalf);
        mb.addBox(base + Vec3(0, d.height + jamb, 0), lintelHalf);
    }
    mb.finishSubMesh();

    if (isStair) {
        mb.setMaterial(MAT_CONCRETE_FLOOR);
        if (!topFloor) {
            const int steps = 18;
            float totalRise = config.ceilingHeight * 1.18f;
            float rise = totalRise / steps;
            float arrival = clampf(opening.d * 0.24f, 1.15f, 1.60f);
            float flightLen = std::max(opening.d - arrival, 2.0f);
            float run = flightLen / steps;
            float cxStair = opening.x + opening.w * 0.5f;
            float halfW = opening.w * 0.5f - 0.05f;
            float startZ = opening.z;

            auto solid = [&](const Vec3& center, const Vec3& half) {
                mb.addBox(center, half);
                Collider col;
                col.center = center;
                col.half = half;
                col.flags = COL_STATIC;
                phys.addCollider(col);
            };

            for (int i = 0; i < steps; i++) {
                float topY = y0 + rise * (i + 1);
                float zc = startZ + run * (i + 0.5f);
                solid(Vec3(cxStair, (y0 - 0.2f + topY) * 0.5f, zc),
                      Vec3(halfW, (topY - y0 + 0.2f) * 0.5f, run * 0.5f));
            }

            float landZ0 = startZ + run * steps;
            float landZ1 = opening.z1();
            if (landZ1 > landZ0 + 0.06f) {
                float topY = y0 + totalRise;
                solid(Vec3(cxStair, topY - 0.20f, (landZ0 + landZ1) * 0.5f),
                      Vec3(halfW, 0.20f, (landZ1 - landZ0) * 0.5f));
            }
            mb.finishSubMesh();

            mb.setMaterial(MAT_METAL_RUST);
            for (int i = 0; i <= steps; i += 3) {
                float sz = startZ + run * i;
                float sy = y0 + rise * i;
                mb.addBox(Vec3(cxStair + halfW, sy + 0.52f, sz), Vec3(0.022f, 0.52f, 0.022f));
            }
            for (int i = 0; i < steps; i += 2) {
                float sz = startZ + run * (i + 1);
                float sy = y0 + rise * (i + 1) + 1.02f;
                mb.addBox(Vec3(cxStair + halfW, sy, sz), Vec3(0.020f, 0.020f, run * 1.1f));
            }
            mb.finishSubMesh();
        } else {
            mb.finishSubMesh();
        }

        if (!bottomFloor) {
            mb.setMaterial(MAT_METAL_RUST);
            float ry = y0 + 0.55f;
            mb.addBox(Vec3(opening.x1() + 0.05f, ry, opening.center().y), Vec3(0.05f, 0.55f, opening.d * 0.5f));
            mb.finishSubMesh();

            Collider rail;
            rail.flags = COL_STATIC;
            rail.half = Vec3(0.07f, 0.55f, opening.d * 0.5f);
            rail.center = Vec3(opening.x1() + 0.05f, ry, opening.center().y);
            phys.addCollider(rail);
        }
    }

    if (room.type == ROOM_ELEVATOR && room.elevatorShaft >= 0) {
        float cabW = 2.10f;
        float cabD = 2.20f;
        float cabH = 2.32f;
        float cx = r.center().x;
        float backZ = r.z1() - t * 2.0f;
        float frontZ = backZ - cabD;

        mb.setMaterial(MAT_MORGUE_STEEL);
        mb.addBox(Vec3(cx - cabW * 0.5f - 0.06f, y0 + cabH * 0.5f, (frontZ + backZ) * 0.5f),
                  Vec3(0.06f, cabH * 0.5f, cabD * 0.5f));
        mb.addBox(Vec3(cx + cabW * 0.5f + 0.06f, y0 + cabH * 0.5f, (frontZ + backZ) * 0.5f),
                  Vec3(0.06f, cabH * 0.5f, cabD * 0.5f));
        mb.addBox(Vec3(cx, y0 + cabH * 0.5f, backZ + 0.05f), Vec3(cabW * 0.5f + 0.12f, cabH * 0.5f, 0.06f));
        mb.addBox(Vec3(cx, y0 + cabH + 0.05f, (frontZ + backZ) * 0.5f), Vec3(cabW * 0.5f + 0.12f, 0.05f, cabD * 0.5f));
        mb.addBox(Vec3(cx, y0 + cabH + 0.05f + (y1 - y0 - cabH) * 0.5f, frontZ - 0.06f),
                  Vec3(cabW * 0.5f + 0.12f, (y1 - y0 - cabH) * 0.5f, 0.06f));
        mb.addBox(Vec3(cx - cabW * 0.5f - 0.30f, y0 + cabH * 0.5f, frontZ - 0.06f), Vec3(0.30f, cabH * 0.5f, 0.06f));
        mb.addBox(Vec3(cx + cabW * 0.5f + 0.30f, y0 + cabH * 0.5f, frontZ - 0.06f), Vec3(0.30f, cabH * 0.5f, 0.06f));
        mb.finishSubMesh();

        mb.setMaterial(MAT_STEEL);
        mb.addBox(Vec3(cx, y0 + 0.012f, (frontZ + backZ) * 0.5f), Vec3(cabW * 0.5f, 0.012f, cabD * 0.5f));
        mb.addBox(Vec3(cx + cabW * 0.5f - 0.14f, y0 + 1.05f, backZ - 0.08f), Vec3(0.10f, 0.22f, 0.03f));
        mb.finishSubMesh();

        mb.setMaterial(MAT_LIGHT_PANEL);
        mb.addBox(Vec3(cx, y0 + cabH - 0.03f, (frontZ + backZ) * 0.5f), Vec3(0.42f, 0.03f, 0.30f));
        mb.finishSubMesh();

        auto wallCol = [&](const Vec3& c, const Vec3& hf) {
            Collider col;
            col.center = c;
            col.half = hf;
            col.flags = COL_STATIC | COL_BLOCKS_SIGHT;
            phys.addCollider(col);
        };
        wallCol(Vec3(cx - cabW * 0.5f - 0.06f, y0 + cabH * 0.5f, (frontZ + backZ) * 0.5f), Vec3(0.08f, cabH * 0.5f, cabD * 0.5f));
        wallCol(Vec3(cx + cabW * 0.5f + 0.06f, y0 + cabH * 0.5f, (frontZ + backZ) * 0.5f), Vec3(0.08f, cabH * 0.5f, cabD * 0.5f));
        wallCol(Vec3(cx, y0 + cabH * 0.5f, backZ + 0.05f), Vec3(cabW * 0.5f + 0.14f, cabH * 0.5f, 0.08f));
        wallCol(Vec3(cx, y0 + cabH + 0.06f, (frontZ + backZ) * 0.5f), Vec3(cabW * 0.5f + 0.14f, 0.08f, cabD * 0.5f));
        wallCol(Vec3(cx - cabW * 0.5f - 0.30f, y0 + cabH * 0.5f, frontZ - 0.06f), Vec3(0.30f, cabH * 0.5f, 0.08f));
        wallCol(Vec3(cx + cabW * 0.5f + 0.30f, y0 + cabH * 0.5f, frontZ - 0.06f), Vec3(0.30f, cabH * 0.5f, 0.08f));

        LightFixture cabLight;
        cabLight.id = (int)lightList.size();
        cabLight.room = roomId;
        cabLight.floor = room.floor;
        cabLight.position = Vec3(cx, y0 + cabH - 0.16f, (frontZ + backZ) * 0.5f);
        cabLight.direction = Vec3(0, -1, 0);
        cabLight.color = Vec3(0.94f, 0.92f, 0.84f);
        cabLight.intensity = 6.5f;
        cabLight.range = 4.2f;
        cabLight.innerAngle = 1.00f;
        cabLight.outerAngle = 1.50f;
        cabLight.spot = true;
        cabLight.switchable = false;
        cabLight.flickerAmount = 0.10f;
        cabLight.flickerRate = 1.4f;
        cabLight.flickerPhase = (float)roomId * 3.7f;
        cabLight.currentScale = 1.0f;
        cabLight.propType = -1;
        lightList.push_back(cabLight);
        room.lights.push_back(cabLight.id);

        Door liftDoor;
        liftDoor.id = (int)doorList.size();
        liftDoor.roomA = roomId;
        liftDoor.roomB = roomId;
        liftDoor.floor = room.floor;
        liftDoor.center = Vec3(cx, y0, frontZ);
        liftDoor.yaw = 0.0f;
        liftDoor.width = cabW;
        liftDoor.height = cabH - 0.10f;
        liftDoor.kind = DOOR_ELEVATOR;
        liftDoor.material = MAT_MORGUE_STEEL;
        liftDoor.openAmount = 1.0f;
        liftDoor.targetOpen = 1.0f;
        liftDoor.locked = false;
        doorList.push_back(liftDoor);
        room.doors.push_back(liftDoor.id);

        ElevatorCab cab;
        cab.id = (int)cabList.size();
        cab.room = roomId;
        cab.floor = room.floor;
        cab.shaft = room.elevatorShaft;
        cab.doorId = liftDoor.id;
        cab.interior = Vec3(cx, y0, (frontZ + backZ) * 0.5f + 0.10f);
        cab.doorCenter = liftDoor.center;
        cab.width = cabW;
        cab.depth = cabD;
        cabList.push_back(cab);
    }

    if (room.type == ROOM_CORRIDOR || room.type == ROOM_UTILITY || room.floor == 0) {
        mb.setMaterial(MAT_STEEL);
        bool alongX = r.w > r.d;
        float py = y1 - 0.30f;
        if (alongX && r.w > 4.0f) {
            mb.pushTransform(Mat4::translate(Vec3(r.center().x, py, r.z + 0.5f)) * Mat4::rotateY(HALF_PI));
            mb.addCylinder(Vec3(0, 0, 0), 0.06f, 0.0f, 8);
            mb.popTransform();
            mb.addBox(Vec3(r.center().x, py, r.z + 0.55f), Vec3(r.w * 0.5f - 0.2f, 0.055f, 0.055f));
            mb.addBox(Vec3(r.center().x, py - 0.14f, r.z + 0.75f), Vec3(r.w * 0.5f - 0.2f, 0.035f, 0.035f));
        } else if (!alongX && r.d > 4.0f) {
            mb.addBox(Vec3(r.x + 0.55f, py, r.center().y), Vec3(0.055f, 0.055f, r.d * 0.5f - 0.2f));
            mb.addBox(Vec3(r.x + 0.75f, py - 0.14f, r.center().y), Vec3(0.035f, 0.035f, r.d * 0.5f - 0.2f));
        }
        mb.finishSubMesh();
    }

    if (roomId == startRoomId && !ventBuilt) buildStartVent(roomId, mb);

    mb.build(*(sector.mesh = std::make_shared<Mesh>()));
    sector.built = true;
    room.meshIndex = roomId;

    for (int i = 0; i < (int)sector.mesh->subMeshes().size(); i++) {
        if (sector.mesh->subMeshes()[(size_t)i].material == MAT_GLASS) sector.transparentSubs.push_back(i);
    }
}

}
