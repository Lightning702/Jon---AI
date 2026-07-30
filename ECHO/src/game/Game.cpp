#include "Game.h"
#include "../core/FileSystem.h"
#include "../core/Log.h"
#include "../core/Time.h"
#include "../core/ImageWriter.h"

#include <cstdio>

using namespace em;

namespace echo {

namespace {

const Vec4 kInk(0.86f, 0.88f, 0.90f, 1.0f);
const Vec4 kDim(0.52f, 0.55f, 0.58f, 1.0f);
const Vec4 kAccent(0.62f, 0.86f, 0.78f, 1.0f);
const Vec4 kShade(0.02f, 0.025f, 0.03f, 0.88f);

const char* kMenuItems[] = { "NEUES SPIEL", "FORTSETZEN", "ONLINE KOOP", "OPTIONEN", "ZUR COLLECTION" };
const int kMenuCount = 5;

const char* kOptionNames[] = { "LAUTSTAERKE", "MAUSEMPFINDLICHKEIT", "Y INVERTIEREN", "UNTERTITEL", "TUTORIAL", "GRAFIK", "VOLLBILD", "ZURUECK" };
const int kOptionCount = 8;

const char* kQualityNames[] = { "NIEDRIG", "MITTEL", "HOCH", "ULTRA" };

std::string formatTime(float seconds) {
    int total = (int)seconds;
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%02d:%02d:%02d", total / 3600, (total / 60) % 60, total % 60);
    return std::string(buf);
}

}

void Settings::load() {
    std::string text;
    if (!fs::readText("settings.cfg", text)) return;
    size_t pos = 0;
    while (pos < text.size()) {
        size_t eol = text.find('\n', pos);
        if (eol == std::string::npos) eol = text.size();
        std::string line = text.substr(pos, eol - pos);
        pos = eol + 1;
        size_t eq = line.find('=');
        if (eq == std::string::npos) continue;
        std::string key = line.substr(0, eq);
        std::string value = line.substr(eq + 1);
        float v = (float)std::atof(value.c_str());
        if (key == "volume") masterVolume = v;
        else if (key == "sensitivity") sensitivity = v;
        else if (key == "invertY") invertY = v > 0.5f;
        else if (key == "subtitles") subtitles = v > 0.5f;
        else if (key == "tutorial") tutorial = v > 0.5f;
        else if (key == "vsync") vsync = v > 0.5f;
        else if (key == "fullscreen") fullscreen = v > 0.5f;
        else if (key == "quality") qualityPreset = (int)v;
        else if (key == "fov") fov = v;
        else if (key == "brightness") brightness = v;
    }
}

void Settings::save() const {
    char buf[512];
    std::snprintf(buf, sizeof(buf),
                  "volume=%.3f\nsensitivity=%.5f\ninvertY=%d\nsubtitles=%d\ntutorial=%d\nvsync=%d\nfullscreen=%d\nquality=%d\nfov=%.1f\nbrightness=%.2f\n",
                  masterVolume, sensitivity, invertY ? 1 : 0, subtitles ? 1 : 0, tutorial ? 1 : 0, vsync ? 1 : 0,
                  fullscreen ? 1 : 0, qualityPreset, fov, brightness);
    fs::writeText("settings.cfg", buf);
}

bool Game::init(Window* w, int forcedPreset, bool startWindowed) {
    window = w;
    renderer = &ownRenderer;
    ui = &ownUi;
    audio = &ownAudio;
    ownsSystems = true;

    settings.load();
    if (startWindowed) settings.fullscreen = false;

    QualitySettings quality;
    int preset = forcedPreset >= 0 ? forcedPreset : (settings.qualityPreset >= 0 ? settings.qualityPreset : QualitySettings::detectPreset());
    quality.applyPreset(preset);
    settings.qualityPreset = preset;
    LOG_INFO("Quality preset: %d", preset);

    if (!renderer->init(window->width(), window->height(), quality)) return false;
    if (!ui->init()) return false;

    propLib.build();
    humanRig.build();
    coop.init("echo", &humanRig);
    coopMenu.init(&coop, window, ui, audio);
    story.build();
    if (ownsSystems) audio->init();
    audio->setMasterVolume(settings.masterVolume);

    player.setSensitivity(settings.sensitivity);
    player.setInvertY(settings.invertY);
    player.setFovBase(settings.fov * DEG2RAD);

    progress.itemCounts.assign((size_t)ITEM_COUNT, 0);
    progress.documentsFound.assign((size_t)story.documentCount(), 0);
    progress.logsFound.assign((size_t)story.audioLogCount(), 0);

    {
        WorldConfig menuCfg;
        menuCfg.seed = 0x4D454E55ULL;
        world.generate(menuCfg, propLib);
        setupMenuCamera();
        menuWorldReady = true;
    }

    hasSave = SaveSystem::exists("quicksave");
    window->setVSync(settings.vsync);
    if (settings.fullscreen != window->fullscreen()) window->setFullscreen(settings.fullscreen);

    setState(GameState::Splash);
    return true;
}

bool Game::initShared(Window* w, Renderer* sharedRenderer, UIRenderer* sharedUi, AudioEngine* sharedAudio, int forcedPreset) {
    window = w;
    renderer = sharedRenderer;
    ui = sharedUi;
    audio = sharedAudio;
    ownsSystems = false;

    settings.load();
    if (forcedPreset >= 0) settings.qualityPreset = forcedPreset;

    propLib.build();
    humanRig.build();
    coop.init("echo", &humanRig);
    coopMenu.init(&coop, window, ui, audio);
    story.build();
    audio->setMasterVolume(settings.masterVolume);

    player.setSensitivity(settings.sensitivity);
    player.setInvertY(settings.invertY);
    player.setFovBase(settings.fov * DEG2RAD);

    progress.itemCounts.assign((size_t)ITEM_COUNT, 0);
    progress.documentsFound.assign((size_t)story.documentCount(), 0);
    progress.logsFound.assign((size_t)story.audioLogCount(), 0);

    hasSave = SaveSystem::exists("quicksave");
    menuWorldReady = false;
    state = GameState::MainMenu;
    return true;
}

void Game::beginTestRun(u64 seed) {
    startNewGame(seed);
    fadeAmount = 0.0f;
    fadeTarget = 0.0f;
}

void Game::enterFromCollection() {
    collectionRequested = false;
    if (world.rooms().empty()) {
        WorldConfig menuCfg;
        menuCfg.seed = 0x4D454E55ULL;
        world.generate(menuCfg, propLib);
        setupMenuCamera();
        menuWorldReady = true;
    }
    hasSave = SaveSystem::exists("quicksave");
    menuIndex = hasSave ? 1 : 0;
    setState(GameState::MainMenu);
    fadeAmount = 1.0f;
    fadeTarget = 0.0f;
}

void Game::tick(float dt) {
    settings.fullscreen = window->fullscreen();
    update(dt);
}

void Game::renderFrame() {
    bool inWorld = state == GameState::Playing || state == GameState::Paused || state == GameState::Reading ||
                   state == GameState::Listening || state == GameState::Journal;
    bool menuBackdrop = menuWorldReady && (state == GameState::MainMenu || state == GameState::Options ||
                                           state == GameState::Splash);

    if (inWorld || state == GameState::Cutscene) {
        CameraData cam = state == GameState::Cutscene ? cutscene.camera(window->aspect())
                                                      : player.buildCamera(window->aspect());
        if (state != GameState::Cutscene) lastCamera = cam;
        renderer->sky().enabled = false;
        renderer->beginFrame(cam, globalTime, 0.016f);
        if (state != GameState::Cutscene && flashlight.glowIntensity() > 0.01f) renderer->submitLight(flashlight.buildLight());
        world.collectRender(*renderer, cam, 44.0f);
        director.submitPresences(*renderer);
        jumpscare.submit(*renderer);
        coop.submitRemotes(*renderer);
        renderer->render();
    } else if (menuBackdrop) {
        updateMenuCamera(0.016f);
        renderer->sky().enabled = false;
        renderer->beginFrame(menuCam, globalTime, 0.016f);
        world.collectRender(*renderer, menuCam, 40.0f);
        renderer->render();
    } else {
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glViewport(0, 0, window->width(), window->height());
        glClearColor(0.012f, 0.014f, 0.017f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    }
}

void Game::drawOverlay() {
    hitRects.clear();

    if (coopMenu.visible()) {
        coopMenu.draw(globalTime);
        if (fadeAmount > 0.001f) {
            ui->rect(0, 0, (float)window->width(), (float)window->height(), Vec4(0, 0, 0, fadeAmount));
        }
        return;
    }
    coopMenu.drawHudBadge(globalTime);

    switch (state) {
    case GameState::Splash: drawSplash(); break;
    case GameState::MainMenu: drawMenu(); break;
    case GameState::Options: drawOptions(); break;
    case GameState::Loading: drawLoading(); break;
    case GameState::Playing: drawHud(); break;
    case GameState::Paused: drawHud(); drawPause(); break;
    case GameState::Reading:
    case GameState::Listening: drawReading(); break;
    case GameState::Journal: drawJournal(); break;
    case GameState::Ending: drawEnding(); break;
    case GameState::Credits: drawEnding(); break;
    case GameState::Cutscene: drawCutscene(); break;
    }

    if (fadeAmount > 0.001f) {
        ui->rect(0, 0, (float)window->width(), (float)window->height(), Vec4(0, 0, 0, fadeAmount));
    }
}

void Game::shutdown() {
    if (inGameSession() && (state == GameState::Playing || state == GameState::Paused ||
                            state == GameState::Journal || state == GameState::Reading ||
                            state == GameState::Listening)) {
        saveGame("quicksave");
    }
    settings.save();
    if (ownsSystems) {
        audio->shutdown();
        ui->shutdown();
        renderer->shutdown();
    }
    coop.shutdown();
    world.destroy();
    humanRig.destroy();
    horrorRig.destroy();
    propLib.destroy();
}

void Game::pushHit(float x, float y, float w, float h, int action, int value) {
    HitRect r;
    r.x = x; r.y = y; r.w = w; r.h = h;
    r.action = action; r.value = value;
    hitRects.push_back(r);
}

bool Game::isHovered(int action, int value) const {
    return hoverAction == action && hoverValue == value;
}

void Game::updateMouseUi() {
    mousePos = window->input().mousePos();
    int lastAction = hoverAction;
    int lastValue = hoverValue;
    hoverAction = UI_NONE;
    hoverValue = -1;

    for (int i = (int)hitRects.size() - 1; i >= 0; i--) {
        const HitRect& r = hitRects[(size_t)i];
        if (mousePos.x >= r.x && mousePos.x <= r.x + r.w && mousePos.y >= r.y && mousePos.y <= r.y + r.h) {
            hoverAction = r.action;
            hoverValue = r.value;
            break;
        }
    }

    bool changed = hoverAction != lastAction || hoverValue != lastValue;

    switch (hoverAction) {
    case UI_MENU_ITEM:
    case UI_PAUSE_ITEM:
        if (changed) audio->play2D(SFX_CLICK, 0.16f, 1.35f);
        menuIndex = hoverValue;
        break;
    case UI_OPTION_ROW:
    case UI_OPTION_DEC:
    case UI_OPTION_INC:
        optionIndex = hoverValue;
        break;
    case UI_JOURNAL_ROW:
        journalIndex = hoverValue;
        break;
    default:
        break;
    }

    if (window->input().mousePressed(MOUSE_LEFT) && hoverAction != UI_NONE) {
        activateUi(hoverAction, hoverValue);
    }
}

void Game::activateUi(int action, int value) {
    switch (action) {
    case UI_MENU_ITEM:
        audio->play2D(SFX_CLICK, 0.45f, 0.9f);
        activateMenuItem(value);
        break;
    case UI_PAUSE_ITEM:
        audio->play2D(SFX_CLICK, 0.45f, 0.9f);
        activatePauseItem(value);
        break;
    case UI_OPTION_ROW:
        if (value == kOptionCount - 1) {
            audio->play2D(SFX_CLICK, 0.4f, 0.9f);
            settings.save();
            setState(previousState == GameState::Paused ? GameState::Paused : GameState::MainMenu);
        } else if (value == 2 || value == 3 || value == 4 || value == 6) {
            adjustOption(value, 1);
        }
        break;
    case UI_OPTION_DEC: adjustOption(value, -1); break;
    case UI_OPTION_INC: adjustOption(value, 1); break;
    case UI_JOURNAL_TAB:
        journalTab = value;
        journalIndex = 0;
        audio->play2D(SFX_CLICK, 0.3f, 1.2f);
        break;
    case UI_JOURNAL_ROW:
        journalIndex = value;
        if (journalTab == 1) {
            int found = 0;
            for (int i = 0; i < (int)progress.documentsFound.size(); i++) {
                if (!progress.documentsFound[(size_t)i]) continue;
                if (found == value) {
                    readingDoc = i;
                    readingPage = 0;
                    audio->play2D(SFX_PAPER, 0.4f, 1.0f);
                    setState(GameState::Reading);
                    return;
                }
                found++;
            }
        }
        break;
    case UI_DOC_NEXT: {
        const Document* doc = story.document(readingDoc);
        if (doc && readingPage + 1 < (int)doc->pages.size()) {
            readingPage++;
            audio->play2D(SFX_PAPER, 0.35f, 1.1f);
        } else {
            setState(GameState::Playing);
        }
        break;
    }
    case UI_DOC_PREV:
        if (readingPage > 0) {
            readingPage--;
            audio->play2D(SFX_PAPER, 0.35f, 0.95f);
        }
        break;
    case UI_DOC_CLOSE:
        audio->play2D(SFX_CLICK, 0.35f, 1.0f);
        setState(GameState::Playing);
        break;
    case UI_SKIP:
        if (state == GameState::Splash) {
            setState(GameState::MainMenu);
            fadeAmount = 1.0f;
            fadeTarget = 0.0f;
        } else if (state == GameState::Credits) {
            endingId = -1;
            currentSeed = 0;
            setState(GameState::MainMenu);
        }
        break;
    default:
        break;
    }
}

void Game::activateMenuItem(int index) {
    switch (index) {
    case 0: setState(GameState::Loading); break;
    case 1:
        if (hasSave) loadGame("quicksave");
        else addToast("Kein Spielstand vorhanden");
        break;
    case 2: coopMenu.open(); break;
    case 3: optionIndex = 0; setState(GameState::Options); break;
    case 4:
        if (ownsSystems) quitRequested = true;
        else collectionRequested = true;
        break;
    }
}

void Game::activatePauseItem(int index) {
    switch (index) {
    case 0: setState(GameState::Playing); break;
    case 1: saveGame("quicksave"); break;
    case 2: coopMenu.open(); break;
    case 3: optionIndex = 0; setState(GameState::Options); break;
    case 4: returnToMainMenu(); break;
    }
}

void Game::returnToMainMenu() {
    if (inGameSession()) {
        saveGame("quicksave");
        addToast("Spielstand gesichert");
    }
    audio->stopAll();
    cutscene.stop();
    setupMenuCamera();
    setState(GameState::MainMenu);
    menuIndex = hasSave ? 1 : 0;
    fadeAmount = 1.0f;
    fadeTarget = 0.0f;
}

bool Game::inGameSession() const {
    return !world.rooms().empty() && currentSeed != 0 && endingId < 0;
}

void Game::adjustOption(int index, int dir) {
    switch (index) {
    case 0:
        settings.masterVolume = clampf(settings.masterVolume + dir * 0.05f, 0.0f, 1.0f);
        audio->setMasterVolume(settings.masterVolume);
        audio->play2D(SFX_CLICK, 0.4f, 1.0f);
        break;
    case 1:
        settings.sensitivity = clampf(settings.sensitivity + dir * 0.0002f, 0.0004f, 0.008f);
        player.setSensitivity(settings.sensitivity);
        break;
    case 2:
        settings.invertY = !settings.invertY;
        player.setInvertY(settings.invertY);
        audio->play2D(SFX_CLICK, 0.35f, 1.1f);
        break;
    case 3:
        settings.subtitles = !settings.subtitles;
        audio->play2D(SFX_CLICK, 0.35f, 1.1f);
        break;
    case 4:
        settings.tutorial = !settings.tutorial;
        if (!settings.tutorial) tutorial.skip();
        audio->play2D(SFX_CLICK, 0.35f, 1.1f);
        break;
    case 5: {
        settings.qualityPreset = clampi(settings.qualityPreset + dir, 0, 3);
        QualitySettings q;
        q.applyPreset(settings.qualityPreset);
        renderer->setQuality(q);
        audio->play2D(SFX_CLICK, 0.35f, 1.0f);
        break;
    }
    case 6:
        settings.fullscreen = !settings.fullscreen;
        window->setFullscreen(settings.fullscreen);
        break;
    default:
        break;
    }
}

void Game::setupMenuCamera() {
    if (world.rooms().empty()) {
        menuWorldReady = false;
        return;
    }

    int best = -1;
    float bestLen = 0.0f;
    for (const auto& room : world.rooms()) {
        if (room.type != ROOM_CORRIDOR || room.floor != 1) continue;
        float len = std::max(room.rect.w, room.rect.d);
        if (len > bestLen) { bestLen = len; best = room.id; }
    }
    if (best < 0) {
        for (const auto& room : world.rooms()) {
            if (room.type != ROOM_CORRIDOR) continue;
            float len = std::max(room.rect.w, room.rect.d);
            if (len > bestLen) { bestLen = len; best = room.id; }
        }
    }
    if (best < 0) { menuWorldReady = false; return; }

    const Room& room = world.rooms()[(size_t)best];
    bool alongX = room.rect.w > room.rect.d;
    Vec2 c = room.rect.center();

    if (alongX) {
        menuCamBase = Vec3(room.rect.x + 1.3f, room.floorY + 1.62f, c.y);
        menuCamDir = Vec3(1, 0, 0);
    } else {
        menuCamBase = Vec3(c.x, room.floorY + 1.62f, room.rect.z + 1.3f);
        menuCamDir = Vec3(0, 0, 1);
    }

    for (int lightId : room.lights) {
        LightFixture& l = world.lights()[(size_t)lightId];
        if (l.broken) continue;
        l.on = true;
        if (l.flickerAmount < 0.15f) l.flickerAmount = 0.18f;
    }

    menuCamPhase = 0.0f;
    menuWorldReady = true;
}

void Game::updateMenuCamera(float dt) {
    if (!menuWorldReady) return;
    menuCamPhase += dt * 0.055f;
    float drift = std::sin(menuCamPhase * TAU) * 0.5f + 0.5f;

    menuCam.position = menuCamBase + menuCamDir * (drift * 3.4f);
    menuCam.position.y = menuCamBase.y + std::sin(menuCamPhase * 3.1f) * 0.035f;
    Vec3 target = menuCamBase + menuCamDir * 26.0f;
    target.y = menuCamBase.y - 0.16f + std::sin(menuCamPhase * 2.2f) * 0.05f;
    Vec3 side = normalize(cross(menuCamDir, Vec3(0, 1, 0)));
    target += side * std::sin(menuCamPhase * 1.7f) * 1.1f;

    menuCam.forward = normalize(target - menuCam.position);
    menuCam.fovY = 1.02f;
    menuCam.nearPlane = 0.05f;
    menuCam.farPlane = 240.0f;
    menuCam.update(window->aspect());
}

void Game::applyCampaignEvent(int id) {
    Vec3 p = player.position();
    int room = world.roomAt(p + Vec3(0, 0.6f, 0));

    switch (id) {
    case 1: {
        if (room >= 0) {
            for (int n : world.rooms()[(size_t)room].neighbors) {
                if (n < 0 || n >= (int)world.rooms().size()) continue;
                if (world.rooms()[(size_t)n].type != ROOM_CORRIDOR) continue;
                for (int lid : world.rooms()[(size_t)n].lights) {
                    LightFixture& l = world.lights()[(size_t)lid];
                    if (!l.emergency) l.flickerAmount = std::max(l.flickerAmount, 0.7f);
                }
            }
        }
        audio->playAt(SFX_WHISPER, p - player.flatForward() * 3.0f + Vec3(0, 1.5f, 0), 0.6f, 1.0f);
        break;
    }
    case 2:
        audio->play2D(SFX_STING_LOW, 0.42f, 1.0f);
        flashlight.forceFlicker(2.4f, 0.8f);
        player.addShake(0.18f, 0.5f);
        break;
    case 3:
        audio->play2D(SFX_STING_HIGH, 0.5f, 1.0f);
        if (room >= 0) {
            for (int lid : world.rooms()[(size_t)room].lights) world.lights()[(size_t)lid].flickerAmount = 1.0f;
        }
        break;
    case 4:
        audio->play2D(SFX_DRONE, 0.30f, 1.0f);
        break;
    case 20:
        break;
    default:
        if (id >= 10 && id < 20) {
            audio->play2D(SFX_DRAWER, 0.55f, 0.9f);
            addToast("Transport abgeschlossen", 3.4f);
        }
        break;
    }
}

void Game::setState(GameState s) {
    previousState = state;
    state = s;
    stateTime = 0.0f;
    hitRects.clear();
    hoverAction = UI_NONE;
    hoverValue = -1;

    bool wantLock = (s == GameState::Playing);
    if (wantLock != cursorLocked) {
        cursorLocked = wantLock;
        window->setCursorLocked(wantLock);
    }
    audio->setDucking(s == GameState::Playing ? 0.0f : 0.35f);

    bool wantMusic = s == GameState::Splash || s == GameState::MainMenu ||
                     s == GameState::Options || s == GameState::Credits;
    if (wantMusic) {
        if (!audio->isPlaying(musicHandle)) {
            PlayParams mp;
            mp.spatial = false;
            mp.looping = true;
            mp.volume = 0.52f;
            mp.reverbSend = 0.30f;
            mp.fadeIn = 3.0f;
            musicHandle = audio->play(SFX_MUSIC_LOBBY, mp);
        }
    } else if (audio->isPlaying(musicHandle)) {
        audio->stop(musicHandle, 1.8f);
    }
}

void Game::addToast(const std::string& text, float duration) {
    Toast t;
    t.text = text;
    t.duration = duration;
    t.timer = duration;
    toasts.push_back(t);
    if (toasts.size() > 4) toasts.erase(toasts.begin());
}

bool Game::hasItem(int itemId) const {
    if (itemId < 0 || itemId >= (int)progress.itemCounts.size()) return false;
    return progress.itemCounts[(size_t)itemId] > 0;
}

void Game::addItem(int itemId, int count) {
    if (itemId < 0 || itemId >= (int)progress.itemCounts.size()) return;
    int v = progress.itemCounts[(size_t)itemId] + count;
    progress.itemCounts[(size_t)itemId] = (u8)clampi(v, 0, 255);
}

void Game::startNewGame(u64 seed) {
    currentSeed = seed;
    progress = GameProgress();
    progress.worldSeed = seed;
    progress.itemCounts.assign((size_t)ITEM_COUNT, 0);
    progress.documentsFound.assign((size_t)story.documentCount(), 0);
    progress.logsFound.assign((size_t)story.audioLogCount(), 0);

    WorldConfig cfg;
    cfg.seed = seed;
    world.generate(cfg, propLib);
    placeStoryContent();

    player.reset(world.spawnPoint() + Vec3(0, 0.05f, 0), world.spawnYaw());
    player.setSensitivity(settings.sensitivity);
    player.setInvertY(settings.invertY);
    player.setFovBase(settings.fov * DEG2RAD);

    flashlight.reset();
    flashlight.setOn(false);
    addItem(ITEM_FLASHLIGHT);
    addItem(ITEM_WRISTBAND);

    director.init(&world, audio, &humanRig, seed);
    if (!horrorRig.ready()) horrorRig.build();
    jumpscare.init(&world, audio, &horrorRig, seed);
    guide.init(&world);
    guideTargetCache = em::Vec3(0, -9999, 0);
    guideLabelCache.clear();
    scareFlash = 0.0f;
    scareRing = 0.0f;
    campaign.init(&world, seed);
    cutscene.stop();
    tutorial.reset(settings.tutorial);
    riding = false;
    rideCab = -1;
    rideCooldown = 3.0f;
    rideAutoTimer = 1.2f;
    player.setMovementLock(false);
    lastSafePos = player.position();
    safeTimer = 0.0f;
    playTime = 0.0f;
    autosaveTimer = 120.0f;
    subtitleTimer = 0.0f;
    toasts.clear();

    addToast("ECHO", 4.0f);
    director.queueSubtitle("(Irgendwo tropft Wasser.)", 4.0f);
    if (world.hasStartVent()) {
        addToast("Der Generalschluessel liegt im Lueftungsschacht", 7.0f);
        addToast("STRG ducken, dann hineinkriechen", 9.0f);
    }

    setState(GameState::Playing);
    fadeAmount = 1.0f;
    fadeTarget = 0.0f;
}

void Game::placeStoryContent() {
    Rng rng(hashCombine(currentSeed, 0x00D0C5ULL));

    auto addInteract = [&](int kind, int roomId, const Vec3& pos, int content, int item, const std::string& prompt) {
        Interactable it;
        it.id = (int)world.interactables().size();
        it.kind = kind;
        it.room = roomId;
        it.floor = roomId >= 0 ? world.rooms()[(size_t)roomId].floor : 0;
        it.position = pos;
        it.contentId = content;
        it.itemId = item;
        it.prompt = prompt;
        it.oneShot = true;
        world.interactables().push_back(it);
        if (roomId >= 0) world.rooms()[(size_t)roomId].interactables.push_back(it.id);
        return it.id;
    };

    auto addPickupModel = [&](int propType, int roomId, const Vec3& pos, float yaw, float scale) {
        if (roomId < 0 || roomId >= (int)world.rooms().size()) return -1;
        PropInstance p;
        p.id = (int)world.props().size();
        p.type = propType;
        p.room = roomId;
        p.floor = world.rooms()[(size_t)roomId].floor;
        p.position = pos;
        p.yaw = yaw;
        p.scale = Vec3(scale, scale, scale);
        p.originalPosition = p.position;
        p.originalYaw = p.yaw;
        world.props().push_back(p);
        world.rooms()[(size_t)roomId].props.push_back(p.id);
        return p.id;
    };

    std::vector<int> candidates;
    for (const auto& r : world.rooms()) {
        if (r.type == ROOM_CORRIDOR || r.type == ROOM_STAIRWELL || r.type == ROOM_ELEVATOR) continue;
        if (r.rect.area() < 9.0f) continue;
        candidates.push_back(r.id);
    }
    if (candidates.empty()) return;
    rng.shuffle(candidates);

    int index = 0;
    for (const Document& doc : story.documents()) {
        int roomId = candidates[(size_t)(index++ % candidates.size())];
        Vec3 pos = world.randomPointInRoom(roomId, rng);
        pos.y = world.rooms()[(size_t)roomId].floorY + 0.78f;
        addInteract(INTERACT_DOCUMENT, roomId, pos, doc.id, ITEM_NONE, "Dokument lesen");

        PropInstance p;
        p.id = (int)world.props().size();
        p.type = PROP_PAPER_PILE;
        p.room = roomId;
        p.floor = world.rooms()[(size_t)roomId].floor;
        p.position = pos - Vec3(0, 0.02f, 0);
        p.yaw = rng.range(0, TAU);
        p.originalPosition = p.position;
        p.originalYaw = p.yaw;
        world.props().push_back(p);
        world.rooms()[(size_t)roomId].props.push_back(p.id);
    }

    for (const AudioLog& log : story.audioLogs()) {
        int roomId = candidates[(size_t)(index++ % candidates.size())];
        Vec3 pos = world.randomPointInRoom(roomId, rng);
        pos.y = world.rooms()[(size_t)roomId].floorY + 0.80f;
        addInteract(INTERACT_AUDIOLOG, roomId, pos, log.id, ITEM_NONE, "Aufnahme abspielen");

        PropInstance p;
        p.id = (int)world.props().size();
        p.type = PROP_DEFIBRILLATOR;
        p.room = roomId;
        p.floor = world.rooms()[(size_t)roomId].floor;
        p.position = pos - Vec3(0, 0.78f, 0);
        p.yaw = rng.range(0, TAU);
        p.scale = Vec3(0.42f, 0.42f, 0.42f);
        p.originalPosition = p.position;
        p.originalYaw = p.yaw;
        world.props().push_back(p);
        world.rooms()[(size_t)roomId].props.push_back(p.id);
    }

    for (int i = 0; i < 14; i++) {
        int roomId = candidates[(size_t)(index++ % candidates.size())];
        Vec3 pos = world.randomPointInRoom(roomId, rng);
        pos.y = world.rooms()[(size_t)roomId].floorY + 0.55f;
        int id = addInteract(INTERACT_PICKUP, roomId, pos, -1, ITEM_BATTERY, "Batterie nehmen");
        world.interactables()[(size_t)id].propId =
            addPickupModel(PROP_BATTERY, roomId, pos - Vec3(0, 0.03f, 0), rng.range(0, TAU), 1.35f);
    }

    {
        int startRoom = world.startRoom();
        if (startRoom < 0) startRoom = world.roomAt(world.spawnPoint() + Vec3(0, 0.6f, 0));
        if (startRoom >= 0) {
            float floorY = world.rooms()[(size_t)startRoom].floorY;

            Vec3 keyPos;
            if (world.hasStartVent()) {
                keyPos = world.ventKeyPosition();
            } else {
                keyPos = world.roomCenter(startRoom);
                keyPos.y = floorY + 0.82f;
                keyPos.x += 0.9f;
            }
            int keyId = addInteract(INTERACT_PICKUP, startRoom, keyPos, -1, ITEM_KEYCARD, "Generalschluessel nehmen");
            world.interactables()[(size_t)keyId].propId =
                addPickupModel(PROP_KEYRING, startRoom, keyPos - Vec3(0, 0.06f, 0), rng.range(0, TAU), 1.7f);

            Vec3 batPos = world.roomCenter(startRoom);
            batPos.y = floorY + 0.55f;
            batPos.x -= 0.9f;
            int batId = addInteract(INTERACT_PICKUP, startRoom, batPos, -1, ITEM_BATTERY, "Batterie nehmen");
            world.interactables()[(size_t)batId].propId =
                addPickupModel(PROP_BATTERY, startRoom, batPos - Vec3(0, 0.03f, 0), rng.range(0, TAU), 1.35f);
        }
    }

    int keys[] = { ITEM_KEY_WARD, ITEM_KEY_BASEMENT, ITEM_KEY_OR, ITEM_KEY_ARCHIVE, ITEM_KEYCARD };
    for (int k : keys) {
        int roomId = candidates[(size_t)(index++ % candidates.size())];
        Vec3 pos = world.randomPointInRoom(roomId, rng);
        pos.y = world.rooms()[(size_t)roomId].floorY + 0.80f;
        int id = addInteract(INTERACT_PICKUP, roomId, pos, -1, k, std::string(itemDef(k).name) + " nehmen");
        world.interactables()[(size_t)id].propId =
            addPickupModel(PROP_KEYRING, roomId, pos - Vec3(0, 0.06f, 0), rng.range(0, TAU), 1.7f);
    }

    LOG_INFO("Story content placed: %d documents, %d logs", story.documentCount(), story.audioLogCount());
}

void Game::loadGame(const std::string& slot) {
    SaveMeta meta = SaveSystem::peek(slot);
    if (!meta.valid) {
        addToast("Kein gueltiger Spielstand");
        return;
    }

    std::vector<u8> probe;
    GameProgress temp;
    temp.itemCounts.assign((size_t)ITEM_COUNT, 0);

    WorldConfig cfg;
    {
        SaveMeta m = SaveSystem::peek(slot);
        (void)m;
    }

    GameProgress loaded;
    Player tempPlayer;
    Flashlight tempLight;

    std::vector<u8> raw;
    if (!fs::readBinary(SaveSystem::slotPath(slot), raw) || raw.size() < 24) {
        addToast("Spielstand beschaedigt");
        return;
    }
    u64 seed = 0;
    std::memcpy(&seed, raw.data() + 8, sizeof(u64));

    currentSeed = seed;
    cfg.seed = seed;
    world.generate(cfg, propLib);
    progress = GameProgress();
    progress.worldSeed = seed;
    progress.itemCounts.assign((size_t)ITEM_COUNT, 0);
    progress.documentsFound.assign((size_t)story.documentCount(), 0);
    progress.logsFound.assign((size_t)story.audioLogCount(), 0);
    placeStoryContent();

    director.init(&world, audio, &humanRig, seed);
    if (!horrorRig.ready()) horrorRig.build();
    jumpscare.init(&world, audio, &horrorRig, seed);
    guide.init(&world);
    guideTargetCache = em::Vec3(0, -9999, 0);
    guideLabelCache.clear();
    scareFlash = 0.0f;
    scareRing = 0.0f;
    campaign.init(&world, seed);
    cutscene.stop();
    tutorial.reset(false);

    if (!SaveSystem::load(slot, world, player, flashlight, director, progress)) {
        addToast("Laden fehlgeschlagen");
        return;
    }

    world.physics().rebuildGrid();
    player.setSensitivity(settings.sensitivity);
    player.setInvertY(settings.invertY);
    player.setFovBase(settings.fov * DEG2RAD);
    playTime = progress.playTime;
    autosaveTimer = 120.0f;

    addToast("Spielstand geladen");
    setState(GameState::Playing);
    fadeAmount = 1.0f;
    fadeTarget = 0.0f;
}

void Game::saveGame(const std::string& slot) {
    progress.playTime = playTime;
    progress.worldSeed = currentSeed;
    if (SaveSystem::save(slot, world, player, flashlight, director, progress)) {
        hasSave = true;
        addToast("Gespeichert");
    }
}

std::string Game::interactionPrompt(const Interactable& it) const {
    switch (it.kind) {
    case INTERACT_DOOR: {
        if (it.targetId < 0 || it.targetId >= (int)world.doors().size()) return "Tuer";
        const Door& d = world.doors()[(size_t)it.targetId];
        if (d.jammed) return "Blockiert";
        if (d.locked) return "Verschlossen";
        return d.targetOpen > 0.5f ? "Tuer schliessen" : "Tuer oeffnen";
    }
    case INTERACT_SWITCH: return "Lichtschalter";
    case INTERACT_DOCUMENT: return "Dokument lesen";
    case INTERACT_AUDIOLOG: return "Aufnahme abspielen";
    case INTERACT_PICKUP: return it.prompt.empty() ? "Aufnehmen" : it.prompt;
    default: return it.prompt.empty() ? "Benutzen" : it.prompt;
    }
}

void Game::handleInteraction() {
    if (hoverInteractable < 0 || hoverInteractable >= (int)world.interactables().size()) return;
    Interactable& it = world.interactables()[(size_t)hoverInteractable];

    if (campaign.onInteract(it.kind, it.targetId, it.position)) {
        audio->playAt(SFX_DRAWER, it.position, 0.55f, 0.95f);
        return;
    }

    switch (it.kind) {
    case INTERACT_DOOR: {
        if (it.targetId < 0 || it.targetId >= (int)world.doors().size()) break;
        Door& d = world.doors()[(size_t)it.targetId];
        if (d.jammed) {
            audio->playAt(SFX_DOOR_LOCKED, d.center, 0.6f, 0.9f);
            addToast("Die Tuer ist blockiert");
            break;
        }
        if (d.locked) {
            bool opened = false;
            int required[] = { ITEM_KEY_WARD, ITEM_KEY_BASEMENT, ITEM_KEY_OR, ITEM_KEY_ARCHIVE, ITEM_KEYCARD };
            for (int k : required) {
                if (hasItem(k)) { opened = true; break; }
            }
            if (!opened) {
                audio->playAt(SFX_DOOR_LOCKED, d.center, 0.7f, 1.0f);
                addToast("Verschlossen");
                break;
            }
            d.locked = false;
            addToast("Aufgeschlossen");
        }
        int entryCab = d.roomA != d.roomB ? world.cabForDoor(it.targetId) : -1;
        if (entryCab >= 0) {
            world.setDoorOpen(it.targetId, true);
            coop.sendInteract("door", std::to_string(it.targetId), 1.0, d.center);
            audio->playAt(SFX_DOOR_OPEN, d.center, 0.65f, 0.95f);
            director.notifyInteract(INTERACT_DOOR, it.targetId, d.center);
            enterCab(entryCab);
            break;
        }
        world.toggleDoor(it.targetId);
        coop.sendInteract("door", std::to_string(it.targetId), d.targetOpen > 0.5f ? 1.0 : 0.0, d.center);
        audio->playAt(d.targetOpen > 0.5f ? SFX_DOOR_OPEN : SFX_DOOR_CLOSE, d.center, 0.65f, 0.95f + (float)(it.targetId % 7) * 0.012f);
        director.notifyInteract(INTERACT_DOOR, it.targetId, d.center);
        break;
    }
    case INTERACT_SWITCH: {
        int roomId = it.targetId;
        if (roomId < 0 || roomId >= (int)world.rooms().size()) break;
        const Room& room = world.rooms()[(size_t)roomId];
        bool anyOn = false;
        for (int lid : room.lights) if (world.lights()[(size_t)lid].on && !world.lights()[(size_t)lid].broken) anyOn = true;
        world.setRoomLights(roomId, !anyOn, true);
        coop.sendInteract("switch", std::to_string(roomId), anyOn ? 0.0 : 1.0, it.position);
        audio->playAt(SFX_SWITCH, it.position, 0.55f, 1.0f);
        break;
    }
    case INTERACT_DOCUMENT: {
        readingDoc = it.contentId;
        readingPage = 0;
        if (readingDoc >= 0 && readingDoc < (int)progress.documentsFound.size() && !progress.documentsFound[(size_t)readingDoc]) {
            progress.documentsFound[(size_t)readingDoc] = 1;
            const Document* doc = story.document(readingDoc);
            director.notifyDocumentRead(doc ? doc->truthLayer : 0);
        }
        audio->play2D(SFX_PAPER, 0.5f, 1.0f);
        it.used = true;
        setState(GameState::Reading);
        break;
    }
    case INTERACT_AUDIOLOG: {
        listeningLog = it.contentId;
        listeningLine = 0;
        listeningTimer = 0.0f;
        if (listeningLog >= 0 && listeningLog < (int)progress.logsFound.size() && !progress.logsFound[(size_t)listeningLog]) {
            progress.logsFound[(size_t)listeningLog] = 1;
            const AudioLog* log = story.audioLog(listeningLog);
            director.notifyLogHeard(log ? log->truthLayer : 0);
        }
        audio->play2D(SFX_CLICK, 0.6f, 1.0f);
        audio->play2D(SFX_TAPE_HISS, 0.22f, 1.0f);
        it.used = true;
        setState(GameState::Listening);
        break;
    }
    case INTERACT_PICKUP: {
        if (it.used) break;
        it.used = true;
        it.hidden = true;
        if (it.propId >= 0) {
            world.hideProp(it.propId, true);
            world.refreshCollider(it.propId);
        }
        addItem(it.itemId, 1);
        if (it.itemId == ITEM_BATTERY) flashlight.addSpare(1);
        audio->playAt(SFX_PICKUP, it.position, 0.6f, 1.0f);
        addToast(std::string(itemDef(it.itemId).name) + " aufgenommen");
        break;
    }
    default:
        break;
    }
}

void Game::updateFootsteps(float dt) {
    FootstepEvent step;
    while (player.consumeFootstep(step)) {
        int roomId = world.roomAt(step.position + Vec3(0, 0.4f, 0));
        int sound = SFX_STEP_TILE;
        if (roomId >= 0) {
            int mat = world.rooms()[(size_t)roomId].floorMaterial;
            if (mat == MAT_CONCRETE_FLOOR) sound = SFX_STEP_CONCRETE;
            else if (mat == MAT_FLOOR_LINO) sound = SFX_STEP_LINO;
            else if (mat == MAT_TILE_FLOOR_SMALL || mat == MAT_FLOOR_CHECKER) sound = SFX_STEP_TILE;
            if (world.rooms()[(size_t)roomId].type == ROOM_STAIRWELL) sound = SFX_STEP_METAL;
        }
        PlayParams p;
        p.position = step.position + Vec3(0, 0.1f, 0);
        p.volume = step.loudness * 0.5f;
        p.pitch = 0.92f + hash11(globalTime * 13.7f) * 0.18f;
        p.minDistance = 0.6f;
        p.maxDistance = 16.0f;
        p.reverbSend = 0.45f;
        audio->play(sound, p);
    }

    DoorSoundEvent ev;
    while (world.consumeSound(ev)) {
        int sound = SFX_DOOR_CREAK;
        if (ev.kind == 0) sound = SFX_DOOR_OPEN;
        else if (ev.kind == 1) sound = SFX_DOOR_CLOSE;
        else if (ev.kind == 2) sound = SFX_LIGHT_POP;
        audio->playAt(sound, ev.position, ev.volume * 0.5f, 0.95f);
    }
}

void Game::updateAtmosphere(float dt) {
    AtmosphereParams& atmos = renderer->atmosphere();
    PostParams& post = renderer->post();

    float tension = director.tension();
    float sanity = director.sanity();
    int floorIndex = world.floorAt(player.position().y);

    Vec3 baseTop(0.190f, 0.212f, 0.248f);
    Vec3 baseBottom(0.082f, 0.090f, 0.104f);
    if (floorIndex == 0) {
        baseTop = Vec3(0.130f, 0.126f, 0.118f);
        baseBottom = Vec3(0.058f, 0.054f, 0.050f);
    }

    float dim = 1.0f - tension * 0.28f;
    atmos.ambientTop = baseTop * dim * settings.brightness;
    atmos.ambientBottom = baseBottom * dim * settings.brightness;
    atmos.fogDensity = lerpf(0.0092f, 0.020f, tension * 0.6f + (floorIndex == 0 ? 0.35f : 0.0f));
    atmos.fogColor = lerp(Vec3(0.070f, 0.086f, 0.104f), Vec3(0.10f, 0.075f, 0.065f), floorIndex == 0 ? 0.6f : 0.0f);
    atmos.globalWetness = floorIndex == 0 ? 0.35f : 0.05f;
    atmos.decay = 0.45f + (3 - floorIndex) * 0.08f;
    atmos.dust = 0.18f + tension * 0.2f;

    post.sanity = sanity;
    post.distortion = director.distortion() * 0.85f;
    post.saturation = lerpf(0.92f, 0.62f, 1.0f - sanity);
    post.contrast = lerpf(1.04f, 1.16f, tension);
    post.vignette = lerpf(0.58f, 1.05f, tension);
    post.grain = lerpf(0.032f, 0.075f, 1.0f - sanity);
    post.chromatic = lerpf(0.0008f, 0.0032f, director.distortion());
    post.pulse = tension > 0.6f ? (tension - 0.6f) * 0.6f : 0.0f;
    post.exposure = lerpf(2.35f, 2.0f, tension) * settings.brightness;

    if (scareFlash > 0.01f) {
        post.saturation = lerpf(post.saturation, 1.45f, scareFlash);
        post.contrast = lerpf(post.contrast, 1.42f, scareFlash);
        post.vignette = lerpf(post.vignette, 1.55f, scareFlash);
        post.grain = lerpf(post.grain, 0.20f, scareFlash);
        post.chromatic = lerpf(post.chromatic, 0.010f, scareFlash);
        post.pulse = std::max(post.pulse, scareFlash * 1.35f);
        post.distortion = std::max(post.distortion, scareFlash * 0.75f);
        post.exposure *= 1.0f + scareFlash * 0.55f;
        atmos.dust = std::max(atmos.dust, scareFlash * 0.85f);
    }

    float breath = player.breathLevel();
    atmos.warp = Vec4(player.position().x, player.position().z, 0.02f, director.distortion() * 0.35f);

    audio->setListener(player.eyePosition(), player.forward(), Vec3(0, 1, 0), player.velocityVec());

    if (breath > 0.55f && !audio->isPlaying(ambienceLoop)) {
        PlayParams p;
        p.spatial = false;
        p.volume = clampf((breath - 0.55f) * 0.7f, 0.0f, 0.35f);
        p.looping = false;
        p.reverbSend = 0.1f;
        ambienceLoop = audio->play(SFX_BREATH, p);
    }
}

void Game::checkEndingConditions(float dt) {
    const BehaviorProfile& p = director.tracker().profile();
    if (playTime < 300.0f) return;

    bool allTruth = p.truthLayers >= 3;
    bool longPlay = playTime > 1500.0f;
    bool deepDark = p.darkRatio > 0.5f && director.sanity() < 0.28f;

    if (deepDark && world.floorAt(player.position().y) == 0) {
        triggerEnding(ENDING_DISSOLUTION);
        return;
    }
    if ((allTruth || longPlay) && exitProximity > 0.9f) {
        triggerEnding(director.chooseEnding());
    }
}

void Game::triggerEnding(int id) {
    endingId = clampi(id, 0, ENDING_COUNT - 1);
    endingLine = 0;
    endingTimer = 0.0f;
    progress.endingSeen = endingId;
    audio->stopAll();
    audio->play2D(SFX_STING_LOW, 0.5f, 1.0f);
    setState(GameState::Ending);
    fadeAmount = 1.0f;
    fadeTarget = 0.0f;
}

int Game::findExitInteractable() const {
    return -1;
}

void Game::updateSplash(float dt) {
    if (stateTime > 1.0f && (window->input().anyKeyPressed() || stateTime > 5.6f)) {
        setState(GameState::MainMenu);
        fadeAmount = 1.0f;
        fadeTarget = 0.0f;
    }
}

void Game::updateMenu(float dt) {
    Input& in = window->input();
    if (in.keyPressed(KEY_DOWN) || in.keyPressed(KEY_S)) {
        menuIndex = (menuIndex + 1) % kMenuCount;
        audio->play2D(SFX_CLICK, 0.3f, 1.2f);
    }
    if (in.keyPressed(KEY_UP) || in.keyPressed(KEY_W)) {
        menuIndex = (menuIndex + kMenuCount - 1) % kMenuCount;
        audio->play2D(SFX_CLICK, 0.3f, 1.2f);
    }
    if (in.keyPressed(KEY_ENTER) || in.keyPressed(KEY_SPACE) || in.keyPressed(KEY_E)) {
        audio->play2D(SFX_CLICK, 0.45f, 0.9f);
        activateMenuItem(menuIndex);
    }
}

void Game::updateOptions(float dt) {
    Input& in = window->input();
    if (in.keyPressed(KEY_DOWN) || in.keyPressed(KEY_S)) optionIndex = (optionIndex + 1) % kOptionCount;
    if (in.keyPressed(KEY_UP) || in.keyPressed(KEY_W)) optionIndex = (optionIndex + kOptionCount - 1) % kOptionCount;

    float step = in.key(KEY_SHIFT) ? 4.0f : 1.0f;
    int dir = 0;
    if (in.keyPressed(KEY_RIGHT) || in.keyPressed(KEY_D)) dir = 1;
    if (in.keyPressed(KEY_LEFT) || in.keyPressed(KEY_A)) dir = -1;

    if (dir != 0) {
        int repeats = (optionIndex == 0 || optionIndex == 1) ? (int)step : 1;
        for (int i = 0; i < repeats; i++) adjustOption(optionIndex, dir);
    }

    if (in.keyPressed(KEY_ENTER) || in.keyPressed(KEY_E)) {
        if (optionIndex == kOptionCount - 1) {
            settings.save();
            setState(GameState::MainMenu);
        }
    }
    if (in.keyPressed(KEY_ESCAPE)) {
        settings.save();
        setState(previousState == GameState::Paused ? GameState::Paused : GameState::MainMenu);
    }
}

void Game::updateElevator(float dt) {
    if (rideCooldown > 0.0f) rideCooldown -= dt;

    if (!riding) {
        int cabId = world.cabContaining(player.position());
        panelFloor = cabId;
        if (rideCooldown > 0.0f || cabId < 0) return;

        Input& in = window->input();
        int picked = -1;
        if (in.keyPressed(KEY_1)) picked = 0;
        else if (in.keyPressed(KEY_2)) picked = 1;
        else if (in.keyPressed(KEY_3)) picked = 2;
        else if (in.keyPressed(KEY_4)) picked = 3;

        if (picked >= 0) {
            beginRide(cabId, picked);
        } else if (rideAutoTimer <= 0.0f) {
            beginRide(cabId, -1);
        } else {
            rideAutoTimer -= dt;
        }
        return;
    }

    rideTimer += dt;
    const ElevatorCab& cab = world.cabs()[(size_t)rideCab];

    if (rideTimer > 0.35f && rideTimer < 0.45f && cab.doorId >= 0) {
        world.doors()[(size_t)cab.doorId].targetOpen = 0.0f;
    }

    if (rideTimer > 1.0f) fadeTarget = 1.0f;

    if (rideTimer > 2.4f && rideTargetFloor >= 0) {
        int destCab = world.cabOnFloor(cab.shaft, rideTargetFloor);
        if (destCab >= 0) {
            const ElevatorCab& dest = world.cabs()[(size_t)destCab];
            if (dest.doorId >= 0) {
                world.doors()[(size_t)dest.doorId].openAmount = 0.0f;
                world.doors()[(size_t)dest.doorId].targetOpen = 0.0f;
            }
            player.setPosition(dest.interior + Vec3(0, 0.06f, 0));
            lastSafePos = player.position();
            rideCab = destCab;
        }
        rideTargetFloor = -1;
    }

    if (rideTimer > 3.3f) fadeTarget = 0.0f;

    if (rideTimer > 3.6f && rideTimer < 3.7f) {
        const ElevatorCab& here = world.cabs()[(size_t)rideCab];
        if (here.doorId >= 0) world.doors()[(size_t)here.doorId].targetOpen = 1.0f;
        audio->play2D(SFX_ELEVATOR_DING, 0.55f, 1.0f);
        campaign.onFloorReached(here.floor);
        if (!campaign.objective().empty()) addToast(campaign.objective(), 5.5f);
    }

    if (rideTimer > 5.0f) {
        riding = false;
        rideCooldown = 2.5f;
        rideAutoTimer = 1.6f;
        player.setMovementLock(false);
        if (audio->isPlaying(rideHum)) audio->stop(rideHum, 0.6f);
    }

    player.addShake(0.035f, 0.2f);
}

void Game::enterCab(int cabId) {
    if (cabId < 0 || cabId >= (int)world.cabs().size()) return;
    const ElevatorCab& cab = world.cabs()[(size_t)cabId];
    if (world.cabContaining(player.position()) == cabId) return;

    if (cab.doorId >= 0 && cab.doorId < (int)world.doors().size()) {
        Door& cabDoor = world.doors()[(size_t)cab.doorId];
        cabDoor.jammed = false;
        cabDoor.locked = false;
        cabDoor.targetOpen = 1.0f;
        cabDoor.openAmount = 1.0f;
    }

    Vec3 inside = cab.interior + Vec3(0, 0.06f, 0);
    float lookYaw = std::atan2(cab.doorCenter.x - inside.x, inside.z - cab.doorCenter.z);
    player.setMovementLock(false);
    player.setPosition(inside);
    player.setOrientation(lookYaw, 0.0f);
    lastSafePos = player.position();

    riding = false;
    rideCab = cabId;
    panelFloor = cabId;
    rideTargetFloor = -1;
    rideTimer = 0.0f;
    rideCooldown = 0.0f;
    rideAutoTimer = 6.0f;

    audio->play2D(SFX_ELEVATOR_DING, 0.5f, 1.0f);
    addToast("Im Aufzug — 1 bis 4 waehlt die Etage", 4.5f);
}

void Game::beginRide(int cabId, int requestedFloor) {
    if (cabId < 0 || cabId >= (int)world.cabs().size()) return;
    const ElevatorCab& cab = world.cabs()[(size_t)cabId];

    int floorCount = (int)world.floors().size();
    int current = cab.floor;
    int target = requestedFloor;

    if (target < 0) {
        target = campaign.hasMarker() ? campaign.targetFloor() : -1;
        if (target < 0 || target == current) target = (current + 1) % floorCount;
    }
    target = clampi(target, 0, floorCount - 1);
    if (target == current) {
        rideAutoTimer = 1.5f;
        return;
    }

    riding = true;
    rideCab = cabId;
    rideTargetFloor = target;
    rideTimer = 0.0f;
    player.setMovementLock(true);
    player.setPosition(cab.interior + Vec3(0, 0.06f, 0));

    char buf[96];
    std::snprintf(buf, sizeof(buf), "ETAGE %d", target);
    rideText = buf;

    audio->play2D(SFX_DOOR_CLOSE, 0.5f, 0.85f);
    PlayParams hp;
    hp.spatial = false;
    hp.looping = true;
    hp.volume = 0.35f;
    hp.fadeIn = 0.5f;
    hp.reverbSend = 0.2f;
    rideHum = audio->play(SFX_ELEVATOR_HUM, hp);
}

void Game::drawRide() {
    if (!riding && panelFloor >= 0 && rideCooldown <= 0.0f) {
        float w = (float)window->width(), h = (float)window->height();
        const char* names[4] = { "1  KELLER", "2  ERDGESCHOSS", "3  ERSTE ETAGE", "4  ZWEITE ETAGE" };
        float size = h * 0.021f;
        float y = h * 0.62f;
        ui->text("ETAGE WAEHLEN", w * 0.5f, y - h * 0.045f, h * 0.018f,
                Vec4(kDim.x, kDim.y, kDim.z, 0.75f), ALIGN_CENTER, h * 0.005f);
        int here = world.cabs()[(size_t)panelFloor].floor;
        for (int i = 0; i < 4 && i < (int)world.floors().size(); i++) {
            bool cur = i == here;
            ui->text(names[i], w * 0.5f, y, size,
                    cur ? Vec4(kDim.x, kDim.y, kDim.z, 0.45f) : Vec4(kAccent.x, kAccent.y, kAccent.z, 0.9f),
                    ALIGN_CENTER, size * 0.08f);
            y += h * 0.031f;
        }
    }

    if (!riding) return;
    float w = (float)window->width(), h = (float)window->height();
    float a = clampf(rideTimer * 2.2f, 0.0f, 1.0f) * clampf((5.0f - rideTimer) * 1.4f, 0.0f, 1.0f);
    ui->textShadow(rideText, w * 0.5f, h * 0.30f, h * 0.040f, Vec4(kAccent.x, kAccent.y, kAccent.z, a), ALIGN_CENTER, h * 0.010f);
    ui->text("AUFZUG", w * 0.5f, h * 0.255f, h * 0.019f, Vec4(kDim.x, kDim.y, kDim.z, a * 0.7f), ALIGN_CENTER, h * 0.006f);
}

void Game::updatePlaying(float dt) {
    Input& in = window->input();
    playTime += dt;

    if (in.keyPressed(KEY_ESCAPE)) {
        TutorialSignals s;
        s.paused = true;
        tutorial.update(player, s, 0.0f);
        setState(GameState::Paused);
        return;
    }
    if (in.keyPressed(KEY_TAB)) {
        journalTab = 0;
        journalIndex = 0;
        TutorialSignals s;
        s.journalOpened = true;
        tutorial.update(player, s, 0.0f);
        setState(GameState::Journal);
        return;
    }
    if (in.keyPressed(KEY_F5)) saveGame("quicksave");
    if (in.keyPressed(KEY_F9) && SaveSystem::exists("quicksave")) { loadGame("quicksave"); return; }
    TutorialSignals tutSignals;
    if (in.keyPressed(KEY_F)) {
        flashlight.toggle();
        audio->play2D(SFX_CLICK, 0.35f, 1.4f);
        tutSignals.flashlightToggled = true;
    }
    if (in.keyPressed(KEY_R)) {
        if (flashlight.swapBattery()) {
            addToast("Batterie gewechselt");
            audio->play2D(SFX_DRAWER, 0.4f, 1.3f);
        } else {
            addToast("Keine Ersatzbatterie");
        }
    }

    PlayerInput pin;
    pin.move.y = (in.key(KEY_W) ? 1.0f : 0.0f) - (in.key(KEY_S) ? 1.0f : 0.0f);
    pin.move.x = (in.key(KEY_D) ? 1.0f : 0.0f) - (in.key(KEY_A) ? 1.0f : 0.0f);
    pin.look = in.mouseDelta();
    pin.sprint = in.key(KEY_SHIFT) && !campaign.carryingBody();
    pin.crouch = in.key(KEY_CONTROL);
    pin.jump = in.keyPressed(KEY_SPACE);
    pin.interact = in.keyPressed(KEY_E) || in.mousePressed(MOUSE_LEFT);
    player.update(pin, world.physics(), dt);
    if (in.keyPressed(KEY_H)) {
        guide.toggle();
        audio->play2D(SFX_SWITCH, 0.22f, guide.visible() ? 1.25f : 0.85f);
        addToast(guide.visible() ? "Wegweiser an — H schliesst ihn" : "Wegweiser aus", 2.4f);
    }
    flashlight.disturb((director.flashlightDisturb + jumpscare.flashlightKill * 3.2f) * dt * 2.0f);
    flashlight.update(player.eyePosition(), player.forward(), player.right(), dt, globalTime, player.speed());

    hoverInteractable = world.findNearestInteractable(player.eyePosition(), player.forward(), 2.9f, 0.62f);
    if (hoverInteractable < 0) {
        int doorId = world.doorInFront(player.eyePosition(), player.forward(), 2.9f);
        if (doorId >= 0 && doorId < (int)world.doors().size()) {
            const Door& hit = world.doors()[(size_t)doorId];
            bool cabDoor = hit.kind == DOOR_ELEVATOR && hit.roomA == hit.roomB;
            if (!cabDoor) hoverInteractable = hit.interactId;
        }
    }
    if (pin.interact) {
        handleInteraction();
        if (hoverInteractable >= 0) tutSignals.interacted = true;
    }

    tutSignals.crouched = player.isCrouching();
    tutSignals.sprinted = player.isSprinting() && player.isMoving();
    tutorial.update(player, tutSignals, dt);

    updateElevator(dt);
    world.setObserver(player.eyePosition(), player.forward());
    world.update(dt, globalTime, player.position());
    pushCoopState();
    director.update(player, dt, globalTime);
    jumpscare.update(player, dt, globalTime, 1.0f);
    if (jumpscare.forcedLookStrength > 0.01f) {
        player.forceLookAt(jumpscare.forcedLookTarget, jumpscare.forcedLookStrength * dt * 9.0f);
    }
    scareFlash = std::max(scareFlash * std::exp(-dt * 2.2f), jumpscare.bloodFlash);
    scareRing = std::max(scareRing * std::exp(-dt * 1.1f), jumpscare.deafen);
    refreshGuideTarget();
    guide.update(player, dt, globalTime);
    campaign.update(player, dt, globalTime);
    updateFootsteps(dt);
    updateAtmosphere(dt);

    if (player.isGrounded()) {
        safeTimer += dt;
        if (safeTimer > 0.35f) {
            safeTimer = 0.0f;
            lastSafePos = player.position();
        }
    }
    float floorBottom = world.floors().empty() ? -10.0f : world.floors().front().baseY;
    if (player.position().y < floorBottom - 3.5f) {
        player.setPosition(lastSafePos + Vec3(0, 0.15f, 0));
        player.addShake(0.25f, 0.4f);
    }

    std::string campMsg;
    float campDur = 3.0f;
    while (campaign.consumeMessage(campMsg, campDur)) addToast(campMsg, campDur);

    int evt = 0;
    while (campaign.consumeEvent(evt)) applyCampaignEvent(evt);

    std::vector<CutShot> shots;
    if (campaign.consumeCutscene(shots)) {
        cutscene.play(shots);
        setState(GameState::Cutscene);
        return;
    }

    if (campaign.finished() && !cutscene.active()) triggerEnding(director.chooseEnding());

    std::string sub;
    float dur;
    while (director.consumeSubtitle(sub, dur)) {
        subtitleText = sub;
        subtitleTimer = dur;
    }
    while (jumpscare.consumeSubtitle(sub, dur)) {
        subtitleText = sub;
        subtitleTimer = dur;
    }
    if (subtitleTimer > 0.0f) subtitleTimer -= dt;

    autosaveTimer -= dt;
    if (autosaveTimer <= 0.0f) {
        autosaveTimer = 180.0f;
        saveGame("autosave");
    }

    checkEndingConditions(dt);
}

void Game::updatePaused(float dt) {
    Input& in = window->input();
    if (in.keyPressed(KEY_ESCAPE)) { setState(GameState::Playing); return; }

    if (in.keyPressed(KEY_DOWN) || in.keyPressed(KEY_S)) menuIndex = (menuIndex + 1) % 5;
    if (in.keyPressed(KEY_UP) || in.keyPressed(KEY_W)) menuIndex = (menuIndex + 4) % 5;
    if (in.keyPressed(KEY_ENTER) || in.keyPressed(KEY_E)) activatePauseItem(menuIndex);
}

void Game::updateReading(float dt) {
    Input& in = window->input();
    if (state == GameState::Reading) {
        const Document* doc = story.document(readingDoc);
        if (!doc) { setState(GameState::Playing); return; }
        if (in.keyPressed(KEY_RIGHT) || in.keyPressed(KEY_SPACE) ||
            (in.mousePressed(MOUSE_LEFT) && hoverAction == UI_NONE)) {
            if (readingPage + 1 < (int)doc->pages.size()) {
                readingPage++;
                audio->play2D(SFX_PAPER, 0.35f, 1.1f);
            } else {
                setState(GameState::Playing);
            }
        }
        if (in.keyPressed(KEY_LEFT) && readingPage > 0) readingPage--;
        if (in.keyPressed(KEY_ESCAPE) || in.keyPressed(KEY_E)) setState(GameState::Playing);
    } else {
        const AudioLog* log = story.audioLog(listeningLog);
        if (!log || log->lines.empty()) { setState(GameState::Playing); return; }
        listeningTimer += dt;
        if (listeningLine < (int)log->lineDurations.size() && listeningTimer >= log->lineDurations[(size_t)listeningLine]) {
            listeningTimer = 0.0f;
            listeningLine++;
            if (listeningLine >= (int)log->lines.size()) {
                setState(GameState::Playing);
                return;
            }
            audio->play2D(SFX_WHISPER, 0.18f, 1.0f);
        }
        if (in.keyPressed(KEY_ESCAPE) || in.keyPressed(KEY_E)) setState(GameState::Playing);
    }
}

void Game::updateJournal(float dt) {
    Input& in = window->input();
    if (in.keyPressed(KEY_TAB) || in.keyPressed(KEY_ESCAPE)) { setState(GameState::Playing); return; }
    if (in.keyPressed(KEY_RIGHT) || in.keyPressed(KEY_D)) { journalTab = (journalTab + 1) % 3; journalIndex = 0; }
    if (in.keyPressed(KEY_LEFT) || in.keyPressed(KEY_A)) { journalTab = (journalTab + 2) % 3; journalIndex = 0; }
    if (in.keyPressed(KEY_DOWN) || in.keyPressed(KEY_S)) journalIndex++;
    if (in.keyPressed(KEY_UP) || in.keyPressed(KEY_W)) journalIndex = std::max(0, journalIndex - 1);
    float wheel = in.scroll();
    if (wheel > 0.5f) journalIndex = std::max(0, journalIndex - 1);
    else if (wheel < -0.5f) journalIndex++;

    if (in.keyPressed(KEY_ENTER) && journalTab == 1) {
        int found = 0;
        for (int i = 0; i < (int)progress.documentsFound.size(); i++) {
            if (!progress.documentsFound[(size_t)i]) continue;
            if (found == journalIndex) {
                readingDoc = i;
                readingPage = 0;
                setState(GameState::Reading);
                return;
            }
            found++;
        }
    }
}

void Game::updateEnding(float dt) {
    Input& in = window->input();
    endingTimer += dt;
    const Ending& e = StoryDatabase::ending(endingId);
    if (endingTimer > 4.2f && endingLine < 5) {
        endingTimer = 0.0f;
        endingLine++;
    }
    if (endingLine >= 5 && endingTimer > 6.0f) {
        setState(GameState::Credits);
        return;
    }
    if (in.keyPressed(KEY_ESCAPE)) setState(GameState::Credits);
}

void Game::updateCutscene(float dt) {
    if (!cutscene.update(dt) || window->input().keyPressed(KEY_ESCAPE)) {
        cutscene.stop();
        if (campaign.finished()) triggerEnding(director.chooseEnding());
        else setState(GameState::Playing);
    }
}

void Game::update(float dt) {
    stateTime += dt;
    globalTime += dt;
    fadeAmount = moveTowards(fadeAmount, fadeTarget, dt * 1.6f);

    updateCoop(dt);
    if (coopMenu.visible()) return;

    if (state != GameState::Playing) updateMouseUi();

    for (auto it = toasts.begin(); it != toasts.end();) {
        it->timer -= dt;
        if (it->timer <= 0.0f) it = toasts.erase(it);
        else ++it;
    }

    switch (state) {
    case GameState::Splash: updateSplash(dt); break;
    case GameState::MainMenu: updateMenu(dt); break;
    case GameState::Options: updateOptions(dt); break;
    case GameState::Loading:
        if (stateTime > 0.25f) startNewGame(hashCombine((u64)(globalTime * 1000000.0), 0xEC40D1AULL));
        break;
    case GameState::Playing: updatePlaying(dt); break;
    case GameState::Paused: updatePaused(dt); break;
    case GameState::Reading:
    case GameState::Listening: updateReading(dt); break;
    case GameState::Journal: updateJournal(dt); break;
    case GameState::Ending: updateEnding(dt); break;
    case GameState::Cutscene: updateCutscene(dt); break;
    case GameState::Credits:
        if (stateTime > 14.0f || (stateTime > 2.5f && window->input().anyKeyPressed())) {
            endingId = -1;
            currentSeed = 0;
            progress.itemCounts.assign((size_t)ITEM_COUNT, 0);
            if (ownsSystems) {
                setState(GameState::MainMenu);
            } else {
                collectionRequested = true;
                setState(GameState::MainMenu);
            }
        }
        break;
    }
}

void Game::render() {
    bool inWorld = state == GameState::Playing || state == GameState::Paused || state == GameState::Reading ||
                   state == GameState::Listening || state == GameState::Journal;
    bool menuBackdrop = menuWorldReady && (state == GameState::MainMenu || state == GameState::Options ||
                                           state == GameState::Splash);

    if (inWorld || state == GameState::Cutscene) {
        CameraData cam = state == GameState::Cutscene ? cutscene.camera(window->aspect())
                                                      : player.buildCamera(window->aspect());
        if (state != GameState::Cutscene) lastCamera = cam;
        renderer->beginFrame(cam, globalTime, 0.016f);
        if (state != GameState::Cutscene && flashlight.glowIntensity() > 0.01f) renderer->submitLight(flashlight.buildLight());
        world.collectRender(*renderer, cam, 44.0f);
        director.submitPresences(*renderer);
        jumpscare.submit(*renderer);
        coop.submitRemotes(*renderer);
        renderer->render();
    } else if (menuBackdrop) {
        updateMenuCamera(0.016f);
        renderer->beginFrame(menuCam, globalTime, 0.016f);
        world.collectRender(*renderer, menuCam, 40.0f);
        renderer->render();
    } else {
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glViewport(0, 0, window->width(), window->height());
        glClearColor(0.012f, 0.014f, 0.017f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    }

    ui->begin(window->width(), window->height(), globalTime);
    hitRects.clear();

    switch (state) {
    case GameState::Splash: drawSplash(); break;
    case GameState::MainMenu: drawMenu(); break;
    case GameState::Options: drawOptions(); break;
    case GameState::Loading: drawLoading(); break;
    case GameState::Playing: drawHud(); break;
    case GameState::Paused: drawHud(); drawPause(); break;
    case GameState::Reading:
    case GameState::Listening: drawReading(); break;
    case GameState::Journal: drawJournal(); break;
    case GameState::Ending: drawEnding(); break;
    case GameState::Credits: drawEnding(); break;
    case GameState::Cutscene: drawCutscene(); break;
    }

    if (fadeAmount > 0.001f) {
        ui->rect(0, 0, (float)window->width(), (float)window->height(), Vec4(0, 0, 0, fadeAmount));
    }

    ui->end();
}

void Game::drawCutscene() {
    float w = (float)window->width(), h = (float)window->height();
    float bar = h * 0.115f;
    ui->rect(0, 0, w, bar, Vec4(0, 0, 0, 1));
    ui->rect(0, h - bar, w, bar, Vec4(0, 0, 0, 1));

    float f = cutscene.fade();
    if (f < 0.999f) ui->rect(0, 0, w, h, Vec4(0, 0, 0, 1.0f - f));

    std::string line = cutscene.currentLine();
    if (!line.empty()) {
        float size = h * 0.028f;
        auto lines = ui->font().wrap(line, size, w * 0.66f);
        float y = h - bar - (float)lines.size() * size * 1.4f - h * 0.03f;
        for (const auto& l : lines) {
            ui->textShadow(l, w * 0.5f, y, size, Vec4(kInk.x, kInk.y, kInk.z, f), ALIGN_CENTER);
            y += size * 1.4f;
        }
    }

    ui->text("ESC UEBERSPRINGEN", w - h * 0.03f, h - bar * 0.62f, h * 0.016f,
            Vec4(kDim.x, kDim.y, kDim.z, 0.35f * f), ALIGN_RIGHT);
}

void Game::drawWaypoint(const Vec3& worldPos, const Vec4& color, const std::string& label, bool stairs) {
    float w = (float)window->width(), h = (float)window->height();
    float cx = w * 0.5f, cy = h * 0.5f;

    Vec4 clip = lastCamera.viewProj * Vec4(worldPos, 1.0f);
    bool behind = clip.w <= 0.001f;

    float sx = cx, sy = cy;
    bool onScreen = false;

    if (!behind) {
        Vec3 ndc(clip.x / clip.w, clip.y / clip.w, clip.z / clip.w);
        sx = (ndc.x * 0.5f + 0.5f) * w;
        sy = (1.0f - (ndc.y * 0.5f + 0.5f)) * h;
        onScreen = std::fabs(ndc.x) < 0.92f && std::fabs(ndc.y) < 0.88f;
    }

    if (!onScreen) {
        Vec3 flat = worldPos - lastCamera.position;
        flat.y = 0.0f;
        if (lengthSq(flat) < 1e-4f) return;
        flat = normalize(flat);

        Vec3 fwd = lastCamera.forward;
        fwd.y = 0.0f;
        if (lengthSq(fwd) < 1e-4f) return;
        fwd = normalize(fwd);
        Vec3 right = normalize(cross(fwd, Vec3(0, 1, 0)));

        float ang = std::atan2(dot(flat, right), dot(flat, fwd));
        float radius = std::min(w, h) * 0.30f;
        sx = cx + std::sin(ang) * radius;
        sy = cy - std::cos(ang) * radius * 0.62f;

        Vec2 dir(std::sin(ang), -std::cos(ang) * 0.62f);
        dir = normalize(dir);
        Vec2 perp(-dir.y, dir.x);
        float size = h * 0.020f;
        Vec2 tip(sx + dir.x * size, sy + dir.y * size);
        Vec2 a(sx - dir.x * size * 0.4f + perp.x * size * 0.72f, sy - dir.y * size * 0.4f + perp.y * size * 0.72f);
        Vec2 b(sx - dir.x * size * 0.4f - perp.x * size * 0.72f, sy - dir.y * size * 0.4f - perp.y * size * 0.72f);
        ui->triangle(tip, a, b, color);
        return;
    }

    float pulse = 0.72f + 0.28f * std::sin(globalTime * 2.6f);
    float r = h * 0.011f;
    ui->diamond(sx, sy, r * 1.55f, Vec4(0, 0, 0, color.w * 0.45f));
    ui->diamond(sx, sy, r, Vec4(color.x, color.y, color.z, color.w * pulse));

    if (stairs) ui->rect(sx - r * 1.9f, sy + r * 1.7f, r * 3.8f, h * 0.0035f, Vec4(color.x, color.y, color.z, color.w * 0.6f));

    if (!label.empty()) {
        ui->textShadow(label, sx, sy + h * 0.024f, h * 0.017f, Vec4(color.x, color.y, color.z, color.w * 0.85f), ALIGN_CENTER);
    }
}

void Game::pushCoopState() {
    CoopLocalState state;
    state.position = player.position();
    state.velocity = player.velocityVec();
    state.yaw = player.yawAngle();
    state.pitch = player.pitchAngle();
    state.health = 100;
    u32 flags = 0;
    if (player.isGrounded()) flags |= CFLAG_GROUND;
    if (player.isSprinting()) flags |= CFLAG_SPRINT;
    if (player.isCrouching()) flags |= CFLAG_CROUCH;
    if (flashlight.isOn()) flags |= CFLAG_LIGHT;
    if (hoverInteractable >= 0) flags |= CFLAG_INTERACT;
    state.flags = flags;

    if (!player.isGrounded()) state.anim = player.velocityVec().y > 0.6f ? CANIM_JUMP : CANIM_FALL;
    else if (!player.isMoving()) state.anim = player.isCrouching() ? CANIM_CROUCH : CANIM_IDLE;
    else if (player.isCrouching()) state.anim = CANIM_SNEAK;
    else state.anim = player.isSprinting() ? CANIM_RUN : CANIM_WALK;

    coop.pushLocal(state);
}

void Game::applyCoopEvents() {
    std::string kind, key;
    double value = 0.0;
    while (coop.consumeWorldEvent(kind, key, value)) {
        size_t colon = key.find(':');
        int id = colon == std::string::npos ? -1 : std::atoi(key.c_str() + colon + 1);
        if (kind == "door" && id >= 0 && id < (int)world.doors().size()) {
            world.setDoorOpen(id, value != 0.0);
            continue;
        }
        if (kind == "light" && id >= 0 && id < (int)world.lights().size()) {
            world.setLightOn(id, value != 0.0, false);
            continue;
        }
        if (kind == "item" && id >= 0) {
            addToast("Mitspieler hat etwas aufgenommen", 2.6f);
            continue;
        }
        if (kind == "puzzle" || kind == "lever" || kind == "switch") {
            addToast("Mitspieler hat einen Mechanismus benutzt", 2.6f);
            continue;
        }
        if (kind == "save") {
            addToast("Koop-Fortschritt gesichert", 2.6f);
            continue;
        }
    }
}

void Game::updateCoop(float dt) {
    coop.update(dt);

    if (coopMenu.visible()) {
        coopMenu.update(dt);
        if (coopMenu.consumeLaunch()) coopStarting = true;
        coopMenu.consumeExit();
    }

    if (coop.phase() == COOP_LOADING && !coopReported) {
        if (!inGameSession()) {
            startNewGame(coop.worldSeed() ? coop.worldSeed() : 20260730ULL);
        }
        coopReported = true;
        coop.reportLoaded();
    }
    if (coop.phase() != COOP_LOADING) coopReported = false;

    if (coopStarting && coop.playing()) {
        coopStarting = false;
        if (!inGameSession()) startNewGame(coop.worldSeed() ? coop.worldSeed() : 20260730ULL);
        if (coop.spawnReady()) {
            em::Vec3 point = coop.spawnPoint();
            if (lengthSq(point) > 0.01f) player.setPosition(point);
        }
        setState(GameState::Playing);
        coopMenu.close();
        addToast("Koop laeuft — bleibt zusammen", 4.0f);
    }

    if (coop.consumeSpawnSignal() && coop.playing() && coop.spawnReady()) {
        em::Vec3 point = coop.spawnPoint();
        if (lengthSq(point) > 0.01f) player.setPosition(point);
    }

    applyCoopEvents();
    if (coop.inSession()) coop.updateRemotes(dt, globalTime, player.eyePosition());

    if (coop.playing()) {
        coopSaveTimer -= dt;
        if (coopSaveTimer <= 0.0f) {
            coopSaveTimer = 60.0f;
            js::Value blob = js::Value::object();
            blob.set("chapter", campaign.chapterName());
            blob.set("objective", campaign.objective());
            blob.set("floor", campaign.playerFloor());
            coop.sendCheckpoint(blob);
        }
    }
}

void Game::refreshGuideTarget() {
    Vec3 want;
    std::string label;
    bool have = false;

    if (campaign.hasGuide()) {
        want = campaign.guide();
        label = campaign.guideIsStairs() ? "TREPPENHAUS" : "ZIEL";
        have = true;
    } else {
        float best = 1e9f;
        int bestRoom = -1;
        int floorIndex = world.floorAt(player.position().y);
        const std::vector<int> shafts = world.roomsOfType(ROOM_ELEVATOR);
        for (int id : shafts) {
            if (id < 0 || id >= (int)world.rooms().size()) continue;
            const Room& room = world.rooms()[(size_t)id];
            if (room.floor != floorIndex) continue;
            float d = distance(world.roomCenter(id), player.position());
            if (d < best) {
                best = d;
                bestRoom = id;
            }
        }
        if (bestRoom < 0) {
            const std::vector<int> stairs = world.roomsOfType(ROOM_STAIRWELL);
            for (int id : stairs) {
                if (id < 0 || id >= (int)world.rooms().size()) continue;
                float d = distance(world.roomCenter(id), player.position());
                if (d < best) {
                    best = d;
                    bestRoom = id;
                }
            }
            if (bestRoom >= 0) label = "TREPPENHAUS";
        } else {
            label = "AUFZUG";
        }
        if (bestRoom >= 0) {
            want = world.roomCenter(bestRoom);
            have = true;
        }
    }

    if (!have) {
        if (guide.hasTarget()) guide.clearTarget();
        return;
    }
    if (guide.hasTarget() && label == guideLabelCache && distance(want, guideTargetCache) < 0.75f) return;
    guideTargetCache = want;
    guideLabelCache = label;
    guide.setTarget(want, label);
}

void Game::drawGuide() {
    if (!guide.visible() || state != GameState::Playing) return;
    float w = (float)window->width(), h = (float)window->height();

    Vec4 head(0.42f, 0.92f, 1.0f, 0.95f);
    Vec4 trail(0.36f, 0.82f, 0.98f, 0.55f);

    if (!guide.reachable()) {
        ui->rect(w * 0.5f - h * 0.20f, h * 0.032f, h * 0.40f, h * 0.044f, Vec4(0.05f, 0.05f, 0.07f, 0.72f));
        ui->text("WEGWEISER: " + guide.status(), w * 0.5f, h * 0.048f, h * 0.020f,
                 Vec4(0.98f, 0.62f, 0.55f, 0.92f), ALIGN_CENTER, h * 0.004f);
        return;
    }

    const std::vector<GuideNode>& nodes = guide.nodes();
    int start = guide.nextIndex();
    for (int i = (int)nodes.size() - 1; i >= start; i--) {
        const GuideNode& node = nodes[(size_t)i];
        bool isNext = i == start;
        float fade = isNext ? 1.0f : clampf(1.0f - (float)(i - start) * 0.16f, 0.22f, 0.8f);
        Vec4 col = isNext ? head : Vec4(trail.x, trail.y, trail.z, trail.w * fade);
        if (node.stairs) col = Vec4(0.98f, 0.82f, 0.42f, col.w);
        if (node.elevator) col = Vec4(0.62f, 0.98f, 0.72f, col.w);
        std::string tag;
        if (isNext) {
            tag = node.stairs ? "TREPPE" : (node.elevator ? "AUFZUG" : (i == (int)nodes.size() - 1 ? guide.status() : "WEITER"));
        }
        Vec3 lift = node.position + Vec3(0, isNext ? 1.35f : 1.05f, 0);
        drawWaypoint(lift, col, tag, node.stairs);
    }

    float pulse = 0.62f + 0.38f * guide.pulse();
    float barW = h * 0.44f;
    ui->rect(w * 0.5f - barW * 0.5f, h * 0.030f, barW, h * 0.050f, Vec4(0.04f, 0.05f, 0.07f, 0.70f));
    ui->rect(w * 0.5f - barW * 0.5f, h * 0.030f, barW * 0.004f + 2.0f, h * 0.050f,
             Vec4(head.x, head.y, head.z, pulse));
    char buf[96];
    int segments = (int)nodes.size() - start;
    std::snprintf(buf, sizeof(buf), "DIREKTER WEG  %s   %d M   %d ABSCHNITTE",
                  guide.status().c_str(), (int)guide.remainingDistance(), segments < 0 ? 0 : segments);
    ui->text(buf, w * 0.5f, h * 0.049f, h * 0.019f,
             Vec4(head.x, head.y, head.z, 0.92f * pulse), ALIGN_CENTER, h * 0.004f);
    ui->text("H schliesst den Wegweiser", w * 0.5f, h * 0.070f, h * 0.014f,
             Vec4(kDim.x, kDim.y, kDim.z, 0.55f), ALIGN_CENTER, h * 0.003f);
}

void Game::drawObjective() {
    if (campaign.objective().empty()) return;
    float w = (float)window->width(), h = (float)window->height();

    float x = h * 0.045f;
    float y = h * 0.075f;

    ui->text(campaign.chapterName(), x, y, h * 0.018f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.65f), ALIGN_LEFT, h * 0.005f);
    ui->rect(x, y + h * 0.028f, h * 0.10f, 1.5f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.35f));
    ui->textShadow(campaign.objective(), x, y + h * 0.040f, h * 0.023f, Vec4(kInk.x, kInk.y, kInk.z, 0.92f), ALIGN_LEFT);

    float line = y + h * 0.078f;

    if (!campaign.guideHint().empty()) {
        ui->text(campaign.guideHint(), x, line, h * 0.018f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.80f), ALIGN_LEFT);
        line += h * 0.028f;
    }

