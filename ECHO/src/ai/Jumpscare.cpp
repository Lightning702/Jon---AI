#include "Jumpscare.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

namespace {
const float kArmMinRoomTime = 0.35f;
const float kArmMinTravel = 1.6f;
const float kGlobalCooldown = 5.5f;
const float kHitHold = 0.85f;
const float kFadeTime = 0.55f;
}

void JumpscareDirector::init(World* w, AudioEngine* a, HorrorRig* r, u64 seed) {
    world = w;
    audio = a;
    rig = r;
    rng = Rng(seed ^ 0x9E3779B97F4A7C15ULL);
    seeded = true;
    reset();
}

void JumpscareDirector::reset() {
    done.clear();
    darkenedLights.clear();
    subtitles.clear();
    entity.active = false;
    phase = SPHASE_IDLE;
    currentTrigger = -1;
    currentRoom = -1;
    armedRoom = -1;
    burstDoor = -1;
    phaseTime = 0.0f;
    armTime = 0.0f;
    roomTime = 0.0f;
    cooldown = 2.5f;
    impactPulse = 0.0f;
    travelled = 0.0f;
    lightsKilled = false;
    restored = false;
    cameraShake = 0.0f;
    flashlightKill = 0.0f;
    forcedLookStrength = 0.0f;
    bloodFlash = 0.0f;
    deafen = 0.0f;
}

bool JumpscareDirector::consumeSubtitle(std::string& text, float& duration) {
    if (subtitles.empty()) return false;
    text = subtitles.front().first;
    duration = subtitles.front().second;
    subtitles.erase(subtitles.begin());
    return true;
}

bool JumpscareDirector::alreadyScared(int room) const {
    for (int id : done) if (id == room) return true;
    return false;
}

float JumpscareDirector::corridorLength(const Room& room) const {
    return room.rect.w > room.rect.d ? room.rect.w : room.rect.d;
}

Vec3 JumpscareDirector::corridorAxis(const Room& room) const {
    return room.rect.w > room.rect.d ? Vec3(1, 0, 0) : Vec3(0, 0, 1);
}

Vec3 JumpscareDirector::floorPoint(const Room& room, const Vec3& p) const {
    Vec3 out = p;
    out.y = room.floorY;
    return out;
}

bool JumpscareDirector::looksAt(const Player& player, const Vec3& p, float cosLimit) const {
    Vec3 d = p - player.eyePosition();
    float len = length(d);
    if (len < 0.05f) return true;
    return dot(d / len, player.forward()) > cosLimit;
}

void JumpscareDirector::killLights(int room, bool restore) {
    if (!world) return;
    if (restore) {
        for (int id : darkenedLights) {
            if (id < 0 || id >= (int)world->lights().size()) continue;
            world->setLightOn(id, true, false);
            world->lights()[(size_t)id].flickerAmount = 0.45f;
        }
        darkenedLights.clear();
        lightsKilled = false;
        return;
    }
    darkenedLights.clear();
    if (room < 0 || room >= (int)world->rooms().size()) return;
    const Room& r = world->rooms()[(size_t)room];
    for (int id : r.lights) {
        if (id < 0 || id >= (int)world->lights().size()) continue;
        LightFixture& l = world->lights()[(size_t)id];
        if (!l.on) continue;
        darkenedLights.push_back(id);
        l.flickerAmount = 1.0f;
        world->setLightOn(id, false, true);
    }
    lightsKilled = true;
}

void JumpscareDirector::arm(int trigger, const Vec3& pos, float faceYaw, int mode) {
    currentTrigger = trigger;
    entity.configure(rng.rangeInt(0, HORROR_KIND_COUNT), rng.nextU32() | 1ULL);
    entity.position = pos;
    entity.yaw = faceYaw;
    entity.visibility = trigger == TRIG_RUSH_AHEAD || trigger == TRIG_WALL_PEEK ? 1.0f : 0.0f;
    entity.setMode(mode);
    anchor = pos;
    phase = SPHASE_ARMED;
    phaseTime = 0.0f;
    armTime = 0.0f;
    armedRoom = currentRoom;
}

