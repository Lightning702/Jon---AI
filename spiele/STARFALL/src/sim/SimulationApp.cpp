#include "SimulationApp.hpp"

#include "../engine/core/Log.hpp"
#include "../engine/math/Scalar.hpp"
#include "../engine/platform/FileSystem.hpp"
#include "../engine/render/SkyCommon.hpp"

#include <cstdio>
#include <vector>

namespace sf {
namespace {

const char* const kCompositeSource = R"GLSL(#version 330 core
in vec2 vScreenUv;
out vec4 fragColor;
uniform sampler2D uSource;
uniform float uIntensity;

void main() {
    fragColor = vec4(texture(uSource, vScreenUv).rgb * uIntensity, 1.0);
}
)GLSL";

constexpr u32 kControlCount = 8;

std::string formatMass(f64 massSolar) {
    char buffer[96];
    if (massSolar >= 1.0e9) std::snprintf(buffer, sizeof(buffer), "%.2f Mrd. Sonnenmassen", massSolar / 1.0e9);
    else if (massSolar >= 1.0e6) std::snprintf(buffer, sizeof(buffer), "%.3f Mio. Sonnenmassen", massSolar / 1.0e6);
    else if (massSolar >= 1.0e3) std::snprintf(buffer, sizeof(buffer), "%.1f Tsd. Sonnenmassen", massSolar / 1.0e3);
    else std::snprintf(buffer, sizeof(buffer), "%.2f Sonnenmassen", massSolar);
    return buffer;
}

std::string formatLength(f64 meters) {
    char buffer[96];
    if (meters >= kLightYear * 0.01) std::snprintf(buffer, sizeof(buffer), "%.4f Lichtjahre", meters / kLightYear);
    else if (meters >= kAstronomicalUnit * 0.01) std::snprintf(buffer, sizeof(buffer), "%.4f AE", meters / kAstronomicalUnit);
    else if (meters >= 1.0e6) std::snprintf(buffer, sizeof(buffer), "%.3f Mio. km", meters / 1.0e9 * 1000.0);
    else if (meters >= 1000.0) std::snprintf(buffer, sizeof(buffer), "%.1f km", meters / 1000.0);
    else std::snprintf(buffer, sizeof(buffer), "%.1f m", meters);
    return buffer;
}

std::string formatDuration(f64 seconds) {
    char buffer[96];
    const f64 years = seconds / 3.15576e7;
    if (years >= 1.0e6) std::snprintf(buffer, sizeof(buffer), "%.3g Jahre", years);
    else if (seconds >= 3.15576e7) std::snprintf(buffer, sizeof(buffer), "%.2f Jahre", years);
    else if (seconds >= 86400.0) std::snprintf(buffer, sizeof(buffer), "%.2f Tage", seconds / 86400.0);
    else if (seconds >= 3600.0) std::snprintf(buffer, sizeof(buffer), "%.2f Stunden", seconds / 3600.0);
    else if (seconds >= 60.0) std::snprintf(buffer, sizeof(buffer), "%.2f Minuten", seconds / 60.0);
    else std::snprintf(buffer, sizeof(buffer), "%.3f Sekunden", seconds);
    return buffer;
}

std::string formatScientific(f64 value, const char* unit) {
    char buffer[96];
    const f64 magnitude = std::fabs(value);
    if (magnitude > 0.0 && (magnitude < 1.0e-3 || magnitude >= 1.0e6)) {
        std::snprintf(buffer, sizeof(buffer), "%.4g %s", value, unit);
    } else {
        std::snprintf(buffer, sizeof(buffer), "%.4f %s", value, unit);
    }
    return buffer;
}

std::string formatRadii(f64 value) {
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%.3f r_g", value);
    return buffer;
}

}

