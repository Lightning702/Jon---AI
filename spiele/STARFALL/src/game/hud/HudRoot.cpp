#include "HudRoot.hpp"

#include "../../engine/math/Scalar.hpp"

#include <cstdio>

namespace sf {

std::string formatDistance(f64 meters) {
    char buffer[64];
    const f64 absolute = std::fabs(meters);
    if (absolute >= kLightYear * 0.01) {
        std::snprintf(buffer, sizeof(buffer), "%.3f Lj", meters / kLightYear);
    } else if (absolute >= kAstronomicalUnit * 0.01) {
        std::snprintf(buffer, sizeof(buffer), "%.4f AE", meters / kAstronomicalUnit);
    } else if (absolute >= 1000.0) {
        std::snprintf(buffer, sizeof(buffer), "%.1f km", meters / 1000.0);
    } else {
        std::snprintf(buffer, sizeof(buffer), "%.0f m", meters);
    }
    return buffer;
}

std::string formatDuration(f64 seconds) {
    char buffer[64];
    if (seconds >= 86400.0) {
        std::snprintf(buffer, sizeof(buffer), "%.1f d", seconds / 86400.0);
    } else if (seconds >= 3600.0) {
        std::snprintf(buffer, sizeof(buffer), "%.1f h", seconds / 3600.0);
    } else if (seconds >= 60.0) {
        std::snprintf(buffer, sizeof(buffer), "%.1f min", seconds / 60.0);
    } else {
        std::snprintf(buffer, sizeof(buffer), "%.1f s", seconds);
    }
    return buffer;
}

std::string formatSpeed(f64 metresPerSecond) {
    char buffer[80];
    const f64 fractionOfLight = metresPerSecond / kSpeedOfLight;
    if (fractionOfLight >= 0.001) {
        std::snprintf(buffer, sizeof(buffer), "%.4f c", fractionOfLight);
    } else if (metresPerSecond >= 10000.0) {
        std::snprintf(buffer, sizeof(buffer), "%.1f km/s", metresPerSecond / 1000.0);
    } else {
        std::snprintf(buffer, sizeof(buffer), "%.0f m/s", metresPerSecond);
    }
    return buffer;
}

namespace {

Vec4 gaugeColor(const UIStyle& style, f64 fraction) {
    if (fraction < 0.22) return style.danger;
    if (fraction < 0.48) return style.warning;
    return style.accent;
}

}

void HudRoot::draw(UIRenderer& ui, const Ship& ship, const FlightState& flight,
                   const SpaceFlightController& controller, const HyperdriveState& hyperdrive,
                   const HyperdriveSystem& drive, const VoidHeartState& voidState, const JonCompanion& jon,
                   const HudFrameData& frame) {
    pulseTimer += 0.016f;
    drawShipStatus(ui, ship, flight, frame);
    drawFlightBlock(ui, flight, controller, frame);
    drawHyperdriveBlock(ui, hyperdrive, drive);
    if (voidState.zone != VoidZone::FarField) drawVoidBlock(ui, voidState);
    drawJonPanel(ui, jon);
    drawReticle(ui, flight);
    if (frame.coopPlayers > 0) drawCoopBlock(ui, frame);
    drawPerformanceBlock(ui, frame);
}

void HudRoot::drawPerformanceBlock(UIRenderer& ui, const HudFrameData& frame) {
    const UIStyle& style = ui.style();
    char line[160];
    std::snprintf(line, sizeof(line), "%.0f fps  %s%s", frame.framesPerSecond, frame.qualityPreset.c_str(),
                  frame.qualityAutomatic ? "  AUTO" : "");
    const f32 baseY = frame.coopPlayers > 0 ? 44.0f : 24.0f;
    ui.drawText(line, static_cast<f32>(ui.surfaceWidth()) - 24.0f, baseY, 1.3f,
                frame.framesPerSecond < 24.0 ? style.warning : style.textDim, TextAlign::Right);

    if (!frame.showQualityNotice || frame.qualityNotice.empty()) return;
    const f32 noticeWidth = ui.textWidth(frame.qualityNotice, 1.4f) + 36.0f;
    const f32 noticeX = static_cast<f32>(ui.surfaceWidth()) * 0.5f - noticeWidth * 0.5f;
    const f32 noticeY = static_cast<f32>(ui.surfaceHeight()) * 0.78f;
    ui.drawHologramPanel(noticeX, noticeY, noticeWidth, 42.0f, style, 0.5f + 0.5f * std::sin(pulseTimer * 5.0f));
    ui.drawText(frame.qualityNotice, static_cast<f32>(ui.surfaceWidth()) * 0.5f, noticeY + 16.0f, 1.4f, style.accent,
                TextAlign::Center);
}

void HudRoot::drawShipStatus(UIRenderer& ui, const Ship& ship, const FlightState& flight, const HudFrameData& frame) {
    const UIStyle& style = ui.style();
    const f32 panelX = 24.0f;
    const f32 panelY = static_cast<f32>(ui.surfaceHeight()) - 208.0f;
    const f32 panelWidth = 306.0f;
    const f32 panelHeight = 184.0f;
    const f32 pulse = 0.5f + 0.5f * std::sin(pulseTimer * 1.7f);

    ui.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);

