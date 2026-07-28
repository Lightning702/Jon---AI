#pragma once

#include "../platform/Window.h"
#include "../render/Renderer.h"
#include "../ui/UIRenderer.h"
#include "../audio/AudioEngine.h"
#include "../game/Game.h"
#include "../aetheria/AetheriaGame.h"
#include "../game/Campaign.h"

namespace felworks {

using namespace echo;

enum class Shell {
    Boot,
    Cards,
    LaunchEcho,
    LaunchAetheria,
    InEcho,
    InAetheria
};

struct CardVisual {
    std::string title;
    std::string author;
    std::string genre;
    std::string tagline;
    em::Vec3 accent;
    em::Vec3 deep;
    float hover = 0.0f;
};

class Collection {
public:
    bool init(Window* window, int forcedPreset, bool windowed);
    void shutdown();
    void run();

private:
    void update(float dt);
    void render(float dt);
    void drawCards();
    void drawBoot();
    void updateCardInput(float dt);
    void enterEcho();
    void enterAetheria();
    void returnToShell();
    void renderPreviewScene(int index, float dt);
    void captureCardShots();
    void buildPreviewScene();
    void updatePreviewCamera(float dt);
    void drawParticles(float dt);

    Window* window = nullptr;
    Renderer renderer;
    UIRenderer ui;
    AudioEngine audio;

    Scope<Game> echoGame;
    Scope<aeth::AetheriaGame> aetheriaGame;
    bool echoReady = false;
    bool aetheriaReady = false;

    Shell state = Shell::Boot;
    float stateTime = 0.0f;
    float globalTime = 0.0f;
    float fade = 1.0f;
    float fadeTarget = 0.0f;

    CardVisual cards[2];
    int selected = 0;
    float blendToAetheria = 0.0f;

    World echoPreview;
    PropLibrary props;
    aeth::AetheriaWorld aetherPreview;
    bool previewBuilt = false;

    CameraData previewCam;
    em::Vec3 previewBase, previewDir;
    float previewPhase = 0.0f;

    struct Particle {
        em::Vec2 pos;
        em::Vec2 vel;
        float size = 1.0f;
        float life = 1.0f;
        float spin = 0.0f;
    };
    std::vector<Particle> particles;
    em::Rng rng;

    SoundHandle music;
    float displayHintTimer = 0.0f;
    GLuint cardShot[2] = { 0, 0 };
    bool shotsCaptured = false;
    int forcedPresetValue = -1;
    bool quitRequested = false;
    int testFrames = 0;
    int testCard = -1;
    int testPlay = -1;
    bool testMapOpen = false;
    bool testAutoRun = false;
    int seedTest = 0;
    std::string shotPath;

public:
    void setTestMode(int frames, const std::string& shot, int card) {
        testFrames = frames;
        shotPath = shot;
        testCard = card;
    }
    void setTestPlay(int card) { testPlay = card; }
    void setTestMapOpen(bool open) { testMapOpen = open; }
    void setTestAutoRun(bool run) { testAutoRun = run; }
    void setSeedTest(int count) { seedTest = count; }
};

}
