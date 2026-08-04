#include "MainMenuScreen.hpp"

#include "../../engine/math/Noise.hpp"
#include "../../engine/math/Random.hpp"
#include "../../engine/math/Scalar.hpp"
#include "../../engine/ui/Localization.hpp"

#include <cstdio>

namespace sf {
namespace {

constexpr f64 kCycleLength = 90.0;

f64 smoothBlend(f64 value) {
    const f64 clamped = clampValue(value, 0.0, 1.0);
    return clamped * clamped * (3.0 - 2.0 * clamped);
}

}

void MainMenuScreen::initialize(const VoidHeart& heart) {
    gravitationalRadius = heart.gravitationalRadiusMeters();
    cycleTime = 0.0;
    selection = 0;
    pendingAction = MainMenuAction::None;

    keys.clear();
    keys.push_back({0.0, DVec3(-96.0, 15.0, 132.0), DVec3(0.0, 0.0, 0.0), 46.0, 12.0});
    keys.push_back({18.0, DVec3(-74.0, 11.0, 104.0), DVec3(0.0, 0.0, 0.0), 48.0, 11.0});
    keys.push_back({40.0, DVec3(-46.0, 22.0, 62.0), DVec3(0.0, 0.0, 0.0), 54.0, 9.0});
    keys.push_back({65.0, DVec3(-11.0, 6.4, 15.0), DVec3(0.0, 0.0, 0.0), 66.0, 5.0});
    keys.push_back({82.0, DVec3(-7.2, 2.4, 8.6), DVec3(0.0, 0.0, 0.0), 78.0, 0.0});
    keys.push_back({kCycleLength, DVec3(-96.0, 15.0, 132.0), DVec3(0.0, 0.0, 0.0), 46.0, 12.0});

    entries.clear();
    entries.push_back(translate("menu.continue"));
    entries.push_back(translate("menu.newgame"));
    entries.push_back(translate("menu.multiplayer"));
    entries.push_back(translate("menu.catalog"));
    entries.push_back(translate("menu.settings"));
    entries.push_back(translate("menu.quit"));
}

void MainMenuScreen::seekCycle(f64 seconds) {
    cycleTime = seconds;
    while (cycleTime >= kCycleLength) cycleTime -= kCycleLength;
    while (cycleTime < 0.0) cycleTime += kCycleLength;
}

DVec3 MainMenuScreen::samplePosition(f64 time) const {
    for (usize index = 0; index + 1 < keys.size(); ++index) {
        if (time < keys[index].time || time > keys[index + 1].time) continue;
        const f64 span = maxValue(keys[index + 1].time - keys[index].time, 1.0e-4);
        const f64 alpha = smoothBlend((time - keys[index].time) / span);
        return lerp(keys[index].positionInRadii, keys[index + 1].positionInRadii, alpha);
    }
    return keys.empty() ? DVec3::zero() : keys.front().positionInRadii;
}

DVec3 MainMenuScreen::sampleTarget(f64 time) const {
    for (usize index = 0; index + 1 < keys.size(); ++index) {
        if (time < keys[index].time || time > keys[index + 1].time) continue;
        const f64 span = maxValue(keys[index + 1].time - keys[index].time, 1.0e-4);
        const f64 alpha = smoothBlend((time - keys[index].time) / span);
        return lerp(keys[index].targetInRadii, keys[index + 1].targetInRadii, alpha);
    }
    return keys.empty() ? DVec3::zero() : keys.front().targetInRadii;
}

f64 MainMenuScreen::sampleFieldOfView(f64 time) const {
    for (usize index = 0; index + 1 < keys.size(); ++index) {
        if (time < keys[index].time || time > keys[index + 1].time) continue;
        const f64 span = maxValue(keys[index + 1].time - keys[index].time, 1.0e-4);
        const f64 alpha = smoothBlend((time - keys[index].time) / span);
        return mixValue(keys[index].fieldOfViewDegrees, keys[index + 1].fieldOfViewDegrees, alpha);
    }
    return 55.0;
}

f64 MainMenuScreen::sampleFramingBias(f64 time) const {
    for (usize index = 0; index + 1 < keys.size(); ++index) {
        if (time < keys[index].time || time > keys[index + 1].time) continue;
        const f64 span = maxValue(keys[index + 1].time - keys[index].time, 1.0e-4);
        const f64 alpha = smoothBlend((time - keys[index].time) / span);
        return mixValue(keys[index].framingBiasDegrees, keys[index + 1].framingBiasDegrees, alpha);
    }
    return 0.0;
}

DVec3 MainMenuScreen::handheldOffset(f64 time) const {
    const f64 amplitude = 0.0026;
    const f64 x = simplexNoise3(0x48414E44ull, DVec3(time * 0.12, 0.0, 0.0));
    const f64 y = simplexNoise3(0x48414E44ull, DVec3(0.0, time * 0.11, 4.7));
    const f64 z = simplexNoise3(0x48414E44ull, DVec3(9.1, 0.0, time * 0.09));
    return DVec3(x, y, z) * amplitude;
}

void MainMenuScreen::update(f64 stepSeconds, const Input& input) {
    const DVec3 previous = samplePosition(cycleTime);
    cycleTime += stepSeconds;
    while (cycleTime >= kCycleLength) cycleTime -= kCycleLength;
    const DVec3 current = samplePosition(cycleTime);
    const f64 travelled = length(current - previous) / maxValue(stepSeconds, 1.0e-4);
    motionAmount = clampValue(travelled / 140.0, 0.0, 1.0);

    if (entries.empty()) return;

    if (input.keyPressed(Key::Down) || input.keyPressed(Key::S)) {
        selection = (selection + 1) % static_cast<u32>(entries.size());
    }
    if (input.keyPressed(Key::Up) || input.keyPressed(Key::W)) {
        selection = (selection + static_cast<u32>(entries.size()) - 1) % static_cast<u32>(entries.size());
    }
    if (input.keyPressed(Key::Enter) || input.keyPressed(Key::Space)) {
        switch (selection) {
            case 0: pendingAction = MainMenuAction::Continue; break;
            case 1: pendingAction = MainMenuAction::NewGame; break;
            case 2: pendingAction = MainMenuAction::Multiplayer; break;
            case 3: pendingAction = MainMenuAction::Catalogue; break;
            case 4: pendingAction = MainMenuAction::Settings; break;
            default: pendingAction = MainMenuAction::Quit; break;
        }
    }
    if (input.keyPressed(Key::Escape)) pendingAction = MainMenuAction::Quit;
}

void MainMenuScreen::configureCamera(Camera& camera, const DVec3& blackHoleWorldPosition) const {
    const DVec3 offset = (samplePosition(cycleTime) + handheldOffset(cycleTime)) * gravitationalRadius;
    const DVec3 target = sampleTarget(cycleTime) * gravitationalRadius;
    const DVec3 worldPosition = blackHoleWorldPosition + offset;

    camera.setRenderOrigin(worldPosition);
    camera.setWorldPosition(worldPosition);

    Vec3 forward = normalize((blackHoleWorldPosition + target - worldPosition).toFloat());
    const Vec3 worldUp(0.0f, 1.0f, 0.0f);
    Vec3 right = cross(forward, worldUp);
    if (lengthSquared(right) < 1.0e-8f) right = Vec3::unitX();
    right = normalize(right);

    const Quat framing = Quat::fromAxisAngle(cross(right, forward), radians(static_cast<f32>(sampleFramingBias(cycleTime))));
    forward = normalize(framing * forward);
    right = normalize(cross(forward, worldUp));
    const Vec3 up = cross(right, forward);
    camera.setOrientation(Quat::fromBasis(right, up, forward));
    camera.setPerspective(radians(static_cast<f32>(sampleFieldOfView(cycleTime))), camera.aspectRatio(), 0.5f,
                          1.0e12f);
}

void MainMenuScreen::collectBodies(std::vector<CelestialBodyDraw>& bodies, const DVec3& blackHoleWorldPosition) const {
    bodies.clear();
    if (cycleTime > 54.0) return;

    const DVec3 giantAnchor = blackHoleWorldPosition + samplePosition(29.0) * gravitationalRadius +
                              DVec3(-0.104, 0.012, -0.082) * gravitationalRadius;

    CelestialBodyDraw gasGiant;
    gasGiant.worldPosition = giantAnchor;
    gasGiant.radiusMeters = 7.2e7;
    gasGiant.primaryColor = Vec3(0.52f, 0.38f, 0.24f);
    gasGiant.secondaryColor = Vec3(0.74f, 0.60f, 0.42f);
    gasGiant.atmosphereColor = Vec3(0.72f, 0.56f, 0.36f);
    gasGiant.atmosphereDensity = 1.4f;
    gasGiant.atmosphereHeightFraction = 0.05f;
    gasGiant.surfaceType = CelestialSurface::GasGiant;
    gasGiant.hasRing = true;
    gasGiant.ringInnerFraction = 1.4f;
    gasGiant.ringOuterFraction = 2.6f;
    gasGiant.ringColor = Vec3(0.78f, 0.70f, 0.56f);
    gasGiant.surfaceSeed = 4177;
    gasGiant.orientation = Quat::fromAxisAngle(normalize(Vec3(0.14f, 1.0f, 0.06f)),
                                               static_cast<f32>(cycleTime * 0.010));
    bodies.push_back(gasGiant);

    for (u32 index = 0; index < 3; ++index) {
        CelestialBodyDraw moon;
        const f64 angle = cycleTime * 0.06 + static_cast<f64>(index) * 2.1;
        const f64 distance = (3.4 + static_cast<f64>(index) * 1.8) * gasGiant.radiusMeters;
        moon.worldPosition = giantAnchor + DVec3(std::cos(angle) * distance, std::sin(angle) * distance * 0.18,
                                                 std::sin(angle) * distance);
        moon.radiusMeters = 1.4e6 + static_cast<f64>(index) * 6.0e5;
        moon.primaryColor = Vec3(0.42f - static_cast<f32>(index) * 0.05f, 0.40f, 0.38f);
        moon.secondaryColor = Vec3(0.30f, 0.29f, 0.28f);
        moon.atmosphereDensity = 0.0f;
        moon.surfaceType = CelestialSurface::Rock;
        moon.surfaceSeed = 9001 + index;
        bodies.push_back(moon);
    }

    for (u32 index = 0; index < 18; ++index) {
        Random random(hashCombine(0xA57E01Dull, index));
        const f64 keyTime = random.rangeDouble(0.0, 22.0);
        const DVec3 pathPoint = samplePosition(keyTime);
        const DVec3 lateral(random.rangeDouble(-0.22, 0.22), random.rangeDouble(-0.09, 0.09),
                            random.rangeDouble(-0.22, 0.22));

        CelestialBodyDraw asteroid;
        asteroid.worldPosition = blackHoleWorldPosition + (pathPoint + lateral) * gravitationalRadius;
        asteroid.radiusMeters = random.rangeDouble(4.0e5, 2.6e6);
        asteroid.primaryColor = Vec3(0.26f, 0.23f, 0.21f);
        asteroid.secondaryColor = Vec3(0.17f, 0.16f, 0.15f);
        asteroid.atmosphereDensity = 0.0f;
        asteroid.surfaceDetail = 1.6f;
        asteroid.roughness = 0.94f;
        asteroid.surfaceType = CelestialSurface::Rock;
        asteroid.surfaceSeed = 3000 + index;
        asteroid.orientation = Quat::fromAxisAngle(random.unitVector(), static_cast<f32>(cycleTime * 0.08));
        bodies.push_back(asteroid);
    }

    const DVec3 foreground = samplePosition(minValue(cycleTime + 2.4, 16.0));
    CelestialBodyDraw wreck;
    wreck.worldPosition = blackHoleWorldPosition + (foreground + DVec3(-0.030, -0.011, -0.024)) * gravitationalRadius;
    wreck.radiusMeters = 2.6e5;
    wreck.primaryColor = Vec3(0.20f, 0.21f, 0.23f);
    wreck.secondaryColor = Vec3(0.12f, 0.12f, 0.14f);
    wreck.metallic = 0.82f;
    wreck.roughness = 0.52f;
    wreck.atmosphereDensity = 0.0f;
    wreck.surfaceDetail = 1.9f;
    wreck.surfaceType = CelestialSurface::Metal;
    wreck.surfaceSeed = 60613;
    wreck.orientation = Quat::fromAxisAngle(normalize(Vec3(0.3f, 0.8f, 0.5f)), static_cast<f32>(cycleTime * 0.035));
    bodies.push_back(wreck);

    CelestialBodyDraw explorer;
    explorer.worldPosition = blackHoleWorldPosition + (foreground + DVec3(0.021, 0.006, -0.017)) * gravitationalRadius;
    explorer.radiusMeters = 9.0e4;
    explorer.primaryColor = Vec3(0.16f, 0.17f, 0.19f);
    explorer.secondaryColor = Vec3(0.30f, 0.34f, 0.38f);
    explorer.metallic = 0.90f;
    explorer.roughness = 0.28f;
    explorer.emissiveStrength = 0.06f;
    explorer.atmosphereDensity = 0.0f;
    explorer.surfaceType = CelestialSurface::Metal;
    explorer.surfaceSeed = 1701;
    explorer.orientation = Quat::fromAxisAngle(normalize(Vec3(0.1f, 1.0f, 0.2f)), static_cast<f32>(cycleTime * 0.02));
    bodies.push_back(explorer);
}

f32 MainMenuScreen::exposureBias() const {
    const f64 distance = length(samplePosition(cycleTime));
    return static_cast<f32>(clampValue(0.09 + distance / 2600.0, 0.055, 0.34));
}

void MainMenuScreen::draw(UIRenderer& ui, bool saveAvailable, bool bridgeOnline) {
    saveWasAvailable = saveAvailable;
    const UIStyle& style = ui.style();
    const f32 width = static_cast<f32>(ui.surfaceWidth());
    const f32 height = static_cast<f32>(ui.surfaceHeight());
    const f32 pulse = 0.5f + 0.5f * std::sin(static_cast<f32>(cycleTime) * 1.4f);

    const f32 panelWidth = clampValue(width * 0.28f, 320.0f, 480.0f);
    const f32 panelHeight = clampValue(height * 0.42f, 280.0f, 420.0f);
    const f32 panelX = width * 0.07f;
    const f32 panelY = height - panelHeight - height * 0.12f;

    ui.drawTextShadowed(translate("menu.title"), panelX, panelY - 96.0f, 6.0f, style.text);
    ui.drawTextShadowed(translate("menu.subtitle"), panelX + 4.0f, panelY - 44.0f, 2.4f, style.accent);
    ui.drawRect(panelX, panelY - 16.0f, panelWidth * 0.6f, 1.0f, style.accentDim);

    ui.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);