    if (campaign.carryingBody()) {
        ui->text("TRAGE", x, line, h * 0.017f, Vec4(kDim.x, kDim.y, kDim.z, 0.7f), ALIGN_LEFT, h * 0.004f);
        line += h * 0.026f;
    }

    if (campaign.hasGuide()) {
        float d = distance(campaign.guide(), player.position());
        char buf[48];
        std::snprintf(buf, sizeof(buf), "%d M   ETAGE %d", (int)d, campaign.playerFloor());
        ui->text(buf, x, line, h * 0.017f, Vec4(kDim.x, kDim.y, kDim.z, 0.6f), ALIGN_LEFT, h * 0.004f);
    }

    if (campaign.hasGuide()) {
        Vec4 col = campaign.guideIsStairs() ? Vec4(0.98f, 0.82f, 0.42f, 0.9f) : Vec4(kAccent.x, kAccent.y, kAccent.z, 0.9f);
        std::string label = campaign.guideIsStairs() ? "TREPPENHAUS" : "ZIEL";
        drawWaypoint(campaign.guide(), col, label, campaign.guideIsStairs());
    }
}

void Game::drawSplash() {
    float w = (float)window->width(), h = (float)window->height();
    float t = stateTime;

    if (menuWorldReady) ui->rect(0, 0, w, h, Vec4(0.004f, 0.005f, 0.008f, 0.80f));

    float titleAlpha = smoothstepf(0.3f, 1.4f, t) * (1.0f - smoothstepf(4.6f, 5.4f, t));
    float subAlpha = smoothstepf(1.2f, 2.2f, t) * (1.0f - smoothstepf(4.6f, 5.4f, t));

    float flicker = 1.0f;
    if (t > 1.5f && t < 2.1f) flicker = hash11(std::floor(t * 26.0f)) > 0.4f ? 1.0f : 0.35f;

    float titleSize = h * 0.16f;
    ui->text("ECHO", w * 0.5f, h * 0.40f - titleSize * 0.5f, titleSize, Vec4(kInk.x, kInk.y, kInk.z, titleAlpha * flicker), ALIGN_CENTER, titleSize * 0.16f);

    float subSize = h * 0.036f;
    ui->text("BY FELWORKS", w * 0.5f, h * 0.545f, subSize, Vec4(kAccent.x, kAccent.y, kAccent.z, subAlpha * 0.9f), ALIGN_CENTER, subSize * 0.42f);

    float hintAlpha = smoothstepf(2.8f, 3.6f, t) * (0.45f + 0.25f * std::sin(t * 2.2f));
    ui->text("TASTE ODER KLICK", w * 0.5f, h * 0.86f, h * 0.021f, Vec4(kDim.x, kDim.y, kDim.z, hintAlpha), ALIGN_CENTER, h * 0.006f);
    if (t > 1.0f) pushHit(0, 0, w, h, UI_SKIP, 0);

    float vig = 0.35f + 0.1f * std::sin(t * 0.7f);
    ui->rect(0, 0, w, h * 0.06f, Vec4(0, 0, 0, vig));
    ui->rect(0, h * 0.94f, w, h * 0.06f, Vec4(0, 0, 0, vig));
}