    f32 rowY = panelY + 16.0f;
    const f32 barX = panelX + 118.0f;
    const f32 barWidth = panelWidth - 136.0f;

    const f64 fuelFraction = flight.fuelKilograms / maxValue(ship.specification().fuelCapacity, 1.0);
    const f64 heatFraction = clampValue(ship.heatFraction() / 1.4, 0.0, 1.0);

    struct Row {
        const char* label;
        f64 fraction;
        bool inverted;
    };
    const Row rows[] = {{"RUMPF", ship.hullIntegrity(), false},
                        {"SCHILD", ship.totalShieldCharge(), false},
                        {"TREIBSTOFF", fuelFraction, false},
                        {"HITZE", heatFraction, true},
                        {"SAUERSTOFF", frame.oxygenFraction, false}};

    for (const Row& row : rows) {
        ui.drawText(row.label, panelX + 14.0f, rowY, 1.5f, style.textDim);
        const f64 gaugeFraction = row.inverted ? 1.0 - row.fraction : row.fraction;
        ui.drawProgressBar(barX, rowY - 2.0f, barWidth, 12.0f, static_cast<f32>(clampValue(row.fraction, 0.0, 1.0)),
                           gaugeColor(style, gaugeFraction), style.accentDim);
        rowY += 22.0f;
    }

    char sectorLine[128];
    std::snprintf(sectorLine, sizeof(sectorLine), "SEKTOR %s %.0f%%  %s %.0f%%  %s %.0f%%  %s %.0f%%",
                  "V", ship.shields().charge[0] * 100.0, "H", ship.shields().charge[1] * 100.0, "L",
                  ship.shields().charge[2] * 100.0, "R", ship.shields().charge[3] * 100.0);
    ui.drawText(sectorLine, panelX + 14.0f, rowY + 4.0f, 1.3f, style.textDim);

    ui.drawText(frame.systemName, panelX + 14.0f, panelY - 22.0f, 1.8f, style.text);
}

void HudRoot::drawFlightBlock(UIRenderer& ui, const FlightState& flight, const SpaceFlightController& controller,
                              const HudFrameData& frame) {
    const UIStyle& style = ui.style();
    const f32 panelWidth = 296.0f;
    const f32 panelHeight = 196.0f;
    const f32 panelX = static_cast<f32>(ui.surfaceWidth()) - panelWidth - 24.0f;
    const f32 panelY = static_cast<f32>(ui.surfaceHeight()) - panelHeight - 24.0f;
    const f32 pulse = 0.5f + 0.5f * std::sin(pulseTimer * 1.2f);

    ui.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);

    char line[128];
    f32 rowY = panelY + 16.0f;

    std::snprintf(line, sizeof(line), "MODUS %s", SpaceFlightController::modeName(controller.currentMode()));
    ui.drawText(line, panelX + 14.0f, rowY, 1.6f, style.accent);
    rowY += 24.0f;

    std::snprintf(line, sizeof(line), "TEMPO %s", formatSpeed(frame.speedMetresPerSecond).c_str());
    ui.drawText(line, panelX + 14.0f, rowY, 1.5f, style.text);
    rowY += 20.0f;

    std::snprintf(line, sizeof(line), "SCHUB %.0f%%", flight.throttleLevel * 100.0);
    ui.drawText(line, panelX + 14.0f, rowY, 1.5f, style.text);
    rowY += 20.0f;

    ui.drawText(std::string("HOEHE ") + formatDistance(frame.altitudeMeters), panelX + 14.0f, rowY, 1.5f, style.text);
    rowY += 20.0f;

    if (frame.orbitValid) {
        ui.drawText(std::string("APO ") + formatDistance(frame.apoapsisMeters), panelX + 14.0f, rowY, 1.4f,
                    style.textDim);
        rowY += 18.0f;
        ui.drawText(std::string("PERI ") + formatDistance(frame.periapsisMeters), panelX + 14.0f, rowY, 1.4f,
                    style.textDim);
        rowY += 18.0f;
        std::snprintf(line, sizeof(line), "UMLAUF %s  INK %.1f Grad", formatDuration(frame.orbitalPeriodSeconds).c_str(),
                      frame.inclinationDegrees);
        ui.drawText(line, panelX + 14.0f, rowY, 1.3f, style.textDim);
        rowY += 18.0f;
    }

    if (flight.plasmaSheath) {
        ui.drawText("PLASMAMANTEL", panelX + 14.0f, rowY, 1.5f, style.warning);
        rowY += 18.0f;
    }
    if (flight.communicationBlackout) {
        ui.drawText("FUNKSTILLE", panelX + 14.0f, rowY, 1.5f, style.danger);
    }
}

