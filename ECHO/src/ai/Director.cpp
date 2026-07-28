#include "Director.h"
#include "../game/Story.h"
#include "../core/Log.h"

using namespace em;

namespace echo {

void BehaviorTracker::reset() {
    data = BehaviorProfile();
    visits.clear();
    doorSeenTime.clear();
    ignored.clear();
    doorOpened.clear();
    recentRooms.clear();
    room = previousRoom = -1;
    roomTime = sprintTime = idleTime = darkTime = standStillTime = 0.0f;
    lastYaw = yawAccum = lookBackTimer = recentLookDelta = turnRateAvg = 0.0f;
    lastPos = Vec3(0, 0, 0);
}

void BehaviorTracker::update(const Player& player, const World& world, float dt, float time) {
    if (dt <= 0.0f) return;
    data.totalTime += dt;

    float moved = length(Vec2(player.position().x - lastPos.x, player.position().z - lastPos.z));
    lastPos = player.position();
    data.distanceWalked += moved;

    if (player.isSprinting() && player.isMoving()) sprintTime += dt;
    if (!player.isMoving()) {
        idleTime += dt;
        standStillTime += dt;
    } else {
        standStillTime = 0.0f;
    }

    float lightLevel = world.lightLevelAt(player.eyePosition());
    if (lightLevel < 0.06f) darkTime += dt;

    float yaw = player.yawAngle();
    float delta = std::fabs(wrapAngle(yaw - lastYaw));
    lastYaw = yaw;
    recentLookDelta = lerpf(recentLookDelta, delta / std::max(dt, 1e-4f), 1.0f - std::exp(-3.0f * dt));
    turnRateAvg = lerpf(turnRateAvg, recentLookDelta, 1.0f - std::exp(-0.4f * dt));

    yawAccum += delta;
    if (yawAccum > 2.3f) {
        yawAccum = 0.0f;
        lookBackTimer = 2.5f;
        data.lookBackRate += 1.0f;
    }
    yawAccum *= std::exp(-1.4f * dt);
    if (lookBackTimer > 0.0f) lookBackTimer -= dt;

    int newRoom = world.roomAt(player.position() + Vec3(0, 0.6f, 0));
    if (newRoom != room) {
        previousRoom = room;
        room = newRoom;
        roomTime = 0.0f;
        if (room >= 0) {
            int& count = visits[room];
            count++;
            if (count == 1) data.roomsSeen++;
            else data.roomsRevisited++;

            recentRooms.push_back(room);
            if (recentRooms.size() > 12) recentRooms.erase(recentRooms.begin());
        }
    } else {
        roomTime += dt;
    }

    if (room >= 0 && room < (int)world.rooms().size()) {
        for (int doorId : world.rooms()[(size_t)room].doors) notifyDoorSeen(doorId);
    }

    float t = std::max(data.totalTime, 1.0f);
    data.sprintRatio = sprintTime / t;
    data.idleRatio = idleTime / t;
    data.darkRatio = darkTime / t;
    data.nervousness = clampf(turnRateAvg / 2.6f, 0.0f, 1.0f);
    data.explorationRate = (float)data.roomsSeen / std::max(t / 22.0f, 1.0f);
    data.backtrackRatio = data.roomsRevisited / std::max((float)(data.roomsSeen + data.roomsRevisited), 1.0f);
    data.readingRate = (float)(data.documentsRead + data.logsHeard) / std::max(t / 90.0f, 1.0f);
    data.doorsIgnored = (int)ignored.size();
    data.avoidance = data.presencesSeen > 0 ? (float)data.presencesAvoided / (float)data.presencesSeen : 0.0f;
}

void BehaviorTracker::notifyDoorSeen(int doorId) {
    if (doorId < 0) return;
    if ((int)doorOpened.size() <= doorId) doorOpened.resize((size_t)doorId + 1, 0);
    if (doorOpened[(size_t)doorId]) return;
    auto it = doorSeenTime.find(doorId);
    if (it == doorSeenTime.end()) {
        doorSeenTime[doorId] = 0.0f;
    } else {
        it->second += 1.0f;
        if (it->second > 90.0f) {
            bool found = false;
            for (int d : ignored) if (d == doorId) { found = true; break; }
            if (!found) ignored.push_back(doorId);
        }
    }
}

void BehaviorTracker::notifyDoorOpened(int doorId) {
    if (doorId < 0) return;
    if ((int)doorOpened.size() <= doorId) doorOpened.resize((size_t)doorId + 1, 0);
    if (!doorOpened[(size_t)doorId]) {
        doorOpened[(size_t)doorId] = 1;
        data.doorsOpened++;
    }
    for (size_t i = 0; i < ignored.size(); i++) {
        if (ignored[i] == doorId) { ignored.erase(ignored.begin() + i); break; }
    }
}

void BehaviorTracker::notifyDocumentRead(int layer) {
    data.documentsRead++;
    data.truthLayers = std::max(data.truthLayers, layer + 1);
}

void BehaviorTracker::notifyLogHeard(int layer) {
    data.logsHeard++;
    data.truthLayers = std::max(data.truthLayers, layer + 1);
}

void BehaviorTracker::notifyPresenceSeen(bool lookedAt) {
    data.presencesSeen++;
    if (!lookedAt) data.presencesAvoided++;
}

int BehaviorTracker::mostVisitedRoom() const {
    int best = -1, bestCount = 0;
    for (const auto& kv : visits) {
        if (kv.second > bestCount) { bestCount = kv.second; best = kv.first; }
    }
    return best;
}

void Director::init(World* w, AudioEngine* a, HumanRig* r, u64 seed) {
    world = w;
    audio = a;
    rig = r;
    rng.setSeed(seed ^ 0x5CA3E0ULL);
    reset();
}

void Director::reset() {
    behavior.reset();
    for (int i = 0; i < SCARE_COUNT; i++) scares[i] = ScareState();
    tensionValue = dreadValue = distortionValue = ambientMod = 0.0f;
    sanityValue = 1.0f;
    ambientTimer = 6.0f;
    mutationTimer = 28.0f;
    whisperTimer = 45.0f;
    paTimer = 120.0f;
    scareCooldown = 75.0f;
    currentScare = -1;
    presenceActive = false;
    presenceFade = 0.0f;
    presence.active = false;
    subtitles.clear();
    mutatedRooms.clear();
}

void Director::queueSubtitle(const std::string& text, float duration) {
    if (subtitles.size() > 8) return;
    subtitles.push_back({ text, duration });
}

bool Director::consumeSubtitle(std::string& text, float& duration) {
    if (subtitles.empty()) return false;
    text = subtitles.front().first;
    duration = subtitles.front().second;
    subtitles.erase(subtitles.begin());
    return true;
}

void Director::notifyInteract(int kind, int targetId, const Vec3& pos) {
    if (kind == INTERACT_DOOR) behavior.notifyDoorOpened(targetId);
}

void Director::notifyDocumentRead(int layer) {
    behavior.notifyDocumentRead(layer);
    sanityValue = clampf(sanityValue + 0.03f, 0.0f, 1.0f);
}

void Director::notifyLogHeard(int layer) {
    behavior.notifyLogHeard(layer);
}

void Director::playCue(int sound, const Vec3& pos, float volume, float pitch) {
    if (!audio) return;
    PlayParams p;
    p.position = pos;
    p.volume = volume;
    p.pitch = pitch;
    p.maxDistance = 40.0f;
    p.minDistance = 2.0f;
    p.reverbSend = 0.55f;
    audio->play(sound, p);
}

bool Director::inPlayerView(const Player& player, const Vec3& pos) const {
    Vec3 d = pos - player.eyePosition();
    float dist = length(d);
    if (dist < 1e-3f) return true;
    return dot(d / dist, player.forward()) > 0.42f;
}

bool Director::playerLooksAt(const Player& player, const Vec3& pos, float cosLimit) const {
    Vec3 d = pos - player.eyePosition();
    float dist = length(d);
    if (dist < 1e-3f) return true;
    return dot(d / dist, player.forward()) > cosLimit;
}

bool Director::roomOffScreen(const Player& player, int roomId) const {
    if (!world || roomId < 0 || roomId >= (int)world->rooms().size()) return true;
    const Room& r = world->rooms()[(size_t)roomId];
    if (behavior.currentRoom() == roomId) return false;
    return !inPlayerView(player, r.bounds.center());
}

void Director::updateTension(const Player& player, float dt) {
    const BehaviorProfile& p = behavior.profile();

    float target = 0.14f;
    target += p.darkRatio * 0.32f;
    target += p.nervousness * 0.26f;
    target += clampf(behavior.stillTime() / 22.0f, 0.0f, 0.22f);
    target += p.sprintRatio * 0.18f;
    target += clampf((float)p.presencesSeen * 0.05f, 0.0f, 0.24f);
    if (presenceActive) target += 0.42f;
    if (currentScare >= 0) target += 0.5f;

    float rate = target > tensionValue ? 0.9f : 0.14f;
    tensionValue = lerpf(tensionValue, clampf(target, 0.0f, 1.0f), 1.0f - std::exp(-rate * dt));

    dreadValue = lerpf(dreadValue, clampf(p.darkRatio * 0.6f + p.backtrackRatio * 0.35f + tensionValue * 0.3f, 0.0f, 1.0f), 1.0f - std::exp(-0.25f * dt));

    float sanityDrift = -0.0022f * (0.4f + tensionValue) * (0.6f + p.darkRatio);
    sanityDrift += p.readingRate * 0.0016f;
    sanityValue = clampf(sanityValue + sanityDrift * dt * 6.0f, 0.05f, 1.0f);

    distortionValue = lerpf(distortionValue, clampf((1.0f - sanityValue) * 0.7f + tensionValue * 0.25f, 0.0f, 1.0f), 1.0f - std::exp(-0.6f * dt));

    heartbeatTarget = tensionValue > 0.42f ? lerpf(52.0f, 118.0f, tensionValue) : 0.0f;
    if (audio) {
        audio->setTension(tensionValue);
        audio->setHeartbeatRate(heartbeatTarget);
        float roomSize = 0.55f + dreadValue * 0.3f;
        audio->setReverb(roomSize, 0.3f, 0.22f + tensionValue * 0.12f);
    }

    ambientMod = -tensionValue * 0.35f;
    cameraShake = lerpf(cameraShake, 0.0f, 1.0f - std::exp(-2.0f * dt));
    flashlightDisturb = lerpf(flashlightDisturb, 0.0f, 1.0f - std::exp(-1.5f * dt));
    forcedLookStrength = lerpf(forcedLookStrength, 0.0f, 1.0f - std::exp(-3.0f * dt));
}

void Director::updateAmbientEvents(const Player& player, float dt, float time) {
    if (!world) return;
    const BehaviorProfile& p = behavior.profile();

    ambientTimer -= dt * (1.0f + p.idleRatio * 1.6f + tensionValue * 0.8f);
    if (ambientTimer <= 0.0f) {
        ambientTimer = rng.range(9.0f, 26.0f) * lerpf(1.0f, 0.5f, tensionValue);

        int room = behavior.currentRoom();
        Vec3 origin = player.position();
        Vec3 pos = origin + rng.unitSphere() * rng.range(7.0f, 22.0f);
        pos.y = origin.y + rng.range(0.0f, 1.8f);

        float loudness = lerpf(0.35f, 1.0f, p.idleRatio) * lerpf(0.6f, 1.15f, tensionValue);
        int roll = rng.rangeInt(0, 10);
        switch (roll) {
        case 0: playCue(SFX_DISTANT_STEPS, pos, loudness * 0.85f, rng.range(0.85f, 1.1f)); break;
        case 1: playCue(SFX_DISTANT_DOOR, pos, loudness * 0.7f, rng.range(0.8f, 1.05f)); break;
        case 2: playCue(SFX_DRIP, pos, loudness * 0.6f, rng.range(0.9f, 1.2f)); break;
        case 3: playCue(SFX_PIPE_KNOCK, pos, loudness * 0.75f, rng.range(0.7f, 1.0f)); break;
        case 4: playCue(SFX_METAL_DRAG, pos, loudness * 0.55f, rng.range(0.75f, 0.95f)); break;
        case 5: playCue(SFX_SCRATCH, pos, loudness * 0.6f, rng.range(0.9f, 1.15f)); break;
        case 6: playCue(SFX_VENT_HUM, pos, loudness * 0.35f, rng.range(0.9f, 1.05f)); break;
        case 7: playCue(SFX_WHEELCHAIR, pos, loudness * 0.5f, rng.range(0.8f, 1.0f)); break;
        default: playCue(SFX_WIND, pos, loudness * 0.45f, rng.range(0.85f, 1.0f)); break;
        }
    }

    whisperTimer -= dt * (0.6f + tensionValue * 1.8f + p.darkRatio);
    if (whisperTimer <= 0.0f) {
        whisperTimer = rng.range(60.0f, 165.0f);
        Vec3 pos = player.eyePosition() + player.right() * rng.range(-2.5f, 2.5f) - player.flatForward() * rng.range(1.5f, 4.0f);
        playCue(rng.chance(0.5f) ? SFX_WHISPER : SFX_VOICE_FAR, pos, 0.55f + tensionValue * 0.3f, rng.range(0.85f, 1.15f));
        if (rng.chance(0.35f)) {
            static const char* lines[] = {
                "(fluestern, unverstaendlich)",
                "(eine Stimme, sehr weit weg)",
                "(jemand spricht in einem anderen Raum)",
                "(ein Name, vielleicht Ihrer)"
            };
            queueSubtitle(lines[rng.rangeInt(0, 4)], 3.2f);
        }
    }

    paTimer -= dt;
    if (paTimer <= 0.0f) {
        paTimer = rng.range(240.0f, 480.0f);
        Vec3 pos = player.eyePosition() + Vec3(0, 2.0f, 0);
        playCue(SFX_PA_STATIC, pos, 0.5f, 1.0f);
        queueSubtitle("LAUTSPRECHER: ...bitte auf Station... (Rauschen)", 4.2f);
    }
}

void Director::mutateRoom(int roomId, float strength) {
    if (!world || roomId < 0 || roomId >= (int)world->rooms().size()) return;
    Room& room = world->rooms()[(size_t)roomId];
    if (room.type == ROOM_STAIRWELL) return;

    for (int propId : room.props) {
        if (propId < 0 || propId >= (int)world->props().size()) continue;
        PropInstance& prop = world->props()[(size_t)propId];
        if (!prop.movable) continue;
        if (!rng.chance(0.35f * strength)) continue;

        Vec3 target = prop.originalPosition;
        target.x += rng.range(-1.4f, 1.4f) * strength;
        target.z += rng.range(-1.4f, 1.4f) * strength;
        target.x = clampf(target.x, room.rect.x + 0.6f, room.rect.x1() - 0.6f);
        target.z = clampf(target.z, room.rect.z + 0.6f, room.rect.z1() - 0.6f);
        world->moveProp(propId, target, prop.yaw + rng.range(-1.2f, 1.2f) * strength);
    }

    for (int lightId : room.lights) {
        if (lightId < 0 || lightId >= (int)world->lights().size()) continue;
        LightFixture& l = world->lights()[(size_t)lightId];
        if (l.emergency) continue;
        float roll = rng.nextFloat();
        if (roll < 0.14f * strength) world->breakLight(lightId);
        else if (roll < 0.42f * strength) l.flickerAmount = clampf(l.flickerAmount + rng.range(0.2f, 0.6f), 0.0f, 1.0f);
        else if (roll < 0.52f * strength) l.on = !l.on;
    }

    for (int doorId : room.doors) {
        if (doorId < 0 || doorId >= (int)world->doors().size()) continue;
        Door& d = world->doors()[(size_t)doorId];
        float roll = rng.nextFloat();
        if (roll < 0.16f * strength) {
            d.targetOpen = d.targetOpen > 0.5f ? 0.0f : 1.0f;
        } else if (roll < 0.24f * strength && !d.wasOpened) {
            if (d.locked) d.locked = false;
            else if (world->canLockDoor(doorId)) d.locked = true;
        }
    }

    room.mutated = true;
    bool known = false;
    for (int r : mutatedRooms) if (r == roomId) { known = true; break; }
    if (!known) mutatedRooms.push_back(roomId);
}

void Director::updateMutations(const Player& player, float dt, float time) {
    if (!world) return;
    const BehaviorProfile& p = behavior.profile();

    mutationTimer -= dt * (0.7f + p.sprintRatio * 1.5f + p.backtrackRatio * 1.2f + tensionValue * 0.6f);
    if (mutationTimer > 0.0f) return;
    mutationTimer = rng.range(35.0f, 85.0f) * lerpf(1.0f, 0.55f, p.backtrackRatio);

    if (behavior.lookedBackRecently() && rng.chance(0.65f)) {
        int room = behavior.currentRoom();
        if (room >= 0 && !world->rooms()[(size_t)room].props.empty()) {
            const Room& r = world->rooms()[(size_t)room];
            for (int propId : r.props) {
                PropInstance& prop = world->props()[(size_t)propId];
                if (!prop.movable) continue;
                if (inPlayerView(player, prop.position)) continue;
                if (!rng.chance(0.5f)) continue;
                Vec3 target = prop.position + Vec3(rng.range(-0.9f, 0.9f), 0, rng.range(-0.9f, 0.9f));
                world->moveProp(propId, target, prop.yaw + rng.range(-0.8f, 0.8f));
                playCue(SFX_METAL_DRAG, prop.position, 0.28f, rng.range(0.7f, 0.9f));
                break;
            }
        }
    }

    int favourite = behavior.mostVisitedRoom();
    if (favourite >= 0 && p.backtrackRatio > 0.28f && roomOffScreen(player, favourite) && rng.chance(0.8f)) {
        mutateRoom(favourite, 0.9f);
        return;
    }

    if (p.sprintRatio > 0.22f) {
        int room = behavior.currentRoom();
        if (room >= 0 && room < (int)world->rooms().size()) {
            const Room& r = world->rooms()[(size_t)room];
            for (int doorId : r.doors) {
                Door& d = world->doors()[(size_t)doorId];
                if (inPlayerView(player, d.center)) continue;
                if (d.wasOpened && rng.chance(0.4f) && world->canLockDoor(doorId)) {
                    d.targetOpen = 0.0f;
                    d.locked = true;
                    playCue(SFX_DOOR_CLOSE, d.center, 0.45f, 0.9f);
                    break;
                }
            }
        }
    }

    if (p.nervousness > 0.45f) {
        int room = behavior.currentRoom();
        if (room >= 0) {
            const Room& r = world->rooms()[(size_t)room];
            for (int lightId : r.lights) {
                LightFixture& l = world->lights()[(size_t)lightId];
                if (l.emergency || l.broken) continue;
                l.flickerAmount = clampf(l.flickerAmount + 0.35f, 0.0f, 1.0f);
                l.flickerRate = rng.range(1.4f, 3.6f);
            }
        }
    }

    const std::vector<int>& ignoredDoors = behavior.ignoredDoors();
    if (!ignoredDoors.empty() && rng.chance(0.55f)) {
        int doorId = ignoredDoors[(size_t)rng.rangeInt(0, (int)ignoredDoors.size())];
        if (doorId >= 0 && doorId < (int)world->doors().size()) {
            Door& d = world->doors()[(size_t)doorId];
            if (!inPlayerView(player, d.center)) {
                d.locked = false;
                d.targetOpen = 0.28f;
                int other = d.roomA == behavior.currentRoom() ? d.roomB : d.roomA;
                if (other >= 0 && other < (int)world->rooms().size()) {
                    for (int lightId : world->rooms()[(size_t)other].lights) {
                        LightFixture& l = world->lights()[(size_t)lightId];
                        if (!l.broken) { l.on = true; l.flickerAmount = std::max(l.flickerAmount, 0.25f); }
                    }
                }
                playCue(SFX_DOOR_CREAK, d.center, 0.4f, 0.85f);
            }
        }
    }

    if (p.idleRatio > 0.3f && rng.chance(0.4f)) {
        int room = behavior.currentRoom();
        if (room >= 0) {
            const Room& r = world->rooms()[(size_t)room];
            Vec3 behind = player.position() - player.flatForward() * 3.0f + Vec3(0, 1.2f, 0);
            playCue(SFX_STEP_TILE, behind, 0.5f, 0.9f);
        }
    }
}

void Director::spawnPresence(const Vec3& pos, float faceYaw, int type, int pose) {
    presence.configure(type, rng.state() ^ (u64)(pos.x * 1000.0f));
    presence.position = pos;
    presence.yaw = faceYaw;
    presence.setPose(pose, 0.01f);
    presence.snapPose();
    presence.visibility = 1.0f;
    presence.active = true;
    presenceActive = true;
    presenceSeen = false;
    presenceFade = 1.0f;
    presenceTimer = 0.0f;
}

void Director::despawnPresence(bool fade) {
    presenceActive = false;
    presence.active = false;
    presenceFade = 0.0f;
    if (presenceSeen) behavior.notifyPresenceSeen(true);
}

bool Director::presenceVisible() const {
    return presenceActive && presence.visibility > 0.02f;
}

void Director::updateScares(Player& player, float dt, float time) {
    if (!world) return;
    const BehaviorProfile& p = behavior.profile();

    if (scareCooldown > 0.0f) scareCooldown -= dt;

    if (presenceActive) {
        presenceTimer += dt;
        presence.update(dt, time, player.eyePosition(), true);
        if (!presenceSeen && playerLooksAt(player, presence.headPosition(), 0.72f) &&
            world->physics().lineOfSight(player.eyePosition(), presence.headPosition())) {
            presenceSeen = true;
            behavior.notifyPresenceSeen(false);
        }
    }

    if (currentScare >= 0) {
        ScareState& s = scares[currentScare];
        s.timer += dt;

        switch (currentScare) {
        case SCARE_DOOR_NURSE: {
            if (s.stage == 0 && s.timer > 0.55f) {
                s.stage = 1;
                if (s.targetRoom >= 0) world->setRoomLights(s.targetRoom, false, true);
                for (int lid : world->rooms()[(size_t)clampi(behavior.currentRoom(), 0, (int)world->rooms().size() - 1)].lights)
                    world->lights()[(size_t)lid].flickerAmount = 1.0f;
                playCue(SFX_LIGHT_POP, presence.position, 0.9f, 1.0f);
                cameraShake = 0.22f;
                flashlightDisturb = 0.9f;
            } else if (s.stage == 1 && s.timer > 1.35f) {
                despawnPresence(false);
                queueSubtitle("(Das Licht kommt zurueck. Der Raum ist leer.)", 3.0f);
                currentScare = -1;
            }
            break;
        }
        case SCARE_CORRIDOR_PATIENT: {
            if (s.stage == 0) {
                if (!playerLooksAt(player, presence.position + Vec3(0, 1.2f, 0), 0.80f) || s.timer > 14.0f) {
                    despawnPresence(false);
                    playCue(SFX_STING_LOW, player.eyePosition(), 0.35f, 1.0f);
                    currentScare = -1;
                }
            }
            break;
        }
        case SCARE_MIRROR_FIGURE: {
            if (s.stage == 0 && s.timer > 1.6f) {
                s.stage = 1;
                despawnPresence(false);
                queueSubtitle("(Sie drehen sich um. Niemand.)", 2.6f);
                currentScare = -1;
            } else if (s.stage == 0 && !playerLooksAt(player, s.anchor, 0.6f)) {
                despawnPresence(false);
                currentScare = -1;
            }
            break;
        }
        case SCARE_WHEELCHAIR: {
            if (s.targetProp >= 0 && s.targetProp < (int)world->props().size()) {
                PropInstance& prop = world->props()[(size_t)s.targetProp];
                float dist = distance(prop.position, player.position());
                if (s.stage == 0) {
                    Vec3 dir(std::sin(prop.yaw), 0, -std::cos(prop.yaw));
                    world->moveProp(s.targetProp, prop.position + dir * dt * 0.55f, prop.yaw);
                    if (dist < 4.2f || s.timer > 9.0f) {
                        s.stage = 1;
                        s.timer = 0.0f;
                        playCue(SFX_WHEELCHAIR, prop.position, 0.4f, 0.7f);
                        queueSubtitle("(Der Rollstuhl haelt an. Die Raeder drehen sich weiter.)", 3.4f);
                    }
                } else if (s.timer > 4.0f) {
                    currentScare = -1;
                }
            } else {
                currentScare = -1;
            }
            break;
        }
        case SCARE_ELEVATOR_DOCTOR: {
            if (s.stage == 0 && s.timer > 2.2f) {
                s.stage = 1;
                if (s.targetDoor >= 0) world->doors()[(size_t)s.targetDoor].targetOpen = 0.0f;
                despawnPresence(false);
                playCue(SFX_ELEVATOR_DING, s.anchor, 0.6f, 1.0f);
                queueSubtitle("(Die Tuer schliesst sich.)", 2.6f);
            } else if (s.stage == 1 && s.timer > 6.5f) {
                if (s.targetDoor >= 0) world->doors()[(size_t)s.targetDoor].targetOpen = 1.0f;
                playCue(SFX_ELEVATOR_DING, s.anchor, 0.6f, 0.98f);
                currentScare = -1;
            }
            break;
        }
        case SCARE_PA_FIGURE: {
            if (s.stage == 0) {
                float dist = distance(presence.position, player.position());
                if (dist < 7.0f || s.timer > 16.0f) {
                    despawnPresence(false);
                    queueSubtitle("(Der Flur ist leer.)", 2.4f);
                    currentScare = -1;
                }
            }
            break;
        }
        case SCARE_KEY_TURNAROUND: {
            if (s.stage == 0 && playerLooksAt(player, presence.position + Vec3(0, 1.3f, 0), 0.7f)) {
                s.stage = 1;
                s.timer = 0.0f;
                playCue(SFX_STING_HIGH, presence.position, 0.5f, 1.0f);
            } else if (s.stage == 1 && s.timer > 1.1f) {
                int room = behavior.currentRoom();
                if (room >= 0) {
                    for (int lid : world->rooms()[(size_t)room].lights)
                        world->lights()[(size_t)lid].flickerAmount = 1.0f;
                }
                flashlightDisturb = 1.0f;
                despawnPresence(false);
                currentScare = -1;
            } else if (s.timer > 12.0f) {
                despawnPresence(false);
                currentScare = -1;
            }
            break;
        }
        case SCARE_FOOTSTEPS_BED: {
            if (s.stage == 0 && s.timer > 1.4f) {
                s.stage = 1;
                if (s.targetProp >= 0) {
                    Vec3 target = player.position() + player.flatForward() * -3.4f;
                    target.y = player.position().y;
                    world->moveProp(s.targetProp, target, player.yawAngle() + HALF_PI);
                    world->hideProp(s.targetProp, false);
                }
                queueSubtitle("(Ein Bett steht jetzt im Flur.)", 3.0f);
            } else if (s.stage == 1 && s.timer > 5.0f) {
                currentScare = -1;
            }
            break;
        }
        default:
            currentScare = -1;
            break;
        }
        return;
    }

    if (scareCooldown > 0.0f) return;
    if (p.totalTime < 90.0f) return;

    int room = behavior.currentRoom();
    if (room < 0 || room >= (int)world->rooms().size()) return;
    const Room& current = world->rooms()[(size_t)room];

    std::vector<int> candidates;
    for (int i = 0; i < SCARE_COUNT; i++) if (!scares[i].used) candidates.push_back(i);
    if (candidates.empty()) return;

    rng.shuffle(candidates);

    for (int id : candidates) {
        ScareState& s = scares[id];

        if (id == SCARE_DOOR_NURSE) {
            for (int doorId : current.doors) {
                const Door& d = world->doors()[(size_t)doorId];
                if (d.openAmount < 0.6f) continue;
                if (distance(d.center, player.position()) > 3.2f) continue;
                if (!playerLooksAt(player, d.center + Vec3(0, 1.2f, 0), 0.86f)) continue;
                int other = d.roomA == room ? d.roomB : d.roomA;
                if (other < 0) continue;
                Vec3 pos = d.center;
                Vec3 into = normalize(world->roomCenter(other) - d.center);
                pos += into * 0.85f;
                pos.y = world->rooms()[(size_t)other].floorY;
                float faceYaw = std::atan2(-into.x, into.z);
                spawnPresence(pos, faceYaw, HUMAN_NURSE, POSE_STAND_STILL);
                s.used = true;
                s.stage = 0;
                s.timer = 0.0f;
                s.targetRoom = other;
                currentScare = id;
                scareCooldown = rng.range(420.0f, 760.0f);
                return;
            }
        }

        if (id == SCARE_CORRIDOR_PATIENT && current.type == ROOM_CORRIDOR) {
            bool alongX = current.rect.w > current.rect.d;
            float length_ = alongX ? current.rect.w : current.rect.d;
            if (length_ < 11.0f) continue;
            Vec3 fwd = player.flatForward();
            Vec3 pos = player.position() + fwd * std::min(length_ * 0.75f, 15.0f);
            if (world->roomAt(pos + Vec3(0, 0.6f, 0)) != room) continue;
            pos.y = current.floorY;
            spawnPresence(pos, std::atan2(-fwd.x, fwd.z), HUMAN_PATIENT, POSE_STAND_STILL);
            s.used = true;
            s.stage = 0;
            s.timer = 0.0f;
            currentScare = id;
            scareCooldown = rng.range(420.0f, 760.0f);
            return;
        }

        if (id == SCARE_MIRROR_FIGURE && current.type == ROOM_BATHROOM) {
            for (int propId : current.props) {
                const PropInstance& prop = world->props()[(size_t)propId];
                if (prop.type != PROP_MIRROR) continue;
                if (distance(prop.position, player.eyePosition()) > 2.4f) continue;
                if (!playerLooksAt(player, prop.position, 0.88f)) continue;
                Vec3 behind = player.position() - player.flatForward() * 1.9f;
                behind.y = current.floorY;
                spawnPresence(behind, player.yawAngle() + PI, rng.chance(0.5f) ? HUMAN_DOCTOR : HUMAN_PATIENT, POSE_STAND_STILL);
                s.used = true;
                s.stage = 0;
                s.timer = 0.0f;
                s.anchor = prop.position;
                currentScare = id;
                scareCooldown = rng.range(420.0f, 760.0f);
                return;
            }
        }

        if (id == SCARE_WHEELCHAIR && current.type == ROOM_CORRIDOR) {
            for (int propId : current.props) {
                PropInstance& prop = world->props()[(size_t)propId];
                if (prop.type != PROP_WHEELCHAIR) continue;
                float dist = distance(prop.position, player.position());
                if (dist < 6.0f || dist > 18.0f) continue;
                if (!playerLooksAt(player, prop.position, 0.7f)) continue;
                Vec3 toPlayer = normalize(player.position() - prop.position);
                prop.yaw = std::atan2(toPlayer.x, -toPlayer.z) + HALF_PI;
                playCue(SFX_WHEELCHAIR, prop.position, 0.5f, 0.85f);
                s.used = true;
                s.stage = 0;
                s.timer = 0.0f;
                s.targetProp = propId;
                currentScare = id;
                scareCooldown = rng.range(420.0f, 760.0f);
                return;
            }
        }

        if (id == SCARE_ELEVATOR_DOCTOR && current.type == ROOM_CORRIDOR) {
            for (int doorId : current.doors) {
                Door& d = world->doors()[(size_t)doorId];
                if (d.kind != DOOR_ELEVATOR) continue;
                if (distance(d.center, player.position()) > 6.5f) continue;
                if (!playerLooksAt(player, d.center + Vec3(0, 1.2f, 0), 0.8f)) continue;
                d.locked = false;
                d.targetOpen = 1.0f;
                int other = d.roomA == room ? d.roomB : d.roomA;
                Vec3 into = normalize(world->roomCenter(other) - d.center);
                Vec3 pos = d.center + into * 0.9f;
                pos.y = current.floorY;
                spawnPresence(pos, std::atan2(-into.x, into.z), HUMAN_DOCTOR, POSE_STAND_STILL);
                playCue(SFX_ELEVATOR_DING, d.center, 0.7f, 1.0f);
                s.used = true;
                s.stage = 0;
                s.timer = 0.0f;
                s.targetDoor = doorId;
                s.anchor = d.center;
                currentScare = id;
                scareCooldown = rng.range(420.0f, 760.0f);
                return;
            }
        }

        if (id == SCARE_PA_FIGURE && current.type == ROOM_CORRIDOR && rng.chance(0.5f)) {
            bool alongX = current.rect.w > current.rect.d;
            float length_ = alongX ? current.rect.w : current.rect.d;
            if (length_ < 9.0f) continue;
            Vec3 fwd = player.flatForward();
            Vec3 pos = player.position() + fwd * std::min(length_ * 0.8f, 17.0f);
            if (world->roomAt(pos + Vec3(0, 0.6f, 0)) != room) continue;
            pos.y = current.floorY;
            playCue(SFX_PA_STATIC, player.eyePosition() + Vec3(0, 2.2f, 0), 0.6f, 1.0f);
            queueSubtitle("LAUTSPRECHER: ...alle verbleibenden... (Rauschen)", 4.0f);
            spawnPresence(pos, std::atan2(-fwd.x, fwd.z), HUMAN_CLEANER, POSE_STAND_STILL);
            s.used = true;
            s.stage = 0;
            s.timer = 0.0f;
            currentScare = id;
            scareCooldown = rng.range(420.0f, 760.0f);
            return;
        }

        if (id == SCARE_FOOTSTEPS_BED && current.type == ROOM_CORRIDOR) {
            int bed = -1;
            for (int propId : current.props) {
                if (world->props()[(size_t)propId].type == PROP_GURNEY) { bed = propId; break; }
            }
            if (bed < 0) {
                for (const auto& prop : world->props()) {
                    if (prop.type == PROP_GURNEY && prop.floor == current.floor) { bed = prop.id; break; }
                }
            }
            if (bed < 0) continue;
            Vec3 behind = player.position() - player.flatForward() * 2.6f + Vec3(0, 1.0f, 0);
            playCue(SFX_STEP_TILE, behind, 0.9f, 1.25f);
            playCue(SFX_STEP_TILE, behind, 0.85f, 1.32f);
            s.used = true;
            s.stage = 0;
            s.timer = 0.0f;
            s.targetProp = bed;
            currentScare = id;
            scareCooldown = rng.range(420.0f, 760.0f);
            return;
        }

        if (id == SCARE_KEY_TURNAROUND) {
            continue;
        }
    }
}

void Director::update(Player& player, float dt, float time) {
    if (!world) return;
    behavior.update(player, *world, dt, time);
    updateTension(player, dt);
    updateAmbientEvents(player, dt, time);
    updateMutations(player, dt, time);
    updateScares(player, dt, time);

    if (presenceActive) {
        presence.visibility = lerpf(presence.visibility, 1.0f, 1.0f - std::exp(-6.0f * dt));
    } else if (presence.visibility > 0.0f) {
        presence.visibility = lerpf(presence.visibility, 0.0f, 1.0f - std::exp(-9.0f * dt));
        if (presence.visibility < 0.02f) presence.active = false;
    }

    if (cameraShake > 0.001f) player.addShake(cameraShake, 0.3f);
}

void Director::submitPresences(Renderer& renderer) {
    if (!rig) return;
    if (presence.active && presence.visibility > 0.02f) presence.submit(renderer, *rig);
}

int Director::chooseEnding() const {
    const BehaviorProfile& p = behavior.profile();

    if (p.truthLayers >= 3 && p.avoidance < 0.4f && p.presencesSeen >= 2) return ENDING_WITNESS;
    if (p.darkRatio > 0.45f && dreadValue > 0.55f && sanityValue < 0.45f) return ENDING_DISSOLUTION;
    if (p.backtrackRatio > 0.55f && p.explorationRate < 0.8f) return ENDING_LOOP;
    if (p.sprintRatio > 0.24f && p.documentsRead <= 2) return ENDING_DENIAL;
    return ENDING_RELEASE;
}

}
