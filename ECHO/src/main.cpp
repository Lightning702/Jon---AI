#include "platform/Window.h"
#include "core/Log.h"
#include "core/FileSystem.h"
#include "launcher/Collection.h"
#include "net/CoopSession.h"

static int runNetTest(const std::string& address, const std::string& code) {
    echo::fs::init();
    echo::logInit("echo.log");

    std::string host = address;
    int port = 8759;
    size_t colon = address.rfind(':');
    if (colon != std::string::npos) {
        port = std::atoi(address.c_str() + colon + 1);
        host = address.substr(0, colon);
    }

    echo::CoopSession session;
    session.init("echo", nullptr);
    session.setServer(host, port);
    if (code.empty()) session.hostGame("NetTest", 4242, em::Vec3(0, 0, 0));
    else session.joinGame(code, "NetTest");

    for (int i = 0; i < 600; i++) {
        session.update(0.05f);
        if (session.phase() == echo::COOP_LOBBY && !session.code().empty()) {
            LOG_INFO("NetTest OK: code=%s players=%d ping=%.0fms invite=%s",
                     session.code().c_str(), session.playerCount(), session.ping(),
                     session.invite().c_str());
            for (int k = 0; k < 60; k++) session.update(0.05f);
            LOG_INFO("NetTest roster=%d ping=%.0fms", session.playerCount(), session.ping());
            session.leave();
            session.shutdown();
            echo::logShutdown();
            return 0;
        }
        if (session.phase() == echo::COOP_ERROR) {
            LOG_ERROR("NetTest FAILED: %s", session.errorText().c_str());
            session.shutdown();
            echo::logShutdown();
            return 3;
        }
        Sleep(50);
    }
    LOG_ERROR("NetTest TIMEOUT (phase %d)", session.phase());
    session.shutdown();
    echo::logShutdown();
    return 4;
}

int main(int argc, char** argv) {
    for (int i = 1; i < argc; i++) {
        if (std::string(argv[i]) != "-nettest") continue;
        std::string address = i + 1 < argc ? argv[i + 1] : "127.0.0.1:8759";
        std::string code = i + 2 < argc ? argv[i + 2] : std::string();
        return runNetTest(address, code);
    }
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