void Game::drawMenu() {
    float w = (float)window->width(), h = (float)window->height();

    if (menuWorldReady) {
        ui->gradientRect(0, 0, w, h * 0.55f, Vec4(0.005f, 0.007f, 0.010f, 0.92f), Vec4(0.005f, 0.007f, 0.010f, 0.58f));
        ui->gradientRect(0, h * 0.55f, w, h * 0.45f, Vec4(0.005f, 0.007f, 0.010f, 0.58f), Vec4(0.005f, 0.007f, 0.010f, 0.88f));
        ui->rect(0, 0, w, h, Vec4(0.004f, 0.006f, 0.009f, 0.28f));
    }

    ui->text("ECHO", w * 0.5f, h * 0.16f, h * 0.11f, kInk, ALIGN_CENTER, h * 0.018f);
    ui->text("BY FELWORKS", w * 0.5f, h * 0.30f, h * 0.024f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.75f), ALIGN_CENTER, h * 0.010f);

    float itemSize = h * 0.036f;
    float y = h * 0.46f;
    for (int i = 0; i < kMenuCount; i++) {
        bool selected = i == menuIndex;
        bool disabled = (i == 1 && !hasSave);
        Vec4 color = disabled ? Vec4(0.32f, 0.33f, 0.34f, 1.0f) : (selected ? kAccent : kDim);
        float size = selected ? itemSize * 1.12f : itemSize;
        float bw = std::max(ui->font().measure(kMenuItems[i], itemSize * 1.12f, itemSize * 0.11f) + h * 0.10f, h * 0.30f);
        float bx = w * 0.5f - bw * 0.5f;
        float by = y - itemSize * 0.30f;
        float bh = itemSize * 1.60f;

        if (selected) {
            float pulse = 0.5f + 0.5f * std::sin(globalTime * 2.4f);
            ui->rect(bx, by, bw, bh, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.045f + pulse * 0.045f));
            ui->rect(bx, by, h * 0.004f, bh, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.55f + pulse * 0.3f));
        }
        ui->text(kMenuItems[i], w * 0.5f, y, size, color, ALIGN_CENTER, size * 0.10f);
        pushHit(bx, by, bw, bh, UI_MENU_ITEM, i);
        y += h * 0.075f;
    }

    ui->text("MAUS ODER PFEILTASTEN   F11 VOLLBILD", w * 0.5f, h * 0.88f, h * 0.018f, Vec4(kDim.x, kDim.y, kDim.z, 0.5f), ALIGN_CENTER, h * 0.004f);
    ui->text(ECHO_VERSION, w - h * 0.03f, h - h * 0.05f, h * 0.016f, Vec4(kDim.x, kDim.y, kDim.z, 0.35f), ALIGN_RIGHT);
}

