#pragma once

#include "../../engine/platform/Input.hpp"
#include "../../engine/render/Camera.hpp"
#include "../../engine/render/CelestialBodyPass.hpp"
#include "../../engine/ui/UIRenderer.hpp"
#include "../voidheart/VoidHeart.hpp"

#include <string>
#include <vector>

namespace sf {

enum class MainMenuAction : u32 {
    None = 0,
    Continue,
    NewGame,
    Multiplayer,
    Catalogue,
    Settings,
    Quit
};

class MainMenuScreen {
public:
    void initialize(const VoidHeart& heart);
    void update(f64 stepSeconds, const Input& input);
    void configureCamera(Camera& camera, const DVec3& blackHoleWorldPosition) const;
    void collectBodies(std::vector<CelestialBodyDraw>& bodies, const DVec3& blackHoleWorldPosition) const;
    void draw(UIRenderer& ui, bool saveAvailable, bool bridgeOnline);

    MainMenuAction consumeAction();
    f32 cycleSeconds() const { return static_cast<f32>(cycleTime); }
    f32 exposureBias() const;
    f32 motionBlurAmount() const { return static_cast<f32>(motionAmount); }
    u32 selectedIndex() const { return selection; }
    void setSubmenuText(const std::string& text) { submenuText = text; }
    void setQualityLine(const std::string& text) { qualityLine = text; }
    void seekCycle(f64 seconds);

private:
    struct CameraKey {
        f64 time = 0.0;
        DVec3 positionInRadii = DVec3::zero();
        DVec3 targetInRadii = DVec3::zero();
        f64 fieldOfViewDegrees = 55.0;
        f64 framingBiasDegrees = 0.0;
    };

    DVec3 samplePosition(f64 time) const;
    DVec3 sampleTarget(f64 time) const;
    f64 sampleFieldOfView(f64 time) const;
    f64 sampleFramingBias(f64 time) const;
    DVec3 handheldOffset(f64 time) const;

    std::vector<CameraKey> keys;
    std::vector<std::string> entries;
    std::string submenuText;
    std::string qualityLine;
    f64 cycleTime = 0.0;
    f64 gravitationalRadius = 6.0553e9;
    f64 motionAmount = 0.0;
    u32 selection = 0;
    MainMenuAction pendingAction = MainMenuAction::None;
    bool saveWasAvailable = false;
};

}
