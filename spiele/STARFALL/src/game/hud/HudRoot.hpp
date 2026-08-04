#pragma once

#include "../../engine/ui/UIRenderer.hpp"
#include "../jon/JonCompanion.hpp"
#include "../ship/Ship.hpp"
#include "../space/HyperdriveSystem.hpp"
#include "../space/SpaceFlightController.hpp"
#include "../voidheart/VoidHeart.hpp"

#include <string>
#include <vector>

namespace sf {

struct HudFrameData {
    std::string systemName;
    std::string bodyName;
    std::string targetName;
    f64 altitudeMeters = 0.0;
    f64 distanceToTargetMeters = 0.0;
    f64 speedMetresPerSecond = 0.0;
    f64 apoapsisMeters = 0.0;
    f64 periapsisMeters = 0.0;
    f64 orbitalPeriodSeconds = 0.0;
    f64 inclinationDegrees = 0.0;
    bool orbitValid = false;
    f64 oxygenFraction = 1.0;
    f64 universeSeconds = 0.0;
    u32 coopPlayers = 0;
    std::string coopStatus;
    std::string qualityPreset;
    std::string qualityNotice;
    f64 framesPerSecond = 0.0;
    bool qualityAutomatic = true;
    bool showQualityNotice = false;
};

class HudRoot {
public:
    void draw(UIRenderer& ui, const Ship& ship, const FlightState& flight, const SpaceFlightController& controller,
              const HyperdriveState& hyperdrive, const HyperdriveSystem& drive, const VoidHeartState& voidState,
              const JonCompanion& jon, const HudFrameData& frame);

private:
    void drawShipStatus(UIRenderer& ui, const Ship& ship, const FlightState& flight, const HudFrameData& frame);
    void drawFlightBlock(UIRenderer& ui, const FlightState& flight, const SpaceFlightController& controller,
                         const HudFrameData& frame);
    void drawVoidBlock(UIRenderer& ui, const VoidHeartState& voidState);
    void drawHyperdriveBlock(UIRenderer& ui, const HyperdriveState& hyperdrive, const HyperdriveSystem& drive);
    void drawJonPanel(UIRenderer& ui, const JonCompanion& jon);
    void drawReticle(UIRenderer& ui, const FlightState& flight);
    void drawCoopBlock(UIRenderer& ui, const HudFrameData& frame);
    void drawPerformanceBlock(UIRenderer& ui, const HudFrameData& frame);

    f32 pulseTimer = 0.0f;
};

std::string formatDistance(f64 meters);
std::string formatDuration(f64 seconds);
std::string formatSpeed(f64 metresPerSecond);

}
