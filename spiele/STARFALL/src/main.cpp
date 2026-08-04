#include "engine/core/CommandLine.hpp"
#include "engine/core/Log.hpp"
#include "engine/net/Socket.hpp"
#include "engine/platform/FileSystem.hpp"
#include "game/GameApp.hpp"

#include <cstdio>

namespace sf {

int runTestSuite();

namespace {

GameLaunchOptions parseOptions(const CommandLine& commandLine) {
    GameLaunchOptions options;
    options.universeSeed = commandLine.unsignedInteger("seed", options.universeSeed);
    options.windowWidth = static_cast<u32>(commandLine.integer("width", options.windowWidth));
    options.windowHeight = static_cast<u32>(commandLine.integer("height", options.windowHeight));
    options.fullscreen = commandLine.flag("fullscreen", false) && !commandLine.flag("windowed", false);
    options.verticalSync = commandLine.flag("vsync", true);
    options.startInVoidZone = commandLine.flag("voidzone", false);
    options.runTests = commandLine.has("tests");
    options.frameLimit = static_cast<u32>(commandLine.integer("frames", 0));
    options.screenshotPath = commandLine.text("shot", "");

    QualityPreset preset = QualityPreset::Count;
    if (commandLine.has("grafik")) preset = QualitySettings::presetFromText(commandLine.text("grafik", ""), preset);
    if (commandLine.has("quality")) preset = QualitySettings::presetFromText(commandLine.text("quality", ""), preset);
    if (commandLine.flag("sparmodus", false) || commandLine.flag("lowspec", false)) {
        preset = QualityPreset::Sparmodus;
    }
    options.qualityPreset = preset;
    options.qualityAutomatic = commandLine.flag("autografik", preset == QualityPreset::Count);
    options.targetFramesPerSecond = commandLine.number("zielfps", options.targetFramesPerSecond);
    options.menuStartSeconds = commandLine.number("menuzeit", 0.0);
    options.skipMenu = commandLine.flag("flug", false) || commandLine.flag("landen", false);
    options.startLanded = commandLine.flag("landen", false);
    options.coopHost = commandLine.text("coophost", options.coopHost);
    options.coopPort = static_cast<u16>(commandLine.integer("coopport", options.coopPort));
    options.playerName = commandLine.text("name", options.playerName);
    options.coopHostSession = commandLine.flag("host", false);
    options.coopJoinCode = commandLine.text("join", "");
    return options;
}

}

}

int main(int argumentCount, char** argumentValues) {
    sf::CommandLine& commandLine = sf::globalCommandLine();
    commandLine.parse(argumentCount, argumentValues);

    const std::string logPath =
        sf::FileSystem::joinPath(sf::FileSystem::executableDirectory(), "starfall.log");
    sf::logInit(logPath, commandLine.flag("structuredlog", false));
    sf::logSetMinimumLevel(commandLine.flag("verbose", false) ? sf::LogLevel::Debug : sf::LogLevel::Info);

    const sf::GameLaunchOptions options = sf::parseOptions(commandLine);

    if (options.runTests) {
        const int failures = sf::runTestSuite();
        sf::logShutdown();
        return failures;
    }

    sf::TcpSocket::platformStartup();

    sf::GameApp application;
    const sf::Status started = application.initialize(options);
    if (!started.ok()) {
        sf::logFatal("app", "Start fehlgeschlagen: %s", started.detail.c_str());
        std::fprintf(stderr, "STARFALL konnte nicht starten: %s\n", started.detail.c_str());
        application.shutdown();
        sf::TcpSocket::platformShutdown();
        sf::logShutdown();
        return 2;
    }

    application.run();
    application.shutdown();

    sf::TcpSocket::platformShutdown();
    sf::logShutdown();
    return 0;
}
