#include "QualitySettings.hpp"

#include "../core/Log.hpp"
#include "../math/Scalar.hpp"

#include <cstring>

namespace sf {
namespace {

bool containsFragment(const char* haystack, const char* needle) {
    if (!haystack || !needle) return false;
    std::string lowered;
    for (const char* cursor = haystack; *cursor; ++cursor) {
        lowered += (*cursor >= 'A' && *cursor <= 'Z') ? static_cast<char>(*cursor - 'A' + 'a') : *cursor;
    }
    return lowered.find(needle) != std::string::npos;
}

}

QualitySettings QualitySettings::fromPreset(QualityPreset preset) {
    QualitySettings settings;
    settings.preset = preset;
    switch (preset) {
        case QualityPreset::Sparmodus:
            settings.sceneResolutionScale = 0.62f;
            settings.blackHoleResolutionScale = 0.28f;
            settings.blackHoleMaximumSteps = 96;
            settings.blackHoleStepFraction = 0.062f;
            settings.blackHoleIntegratorOrder = 1;
            settings.blackHoleJetStrength = 0.0f;
            settings.skyDetail = 0;
            settings.sphereSubdivisions = 2;
            settings.atmosphereEnabled = false;
            settings.ringsEnabled = false;
            settings.bloomEnabled = false;
            settings.bloomLevels = 0;
            settings.filmGrain = 0.0f;
            settings.chromaticAberration = 0.0f;
            settings.maximumVisibleBodies = 12;
            settings.mapStarBudget = 180;
            break;
        case QualityPreset::Niedrig:
            settings.sceneResolutionScale = 0.80f;
            settings.blackHoleResolutionScale = 0.36f;
            settings.blackHoleMaximumSteps = 160;
            settings.blackHoleStepFraction = 0.042f;
            settings.blackHoleIntegratorOrder = 1;
            settings.blackHoleJetStrength = 0.55f;
            settings.skyDetail = 1;
            settings.sphereSubdivisions = 3;
            settings.atmosphereEnabled = true;
            settings.ringsEnabled = false;
            settings.bloomEnabled = true;
            settings.bloomLevels = 2;
            settings.filmGrain = 0.008f;
            settings.chromaticAberration = 0.0008f;
            settings.maximumVisibleBodies = 24;
            settings.mapStarBudget = 360;
            break;
        case QualityPreset::Mittel:
            settings.sceneResolutionScale = 1.0f;
            settings.blackHoleResolutionScale = 0.50f;
            settings.blackHoleMaximumSteps = 280;
            settings.blackHoleStepFraction = 0.028f;
            settings.blackHoleIntegratorOrder = 2;
            settings.blackHoleJetStrength = 1.0f;
            settings.skyDetail = 2;
            settings.sphereSubdivisions = 4;
            settings.bloomLevels = 4;
            settings.maximumVisibleBodies = 48;
            settings.mapStarBudget = 700;
            break;
        case QualityPreset::Hoch:
            settings.sceneResolutionScale = 1.0f;
            settings.blackHoleResolutionScale = 0.70f;
            settings.blackHoleMaximumSteps = 400;
            settings.blackHoleStepFraction = 0.020f;
            settings.blackHoleIntegratorOrder = 2;
            settings.blackHoleJetStrength = 1.0f;
            settings.skyDetail = 2;
            settings.sphereSubdivisions = 5;
            settings.bloomLevels = 5;
            settings.maximumVisibleBodies = 72;
            settings.mapStarBudget = 900;
            break;
        case QualityPreset::Ultra:
            settings.sceneResolutionScale = 1.0f;
            settings.blackHoleResolutionScale = 1.0f;
            settings.blackHoleMaximumSteps = 520;
            settings.blackHoleStepFraction = 0.014f;
            settings.blackHoleIntegratorOrder = 2;
            settings.blackHoleJetStrength = 1.0f;
            settings.skyDetail = 2;
            settings.sphereSubdivisions = 6;
            settings.bloomLevels = 5;
            settings.filmGrain = 0.020f;
            settings.chromaticAberration = 0.0018f;
            settings.maximumVisibleBodies = 128;
            settings.mapStarBudget = 1400;
            break;
        default:
            break;
    }
    return settings;
}

const char* QualitySettings::presetName(QualityPreset preset) {
    switch (preset) {
        case QualityPreset::Sparmodus: return "SPARMODUS";
        case QualityPreset::Niedrig: return "NIEDRIG";
        case QualityPreset::Mittel: return "MITTEL";
        case QualityPreset::Hoch: return "HOCH";
        case QualityPreset::Ultra: return "ULTRA";
        default: return "UNBEKANNT";
    }
}

const char* QualitySettings::presetDescription(QualityPreset preset) {
    switch (preset) {
        case QualityPreset::Sparmodus:
            return "Fuer schwache Geraete und Notebook-Grafik: halbe Aufloesung, sparsamer Geodaeten-Integrator, "
                   "kein Bloom, keine Jets. Das Schwarze Loch bleibt vollstaendig physikalisch, nur groeber abgetastet.";
        case QualityPreset::Niedrig:
            return "Fuer aeltere Grafikkarten: reduzierte Aufloesung, weniger Schritte, Bloom in zwei Stufen.";
        case QualityPreset::Mittel:
            return "Ausgewogen fuer Mittelklassehardware, volle Fensteraufloesung.";
        case QualityPreset::Hoch:
            return "Fuer aktuelle Grafikkarten: dichte Geodaeten-Abtastung, voller Bloom.";
        case QualityPreset::Ultra:
            return "Kerr-Raymarching in voller Aufloesung mit maximaler Schrittzahl.";
        default:
            return "";
    }
}

QualityPreset QualitySettings::presetFromText(const std::string& text, QualityPreset fallback) {
    std::string lowered;
    for (char character : text) {
        lowered += (character >= 'A' && character <= 'Z') ? static_cast<char>(character - 'A' + 'a') : character;
    }
    if (lowered == "spar" || lowered == "sparmodus" || lowered == "potato" || lowered == "minimal") {
        return QualityPreset::Sparmodus;
    }
    if (lowered == "niedrig" || lowered == "low") return QualityPreset::Niedrig;
    if (lowered == "mittel" || lowered == "medium") return QualityPreset::Mittel;
    if (lowered == "hoch" || lowered == "high") return QualityPreset::Hoch;
    if (lowered == "ultra" || lowered == "maximal") return QualityPreset::Ultra;
    return fallback;
}

QualityPreset AdaptiveQualityController::detectStartingPreset(const char* rendererName, const char* vendorName) {
    if (containsFragment(rendererName, "llvmpipe") || containsFragment(rendererName, "softwarerasterizer") ||
        containsFragment(rendererName, "gdi generic") || containsFragment(rendererName, "swiftshader")) {
        return QualityPreset::Sparmodus;
    }
    if (containsFragment(rendererName, "uhd graphics") || containsFragment(rendererName, "hd graphics") ||
        containsFragment(rendererName, "iris") || containsFragment(rendererName, "vega 8") ||
        containsFragment(rendererName, "radeon graphics") || containsFragment(vendorName, "intel")) {
        return QualityPreset::Sparmodus;
    }
    if (containsFragment(rendererName, "gtx 10") || containsFragment(rendererName, "gtx 16") ||
        containsFragment(rendererName, "mx") || containsFragment(rendererName, "rx 5")) {
        return QualityPreset::Niedrig;
    }
    if (containsFragment(rendererName, "rtx 40") || containsFragment(rendererName, "rtx 50") ||
        containsFragment(rendererName, "rx 7") || containsFragment(rendererName, "rx 9")) {
        return QualityPreset::Hoch;
    }
    return QualityPreset::Mittel;
}

void AdaptiveQualityController::configure(QualityPreset startingPreset, bool automatic, f64 targetFramesPerSecond) {
    basePreset = QualitySettings::fromPreset(startingPreset);
    active = basePreset;
    automaticEnabled = automatic;
    targetFrameSeconds = 1.0 / clampValue(targetFramesPerSecond, 20.0, 240.0);
    smoothedFrameSeconds = targetFrameSeconds;
    dynamicScale = 1.0f;
    sinceChange = 10.0;
    sustainedSlowSeconds = 0.0;
    sustainedFastSeconds = 0.0;
    changeReason = automatic ? "Automatische Anpassung aktiv" : "Feste Qualitaetsstufe";
    logInfo("quality", "Stufe %s, automatisch %s, Ziel %.0f fps", QualitySettings::presetName(startingPreset),
            automatic ? "an" : "aus", 1.0 / targetFrameSeconds);
}

void AdaptiveQualityController::setPreset(QualityPreset preset) {
    basePreset = QualitySettings::fromPreset(preset);
    dynamicScale = 1.0f;
    applyDynamicScale();
    sinceChange = 0.0;
    sustainedSlowSeconds = 0.0;
    sustainedFastSeconds = 0.0;
    changeReason = std::string("Stufe ") + QualitySettings::presetName(preset);
    logInfo("quality", "Qualitaetsstufe gewechselt: %s", QualitySettings::presetName(preset));
}

void AdaptiveQualityController::stepPreset(i32 direction) {
    const i32 current = static_cast<i32>(basePreset.preset);
    const i32 next = clampValue(current + direction, 0, static_cast<i32>(QualityPreset::Count) - 1);
    if (next == current) return;
    setPreset(static_cast<QualityPreset>(next));
}

void AdaptiveQualityController::setAutomatic(bool value) {
    automaticEnabled = value;
    changeReason = value ? "Automatische Anpassung aktiv" : "Automatische Anpassung aus";
    if (!value) {
        dynamicScale = 1.0f;
        applyDynamicScale();
    }
}

void AdaptiveQualityController::applyDynamicScale() {
    active = basePreset;
    active.blackHoleResolutionScale = clampValue(basePreset.blackHoleResolutionScale * dynamicScale, 0.20f, 1.0f);
    active.sceneResolutionScale = clampValue(basePreset.sceneResolutionScale * mixValue(0.72f, 1.0f, dynamicScale),
                                             0.5f, 1.0f);
    active.blackHoleMaximumSteps = static_cast<u32>(clampValue(
        static_cast<f32>(basePreset.blackHoleMaximumSteps) * mixValue(0.45f, 1.0f, dynamicScale), 64.0f, 520.0f));
    active.blackHoleStepFraction = clampValue(basePreset.blackHoleStepFraction / maxValue(dynamicScale, 0.25f), 0.012f,
                                              0.085f);
}

void AdaptiveQualityController::submitFrameTime(f64 frameSeconds) {
    if (frameSeconds <= 0.0) return;
    const f64 clamped = clampValue(frameSeconds, 1.0 / 1000.0, 0.5);
    smoothedFrameSeconds = smoothedFrameSeconds * 0.90 + clamped * 0.10;
    sinceChange += clamped;
    if (!automaticEnabled) return;

    const f64 slowThreshold = targetFrameSeconds * 1.35;
    const f64 fastThreshold = targetFrameSeconds * 0.72;

    if (smoothedFrameSeconds > slowThreshold) {
        sustainedSlowSeconds += clamped;
        sustainedFastSeconds = 0.0;
    } else if (smoothedFrameSeconds < fastThreshold) {
        sustainedFastSeconds += clamped;
        sustainedSlowSeconds = 0.0;
    } else {
        sustainedSlowSeconds = 0.0;
        sustainedFastSeconds = 0.0;
    }

    if (sustainedSlowSeconds > 1.2) {
        sustainedSlowSeconds = 0.0;
        if (dynamicScale > 0.36f) {
            dynamicScale = clampValue(dynamicScale - 0.16f, 0.30f, 1.0f);
            applyDynamicScale();
            sinceChange = 0.0;
            changeReason = "Aufloesung gesenkt";
        } else if (basePreset.preset != QualityPreset::Sparmodus) {
            const QualityPreset lower = static_cast<QualityPreset>(static_cast<u32>(basePreset.preset) - 1);
            basePreset = QualitySettings::fromPreset(lower);
            dynamicScale = 1.0f;
            applyDynamicScale();
            sinceChange = 0.0;
            changeReason = std::string("Automatisch auf ") + QualitySettings::presetName(lower);
            logInfo("quality", "Automatisch heruntergestuft auf %s bei %.1f fps",
                    QualitySettings::presetName(lower), smoothedFramesPerSecond());
        }
    } else if (sustainedFastSeconds > 4.0) {
        sustainedFastSeconds = 0.0;
        if (dynamicScale < 0.999f) {
            dynamicScale = clampValue(dynamicScale + 0.10f, 0.30f, 1.0f);
            applyDynamicScale();
            sinceChange = 0.0;
            changeReason = "Aufloesung erhoeht";
        }
    }
}

}
