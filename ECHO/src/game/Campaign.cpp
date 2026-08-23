#include "Campaign.h"
#include "../world/Props.h"
#include "Story.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

namespace {

const char* kChapterNames[6] = {
    "NACHTDIENST",
    "ZWEITER GANG",
    "DRITTER GANG",
    "VIERTER GANG",
    "LETZTER GANG",
    "ENDE DER SCHICHT"
};

}

void CutscenePlayer::play(const std::vector<CutShot>& shots) {
    list = shots;
    index = 0;
    timer = 0.0f;
    elapsed = 0.0f;
    total = 0.0f;
    for (const auto& s : list) total += s.duration;
    running = !list.empty();
}

void CutscenePlayer::stop() {
    running = false;
    list.clear();
}

bool CutscenePlayer::update(float dt) {
    if (!running) return false;
    timer += dt;
    elapsed += dt;
    while (index < (int)list.size() && timer >= list[(size_t)index].duration) {
        timer -= list[(size_t)index].duration;
        index++;
    }
    if (index >= (int)list.size()) {
        running = false;
        return false;
    }
    return true;
}

CameraData CutscenePlayer::camera(float aspect) const {
    CameraData cam;
    if (!running || index >= (int)list.size()) {
        cam.update(aspect);
        return cam;
    }
    const CutShot& s = list[(size_t)index];
    float t = clampf(timer / std::max(s.duration, 0.01f), 0.0f, 1.0f);
    float e = t * t * (3.0f - 2.0f * t);
    cam.position = lerp(s.camFrom, s.camTo, e);
    Vec3 target = lerp(s.lookFrom, s.lookTo, e);
    Vec3 d = target - cam.position;
    cam.forward = lengthSq(d) > 1e-5f ? normalize(d) : Vec3(0, 0, -1);
    cam.fovY = s.fov;
    cam.nearPlane = 0.045f;
    cam.farPlane = 240.0f;
    cam.update(aspect);
    return cam;
}

std::string CutscenePlayer::currentLine() const {
    if (!running || index >= (int)list.size()) return std::string();
    return list[(size_t)index].line;
}

float CutscenePlayer::fade() const {
    if (!running) return 1.0f;
    float headIn = clampf(elapsed / 1.1f, 0.0f, 1.0f);
    float tailOut = clampf((total - elapsed) / 1.1f, 0.0f, 1.0f);
    return std::min(headIn, tailOut);
}

float CutscenePlayer::progress() const {
    return total > 0.0f ? clampf(elapsed / total, 0.0f, 1.0f) : 1.0f;
}

void Campaign::init(World* w, u64 seed) {
    world = w;
    rng.setSeed(seed ^ 0xC4A9A19ULL);
    reset();
}

void Campaign::reset() {
    runs.clear();
    pendingCutscene.clear();
    messages.clear();
    events.clear();
    currentRun = 0;
    currentStep = STEP_INTRO;
    carrying = false;
    cutsceneReady = false;
    stepTimer = 0.0f;
    markerValid = false;
    objectiveText.clear();
    chapterText = kChapterNames[0];
    if (!world) return;
    buildRuns(rng);
    enterStep(STEP_INTRO);
}

Vec3 Campaign::roomAnchor(int roomId) const {
    if (!world || roomId < 0 || roomId >= (int)world->rooms().size()) return Vec3(0, 0, 0);
    Vec3 c = world->roomCenter(roomId);
    c.y = world->rooms()[(size_t)roomId].floorY;
    return c;
}

