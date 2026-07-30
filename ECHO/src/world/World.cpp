#include "World.h"
#include "../core/Log.h"
#include "../core/Time.h"

using namespace em;

namespace echo {

static const char* kRoomNames[ROOM_TYPE_COUNT] = {
    "corridor", "ward", "icu", "operating", "emergency", "radiology",
    "pediatric", "psychiatry", "morgue", "server", "office", "storage",
    "bathroom", "stairwell", "elevator", "reception", "laundry", "pharmacy",
    "chapel", "utility", "vent", "nurse_station"
};

static const char* kRoomLabels[ROOM_TYPE_COUNT] = {
    "Flur", "Krankenzimmer", "Intensivstation", "OP-Saal", "Notaufnahme", "Radiologie",
    "Kinderstation", "Psychiatrie", "Leichenhalle", "Serverraum", "Buero", "Lager",
    "Sanitaer", "Treppenhaus", "Aufzug", "Empfang", "Waescherei", "Apotheke",
    "Kapelle", "Technik", "Lueftung", "Schwesternzimmer"
};

const char* roomTypeName(int t) { return kRoomNames[clampi(t, 0, ROOM_TYPE_COUNT - 1)]; }
const char* roomTypeLabel(int t) { return kRoomLabels[clampi(t, 0, ROOM_TYPE_COUNT - 1)]; }

int World::cellIndex(int floorIndex, int cx, int cz) const {
    return cz * gridW + cx;
}

int World::cellRoom(int floorIndex, int cx, int cz) const {
    if (floorIndex < 0 || floorIndex >= (int)grids.size()) return -1;
    if (cx < 0 || cz < 0 || cx >= gridW || cz >= gridH) return -1;
    return grids[(size_t)floorIndex][(size_t)cellIndex(floorIndex, cx, cz)];
}

void World::setCellRoom(int floorIndex, int cx, int cz, int room) {
    if (floorIndex < 0 || floorIndex >= (int)grids.size()) return;
    if (cx < 0 || cz < 0 || cx >= gridW || cz >= gridH) return;
    grids[(size_t)floorIndex][(size_t)cellIndex(floorIndex, cx, cz)] = room;
}

namespace {

struct BspNode {
    Rect2 rect;
    int depth = 0;
};

void bspSplit(const Rect2& area, Rng& rng, float minSize, float maxArea, std::vector<Rect2>& out, int depth) {
    bool tooBig = area.area() > maxArea;
    bool canSplitX = area.w > minSize * 2.0f;
    bool canSplitZ = area.d > minSize * 2.0f;

    if (depth > 7 || (!tooBig && depth > 1) || (!canSplitX && !canSplitZ)) {
        if (area.w >= minSize * 0.85f && area.d >= minSize * 0.85f) out.push_back(area);
        return;
    }

    bool splitVertical;
    if (canSplitX && canSplitZ) splitVertical = area.w > area.d ? rng.chance(0.78f) : rng.chance(0.22f);
    else splitVertical = canSplitX;

    float ratio = rng.range(0.38f, 0.62f);
    if (splitVertical) {
        float cut = area.w * ratio;
        cut = std::round(cut * 2.0f) * 0.5f;
        cut = clampf(cut, minSize, area.w - minSize);
        Rect2 a = { area.x, area.z, cut, area.d };
        Rect2 b = { area.x + cut, area.z, area.w - cut, area.d };
        bspSplit(a, rng, minSize, maxArea, out, depth + 1);
        bspSplit(b, rng, minSize, maxArea, out, depth + 1);
    } else {
        float cut = area.d * ratio;
        cut = std::round(cut * 2.0f) * 0.5f;
        cut = clampf(cut, minSize, area.d - minSize);
        Rect2 a = { area.x, area.z, area.w, cut };
        Rect2 b = { area.x, area.z + cut, area.w, area.d - cut };
        bspSplit(a, rng, minSize, maxArea, out, depth + 1);
        bspSplit(b, rng, minSize, maxArea, out, depth + 1);
    }
}

struct FloorTheme {
    const char* name;
    int primary[6];
    int primaryCount;
};

const FloorTheme kThemes[4] = {
    { "Keller", { ROOM_MORGUE, ROOM_SERVER, ROOM_STORAGE, ROOM_LAUNDRY, ROOM_UTILITY, ROOM_CHAPEL }, 6 },
    { "Erdgeschoss", { ROOM_ER, ROOM_RECEPTION, ROOM_RADIOLOGY, ROOM_PHARMACY, ROOM_OFFICE, ROOM_BATHROOM }, 6 },
    { "Erste Etage", { ROOM_ICU, ROOM_OR, ROOM_WARD, ROOM_NURSE_STATION, ROOM_STORAGE, ROOM_OFFICE }, 6 },
    { "Zweite Etage", { ROOM_PEDIATRIC, ROOM_PSYCH, ROOM_WARD, ROOM_BATHROOM, ROOM_OFFICE, ROOM_NURSE_STATION }, 6 }
};

}

void World::generate(const WorldConfig& cfg, PropLibrary& props) {
    Clock clock;
    destroy();
    config = cfg;
    propLib = &props;

    gridW = (int)std::round(cfg.floorWidth / cfg.cellSize);
    gridH = (int)std::round(cfg.floorDepth / cfg.cellSize);

    Rng rng(cfg.seed);

    floorList.resize((size_t)cfg.floors);
    grids.resize((size_t)cfg.floors);
    for (int f = 0; f < cfg.floors; f++) {
        floorList[(size_t)f].index = f;
        floorList[(size_t)f].baseY = (f - 1) * cfg.ceilingHeight * 1.18f;
        floorList[(size_t)f].height = cfg.ceilingHeight;
        floorList[(size_t)f].name = kThemes[clampi(f, 0, 3)].name;
        floorList[(size_t)f].extent = { 0, 0, cfg.floorWidth, cfg.floorDepth };
        grids[(size_t)f].assign((size_t)gridW * gridH, -1);
    }

    buildLayout(rng);

    for (int f = 0; f < cfg.floors; f++) {
        rasterizeRooms(f);
        buildWalls(f, rng);
    }

    sectors.resize(roomList.size());
    for (int i = 0; i < (int)roomList.size(); i++) {
        Rng roomRng(hashCombine(cfg.seed, (u64)(i + 1) * 2654435761ULL));
        roomList[(size_t)i].seed = (u32)roomRng.state();
        assignMaterials(roomList[(size_t)i], roomRng);
        placeLights(i, roomRng);
        populateRoom(i, props, roomRng);
    }

    pickStartRoom();

    for (int i = 0; i < (int)roomList.size(); i++) {
        Rng roomRng(hashCombine(cfg.seed ^ 0xABCDEFULL, (u64)(i + 1) * 40503ULL));
        buildSectorMesh(i, props, roomRng);
    }

    buildDoorLeaf();
    buildPortals();
    createDoorInteractables();
    createColliders(props);
    phys.rebuildGrid();

    chooseSpawn();

    triangleCount = 0;
    for (const auto& s : sectors) if (s.mesh) triangleCount += (int)(s.mesh->indexCount() / 3);

    {
        int start = roomAt(spawn + Vec3(0, 0.6f, 0));
        if (start < 0) start = 0;
        std::vector<int> seen((size_t)roomList.size(), 0);
        std::vector<int> queue;
        queue.push_back(start);
        seen[(size_t)start] = 1;
        for (size_t qi = 0; qi < queue.size(); qi++) {
            const Room& r = roomList[(size_t)queue[qi]];
            for (int doorId : r.doors) {
                const Door& d = doorList[(size_t)doorId];
                if (d.removed || d.locked) continue;
                int other = d.roomA == r.id ? d.roomB : d.roomA;
                if (other < 0 || seen[(size_t)other]) continue;
                seen[(size_t)other] = 1;
                queue.push_back(other);
            }
            if (r.type == ROOM_CORRIDOR) {
                for (int n : r.neighbors) {
                    if (n < 0 || seen[(size_t)n] || roomList[(size_t)n].type != ROOM_CORRIDOR) continue;
                    seen[(size_t)n] = 1;
                    queue.push_back(n);
                }
            }
        }
        int floorRooms = 0, floorSeen = 0, lifts = 0;
        int startFloor = roomList[(size_t)start].floor;
        for (const Room& r : roomList) {
            if (r.floor != startFloor) continue;
            floorRooms++;
            if (seen[(size_t)r.id]) {
                floorSeen++;
                if (r.type == ROOM_ELEVATOR) lifts++;
            }
        }
        LOG_INFO("Spawn room %d (%s), reachable %d/%d on floor %d, elevators reachable %d",
                 start, roomList[(size_t)start].label.c_str(), floorSeen, floorRooms, startFloor, lifts);

        int liftDoors = 0, liftUsable = 0, liftOpen = 0;
        for (const Door& d : doorList) {
            if (d.kind != DOOR_ELEVATOR || d.roomA == d.roomB || d.removed) continue;
            liftDoors++;
            if (d.interactId >= 0 && !d.locked) liftUsable++;
            if (d.openAmount > 0.5f) liftOpen++;
        }
        LOG_INFO("Elevator entry doors: %d total, %d usable, %d open", liftDoors, liftUsable, liftOpen);

        if (ventBuilt) {
            const float radius = 0.30f;
            Vec3 probe = ventKeyPos;
            probe.y -= 0.10f;
            bool crouchFits = !phys.overlapCapsule(probe + Vec3(0, radius, 0), probe + Vec3(0, 1.10f - radius, 0), radius * 0.94f);
            bool standBlocked = phys.overlapCapsule(probe + Vec3(0, radius, 0), probe + Vec3(0, 1.78f - radius, 0), radius * 0.94f);
            Vec3 mouth = ventEntrancePos;
            mouth.y += 0.36f;
            bool mouthClear = !phys.overlapCapsule(mouth + Vec3(0, radius, 0), mouth + Vec3(0, 1.10f - radius, 0), radius * 0.94f);
            LOG_INFO("Vent check: crouch fits %d, standing blocked %d, entrance clear %d",
                     (int)crouchFits, (int)standBlocked, (int)mouthClear);
        }

        for (int f = 0; f < (int)floorList.size(); f++) {
            int anchor = findRoomOfType(ROOM_ELEVATOR, f);
            if (anchor < 0) continue;
            std::vector<int> mark((size_t)roomList.size(), 0);
            std::vector<int> open;
            open.push_back(anchor);
            mark[(size_t)anchor] = 1;
            for (size_t qi = 0; qi < open.size(); qi++) {
                const Room& r = roomList[(size_t)open[qi]];
                for (int doorId : r.doors) {
                    const Door& d = doorList[(size_t)doorId];
                    if (d.removed || d.locked) continue;
                    int other = d.roomA == r.id ? d.roomB : d.roomA;
                    if (other < 0 || mark[(size_t)other]) continue;
                    mark[(size_t)other] = 1;
                    open.push_back(other);
                }
                if (r.type == ROOM_CORRIDOR) {
                    for (int n : r.neighbors) {
                        if (n < 0 || mark[(size_t)n] || roomList[(size_t)n].type != ROOM_CORRIDOR) continue;
                        mark[(size_t)n] = 1;
                        open.push_back(n);
                    }
                }
            }
            int total = 0, hit = 0;
            for (const Room& r : roomList) {
                if (r.floor != f) continue;
                total++;
                if (mark[(size_t)r.id]) hit++;
            }
            if (hit < total) LOG_WARN("Floor %d: only %d/%d rooms reachable from elevator", f, hit, total);
        }
    }

    LOG_INFO("Hospital generated: %d floors, %d rooms, %d doors, %d lights, %d props, %d tris in %.2fs",
             cfg.floors, (int)roomList.size(), (int)doorList.size(), (int)lightList.size(),
             (int)propList.size(), triangleCount, clock.elapsed());
}

bool World::roomHasOpenExit(int roomId) const {
    if (roomId < 0 || roomId >= (int)roomList.size()) return false;
    const Room& r = roomList[(size_t)roomId];
    for (int id : r.doors) {
        if (id < 0 || id >= (int)doorList.size()) continue;
        const Door& d = doorList[(size_t)id];
        if (d.removed || d.locked || d.jammed) continue;
        return true;
    }
    if (r.type == ROOM_CORRIDOR) {
        for (int n : r.neighbors) {
            if (n >= 0 && n < (int)roomList.size() && roomList[(size_t)n].type == ROOM_CORRIDOR) return true;
        }
    }
    return false;
}

bool World::canLockDoor(int doorId) const {
    if (doorId < 0 || doorId >= (int)doorList.size()) return false;
    const Door& d = doorList[(size_t)doorId];
    if (d.removed || d.locked || d.kind == DOOR_ELEVATOR) return false;

    auto otherExit = [&](int roomId) {
        if (roomId < 0 || roomId >= (int)roomList.size()) return true;
        const Room& r = roomList[(size_t)roomId];
        if (r.type == ROOM_CORRIDOR) return true;
        if (r.type == ROOM_ELEVATOR) return false;
        for (int id : r.doors) {
            if (id == doorId || id < 0 || id >= (int)doorList.size()) continue;
            const Door& o = doorList[(size_t)id];
            if (o.removed || o.locked || o.jammed) continue;
            return true;
        }
        return false;
    };
    return otherExit(d.roomA) && otherExit(d.roomB);
}

void World::pickStartRoom() {
    auto usable = [&](int id, float minSpan) {
        if (id < 0 || id >= (int)roomList.size()) return false;
        const Room& r = roomList[(size_t)id];
        if (r.type == ROOM_ELEVATOR || r.type == ROOM_STAIRWELL) return false;
        if (std::max(r.rect.w, r.rect.d) < minSpan) return false;
        if (std::min(r.rect.w, r.rect.d) < 3.2f) return false;
        return roomHasOpenExit(id);
    };

    int startFloor = (int)floorList.size() > 1 ? 1 : 0;
    const std::vector<int>& floorRooms = floorList[(size_t)startFloor].rooms;

    startRoomId = -1;
    int wishes[3] = { ROOM_ER, ROOM_RECEPTION, ROOM_WARD };
    for (int pass = 0; pass < 2 && startRoomId < 0; pass++) {
        float minSpan = pass == 0 ? 5.0f : 4.2f;
        for (int w = 0; w < 3 && startRoomId < 0; w++) {
            std::vector<int> matches = roomsOfType(wishes[w]);
            for (int id : matches) {
                if (roomList[(size_t)id].floor != startFloor) continue;
                if (!usable(id, minSpan)) continue;
                startRoomId = id;
                break;
            }
        }
    }
    if (startRoomId < 0) {
        for (int id : floorRooms) {
            if (roomList[(size_t)id].type == ROOM_CORRIDOR) continue;
            if (!usable(id, 4.2f)) continue;
            startRoomId = id;
            break;
        }
    }
    if (startRoomId < 0) {
        for (int id : floorRooms) {
            if (!usable(id, 3.2f)) continue;
            startRoomId = id;
            break;
        }
    }
    if (startRoomId < 0) startRoomId = floorRooms.empty() ? 0 : floorRooms[0];
}

void World::buildStartVent(int roomId, MeshBuilder& mb) {
    Room& room = roomList[(size_t)roomId];
    const Rect2& r = room.rect;
    const float y0 = room.floorY;

    const float inner = 1.12f;
    const float innerH = 1.30f;
    const float t = 0.09f;
    const float base = y0 + 0.36f;
    const float wallGap = 0.22f;

    bool alongX = r.w >= r.d;
    float span = alongX ? r.w : r.d;
    float length = clampf(span * 0.55f, 2.4f, 3.7f);
    if (span - length < 1.6f) length = span - 1.6f;
    if (length < 2.0f) return;

    float lane = wallGap + t + inner * 0.5f;
    Vec2 center = r.center();

    struct Option {
        Vec3 closed;
        Vec3 open;
        float axisSign;
        float laneCoord;
    };

    std::vector<Option> options;
    for (int side = 0; side < 2; side++) {
        for (int dir = 0; dir < 2; dir++) {
            Option o;
            if (alongX) {
                o.laneCoord = side == 0 ? r.z + lane : r.z1() - lane;
                o.axisSign = dir == 0 ? 1.0f : -1.0f;
                float startX = dir == 0 ? r.x + 0.30f : r.x1() - 0.30f;
                o.closed = Vec3(startX, base, o.laneCoord);
                o.open = Vec3(startX + o.axisSign * length, base, o.laneCoord);
            } else {
                o.laneCoord = side == 0 ? r.x + lane : r.x1() - lane;
                o.axisSign = dir == 0 ? 1.0f : -1.0f;
                float startZ = dir == 0 ? r.z + 0.30f : r.z1() - 0.30f;
                o.closed = Vec3(o.laneCoord, base, startZ);
                o.open = Vec3(o.laneCoord, base, startZ + o.axisSign * length);
            }
            options.push_back(o);
        }
    }

    int best = -1;
    float bestScore = -1e30f;
    for (int i = 0; i < (int)options.size(); i++) {
        const Option& o = options[(size_t)i];
        float score = 1e30f;
        for (int doorId : room.doors) {
            if (doorId < 0 || doorId >= (int)doorList.size()) continue;
            const Door& d = doorList[(size_t)doorId];
            Vec2 dp(d.center.x, d.center.z);
            float dc = distance(dp, Vec2(o.closed.x, o.closed.z));
            float dm = distance(dp, Vec2((o.closed.x + o.open.x) * 0.5f, (o.closed.z + o.open.z) * 0.5f));
            score = std::min(score, std::min(dc, dm));
        }
        if (score > 1e29f) score = 10.0f;
        score += distance(Vec2(o.open.x, o.open.z), center) * 0.15f;
        if (score > bestScore) { bestScore = score; best = i; }
    }
    if (best < 0) return;

    const Option& pick = options[(size_t)best];
    Vec3 axis = alongX ? Vec3(pick.axisSign, 0, 0) : Vec3(0, 0, pick.axisSign);
    Vec3 side = alongX ? Vec3(0, 0, 1) : Vec3(1, 0, 0);
    Vec3 mid = (pick.closed + pick.open) * 0.5f;

    Vec3 halfLong = alongX ? Vec3(length * 0.5f, 0, 0) : Vec3(0, 0, length * 0.5f);
    Vec3 halfWide = alongX ? Vec3(0, 0, inner * 0.5f) : Vec3(inner * 0.5f, 0, 0);
    Vec3 halfEdge = alongX ? Vec3(t * 0.5f, 0, 0) : Vec3(0, 0, t * 0.5f);

    auto slab = [&](const Vec3& c, const Vec3& half) {
        mb.addBox(c, half);
        Collider col;
        col.center = c;
        col.half = half;
        col.flags = COL_STATIC;
        phys.addCollider(col);
    };

    mb.setMaterial(MAT_VENT_GRATE);
    mb.setColor(Vec4(0.74f, 0.75f, 0.76f, 1.0f));

    Vec3 wallHalf = halfLong + Vec3(0, innerH * 0.5f + t, 0) + halfWide * 0.0f + (alongX ? Vec3(0, 0, t * 0.5f) : Vec3(t * 0.5f, 0, 0));
    Vec3 floorHalf = halfLong + Vec3(0, t * 0.5f, 0) + halfWide + (alongX ? Vec3(0, 0, t) : Vec3(t, 0, 0));

    slab(mid + Vec3(0, -t * 0.5f, 0), floorHalf);
    slab(mid + Vec3(0, innerH + t * 0.5f, 0), floorHalf);
    slab(mid + side * (inner * 0.5f + t * 0.5f) + Vec3(0, innerH * 0.5f, 0), wallHalf);
    slab(mid - side * (inner * 0.5f + t * 0.5f) + Vec3(0, innerH * 0.5f, 0), wallHalf);
    slab(pick.closed - axis * (t * 0.5f) + Vec3(0, innerH * 0.5f, 0),
         halfEdge + Vec3(0, innerH * 0.5f + t, 0) + halfWide + (alongX ? Vec3(0, 0, t) : Vec3(t, 0, 0)));

    mb.finishSubMesh();

    mb.setMaterial(MAT_STEEL);
    mb.setColor(Vec4(0.42f, 0.44f, 0.46f, 1.0f));
    for (int i = 0; i < 3; i++) {
        float u = -0.34f + i * 0.34f;
        Vec3 c = mid + (alongX ? Vec3(length * u, 0, 0) : Vec3(0, 0, length * u));
        mb.addBox(c + Vec3(0, base - y0 > 0.0f ? -(base - y0) * 0.5f - t : 0.0f, 0),
                  (alongX ? Vec3(0.07f, (base - y0) * 0.5f, inner * 0.5f + t) : Vec3(inner * 0.5f + t, (base - y0) * 0.5f, 0.07f)));
    }
    Vec3 leanBase = pick.open + axis * 0.34f;
    mb.pushTransform(Mat4::translate(Vec3(leanBase.x, y0 + 0.62f, leanBase.z)) *
                     Mat4::rotateY(alongX ? 0.0f : HALF_PI) * Mat4::rotateZ(0.24f));
    mb.addBox(Vec3(0, 0, 0), Vec3(0.05f, 0.60f, inner * 0.48f));
    mb.popTransform();
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(Vec4(1.0f, 0.42f, 0.30f, 1.0f));
    Vec3 lampPos = pick.closed + axis * 0.42f + Vec3(0, innerH - 0.10f, 0);
    mb.addBox(lampPos, Vec3(0.10f, 0.03f, 0.10f));
    mb.finishSubMesh();

    LightFixture vent;
    vent.id = (int)lightList.size();
    vent.room = roomId;
    vent.floor = room.floor;
    vent.position = lampPos - Vec3(0, 0.08f, 0);
    vent.direction = Vec3(0, -1, 0);
    vent.color = Vec3(1.0f, 0.46f, 0.34f);
    vent.intensity = 2.6f;
    vent.range = 4.0f;
    vent.spot = false;
    vent.switchable = false;
    vent.flickerAmount = 0.35f;
    vent.flickerRate = 2.4f;
    vent.flickerPhase = (float)roomId * 1.7f;
    vent.currentScale = 1.0f;
    vent.propType = -1;
    lightList.push_back(vent);
    room.lights.push_back(vent.id);

    ventKeyPos = pick.closed + axis * 0.62f + Vec3(0, 0.10f, 0);
    ventEntrancePos = pick.open + axis * 0.55f;
    ventEntrancePos.y = y0;
    ventInterior = AABB(Vec3(std::min(pick.closed.x, pick.open.x) - inner, base - 0.1f, std::min(pick.closed.z, pick.open.z) - inner),
                        Vec3(std::max(pick.closed.x, pick.open.x) + inner, base + innerH + 0.2f, std::max(pick.closed.z, pick.open.z) + inner));
    ventBuilt = true;

    LOG_INFO("Start vent in room %d (%s): entrance %.2f,%.2f,%.2f key %.2f,%.2f,%.2f length %.2f",
             roomId, room.label.c_str(), ventEntrancePos.x, ventEntrancePos.y, ventEntrancePos.z,
             ventKeyPos.x, ventKeyPos.y, ventKeyPos.z, length);

    for (int propId : room.props) {
        if (propId < 0 || propId >= (int)propList.size()) continue;
        PropInstance& p = propList[(size_t)propId];
        Vec3 q = p.position;
        if (q.x < ventInterior.mn.x - 0.3f || q.x > ventInterior.mx.x + 0.3f) continue;
        if (q.z < ventInterior.mn.z - 0.3f || q.z > ventInterior.mx.z + 0.3f) continue;
        p.hidden = true;
    }
}

void World::chooseSpawn() {
    int startRoom = startRoomId;
    if (startRoom < 0 || startRoom >= (int)roomList.size()) {
        pickStartRoom();
        startRoom = startRoomId;
    }

    const Room& room = roomList[(size_t)startRoom];
    Vec3 base = roomCenter(startRoom);
    base.y = room.floorY + 0.02f;

    Vec3 target = base;
    bool haveTarget = false;
    if (ventBuilt) {
        target = ventEntrancePos;
        haveTarget = true;
    }
    for (int doorId : room.doors) {
        if (haveTarget) break;
        if (doorId < 0 || doorId >= (int)doorList.size()) continue;
        const Door& d = doorList[(size_t)doorId];
        if (d.removed || d.locked) continue;
        target = Vec3(d.center.x, room.floorY, d.center.z);
        haveTarget = true;
    }

    Vec3 best = base;
    bool found = false;
    for (int attempt = 0; attempt < 40 && !found; attempt++) {
        Vec3 p = base;
        if (attempt > 0) {
            float t = (float)attempt / 40.0f;
            float angle = TAU * (float)attempt * 0.618f;
            float radius = 0.4f + t * std::min(room.rect.w, room.rect.d) * 0.34f;
            p.x = base.x + std::cos(angle) * radius;
            p.z = base.z + std::sin(angle) * radius;
            p.x = clampf(p.x, room.rect.x + 0.6f, room.rect.x1() - 0.6f);
            p.z = clampf(p.z, room.rect.z + 0.6f, room.rect.z1() - 0.6f);
        }
        if (ventBuilt) {
            bool insideVent = p.x > ventInterior.mn.x - 0.7f && p.x < ventInterior.mx.x + 0.7f &&
                              p.z > ventInterior.mn.z - 0.7f && p.z < ventInterior.mx.z + 0.7f;
            if (insideVent) continue;
        }
        Vec3 bottom = p + Vec3(0, 0.42f, 0);
        Vec3 top = p + Vec3(0, 1.52f, 0);
        if (phys.overlapCapsule(bottom, top, 0.30f)) continue;
        best = p;
        found = true;
    }

    spawn = best;
    spawn.y = room.floorY + 0.02f;

    Vec2 toDoor(target.x - spawn.x, target.z - spawn.z);
    spawnFacing = lengthSq(toDoor) > 0.04f ? std::atan2(toDoor.x, -toDoor.y) : 0.0f;
}

void World::buildDoorLeaf() {
    MeshBuilder mb;
    mb.setMaterial(MAT_DOOR_GREEN);
    mb.setUVScale(Vec2(1.0f, 1.0f));
    mb.addBox(Vec3(0.5f, 0.5f, 0.0f), Vec3(0.5f, 0.5f, 0.022f));
    mb.addBox(Vec3(0.5f, 0.86f, 0.024f), Vec3(0.18f, 0.12f, 0.004f));
    mb.addBox(Vec3(0.5f, 0.86f, -0.024f), Vec3(0.18f, 0.12f, 0.004f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_STEEL);
    mb.pushTransform(Mat4::translate(Vec3(0.88f, 0.46f, 0.05f)) * Mat4::rotateX(HALF_PI));
    mb.addCylinder(Vec3(0, -0.03f, 0), 0.022f, 0.06f, 8);
    mb.popTransform();
    mb.addBox(Vec3(0.845f, 0.46f, 0.075f), Vec3(0.055f, 0.016f, 0.016f));
    mb.pushTransform(Mat4::translate(Vec3(0.88f, 0.46f, -0.05f)) * Mat4::rotateX(HALF_PI));
    mb.addCylinder(Vec3(0, -0.03f, 0), 0.022f, 0.06f, 8);
    mb.popTransform();
    mb.addBox(Vec3(0.845f, 0.46f, -0.075f), Vec3(0.055f, 0.016f, 0.016f));
    mb.finishSubMesh();

    mb.setMaterial(MAT_GLASS);
    mb.addBox(Vec3(0.5f, 0.86f, 0.0f), Vec3(0.17f, 0.11f, 0.006f));
    mb.finishSubMesh();

    doorLeaf = std::make_shared<Mesh>();
    mb.build(*doorLeaf);
}

void World::destroy() {
    doorLeaf.reset();
    cabList.clear();
    roomList.clear();
    doorList.clear();
    lightList.clear();
    propList.clear();
    interactList.clear();
    floorList.clear();
    sectors.clear();
    grids.clear();
    soundQueue.clear();
    visibleList.clear();
    phys.clear();
    triangleCount = 0;
    startRoomId = -1;
    ventBuilt = false;
}

void World::buildLayout(Rng& rng) {
    for (int f = 0; f < config.floors; f++) buildFloorLayout(f, rng);
}

void World::buildFloorLayout(int floorIndex, Rng& rng) {
    const float W = config.floorWidth;
    const float D = config.floorDepth;
    const float cw = 3.0f;
    const FloorTheme& theme = kThemes[clampi(floorIndex, 0, 3)];
    FloorPlan& plan = floorList[(size_t)floorIndex];

    float vx0 = 17.0f;
    float vx1 = W - 25.0f;
    float mz = D * 0.5f - cw * 0.5f;

    auto addRoom = [&](const Rect2& r, int type) -> int {
        Room room;
        room.id = (int)roomList.size();
        room.type = type;
        room.floor = floorIndex;
        room.rect = r;
        room.floorY = plan.baseY;
        room.ceilY = plan.baseY + plan.height;
        room.bounds = AABB(Vec3(r.x, room.floorY - 0.2f, r.z), Vec3(r.x1(), room.ceilY + 0.4f, r.z1()));
        room.label = roomTypeLabel(type);
        roomList.push_back(room);
        plan.rooms.push_back(room.id);
        return room.id;
    };

    addRoom({ vx0, 0.0f, cw, D }, ROOM_CORRIDOR);
    addRoom({ vx1, 0.0f, cw, D }, ROOM_CORRIDOR);
    addRoom({ 0.0f, mz, vx0, cw }, ROOM_CORRIDOR);
    addRoom({ vx0 + cw, mz, vx1 - vx0 - cw, cw }, ROOM_CORRIDOR);
    addRoom({ vx1 + cw, mz, W - vx1 - cw, cw }, ROOM_CORRIDOR);

    Rect2 blocks[6] = {
        { 0.0f, 0.0f, vx0, mz },
        { vx0 + cw, 0.0f, vx1 - vx0 - cw, mz },
        { vx1 + cw, 0.0f, W - vx1 - cw, mz },
        { 0.0f, mz + cw, vx0, D - mz - cw },
        { vx0 + cw, mz + cw, vx1 - vx0 - cw, D - mz - cw },
        { vx1 + cw, mz + cw, W - vx1 - cw, D - mz - cw }
    };

    Rect2 reserved[3] = {
        { 10.0f, mz + cw, 6.4f, 6.2f },
        { W - 18.4f, mz - 6.2f, 6.4f, 6.2f },
        { 24.0f, mz + cw, 4.0f, 4.4f }
    };
    int liftA = addRoom(reserved[0], ROOM_ELEVATOR);
    int liftB = addRoom(reserved[1], ROOM_ELEVATOR);
    addRoom(reserved[2], ROOM_UTILITY);
    roomList[(size_t)liftA].elevatorShaft = 0;
    roomList[(size_t)liftB].elevatorShaft = 1;

    std::vector<int> created;
    for (int b = 0; b < 6; b++) {
        std::vector<Rect2> cells;
        bspSplit(blocks[b], rng, 4.0f, rng.range(52.0f, 88.0f), cells, 0);
        for (const Rect2& c : cells) {
            bool blocked = false;
            for (const Rect2& res : reserved) {
                if (c.overlaps(res)) { blocked = true; break; }
            }
            if (blocked) continue;
            int type = theme.primary[rng.rangeInt(0, theme.primaryCount)];
            if (c.area() < 14.0f) type = rng.chance(0.5f) ? ROOM_STORAGE : ROOM_BATHROOM;
            if (c.area() > 78.0f && floorIndex == 2) type = ROOM_ICU;
            created.push_back(addRoom(c, type));
        }
    }

    auto claimNearest = [&](const Vec2& anchor, int type) {
        int best = -1;
        float bestD = 1e30f;
        for (int id : created) {
            Room& r = roomList[(size_t)id];
            if (r.type == ROOM_STAIRWELL || r.type == ROOM_ELEVATOR) continue;
            if (r.rect.w < 4.0f || r.rect.d < 4.0f) continue;
            float d = distance(r.rect.center(), anchor);
            if (d < bestD) { bestD = d; best = id; }
        }
        if (best >= 0) {
            roomList[(size_t)best].type = type;
            roomList[(size_t)best].label = roomTypeLabel(type);
        }
        return best;
    };

    if (floorIndex == 1) {
        claimNearest(Vec2(W * 0.5f, mz + 8.0f), ROOM_RECEPTION);
        claimNearest(Vec2(vx0 + 12.0f, 8.0f), ROOM_ER);
    }
    if (floorIndex == 0) {
        claimNearest(Vec2(W * 0.62f, mz - 8.0f), ROOM_MORGUE);
        claimNearest(Vec2(vx1 + 6.0f, 10.0f), ROOM_SERVER);
    }
    if (floorIndex == 2) {
        claimNearest(Vec2(W * 0.45f, 9.0f), ROOM_OR);
        claimNearest(Vec2(W * 0.55f, 16.0f), ROOM_OR);
    }
    if (floorIndex == 3) {
        claimNearest(Vec2(W * 0.35f, mz + 9.0f), ROOM_PEDIATRIC);
        claimNearest(Vec2(W * 0.66f, mz + 9.0f), ROOM_PSYCH);
    }

    for (int id : created) {
        Room& r = roomList[(size_t)id];
        r.label = roomTypeLabel(r.type);
    }
}

void World::rasterizeRooms(int floorIndex) {
    for (int id : floorList[(size_t)floorIndex].rooms) {
        const Room& r = roomList[(size_t)id];
        int x0 = clampi((int)std::round(r.rect.x / config.cellSize), 0, gridW);
        int x1 = clampi((int)std::round(r.rect.x1() / config.cellSize), 0, gridW);
        int z0 = clampi((int)std::round(r.rect.z / config.cellSize), 0, gridH);
        int z1 = clampi((int)std::round(r.rect.z1() / config.cellSize), 0, gridH);
        for (int z = z0; z < z1; z++)
            for (int x = x0; x < x1; x++)
                setCellRoom(floorIndex, x, z, id);
    }
}

void World::buildWalls(int floorIndex, Rng& rng) {
    struct Edge {
        int a, b;
        bool vertical;
        int fixed;
        int start, end;
    };
    std::vector<Edge> edges;

    for (int x = 0; x <= gridW; x++) {
        int runStart = -1;
        int runA = -2, runB = -2;
        for (int z = 0; z <= gridH; z++) {
            int a = z < gridH ? cellRoom(floorIndex, x - 1, z) : -2;
            int b = z < gridH ? cellRoom(floorIndex, x, z) : -2;
            bool isWall = z < gridH && a != b && (a >= 0 || b >= 0);
            if (isWall && a == runA && b == runB) continue;
            if (runStart >= 0) edges.push_back({ runA, runB, true, x, runStart, z });
            if (isWall) { runStart = z; runA = a; runB = b; }
            else { runStart = -1; runA = runB = -2; }
        }
    }

    for (int z = 0; z <= gridH; z++) {
        int runStart = -1;
        int runA = -2, runB = -2;
        for (int x = 0; x <= gridW; x++) {
            int a = x < gridW ? cellRoom(floorIndex, x, z - 1) : -2;
            int b = x < gridW ? cellRoom(floorIndex, x, z) : -2;
            bool isWall = x < gridW && a != b && (a >= 0 || b >= 0);
            if (isWall && a == runA && b == runB) continue;
            if (runStart >= 0) edges.push_back({ runA, runB, false, z, runStart, x });
            if (isWall) { runStart = x; runA = a; runB = b; }
            else { runStart = -1; runA = runB = -2; }
        }
    }

    struct PairInfo {
        int bestEdge = -1;
        float bestLen = 0.0f;
    };
    std::unordered_map<u64, PairInfo> pairs;

    for (int i = 0; i < (int)edges.size(); i++) {
        const Edge& e = edges[(size_t)i];
        if (e.a < 0 || e.b < 0) continue;
        float len = (e.end - e.start) * config.cellSize;
        if (len < 1.6f) continue;
        u64 key = ((u64)std::min(e.a, e.b) << 32) | (u64)std::max(e.a, e.b);
        PairInfo& p = pairs[key];
        if (len > p.bestLen) { p.bestLen = len; p.bestEdge = i; }
    }

    std::vector<DoorSpot> spots;
    for (auto& kv : pairs) {
        const PairInfo& info = kv.second;
        if (info.bestEdge < 0) continue;
        const Edge& e = edges[(size_t)info.bestEdge];
        DoorSpot spot;
        spot.a = (int)(kv.first >> 32);
        spot.b = (int)(kv.first & 0xFFFFFFFF);
        spot.vertical = e.vertical;
        spot.fixed = e.fixed;
        spot.start = e.start;
        spot.end = e.end;
        spot.length = info.bestLen;
        spots.push_back(spot);
    }

    std::sort(spots.begin(), spots.end(), [](const DoorSpot& x, const DoorSpot& y) {
        if (x.a != y.a) return x.a < y.a;
        return x.b < y.b;
    });

    for (const DoorSpot& spot : spots) {
        Room& A = roomList[(size_t)spot.a];
        Room& B = roomList[(size_t)spot.b];
        bool corridorLink = A.type == ROOM_CORRIDOR || B.type == ROOM_CORRIDOR;
        bool bothCorridor = A.type == ROOM_CORRIDOR && B.type == ROOM_CORRIDOR;

        if (bothCorridor) {
            A.neighbors.push_back(spot.b);
            B.neighbors.push_back(spot.a);
            continue;
        }
        if (!corridorLink && !rng.chance(0.22f)) continue;
        createDoorAt(spot, rng, false);
    }

    connectFloor(floorIndex, spots, rng);
}

int World::createDoorAt(const DoorSpot& spot, Rng& rng, bool guaranteed) {
    Room& A = roomList[(size_t)spot.a];
    Room& B = roomList[(size_t)spot.b];
    if (doorBetween(spot.a, spot.b) >= 0) return -1;

    bool corridorLink = A.type == ROOM_CORRIDOR || B.type == ROOM_CORRIDOR;
    float mid = (spot.start + spot.end) * 0.5f * config.cellSize;
    float fixedPos = spot.fixed * config.cellSize;

    Door door;
    door.id = (int)doorList.size();
    door.roomA = spot.a;
    door.roomB = spot.b;
    door.floor = A.floor;
    door.width = (A.type == ROOM_OR || B.type == ROOM_OR || A.type == ROOM_ER || B.type == ROOM_ER) ? 1.7f : 1.0f;
    door.kind = door.width > 1.4f ? DOOR_DOUBLE : DOOR_SINGLE;
    door.height = 2.12f;
    door.yaw = spot.vertical ? HALF_PI : 0.0f;

    int elevatorRoom = (A.type == ROOM_ELEVATOR || B.type == ROOM_ELEVATOR) ? 1 : 0;
    if (elevatorRoom) {
        door.kind = DOOR_ELEVATOR;
        door.material = MAT_STEEL;
        door.width = 1.5f;
    } else {
        int mats[4] = { MAT_DOOR_GREEN, MAT_WOOD_DOOR, MAT_DOOR_METAL, MAT_DOOR_GREEN };
        door.material = mats[rng.rangeInt(0, 4)];
    }

    float halfW = door.width * 0.5f;
    float lo = spot.start * config.cellSize + halfW + 0.25f;
    float hi = spot.end * config.cellSize - halfW - 0.25f;
    if (hi <= lo) {
        if (!guaranteed || door.width <= 1.05f) return -1;
        door.width = 1.0f;
        door.kind = elevatorRoom ? DOOR_ELEVATOR : DOOR_SINGLE;
        halfW = 0.5f;
        lo = spot.start * config.cellSize + halfW + 0.15f;
        hi = spot.end * config.cellSize - halfW - 0.15f;
        if (hi <= lo) return -1;
    }
    mid = clampf(mid, lo, hi);

    if (spot.vertical) door.center = Vec3(fixedPos, A.floorY, mid);
    else door.center = Vec3(mid, A.floorY, fixedPos);

    door.swingSign = rng.chance(0.5f) ? 1.0f : -1.0f;
    door.openAmount = elevatorRoom ? 1.0f : (rng.chance(0.28f) ? rng.range(0.35f, 1.0f) : 0.0f);
    door.targetOpen = door.openAmount;
    door.locked = guaranteed ? false : (corridorLink && rng.chance(0.06f));
    if (elevatorRoom) door.locked = false;
    if (A.type == ROOM_CORRIDOR && B.type == ROOM_CORRIDOR) door.locked = false;
    if (door.locked) door.openAmount = door.targetOpen = 0.0f;

    A.doors.push_back(door.id);
    B.doors.push_back(door.id);
    A.neighbors.push_back(spot.b);
    B.neighbors.push_back(spot.a);
    doorList.push_back(door);
    return door.id;
}

void World::connectFloor(int floorIndex, std::vector<DoorSpot>& spots, Rng& rng) {
    const std::vector<int>& ids = floorList[(size_t)floorIndex].rooms;
    if (ids.empty()) return;

    std::unordered_map<int, int> slot;
    for (int i = 0; i < (int)ids.size(); i++) slot[ids[(size_t)i]] = i;

    std::vector<int> parent((size_t)ids.size());
    for (int i = 0; i < (int)ids.size(); i++) parent[(size_t)i] = i;

    auto find = [&](int x) {
        while (parent[(size_t)x] != x) {
            parent[(size_t)x] = parent[(size_t)parent[(size_t)x]];
            x = parent[(size_t)x];
        }
        return x;
    };
    auto unite = [&](int a, int b) {
        int ra = find(a), rb = find(b);
        if (ra == rb) return false;
        parent[(size_t)ra] = rb;
        return true;
    };
    auto localOf = [&](int roomId) {
        auto it = slot.find(roomId);
        return it == slot.end() ? -1 : it->second;
    };

    for (const Door& d : doorList) {
        if (d.floor != floorIndex || d.removed) continue;
        int la = localOf(d.roomA), lb = localOf(d.roomB);
        if (la < 0 || lb < 0) continue;
        unite(la, lb);
    }
    for (int id : ids) {
        const Room& r = roomList[(size_t)id];
        if (r.type != ROOM_CORRIDOR) continue;
        for (int n : r.neighbors) {
            int la = localOf(id), lb = localOf(n);
            if (la >= 0 && lb >= 0 && roomList[(size_t)n].type == ROOM_CORRIDOR) unite(la, lb);
        }
    }

    std::vector<DoorSpot> ranked = spots;
    std::sort(ranked.begin(), ranked.end(), [&](const DoorSpot& x, const DoorSpot& y) {
        bool cx = roomList[(size_t)x.a].type == ROOM_CORRIDOR || roomList[(size_t)x.b].type == ROOM_CORRIDOR;
        bool cy = roomList[(size_t)y.a].type == ROOM_CORRIDOR || roomList[(size_t)y.b].type == ROOM_CORRIDOR;
        if (cx != cy) return cx;
        if (x.length != y.length) return x.length > y.length;
        if (x.a != y.a) return x.a < y.a;
        return x.b < y.b;
    });

    for (const DoorSpot& spot : ranked) {
        int la = localOf(spot.a), lb = localOf(spot.b);
        if (la < 0 || lb < 0) continue;
        if (find(la) == find(lb)) continue;
        if (createDoorAt(spot, rng, true) < 0) continue;
        unite(la, lb);
    }

    for (int i = 0; i < (int)ids.size(); i++) parent[(size_t)i] = i;
    for (const Door& d : doorList) {
        if (d.floor != floorIndex || d.removed || d.locked) continue;
        int la = localOf(d.roomA), lb = localOf(d.roomB);
        if (la < 0 || lb < 0) continue;
        unite(la, lb);
    }
    for (int id : ids) {
        const Room& r = roomList[(size_t)id];
        if (r.type != ROOM_CORRIDOR) continue;
        for (int n : r.neighbors) {
            int la = localOf(id), lb = localOf(n);
            if (la >= 0 && lb >= 0 && roomList[(size_t)n].type == ROOM_CORRIDOR) unite(la, lb);
        }
    }
    for (Door& d : doorList) {
        if (d.floor != floorIndex || d.removed || !d.locked) continue;
        int la = localOf(d.roomA), lb = localOf(d.roomB);
        if (la < 0 || lb < 0) continue;
        if (find(la) == find(lb)) continue;
        d.locked = false;
        unite(la, lb);
    }
}

void World::assignMaterials(Room& room, Rng& rng) {
    switch (room.type) {
    case ROOM_CORRIDOR:
        room.floorMaterial = rng.chance(0.62f) ? MAT_FLOOR_CHECKER : MAT_FLOOR_LINO;
        room.wallMaterial = rng.chance(0.55f) ? MAT_TILE_WALL : MAT_TILE_WALL_GREEN;
        room.ceilMaterial = MAT_CEILING_TILE;
        break;
    case ROOM_OR:
        room.floorMaterial = MAT_TILE_FLOOR_SMALL;
        room.wallMaterial = MAT_TILE_WALL_WHITE;
        room.ceilMaterial = MAT_CEILING_TILE;
        break;
    case ROOM_MORGUE:
        room.floorMaterial = MAT_TILE_FLOOR_SMALL;
        room.wallMaterial = MAT_TILE_WALL;
        room.ceilMaterial = MAT_CEILING_CONCRETE;
        break;
    case ROOM_SERVER:
    case ROOM_UTILITY:
    case ROOM_LAUNDRY:
    case ROOM_STORAGE:
        room.floorMaterial = MAT_CONCRETE_FLOOR;
        room.wallMaterial = MAT_CONCRETE_WALL;
        room.ceilMaterial = MAT_CEILING_CONCRETE;
        break;
    case ROOM_BATHROOM:
        room.floorMaterial = MAT_TILE_FLOOR_SMALL;
        room.wallMaterial = MAT_TILE_WALL_WHITE;
        room.ceilMaterial = MAT_CEILING_TILE;
        break;
    case ROOM_STAIRWELL:
        room.floorMaterial = MAT_CONCRETE_FLOOR;
        room.wallMaterial = MAT_CONCRETE_WALL;
        room.ceilMaterial = MAT_CEILING_CONCRETE;
        break;
    case ROOM_PEDIATRIC:
        room.floorMaterial = MAT_FLOOR_LINO;
        room.wallMaterial = MAT_PAINT_WALL;
        room.ceilMaterial = MAT_CEILING_TILE;
        break;
    case ROOM_PSYCH:
        room.floorMaterial = MAT_FLOOR_LINO;
        room.wallMaterial = MAT_PLASTER;
        room.ceilMaterial = MAT_CEILING_TILE;
        break;
    case ROOM_CHAPEL:
        room.floorMaterial = MAT_WOOD_OLD;
        room.wallMaterial = MAT_PLASTER;
        room.ceilMaterial = MAT_CEILING_CONCRETE;
        break;
    default:
        room.floorMaterial = rng.chance(0.5f) ? MAT_FLOOR_LINO : MAT_TILE_FLOOR_SMALL;
        room.wallMaterial = rng.chance(0.5f) ? MAT_PLASTER : MAT_PAINT_WALL;
        room.ceilMaterial = MAT_CEILING_TILE;
        break;
    }

    if (room.floor == 0) {
        room.ceilMaterial = MAT_CEILING_CONCRETE;
        if (room.type != ROOM_MORGUE && room.type != ROOM_OR) room.wallMaterial = MAT_CONCRETE_WALL;
    }
}

void World::createColliders(PropLibrary& props) {
    for (auto& d : doorList) {
        if (d.removed) continue;
        Collider c;
        float t = 0.06f;
        Vec3 half = d.kind == DOOR_DOUBLE || d.kind == DOOR_ELEVATOR
                        ? Vec3(d.width * 0.5f, d.height * 0.5f, t)
                        : Vec3(d.width * 0.5f, d.height * 0.5f, t);
        c.half = half;
        c.center = d.center + Vec3(0, d.height * 0.5f, 0);
        c.yaw = d.yaw;
        c.flags = COL_DOOR | COL_BLOCKS_SIGHT;
        c.owner = (u32)d.id;
        c.enabled = d.openAmount < 0.35f;
        d.colliderIndex = phys.addCollider(c);
    }

    for (auto& p : propList) {
        const PropMesh& pm = props.get(p.type);
        if (!pm.solid) continue;
        Collider c;
        c.center = p.position + Vec3(pm.colliderOffset.x, pm.colliderOffset.y, pm.colliderOffset.z);
        c.half = pm.colliderHalf * p.scale;
        c.yaw = p.yaw;
        c.flags = COL_PROP;
        c.owner = (u32)p.id;
        c.enabled = !p.hidden;
        p.colliderIndex = phys.addCollider(c);
    }
}

void World::refreshCollider(int propId) {
    if (propId < 0 || propId >= (int)propList.size()) return;
    PropInstance& p = propList[(size_t)propId];
    if (p.colliderIndex < 0) return;
    Collider* c = phys.collider(p.colliderIndex);
    if (!c) return;
    const PropMesh& pm = propLib->get(p.type);
    c->center = p.position + pm.colliderOffset;
    c->yaw = p.yaw;
    c->enabled = !p.hidden;
    phys.rebuildGrid();
}

int World::roomAt(const Vec3& position) const {
    int f = floorAt(position.y);
    if (f < 0) return -1;
    int cx = (int)std::floor(position.x / config.cellSize);
    int cz = (int)std::floor(position.z / config.cellSize);
    return cellRoom(f, cx, cz);
}

int World::floorAt(float y) const {
    int best = -1;
    float bestD = 1e30f;
    for (const auto& f : floorList) {
        float d = std::fabs(y - (f.baseY + f.height * 0.4f));
        if (d < bestD) { bestD = d; best = f.index; }
    }
    return best;
}

Vec3 World::roomCenter(int room) const {
    if (room < 0 || room >= (int)roomList.size()) return Vec3(0, 0, 0);
    const Room& r = roomList[(size_t)room];
    Vec2 c = r.rect.center();
    return Vec3(c.x, r.floorY, c.y);
}

Vec3 World::randomPointInRoom(int room, Rng& rng) const {
    if (room < 0 || room >= (int)roomList.size()) return Vec3(0, 0, 0);
    const Room& r = roomList[(size_t)room];
    float inset = 0.85f;
    return Vec3(rng.range(r.rect.x + inset, r.rect.x1() - inset), r.floorY,
                rng.range(r.rect.z + inset, r.rect.z1() - inset));
}

int World::findRoomOfType(int type, int floor) const {
    for (const auto& r : roomList) if (r.type == type && (floor < 0 || r.floor == floor)) return r.id;
    return -1;
}

std::vector<int> World::roomsOfType(int type) const {
    std::vector<int> out;
    for (const auto& r : roomList) if (r.type == type) out.push_back(r.id);
    return out;
}

int World::cabContaining(const Vec3& p) const {
    for (const auto& cab : cabList) {
        if (std::fabs(p.x - cab.interior.x) > cab.width * 0.5f + 0.10f) continue;
        if (std::fabs(p.z - cab.interior.z) > cab.depth * 0.5f + 0.10f) continue;
        if (std::fabs(p.y - cab.interior.y) > 1.6f) continue;
        return cab.id;
    }
    return -1;
}

int World::cabOnFloor(int shaft, int floor) const {
    for (const auto& cab : cabList) {
        if (cab.shaft == shaft && cab.floor == floor) return cab.id;
    }
    return -1;
}

int World::cabInRoom(int room) const {
    if (room < 0) return -1;
    for (const auto& cab : cabList) {
        if (cab.room == room) return cab.id;
    }
    return -1;
}

int World::cabForDoor(int doorId) const {
    if (doorId < 0 || doorId >= (int)doorList.size()) return -1;
    const Door& door = doorList[(size_t)doorId];
    if (door.kind != DOOR_ELEVATOR) return -1;
    int rooms[2] = { door.roomA, door.roomB };
    for (int i = 0; i < 2; i++) {
        int room = rooms[i];
        if (room < 0 || room >= (int)roomList.size()) continue;
        if (roomList[(size_t)room].type != ROOM_ELEVATOR) continue;
        int cab = cabInRoom(room);
        if (cab >= 0) return cab;
    }
    return -1;
}

int World::doorBetween(int roomA, int roomB) const {
    for (const auto& d : doorList) {
        if ((d.roomA == roomA && d.roomB == roomB) || (d.roomA == roomB && d.roomB == roomA)) return d.id;
    }
    return -1;
}

void World::setDoorOpen(int doorId, bool open) {
    if (doorId < 0 || doorId >= (int)doorList.size()) return;
    Door& d = doorList[(size_t)doorId];
    if (d.locked && open) return;
    if (d.jammed) return;
    d.targetOpen = open ? 1.0f : 0.0f;
    if (open) d.wasOpened = true;
    queueSound(d.center + Vec3(0, 1.0f, 0), open ? 0 : 1, 0.7f);
}

void World::toggleDoor(int doorId) {
    if (doorId < 0 || doorId >= (int)doorList.size()) return;
    const Door& d = doorList[(size_t)doorId];
    setDoorOpen(doorId, d.targetOpen < 0.5f);
}

bool World::doorBlocked(int doorId, const Vec3& actorPos, float radius) const {
    if (doorId < 0 || doorId >= (int)doorList.size()) return false;
    const Door& d = doorList[(size_t)doorId];
    return distance(Vec2(d.center.x, d.center.z), Vec2(actorPos.x, actorPos.z)) < radius + d.width * 0.5f;
}

void World::setObserver(const Vec3& eye, const Vec3& forward) {
    observerEye = eye;
    observerDir = normalize(forward);
}

bool World::lightObserved(int lightId) const {
    if (lightId < 0 || lightId >= (int)lightList.size()) return false;
    const LightFixture& l = lightList[(size_t)lightId];

    Vec3 d = l.position - observerEye;
    float dist2 = lengthSq(d);
    if (dist2 > 24.0f * 24.0f) return false;
    float dist = std::sqrt(std::max(dist2, 1e-6f));
    if (dot(d / dist, observerDir) < 0.30f) return false;
    return phys.lineOfSight(observerEye, l.position);
}

void World::setLightOn(int lightId, bool on, bool immediate) {
    if (lightId < 0 || lightId >= (int)lightList.size()) return;
    LightFixture& l = lightList[(size_t)lightId];
    if (l.broken) return;

    if (immediate || !l.observed) {
        l.on = on;
        l.hasPending = false;
        if (!on) l.latchedOff = false;
        return;
    }
    l.pendingOn = on;
    l.pendingBroken = false;
    l.hasPending = true;
}

void World::breakLight(int lightId, bool immediate) {
    if (lightId < 0 || lightId >= (int)lightList.size()) return;
    LightFixture& l = lightList[(size_t)lightId];

    if (immediate || !l.observed) {
        l.broken = true;
        l.on = false;
        l.hasPending = false;
        queueSound(l.position, 2, 1.0f);
        return;
    }
    l.pendingBroken = true;
    l.pendingOn = false;
    l.hasPending = true;
}

void World::setRoomLights(int room, bool on, bool immediate) {
    if (room < 0 || room >= (int)roomList.size()) return;
    for (int id : roomList[(size_t)room].lights) setLightOn(id, on, immediate);
}

void World::moveProp(int propId, const Vec3& newPos, float newYaw) {
    if (propId < 0 || propId >= (int)propList.size()) return;
    PropInstance& p = propList[(size_t)propId];
    p.position = newPos;
    p.yaw = newYaw;
    refreshCollider(propId);
}

void World::restoreProp(int propId) {
    if (propId < 0 || propId >= (int)propList.size()) return;
    PropInstance& p = propList[(size_t)propId];
    p.position = p.originalPosition;
    p.yaw = p.originalYaw;
    p.hidden = false;
    refreshCollider(propId);
}

void World::hideProp(int propId, bool hidden) {
    if (propId < 0 || propId >= (int)propList.size()) return;
    propList[(size_t)propId].hidden = hidden;
    refreshCollider(propId);
}

void World::sealDoor(int doorId, bool sealed) {
    if (doorId < 0 || doorId >= (int)doorList.size()) return;
    Door& d = doorList[(size_t)doorId];
    d.jammed = sealed;
    if (sealed) {
        d.targetOpen = 0.0f;
    }
}

void World::extendCorridor(int room, float amount) {
    if (room < 0 || room >= (int)roomList.size()) return;
    Room& r = roomList[(size_t)room];
    if (r.type != ROOM_CORRIDOR) return;
    r.mutated = true;
}

void World::queueSound(const Vec3& pos, int kind, float volume) {
    if (soundQueue.size() > 64) return;
    soundQueue.push_back({ pos, kind, volume });
}

bool World::consumeSound(DoorSoundEvent& out) {
    if (soundQueue.empty()) return false;
    out = soundQueue.back();
    soundQueue.pop_back();
    return true;
}

void World::update(float dt, float time, const Vec3& listener) {
    worldTime = time;

    for (auto& d : doorList) {
        if (d.removed) continue;
        float prev = d.openAmount;
        float speed = d.kind == DOOR_ELEVATOR ? 1.1f : 2.4f;
        d.openAmount = moveTowards(d.openAmount, d.targetOpen, dt * speed);

        if (d.colliderIndex >= 0) {
            Collider* c = phys.collider(d.colliderIndex);
            if (c) {
                bool solid = d.openAmount < 0.30f;
                if (c->enabled != solid) {
                    c->enabled = solid;
                }
                if (d.kind == DOOR_SINGLE) {
                    float ang = d.openAmount * 1.45f * d.swingSign;
                    c->yaw = d.yaw + ang;
                    Vec3 hingeDir(std::cos(d.yaw), 0, -std::sin(d.yaw));
                    Vec3 hinge = d.center - hingeDir * (d.width * 0.5f);
                    Vec3 leafDir(std::cos(c->yaw), 0, -std::sin(c->yaw));
                    c->center = hinge + leafDir * (d.width * 0.5f) + Vec3(0, d.height * 0.5f, 0);
                    c->half = Vec3(d.width * 0.5f, d.height * 0.5f, 0.055f);
                } else {
                    c->yaw = d.yaw;
                    c->center = d.center + Vec3(0, d.height * 0.5f, 0);
                    c->half = Vec3(d.width * 0.5f, d.height * 0.5f, 0.055f);
                }
            }
        }

        if (prev != d.openAmount) {
            d.creakTimer -= dt;
            if (d.creakTimer <= 0.0f) {
                d.creakTimer = 0.45f;
                queueSound(d.center + Vec3(0, 1.1f, 0), 3, 0.35f);
            }
        }

        if (d.autoCloses && d.targetOpen > 0.5f) {
            d.rattleTimer += dt;
            if (d.rattleTimer > 6.0f) {
                d.rattleTimer = 0.0f;
                d.targetOpen = 0.0f;
            }
        }
    }

    for (auto& l : lightList) {
        bool inRange = distanceSq(l.position, listener) < 30.0f * 30.0f;
        l.observed = inRange && lightObserved(l.id);

        if (l.observed) {
            l.unobservedTime = 0.0f;
        } else {
            l.unobservedTime += dt;
            if (l.hasPending && l.unobservedTime > 0.12f) {
                if (l.pendingBroken) {
                    l.broken = true;
                    l.on = false;
                } else {
                    l.on = l.pendingOn;
                }
                l.hasPending = false;
            }
            if (l.unobservedTime > 0.35f) l.latchedOff = false;
        }

        if (l.broken || !l.on) {
            l.currentScale = lerpf(l.currentScale, 0.0f, 1.0f - std::exp(-12.0f * dt));
            continue;
        }

        float target = 1.0f;
        if (l.flickerAmount > 0.001f) {
            float t = time * l.flickerRate + l.flickerPhase;
            float n = fbm2(Vec2(t * 0.7f, l.flickerPhase), 3);
            float spike = hash11(std::floor(t * 3.0f) + l.flickerPhase) > 0.86f ? 0.0f : 1.0f;
            float wave = 0.62f + 0.38f * std::sin(t * 6.1f + std::sin(t * 2.3f) * 2.0f);
            target = lerpf(1.0f, wave * spike * (0.55f + 0.6f * n), l.flickerAmount);
        }

        if (l.flickerAmount > 0.42f && l.observed) {
            if (target < 0.10f) l.latchedOff = true;
            if (l.latchedOff) target = 0.0f;
        }

        float rate = l.flickerAmount > 0.5f ? 40.0f : 16.0f;
        l.currentScale = lerpf(l.currentScale, clampf(target, 0.0f, 1.4f), 1.0f - std::exp(-rate * dt));
    }

    int currentRoom = roomAt(listener);
    if (currentRoom >= 0) {
        Room& r = roomList[(size_t)currentRoom];
        if (!r.visited) {
            r.visited = true;
            r.visitCount = 1;
            r.visitTime = time;
        }
        r.lastSeen = time;
    }
}

void World::buildPortals() {
    for (auto& r : roomList) r.portals.clear();
    for (const auto& d : doorList) {
        if (d.roomA < 0 || d.roomB < 0) continue;
        roomList[(size_t)d.roomA].portals.push_back({ d.roomB, d.id });
        roomList[(size_t)d.roomB].portals.push_back({ d.roomA, d.id });
    }
    for (auto& r : roomList) {
        for (int n : r.neighbors) {
            bool found = false;
            for (auto& p : r.portals) if (p.first == n) { found = true; break; }
            if (!found) r.portals.push_back({ n, -1 });
        }
    }
    for (const auto& f : floorList) {
        for (int id : f.rooms) {
            Room& r = roomList[(size_t)id];
            if (r.type != ROOM_STAIRWELL) continue;
            for (const auto& g : floorList) {
                if (std::abs(g.index - f.index) != 1) continue;
                for (int oid : g.rooms) {
                    const Room& o = roomList[(size_t)oid];
                    if (o.type != ROOM_STAIRWELL) continue;
                    if (std::fabs(o.rect.x - r.rect.x) < 0.5f && std::fabs(o.rect.z - r.rect.z) < 0.5f)
                        r.portals.push_back({ oid, -1 });
                }
            }
        }
    }
}

void World::computeVisibility(const CameraData& cam, float maxDistance) {
    visibleList.clear();
    int startRoom = roomAt(cam.position);
    if (startRoom < 0) {
        float bestD = 1e30f;
        for (int i = 0; i < (int)roomList.size(); i++) {
            float d = roomList[(size_t)i].bounds.distSq(cam.position);
            if (d < bestD) { bestD = d; startRoom = i; }
        }
    }
    if (startRoom < 0) return;

    static thread_local std::vector<u8> seen;
    seen.assign(roomList.size(), 0);

    struct Node { int room; int depth; };
    std::vector<Node> queue;
    queue.push_back({ startRoom, 0 });
    seen[(size_t)startRoom] = 1;

    float maxDistSq = maxDistance * maxDistance;

    for (size_t qi = 0; qi < queue.size(); qi++) {
        Node node = queue[qi];
        visibleList.push_back(node.room);
        if (node.depth >= 5) continue;

        const Room& r = roomList[(size_t)node.room];
        for (const auto& portal : r.portals) {
            int other = portal.first;
            if (other < 0 || other >= (int)roomList.size()) continue;
            if (seen[(size_t)other]) continue;

                if (other == node.room) continue;
            if (portal.second >= 0) {
                const Door& d = doorList[(size_t)portal.second];
                if (!d.removed && d.openAmount < 0.16f && d.kind != DOOR_ELEVATOR) continue;
            }

            const Room& o = roomList[(size_t)other];
            if (o.bounds.distSq(cam.position) > maxDistSq) continue;
            if (!cam.frustum.testAABB(o.bounds)) continue;

            seen[(size_t)other] = 1;
            queue.push_back({ other, node.depth + 1 });
        }
    }
}

void World::collectRender(Renderer& renderer, const CameraData& cam, float maxDistance) {
    computeVisibility(cam, maxDistance);
    const Vec3& viewPos = cam.position;
    const Vec3& viewDir = cam.forward;

    static thread_local std::vector<u8> visibleFlag;
    visibleFlag.assign(roomList.size(), 0);
    for (int rid : visibleList) visibleFlag[(size_t)rid] = 1;

    for (int roomId : visibleList) {
        const Sector& s = sectors[(size_t)roomId];
        if (!s.mesh || !s.mesh->valid()) continue;
        const Room& room = roomList[(size_t)roomId];

        DrawCall dc;
        dc.mesh = s.mesh.get();
        dc.transform = Mat4();
        dc.castShadow = true;
        for (int i = 0; i < (int)s.mesh->subMeshes().size(); i++) {
            const SubMesh& sm = s.mesh->subMeshes()[(size_t)i];
            dc.subIndex = i;
            dc.material = sm.material;
            dc.bounds = sm.bounds;
            dc.transparent = false;
            for (int ts : s.transparentSubs) {
                if (ts == i) { dc.transparent = true; break; }
            }
            dc.tint = dc.transparent ? Vec4(1, 1, 1, 0.28f) : Vec4(1, 1, 1, 1);
            renderer.submit(dc);
        }
    }

    for (const auto& p : propList) {
        if (p.hidden) continue;
        if (p.room < 0 || p.room >= (int)roomList.size()) continue;
        if (!visibleFlag[(size_t)p.room]) continue;
        if (distanceSq(p.position, viewPos) > maxDistance * maxDistance) continue;

        const PropMesh& pm = propLib->get(p.type);
        Mat4 xf = Mat4::trs(p.position, p.yaw, p.scale);
        DrawCall dc;
        dc.mesh = &pm.mesh;
        dc.transform = xf;
        dc.tint = p.tint;
        dc.castShadow = true;
        for (int i = 0; i < (int)pm.mesh.subMeshes().size(); i++) {
            const SubMesh& sm = pm.mesh.subMeshes()[(size_t)i];
            dc.subIndex = i;
            dc.material = sm.material;
            dc.bounds = sm.bounds.transformed(xf);
            dc.transparent = pm.hasTransparent && i == pm.transparentSub;
            if (dc.transparent) dc.tint = Vec4(1, 1, 1, 0.24f);
            else dc.tint = p.tint;
            renderer.submit(dc);
        }
    }

    if (doorLeaf && doorLeaf->valid()) {
        for (const auto& d : doorList) {
            if (d.removed) continue;
            if (distanceSq(d.center, viewPos) > maxDistance * maxDistance) continue;
            bool visible = (d.roomA >= 0 && visibleFlag[(size_t)d.roomA]) || (d.roomB >= 0 && visibleFlag[(size_t)d.roomB]);
            if (!visible) continue;

            Vec3 along(std::cos(d.yaw), 0, -std::sin(d.yaw));
            int leaves = d.kind == DOOR_DOUBLE || d.kind == DOOR_ELEVATOR ? 2 : 1;
            float leafWidth = d.width / leaves;

            for (int li = 0; li < leaves; li++) {
                Mat4 xf;
                if (d.kind == DOOR_ELEVATOR) {
                    Vec3 nrm(std::sin(d.yaw), 0, std::cos(d.yaw));
                    Vec3 origin = li == 0
                        ? d.center - along * (leafWidth * (1.0f + d.openAmount))
                        : d.center + along * (leafWidth * d.openAmount);
                    xf = Mat4::fromBasis(along * leafWidth, Vec3(0, d.height, 0), nrm, origin);
                } else {
                    float side = (leaves == 1 || li == 0) ? -1.0f : 1.0f;
                    Vec3 hinge = d.center + along * (side * d.width * 0.5f);
                    float ang = d.openAmount * 1.45f * d.swingSign * (leaves == 1 ? 1.0f : -side);
                    float leafYaw = d.yaw + ang;
                    Vec3 dir(std::cos(leafYaw), 0, -std::sin(leafYaw));
                    Vec3 nrm(std::sin(leafYaw), 0, std::cos(leafYaw));
                    xf = Mat4::fromBasis(dir * (-side) * leafWidth, Vec3(0, d.height, 0), nrm * (-side), hinge);
                }

                DrawCall dc;
                dc.mesh = doorLeaf.get();
                dc.transform = xf;
                dc.castShadow = true;
                for (int i = 0; i < (int)doorLeaf->subMeshes().size(); i++) {
                    const SubMesh& sm = doorLeaf->subMeshes()[(size_t)i];
                    dc.subIndex = i;
                    dc.material = sm.material == MAT_DOOR_GREEN ? d.material : sm.material;
                    dc.bounds = sm.bounds.transformed(xf);
                    dc.transparent = sm.material == MAT_GLASS;
                    dc.tint = dc.transparent ? Vec4(1, 1, 1, 0.30f) : Vec4(1, 1, 1, 1);
                    renderer.submit(dc);
                }
            }
        }
    }

    for (const auto& l : lightList) {
        if (l.currentScale <= 0.01f) continue;
        if (l.room < 0 || l.room >= (int)roomList.size()) continue;
        if (!visibleFlag[(size_t)l.room]) continue;
        if (distanceSq(l.position, viewPos) > (l.range + maxDistance) * (l.range + maxDistance)) continue;

        RenderLight rl;
        rl.position = l.position;
        rl.direction = l.direction;
        rl.color = l.color;
        rl.intensity = l.intensity * l.currentScale;
        rl.range = l.range;
        rl.spot = l.spot;
        rl.innerAngle = l.innerAngle;
        rl.outerAngle = l.outerAngle;
        rl.volumetric = l.volumetric;
        rl.castShadows = l.spot;
        renderer.submitLight(rl);
    }
}

float World::lightLevelAt(const Vec3& p) const {
    float total = 0.0f;
    for (const auto& l : lightList) {
        if (l.currentScale <= 0.02f) continue;
        float d2 = distanceSq(l.position, p);
        if (d2 > l.range * l.range) continue;
        float d = std::sqrt(d2);
        float att = clampf(1.0f - d / l.range, 0.0f, 1.0f);
        att *= att;
        if (l.spot) {
            Vec3 toP = normalize(p - l.position);
            float cd = dot(toP, normalize(l.direction));
            float spot = clampf((cd - std::cos(l.outerAngle)) / std::max(std::cos(l.innerAngle) - std::cos(l.outerAngle), 1e-3f), 0.0f, 1.0f);
            att *= spot * spot;
        }
        total += att * l.intensity * l.currentScale * 0.1f;
    }
    return clampf(total, 0.0f, 1.0f);
}

float World::ambientOcclusionAt(const Vec3& p) const {
    int room = roomAt(p);
    if (room < 0) return 0.4f;
    const Room& r = roomList[(size_t)room];
    float a = std::min(r.rect.w, r.rect.d);
    return clampf(a / 8.0f, 0.25f, 1.0f);
}

bool World::insideVisibleRoom(const Vec3& p, const Vec3& viewPos) const {
    int a = roomAt(p);
    int b = roomAt(viewPos);
    if (a < 0 || b < 0) return false;
    if (a == b) return true;
    const Room& ra = roomList[(size_t)a];
    for (int n : ra.neighbors) if (n == b) return true;
    return false;
}

bool World::interactableVisible(const Vec3& origin, const Interactable& it) const {
    Vec3 d = it.position - origin;
    float len = length(d);
    if (len < 0.06f) return true;
    RayHit h = phys.raycast(origin, d / len, len - 0.04f, COL_TRIGGER | COL_CHARACTER);
    if (!h.hit) return true;
    if (it.kind == INTERACT_DOOR && (h.flags & COL_DOOR) && (int)h.owner == it.targetId) return true;
    if (h.distance > len - 0.30f) return true;
    return false;
}

int World::doorInFront(const Vec3& origin, const Vec3& dir, float maxDist) const {
    RayHit h = phys.raycast(origin, dir, maxDist, COL_TRIGGER | COL_CHARACTER);
    if (h.hit && (h.flags & COL_DOOR)) return (int)h.owner;
    return -1;
}

int World::findNearestInteractable(const Vec3& origin, const Vec3& dir, float maxDist, float maxAngle) const {
    int best = -1;
    float bestScore = -1e30f;
    float cosLimit = std::cos(maxAngle);

    for (const auto& it : interactList) {
        if (it.hidden) continue;
        Vec3 d = it.position - origin;
        float dist = length(d);
        if (dist > maxDist + it.radius) continue;
        if (dist < 1e-4f) return it.id;
        Vec3 nd = d / dist;
        float c = dot(nd, dir);
        if (c < cosLimit) continue;
        if (!interactableVisible(origin, it)) continue;
        float score = c * 2.0f - dist * 0.12f;
        if (it.kind == INTERACT_DOOR) score += 0.25f;
        if (score > bestScore) { bestScore = score; best = it.id; }
    }
    return best;
}

void World::createDoorInteractables() {
    for (auto& d : doorList) {
        if (d.removed) continue;
        if (d.kind == DOOR_ELEVATOR && d.roomA == d.roomB) continue;

        bool liftEntry = d.kind == DOOR_ELEVATOR;
        if (liftEntry) {
            d.locked = false;
            d.jammed = false;
        }

        Interactable it;
        it.id = (int)interactList.size();
        it.kind = INTERACT_DOOR;
        it.room = d.roomA;
        it.floor = d.floor;
        it.position = d.center + Vec3(0, 1.08f, 0);
        it.yaw = d.yaw;
        it.radius = std::max(d.width * 0.5f, 0.6f);
        it.targetId = d.id;
        it.prompt = liftEntry ? "Aufzugtuer" : "Tuer";
        d.interactId = it.id;
        interactList.push_back(it);

        if (d.roomA >= 0 && d.roomA < (int)roomList.size()) roomList[(size_t)d.roomA].interactables.push_back(it.id);
        if (d.roomB >= 0 && d.roomB < (int)roomList.size()) roomList[(size_t)d.roomB].interactables.push_back(it.id);
    }
}

}