bool JumpscareDirector::spawnAhead(const Player& player, const Room& room) {
    float len = corridorLength(room);
    if (len < 9.0f) return false;
    Vec3 fwd = player.flatForward();
    if (lengthSq(fwd) < 0.01f) return false;
    Vec3 pos = player.position() + fwd * std::min(len * 0.62f, 13.5f);
    if (world->roomAt(pos + Vec3(0, 0.7f, 0)) != room.id) {
        pos = player.position() + fwd * 7.0f;
        if (world->roomAt(pos + Vec3(0, 0.7f, 0)) != room.id) return false;
    }
    pos = floorPoint(room, pos);
    arm(TRIG_RUSH_AHEAD, pos, std::atan2(-fwd.x, fwd.z), HMODE_STARE);
    rushTarget = player.position();
    return true;
}

bool JumpscareDirector::spawnBehind(const Player& player, const Room& room) {
    Vec3 back = player.position() - player.flatForward() * 1.75f;
    if (world->roomAt(back + Vec3(0, 0.7f, 0)) != room.id) return false;
    back = floorPoint(room, back);
    arm(TRIG_BEHIND_TURN, back, player.yawAngle() + PI, HMODE_STARE);
    return true;
}

bool JumpscareDirector::spawnDoor(const Player& player, const Room& room) {
    for (int doorId : room.doors) {
        if (doorId < 0 || doorId >= (int)world->doors().size()) continue;
        Door& d = world->doors()[(size_t)doorId];
        if (d.kind == DOOR_ELEVATOR || d.removed) continue;
        float dist = distance(d.center, player.position());
        if (dist < 2.2f || dist > 7.5f) continue;
        if (!looksAt(player, d.center + Vec3(0, 1.2f, 0), 0.35f)) continue;
        Vec3 toPlayer = player.position() - d.center;
        toPlayer.y = 0.0f;
        if (lengthSq(toPlayer) < 0.04f) continue;
        toPlayer = normalize(toPlayer);
        Vec3 pos = floorPoint(room, d.center + toPlayer * 0.55f);
        burstDoor = doorId;
        arm(TRIG_DOOR_BURST, pos, std::atan2(toPlayer.x, -toPlayer.z), HMODE_TWITCH);
        return true;
    }
    return false;
}

bool JumpscareDirector::spawnCeiling(const Player& player, const Room& room) {
    Vec3 fwd = player.flatForward();
    Vec3 pos = player.position() + fwd * 2.5f;
    if (world->roomAt(pos + Vec3(0, 0.7f, 0)) != room.id) return false;
    pos = floorPoint(room, pos);
    arm(TRIG_CEILING_DROP, pos, std::atan2(-fwd.x, fwd.z), HMODE_HANG);
    return true;
}

bool JumpscareDirector::spawnCrawl(const Player& player, const Room& room) {
    float len = corridorLength(room);
    if (len < 8.0f) return false;
    Vec3 fwd = player.flatForward();
    Vec3 pos = player.position() + fwd * std::min(len * 0.55f, 11.0f);
    if (world->roomAt(pos + Vec3(0, 0.7f, 0)) != room.id) return false;
    pos = floorPoint(room, pos);
    arm(TRIG_FLOOR_CRAWL, pos, std::atan2(-fwd.x, fwd.z), HMODE_CRAWL);
    rushTarget = player.position();
    return true;
}

bool JumpscareDirector::spawnPeek(const Player& player, const Room& room) {
    Vec3 axis = corridorAxis(room);
    Vec3 side(axis.z, 0.0f, axis.x);
    Vec3 fwd = player.flatForward();
    for (int i = 0; i < 2; i++) {
        float sign = i == 0 ? 1.0f : -1.0f;
        Vec3 pos = player.position() + fwd * 4.2f + side * sign * 1.35f;
        if (world->roomAt(pos + Vec3(0, 0.7f, 0)) != room.id) continue;
        pos = floorPoint(room, pos);
        arm(TRIG_WALL_PEEK, pos, std::atan2(-side.x * sign, side.z * sign), HMODE_TWITCH);
        return true;
    }
    return false;
}