Status SimulationApp::initialize(const SimulationOptions& options) {
    launch = options;

    WindowSettings windowSettings;
    windowSettings.title = "STARFALL - Schwarzloch-Simulation";
    windowSettings.width = options.windowWidth;
    windowSettings.height = options.windowHeight;
    windowSettings.fullscreen = options.fullscreen;
    windowSettings.verticalSync = options.verticalSync;

    const Status opened = window.open(windowSettings);
    if (!opened.ok()) return opened;

    Status status = userInterface.initialize();
    if (!status.ok()) return status;
    status = starfieldPass.initialize();
    if (!status.ok()) return status;
    status = blackHolePass.initialize();
    if (!status.ok()) return status;
    status = postProcessPass.initialize();
    if (!status.ok()) return status;
    status = compositeShader.compile("SceneComposite", kFullscreenVertexSource, kCompositeSource);
    if (!status.ok()) return status;
    fullscreenTriangle.initialize();

    const QualityPreset detected = options.qualityPreset != QualityPreset::Count
                                       ? options.qualityPreset
                                       : AdaptiveQualityController::detectStartingPreset(gl().rendererName,
                                                                                         gl().vendorName);
    quality.configure(detected, options.qualityAutomatic, options.targetFramesPerSecond);
    applyQualitySettings();

    interfaceVisible = !options.hideInterface;
    observer.setMode(options.observerMode);
    applyPreset(options.presetIndex);
    if (options.startRadius > 0.0) observer.setRadius(options.startRadius);

    frameClock.reset();
    logInfo("sim", "Simulation bereit: %s", model.parameters().name.c_str());
    return statusOk();
}

void SimulationApp::shutdown() {
    compositeShader.release();
    fullscreenTriangle.release();
    sceneTarget.release();
    postProcessPass.release();
    blackHolePass.release();
    starfieldPass.release();
    userInterface.release();
    window.close();
    logInfo("sim", "Beendet nach %llu Bildern", static_cast<unsigned long long>(renderedFrames));
}

void SimulationApp::applyPreset(u32 index) {
    const std::vector<BlackHoleParameters>& catalogue = BlackHoleModel::presets();
    activePreset = index % static_cast<u32>(catalogue.size());
    model.setParameters(catalogue[activePreset]);
    const f64 inclination = launch.startInclination > 0.0 ? launch.startInclination
                                                          : model.parameters().inclinationDegrees;
    observer.reset(model.parameters().observerRadii, inclination);
    setNotice(model.parameters().name + " - " + model.parameters().note, 6.0);
}

void SimulationApp::applyQualitySettings() {
    const QualitySettings& settings = quality.settings();
    const u32 width = maxValue<u32>(320, static_cast<u32>(static_cast<f32>(window.width()) *
                                                         settings.sceneResolutionScale));
    const u32 height = maxValue<u32>(180, static_cast<u32>(static_cast<f32>(window.height()) *
                                                          settings.sceneResolutionScale));
    if (!sceneTarget.valid() || sceneTarget.width() != width || sceneTarget.height() != height) {
        sceneTarget.create(width, height, GL_RGBA16F, false);
    }
}

void SimulationApp::setNotice(const std::string& text, f64 seconds) {
    noticeText = text;
    noticeTimer = seconds;
}

void SimulationApp::handleInput(f64 stepSeconds) {
    const Input& input = window.input();

    if (input.keyPressed(Key::Escape)) window.requestClose();
    if (input.keyPressed(Key::F11)) window.toggleFullscreen();
    if (input.keyPressed(Key::Tab)) interfaceVisible = !interfaceVisible;
    if (input.keyPressed(Key::C)) controlsVisible = !controlsVisible;
    if (input.keyPressed(Key::V)) observer.cycleMode();

    if (input.keyPressed(Key::F5)) {
        quality.setAutomatic(false);
        quality.stepPreset(-1);
        applyQualitySettings();
    }
    if (input.keyPressed(Key::F6)) {
        quality.setAutomatic(false);
        quality.stepPreset(1);
        applyQualitySettings();
    }
    if (input.keyPressed(Key::F7)) quality.setAutomatic(!quality.automatic());
    if (input.keyPressed(Key::F8)) {
        quality.setAutomatic(false);
        quality.setPreset(QualityPreset::Sparmodus);
        applyQualitySettings();
    }

    const Key presetKeys[] = {Key::Digit1, Key::Digit2, Key::Digit3, Key::Digit4, Key::Digit5, Key::Digit6};
    for (u32 index = 0; index < 6 && index < BlackHoleModel::presets().size(); ++index) {
        if (input.keyPressed(presetKeys[index])) applyPreset(index);
    }

    if (input.keyPressed(Key::Down)) selectedControl = (selectedControl + 1) % kControlCount;
    if (input.keyPressed(Key::Up)) selectedControl = (selectedControl + kControlCount - 1) % kControlCount;

    const f64 direction = static_cast<f64>(input.keyDown(Key::Right) ? 1 : 0) -
                          static_cast<f64>(input.keyDown(Key::Left) ? 1 : 0);
    if (std::fabs(direction) > 0.0) {
        BlackHoleParameters& parameters = model.mutableParameters();
        const f64 rate = stepSeconds * (input.keyDown(Key::LeftShift) ? 4.0 : 1.0);
        switch (selectedControl) {
            case 0: parameters.massSolar = clampValue(parameters.massSolar * std::exp(direction * rate * 1.6), 1.0, 1.0e11); break;
            case 1: parameters.spin = clampValue(parameters.spin + direction * rate * 0.35, 0.0, 0.998); break;
            case 2: parameters.accretionRate = clampValue(parameters.accretionRate + direction * rate * 1.1, 0.0, 6.0); break;
            case 3: parameters.diskInnerTemperatureKelvin = clampValue(parameters.diskInnerTemperatureKelvin + direction * rate * 6200.0, 1600.0, 28000.0); break;
            case 4: parameters.diskOuterRadii = clampValue(parameters.diskOuterRadii + direction * rate * 22.0, 4.0, 120.0); break;
            case 5: parameters.diskThickness = clampValue(parameters.diskThickness + direction * rate * 0.11, 0.004, 0.36); break;
            case 6: parameters.jetStrength = clampValue(parameters.jetStrength + direction * rate * 2.2, 0.0, 5.0); break;
            default: observer.setRadius(observer.radius() * std::exp(-direction * rate * 1.1)); break;
        }
        model.refresh();
    }

    if (input.keyPressed(Key::R)) applyPreset(activePreset);
    if (input.keyPressed(Key::P)) {
        const std::string path = FileSystem::joinPath(FileSystem::executableDirectory(), "aufnahme.ppm");
        captureScreenshot(path);
        setNotice("BILD GESPEICHERT: " + path, 4.0);
    }
}