void Game::drawOptions() {
    float w = (float)window->width(), h = (float)window->height();
    if (menuWorldReady) ui->rect(0, 0, w, h, Vec4(0.005f, 0.007f, 0.010f, 0.86f));
    ui->text("OPTIONEN", w * 0.5f, h * 0.14f, h * 0.055f, kInk, ALIGN_CENTER, h * 0.012f);

    float size = h * 0.028f;
    float y = h * 0.30f;
    char buf[128];

    for (int i = 0; i < kOptionCount; i++) {
        bool selected = i == optionIndex;
        Vec4 color = selected ? kAccent : kDim;

        std::string value;
        switch (i) {
        case 0: std::snprintf(buf, sizeof(buf), "%d%%", (int)(settings.masterVolume * 100)); value = buf; break;
        case 1: std::snprintf(buf, sizeof(buf), "%.2f", settings.sensitivity * 1000.0f); value = buf; break;
        case 2: value = settings.invertY ? "AN" : "AUS"; break;
        case 3: value = settings.subtitles ? "AN" : "AUS"; break;
        case 4: value = settings.tutorial ? "AN" : "AUS"; break;
        case 5: value = kQualityNames[clampi(settings.qualityPreset, 0, 3)]; break;
        case 6: value = settings.fullscreen ? "AN" : "AUS"; break;
        default: value = ""; break;
        }

        float rx = w * 0.24f;
        float ry = y - size * 0.32f;
        float rw = w * 0.52f;
        float rh = size * 1.64f;
        if (selected) ui->rect(rx, ry, rw, rh, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.06f));
        ui->text(kOptionNames[i], w * 0.28f, y, size, color, ALIGN_LEFT, size * 0.08f);
        pushHit(rx, ry, rw, rh, UI_OPTION_ROW, i);

        if (!value.empty()) {
            ui->text(value, w * 0.665f, y, size, color, ALIGN_CENTER);
            bool arrows = (i != 2 && i != 3 && i != 4 && i != 6);
            if (arrows) {
                float aw = h * 0.034f;
                bool hoverDec = isHovered(UI_OPTION_DEC, i);
                bool hoverInc = isHovered(UI_OPTION_INC, i);
                ui->text("<", w * 0.585f, y, size, hoverDec ? kInk : Vec4(color.x, color.y, color.z, 0.55f), ALIGN_CENTER);
                ui->text(">", w * 0.745f, y, size, hoverInc ? kInk : Vec4(color.x, color.y, color.z, 0.55f), ALIGN_CENTER);
                pushHit(w * 0.585f - aw * 0.5f, ry, aw, rh, UI_OPTION_DEC, i);
                pushHit(w * 0.745f - aw * 0.5f, ry, aw, rh, UI_OPTION_INC, i);
            }
        }
        y += h * 0.058f;
    }

    ui->text("MAUS ODER PFEILTASTEN   ESC ZURUECK", w * 0.5f, h * 0.88f, h * 0.018f, Vec4(kDim.x, kDim.y, kDim.z, 0.5f), ALIGN_CENTER);
}

