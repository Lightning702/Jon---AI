#pragma once

#include "../engine/core/ConfigStore.hpp"
#include "../engine/core/Time.hpp"
#include "../engine/platform/Window.hpp"
#include "../engine/render/BlackHolePass.hpp"
#include "../engine/render/CelestialBodyPass.hpp"
#include "../engine/render/PostProcessPass.hpp"
#include "../engine/render/QualitySettings.hpp"
#include "../engine/render/StarfieldPass.hpp"
#include "../engine/render/TerrainPass.hpp"
#include "../engine/ui/UIRenderer.hpp"
#include "alien/TradeMarket.hpp"
#include "base/BaseGrid.hpp"
#include "crafting/RecipeDatabase.hpp"
#include "hud/FootHud.hpp"
#include "hud/HudRoot.hpp"
#include "planet/PlanetSurface.hpp"
#include "player/PlayerCharacter.hpp"
#include "quest/DiscoveryCatalog.hpp"
#include "jon/JonCompanion.hpp"
#include "map/GalaxyMapState.hpp"
#include "multiplayer/CoopSession.hpp"
#include "screens/MainMenuScreen.hpp"
#include "ship/Ship.hpp"
#include "space/HyperdriveSystem.hpp"
#include "space/OrbitalMechanics.hpp"
#include "space/SpaceFlightController.hpp"
#include "universe/GalaxyGenerator.hpp"
#include "voidheart/EndgameCampaign.hpp"
#include "voidheart/ExoticResource.hpp"
#include "voidheart/VoidStation.hpp"

#include <string>
#include <vector>

namespace sf {

enum class GameStateId : u32 {
    Booting = 0,
    MainMenu,
    Loading,
    Flight,
    Landing,
    OnFoot,
    GalaxyMap,
    Paused,
    Shutdown
};

struct GameLaunchOptions {
    u64 universeSeed = 0x5741524653414C4Cull;
    u32 windowWidth = 1600;
    u32 windowHeight = 900;
    bool fullscreen = false;
    bool verticalSync = true;
    bool startInVoidZone = false;
    bool runTests = false;
    bool headlessFrames = false;
    u32 frameLimit = 0;
    QualityPreset qualityPreset = QualityPreset::Count;
    bool qualityAutomatic = true;
    f64 targetFramesPerSecond = 60.0;
    f64 menuStartSeconds = 0.0;
    bool skipMenu = false;
    bool startLanded = false;
    std::string screenshotPath;
    std::string coopHost = "127.0.0.1";
    u16 coopPort = 8759;
    std::string playerName = "Pilot";
    bool coopHostSession = false;
    std::string coopJoinCode;
};

class GameApp {
public:
    Status initialize(const GameLaunchOptions& options);
    void run();
    void shutdown();

    GameStateId state() const { return currentState; }

private:
    void enterState(GameStateId next);
    void loadStartSystem();
    void stepSimulation(f64 stepSeconds);
    void updateMenu(f64 stepSeconds);
    void updateFlight(f64 stepSeconds);
    void updateGalaxyMap(f64 stepSeconds);
    void gatherFlightInput();
    void renderFrame(f64 interpolationAlpha);
    void renderScene(bool menuMode);
    void buildVisibleBodies();
    void buildMapMarkers();
    void refreshJonContext();
    void applyQualitySettings();
    void handleQualityInput();
    void beginLanding(u32 planetIndex);
    void leaveSurface();
    void exitShip();
    void enterShip();
    void updateOnFoot(f64 stepSeconds);
    void stepSurfaceSimulation(f64 stepSeconds);
    void gatherFootInput(FootInput& out);
    void applyMiningBeam(f64 stepSeconds);
    void applyScanner(f64 stepSeconds);
    void applyBuildAction(bool place, bool remove);
    void refreshPanelLists();
    void renderSurface();
    EnvironmentReading readEnvironment() const;
    DVec3 planetLocalOfPlayer() const;
    u32 nearestLandablePlanet(f64& distanceOut) const;
    DVec3 aggregateGravity(const DVec3& position) const;
    f64 alignmentToDestinationDegrees() const;
    void requestHyperjump();
    void captureScreenshot(const std::string& path);

    Window window;
    UIRenderer userInterface;
    StarfieldPass starfieldPass;
    CelestialBodyPass bodyPass;
    BlackHolePass blackHolePass;
    PostProcessPass postProcessPass;
    RenderTarget sceneTarget;
    AdaptiveQualityController quality;
    Shader compositeShader;
    FullscreenTriangle fullscreenTriangle;
    Camera camera;
    FloatingOrigin floatingOrigin;
    FrameClock frameClock;
    FixedStepAccumulator simulationClock{1.0 / 60.0};
    ConfigStore settings;

    UniverseSeed universeSeed;
    GalaxyGenerator galaxyGenerator;
    StarSystemGenerator systemGenerator;
    GalaxyProfile currentGalaxy;
    StarSystemProfile currentSystem;
    std::vector<CelestialBodyDraw> visibleBodies;
    std::vector<MapMarker> mapMarkers;

    VoidHeart voidHeart;
    VoidHeartState voidState;
    VoidStationRegistry voidStations;
    ExoticResourceLedger exoticResources;
    EndgameCampaign endgame;

    Ship ship;
    FlightState flight;
    SpaceFlightController flightController;
    HyperdriveSystem hyperdrive;
    HyperdriveState hyperdriveState;
    HyperRouteSolver routeSolver;
    HyperRoute activeRoute;
    std::string routeDenialText;

    TerrainPass terrainPass;
    PlanetBody landingBody;
    PlanetSurface planetSurface;
    PlayerCharacter player;
    BaseGrid homeBase;
    TradeMarket stationMarket;
    DiscoveryCatalog discoveries;
    FootHud footHud;
    FootHudFrame footFrame;
    std::vector<const TerrainChunk*> visibleChunks;
    std::vector<ScatterRenderItem> scatterItems;
    std::vector<const Recipe*> panelRecipes;
    std::vector<const BuildPartDefinition*> panelParts;
    Inventory shipInventory;
    DVec3 shipLandingPosition = DVec3::zero();
    f64 credits = 42000.0;
    f64 surfaceDayPhase = 0.5;
    f64 statusMessageTimer = 0.0;
    u32 landedPlanetIndex = kInvalidIndex32;
    u32 selectedRecipeIndex = 0;
    u32 selectedPartIndex = 0;
    u32 selectedTradeIndex = 0;
    FootPanel activePanel = FootPanel::None;
    bool marketAvailable = false;

    JonCompanion jon;
    JonWorldContext jonContext;
    CoopSession coop;
    MainMenuScreen mainMenu;
    GalaxyMapState galaxyMap;
    HudRoot hud;

    GameLaunchOptions launch;
    GameStateId currentState = GameStateId::Booting;
    GameStateId previousState = GameStateId::Booting;
    SystemCoord playerSystem;
    f64 universeSeconds = 0.0;
    f64 personalSeconds = 0.0;
    f64 oxygenFraction = 1.0;
    f64 researchProgress = 0.0;
    u32 researchTier = 1;
    u32 recognizedCivilizations = 2;
    u64 renderedFrames = 0;
    bool saveAvailable = false;
    bool cursorCaptured = false;
    bool screenshotTaken = false;
};

}
