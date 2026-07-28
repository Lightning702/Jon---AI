#include "platform/Window.h"
#include "core/Log.h"
#include "core/FileSystem.h"
#include "launcher/Collection.h"

int main(int argc, char** argv) {
    bool showConsole = false;
    bool windowed = false;
    int forcedPreset = -1;
    int testFrames = 0;
    int testCard = -1;
    int testPlay = -1;
    bool testMapOpen = false;
    bool testAutoRun = false;
    int seedTest = 0;
    std::string shotPath;

    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if (a == "-console") showConsole = true;
        else if (a == "-windowed") windowed = true;
        else if (a == "-preset" && i + 1 < argc) forcedPreset = std::atoi(argv[++i]);
        else if (a == "-frames" && i + 1 < argc) testFrames = std::atoi(argv[++i]);
        else if (a == "-shot" && i + 1 < argc) shotPath = argv[++i];
        else if (a == "-card" && i + 1 < argc) testCard = std::atoi(argv[++i]);
        else if (a == "-play" && i + 1 < argc) testPlay = std::atoi(argv[++i]);
        else if (a == "-map") testMapOpen = true;
        else if (a == "-run") testAutoRun = true;
        else if (a == "-seeds" && i + 1 < argc) seedTest = std::atoi(argv[++i]);
    }

    if (!showConsole) {
        HWND console = GetConsoleWindow();
        if (console) ShowWindow(console, SW_HIDE);
    }

    echo::fs::init();
    echo::logInit("echo.log");
    LOG_INFO("FelWorks Game Collection %s", ECHO_VERSION);
    LOG_INFO("Root: %s", echo::fs::rootDir().c_str());

    echo::WindowDesc desc;
    desc.title = "FelWorks Game Collection";
    desc.width = 0;
    desc.height = 0;
    desc.fullscreen = !windowed;

    echo::Window window;
    if (!window.create(desc)) {
        MessageBoxA(nullptr, "Fenster konnte nicht erstellt werden.\nOpenGL 3.3 wird benoetigt.", "FelWorks", MB_ICONERROR);
        return 1;
    }

    felworks::Collection collection;
    if (!collection.init(&window, forcedPreset, windowed)) {
        MessageBoxA(nullptr, "Initialisierung fehlgeschlagen.\nDetails in echo.log", "FelWorks", MB_ICONERROR);
        window.destroy();
        return 2;
    }

    collection.setTestMode(testFrames, shotPath, testCard);
    collection.setTestPlay(testPlay);
    collection.setTestMapOpen(testMapOpen);
    collection.setTestAutoRun(testAutoRun);
    collection.setSeedTest(seedTest);
    collection.run();
    collection.shutdown();
    window.destroy();

    LOG_INFO("Shutdown complete");
    echo::logShutdown();
    return 0;
}