void Game::drawLoading() {
    float w = (float)window->width(), h = (float)window->height();
    ui->text("DAS KRANKENHAUS WIRD GEBAUT", w * 0.5f, h * 0.48f, h * 0.028f, kDim, ALIGN_CENTER, h * 0.008f);
    float p = fractf(globalTime * 0.6f);
    ui->rect(w * 0.35f, h * 0.55f, w * 0.30f, 2.0f, Vec4(kDim.x, kDim.y, kDim.z, 0.25f));
    ui->rect(w * 0.35f + w * 0.30f * p * 0.8f, h * 0.55f, w * 0.06f, 2.0f, kAccent);
}

void Game::drawHud() {
    float w = (float)window->width(), h = (float)window->height();
    float cx = w * 0.5f, cy = h * 0.5f;

    float speed = player.speed();
    float open = clampf(speed / 3.2f, 0.0f, 1.0f);
    float alpha = hoverInteractable >= 0 ? 0.85f : 0.30f;
    ui->crosshair(cx, cy, h * 0.016f, open, Vec4(kInk.x, kInk.y, kInk.z, alpha));

    if (hoverInteractable >= 0 && hoverInteractable < (int)world.interactables().size()) {
        const Interactable& it = world.interactables()[(size_t)hoverInteractable];
        std::string prompt = interactionPrompt(it);
        float size = h * 0.024f;
        float tw = ui->font().measure(prompt, size);
        ui->rect(cx - tw * 0.5f - h * 0.02f, cy + h * 0.035f, tw + h * 0.04f, size * 1.7f, Vec4(0, 0, 0, 0.42f));
        ui->text(prompt, cx, cy + h * 0.045f, size, kInk, ALIGN_CENTER);
        ui->text("[E]", cx, cy + h * 0.078f, h * 0.017f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.8f), ALIGN_CENTER);

        if (it.kind == INTERACT_DOOR && it.targetId >= 0 && it.targetId < (int)world.doors().size()) {
            const Door& d = world.doors()[(size_t)it.targetId];
            int here = world.roomAt(player.position() + Vec3(0, 0.6f, 0));
            int other = d.roomA == here ? d.roomB : d.roomA;
            if (other >= 0 && other < (int)world.rooms().size()) {
                std::string sign = std::string("-> ") + world.rooms()[(size_t)other].label;
                ui->textShadow(sign, cx, cy - h * 0.052f, h * 0.020f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.85f), ALIGN_CENTER);
            }
        }
    }

    if (flashlight.isOn() || flashlight.batteryLevel() < 0.999f) {
        float bx = w - h * 0.10f, by = h - h * 0.10f;
        float radius = h * 0.035f;
        ui->ring(bx, by, radius, h * 0.006f, 1.0f, Vec4(0.1f, 0.11f, 0.12f, 0.55f));
        float level = flashlight.batteryLevel();
        Vec4 col = level > 0.35f ? Vec4(0.68f, 0.86f, 0.80f, 0.85f) : Vec4(0.88f, 0.52f, 0.36f, 0.9f);
        if (level < 0.15f) col.w *= 0.5f + 0.5f * std::sin(globalTime * 8.0f);
        ui->ring(bx, by, radius, h * 0.006f, level, col);
        ui->text(flashlight.isOn() ? "AN" : "AUS", bx, by - h * 0.010f, h * 0.017f, Vec4(kDim.x, kDim.y, kDim.z, 0.75f), ALIGN_CENTER);
        if (flashlight.spareBatteries() > 0) {
            char buf[16];
            std::snprintf(buf, sizeof(buf), "+%d", flashlight.spareBatteries());
            ui->text(buf, bx + radius * 1.35f, by + radius * 0.55f, h * 0.018f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.7f), ALIGN_LEFT);
        }
    }

    float stamina = player.stamina();
    if (stamina < 0.98f) {
        float bw = h * 0.16f;
        float bx = w * 0.5f - bw * 0.5f;
        float by = h - h * 0.055f;
        ui->rect(bx, by, bw, h * 0.005f, Vec4(0.1f, 0.11f, 0.12f, 0.45f));
        ui->rect(bx, by, bw * stamina, h * 0.005f, Vec4(kInk.x, kInk.y, kInk.z, 0.42f));
    }

    float ty = h * 0.10f;
    for (const Toast& t : toasts) {
        float a = clampf(t.timer / 0.7f, 0.0f, 1.0f) * clampf((t.duration - t.timer) / 0.4f, 0.0f, 1.0f);
        ui->textShadow(t.text, w * 0.5f, ty, h * 0.023f, Vec4(kInk.x, kInk.y, kInk.z, a * 0.9f), ALIGN_CENTER);
        ty += h * 0.034f;
    }

    drawObjective();
    drawGuide();
    drawRide();
    drawTutorial();
    drawSubtitles();

    float tension = director.tension();
    if (tension > 0.55f) {
        float a = (tension - 0.55f) * 0.35f * (0.6f + 0.4f * std::sin(globalTime * 5.0f));
        ui->rect(0, 0, w, h, Vec4(0.35f, 0.02f, 0.03f, a * 0.12f));
    }

    if (scareFlash > 0.02f) {
        float a = scareFlash;
        ui->rect(0, 0, w, h, Vec4(0.62f, 0.02f, 0.03f, a * 0.34f));
        float inset = h * (0.02f + 0.10f * (1.0f - a));
        ui->rectOutline(inset, inset, w - inset * 2.0f, h - inset * 2.0f, h * 0.05f * a,
                        Vec4(0.08f, 0.0f, 0.0f, a * 0.55f));
    }
    if (scareRing > 0.03f) {
        float a = scareRing;
        float jitter = std::sin(globalTime * 41.0f) * h * 0.002f * a;
        ui->rect(0, h * 0.5f + jitter - h * 0.0012f, w, h * 0.0024f,
                 Vec4(0.9f, 0.9f, 0.95f, a * 0.06f));
        ui->text("...", w * 0.5f, h * 0.93f, h * 0.03f, Vec4(0.85f, 0.85f, 0.9f, a * 0.30f), ALIGN_CENTER);
    }
}