void HudRoot::drawVoidBlock(UIRenderer& ui, const VoidHeartState& voidState) {
    const UIStyle& style = ui.style();
    const f32 panelWidth = 336.0f;
    const f32 panelHeight = 132.0f;
    const f32 panelX = static_cast<f32>(ui.surfaceWidth()) * 0.5f - panelWidth * 0.5f;
    const f32 panelY = 24.0f;
    const f32 pulse = 0.5f + 0.5f * std::sin(pulseTimer * 3.1f);

    ui.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);
    ui.drawText("THE VOID HEART", panelX + 14.0f, panelY + 14.0f, 1.8f, style.voidGold);

    char line[192];
    std::snprintf(line, sizeof(line), "ZONE %u  %s", static_cast<u32>(voidState.zone),
                  VoidHeart::zoneName(voidState.zone));
    ui.drawText(line, panelX + 14.0f, panelY + 40.0f, 1.5f,
                voidState.zone <= VoidZone::Ergosphere ? style.danger : style.warning);

    std::snprintf(line, sizeof(line), "ABSTAND %.2f r_g", voidState.radiusInGravitationalRadii);
    ui.drawText(line, panelX + 14.0f, panelY + 62.0f, 1.4f, style.text);

    std::snprintf(line, sizeof(line), "ZEITFAKTOR %.5f", voidState.timeDilation);
    ui.drawText(line, panelX + 14.0f, panelY + 82.0f, 1.4f, style.text);

    std::snprintf(line, sizeof(line), "GEZEITEN %.4f m/s2  SCHILDVERLUST %.1f/s", voidState.tidalStressPerSecond,
                  voidState.shieldDrainPerSecond);
    ui.drawText(line, panelX + 14.0f, panelY + 102.0f, 1.2f, style.textDim);
}

void HudRoot::drawHyperdriveBlock(UIRenderer& ui, const HyperdriveState& hyperdrive, const HyperdriveSystem& drive) {
    if (hyperdrive.phase == HyperdrivePhase::Idle) return;
    const UIStyle& style = ui.style();
    const f32 panelWidth = 380.0f;
    const f32 panelHeight = 92.0f;
    const f32 panelX = static_cast<f32>(ui.surfaceWidth()) * 0.5f - panelWidth * 0.5f;
    const f32 panelY = static_cast<f32>(ui.surfaceHeight()) * 0.68f;

    ui.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, 0.5f + 0.5f * std::sin(pulseTimer * 4.0f));

    const char* phaseText = "BEREIT";
    f32 fraction = 0.0f;
    switch (hyperdrive.phase) {
        case HyperdrivePhase::Charging:
            phaseText = "LADEPHASE";
            fraction = static_cast<f32>(hyperdrive.chargeSeconds / maxValue(hyperdrive.requiredChargeSeconds, 0.01));
            break;
        case HyperdrivePhase::Aligning:
            phaseText = "AUSRICHTUNG";
            fraction = static_cast<f32>(clampValue(1.0 - hyperdrive.alignmentDegrees / 45.0, 0.0, 1.0));
            break;
        case HyperdrivePhase::Tunnelling:
            phaseText = "TRANSIT";
            fraction = static_cast<f32>(hyperdrive.transitSeconds / maxValue(hyperdrive.requiredTransitSeconds, 0.01));
            break;
        case HyperdrivePhase::Exiting: phaseText = "AUSTRITT"; fraction = 1.0f; break;
        case HyperdrivePhase::Cooldown: phaseText = "ABKUEHLUNG"; fraction = 1.0f; break;
        default: break;
    }

    char line[160];
    std::snprintf(line, sizeof(line), "%s  %s", HyperdriveSystem::driveClassName(drive.driveSpecification().driveClass),
                  phaseText);
    ui.drawText(line, panelX + 14.0f, panelY + 14.0f, 1.7f, style.accent);
    ui.drawProgressBar(panelX + 14.0f, panelY + 40.0f, panelWidth - 28.0f, 14.0f, fraction, style.accent,
                       style.accentDim);

    if (hyperdrive.activeHazard != TransitHazard::None) {
        ui.drawText(HyperdriveSystem::hazardName(hyperdrive.activeHazard), panelX + 14.0f, panelY + 62.0f, 1.4f,
                    style.danger);
    } else if (hyperdrive.phase == HyperdrivePhase::Aligning) {
        std::snprintf(line, sizeof(line), "ABWEICHUNG %.1f Grad", hyperdrive.alignmentDegrees);
        ui.drawText(line, panelX + 14.0f, panelY + 62.0f, 1.4f, style.textDim);
    }
}

