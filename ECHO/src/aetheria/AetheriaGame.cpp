#include "AetheriaGame.h"
#include "../core/Log.h"

using namespace em;
using namespace echo;

namespace aeth {

namespace {
const Vec4 kInk(0.94f, 0.92f, 0.86f, 1.0f);
const Vec4 kGold(0.98f, 0.82f, 0.45f, 1.0f);
const Vec4 kDim(0.72f, 0.70f, 0.64f, 1.0f);
const Vec4 kPanel(0.05f, 0.05f, 0.06f, 0.78f);

const char* kIdleTalk[] = {
    "Die Wege sind sicher, solange die Feuer brennen.",
    "Frag die Alten am Brunnen, die wissen mehr als ich.",
    "Im Norden steht Stein, der aelter ist als jedes Dorf.",
    "Nachts sollte man nicht allein durch das Moor gehen.",
    "Danke fuer alles, was du fuer uns getan hast."
};
}

void Traveller::grantXp(int amount) {
    xp += amount;
    while (xp >= xpNext) {
        xp -= xpNext;
        level++;
        xpNext = (int)(xpNext * 1.32f);
        maxHealth += 12.0f;
        maxStamina += 6.0f;
        maxMana += 8.0f;
        health = maxHealth;
        stamina = maxStamina;
        mana = maxMana;
    }
}

bool AetheriaGame::init(Window* w, Renderer* r, UIRenderer* u, AudioEngine* a) {
    window = w;
    renderer = r;
    ui = u;
    audio = a;
    coopRig.build();
    coop.init("aetheria", &coopRig);
    coopMenu.init(&coop, window, ui, audio);
    return true;
}

void AetheriaGame::shutdown() {
    coop.shutdown();
    coopRig.destroy();
    map.destroy();
    weapon.destroy();
    quests.clear();
    land.destroy();
    running = false;
}

void AetheriaGame::buildWeapon() {
    MeshBuilder mb;
    mb.setMaterial(MAT_WOOD_OLD);
    mb.setColor(Vec4(0.32f, 0.22f, 0.16f, 1.0f));
    mb.addCylinder(Vec3(0, -0.20f, 0), 0.028f, 0.22f, 8, true);
    mb.finishSubMesh();

    mb.setMaterial(MAT_STEEL);
    mb.setColor(Vec4(0.86f, 0.86f, 0.90f, 1.0f));
    mb.addBox(Vec3(0, 0.02f, 0), Vec3(0.085f, 0.022f, 0.022f));
    mb.addBox(Vec3(0, 0.36f, 0), Vec3(0.030f, 0.34f, 0.010f));
    mb.addCone(Vec3(0, 0.70f, 0), 0.030f, 0.002f, 0.10f, 4, false);
    mb.finishSubMesh();

    mb.setMaterial(MAT_LIGHT_PANEL);
    mb.setColor(Vec4(0.55f, 0.80f, 1.0f, 1.0f));
    mb.addSphere(Vec3(0, -0.32f, 0), 0.030f, 5, 7);
    mb.finishSubMesh();

    mb.build(weapon);
}

void AetheriaGame::open(u64 seed) {
    if (!worldReady) {
        land.generate(seed);
        map.destroy();
        map.build(land.terrain());
        if (!weapon.valid()) buildWeapon();
        worldReady = true;
        runStarted = false;
    }

    menuFocus = land.settlements().empty() ? land.spawnPoint() : land.settlements()[0].center;
    menuOrbit = 0.0f;
    menuTime = 0.0f;
    menuIndex = 0;
    screen = AETH_MENU;
    running = true;
    exitRequested = false;
    mapOpen = false;
    hits.clear();
    window->setCursorLocked(false);
}

void AetheriaGame::beginRun() {
    quests.build(land, 0xAE71EA1AULL);

    for (Settlement& s : land.settlements()) s.visited = false;
    for (Landmark& l : land.landmarks()) l.found = false;

    position = land.spawnPoint() + Vec3(0, 0.2f, 0);
    velocity = Vec3(0, 0, 0);
    yaw = 0.0f;
    pitch = -0.06f;
    if (!land.settlements().empty()) {
        const Settlement& home = land.settlements()[0];
        Vec2 toGiver(home.giverPos.x - position.x, home.giverPos.z - position.z);
        if (lengthSq(toGiver) > 0.25f) yaw = std::atan2(toGiver.x, -toGiver.y);
    }
    hero = Traveller();
    for (int i = 0; i < FLORA_COUNT; i++) satchel[i] = 0;

    toasts.clear();
    speech.clear();
    speaker.clear();
    speechTimer = 0.0f;
    prompt.clear();
    mapOpen = false;
    swing = 0.0f;
    swingCooldown = 0.0f;
    damageFlash = 0.0f;

    lamp.reset();
    lamp.setBattery(1.0f);
    lamp.baseIntensity = 8.4f;
    lamp.baseRange = 22.0f;

    if (!land.settlements().empty()) {
        land.settlements()[0].visited = true;
        quests.revealVillage(0);
    }
    rebuildMarkers();
    refreshObjective();

    regionLabel = land.regionName(position);
    regionToast = regionLabel;
    regionToastTimer = 5.0f;
    runStarted = true;
    screen = AETH_PLAYING;
    running = true;
    exitRequested = false;
    window->setCursorLocked(true);
    addToast("TAB oeffnet die Karte");
}

CameraData AetheriaGame::camera(float aspect) const {
    CameraData cam;
    cam.position = position + Vec3(0, eyeHeight + std::sin(bobPhase * 2.0f) * 0.035f * bobAmount, 0);
    cam.forward = sphericalDir(yaw, pitch);
    cam.fovY = 1.24f;
    cam.nearPlane = 0.08f;
    cam.farPlane = 900.0f;
    cam.update(aspect);
    return cam;
}

void AetheriaGame::addToast(const std::string& text) {
    Toast t;
    t.text = text;
    t.timer = 4.2f;
    toasts.push_back(t);
    if (toasts.size() > 5) toasts.erase(toasts.begin());
}

void AetheriaGame::say(const std::string& who, const std::string& text) {
    speaker = who;
    speech = text;
    speechTimer = 7.0f;
}

void AetheriaGame::refreshObjective() {
    objectiveValid = false;
    objectiveLabel.clear();
    objectiveHint.clear();

    int tracked = quests.trackedIndex();
    if (tracked < 0) return;
    const Quest& q = quests.at(tracked);
    const std::vector<Settlement>& vs = land.settlements();

    if (q.state == QUEST_READY) {
        if (q.village < 0 || q.village >= (int)vs.size()) return;
        objectivePos = vs[(size_t)q.village].giverPos;
        objectiveLabel = q.giver;
        objectiveHint = "Belohnung abholen";
        objectiveValid = true;
        return;
    }

    if (q.kind == QUEST_GATHER) {
        int idx = land.nearestOfType(position, q.target, 260.0f);
        if (idx >= 0) {
            objectivePos = land.floraPosition(idx);
            objectiveLabel = land.harvestName(q.target);
            objectiveHint = "Sammeln mit E";
            objectiveValid = true;
            return;
        }
        objectivePos = q.marker;
        objectiveLabel = q.place;
        objectiveHint = std::string(land.harvestName(q.target)) + " suchen";
        objectiveValid = true;
        return;
    }

    if (q.kind == QUEST_HUNT) {
        if (q.village < 0 || q.village >= (int)vs.size()) return;
        objectivePos = vs[(size_t)q.village].center;
        objectiveLabel = vs[(size_t)q.village].name;
        objectiveHint = "Umgebung durchsuchen";
        objectiveValid = true;
        return;
    }

    objectivePos = q.marker;
    objectiveLabel = q.kind == QUEST_TRAVEL && q.target >= 0 && q.target < (int)vs.size()
                         ? vs[(size_t)q.target].name
                         : (q.kind == QUEST_LANDMARK && q.target >= 0 && q.target < (int)land.landmarks().size()
                                ? land.landmarks()[(size_t)q.target].name
                                : q.place);
    objectiveHint = "Ziel erreichen";
    objectiveValid = true;
}

bool AetheriaGame::projectToScreen(const Vec3& world, float w, float h, Vec2& out, bool& behind) const {
    Vec4 clip = lastCam.viewProj * Vec4(world, 1.0f);
    behind = clip.w <= 0.001f;
    if (behind) {
        Vec3 toTarget = world - lastCam.position;
        Vec3 right = normalize(cross(lastCam.forward, Vec3(0, 1, 0)));
        float side = dot(toTarget, right);
        out = Vec2(side >= 0.0f ? w * 0.94f : w * 0.06f, h * 0.5f);
        return true;
    }
    float ndcX = clip.x / clip.w;
    float ndcY = clip.y / clip.w;
    out = Vec2((ndcX * 0.5f + 0.5f) * w, (1.0f - (ndcY * 0.5f + 0.5f)) * h);
    return true;
}

void AetheriaGame::rebuildMarkers() {
    markers.clear();

    for (const Settlement& s : land.settlements()) {
        MapMarker m;
        m.world = Vec2(s.center.x, s.center.z);
        m.label = s.name;
        m.color = s.visited ? Vec4(0.98f, 0.86f, 0.52f, 1.0f) : Vec4(0.72f, 0.66f, 0.52f, 0.72f);
        m.shape = MARK_VILLAGE;
        m.known = true;
        markers.push_back(m);
    }

    for (const Landmark& l : land.landmarks()) {
        MapMarker m;
        m.world = Vec2(l.position.x, l.position.z);
        m.label = l.found ? l.name : std::string();
        m.color = l.found ? Vec4(0.62f, 0.86f, 1.0f, 1.0f) : Vec4(0.52f, 0.60f, 0.70f, 0.60f);
        m.shape = MARK_LANDMARK;
        m.known = true;
        m.onMinimap = l.found;
        markers.push_back(m);
    }

    int tracked = quests.trackedIndex();
    if (tracked >= 0) {
        const Quest& q = quests.at(tracked);
        MapMarker m;
        m.world = Vec2(q.marker.x, q.marker.z);
        m.label = q.title;
        m.color = Vec4(0.55f, 0.95f, 0.60f, 1.0f);
        m.shape = MARK_QUEST;
        m.known = true;
        markers.push_back(m);
    }

    for (int i = 0; i < quests.count(); i++) {
        const Quest& q = quests.at(i);
        if (q.state != QUEST_READY || i == tracked) continue;
        const std::vector<Settlement>& vs = land.settlements();
        if (q.village >= (int)vs.size()) continue;
        MapMarker m;
        m.world = Vec2(vs[(size_t)q.village].center.x, vs[(size_t)q.village].center.z);
        m.label = "Belohnung";
        m.color = Vec4(0.98f, 0.72f, 0.35f, 1.0f);
        m.shape = MARK_QUEST;
        m.known = true;
        markers.push_back(m);
    }
}

void AetheriaGame::updateMovement(float dt) {
    Input& in = window->input();

    if (!mapOpen) {
        Vec2 look = in.mouseDelta();
        yaw = wrapAngle(yaw + look.x * sensitivity);
        pitch = clampf(pitch - look.y * sensitivity, -1.45f, 1.45f);
    }

    Vec3 fwd = normalize(Vec3(std::sin(yaw), 0.0f, -std::cos(yaw)));
    Vec3 right = normalize(cross(fwd, Vec3(0, 1, 0)));

    Vec2 move(0, 0);
    if (!mapOpen) {
        move = Vec2((in.key(KEY_D) ? 1.0f : 0.0f) - (in.key(KEY_A) ? 1.0f : 0.0f),
                    (in.key(KEY_W) ? 1.0f : 0.0f) - (in.key(KEY_S) ? 1.0f : 0.0f));
    }
    float len = length(move);
    if (len > 1.0f) move /= len;

    sprinting = in.key(KEY_SHIFT) && move.y > 0.2f && hero.stamina > 1.0f;
    float speed = sprinting ? 8.4f : 4.6f;
    if (in.key(KEY_CONTROL)) speed = 2.2f;

    Vec3 wish = fwd * move.y + right * move.x;
    if (lengthSq(wish) > 1e-5f) wish = normalize(wish);

    Vec3 target = wish * (speed * std::min(len, 1.0f));
    Vec3 horiz(velocity.x, 0, velocity.z);
    float rate = grounded ? 14.0f : 3.0f;
    horiz = horiz + (target - horiz) * (1.0f - std::exp(-rate * dt));
    velocity.x = horiz.x;
    velocity.z = horiz.z;

    velocity.y -= 22.0f * dt;
    if (velocity.y < -45.0f) velocity.y = -45.0f;

    if (grounded && !mapOpen && in.keyPressed(KEY_SPACE) && hero.stamina > 8.0f) {
        velocity.y = 7.2f;
        hero.stamina -= 8.0f;
        grounded = false;
    }

    Vec3 next = position + velocity * dt;
    next = land.resolveMovement(position, next, 0.42f);

    float ground = land.groundHeight(next.x, next.z);
    if (next.y <= ground) {
        next.y = ground;
        if (velocity.y < 0.0f) velocity.y = 0.0f;
        grounded = true;
    } else {
        grounded = false;
    }

    float swimLine = land.terrain().waterLevel();
    if (next.y < swimLine - 0.4f) {
        next.y = lerpf(next.y, swimLine - 0.4f, 1.0f - std::exp(-6.0f * dt));
        velocity.y = std::max(velocity.y, 0.0f);
        grounded = true;
    }

    position = next;

    float sp = length(Vec2(velocity.x, velocity.z));
    bobAmount = lerpf(bobAmount, grounded ? clampf(sp / 6.0f, 0.0f, 1.0f) : 0.0f, 1.0f - std::exp(-8.0f * dt));
    bobPhase += dt * (sprinting ? 11.0f : 7.4f) * clampf(sp / 4.0f, 0.0f, 1.4f);

    if (sprinting && sp > 0.5f) hero.stamina = std::max(0.0f, hero.stamina - dt * 14.0f);
    else hero.stamina = std::min(hero.maxStamina, hero.stamina + dt * 11.0f);
    hero.mana = std::min(hero.maxMana, hero.mana + dt * 3.0f);
    hero.health = std::min(hero.maxHealth, hero.health + dt * 1.6f);

    if (grounded && sp > 0.6f) {
        footstepAccum += sp * dt;
        if (footstepAccum > 1.35f) {
            footstepAccum = 0.0f;
            int biome = land.terrain().biomeAt(position.x, position.z);
            int sound = biome == BIOME_SNOW ? SFX_STEP_DEBRIS : (biome == BIOME_MARSH ? SFX_STEP_WATER : SFX_STEP_CONCRETE);
            PlayParams p;
            p.position = position;
            p.volume = 0.30f;
            p.pitch = 0.92f + hash11(bobPhase) * 0.2f;
            p.maxDistance = 14.0f;
            p.reverbSend = 0.18f;
            audio->play(sound, p);
        }
    }
}

void AetheriaGame::updateDiscovery(float dt) {
    std::string here = land.regionName(position);
    if (here != regionLabel) {
        regionLabel = here;
        regionToast = here;
        regionToastTimer = 5.0f;
        hero.discovered++;
        hero.grantXp(45);
        audio->play2D(SFX_ELEVATOR_DING, 0.24f, 1.25f);
    }
    if (regionToastTimer > 0.0f) regionToastTimer -= dt;

    int v = land.villageAt(position, 8.0f);
    if (v >= 0 && !land.settlements()[(size_t)v].visited) {
        land.settlements()[(size_t)v].visited = true;
        quests.revealVillage(v);
        addToast(land.settlements()[(size_t)v].name + " entdeckt");
        hero.grantXp(80);
        rebuildMarkers();
        coop.sendInteract("npc", std::to_string(v), 1.0, position);
    }

    int lm = land.landmarkAt(position, 0.0f);
    if (lm >= 0 && !land.landmarks()[(size_t)lm].found) {
        land.landmarks()[(size_t)lm].found = true;
        addToast(land.landmarks()[(size_t)lm].name + " entdeckt");
        hero.grantXp(110);
        hero.gold += 15;
        rebuildMarkers();
    }

    int ready = quests.checkPositions(position);
    if (ready >= 0) {
        const Quest& q = quests.at(ready);
        addToast(q.title + " - zurueck zu " + q.giver);
        audio->play2D(SFX_ELEVATOR_DING, 0.30f, 1.05f);
        rebuildMarkers();
    }
}

void AetheriaGame::updateInteraction(float dt) {
    if (speechTimer > 0.0f) speechTimer -= dt;
    for (size_t i = 0; i < toasts.size();) {
        toasts[i].timer -= dt;
        if (toasts[i].timer <= 0.0f) toasts.erase(toasts.begin() + (long)i);
        else i++;
    }

    prompt.clear();
    hoverVillage = -1;
    hoverFlora = -1;
    if (mapOpen) return;

    const std::vector<Settlement>& vs = land.settlements();
    float bestGiver = 3.6f;
    for (int i = 0; i < (int)vs.size(); i++) {
        float d = distance(Vec2(vs[(size_t)i].giverPos.x, vs[(size_t)i].giverPos.z), Vec2(position.x, position.z));
        if (d < bestGiver) {
            bestGiver = d;
            hoverVillage = i;
        }
    }

    if (hoverVillage >= 0) {
        const Settlement& s = vs[(size_t)hoverVillage];
        int ready = quests.readyFor(hoverVillage);
        int offer = quests.offeredFor(hoverVillage);
        if (ready >= 0) prompt = "E   " + s.giverName + "  -  Auftrag abgeben";
        else if (offer >= 0) prompt = "E   " + s.giverName + "  -  Auftrag annehmen";
        else prompt = "E   " + s.giverName + "  -  Sprechen";
    } else {
        hoverFlora = land.harvestableNear(position, 2.7f);
        if (hoverFlora >= 0) {
            prompt = std::string("E   ") + land.harvestName(land.floraTypeOf(hoverFlora)) + " sammeln";
        }
    }

    Input& in = window->input();
    if (!in.keyPressed(KEY_E)) return;

    if (hoverVillage >= 0) {
        const Settlement& s = vs[(size_t)hoverVillage];
        int ready = quests.readyFor(hoverVillage);
        if (ready >= 0) {
            Quest q = quests.at(ready);
            quests.complete(ready);
            hero.grantXp(q.xp);
            hero.gold += q.gold;
            say(s.giverName, q.thanks);
            char buf[160];
            std::snprintf(buf, sizeof(buf), "%s erledigt   +%d XP  +%d Gold", q.title.c_str(), q.xp, q.gold);
            addToast(buf);
            audio->play2D(SFX_PICKUP, 0.42f, 1.0f);
            quests.cycleTracked();
            rebuildMarkers();
            refreshObjective();
            return;
        }
        int offer = quests.offeredFor(hoverVillage);
        if (offer >= 0) {
            quests.accept(offer);
            const Quest& q = quests.at(offer);
            say(s.giverName, q.offer);
            addToast("Neuer Auftrag: " + q.title);
            addToast(q.task);
            audio->play2D(SFX_ELEVATOR_DING, 0.32f, 1.15f);
            quests.setTracked(offer);
            rebuildMarkers();
            refreshObjective();
            return;
        }
        int idx = (int)(hash11((float)hoverVillage * 3.7f + land.clock().timeOfDay * 11.0f) * 5.0f);
        say(s.giverName, kIdleTalk[clampi(idx, 0, 4)]);
        return;
    }

    if (hoverFlora >= 0) {
        int type = land.floraTypeOf(hoverFlora);
        Vec3 at = land.floraPosition(hoverFlora);
        coop.sendInteract("harvest", std::to_string(hoverFlora), 1.0, at);
        land.harvest(hoverFlora);
        satchel[clampi(type, 0, FLORA_COUNT - 1)]++;
        hero.gathered++;
        hero.grantXp(10);

        PlayParams p;
        p.position = at;
        p.volume = 0.34f;
        p.pitch = 1.25f;
        p.maxDistance = 12.0f;
        audio->play(SFX_PAPER, p);

        bool relevant = quests.reportGather(type);
        char buf[160];
        if (relevant) {
            int tracked = quests.trackedIndex();
            int shownProgress = 0, shownNeed = 0;
            for (int i = 0; i < quests.count(); i++) {
                const Quest& q = quests.at(i);
                if (q.kind == QUEST_GATHER && q.target == type && (q.state == QUEST_ACTIVE || q.state == QUEST_READY)) {
                    shownProgress = q.progress;
                    shownNeed = q.needed;
                    if (i == tracked) break;
                }
            }
            std::snprintf(buf, sizeof(buf), "%s  %d/%d", land.harvestName(type), shownProgress, shownNeed);
        } else {
            std::snprintf(buf, sizeof(buf), "%s  x%d", land.harvestName(type), satchel[clampi(type, 0, FLORA_COUNT - 1)]);
        }
        addToast(buf);
        rebuildMarkers();
        refreshObjective();
    }
}

void AetheriaGame::updateCombat(float dt) {
    if (swing > 0.0f) swing -= dt;
    if (swingCooldown > 0.0f) swingCooldown -= dt;
    if (damageFlash > 0.0f) damageFlash -= dt;

    Input& in = window->input();
    if (!mapOpen && in.mousePressed(MOUSE_LEFT) && swingCooldown <= 0.0f && hero.stamina > 6.0f) {
        swing = 0.42f;
        swingCooldown = 0.52f;
        hero.stamina -= 6.0f;

        audio->play2D(SFX_METAL_DRAG, 0.20f, 1.7f);

        Vec3 origin = position + Vec3(0, eyeHeight, 0);
        StrikeResult r = land.strike(origin, sphericalDir(yaw, pitch), 3.2f, 24.0f + hero.level * 4.0f);
        if (r.hit && coop.playing()) {
            js::Value fx = js::Value::object();
            fx.set("x", r.point.x);
            fx.set("y", r.point.y);
            fx.set("z", r.point.z);
            coop.sendEffect("hit", fx);
        }
        if (r.hit) {
            PlayParams p;
            p.position = r.point;
            p.volume = 0.40f;
            p.pitch = 1.35f;
            p.maxDistance = 22.0f;
            audio->play(SFX_PIPE_KNOCK, p);
        }
        if (r.killed) {
            hero.kills++;
            hero.grantXp(38);
            hero.gold += 4;
            bool relevant = quests.reportHunt(r.species);
            audio->play2D(SFX_GLASS_BREAK, 0.22f, 1.5f);
            if (relevant) {
                for (int i = 0; i < quests.count(); i++) {
                    const Quest& q = quests.at(i);
                    if (q.kind != QUEST_HUNT || q.target != r.species) continue;
                    if (q.state != QUEST_ACTIVE && q.state != QUEST_READY) continue;
                    char buf[160];
                    std::snprintf(buf, sizeof(buf), "%s  %d/%d", q.title.c_str(), q.progress, q.needed);
                    addToast(buf);
                    break;
                }
                rebuildMarkers();
            }
        }
    }

    float incoming = land.consumeDamage();
    if (incoming > 0.0f) {
        hero.health -= incoming;
        damageFlash = 0.45f;
        audio->play2D(SFX_STING_LOW, 0.28f, 1.2f);
        if (hero.health <= 0.0f) respawnPlayer();
    }
}

void AetheriaGame::respawnPlayer() {
    const std::vector<Settlement>& vs = land.settlements();
    Vec3 target = land.spawnPoint();
    std::string where = "Lichtung";
    float best = 1e18f;
    for (const Settlement& s : vs) {
        float d = distanceSq(s.center, position);
        if (d < best) {
            best = d;
            target = s.center;
            where = s.name;
        }
    }
    position = Vec3(target.x + 4.0f, 0, target.z + 4.0f);
    position.y = land.groundHeight(position.x, position.z);
    velocity = Vec3(0, 0, 0);
    hero.health = hero.maxHealth * 0.55f;
    hero.stamina = hero.maxStamina * 0.5f;
    hero.gold = (int)(hero.gold * 0.9f);
    damageFlash = 1.2f;
    addToast("Du erwachst in " + where);
    audio->play2D(SFX_HEARTBEAT, 0.35f, 0.9f);
}

void AetheriaGame::pushHit(float x, float y, float w, float h, int index) {
    MenuHit r;
    r.x = x; r.y = y; r.w = w; r.h = h;
    r.index = index;
    hits.push_back(r);
}

int AetheriaGame::menuItemCount() const {
    if (screen == AETH_PAUSED) return 4;
    return runStarted ? 4 : 3;
}

const char* AetheriaGame::menuItemLabel(int index) const {
    const char* online = coop.inSession() ? "ONLINE: LOBBY OEFFNEN" : "ONLINE SPIELEN";
    if (screen == AETH_PAUSED) {
        switch (index) {
        case 0: return "WEITER";
        case 1: return "NEUES ABENTEUER";
        case 2: return online;
        default: return "ZUR COLLECTION";
        }
    }
    if (runStarted) {
        switch (index) {
        case 0: return "WEITERSPIELEN";
        case 1: return "NEUES ABENTEUER";
        case 2: return online;
        default: return "ZUR COLLECTION";
        }
    }
    switch (index) {
    case 0: return "ABENTEUER BEGINNEN";
    case 1: return online;
    default: return "ZUR COLLECTION";
    }
}

void AetheriaGame::activateMenuItem(int index) {
    audio->play2D(SFX_SWITCH, 0.26f, 1.1f);
    if (screen == AETH_PAUSED || runStarted) {
        if (index == 0) {
            screen = AETH_PLAYING;
            window->setCursorLocked(true);
        } else if (index == 1) {
            beginRun();
        } else if (index == 2) {
            coopMenu.open();
        } else {
            exitRequested = true;
        }
        return;
    }
    if (index == 0) beginRun();
    else if (index == 1) coopMenu.open();
    else exitRequested = true;
}

void AetheriaGame::updateMenuCamera(float dt) {
    menuOrbit += dt * 0.055f;
    float radius = 42.0f;
    Vec3 eye(menuFocus.x + std::cos(menuOrbit) * radius, 0.0f, menuFocus.z + std::sin(menuOrbit) * radius);
    eye.y = land.groundHeight(eye.x, eye.z) + 13.0f + std::sin(menuOrbit * 1.7f) * 1.6f;

    Vec3 target(menuFocus.x, land.groundHeight(menuFocus.x, menuFocus.z) + 3.4f, menuFocus.z);
    menuCam.position = eye;
    menuCam.forward = normalize(target - eye);
    menuCam.fovY = 1.05f;
    menuCam.nearPlane = 0.2f;
    menuCam.farPlane = 900.0f;
    menuCam.update(window->aspect());
}

void AetheriaGame::updateMenu(float dt) {
    Input& in = window->input();
    menuTime += dt;

    int count = menuItemCount();
    Vec2 mouse = in.mousePos();
    bool moved = lengthSq(mouse - lastMouse) > 1.0f;
    lastMouse = mouse;

    for (const MenuHit& r : hits) {
        if (mouse.x < r.x || mouse.x > r.x + r.w || mouse.y < r.y || mouse.y > r.y + r.h) continue;
        if (moved && menuIndex != r.index) {
            menuIndex = r.index;
            audio->play2D(SFX_CLICK, 0.14f, 1.35f);
        }
        if (in.mousePressed(MOUSE_LEFT)) {
            menuIndex = r.index;
            activateMenuItem(menuIndex);
            return;
        }
    }

    if (in.keyPressed(KEY_DOWN) || in.keyPressed(KEY_S)) {
        menuIndex = (menuIndex + 1) % count;
        audio->play2D(SFX_CLICK, 0.14f, 1.35f);
    }
    if (in.keyPressed(KEY_UP) || in.keyPressed(KEY_W)) {
        menuIndex = (menuIndex + count - 1) % count;
        audio->play2D(SFX_CLICK, 0.14f, 1.35f);
    }
    if (in.keyPressed(KEY_ENTER) || in.keyPressed(KEY_SPACE)) activateMenuItem(menuIndex);

    if (in.keyPressed(KEY_ESCAPE)) {
        if (screen == AETH_PAUSED) {
            screen = AETH_PLAYING;
            window->setCursorLocked(true);
        } else if (runStarted) {
            screen = AETH_PLAYING;
            window->setCursorLocked(true);
        }
    }

    if (screen != AETH_MENU) return;

    updateMenuCamera(dt);
    land.update(dt, menuTime, menuCam.position);
    land.applySky(*renderer);

    PostParams& post = renderer->post();
    post.sanity = 1.0f;
    post.distortion = 0.0f;
    post.saturation = 1.12f;
    post.contrast = 1.04f;
    post.vignette = 0.42f;
    post.grain = 0.010f;
    post.chromatic = 0.0004f;
    post.exposure = lerpf(1.70f, 2.30f, land.clock().ambientScale);
    post.bloomStrength = 0.095f;
    post.bloomThreshold = 1.20f;
    post.lift = Vec3(0.004f, 0.006f, 0.010f);
    post.gamma = Vec3(1.0f, 1.0f, 1.0f);
    post.gain = Vec3(1.05f, 1.02f, 0.96f);
}

void AetheriaGame::pushCoopState() {
    CoopLocalState state;
    state.position = position;
    state.velocity = velocity;
    state.yaw = yaw;
    state.pitch = pitch;
    state.health = (int)hero.health;
    u32 flags = 0;
    if (grounded) flags |= CFLAG_GROUND;
    if (sprinting) flags |= CFLAG_SPRINT;
    if (lamp.isOn()) flags |= CFLAG_LIGHT;
    if (swing > 0.01f) flags |= CFLAG_ATTACK;
    state.flags = flags;

    float speed = length(Vec2(velocity.x, velocity.z));
    if (swing > 0.01f) state.anim = CANIM_ATTACK;
    else if (!grounded) state.anim = velocity.y > 0.6f ? CANIM_JUMP : CANIM_FALL;
    else if (speed < 0.35f) state.anim = CANIM_IDLE;
    else state.anim = sprinting ? CANIM_RUN : CANIM_WALK;

    coop.pushLocal(state);
}

void AetheriaGame::applyCoopEvents() {
    std::string kind, key;
    double value = 0.0;
    while (coop.consumeWorldEvent(kind, key, value)) {
        if (kind == "harvest") {
            size_t colon = key.find(':');
            int index = colon == std::string::npos ? -1 : std::atoi(key.c_str() + colon + 1);
            if (index >= 0 && index < land.floraCount()) land.harvest(index);
            continue;
        }
        if (kind == "quest") {
            size_t colon = key.find(':');
            int id = colon == std::string::npos ? -1 : std::atoi(key.c_str() + colon + 1);
            if (id >= 0) {
                quests.revealVillage(id);
                addToast("Mitspieler bringt die Quest voran");
            }
            continue;
        }
        if (kind == "npc") {
            size_t colon = key.find(':');
            int id = colon == std::string::npos ? -1 : std::atoi(key.c_str() + colon + 1);
            if (id >= 0 && id < (int)land.settlements().size()) {
                land.settlements()[(size_t)id].visited = true;
                quests.revealVillage(id);
            }
            continue;
        }
        if (kind == "strike") {
            addToast("Mitspieler kaempft");
            continue;
        }
        if (kind == "save") {
            addToast("Fortschritt gesichert");
            continue;
        }
    }
}

void AetheriaGame::syncCoopWorld(float dt) {
    if (!coop.playing()) return;

    coopSyncTimer -= dt;
    if (coopSyncTimer <= 0.0f) {
        coopSyncTimer = 1.0f;
        if (coop.isHost()) {
            coop.sendInteract("timer", "sky", (double)land.clock().timeOfDay, position);
        } else if (coop.hasWorldValue("timer:sky")) {
            float wanted = (float)coop.worldValue("timer:sky", (double)land.clock().timeOfDay);
            float diff = wanted - land.clock().timeOfDay;
            if (std::fabs(diff) > 0.004f) land.clock().timeOfDay += diff * 0.35f;
        }
    }

    coopSaveTimer -= dt;
    if (coopSaveTimer <= 0.0f) {
        coopSaveTimer = 45.0f;
        js::Value blob = js::Value::object();
        blob.set("checkpoint", regionLabel);
        blob.set("level", hero.level);
        blob.set("discovered", hero.discovered);
        blob.set("gold", hero.gold);
        coop.sendCheckpoint(blob);
    }
}

void AetheriaGame::updateCoop(float dt, float time) {
    coop.update(dt);

    if (coopMenu.visible()) {
        coopMenu.update(dt);
        if (coopMenu.consumeLaunch()) {
            coopStarting = true;
        }
        if (coopMenu.consumeExit() && screen == AETH_PLAYING) {
            window->setCursorLocked(true);
        }
    }

    if (coop.phase() == COOP_LOADING && !coopReported) {
        if (!worldReady || land.settlements().empty()) {
            open(coop.worldSeed() ? coop.worldSeed() : 0xAE71EA1AULL);
        }
        coopReported = true;
        coop.reportLoaded();
    }
    if (coop.phase() != COOP_LOADING) coopReported = false;

    if (coopStarting && coop.playing()) {
        coopStarting = false;
        beginRun();
        if (coop.spawnReady()) {
            Vec3 point = coop.spawnPoint();
            point.y = land.groundHeight(point.x, point.z) + 0.2f;
            position = point;
            velocity = Vec3(0, 0, 0);
        }
        screen = AETH_PLAYING;
        window->setCursorLocked(true);
        coopMenu.close();
        addToast("Koop gestartet — viel Glueck!");
    }

    if (coop.consumeSpawnSignal() && coop.playing() && runStarted && coop.spawnReady()) {
        Vec3 point = coop.spawnPoint();
        point.y = land.groundHeight(point.x, point.z) + 0.2f;
        position = point;
        velocity = Vec3(0, 0, 0);
    }

    applyCoopEvents();
    if (coop.inSession()) {
        coop.updateRemotes(dt, time, position + Vec3(0, eyeHeight, 0));
    }
}

void AetheriaGame::update(float dt, float time) {
    if (!running) return;

    updateCoop(dt, time);
    if (coopMenu.visible()) return;

    if (screen != AETH_PLAYING) {
        updateMenu(dt);
        return;
    }

    Input& in = window->input();
    if (in.keyPressed(KEY_ESCAPE)) {
        if (mapOpen) {
            mapOpen = false;
            window->setCursorLocked(true);
        } else {
            screen = AETH_PAUSED;
            menuIndex = 0;
            hits.clear();
            window->setCursorLocked(false);
            audio->play2D(SFX_CLICK, 0.20f, 0.85f);
        }
        return;
    }
    if (in.keyPressed(KEY_TAB)) {
        mapOpen = !mapOpen;
        window->setCursorLocked(!mapOpen);
        if (mapOpen) rebuildMarkers();
    }
    if (in.keyPressed(KEY_Q)) {
        quests.cycleTracked();
        rebuildMarkers();
        int t = quests.trackedIndex();
        if (t >= 0) addToast("Verfolgt: " + quests.at(t).title);
    }
    if (in.keyPressed(KEY_F1)) {
        land.clock().timeOfDay = fractf(land.clock().timeOfDay + 0.12f);
    }

    if (in.keyPressed(KEY_F)) {
        lamp.setBattery(1.0f);
        lamp.toggle();
        audio->play2D(SFX_SWITCH, 0.26f, lamp.isOn() ? 1.25f : 0.95f);
        addToast(lamp.isOn() ? "Laterne an" : "Laterne aus");
    }

    updateMovement(dt);
    land.update(dt, time, position);
    updateDiscovery(dt);
    updateInteraction(dt);
    updateCombat(dt);

    lamp.setBattery(1.0f);
    lamp.update(position + Vec3(0, eyeHeight, 0), sphericalDir(yaw, pitch),
                normalize(cross(sphericalDir(yaw, pitch), Vec3(0, 1, 0))), dt, time,
                length(Vec2(velocity.x, velocity.z)));

    markerTimer -= dt;
    if (markerTimer <= 0.0f) {
        markerTimer = 1.0f;
        rebuildMarkers();
    }

    objectiveTimer -= dt;
    if (objectiveTimer <= 0.0f) {
        objectiveTimer = 0.5f;
        refreshObjective();
    }

    pushCoopState();
    syncCoopWorld(dt);

    land.applySky(*renderer);

    PostParams& post = renderer->post();
    post.sanity = 1.0f;
    post.distortion = 0.0f;
    post.saturation = 1.06f;
    post.contrast = 1.02f;
    post.vignette = 0.30f + clampf(damageFlash, 0.0f, 1.0f) * 0.35f;
    post.grain = 0.012f;
    post.chromatic = 0.0004f + clampf(damageFlash, 0.0f, 1.0f) * 0.0016f;
    post.exposure = lerpf(1.60f, 2.35f, land.clock().ambientScale);
    post.bloomStrength = 0.075f;
    post.bloomThreshold = 1.25f;
    post.lift = Vec3(0.004f, 0.006f, 0.010f);
    post.gamma = Vec3(1.00f, 1.00f, 1.00f);
    post.gain = Vec3(1.04f + clampf(damageFlash, 0.0f, 1.0f) * 0.35f, 1.01f, 0.96f);
}

void AetheriaGame::render(float time) {
    if (!running) return;

    if (screen == AETH_MENU) {
        renderer->beginFrame(menuCam, time, 0.016f);
        land.collectRender(*renderer, menuCam, 210.0f);
        renderer->render();
        return;
    }

    CameraData cam = camera(window->aspect());
    lastCam = cam;
    renderer->beginFrame(cam, time, 0.016f);
    if (lamp.glowIntensity() > 0.01f) {
        RenderLight beam = lamp.buildLight();
        beam.volumetric = 0.5f;
        renderer->submitLight(beam);
    }
    land.collectRender(*renderer, cam, viewDistance);
    coop.submitRemotes(*renderer);

    if (weapon.valid()) {
        float t = clampf(swing / 0.42f, 0.0f, 1.0f);
        float arc = std::sin(t * PI) * 1.35f;
        float lower = clampf(bobAmount, 0.0f, 1.0f) * 0.03f;

        Mat4 local = Mat4::translate(Vec3(0.30f, -0.34f - lower + arc * 0.10f, -0.58f)) *
                     Mat4::rotateY(-0.42f + arc * 0.30f) *
                     Mat4::rotateX(-0.30f - arc * 1.30f) *
                     Mat4::rotateZ(0.55f - arc * 0.45f);
        Mat4 xf = cam.invView * local;

        DrawCall dc;
        dc.mesh = &weapon;
        dc.transform = xf;
        dc.castShadow = false;
        dc.bounds = weapon.bounds().transformed(xf);
        for (int sub = 0; sub < (int)weapon.subMeshes().size(); sub++) {
            const SubMesh& sm = weapon.subMeshes()[(size_t)sub];
            dc.subIndex = sub;
            dc.material = sm.material;
            dc.bounds = sm.bounds.transformed(xf);
            renderer->submit(dc);
        }
    }

    renderer->render();
}

void AetheriaGame::drawBars(float w, float h) {
    char buf[96];
    float x = h * 0.048f;
    float y = h * 0.070f;

    std::snprintf(buf, sizeof(buf), "STUFE %d", hero.level);
    ui->textShadow(buf, x, y, h * 0.026f, kGold, ALIGN_LEFT, h * 0.004f);

    float barW = h * 0.28f;
    float barH = h * 0.011f;
    float by = y + h * 0.042f;

    auto bar = [&](float value, float maxValue, const Vec4& col, float offset) {
        ui->rect(x, by + offset, barW, barH, Vec4(0.05f, 0.05f, 0.06f, 0.55f));
        ui->rect(x, by + offset, barW * clampf(value / std::max(maxValue, 1.0f), 0.0f, 1.0f), barH, col);
    };
    bar(hero.health, hero.maxHealth, Vec4(0.80f, 0.28f, 0.30f, 0.92f), 0.0f);
    bar(hero.stamina, hero.maxStamina, Vec4(0.52f, 0.82f, 0.42f, 0.92f), barH * 1.7f);
    bar(hero.mana, hero.maxMana, Vec4(0.42f, 0.62f, 0.95f, 0.92f), barH * 3.4f);

    float xpFrac = clampf((float)hero.xp / (float)std::max(hero.xpNext, 1), 0.0f, 1.0f);
    ui->rect(x, by + barH * 5.3f, barW, barH * 0.55f, Vec4(0.05f, 0.05f, 0.06f, 0.5f));
    ui->rect(x, by + barH * 5.3f, barW * xpFrac, barH * 0.55f, Vec4(kGold.x, kGold.y, kGold.z, 0.75f));

    std::snprintf(buf, sizeof(buf), "%d GOLD", hero.gold);
    ui->text(buf, x, by + barH * 7.6f, h * 0.018f, Vec4(kGold.x, kGold.y, kGold.z, 0.72f), ALIGN_LEFT);
}

void AetheriaGame::drawTracker(float w, float h) {
    int tracked = quests.trackedIndex();
    float x = h * 0.048f;
    float y = h * 0.250f;
    char buf[220];

    if (tracked < 0) {
        ui->rect(x - h * 0.012f, y - h * 0.016f, h * 0.34f, h * 0.066f, Vec4(0.04f, 0.04f, 0.05f, 0.42f));
        ui->rect(x - h * 0.012f, y - h * 0.016f, h * 0.003f, h * 0.066f, Vec4(kDim.x, kDim.y, kDim.z, 0.6f));
        ui->text("KEIN AUFTRAG", x, y, h * 0.020f, Vec4(kDim.x, kDim.y, kDim.z, 0.85f), ALIGN_LEFT);
        ui->text("Bewohner mit  !  ansprechen", x, y + h * 0.030f, h * 0.017f,
                 Vec4(kInk.x, kInk.y, kInk.z, 0.65f), ALIGN_LEFT);
        return;
    }

    const Quest& q = quests.at(tracked);
    bool ready = q.state == QUEST_READY;
    float panelH = h * 0.128f;

    ui->rect(x - h * 0.012f, y - h * 0.018f, h * 0.42f, panelH, Vec4(0.04f, 0.04f, 0.05f, 0.48f));
    ui->rect(x - h * 0.012f, y - h * 0.018f, h * 0.004f, panelH,
             ready ? Vec4(0.55f, 0.95f, 0.60f, 0.9f) : Vec4(kGold.x, kGold.y, kGold.z, 0.8f));

    ui->text("AUFTRAG", x, y, h * 0.014f, Vec4(kDim.x, kDim.y, kDim.z, 0.55f), ALIGN_LEFT, h * 0.004f);
    ui->textShadow(q.title, x, y + h * 0.022f, h * 0.022f, ready ? Vec4(0.62f, 0.96f, 0.66f, 1.0f) : kGold,
                   ALIGN_LEFT, h * 0.002f);

    if (ready) std::snprintf(buf, sizeof(buf), "Erledigt - bring es zu %s", q.giver.c_str());
    else std::snprintf(buf, sizeof(buf), "%s", q.task.c_str());
    ui->text(buf, x, y + h * 0.054f, h * 0.017f, Vec4(kInk.x, kInk.y, kInk.z, 0.85f), ALIGN_LEFT);

    if (!ready && q.needed > 1) {
        float barW = h * 0.28f;
        float barY = y + h * 0.080f;
        float frac = clampf((float)q.progress / (float)std::max(q.needed, 1), 0.0f, 1.0f);
        ui->rect(x, barY, barW, h * 0.009f, Vec4(0.05f, 0.05f, 0.06f, 0.65f));
        ui->rect(x, barY, barW * frac, h * 0.009f, Vec4(kGold.x, kGold.y, kGold.z, 0.85f));
        std::snprintf(buf, sizeof(buf), "%d / %d", q.progress, q.needed);
        ui->text(buf, x + barW + h * 0.012f, barY - h * 0.004f, h * 0.016f, Vec4(kInk.x, kInk.y, kInk.z, 0.72f), ALIGN_LEFT);
    }

    if (objectiveValid) {
        float d = distance(Vec2(objectivePos.x, objectivePos.z), Vec2(position.x, position.z));
        std::snprintf(buf, sizeof(buf), "%s   %.0f m", objectiveLabel.c_str(), d);
        ui->text(buf, x, y + h * 0.100f, h * 0.016f, Vec4(kDim.x, kDim.y, kDim.z, 0.72f), ALIGN_LEFT);
    }

    ui->text("Q  ANDERER AUFTRAG", x, y + panelH + h * 0.002f, h * 0.013f,
             Vec4(kDim.x, kDim.y, kDim.z, 0.35f), ALIGN_LEFT, h * 0.003f);
}

void AetheriaGame::drawObjectives(float w, float h) {
    const std::vector<Settlement>& vs = land.settlements();
    char buf[96];

    for (int i = 0; i < (int)vs.size(); i++) {
        const Settlement& s = vs[(size_t)i];
        Vec3 head = s.giverPos + Vec3(0, 2.25f, 0);
        float d = distance(head, position);
        if (d > 55.0f) continue;

        int ready = quests.readyFor(i);
        int offer = quests.offeredFor(i);
        if (ready < 0 && offer < 0) continue;
        if (dot(normalize(head - (position + Vec3(0, eyeHeight, 0))), sphericalDir(yaw, pitch)) < 0.05f) continue;

        Vec2 screen;
        bool behind = false;
        projectToScreen(head, w, h, screen, behind);
        if (behind) continue;

        float fade = clampf((55.0f - d) / 12.0f, 0.0f, 1.0f);
        float bob = std::sin(bobPhase * 0.4f + (float)i) * h * 0.006f;
        Vec4 col = ready >= 0 ? Vec4(0.58f, 0.96f, 0.62f, fade) : Vec4(kGold.x, kGold.y, kGold.z, fade);
        float size = clampf(h * 0.040f * (24.0f / std::max(d, 6.0f)), h * 0.020f, h * 0.046f);

        ui->textShadow(ready >= 0 ? "?" : "!", screen.x, screen.y + bob, size, col, ALIGN_CENTER, h * 0.002f);
        if (d < 22.0f) {
            ui->text(s.giverName, screen.x, screen.y + bob + size * 1.15f, size * 0.42f,
                     Vec4(kInk.x, kInk.y, kInk.z, fade * 0.75f), ALIGN_CENTER);
        }
    }

    if (!objectiveValid) return;

    Vec3 target = objectivePos + Vec3(0, 1.6f, 0);
    float dist = distance(Vec2(objectivePos.x, objectivePos.z), Vec2(position.x, position.z));
    Vec2 screen;
    bool behind = false;
    projectToScreen(target, w, h, screen, behind);

    float margin = h * 0.075f;
    bool offscreen = behind || screen.x < margin || screen.x > w - margin || screen.y < margin || screen.y > h - margin;

    if (offscreen) {
        Vec2 center(w * 0.5f, h * 0.5f);
        Vec2 dir = screen - center;
        if (behind) dir = Vec2(dir.x >= 0.0f ? 1.0f : -1.0f, 0.35f);
        if (lengthSq(dir) < 1e-4f) dir = Vec2(0, -1);
        dir = normalize(dir);
        float rx = w * 0.5f - margin;
        float ry = h * 0.5f - margin;
        float scale = std::min(std::fabs(rx / (std::fabs(dir.x) < 1e-3f ? 1e-3f : dir.x)),
                               std::fabs(ry / (std::fabs(dir.y) < 1e-3f ? 1e-3f : dir.y)));
        Vec2 edge = center + dir * scale;
        ui->arrow(edge.x, edge.y, h * 0.020f, std::atan2(dir.y, dir.x) + HALF_PI, Vec4(kGold.x, kGold.y, kGold.z, 0.85f));
        std::snprintf(buf, sizeof(buf), "%.0f m", dist);
        ui->textShadow(buf, edge.x, edge.y + h * 0.026f, h * 0.016f, Vec4(kInk.x, kInk.y, kInk.z, 0.75f), ALIGN_CENTER);
        return;
    }

    float pulse = 0.72f + std::sin(bobPhase * 0.9f + land.clock().timeOfDay * 40.0f) * 0.18f;
    ui->diamond(screen.x, screen.y, h * 0.016f, Vec4(0.05f, 0.05f, 0.06f, 0.55f));
    ui->diamond(screen.x, screen.y, h * 0.011f, Vec4(kGold.x, kGold.y, kGold.z, pulse));
    std::snprintf(buf, sizeof(buf), "%.0f m", dist);
    ui->textShadow(buf, screen.x, screen.y + h * 0.026f, h * 0.017f, Vec4(kInk.x, kInk.y, kInk.z, 0.85f), ALIGN_CENTER);
    if (!objectiveHint.empty()) {
        ui->text(objectiveHint, screen.x, screen.y + h * 0.048f, h * 0.014f,
                 Vec4(kGold.x, kGold.y, kGold.z, 0.65f), ALIGN_CENTER);
    }
}

void AetheriaGame::drawPrompt(float w, float h) {
    if (prompt.empty()) return;
    float y = h * 0.62f;
    float pad = h * 0.014f;
    float size = h * 0.022f;
    float width = ui->font().measure(prompt, size, h * 0.004f) + pad * 2.0f;
    ui->rect(w * 0.5f - width * 0.5f, y - pad, width, size + pad * 2.0f, Vec4(0.04f, 0.04f, 0.05f, 0.55f));
    ui->textShadow(prompt, w * 0.5f, y, size, kInk, ALIGN_CENTER, h * 0.004f);
}

void AetheriaGame::drawDialogue(float w, float h) {
    if (speechTimer <= 0.0f || speech.empty()) return;
    float alpha = clampf(speechTimer / 1.0f, 0.0f, 1.0f);

    float boxW = std::min(w * 0.68f, h * 1.10f);
    float boxH = h * 0.155f;
    float x = w * 0.5f - boxW * 0.5f;
    float y = h - boxH - h * 0.095f;

    ui->rect(x, y, boxW, boxH, Vec4(kPanel.x, kPanel.y, kPanel.z, kPanel.w * alpha));
    ui->rectOutline(x, y, boxW, boxH, 1.5f, Vec4(kGold.x, kGold.y, kGold.z, 0.35f * alpha));
    ui->textShadow(speaker, x + h * 0.026f, y + h * 0.026f, h * 0.024f, Vec4(kGold.x, kGold.y, kGold.z, alpha),
                   ALIGN_LEFT, h * 0.004f);

    float textSize = h * 0.0195f;
    float limit = boxW - h * 0.052f;
    std::vector<std::string> lines;
    std::string current;
    std::string word;
    std::string rest = speech + " ";
    for (char c : rest) {
        if (c != ' ') { word += c; continue; }
        std::string candidate = current.empty() ? word : current + " " + word;
        if (ui->font().measure(candidate, textSize, 0.0f) > limit && !current.empty()) {
            lines.push_back(current);
            current = word;
        } else {
            current = candidate;
        }
        word.clear();
        if (lines.size() >= 4) break;
    }
    if (!current.empty() && lines.size() < 4) lines.push_back(current);
    float ly = y + h * 0.066f;
    for (const std::string& line : lines) {
        ui->text(line, x + h * 0.026f, ly, h * 0.0195f, Vec4(kInk.x, kInk.y, kInk.z, 0.88f * alpha), ALIGN_LEFT);
        ly += h * 0.028f;
    }
}

void AetheriaGame::drawToasts(float w, float h) {
    float y = h * 0.70f;
    for (size_t i = 0; i < toasts.size(); i++) {
        const Toast& t = toasts[i];
        float a = clampf(t.timer / 0.9f, 0.0f, 1.0f);
        ui->textShadow(t.text, w - h * 0.048f, y, h * 0.019f, Vec4(kInk.x, kInk.y, kInk.z, 0.85f * a),
                       ALIGN_RIGHT, h * 0.003f);
        y += h * 0.030f;
    }
}

void AetheriaGame::drawMenu(float w, float h) {
    hits.clear();

    Vec4 scrim(0.020f, 0.022f, 0.028f, 0.90f);
    Vec4 clear(0.020f, 0.022f, 0.028f, 0.0f);
    ui->rect(0, 0, w * 0.22f, h, scrim);
    ui->gradientRectH(w * 0.22f, 0, w * 0.42f, h, scrim, clear);
    ui->gradientRect(0, h * 0.80f, w, h * 0.20f, clear, Vec4(0.02f, 0.02f, 0.03f, 0.55f));

    float x = w * 0.085f;
    float titleY = h * 0.26f;

    ui->textShadow("AETHERIA", x, titleY, h * 0.105f, kGold, ALIGN_LEFT, h * 0.028f);
    ui->rect(x, titleY + h * 0.135f, h * 0.30f, 2.0f, Vec4(kGold.x, kGold.y, kGold.z, 0.55f));
    ui->text("BY FELWORKS", x, titleY + h * 0.160f, h * 0.024f, Vec4(kInk.x, kInk.y, kInk.z, 0.55f), ALIGN_LEFT, h * 0.014f);
    ui->text("FANTASY OPEN WORLD RPG", x, titleY + h * 0.200f, h * 0.020f,
             Vec4(kDim.x, kDim.y, kDim.z, 0.60f), ALIGN_LEFT, h * 0.010f);

    float itemY = h * 0.560f;
    float itemH = h * 0.062f;
    int count = menuItemCount();
    for (int i = 0; i < count; i++) {
        bool active = i == menuIndex;
        float y = itemY + i * itemH;
        pushHit(x - h * 0.02f, y - h * 0.012f, h * 0.52f, itemH * 0.86f, i);

        if (active) {
            float pulse = 0.55f + std::sin(menuTime * 3.2f) * 0.12f;
            ui->rect(x - h * 0.02f, y - h * 0.010f, h * 0.46f, itemH * 0.78f, Vec4(kGold.x, kGold.y, kGold.z, 0.10f));
            ui->rect(x - h * 0.02f, y - h * 0.010f, h * 0.004f, itemH * 0.78f, Vec4(kGold.x, kGold.y, kGold.z, pulse));
        }
        ui->textShadow(menuItemLabel(i), x + (active ? h * 0.018f : 0.0f), y + itemH * 0.14f, h * 0.030f,
                       active ? kGold : Vec4(kInk.x, kInk.y, kInk.z, 0.62f), ALIGN_LEFT, h * 0.010f);
    }

    char buf[128];
    std::snprintf(buf, sizeof(buf), "%d DOERFER    %d ORTE    %d PFLANZEN",
                  (int)land.settlements().size(), (int)land.landmarks().size(), land.floraCount());
    ui->text(buf, x, h * 0.815f, h * 0.017f, Vec4(kDim.x, kDim.y, kDim.z, 0.42f), ALIGN_LEFT, h * 0.006f);

    ui->text("MAUS ODER PFEILTASTEN    ENTER WAEHLEN    F11 VOLLBILD", w * 0.5f, h - h * 0.055f, h * 0.017f,
             Vec4(kDim.x, kDim.y, kDim.z, 0.42f), ALIGN_CENTER, h * 0.006f);
}

void AetheriaGame::drawPause(float w, float h) {
    hits.clear();

    ui->rect(0, 0, w, h, Vec4(0.02f, 0.02f, 0.03f, 0.72f));

    float boxW = std::min(w * 0.40f, h * 0.62f);
    float boxH = h * 0.44f;
    float x0 = w * 0.5f - boxW * 0.5f;
    float y0 = h * 0.5f - boxH * 0.5f;

    ui->rect(x0, y0, boxW, boxH, Vec4(0.05f, 0.05f, 0.06f, 0.82f));
    ui->rectOutline(x0, y0, boxW, boxH, 1.6f, Vec4(kGold.x, kGold.y, kGold.z, 0.35f));
    ui->textShadow("PAUSE", w * 0.5f, y0 + h * 0.045f, h * 0.040f, kGold, ALIGN_CENTER, h * 0.014f);
    ui->text(regionLabel, w * 0.5f, y0 + h * 0.098f, h * 0.019f, Vec4(kInk.x, kInk.y, kInk.z, 0.55f), ALIGN_CENTER, h * 0.006f);

    float itemY = y0 + h * 0.160f;
    float itemH = h * 0.058f;
    for (int i = 0; i < menuItemCount(); i++) {
        bool active = i == menuIndex;
        float y = itemY + i * itemH;
        pushHit(x0 + boxW * 0.10f, y - h * 0.008f, boxW * 0.80f, itemH * 0.82f, i);
        if (active) {
            ui->rect(x0 + boxW * 0.10f, y - h * 0.008f, boxW * 0.80f, itemH * 0.82f, Vec4(kGold.x, kGold.y, kGold.z, 0.12f));
        }
        ui->text(menuItemLabel(i), w * 0.5f, y + itemH * 0.16f, h * 0.026f,
                 active ? kGold : Vec4(kInk.x, kInk.y, kInk.z, 0.60f), ALIGN_CENTER, h * 0.008f);
    }

    ui->text("ESC  WEITERSPIELEN", w * 0.5f, y0 + boxH - h * 0.036f, h * 0.016f,
             Vec4(kDim.x, kDim.y, kDim.z, 0.42f), ALIGN_CENTER, h * 0.005f);
}

void AetheriaGame::drawHud() {
    if (!running) return;
    float w = (float)window->width(), h = (float)window->height();
    char buf[96];

    if (coopMenu.visible()) {
        if (screen == AETH_MENU) drawMenu(w, h);
        coopMenu.draw(menuTime);
        return;
    }
    coopMenu.drawHudBadge(menuTime);

    if (screen == AETH_MENU) {
        drawMenu(w, h);
        return;
    }

    if (mapOpen) {
        std::vector<std::string> lines = quests.journalLines();
        lines.push_back("");
        lines.push_back("#REISENDER");
        std::snprintf(buf, sizeof(buf), "  Stufe %d   %d Gold", hero.level, hero.gold);
        lines.push_back(buf);
        std::snprintf(buf, sizeof(buf), "  Orte %d   Beute %d   Siege %d", hero.discovered, hero.gathered, hero.kills);
        lines.push_back(buf);
        lines.push_back("");
        lines.push_back("  Q wechselt den verfolgten Auftrag");
        map.drawFull(*ui, w, h, Vec2(position.x, position.z), yaw, markers, lines, "AETHERIA");
        return;
    }

    float crossAlpha = 0.35f + clampf(swing / 0.42f, 0.0f, 1.0f) * 0.5f;
    ui->crosshair(w * 0.5f, h * 0.5f, h * 0.012f + clampf(swing / 0.42f, 0.0f, 1.0f) * h * 0.008f,
                  0.3f, Vec4(kInk.x, kInk.y, kInk.z, crossAlpha));

    if (damageFlash > 0.0f) {
        float a = clampf(damageFlash, 0.0f, 1.0f) * 0.30f;
        ui->rect(0, 0, w, h * 0.10f, Vec4(0.60f, 0.08f, 0.08f, a));
        ui->rect(0, h * 0.90f, w, h * 0.10f, Vec4(0.60f, 0.08f, 0.08f, a));
    }

    drawObjectives(w, h);
    drawBars(w, h);
    drawTracker(w, h);

    float mapSize = h * 0.215f;
    float mapCx = w - h * 0.048f - mapSize * 0.5f;
    float mapCy = h * 0.048f + mapSize * 0.5f;
    map.drawMinimap(*ui, mapCx, mapCy, mapSize, Vec2(position.x, position.z), yaw, 190.0f, markers);

    float t = land.clock().timeOfDay;
    int hours = (int)(t * 24.0f);
    int minutes = (int)((t * 24.0f - hours) * 60.0f);
    std::snprintf(buf, sizeof(buf), "%02d:%02d", hours, minutes);
    ui->textShadow(buf, w - h * 0.048f, mapCy + mapSize * 0.5f + h * 0.052f, h * 0.024f, kDim, ALIGN_RIGHT, h * 0.004f);
    ui->text(regionLabel, w - h * 0.048f, mapCy + mapSize * 0.5f + h * 0.086f, h * 0.019f,
             Vec4(kGold.x, kGold.y, kGold.z, 0.75f), ALIGN_RIGHT);

    drawPrompt(w, h);
    drawDialogue(w, h);
    drawToasts(w, h);

    if (regionToastTimer > 0.0f) {
        float a = clampf(regionToastTimer / 1.2f, 0.0f, 1.0f) * clampf((5.0f - regionToastTimer) / 0.6f, 0.0f, 1.0f);
        ui->textShadow(regionToast, w * 0.5f, h * 0.30f, h * 0.052f, Vec4(kGold.x, kGold.y, kGold.z, a), ALIGN_CENTER, h * 0.012f);
        ui->rect(w * 0.5f - h * 0.14f, h * 0.375f, h * 0.28f, 1.5f, Vec4(kGold.x, kGold.y, kGold.z, a * 0.5f));
    }

    ui->text("TAB KARTE    Q AUFTRAG    E BENUTZEN    F LATERNE    MAUS ANGRIFF    ESC PAUSE",
             w * 0.5f, h - h * 0.038f, h * 0.015f, Vec4(kDim.x, kDim.y, kDim.z, 0.35f), ALIGN_CENTER, h * 0.004f);

    if (lamp.isOn()) {
        ui->text("LATERNE", w - h * 0.048f, h - h * 0.075f, h * 0.016f,
                 Vec4(kGold.x, kGold.y, kGold.z, 0.55f), ALIGN_RIGHT, h * 0.004f);
    }

    if (screen == AETH_PAUSED) drawPause(w, h);
}

}