void SimulationApp::renderFrame() {
    if (window.resizedThisFrame()) applyQualitySettings();

    const QualitySettings& settings = quality.settings();
    const BlackHoleDerived& derived = model.derived();
    const BlackHoleParameters& parameters = model.parameters();

    const DVec3 observerRadii = observer.positionInRadii();
    const DVec3 observerPosition = observerRadii * derived.gravitationalRadiusMeters;
    readout = model.observerAt(length(observerRadii));

    camera.setRenderOrigin(observerPosition);
    camera.setWorldPosition(observerPosition);
    camera.setOrientation(observer.orientation());
    camera.setPerspective(radians(static_cast<f32>(observer.fieldOfViewDegrees())), window.aspectRatio(), 0.5f,
                          1.0e12f);

    sceneTarget.bindForDrawing();
    sceneTarget.clear(0.0f, 0.0f, 0.0f, 1.0f, false);

    StarfieldParameters starfield;
    starfield.elapsedSeconds = static_cast<f32>(elapsedSeconds);
    starfield.skyDetail = settings.skyDetail;
    starfield.localStarIntensity = 0.0f;
    starfield.nebulaIntensity = 1.05f;
    starfield.galaxyIntensity = 1.0f;
    starfield.starIntensity = 1.25f;
    starfield.exposureScale = 2.4f;
    starfieldPass.render(camera, starfield);

    BlackHoleRenderParameters blackHole;
    blackHole.centerWorldPosition = DVec3::zero();
    blackHole.gravitationalRadiusMeters = derived.gravitationalRadiusMeters;
    blackHole.spinParameter = static_cast<f32>(parameters.spin);
    blackHole.diskInnerRadius = static_cast<f32>(derived.diskInnerRadii);
    blackHole.diskOuterRadius = static_cast<f32>(parameters.diskOuterRadii);
    blackHole.diskInnerTemperatureKelvin = static_cast<f32>(parameters.diskInnerTemperatureKelvin);
    blackHole.diskThickness = static_cast<f32>(parameters.diskThickness);
    blackHole.diskBrightness = 26.0f;
    blackHole.jetStrength = static_cast<f32>(parameters.jetStrength);
    blackHole.accretionRate = static_cast<f32>(parameters.accretionRate);
    blackHole.elapsedSeconds = static_cast<f32>(elapsedSeconds);
    blackHole.resolutionScale = settings.blackHoleResolutionScale;
    blackHole.maximumSteps = settings.blackHoleMaximumSteps;
    blackHole.stepFraction = settings.blackHoleStepFraction;
    blackHole.integratorOrder = settings.blackHoleIntegratorOrder;
    blackHole.skyDetail = settings.skyDetail;
    blackHolePass.render(camera, blackHole, sceneTarget.width(), sceneTarget.height());

    sceneTarget.bindForDrawing();
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    gl().blendFuncSeparate(GL_ONE, GL_ONE, GL_ONE, GL_ZERO);
    compositeShader.bind();
    compositeShader.setTextureUnit("uSource", 0);
    compositeShader.setFloat("uIntensity", 1.0f);
    bindTextureUnit(0, blackHolePass.resultTexture());
    fullscreenTriangle.draw();
    glDisable(GL_BLEND);

    PostProcessParameters post;
    post.exposure = static_cast<f32>(clampValue(0.10 + readout.radiusRadii / 2200.0, 0.055, 0.34));
    post.elapsedSeconds = static_cast<f32>(elapsedSeconds);
    post.bloomStrength = 0.075f;
    post.bloomLevels = settings.bloomEnabled ? settings.bloomLevels : 0;
    post.filmGrain = settings.filmGrain;
    post.chromaticAberration = settings.chromaticAberration;
    post.vignetteStrength = 0.30f;
    postProcessPass.render(sceneTarget.colorTexture(), window.width(), window.height(), post);

    userInterface.beginFrame(window.width(), window.height());
    if (interfaceVisible) drawInterface();
    userInterface.endFrame();

    window.present();
    ++renderedFrames;

    if (!launch.screenshotPath.empty() && !screenshotTaken && renderedFrames > 3) {
        captureScreenshot(launch.screenshotPath);
        screenshotTaken = true;
    }
}

