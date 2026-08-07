#pragma once

#include "../engine/core/Result.hpp"
#include "../engine/core/Time.hpp"
#include "../engine/platform/Window.hpp"
#include "../engine/render/BlackHolePass.hpp"
#include "../engine/render/PostProcessPass.hpp"
#include "../engine/render/QualitySettings.hpp"
#include "../engine/render/StarfieldPass.hpp"
#include "../engine/ui/UIRenderer.hpp"
#include "BlackHoleModel.hpp"
#include "ObserverController.hpp"

#include <string>

namespace sf {

struct SimulationOptions {
    u32 windowWidth = 1600;
    u32 windowHeight = 900;
    bool fullscreen = false;
    bool verticalSync = true;
    bool runTests = false;
    bool hideInterface = false;
    u32 frameLimit = 0;
    u32 presetIndex = 0;
    f64 startRadius = 0.0;
    f64 startInclination = 0.0;
    f64 targetFramesPerSecond = 60.0;
    QualityPreset qualityPreset = QualityPreset::Count;
    bool qualityAutomatic = true;
    ObserverMode observerMode = ObserverMode::Orbit;
    std::string screenshotPath;
};

class SimulationApp {
public:
    Status initialize(const SimulationOptions& options);
    void run();
    void shutdown();

private:
    void applyPreset(u32 index);
    void applyQualitySettings();
    void handleInput(f64 stepSeconds);
    void renderFrame();
    void drawInterface();
    void drawPhysicsPanel();
    void drawControlPanel();
    void drawScalePanel();
    void captureScreenshot(const std::string& path);
    void setNotice(const std::string& text, f64 seconds);

    Window window;
    UIRenderer userInterface;
    StarfieldPass starfieldPass;
    BlackHolePass blackHolePass;
    PostProcessPass postProcessPass;
    RenderTarget sceneTarget;
    Shader compositeShader;
    FullscreenTriangle fullscreenTriangle;
    Camera camera;
    FrameClock frameClock;
    AdaptiveQualityController quality;

    BlackHoleModel model;
    ObserverController observer;
    ObserverReadout readout;
    SimulationOptions launch;

    bool sceneChanged();

    std::string noticeText;
    f64 noticeTimer = 0.0;
    f64 elapsedSeconds = 0.0;
    f64 frozenSeconds = 0.0;
    f64 stillSeconds = 0.0;
    DVec3 lastObserverRadii = DVec3(1.0e30, 0.0, 0.0);
    Quat lastOrientation;
    f64 lastFieldOfView = 0.0;
    f64 lastParameterSignature = 0.0;
    u32 lastQualityKey = 0;
    bool converging = false;
    u64 renderedFrames = 0;
    u32 activePreset = 0;
    u32 selectedControl = 0;
    bool interfaceVisible = true;
    bool controlsVisible = true;
    bool screenshotTaken = false;
};

}