void Campaign::buildRuns(Rng& r) {
    morgueRoom = world->findRoomOfType(ROOM_MORGUE, 0);
    if (morgueRoom < 0) {
        std::vector<int> m = world->roomsOfType(ROOM_MORGUE);
        if (!m.empty()) morgueRoom = m[0];
    }
    if (morgueRoom < 0) {
        std::vector<int> s = world->roomsOfType(ROOM_STORAGE);
        for (int id : s) {
            if (world->rooms()[(size_t)id].floor == 0) { morgueRoom = id; break; }
        }
    }

    std::vector<int> sources;
    for (const auto& room : world->rooms()) {
        if (room.floor == 0) continue;
        if (room.type != ROOM_WARD && room.type != ROOM_ICU && room.type != ROOM_ER && room.type != ROOM_PSYCH) continue;
        if (room.rect.area() < 12.0f) continue;
        sources.push_back(room.id);
    }
    r.shuffle(sources);

    lockerRoom = world->findRoomOfType(ROOM_NURSE_STATION, 1);
    if (lockerRoom < 0) lockerRoom = world->findRoomOfType(ROOM_OFFICE, 1);

    const int kRuns = 5;
    for (int i = 0; i < kRuns && i < (int)sources.size(); i++) {
        TransportRun run;
        run.pickupRoom = sources[(size_t)i];
        run.bodyMissing = (i == 2);

        const Room& room = world->rooms()[(size_t)run.pickupRoom];
        for (int propId : room.props) {
            const PropInstance& p = world->props()[(size_t)propId];
            if (p.hidden) continue;
            if (p.type == PROP_BED || p.type == PROP_GURNEY || p.type == PROP_STRETCHER) {
                run.gurneyProp = propId;
                break;
            }
        }

        Vec3 pos = run.gurneyProp >= 0 ? world->props()[(size_t)run.gurneyProp].position : roomAnchor(run.pickupRoom);
        pos.y = room.floorY + 0.85f;

        Interactable it;
        it.id = (int)world->interactables().size();
        it.kind = INTERACT_PICKUP;
        it.room = run.pickupRoom;
        it.floor = room.floor;
        it.position = pos;
        it.radius = 0.9f;
        it.itemId = ITEM_NONE;
        it.contentId = 900 + i;
        it.targetId = 900 + i;
        it.hidden = true;
        it.prompt = "Verstorbenen aufnehmen";
        world->interactables().push_back(it);
        world->rooms()[(size_t)run.pickupRoom].interactables.push_back(it.id);
        run.pickupInteract = it.id;

        {
            PropInstance body;
            body.id = (int)world->props().size();
            body.type = PROP_CORPSE;
            body.room = run.pickupRoom;
            body.floor = room.floor;
            body.position = pos;
            body.position.y = pos.y - 0.02f;
            body.yaw = run.gurneyProp >= 0
                           ? world->props()[(size_t)run.gurneyProp].yaw
                           : 0.0f;
            body.originalPosition = body.position;
            body.originalYaw = body.yaw;
            body.hidden = true;
            world->props().push_back(body);
            world->rooms()[(size_t)run.pickupRoom].props.push_back(body.id);
            run.bodyProp = body.id;
        }

        runs.push_back(run);
    }

    if (morgueRoom >= 0) {
        const Room& room = world->rooms()[(size_t)morgueRoom];
        Vec3 pos = roomAnchor(morgueRoom);
        Vec3 center = roomAnchor(morgueRoom);

        for (int propId : room.props) {
            const PropInstance& p = world->props()[(size_t)propId];
            if (p.type != PROP_MORGUE_WALL) continue;
            Vec3 front(-std::sin(p.yaw), 0.0f, -std::cos(p.yaw));
            if (dot(front, center - p.position) < 0.0f) front = -front;
            pos = p.position + front * 0.85f;
            break;
        }
        pos.y = room.floorY + 1.05f;

        Interactable it;
        it.id = (int)world->interactables().size();
        it.kind = INTERACT_DRAWER;
        it.room = morgueRoom;
        it.floor = room.floor;
        it.position = pos;
        it.radius = 1.2f;
        it.targetId = 950;
        it.hidden = true;
        it.prompt = "In ein Fach legen";
        world->interactables().push_back(it);
        world->rooms()[(size_t)morgueRoom].interactables.push_back(it.id);
        morgueInteract = it.id;
    }

    int reachable = 0;
    for (const TransportRun& run : runs) {
        if (run.pickupInteract < 0) continue;
        const Interactable& it = world->interactables()[(size_t)run.pickupInteract];
        for (int i = 0; i < 12; i++) {
            float a = TAU * i / 12.0f;
            Vec3 eye = it.position + Vec3(std::cos(a) * 1.15f, 0.62f, std::sin(a) * 1.15f);
            if (!world->interactableVisible(eye, it)) continue;
            reachable++;
            break;
        }
    }

    bool morgueReachable = false;
    if (morgueInteract >= 0) {
        const Interactable& it = world->interactables()[(size_t)morgueInteract];
        for (int i = 0; i < 16; i++) {
            float a = TAU * i / 16.0f;
            Vec3 eye = it.position + Vec3(std::cos(a) * 1.20f, 0.55f, std::sin(a) * 1.20f);
            if (!world->interactableVisible(eye, it)) continue;
            morgueReachable = true;
            break;
        }
    }

    LOG_INFO("Campaign: %d transports (%d reachable), morgue room %d, drawer reachable %d",
             (int)runs.size(), reachable, morgueRoom, (int)morgueReachable);
}