void SimulationApp::drawInterface() {
    const UIStyle& style = userInterface.style();
    const f32 width = static_cast<f32>(window.width());

    userInterface.drawTextShadowed("SCHWARZLOCH-SIMULATION", 24.0f, 24.0f, 2.0f, style.accent);
    userInterface.drawText(model.parameters().name, 24.0f, 50.0f, 1.6f, style.voidGold);
    userInterface.drawText(model.parameters().note, 24.0f, 70.0f, 1.2f, style.textDim);

    char corner[160];
    std::snprintf(corner, sizeof(corner), "%.0f fps  %s%s", quality.smoothedFramesPerSecond(),
                  QualitySettings::presetName(quality.preset()), quality.automatic() ? "  AUTO" : "");
    userInterface.drawText(corner, width - 24.0f, 24.0f, 1.3f, style.textDim, TextAlign::Right);
    userInterface.drawText(ObserverController::modeName(observer.currentMode()), width - 24.0f, 44.0f, 1.4f,
                           style.accent, TextAlign::Right);

    drawPhysicsPanel();
    drawScalePanel();
    if (controlsVisible) drawControlPanel();

    userInterface.drawText("1-6 OBJEKT  V ANSICHT  PFEILE REGLER  C REGLER AUS  TAB HUD  P BILD  F5/F6 GRAFIK  ESC ENDE",
                           24.0f, static_cast<f32>(window.height()) - 26.0f, 1.2f, style.textDim);

    if (noticeTimer > 0.0 && !noticeText.empty()) {
        const f32 noticeWidth = userInterface.textWidth(noticeText, 1.5f) + 44.0f;
        const f32 noticeX = width * 0.5f - noticeWidth * 0.5f;
        const f32 noticeY = static_cast<f32>(window.height()) * 0.80f;
        userInterface.drawHologramPanel(noticeX, noticeY, noticeWidth, 44.0f, style,
                                        static_cast<f32>(clampValue(noticeTimer, 0.0, 1.0)));
        userInterface.drawText(noticeText, width * 0.5f, noticeY + 17.0f, 1.5f, style.accent, TextAlign::Center);
    }
}