bool JumpscareDirector::pickSetup(const Player& player, int room, float time) {
    const Room& r = world->rooms()[(size_t)room];
    std::vector<int> order;
    order.push_back(TRIG_RUSH_AHEAD);
    order.push_back(TRIG_BEHIND_TURN);
    order.push_back(TRIG_DOOR_BURST);
    order.push_back(TRIG_CEILING_DROP);
    order.push_back(TRIG_FLOOR_CRAWL);
    order.push_back(TRIG_WALL_PEEK);
    rng.shuffle(order);

    for (int t : order) {
        bool ok = false;
        switch (t) {
        case TRIG_RUSH_AHEAD: ok = spawnAhead(player, r); break;
        case TRIG_BEHIND_TURN: ok = spawnBehind(player, r); break;
        case TRIG_DOOR_BURST: ok = spawnDoor(player, r); break;
        case TRIG_CEILING_DROP: ok = spawnCeiling(player, r); break;
        case TRIG_FLOOR_CRAWL: ok = spawnCrawl(player, r); break;
        default: ok = spawnPeek(player, r); break;
        }
        if (ok) return true;
    }
    return spawnBehind(player, r);
}

void JumpscareDirector::detonate(Player& player, float time) {
    phase = SPHASE_HIT;
    phaseTime = 0.0f;
    impactPulse = 1.0f;
    bloodFlash = 1.0f;
    deafen = 1.0f;
    cameraShake = 1.0f;
    flashlightKill = 1.0f;
    entity.visibility = 1.0f;
    entity.faceTowards(player.eyePosition());
    entity.setMode(currentTrigger == TRIG_FLOOR_CRAWL ? HMODE_CRAWL : HMODE_LUNGE);

    killLights(currentRoom, false);
    player.addShake(0.85f, 0.9f);
    forcedLookTarget = entity.headPosition();
    forcedLookStrength = 1.0f;

    if (audio) {
        audio->play2D(SFX_SLAM_HIT, 1.0f, rng.range(0.94f, 1.06f));
        audio->play2D(SFX_SCREAM, 1.0f, rng.range(0.92f, 1.10f));
        audio->play2D(SFX_SCREECH, 0.85f, rng.range(0.95f, 1.15f));
        audio->playAt(SFX_BONE_CRACK, entity.position, 0.9f, rng.range(0.9f, 1.1f));
        audio->setDucking(0.85f);
    }

    if (burstDoor >= 0 && burstDoor < (int)world->doors().size()) {
        Door& d = world->doors()[(size_t)burstDoor];
        d.locked = false;
        d.targetOpen = 1.0f;
        d.openAmount = 1.0f;
        world->queueSound(d.center, 1, 1.0f);
    }

    LOG_INFO("Jumpscare fired: trigger %d, kind %d, corridor %d (%d corridors so far)",
             currentTrigger, entity.look().kind, currentRoom, (int)done.size());
}

void JumpscareDirector::finish() {
    if (lightsKilled) killLights(currentRoom, true);
    entity.active = false;
    entity.visibility = 0.0f;
    phase = SPHASE_IDLE;
    currentTrigger = -1;
    burstDoor = -1;
    forcedLookStrength = 0.0f;
    cooldown = kGlobalCooldown;
    if (audio) audio->setDucking(0.0f);
}