void Game::drawTutorial() {
    if (tutorial.alpha() < 0.01f) return;
    float w = (float)window->width(), h = (float)window->height();
    float a = tutorial.alpha();

    float keySize = h * 0.026f;
    float textSize = h * 0.022f;
    std::string key = tutorial.keyLabel();
    std::string text = tutorial.hintText();
    if (key.empty() && text.empty()) return;

    float keyW = ui->font().measure(key, keySize, keySize * 0.14f);
    float textW = ui->font().measure(text, textSize);
    float pad = h * 0.026f;
    float gap = h * 0.026f;
    float boxW = keyW + gap + textW + pad * 2.0f;
    float boxH = h * 0.072f;
    float bx = w * 0.5f - boxW * 0.5f;
    float by = h * 0.645f;

    ui->rect(bx, by, boxW, boxH, Vec4(0.015f, 0.020f, 0.026f, 0.90f * a));
    ui->rect(bx, by, h * 0.0035f, boxH, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.75f * a));

    float progressW = boxW * tutorial.holdProgress();
    if (progressW > 1.0f) ui->rect(bx, by + boxH - h * 0.0035f, progressW, h * 0.0035f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.55f * a));

    float ty = by + boxH * 0.5f - keySize * 0.5f;
    ui->text(key, bx + pad, ty, keySize, Vec4(kAccent.x, kAccent.y, kAccent.z, a), ALIGN_LEFT, keySize * 0.14f);
    ui->text(text, bx + pad + keyW + gap, by + boxH * 0.5f - textSize * 0.5f, textSize, Vec4(kInk.x, kInk.y, kInk.z, 0.92f * a), ALIGN_LEFT);
}

