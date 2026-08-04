#pragma once

#include "../core/Types.hpp"

#include <string>

namespace sf {

enum class QualityPreset : u32 {
    Sparmodus = 0,
    Niedrig,
    Mittel,
    Hoch,
    Ultra,
    Count
};

struct QualitySettings {
    QualityPreset preset = QualityPreset::Mittel;
    f32 sceneResolutionScale = 1.0f;
    f32 blackHoleResolutionScale = 0.5f;
    u32 blackHoleMaximumSteps = 320;
    f32 blackHoleStepFraction = 0.024f;
    i32 blackHoleIntegratorOrder = 2;
    f32 blackHoleJetStrength = 1.0f;
    i32 skyDetail = 2;
    u32 sphereSubdivisions = 5;
    bool atmosphereEnabled = true;
    bool ringsEnabled = true;
    bool bloomEnabled = true;
    u32 bloomLevels = 5;
    f32 filmGrain = 0.016f;
    f32 chromaticAberration = 0.0014f;
    u32 maximumVisibleBodies = 64;
    u32 mapStarBudget = 900;
    bool verticalSyncRecommended = true;

    static QualitySettings fromPreset(QualityPreset preset);
    static const char* presetName(QualityPreset preset);
    static const char* presetDescription(QualityPreset preset);
    static QualityPreset presetFromText(const std::string& text, QualityPreset fallback);
};

class AdaptiveQualityController {
public:
    void configure(QualityPreset startingPreset, bool automatic, f64 targetFramesPerSecond);

    void submitFrameTime(f64 frameSeconds);
    void setPreset(QualityPreset preset);
    void stepPreset(i32 direction);
    void setAutomatic(bool value);

    const QualitySettings& settings() const { return active; }
    QualityPreset preset() const { return active.preset; }
    bool automatic() const { return automaticEnabled; }
    f64 smoothedFramesPerSecond() const { return smoothedFrameSeconds > 0.0 ? 1.0 / smoothedFrameSeconds : 0.0; }
    f32 dynamicResolutionScale() const { return dynamicScale; }
    bool changedRecently() const { return sinceChange < 1.5; }
    const std::string& lastChangeReason() const { return changeReason; }

    static QualityPreset detectStartingPreset(const char* rendererName, const char* vendorName);

private:
    void applyDynamicScale();

    QualitySettings active = QualitySettings::fromPreset(QualityPreset::Mittel);
    QualitySettings basePreset = QualitySettings::fromPreset(QualityPreset::Mittel);
    std::string changeReason;
    f64 targetFrameSeconds = 1.0 / 60.0;
    f64 smoothedFrameSeconds = 1.0 / 60.0;
    f64 sinceChange = 0.0;
    f64 sustainedSlowSeconds = 0.0;
    f64 sustainedFastSeconds = 0.0;
    f32 dynamicScale = 1.0f;
    bool automaticEnabled = true;
};

}