void Campaign::queueCutscene(const std::vector<CutShot>& shots) {
    pendingCutscene = shots;
    cutsceneReady = !pendingCutscene.empty();
}

void Campaign::queueMessage(const std::string& text, float duration) {
    if (messages.size() > 6) return;
    messages.push_back({ text, duration });
}

bool Campaign::consumeCutscene(std::vector<CutShot>& out) {
    if (!cutsceneReady) return false;
    out = pendingCutscene;
    pendingCutscene.clear();
    cutsceneReady = false;
    return true;
}

bool Campaign::consumeMessage(std::string& text, float& duration) {
    if (messages.empty()) return false;
    text = messages.front().first;
    duration = messages.front().second;
    messages.erase(messages.begin());
    return true;
}

bool Campaign::consumeEvent(int& eventId) {
    if (events.empty()) return false;
    eventId = events.front();
    events.erase(events.begin());
    return true;
}

void Campaign::startRun(int index) {
    currentRun = index;
    if (currentRun >= (int)runs.size()) {
        enterStep(STEP_FINALE);
        return;
    }

    chapterText = kChapterNames[clampi(currentRun, 0, 4)];
    TransportRun& run = runs[(size_t)currentRun];

    if (run.pickupInteract >= 0) world->interactables()[(size_t)run.pickupInteract].hidden = false;
    if (run.bodyProp >= 0) world->props()[(size_t)run.bodyProp].hidden = false;
    if (morgueInteract >= 0) world->interactables()[(size_t)morgueInteract].hidden = true;

    enterStep(STEP_GOTO_PICKUP);
}

void Campaign::enterStep(int step) {
    currentStep = step;
    stepTimer = 0.0f;
    refreshObjective();

    if (step == STEP_INTRO) {
        Vec3 start = world->spawnPoint() + Vec3(0, 1.6f, 0);
        Vec3 look = start + Vec3(0, -0.15f, -1.0f) * 4.0f;
        std::vector<CutShot> shots;
        shots.push_back({ start + Vec3(0.0f, 0.5f, 2.2f), start + Vec3(0.0f, 0.1f, 0.6f), look, look, 5.2f, 1.02f,
                          "Nachtdienst. Dritte Woche." });
        shots.push_back({ start + Vec3(0.0f, 0.1f, 0.6f), start + Vec3(0.0f, 0.0f, 0.0f), look, look + Vec3(0, -0.4f, 0), 5.0f, 1.08f,
                          "Ihre Aufgabe ist einfach. Sie bringen die Verstorbenen nach unten." });
        shots.push_back({ start, start + Vec3(0, -0.05f, -0.4f), look, look, 4.6f, 1.12f,
                          "Der Aufzug faehrt nachts nicht. Nehmen Sie das Treppenhaus." });
        queueCutscene(shots);
    }
}

