#include "engine/core/CommandLine.hpp"
#include "engine/core/Log.hpp"
#include "engine/platform/FileSystem.hpp"
#include "sim/SimulationApp.hpp"

#include <cstdio>

namespace sf {

int runTestSuite();

namespace {

SimulationOptions parseOptions(const CommandLine& commandLine) {
    SimulationOptions options;
    options.windowWidth = static_cast<u32>(commandLine.integer("width", options.windowWidth));
    options.windowHeight = static_cast<u32>(commandLine.integer("height", options.windowHeight));
    options.fullscreen = commandLine.flag("fullscreen", false) && !commandLine.flag("windowed", false);
    options.verticalSync = commandLine.flag("vsync", true);
    options.runTests = commandLine.has("tests");
    options.hideInterface = commandLine.flag("ohnehud", false);
    options.frameLimit = static_cast<u32>(commandLine.integer("frames", 0));
    options.presetIndex = static_cast<u32>(commandLine.integer("objekt", 0));
    options.startRadius = commandLine.number("abstand", 0.0);
    options.startInclination = commandLine.number("neigung", 0.0);
    options.targetFramesPerSecond = commandLine.number("zielfps", options.targetFramesPerSecond);
    options.screenshotPath = commandLine.text("shot", "");

    QualityPreset preset = QualityPreset::Count;
    if (commandLine.has("grafik")) preset = QualitySettings::presetFromText(commandLine.text("grafik", ""), preset);
    if (commandLine.flag("sparmodus", false) || commandLine.flag("lowspec", false)) {
        preset = QualityPreset::Sparmodus;
    }
    options.qualityPreset = preset;
    options.qualityAutomatic = commandLine.flag("autografik", preset == QualityPreset::Count);

    if (commandLine.flag("kamerafahrt", false)) options.observerMode = ObserverMode::Cinematic;
    else if (commandLine.flag("freiflug", false)) options.observerMode = ObserverMode::Free;
    return options;
}

}

}

int main(int argumentCount, char** argumentValues) {
    sf::CommandLine& commandLine = sf::globalCommandLine();
    commandLine.parse(argumentCount, argumentValues);

    const std::string logPath = sf::FileSystem::joinPath(sf::FileSystem::executableDirectory(), "starfall.log");
    sf::logInit(logPath, commandLine.flag("structuredlog", false));
    sf::logSetMinimumLevel(commandLine.flag("verbose", false) ? sf::LogLevel::Debug : sf::LogLevel::Info);

    const sf::SimulationOptions options = sf::parseOptions(commandLine);

    if (options.runTests) {
        const int failures = sf::runTestSuite();
        sf::logShutdown();
        return failures;
    }

    sf::SimulationApp application;
    const sf::Status started = application.initialize(options);
    if (!started.ok()) {
        sf::logFatal("sim", "Start fehlgeschlagen: %s", started.detail.c_str());
        std::fprintf(stderr, "Die Simulation konnte nicht starten: %s\n", started.detail.c_str());
        application.shutdown();
        sf::logShutdown();
        return 2;
    }

    application.run();
    application.shutdown();
    sf::logShutdown();
    return 0;
}
