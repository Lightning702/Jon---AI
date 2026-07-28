#pragma once

#include "AetheriaWorld.h"
#include "Quests.h"
#include "WorldMap.h"
#include "../platform/Window.h"
#include "../ui/UIRenderer.h"
#include "../audio/AudioEngine.h"
#include "../game/Player.h"
#include "../game/Flashlight.h"

namespace aeth {

struct Traveller {
    int level = 1;
    int xp = 0;
    int xpNext = 120;
    float health = 100.0f;
    float maxHealth = 100.0f;
    float stamina = 100.0f;
    float maxStamina = 100.0f;
    float mana = 60.0f;
    float maxMana = 60.0f;
    int gold = 0;
    int discovered = 0;
    int kills = 0;
    int gathered = 0;

    void grantXp(int amount);
};

struct Toast {
    std::string text;
    float timer = 0.0f;
};

enum AethScreen {
    AETH_MENU = 0,
    AETH_PLAYING,
    AETH_PAUSED
};

struct MenuHit {
    float x = 0, y = 0, w = 0, h = 0;
    int index = 0;
};

class AetheriaGame {
public:
    bool init(echo::Window* window, echo::Renderer* renderer, echo::UIRenderer* ui, echo::AudioEngine* audio);
    void shutdown();
    void open(u64 seed);
    void beginRun();
    bool active() const { return running; }
    void stop() { running = false; }

    void update(float dt, float time);
    void render(float time);
    void drawHud();

    const AetheriaWorld& world() const { return land; }
    AetheriaWorld& world() { return land; }
    echo::CameraData camera(float aspect) const;
    bool wantsExit() const { return exitRequested; }
    void clearExit() { exitRequested = false; }
    void setMapOpen(bool open) { mapOpen = open; }

private:
    void updateMovement(float dt);
    void updateDiscovery(float dt);
    void updateInteraction(float dt);
    void updateCombat(float dt);
    void updateMenu(float dt);
    void updateMenuCamera(float dt);
    void activateMenuItem(int index);
    void rebuildMarkers();
    void addToast(const std::string& text);
    void say(const std::string& who, const std::string& text);
    void respawnPlayer();
    void buildWeapon();
    void pushHit(float x, float y, float w, float h, int index);

    void drawBars(float w, float h);
    void drawTracker(float w, float h);
    void drawPrompt(float w, float h);
    void drawDialogue(float w, float h);
    void drawToasts(float w, float h);
    void drawMenu(float w, float h);
    void drawPause(float w, float h);
    void drawObjectives(float w, float h);
    int menuItemCount() const;
    const char* menuItemLabel(int index) const;
    void refreshObjective();
    bool projectToScreen(const em::Vec3& world, float w, float h, em::Vec2& out, bool& behind) const;

    echo::Window* window = nullptr;
    echo::Renderer* renderer = nullptr;
    echo::UIRenderer* ui = nullptr;
    echo::AudioEngine* audio = nullptr;

    AetheriaWorld land;
    QuestLog quests;
    WorldMap map;
    std::vector<MapMarker> markers;
    Traveller hero;
    echo::Mesh weapon;
    echo::Flashlight lamp;
    echo::CameraData lastCam;

    em::Vec3 objectivePos;
    std::string objectiveLabel;
    std::string objectiveHint;
    bool objectiveValid = false;
    float objectiveTimer = 0.0f;

    em::Vec3 position;
    em::Vec3 velocity;
    float yaw = 0.0f, pitch = -0.05f;
    float eyeHeight = 1.68f;
    float bobPhase = 0.0f;
    float bobAmount = 0.0f;
    bool grounded = true;
    bool sprinting = false;
    bool running = false;
    bool exitRequested = false;
    bool mapOpen = false;
    bool worldReady = false;
    bool runStarted = false;

    int screen = AETH_MENU;
    int menuIndex = 0;
    float menuTime = 0.0f;
    float menuOrbit = 0.0f;
    em::Vec3 menuFocus;
    echo::CameraData menuCam;
    std::vector<MenuHit> hits;
    em::Vec2 lastMouse;

    int satchel[FLORA_COUNT] = { 0 };
    int hoverVillage = -1;
    int hoverFlora = -1;
    std::string prompt;
    std::string speaker;
    std::string speech;
    float speechTimer = 0.0f;
    float swing = 0.0f;
    float swingCooldown = 0.0f;
    float damageFlash = 0.0f;
    float markerTimer = 0.0f;
    std::vector<Toast> toasts;

    std::string regionLabel;
    std::string regionToast;
    float regionToastTimer = 0.0f;
    float footstepAccum = 0.0f;
    float sensitivity = 0.0022f;
    float viewDistance = 185.0f;
};

}