    const f32 entryHeight = panelHeight / static_cast<f32>(entries.size() + 1);
    for (usize index = 0; index < entries.size(); ++index) {
        const f32 entryY = panelY + entryHeight * (0.75f + static_cast<f32>(index));
        const bool active = index == selection;
        const bool disabled = index == 0 && !saveAvailable;

        Vec4 color = disabled ? style.textDim : (active ? style.accent : style.text);
        if (active) {
            Vec4 highlight = style.accent;
            highlight.w = 0.14f + 0.10f * pulse;
            ui.drawRect(panelX + 8.0f, entryY - 6.0f, panelWidth - 16.0f, entryHeight * 0.78f, highlight);
            ui.drawRect(panelX + 8.0f, entryY - 6.0f, 3.0f, entryHeight * 0.78f, style.accent);
        }
        ui.drawText(entries[index], panelX + 26.0f, entryY, 2.0f, color);
    }

    const f32 footerY = height - 46.0f;
    ui.drawText("FELWORKS", panelX, footerY, 1.5f, style.textDim);
    ui.drawText(bridgeOnline ? "JON: VERBUNDEN" : "JON: OFFLINE-GEHIRN", panelX + 140.0f, footerY, 1.5f,
                bridgeOnline ? style.accent : style.textDim);

    char timecode[64];
    std::snprintf(timecode, sizeof(timecode), "VOID HEART  T+%05.1f s", cycleTime);
    ui.drawText(timecode, width - 28.0f, 32.0f, 1.6f, style.voidGold, TextAlign::Right);
    if (!qualityLine.empty()) {
        ui.drawText(qualityLine, width - 28.0f, 56.0f, 1.3f, style.textDim, TextAlign::Right);
    }

    if (!submenuText.empty()) {
        const f32 noticeWidth = ui.textWidth(submenuText, 1.8f) + 48.0f;
        ui.drawHologramPanel(width * 0.5f - noticeWidth * 0.5f, height * 0.16f, noticeWidth, 56.0f, style, pulse);
        ui.drawText(submenuText, width * 0.5f, height * 0.16f + 22.0f, 1.8f, style.text, TextAlign::Center);
    }
}

MainMenuAction MainMenuScreen::consumeAction() {
    const MainMenuAction action = pendingAction;
    pendingAction = MainMenuAction::None;
    if (action == MainMenuAction::Continue && !saveWasAvailable) return MainMenuAction::None;
    return action;
}

}