void Game::drawSubtitles() {
    if (!settings.subtitles || subtitleTimer <= 0.0f || subtitleText.empty()) return;
    float w = (float)window->width(), h = (float)window->height();
    float size = h * 0.026f;
    auto lines = ui->font().wrap(subtitleText, size, w * 0.62f);
    float y = h * 0.80f - (float)lines.size() * size * 1.35f;
    for (const auto& line : lines) {
        float tw = ui->font().measure(line, size);
        ui->rect(w * 0.5f - tw * 0.5f - h * 0.012f, y - size * 0.22f, tw + h * 0.024f, size * 1.45f, Vec4(0, 0, 0, 0.55f));
        ui->text(line, w * 0.5f, y, size, kInk, ALIGN_CENTER);
        y += size * 1.35f;
    }
}

void Game::drawPause() {
    float w = (float)window->width(), h = (float)window->height();
    ui->rect(0, 0, w, h, Vec4(0.01f, 0.012f, 0.015f, 0.78f));
    ui->text("PAUSE", w * 0.5f, h * 0.24f, h * 0.06f, kInk, ALIGN_CENTER, h * 0.014f);
    ui->text(formatTime(playTime), w * 0.5f, h * 0.33f, h * 0.022f, Vec4(kDim.x, kDim.y, kDim.z, 0.7f), ALIGN_CENTER);

    const char* items[] = { "WEITER", "SPEICHERN", "ONLINE KOOP", "OPTIONEN", "HAUPTMENUE" };
    float size = h * 0.032f;
    float y = h * 0.42f;
    for (int i = 0; i < 5; i++) {
        bool selected = i == menuIndex;
        float bw = std::max(ui->font().measure(items[i], size * 1.1f, size * 0.1f) + h * 0.09f, h * 0.26f);
        float bx = w * 0.5f - bw * 0.5f;
        float by = y - size * 0.28f;
        float bh = size * 1.56f;
        if (selected) {
            float pulse = 0.5f + 0.5f * std::sin(globalTime * 2.4f);
            ui->rect(bx, by, bw, bh, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.05f + pulse * 0.04f));
            ui->rect(bx, by, h * 0.004f, bh, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.55f));
        }
        ui->text(items[i], w * 0.5f, y, selected ? size * 1.1f : size, selected ? kAccent : kDim, ALIGN_CENTER, size * 0.1f);
        pushHit(bx, by, bw, bh, UI_PAUSE_ITEM, i);
        y += h * 0.062f;
    }

    const BehaviorProfile& p = director.tracker().profile();
    char buf[160];
    std::snprintf(buf, sizeof(buf), "RAEUME %d   DOKUMENTE %d   AUFNAHMEN %d", p.roomsSeen, p.documentsRead, p.logsHeard);
    ui->text(buf, w * 0.5f, h * 0.82f, h * 0.018f, Vec4(kDim.x, kDim.y, kDim.z, 0.5f), ALIGN_CENTER);
}