void SimulationApp::drawPhysicsPanel() {
    const UIStyle& style = userInterface.style();
    const BlackHoleDerived& derived = model.derived();
    const f32 panelWidth = 372.0f;
    const f32 panelHeight = 244.0f;
    const f32 panelX = 24.0f;
    const f32 panelY = 100.0f;
    const f32 pulse = 0.5f + 0.5f * std::sin(static_cast<f32>(elapsedSeconds) * 1.3f);

    userInterface.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);
    userInterface.drawText("KENNZAHLEN", panelX + 14.0f, panelY + 14.0f, 1.6f, style.accent);

    struct Row {
        const char* label;
        std::string value;
    };
    char spinText[32];
    std::snprintf(spinText, sizeof(spinText), "%.3f", model.parameters().spin);

    const std::vector<Row> rows = {
        {"MASSE", formatMass(model.parameters().massSolar)},
        {"SPIN a", spinText},
        {"r_g = GM/c2", formatLength(derived.gravitationalRadiusMeters)},
        {"r_s = 2 r_g", formatLength(derived.schwarzschildRadiusMeters)},
        {"HORIZONT r+", formatRadii(derived.horizonRadii)},
        {"ERGOSPHAERE", formatRadii(derived.ergosphereEquatorialRadii)},
        {"PHOTONENSPHAERE", formatRadii(derived.photonSphereRadii)},
        {"ISCO", formatRadii(derived.innermostStableOrbitRadii)},
        {"SCHATTENRADIUS", formatRadii(derived.shadowAngularRadiusRadii)},
        {"HAWKING-TEMP", formatScientific(derived.hawkingTemperatureKelvin, "K")},
        {"VERDAMPFUNG", formatDuration(derived.evaporationYears * 3.15576e7)}};

    f32 rowY = panelY + 40.0f;
    for (const Row& row : rows) {
        userInterface.drawText(row.label, panelX + 14.0f, rowY, 1.2f, style.textDim);
        userInterface.drawText(row.value, panelX + panelWidth - 14.0f, rowY, 1.2f, style.text, TextAlign::Right);
        rowY += 18.0f;
    }
}

void SimulationApp::drawScalePanel() {
    const UIStyle& style = userInterface.style();
    const BlackHoleDerived& derived = model.derived();
    const f32 panelWidth = 348.0f;
    const f32 panelHeight = 236.0f;
    const f32 panelX = static_cast<f32>(window.width()) - panelWidth - 24.0f;
    const f32 panelY = 72.0f;
    const f32 pulse = 0.5f + 0.5f * std::sin(static_cast<f32>(elapsedSeconds) * 1.1f);

    userInterface.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);
    userInterface.drawText("BEOBACHTER", panelX + 14.0f, panelY + 14.0f, 1.6f, style.accent);

    char line[192];
    f32 rowY = panelY + 40.0f;

    userInterface.drawText(BlackHoleModel::zoneLabel(derived, readout.radiusRadii), panelX + 14.0f, rowY, 1.4f,
                           readout.insideErgosphere ? style.danger : style.voidGold);
    rowY += 22.0f;

    std::snprintf(line, sizeof(line), "ABSTAND %.3f r_g", readout.radiusRadii);
    userInterface.drawText(line, panelX + 14.0f, rowY, 1.3f, style.text);
    rowY += 18.0f;

    userInterface.drawText(std::string("        ") + formatLength(readout.distanceMeters), panelX + 14.0f, rowY, 1.2f,
                           style.textDim);
    rowY += 20.0f;

    std::snprintf(line, sizeof(line), "ZEITFAKTOR %.6f", readout.gravitationalTimeDilation);
    userInterface.drawText(line, panelX + 14.0f, rowY, 1.3f,
                           readout.gravitationalTimeDilation < 0.5 ? style.warning : style.text);
    rowY += 18.0f;

    if (readout.gravitationalTimeDilation > 1.0e-6) {
        std::snprintf(line, sizeof(line), "1 h HIER = %.3f h FERN", 1.0 / readout.gravitationalTimeDilation);
        userInterface.drawText(line, panelX + 14.0f, rowY, 1.2f, style.textDim);
    }
    rowY += 20.0f;

    std::snprintf(line, sizeof(line), "KREISBAHN %.4f c", readout.circularOrbitSpeedFraction);
    userInterface.drawText(line, panelX + 14.0f, rowY, 1.3f, style.text);
    rowY += 18.0f;

    std::snprintf(line, sizeof(line), "FLUCHT %.4f c", readout.escapeSpeedFraction);
    userInterface.drawText(line, panelX + 14.0f, rowY, 1.3f, style.text);
    rowY += 18.0f;

    userInterface.drawText(std::string("UMLAUF ") + formatDuration(readout.orbitalPeriodSeconds), panelX + 14.0f,
                           rowY, 1.2f, style.textDim);
    rowY += 18.0f;

    std::snprintf(line, sizeof(line), "GEZEITEN %.4g /s2 je m", readout.tidalAccelerationPerMetre);
    userInterface.drawText(line, panelX + 14.0f, rowY, 1.2f,
                           readout.tidalAccelerationPerMetre > 1.0 ? style.danger : style.textDim);
}