void Campaign::refreshObjective() {
    markerValid = false;

    switch (currentStep) {
    case STEP_INTRO:
        objectiveText = "Schicht beginnen";
        break;
    case STEP_GOTO_PICKUP: {
        if (currentRun >= (int)runs.size()) break;
        const TransportRun& run = runs[(size_t)currentRun];
        const Room& room = world->rooms()[(size_t)run.pickupRoom];
        objectiveText = std::string("Gehen Sie in die ") + room.label + " (Etage " + std::to_string(room.floor) + ")";
        markerPos = roomAnchor(run.pickupRoom) + Vec3(0, 1.4f, 0);
        markerValid = true;
        break;
    }
    case STEP_TAKE_BODY: {
        if (currentRun >= (int)runs.size()) break;
        const TransportRun& run = runs[(size_t)currentRun];
        objectiveText = run.bodyMissing ? "Suchen Sie den Verstorbenen" : "Nehmen Sie den Verstorbenen auf";
        if (run.pickupInteract >= 0) {
            markerPos = world->interactables()[(size_t)run.pickupInteract].position;
            markerValid = !run.bodyMissing;
        }
        break;
    }
    case STEP_GOTO_MORGUE:
        objectiveText = "Bringen Sie ihn in die Leichenhalle im Keller";
        if (morgueRoom >= 0) {
            markerPos = roomAnchor(morgueRoom) + Vec3(0, 1.4f, 0);
            markerValid = true;
        }
        break;
    case STEP_DELIVER:
        objectiveText = "Legen Sie ihn in ein Fach";
        if (morgueInteract >= 0) {
            markerPos = world->interactables()[(size_t)morgueInteract].position;
            markerValid = true;
        }
        break;
    case STEP_TRANSITION:
        objectiveText = "Zurueck nach oben";
        break;
    case STEP_FINALE:
        objectiveText = "Verlassen Sie den Keller";
        break;
    default:
        objectiveText.clear();
        break;
    }
}

bool Campaign::onInteract(int kind, int targetId, const Vec3& pos) {
    if (!world) return false;

    if (currentStep == STEP_TAKE_BODY && currentRun < (int)runs.size()) {
        TransportRun& run = runs[(size_t)currentRun];
        if (targetId == 900 + currentRun) {
            if (run.bodyMissing) {
                queueMessage("Die Trage ist leer.", 4.0f);
                events.push_back(2);
                run.bodyMissing = false;
                if (run.pickupInteract >= 0) world->interactables()[(size_t)run.pickupInteract].hidden = true;
                if (run.bodyProp >= 0) world->props()[(size_t)run.bodyProp].hidden = true;
                carrying = false;
                enterStep(STEP_GOTO_MORGUE);
                objectiveText = "Sehen Sie in der Leichenhalle nach";
                return true;
            }
            carrying = true;
            if (run.pickupInteract >= 0) world->interactables()[(size_t)run.pickupInteract].hidden = true;
            if (run.bodyProp >= 0) world->props()[(size_t)run.bodyProp].hidden = true;
            if (morgueInteract >= 0) world->interactables()[(size_t)morgueInteract].hidden = false;
            queueMessage("Sie schieben die Trage.", 3.4f);
            enterStep(STEP_GOTO_MORGUE);
            return true;
        }
    }

    if (currentStep == STEP_DELIVER && targetId == 950) {
        carrying = false;
        if (morgueInteract >= 0) world->interactables()[(size_t)morgueInteract].hidden = true;
        events.push_back(10 + currentRun);
        enterStep(STEP_TRANSITION);
        return true;
    }

    return false;
}