void HudRoot::drawJonPanel(UIRenderer& ui, const JonCompanion& jon) {
    const std::vector<JonUtterance>& messages = jon.activeMessages();
    if (messages.empty()) return;

    const UIStyle& style = ui.style();
    const f32 panelWidth = clampValue(static_cast<f32>(ui.surfaceWidth()) * 0.42f, 380.0f, 720.0f);
    const f32 lineHeight = 20.0f;
    const f32 panelHeight = 40.0f + lineHeight * static_cast<f32>(messages.size());
    const f32 panelX = 24.0f;
    const f32 panelY = 24.0f;
    const f32 pulse = clampValue(jon.hologramPulse(), 0.0f, 1.0f);

    ui.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);
    ui.drawText(jon.bridgeOnline() ? "JON" : "JON  [OFFLINE]", panelX + 14.0f, panelY + 12.0f, 1.7f, style.accent);

    f32 rowY = panelY + 34.0f;
    for (const JonUtterance& message : messages) {
        Vec4 color = style.text;
        switch (message.urgency) {
            case JonUrgency::Critical: color = style.danger; break;
            case JonUrgency::Warning: color = style.warning; break;
            case JonUrgency::Caution: color = style.voidGold; break;
            case JonUrgency::Notice: color = style.text; break;
            default: color = style.textDim; break;
        }
        std::string text = message.text;
        const f32 maximumCharacters = (panelWidth - 32.0f) / (6.0f * 1.35f);
        if (static_cast<f32>(text.size()) > maximumCharacters) {
            text = text.substr(0, static_cast<usize>(maximumCharacters) - 3) + "...";
        }
        ui.drawText(text, panelX + 14.0f, rowY, 1.35f, color);
        rowY += lineHeight;
    }
}

void HudRoot::drawReticle(UIRenderer& ui, const FlightState& flight) {
    const UIStyle& style = ui.style();
    const f32 centerX = static_cast<f32>(ui.surfaceWidth()) * 0.5f;
    const f32 centerY = static_cast<f32>(ui.surfaceHeight()) * 0.5f;

    Vec4 color = style.accent;
    color.w = 0.62f;
    ui.drawRect(centerX - 12.0f, centerY - 1.0f, 8.0f, 2.0f, color);
    ui.drawRect(centerX + 4.0f, centerY - 1.0f, 8.0f, 2.0f, color);
    ui.drawRect(centerX - 1.0f, centerY - 12.0f, 2.0f, 8.0f, color);
    ui.drawRect(centerX - 1.0f, centerY + 4.0f, 2.0f, 8.0f, color);
    ui.drawCircleOutline(centerX, centerY, 26.0f, 1.6f, 48, Vec4(color.x, color.y, color.z, 0.22f));

    const f32 speedFraction = static_cast<f32>(clampValue(length(flight.velocity) / 1500.0, 0.0, 1.0));
    ui.drawProgressBar(centerX - 90.0f, centerY + 52.0f, 180.0f, 6.0f, speedFraction, style.accentDim, style.accentDim);
}

void HudRoot::drawCoopBlock(UIRenderer& ui, const HudFrameData& frame) {
    const UIStyle& style = ui.style();
    char line[128];
    std::snprintf(line, sizeof(line), "KOOP %u  %s", frame.coopPlayers, frame.coopStatus.c_str());
    ui.drawText(line, static_cast<f32>(ui.surfaceWidth()) - 24.0f, 24.0f, 1.4f, style.accent, TextAlign::Right);
}

}