void JumpscareDirector::update(Player& player, float dt, float time, float intensityScale) {
    if (!world || !seeded) return;

    impactPulse *= std::exp(-dt * 3.2f);
    bloodFlash *= std::exp(-dt * 1.9f);
    deafen *= std::exp(-dt * 0.55f);
    cameraShake *= std::exp(-dt * 4.5f);
    flashlightKill *= std::exp(-dt * 1.4f);
    if (cooldown > 0.0f) cooldown -= dt;

    int room = world->roomAt(player.position() + Vec3(0, 0.6f, 0));
    if (room != currentRoom) {
        currentRoom = room;
        roomTime = 0.0f;
        travelled = 0.0f;
        lastPos = player.position();
    } else {
        roomTime += dt;
        travelled += distance(player.position(), lastPos);
        lastPos = player.position();
    }

    if (entity.active) {
        entity.update(dt, time, player.eyePosition());
    }

    if (phase == SPHASE_ARMED) {
        armTime += dt;
        bool fire = false;

        switch (currentTrigger) {
        case TRIG_RUSH_AHEAD: {
            entity.visibility = std::min(1.0f, entity.visibility + dt * 3.0f);
            float dist = distance(entity.position, player.position());
            if (looksAt(player, entity.headPosition(), 0.55f) && armTime > 0.20f) {
                Vec3 toPlayer = player.position() - entity.position;
                toPlayer.y = 0.0f;
                float len = length(toPlayer);
                if (len > 0.05f) {
                    entity.setMode(HMODE_LUNGE);
                    entity.position += (toPlayer / len) * dt * 17.5f;
                    entity.faceTowards(player.eyePosition());
                }
                if (dist < 2.6f) fire = true;
            }
            if (armTime > 12.0f) { finish(); return; }
            break;
        }
        case TRIG_BEHIND_TURN: {
            float turn = std::fabs(wrapAngle(player.yawAngle() - lastYaw));
            if (looksAt(player, entity.headPosition(), 0.35f) || turn > 1.1f) {
                entity.visibility = 1.0f;
                fire = true;
            }
            if (armTime > 9.0f) { finish(); return; }
            break;
        }
        case TRIG_DOOR_BURST: {
            if (armTime > 0.45f && distance(entity.position, player.position()) < 6.5f) fire = true;
            if (armTime > 7.0f) { finish(); return; }
            break;
        }
        case TRIG_CEILING_DROP: {
            float dist = distance(entity.position, player.position());
            entity.position.y = anchor.y + 2.05f * (1.0f - std::min(1.0f, armTime * 0.6f));
            entity.visibility = std::min(1.0f, armTime * 4.0f);
            if (dist < 3.4f && armTime > 0.18f) {
                entity.position.y = anchor.y;
                fire = true;
            }
            if (armTime > 6.0f) { finish(); return; }
            break;
        }
        case TRIG_FLOOR_CRAWL: {
            entity.visibility = std::min(1.0f, entity.visibility + dt * 4.0f);
            Vec3 toPlayer = player.position() - entity.position;
            toPlayer.y = 0.0f;
            float len = length(toPlayer);
            if (len > 0.05f) {
                entity.position += (toPlayer / len) * dt * 12.0f;
                entity.faceTowards(player.position());
            }
            if (len < 2.2f) fire = true;
            if (armTime > 10.0f) { finish(); return; }
            break;
        }
        default: {
            if (looksAt(player, entity.headPosition(), 0.6f) && armTime > 0.15f) fire = true;
            if (distance(entity.position, player.position()) < 2.0f) fire = true;
            if (armTime > 8.0f) { finish(); return; }
            break;
        }
        }

        lastYaw = player.yawAngle();
        if (fire) detonate(player, time);
        return;
    }

    if (phase == SPHASE_HIT) {
        phaseTime += dt;
        forcedLookTarget = entity.headPosition();
        forcedLookStrength = std::max(0.0f, 1.0f - phaseTime * 1.6f);
        Vec3 toPlayer = player.position() - entity.position;
        toPlayer.y = 0.0f;
        float len = length(toPlayer);
        if (len > 1.05f) entity.position += (toPlayer / len) * dt * 9.5f;
        entity.faceTowards(player.eyePosition());
        if (phaseTime > kHitHold) {
            phase = SPHASE_FADE;
            phaseTime = 0.0f;
            if (audio) audio->playAt(SFX_BREATH_CLOSE, entity.position, 0.9f, 0.85f);
        }
        return;
    }

    if (phase == SPHASE_FADE) {
        phaseTime += dt;
        entity.visibility = std::max(0.0f, 1.0f - phaseTime / kFadeTime);
        if (phaseTime > kFadeTime) {
            const char* lines[] = {
                "(Da war etwas. Ganz sicher.)",
                "(Der Flur ist leer. Wieder.)",
                "(Dein Puls schlaegt bis in den Hals.)",
                "(Es hat dich angesehen.)"
            };
            subtitles.push_back(std::make_pair(std::string(lines[rng.rangeInt(0, 4)]), 3.0f));
            finish();
        }
        return;
    }

    if (cooldown > 0.0f) return;
    if (currentRoom < 0 || currentRoom >= (int)world->rooms().size()) return;
    const Room& r = world->rooms()[(size_t)currentRoom];
    if (r.type != ROOM_CORRIDOR) return;
    if (alreadyScared(currentRoom)) return;
    if (roomTime < kArmMinRoomTime || travelled < kArmMinTravel) return;

    if (pickSetup(player, currentRoom, time)) {
        done.push_back(currentRoom);
        lastYaw = player.yawAngle();
        if (audio && intensityScale > 0.0f) {
            audio->playAt(SFX_SCRATCH, entity.position, 0.30f * intensityScale, 0.7f);
        }
    } else {
        cooldown = 1.5f;
    }
}

void JumpscareDirector::submit(Renderer& renderer) {
    if (!rig || !rig->ready()) return;
    if (!entity.active || entity.visibility <= 0.02f) return;
    entity.submit(renderer, *rig);
}

}