void Campaign::update(Player& player, float dt, float time) {
    if (!world) return;
    stepTimer += dt;

    Vec3 p = player.position();
    updateGuidance(p, dt);
    int room = world->roomAt(p + Vec3(0, 0.6f, 0));

    switch (currentStep) {
    case STEP_INTRO:
        if (stepTimer > 0.4f) startRun(0);
        break;

    case STEP_GOTO_PICKUP: {
        if (currentRun >= (int)runs.size()) break;
        const TransportRun& run = runs[(size_t)currentRun];
        if (room == run.pickupRoom) {
            enterStep(STEP_TAKE_BODY);
            if (run.bodyMissing) queueMessage("Hier sollte jemand liegen.", 4.0f);
        }
        break;
    }

    case STEP_TAKE_BODY: {
        if (currentRun >= (int)runs.size()) break;
        const TransportRun& run = runs[(size_t)currentRun];
        if (run.bodyMissing && stepTimer > 6.0f && room == run.pickupRoom) {
            queueMessage("Das Bett ist warm.", 4.2f);
            stepTimer = 0.0f;
        }
        break;
    }

    case STEP_GOTO_MORGUE:
        if (room == morgueRoom) {
            if (morgueInteract >= 0) world->interactables()[(size_t)morgueInteract].hidden = false;
            enterStep(STEP_DELIVER);
        }
        break;

    case STEP_DELIVER:
        break;

    case STEP_TRANSITION: {
        int next = currentRun + 1;
        if (next >= (int)runs.size()) {
            if (stepTimer > 2.0f) enterStep(STEP_FINALE);
            break;
        }

        if (stepTimer > 2.2f) {
            if (next == 1) {
                queueMessage("Noch vier.", 3.2f);
            } else if (next == 2) {
                events.push_back(1);
                queueMessage("Im Flur ist es dunkler geworden.", 4.2f);
            } else if (next == 3) {
                Vec3 anchor = roomAnchor(morgueRoom) + Vec3(0, 1.55f, 0);
                Vec3 side = anchor + Vec3(2.6f, 0.0f, 0.6f);
                std::vector<CutShot> shots;
                shots.push_back({ side, side + Vec3(-1.4f, 0, 0), anchor, anchor, 4.6f, 1.05f,
                                  "Eines der Faecher steht offen." });
                shots.push_back({ anchor + Vec3(0, 0, 2.0f), anchor + Vec3(0, 0, 1.2f), anchor, anchor, 4.4f, 1.0f,
                                  "Es ist leer. Sie haben es heute Nacht zweimal gefuellt." });
                queueCutscene(shots);
                events.push_back(3);
            } else if (next == 4) {
                events.push_back(4);
                queueMessage("Sie haben aufgehoert zu zaehlen.", 4.0f);
            }
            startRun(next);
        }
        break;
    }

    case STEP_FINALE: {
        if (stepTimer > 1.0f && !cutsceneReady) {
            Vec3 anchor = roomAnchor(morgueRoom) + Vec3(0, 1.6f, 0);
            std::vector<CutShot> shots;
            shots.push_back({ anchor + Vec3(0, 0, 3.0f), anchor + Vec3(0, 0, 0.4f), anchor, anchor, 5.0f, 1.02f,
                              "Die Treppe nach oben ist da, wo sie immer war." });
            shots.push_back({ anchor + Vec3(0, 0.2f, 0.4f), anchor + Vec3(0, 0.2f, -2.6f), anchor + Vec3(0, 0, -6.0f), anchor + Vec3(0, 0, -14.0f), 5.4f, 1.10f,
                              "Sie fuehrt nur nicht mehr nach oben." });
            shots.push_back({ anchor + Vec3(0, 0.2f, -2.6f), anchor + Vec3(0, 0.1f, -5.0f), anchor + Vec3(0, 0, -14.0f), anchor + Vec3(0, 0, -22.0f), 5.0f, 1.16f,
                              "Dritte Woche. Sie haben nie einen ersten Tag gehabt." });
            queueCutscene(shots);
            events.push_back(20);
            currentStep = STEP_DONE;
            refreshObjective();
        }
        break;
    }

    default:
        break;
    }
}

