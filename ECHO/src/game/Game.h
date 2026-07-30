#pragma once

#include "../platform/Window.h"
#include "../render/Renderer.h"
#include "../world/World.h"
#include "../world/Human.h"
#include "../world/Horror.h"
#include "../audio/AudioEngine.h"
#include "../ai/Director.h"
#include "../ai/Jumpscare.h"
#include "../ui/UIRenderer.h"
#include "../save/SaveSystem.h"
#include "Player.h"
#include "Guide.h"
#include "../net/CoopSession.h"
#include "../net/CoopUI.h"
#include "Flashlight.h"
#include "Story.h"
#include "Campaign.h"
#include "Tutorial.h"

namespace echo {

enum class GameState {
    Splash,
    MainMenu,
    Options,
    Loading,
    Playing,
    Paused,
    Reading,
    Listening,
    Journal,
    Ending,
    Credits,
    Cutscene
};

struct Settings {
    float masterVolume = 0.85f;
    float sensitivity = 0.0022f;
    bool invertY = false;
    bool subtitles = true;
    bool tutorial = true;
    bool vsync = true;
    bool fullscreen = true;
    int qualityPreset = -1;
    float fov = 69.0f;
    float brightness = 1.0f;

    void load();
    void save() const;
};

struct Toast {
    std::string text;
    float timer = 0.0f;
    float duration = 3.0f;
};

enum UiAction {
    UI_NONE = 0,
    UI_MENU_ITEM,
    UI_OPTION_ROW,
    UI_OPTION_DEC,
    UI_OPTION_INC,
    UI_PAUSE_ITEM,
    UI_JOURNAL_TAB,
    UI_JOURNAL_ROW,
    UI_DOC_NEXT,
    UI_DOC_PREV,
    UI_DOC_CLOSE,
    UI_SKIP
};

struct HitRect {
    float x = 0, y = 0, w = 0, h = 0;
    int action = UI_NONE;
    int value = 0;
};

class Game {
public:
    bool init(Window* window, int forcedPreset, bool startWindowed);
    bool initShared(Window* window, Renderer* sharedRenderer, UIRenderer* sharedUi, AudioEngine* sharedAudio, int forcedPreset);
    void enterFromCollection();
    void tick(float dt);
    void renderFrame();
    void drawOverlay();
    bool wantsCollection() const { return collectionRequested; }
    void clearCollectionRequest() { collectionRequested = false; }
    void setTestMode(int frames, const std::string& shot, int forceState) { testFrames = frames; shotPath = shot; testState = forceState; }
    void beginTestRun(u64 seed);
    void shutdown();
    void run();

private:
    void update(float dt);
    void render();

    void updateSplash(float dt);
    void updateMenu(float dt);
    void updateOptions(float dt);
    void updatePlaying(float dt);
    void updatePaused(float dt);
    void updateReading(float dt);
    void updateJournal(float dt);
    void updateEnding(float dt);
    void updateCutscene(float dt);
    void setupMenuCamera();
    void updateMenuCamera(float dt);
    void applyCampaignEvent(int id);
    void drawCutscene();
    void drawObjective();
    void drawGuide();
    void updateCoop(float dt);
    void pushCoopState();
    void applyCoopEvents();
    void refreshGuideTarget();
    void drawTutorial();
    void drawWaypoint(const em::Vec3& worldPos, const em::Vec4& color, const std::string& label, bool stairs);
    void updateElevator(float dt);
    void beginRide(int cabId, int requestedFloor);
    void drawRide();

    void drawHud();
    void drawMenu();
    void drawOptions();
    void drawSplash();
    void drawPause();
    void drawReading();
    void drawJournal();
    void drawEnding();
    void drawSubtitles();
    void drawLoading();

    void startNewGame(u64 seed);
    void loadGame(const std::string& slot);
    void saveGame(const std::string& slot);
    void placeStoryContent();
    void handleInteraction();
    void updateFootsteps(float dt);
    void updateAtmosphere(float dt);
    void addToast(const std::string& text, float duration = 3.2f);
    void setState(GameState s);
    void returnToMainMenu();
    bool inGameSession() const;
    void pushHit(float x, float y, float w, float h, int action, int value);
    void updateMouseUi();
    void activateUi(int action, int value);
    void activateMenuItem(int index);
    void activatePauseItem(int index);
    void adjustOption(int index, int dir);
    bool isHovered(int action, int value) const;
    void triggerEnding(int endingId);
    void checkEndingConditions(float dt);
    int findExitInteractable() const;
    std::string interactionPrompt(const Interactable& it) const;
    bool hasItem(int itemId) const;
    void addItem(int itemId, int count = 1);

    Window* window = nullptr;
    Renderer* renderer = nullptr;
    UIRenderer* ui = nullptr;
    AudioEngine* audio = nullptr;
    bool ownsSystems = false;
    bool collectionRequested = false;
    Renderer ownRenderer;
    UIRenderer ownUi;
    AudioEngine ownAudio;
    World world;
    PropLibrary propLib;
    HumanRig humanRig;
    HorrorRig horrorRig;
    Director director;
    JumpscareDirector jumpscare;
    RouteGuide guide;
    CoopSession coop;
    CoopMenu coopMenu;
    float coopSaveTimer = 0.0f;
    bool coopStarting = false;
    bool coopReported = false;
    StoryDatabase story;
    Campaign campaign;
    Tutorial tutorial;
    CutscenePlayer cutscene;
    Player player;
    Flashlight flashlight;
    Settings settings;
    GameProgress progress;

    GameState state = GameState::Splash;
    GameState previousState = GameState::Splash;
    float stateTime = 0.0f;
    float fadeAmount = 1.0f;
    float fadeTarget = 0.0f;
    float globalTime = 0.0f;
    float playTime = 0.0f;

    int menuIndex = 0;
    int optionIndex = 0;
    int journalTab = 0;
    int journalIndex = 0;
    int readingDoc = -1;
    int readingPage = 0;
    int listeningLog = -1;
    int listeningLine = 0;
    float listeningTimer = 0.0f;
    int endingId = -1;
    int endingLine = 0;
    float endingTimer = 0.0f;

    int hoverInteractable = -1;
    float interactHold = 0.0f;
    float footstepTimer = 0.0f;
    float autosaveTimer = 0.0f;
    float exitProximity = 0.0f;

    std::string subtitleText;
    float subtitleTimer = 0.0f;
    std::vector<Toast> toasts;

    SoundHandle musicHandle;
    SoundHandle ambienceLoop;
    SoundHandle ventLoop;
    bool cursorLocked = false;
    bool quitRequested = false;
    bool hasSave = false;
    u64 currentSeed = 0;
    int testFrames = 0;
    int testState = -1;
    std::string shotPath;

    std::vector<HitRect> hitRects;
    int hoverAction = UI_NONE;
    int hoverValue = -1;
    em::Vec2 mousePos;

    em::Vec3 guideTargetCache;
    std::string guideLabelCache;
    float scareFlash = 0.0f;
    float scareRing = 0.0f;

    CameraData lastCamera;
    CameraData menuCam;
    float menuCamPhase = 0.0f;
    em::Vec3 menuCamBase;
    em::Vec3 menuCamDir;
    bool menuWorldReady = false;
    em::Vec3 lastSafePos;
    float safeTimer = 0.0f;

    int rideCab = -1;
    int panelFloor = -1;
    int rideTargetFloor = -1;
    float rideTimer = 0.0f;
    float rideCooldown = 0.0f;
    float rideAutoTimer = 0.0f;
    bool riding = false;
    std::string rideText;
    SoundHandle rideHum;
};

}