void Game::drawReading() {
    float w = (float)window->width(), h = (float)window->height();
    ui->rect(0, 0, w, h, Vec4(0.01f, 0.012f, 0.014f, 0.86f));

    if (state == GameState::Reading) {
        const Document* doc = story.document(readingDoc);
        if (!doc) return;

        float px = w * 0.5f - w * 0.20f;
        float py = h * 0.14f;
        float pw = w * 0.40f;
        float ph = h * 0.72f;
        ui->rect(px, py, pw, ph, Vec4(0.72f, 0.70f, 0.64f, 0.95f));
        ui->rect(px, py, pw, h * 0.006f, Vec4(0.55f, 0.53f, 0.48f, 1.0f));

        Vec4 inkDark(0.10f, 0.09f, 0.08f, 1.0f);
        ui->text(doc->title, px + pw * 0.5f, py + h * 0.05f, h * 0.032f, inkDark, ALIGN_CENTER, h * 0.004f);
        ui->text(doc->author + "   " + doc->date, px + pw * 0.5f, py + h * 0.095f, h * 0.018f, Vec4(0.32f, 0.30f, 0.27f, 1.0f), ALIGN_CENTER);

        if (readingPage < (int)doc->pages.size()) {
            auto lines = ui->font().wrap(doc->pages[(size_t)readingPage], h * 0.023f, pw * 0.84f);
            float ly = py + h * 0.17f;
            for (const auto& line : lines) {
                ui->text(line, px + pw * 0.08f, ly, h * 0.023f, inkDark, ALIGN_LEFT);
                ly += h * 0.036f;
            }
        }

        char buf[32];
        std::snprintf(buf, sizeof(buf), "%d / %d", readingPage + 1, (int)doc->pages.size());
        ui->text(buf, px + pw * 0.5f, py + ph - h * 0.06f, h * 0.018f, Vec4(0.35f, 0.33f, 0.30f, 1.0f), ALIGN_CENTER);

        float bs = h * 0.026f;
        float by = py + ph - h * 0.062f;
        bool canPrev = readingPage > 0;
        Vec4 prevCol = canPrev ? (isHovered(UI_DOC_PREV, 0) ? Vec4(0.05f, 0.05f, 0.04f, 1.0f) : Vec4(0.30f, 0.28f, 0.25f, 1.0f)) : Vec4(0.55f, 0.53f, 0.50f, 1.0f);
        Vec4 nextCol = isHovered(UI_DOC_NEXT, 0) ? Vec4(0.05f, 0.05f, 0.04f, 1.0f) : Vec4(0.30f, 0.28f, 0.25f, 1.0f);
        ui->text("<", px + pw * 0.14f, by, bs, prevCol, ALIGN_CENTER);
        ui->text(">", px + pw * 0.86f, by, bs, nextCol, ALIGN_CENTER);
        pushHit(px + pw * 0.05f, by - bs * 0.4f, pw * 0.18f, bs * 1.8f, UI_DOC_PREV, 0);
        pushHit(px + pw * 0.77f, by - bs * 0.4f, pw * 0.18f, bs * 1.8f, UI_DOC_NEXT, 0);

        float cw = ui->font().measure("SCHLIESSEN", h * 0.019f) + h * 0.05f;
        float cx = w * 0.5f - cw * 0.5f;
        float cy = h * 0.905f;
        bool hoverClose = isHovered(UI_DOC_CLOSE, 0);
        ui->rect(cx, cy, cw, h * 0.038f, Vec4(kInk.x, kInk.y, kInk.z, hoverClose ? 0.14f : 0.06f));
        ui->text("SCHLIESSEN", w * 0.5f, cy + h * 0.009f, h * 0.019f, hoverClose ? kInk : kDim, ALIGN_CENTER);
        pushHit(cx, cy, cw, h * 0.038f, UI_DOC_CLOSE, 0);
    } else {
        const AudioLog* log = story.audioLog(listeningLog);
        if (!log) return;

        ui->text(log->title, w * 0.5f, h * 0.30f, h * 0.030f, kInk, ALIGN_CENTER, h * 0.006f);
        ui->text(log->speaker, w * 0.5f, h * 0.355f, h * 0.020f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.7f), ALIGN_CENTER);

        for (int i = 0; i <= listeningLine && i < (int)log->lines.size(); i++) {
            float age = (float)(listeningLine - i);
            float a = clampf(1.0f - age * 0.28f, 0.12f, 1.0f);
            ui->text(log->lines[(size_t)i], w * 0.5f, h * 0.45f + i * h * 0.042f, h * 0.024f,
                    Vec4(kInk.x, kInk.y, kInk.z, a), ALIGN_CENTER);
        }

        float barW = w * 0.3f;
        float progressValue = (float)listeningLine / std::max(1.0f, (float)log->lines.size());
        ui->rect(w * 0.5f - barW * 0.5f, h * 0.82f, barW, 2.0f, Vec4(kDim.x, kDim.y, kDim.z, 0.3f));
        ui->rect(w * 0.5f - barW * 0.5f, h * 0.82f, barW * progressValue, 2.0f, kAccent);
        float cw2 = ui->font().measure("BEENDEN", h * 0.019f) + h * 0.05f;
        float cx2 = w * 0.5f - cw2 * 0.5f;
        bool hoverClose2 = isHovered(UI_DOC_CLOSE, 0);
        ui->rect(cx2, h * 0.875f, cw2, h * 0.038f, Vec4(kInk.x, kInk.y, kInk.z, hoverClose2 ? 0.14f : 0.06f));
        ui->text("BEENDEN", w * 0.5f, h * 0.884f, h * 0.019f, hoverClose2 ? kInk : kDim, ALIGN_CENTER);
        pushHit(cx2, h * 0.875f, cw2, h * 0.038f, UI_DOC_CLOSE, 0);
    }
}

void Game::drawJournal() {
    float w = (float)window->width(), h = (float)window->height();
    ui->rect(0, 0, w, h, Vec4(0.01f, 0.012f, 0.014f, 0.88f));

    const char* tabs[] = { "INVENTAR", "DOKUMENTE", "AUFNAHMEN" };
    float tx = w * 0.25f;
    for (int i = 0; i < 3; i++) {
        bool sel = i == journalTab;
        bool hover = isHovered(UI_JOURNAL_TAB, i);
        ui->text(tabs[i], tx, h * 0.12f, h * 0.026f, sel ? kAccent : (hover ? kInk : kDim), ALIGN_CENTER, h * 0.006f);
        if (sel) ui->rect(tx - w * 0.06f, h * 0.155f, w * 0.12f, 2.0f, kAccent);
        pushHit(tx - w * 0.07f, h * 0.10f, w * 0.14f, h * 0.055f, UI_JOURNAL_TAB, i);
        tx += w * 0.25f;
    }

    float y = h * 0.24f;
    float size = h * 0.024f;

    if (journalTab == 0) {
        int shown = 0;
        for (int i = 0; i < (int)progress.itemCounts.size(); i++) {
            if (progress.itemCounts[(size_t)i] == 0) continue;
            const ItemDef& def = itemDef(i);
            bool sel = shown == journalIndex;
            ui->text(def.name, w * 0.24f, y, size, sel ? kAccent : kInk, ALIGN_LEFT);
            if (progress.itemCounts[(size_t)i] > 1) {
                char buf[16];
                std::snprintf(buf, sizeof(buf), "x%d", (int)progress.itemCounts[(size_t)i]);
                ui->text(buf, w * 0.44f, y, size, kDim, ALIGN_LEFT);
            }
            if (sel) ui->text(def.description, w * 0.24f, y + h * 0.030f, h * 0.018f, Vec4(kDim.x, kDim.y, kDim.z, 0.75f), ALIGN_LEFT);
            pushHit(w * 0.22f, y - size * 0.25f, w * 0.56f, size * 1.5f, UI_JOURNAL_ROW, shown);
            y += sel ? h * 0.068f : h * 0.038f;
            shown++;
        }
        if (shown == 0) ui->text("LEER", w * 0.5f, h * 0.45f, size, kDim, ALIGN_CENTER);
        journalIndex = clampi(journalIndex, 0, std::max(0, shown - 1));
    } else if (journalTab == 1) {
        int shown = 0;
        for (int i = 0; i < (int)progress.documentsFound.size(); i++) {
            if (!progress.documentsFound[(size_t)i]) continue;
            const Document* doc = story.document(i);
            if (!doc) continue;
            bool sel = shown == journalIndex;
            ui->text(doc->title, w * 0.24f, y, size, sel ? kAccent : kInk, ALIGN_LEFT);
            ui->text(doc->date, w * 0.70f, y, h * 0.018f, kDim, ALIGN_RIGHT);
            pushHit(w * 0.22f, y - size * 0.25f, w * 0.56f, size * 1.5f, UI_JOURNAL_ROW, shown);
            y += h * 0.040f;
            shown++;
        }
        if (shown == 0) ui->text("NOCH NICHTS GEFUNDEN", w * 0.5f, h * 0.45f, size, kDim, ALIGN_CENTER);
        else ui->text("ENTER ZUM LESEN", w * 0.5f, h * 0.86f, h * 0.017f, Vec4(kDim.x, kDim.y, kDim.z, 0.5f), ALIGN_CENTER);
        journalIndex = clampi(journalIndex, 0, std::max(0, shown - 1));
    } else {
        int shown = 0;
        for (int i = 0; i < (int)progress.logsFound.size(); i++) {
            if (!progress.logsFound[(size_t)i]) continue;
            const AudioLog* log = story.audioLog(i);
            if (!log) continue;
            bool sel = shown == journalIndex;
            ui->text(log->title, w * 0.24f, y, size, sel ? kAccent : kInk, ALIGN_LEFT);
            ui->text(log->speaker, w * 0.70f, y, h * 0.018f, kDim, ALIGN_RIGHT);
            pushHit(w * 0.22f, y - size * 0.25f, w * 0.56f, size * 1.5f, UI_JOURNAL_ROW, shown);
            y += h * 0.040f;
            shown++;
        }
        if (shown == 0) ui->text("NOCH NICHTS GEFUNDEN", w * 0.5f, h * 0.45f, size, kDim, ALIGN_CENTER);
        journalIndex = clampi(journalIndex, 0, std::max(0, shown - 1));
    }

    ui->text("TAB SCHLIESSEN", w * 0.5f, h * 0.91f, h * 0.017f, Vec4(kDim.x, kDim.y, kDim.z, 0.5f), ALIGN_CENTER);
}

void Game::drawEnding() {
    float w = (float)window->width(), h = (float)window->height();
    ui->rect(0, 0, w, h, Vec4(0.006f, 0.007f, 0.009f, 1.0f));

    const Ending& e = StoryDatabase::ending(endingId);

    if (state == GameState::Credits) {
        ui->text("ECHO", w * 0.5f, h * 0.32f, h * 0.09f, kInk, ALIGN_CENTER, h * 0.015f);
        ui->text("BY FELWORKS", w * 0.5f, h * 0.44f, h * 0.026f, Vec4(kAccent.x, kAccent.y, kAccent.z, 0.8f), ALIGN_CENTER, h * 0.010f);
        ui->text(e.title, w * 0.5f, h * 0.56f, h * 0.030f, kDim, ALIGN_CENTER, h * 0.008f);
        char buf[96];
        std::snprintf(buf, sizeof(buf), "SPIELZEIT %s", formatTime(playTime).c_str());
        ui->text(buf, w * 0.5f, h * 0.64f, h * 0.020f, Vec4(kDim.x, kDim.y, kDim.z, 0.6f), ALIGN_CENTER);
        ui->text(ownsSystems ? "TASTE ODER KLICK" : "TASTE ODER KLICK   ZURUECK ZUR COLLECTION",
                 w * 0.5f, h * 0.84f, h * 0.018f,
                 Vec4(kDim.x, kDim.y, kDim.z, 0.4f + 0.2f * std::sin(globalTime * 2.0f)), ALIGN_CENTER);
        if (stateTime > 3.0f) pushHit(0, 0, w, h, UI_SKIP, 0);
        return;
    }

    ui->text(e.title, w * 0.5f, h * 0.20f, h * 0.048f, kInk, ALIGN_CENTER, h * 0.014f);

    for (int i = 0; i <= endingLine && i < 6; i++) {
        float a = i == endingLine ? clampf(endingTimer / 1.2f, 0.0f, 1.0f) : clampf(1.0f - (endingLine - i) * 0.16f, 0.25f, 1.0f);
        auto lines = ui->font().wrap(e.text[i], h * 0.024f, w * 0.60f);
        float ly = h * 0.36f + i * h * 0.072f;
        for (const auto& line : lines) {
            ui->text(line, w * 0.5f, ly, h * 0.024f, Vec4(kInk.x, kInk.y, kInk.z, a * 0.92f), ALIGN_CENTER);
            ly += h * 0.032f;
        }
    }
}

void Game::run() {
    FrameTimer timer;
    int frameCount = 0;

    if (testState >= 0) {
        if (testState == 1) setState(GameState::MainMenu);
        else if (testState == 6) { loadGame("quicksave"); fadeAmount = 0.0f; fadeTarget = 0.0f; }
        else if (testState >= 2) { startNewGame(20260727ULL); fadeAmount = 0.0f; fadeTarget = 0.0f; }
        if (testState == 7) {
            int lift = -1;
            for (const auto& rm : world.rooms()) {
                if (rm.type == ROOM_ELEVATOR && rm.elevatorShaft == 0 && rm.floor == 1) { lift = rm.id; break; }
            }
            if (lift >= 0) {
                const Room& rm = world.rooms()[(size_t)lift];
                player.setPosition(Vec3(rm.rect.center().x, rm.floorY + 0.1f, rm.rect.z + 0.9f));
                player.setOrientation(PI, 0.0f);
                world.setRoomLights(lift, true, true);
                LOG_INFO("lifttest room %d floor %d rect %.1f,%.1f %.1fx%.1f cabs=%d", lift, rm.floor,
                         rm.rect.x, rm.rect.z, rm.rect.w, rm.rect.d, (int)world.cabs().size());
            }
        }
        if (testState >= 3 && testState != 6 && testState != 7) {
            int doorId = -1;
            int room = world.roomAt(player.position() + Vec3(0, 0.6f, 0));
            if (room >= 0 && !world.rooms()[(size_t)room].doors.empty()) doorId = world.rooms()[(size_t)room].doors[testState == 4 ? std::min(1, (int)world.rooms()[(size_t)room].doors.size() - 1) : 0];
            if (doorId >= 0) {
                const Door& d = world.doors()[(size_t)doorId];
                Vec3 toRoom = normalize(world.roomCenter(room) - d.center);
                Vec3 stand = d.center + toRoom * 3.0f;
                stand.y = world.rooms()[(size_t)room].floorY + 0.05f;
                player.setPosition(stand);
                player.setOrientation(std::atan2(-toRoom.x, toRoom.z), -0.05f);
                world.doors()[(size_t)doorId].targetOpen = testState == 4 ? 1.0f : 0.0f;
                world.doors()[(size_t)doorId].openAmount = testState == 4 ? 1.0f : 0.0f;
                world.setRoomLights(room, true);
            }
        }
    }

    while (!window->shouldClose() && !quitRequested) {
        window->pollEvents();
        timer.tick();

        Input& in = window->input();
        if (in.keyPressed(KEY_F11)) {
            if (in.key(KEY_SHIFT)) {
                window->moveToNextMonitor();
            } else {
                settings.fullscreen = !settings.fullscreen;
                window->setFullscreen(settings.fullscreen);
            }
        }
        if (window->resized()) renderer->resize(window->width(), window->height());
        if (window->minimized()) continue;

        float dt = std::min(timer.dt, 0.05f);
        update(dt);
        if (window->resized()) renderer->resize(window->width(), window->height());
        render();

        frameCount++;
        if (!shotPath.empty() && testFrames > 0 && frameCount == testFrames) {
            int sw = window->width(), sh = window->height();
            std::vector<unsigned char> pixels((size_t)sw * sh * 3);
            glPixelStorei(GL_PACK_ALIGNMENT, 1);
            glReadBuffer(GL_BACK);
            glReadPixels(0, 0, sw, sh, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
            writePNG(shotPath, sw, sh, 3, pixels.data(), true);
            LOG_INFO("Screenshot: %s", shotPath.c_str());
        }

        window->swapBuffers();
        if (testFrames > 0 && frameCount >= testFrames) break;
    }
}

}