void Campaign::updateGuidance(const Vec3& playerPos, float dt) {
    guideTimer -= dt;

    if (!markerValid) {
        guideValid = false;
        guideStairs = false;
        guideText.clear();
        return;
    }

    playerFloorIndex = world->floorAt(playerPos.y);
    targetFloorIndex = world->floorAt(markerPos.y);

    if (playerFloorIndex == targetFloorIndex) {
        guidePos = markerPos;
        guideValid = true;
        guideStairs = false;
        guideText.clear();
        return;
    }

    if (guideTimer > 0.0f && guideStairs) return;
    guideTimer = 0.75f;

    int best = -1;
    float bestDist = 1e30f;
    for (const auto& room : world->rooms()) {
        if (room.type != ROOM_ELEVATOR || room.floor != playerFloorIndex) continue;
        if (room.elevatorShaft < 0) continue;
        float d = distance(world->roomCenter(room.id), playerPos);
        if (d < bestDist) { bestDist = d; best = room.id; }
    }

    if (best < 0) {
        guidePos = markerPos;
        guideValid = true;
        guideStairs = false;
        guideText.clear();
        return;
    }

    guidePos = roomAnchor(best) + Vec3(0, 1.4f, 0);
    guideValid = true;
    guideStairs = true;

    int delta = targetFloorIndex - playerFloorIndex;
    int steps = delta < 0 ? -delta : delta;
    guideText = std::string("Aufzug nehmen: ") + std::to_string(steps) +
                (steps == 1 ? " Etage " : " Etagen ") + (delta < 0 ? "nach unten" : "nach oben");
}

void Campaign::onFloorReached(int floor) {
    if (!markerValid) return;
    if (floor != targetFloorIndex) return;
    guideStairs = false;
    guideText.clear();
    guidePos = markerPos;
    guideValid = true;
}

float Campaign::markerDistance(const Vec3& from) const {
    if (!markerValid) return -1.0f;
    return distance(markerPos, from);
}

void Campaign::serialize(std::vector<u8>& out) const {
    auto put = [&](i32 v) {
        const u8* p = (const u8*)&v;
        out.insert(out.end(), p, p + 4);
    };
    put((i32)currentRun);
    put((i32)currentStep);
    put(carrying ? 1 : 0);
    put((i32)runs.size());
    for (const auto& r : runs) put(r.bodyMissing ? 1 : 0);
}

void Campaign::deserialize(const u8* data, size_t size) {
    if (!data || size < 16) return;
    size_t off = 0;
    auto get = [&]() -> i32 {
        i32 v = 0;
        if (off + 4 <= size) std::memcpy(&v, data + off, 4);
        off += 4;
        return v;
    };
    currentRun = clampi(get(), 0, std::max(0, (int)runs.size()));
    currentStep = clampi(get(), 0, STEP_DONE);
    carrying = get() != 0;
    int count = get();
    for (int i = 0; i < count && i < (int)runs.size(); i++) runs[(size_t)i].bodyMissing = get() != 0;

    if (currentRun < (int)runs.size()) {
        chapterText = kChapterNames[clampi(currentRun, 0, 4)];
        const TransportRun& run = runs[(size_t)currentRun];
        bool needPickup = currentStep == STEP_GOTO_PICKUP || currentStep == STEP_TAKE_BODY;
        if (run.pickupInteract >= 0) world->interactables()[(size_t)run.pickupInteract].hidden = !needPickup;
        if (run.bodyProp >= 0) world->props()[(size_t)run.bodyProp].hidden = !needPickup;
        if (morgueInteract >= 0) world->interactables()[(size_t)morgueInteract].hidden = currentStep != STEP_DELIVER;
    }
    cutsceneReady = false;
    pendingCutscene.clear();
    refreshObjective();
}

}