void SimulationApp::drawControlPanel() {
    const UIStyle& style = userInterface.style();
    const BlackHoleParameters& parameters = model.parameters();
    const f32 panelWidth = 348.0f;
    const f32 panelHeight = 232.0f;
    const f32 panelX = static_cast<f32>(window.width()) - panelWidth - 24.0f;
    const f32 panelY = 320.0f;
    const f32 pulse = 0.5f + 0.5f * std::sin(static_cast<f32>(elapsedSeconds) * 1.7f);

    userInterface.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, pulse);
    userInterface.drawText("REGLER", panelX + 14.0f, panelY + 14.0f, 1.6f, style.accent);

    char values[kControlCount][64];
    std::snprintf(values[0], 64, "%.4g M_Sonne", parameters.massSolar);
    std::snprintf(values[1], 64, "%.3f", parameters.spin);
    std::snprintf(values[2], 64, "%.2f", parameters.accretionRate);
    std::snprintf(values[3], 64, "%.0f K", parameters.diskInnerTemperatureKelvin);
    std::snprintf(values[4], 64, "%.1f r_g", parameters.diskOuterRadii);
    std::snprintf(values[5], 64, "%.3f", parameters.diskThickness);
    std::snprintf(values[6], 64, "%.2f", parameters.jetStrength);
    std::snprintf(values[7], 64, "%.2f r_g", observer.radius());

    const char* labels[kControlCount] = {"MASSE",         "SPIN",           "AKKRETIONSRATE", "SCHEIBENTEMP",
                                         "SCHEIBENRAND",  "SCHEIBENDICKE",  "JETSTAERKE",     "ABSTAND"};

    f32 rowY = panelY + 40.0f;
    for (u32 index = 0; index < kControlCount; ++index) {
        const bool selected = index == selectedControl;
        if (selected) {
            Vec4 highlight = style.accent;
            highlight.w = 0.16f;
            userInterface.drawRect(panelX + 10.0f, rowY - 4.0f, panelWidth - 20.0f, 22.0f, highlight);
            userInterface.drawRect(panelX + 10.0f, rowY - 4.0f, 3.0f, 22.0f, style.accent);
        }
        userInterface.drawText(labels[index], panelX + 20.0f, rowY, 1.3f, selected ? style.accent : style.text);
        userInterface.drawText(values[index], panelX + panelWidth - 14.0f, rowY, 1.3f,
                               selected ? style.accent : style.textDim, TextAlign::Right);
        rowY += 23.0f;
    }
}

void SimulationApp::captureScreenshot(const std::string& path) {
    const u32 width = window.width();
    const u32 height = window.height();
    std::vector<u8> pixels(static_cast<usize>(width) * height * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, static_cast<GLsizei>(width), static_cast<GLsizei>(height), GL_RGB, GL_UNSIGNED_BYTE,
                 pixels.data());

    const std::string header = "P6\n" + std::to_string(width) + " " + std::to_string(height) + "\n255\n";
    std::vector<u8> flipped(pixels.size());
    for (u32 row = 0; row < height; ++row) {
        const usize sourceOffset = static_cast<usize>(height - 1 - row) * width * 3;
        const usize targetOffset = static_cast<usize>(row) * width * 3;
        for (usize index = 0; index < static_cast<usize>(width) * 3; ++index) {
            flipped[targetOffset + index] = pixels[sourceOffset + index];
        }
    }

    std::vector<u8> file(header.begin(), header.end());
    file.insert(file.end(), flipped.begin(), flipped.end());
    FileSystem::writeBinary(path, file.data(), file.size());
    logInfo("sim", "Bild gespeichert: %s", path.c_str());
}

void SimulationApp::run() {
    while (!window.shouldClose()) {
        window.pumpEvents();
        frameClock.tick();

        const f64 delta = frameClock.deltaSeconds();
        elapsedSeconds += delta;
        noticeTimer = maxValue(noticeTimer - delta, 0.0);

        const QualityPreset previousPreset = quality.preset();
        const f32 previousScale = quality.settings().sceneResolutionScale;
        quality.submitFrameTime(delta);
        if (quality.preset() != previousPreset ||
            std::fabs(quality.settings().sceneResolutionScale - previousScale) > 1.0e-4f) {
            applyQualitySettings();
        }

        handleInput(delta);
        observer.update(window.input(), delta, true);
        renderFrame();

        if (launch.frameLimit > 0 && renderedFrames >= launch.frameLimit) break;
    }
}

}
