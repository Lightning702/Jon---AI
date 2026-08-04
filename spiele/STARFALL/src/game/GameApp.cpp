#include "GameApp.hpp"

#include "../engine/core/Log.hpp"
#include "../engine/job/JobSystem.hpp"
#include "../engine/math/Scalar.hpp"
#include "../engine/memory/FrameAllocator.hpp"
#include "../engine/memory/MemoryTracker.hpp"
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

constexpr f64 kVoidHeartSystemDistance = 4.2e12;

}

Status GameApp::initialize(const GameLaunchOptions& options) {
    launch = options;
    universeSeed.setValue(options.universeSeed);

    JobSystem::instance().initialize(0);
    globalFrameAllocator().initialize(32ull * 1024ull * 1024ull, 3, MemoryCategory::Scratch);

    WindowSettings windowSettings;
    windowSettings.title = "STARFALL: BEYOND THE VOID";
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
    status = bodyPass.initialize();
    if (!status.ok()) return status;
    status = blackHolePass.initialize();
    if (!status.ok()) return status;
    status = postProcessPass.initialize();
    if (!status.ok()) return status;
    status = compositeShader.compile("SceneComposite", kFullscreenVertexSource, kCompositeSource);
    if (!status.ok()) return status;
    status = terrainPass.initialize();
    if (!status.ok()) return status;
    fullscreenTriangle.initialize();

    const QualityPreset detected = options.qualityPreset != QualityPreset::Count
                                       ? options.qualityPreset
                                       : AdaptiveQualityController::detectStartingPreset(gl().rendererName,
                                                                                         gl().vendorName);
    quality.configure(detected, options.qualityAutomatic, options.targetFramesPerSecond);
    applyQualitySettings();

    voidHeart.configure(SystemCoord(), DVec3::zero());
    voidStations = VoidStationRegistry();

    player.configureInventory(24);
    player.inventory().add(ItemId::Ferrite, 120);
    player.inventory().add(ItemId::Carbon, 90);
    player.inventory().add(ItemId::Oxygen, 60);
    player.inventory().add(ItemId::LaunchFuel, 2);
    shipInventory.configure(InventoryKind::Ship, 32, "SCHIFF");
    shipInventory.add(ItemId::Deuterium, 180);
    homeBase.configure("BASIS ALPHA", DVec3::zero());

    ship.configure(Ship::specificationFor(ShipClassId::Explorer, ShipSize::Medium));
    flightController.setSpecification(ship.specification().flight);
    flight.fuelKilograms = ship.specification().fuelCapacity;
    hyperdrive.setSpecification(HyperdriveSystem::specificationFor(ship.specification().hyperdrive));

    JonBridgeSettings bridge;
    bridge.host = "127.0.0.1";
    bridge.port = 8756;
    jon.initialize(options.universeSeed, bridge);

    coop.configure(options.coopHost, options.coopPort, options.playerName);
    if (options.coopHostSession) coop.hostGame(options.universeSeed);
    else if (!options.coopJoinCode.empty()) coop.joinGame(options.coopJoinCode);

    currentGalaxy = galaxyGenerator.generate(universeSeed, 0);
    mainMenu.initialize(voidHeart);
    mainMenu.seekCycle(options.menuStartSeconds);
    frameClock.reset();

    const std::string savePath = FileSystem::joinPath(FileSystem::executableDirectory(), "..\\saves\\slot0.sfsave");
    saveAvailable = FileSystem::exists(savePath);

    enterState(GameStateId::MainMenu);
    if (options.skipMenu) {
        enterState(GameStateId::Loading);
        enterState(GameStateId::Flight);
    }
    if (options.startLanded) {
        f64 distance = 0.0;
        const u32 candidate = nearestLandablePlanet(distance);
        if (candidate != kInvalidIndex32) beginLanding(candidate);
    }
    logInfo("app", "STARFALL bereit, Seed 0x%llx", static_cast<unsigned long long>(options.universeSeed));
    return statusOk();
}

void GameApp::shutdown() {
    coop.leave();
    jon.shutdown();
    planetSurface.release();
    terrainPass.release();
    compositeShader.release();
    fullscreenTriangle.release();
    sceneTarget.release();
    postProcessPass.release();
    blackHolePass.release();
    bodyPass.release();
    starfieldPass.release();
    userInterface.release();
    window.close();
    globalFrameAllocator().release();
    JobSystem::instance().shutdown();
    logInfo("app", "Beendet nach %llu Bildern", static_cast<unsigned long long>(renderedFrames));
}

void GameApp::applyQualitySettings() {
    const QualitySettings& settings = quality.settings();

    const u32 targetWidth = maxValue<u32>(320, static_cast<u32>(static_cast<f32>(window.width()) *
                                                                settings.sceneResolutionScale));
    const u32 targetHeight = maxValue<u32>(180, static_cast<u32>(static_cast<f32>(window.height()) *
                                                                 settings.sceneResolutionScale));
    if (!sceneTarget.valid() || sceneTarget.width() != targetWidth || sceneTarget.height() != targetHeight) {
        sceneTarget.create(targetWidth, targetHeight, GL_RGBA16F, true);
    }

    bodyPass.applyDetail(settings.sphereSubdivisions, settings.atmosphereEnabled, settings.ringsEnabled);
}

void GameApp::handleQualityInput() {
    const Input& input = window.input();
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
    if (input.keyPressed(Key::F7)) {
        quality.setAutomatic(!quality.automatic());
    }
    if (input.keyPressed(Key::F8)) {
        quality.setAutomatic(false);
        quality.setPreset(QualityPreset::Sparmodus);
        applyQualitySettings();
    }
}

u32 GameApp::nearestLandablePlanet(f64& distanceOut) const {
    const DVec3 systemCenter(kVoidHeartSystemDistance, 0.0, 0.0);
    u32 best = kInvalidIndex32;
    distanceOut = 1.0e30;
    for (usize index = 0; index < currentSystem.planets.size(); ++index) {
        const PlanetProfile& planet = currentSystem.planets[index];
        if (planet.planetClass == PlanetClass::GasGiant || planet.planetClass == PlanetClass::IceGiant) continue;
        const f64 angle = universeSeconds / maxValue(planet.orbitalPeriodSeconds, 1.0) * kTwoPiDouble +
                          planet.meanAnomalyAtEpoch;
        const DVec3 position = systemCenter + DVec3(std::cos(angle),
                                                    std::sin(angle) * std::sin(planet.orbitalInclinationRadians),
                                                    std::sin(angle)) *
                                                  planet.semiMajorAxisMeters;
        const f64 distance = length(position - flight.position) - planet.radiusMeters;
        if (distance >= distanceOut) continue;
        distanceOut = distance;
        best = static_cast<u32>(index);
    }
    return best;
}

void GameApp::beginLanding(u32 planetIndex) {
    if (planetIndex >= currentSystem.planets.size()) return;
    const PlanetProfile& planet = currentSystem.planets[planetIndex];

    const DVec3 systemCenter(kVoidHeartSystemDistance, 0.0, 0.0);
    const f64 angle = universeSeconds / maxValue(planet.orbitalPeriodSeconds, 1.0) * kTwoPiDouble +
                      planet.meanAnomalyAtEpoch;
    const DVec3 planetPosition = systemCenter + DVec3(std::cos(angle),
                                                      std::sin(angle) * std::sin(planet.orbitalInclinationRadians),
                                                      std::sin(angle)) *
                                                    planet.semiMajorAxisMeters;

    landingBody.configure(planet, planetPosition);
    const u32 maximumLevel = static_cast<u32>(clampValue(std::log2(planet.radiusMeters / 24.0), 8.0, 17.0));
    planetSurface.configure(landingBody, maximumLevel,
                            quality.settings().preset == QualityPreset::Sparmodus ? 1.0f : 1.5f);

    DVec3 landingDirection = normalize(flight.position - planetPosition);
    if (lengthSquared(landingDirection) < 0.5) landingDirection = DVec3::unitY();

    const DVec3 systemStar = currentSystem.stars.empty() ? systemCenter
                                                         : systemCenter + currentSystem.stars[0].localOffset;
    const DVec3 sunward = normalize(systemStar - planetPosition);
    if (dot(landingDirection, sunward) < 0.35) {
        const DVec3 lateral = landingDirection - sunward * dot(landingDirection, sunward);
        landingDirection = lengthSquared(lateral) > 1.0e-6 ? normalize(sunward * 1.6 + normalize(lateral) * 0.7)
                                                           : sunward;
    }

    shipLandingPosition = landingBody.center() + landingDirection * (landingBody.radiusAt(landingDirection) + 3.0);
    flight.position = shipLandingPosition;
    flight.velocity = DVec3::zero();
    landedPlanetIndex = planetIndex;

    player.spawnOn(landingBody, landingDirection);
    homeBase.configure("BASIS " + planet.name, player.localPosition());
    floatingOrigin.forceOrigin(player.localPosition());
    surfaceDayPhase = std::fmod(universeSeconds / maxValue(landingBody.dayLengthSeconds(), 1.0), 1.0);
    planetSurface.prime(player.localPosition(), surfaceDayPhase,
                        quality.settings().preset == QualityPreset::Sparmodus ? 120u : 260u);
    logInfo("planet", "Terrain bereit: %u Kacheln, tiefste Stufe %u von %u, feinste Kachel %.1f m",
            planetSurface.leafCount(), planetSurface.deepestLevel(), maximumLevel,
            planetSurface.finestChunkMeters());

    marketAvailable = false;
    for (const StationProfile& station : currentSystem.stations) {
        if (station.orbitingPlanetIndex != planetIndex) continue;
        stationMarket.configure(station.seed, station.name, station.owner);
        marketAvailable = true;
        break;
    }
    if (!marketAvailable) {
        stationMarket.configure(planet.seed ^ 0x4D4B54ull, planet.name + " Handelsposten",
                                currentSystem.dominantCulture);
        marketAvailable = true;
    }

    const u64 planetKey = hashCombine(planet.seed, 0x504C4E54ull);
    if (discoveries.record(DiscoveryKind::Planet, planetKey, planet.name, currentSystem.name,
                           PlanetGenerator::planetClassName(planet.planetClass), 8500.0)) {
        jon.announceDiscovery(planet.name, jonContext);
    }

    footFrame.statusMessage = "GELANDET AUF " + planet.name;
    statusMessageTimer = 5.0;
    enterState(GameStateId::OnFoot);
}

void GameApp::leaveSurface() {
    if (landedPlanetIndex == kInvalidIndex32) return;
    const DVec3 up = landingBody.upAt(flight.position);
    flight.position = landingBody.center() + up * (landingBody.maximumRadius() + landingBody.atmosphereTopRadius());
    flight.velocity = up * 1200.0;
    floatingOrigin.forceOrigin(flight.position);
    planetSurface.release();
    landedPlanetIndex = kInvalidIndex32;
    activePanel = FootPanel::None;
    enterState(GameStateId::Flight);
}

void GameApp::exitShip() {
    if (landedPlanetIndex == kInvalidIndex32) return;
    const DVec3 direction = landingBody.upAt(shipLandingPosition);
    player.spawnOn(landingBody, direction);
    enterState(GameStateId::OnFoot);
}

void GameApp::enterShip() {
    if (landedPlanetIndex == kInvalidIndex32) return;
    if (player.inventory().count(ItemId::LaunchFuel) == 0) {
        footFrame.statusMessage = "STARTBRENNSTOFF FEHLT";
        statusMessageTimer = 4.0;
        return;
    }
    player.inventory().remove(ItemId::LaunchFuel, 1);
    leaveSurface();
}

void GameApp::enterState(GameStateId next) {
    if (currentState == next) return;
    previousState = currentState;
    currentState = next;

    const bool wantCapture = next == GameStateId::Flight || next == GameStateId::OnFoot;
    if (wantCapture != cursorCaptured) {
        cursorCaptured = wantCapture;
        window.setCursorCaptured(wantCapture);
    }
    if (next == GameStateId::Loading) loadStartSystem();
}

void GameApp::loadStartSystem() {
    playerSystem = SystemCoord();
    playerSystem.x = 0;
    playerSystem.y = 0;
    playerSystem.z = 0;

    currentSystem = systemGenerator.generate(universeSeed, currentGalaxy.seed, playerSystem);
    currentSystem.containsVoidHeart = currentGalaxy.hostsVoidHeart;
    voidHeart.configure(playerSystem, DVec3(0.0, 0.0, 0.0));

    const f64 startRadius = launch.startInVoidZone ? voidHeart.gravitationalRadiusMeters() * 220.0
                                                   : kVoidHeartSystemDistance;
    flight = FlightState();
    flight.position = DVec3(startRadius, voidHeart.gravitationalRadiusMeters() * 12.0, startRadius * 0.35);
    flight.fuelKilograms = ship.specification().fuelCapacity;
    flight.orientation = Quat::identity();

    const f64 orbitSpeed = voidHeart.orbitalSpeedAt(length(flight.position));
    const DVec3 radial = normalize(flight.position);
    const DVec3 tangential = normalize(cross(DVec3::unitY(), radial));
    flight.velocity = tangential * orbitSpeed;

    floatingOrigin.forceOrigin(flight.position);
    galaxyMap.initialize(currentGalaxy, playerSystem);
    buildMapMarkers();

    std::vector<HyperRouteSolver::StarNode> nodes;
    for (const MapMarker& marker : mapMarkers) {
        HyperRouteSolver::StarNode node;
        node.coordinate = marker.coordinate;
        node.hazardRating = marker.dangerRating;
        node.hasRefuel = marker.hasStation;
        node.surveyed = marker.visited;
        nodes.push_back(node);
    }
    routeSolver.setNodes(nodes);

    universeSeconds = 0.0;
    personalSeconds = 0.0;
    oxygenFraction = 1.0;
    logInfo("app", "System %s geladen, %u Planeten", currentSystem.name.c_str(),
            static_cast<u32>(currentSystem.planets.size()));
}

void GameApp::buildMapMarkers() {
    mapMarkers.clear();
    const std::vector<SystemCoord> neighbours =
        GalaxyGenerator::sampleNeighbourhood(currentGalaxy, playerSystem, 46, quality.settings().mapStarBudget);

    for (const SystemCoord& coordinate : neighbours) {
        MapMarker marker;
        marker.coordinate = coordinate;
        const u64 seed = universeSeed.systemSeed(currentGalaxy.seed, coordinate);
        Random random(seed);
        const StarProfile star = StarSystemGenerator::makeStar(hashCombine(seed, 0x5741u), StarClass::Count);
        marker.label = star.name;
        marker.color = star.lightColor;
        marker.magnitude = static_cast<f32>(clampValue(0.6 + std::log10(maxValue(star.luminositySolar, 1.0e-4)) * 0.35,
                                                       0.4, 3.2));
        marker.visited = coordinate == playerSystem;
        marker.habitable = random.chance(0.22f);
        marker.hasStation = random.chance(0.26f);
        marker.dangerRating = static_cast<f32>(random.nextDouble() * 0.8);
        marker.isVoidHeart = coordinate.x == 0 && coordinate.y == 0 && coordinate.z == 0;
        mapMarkers.push_back(marker);
    }

    bool hasHome = false;
    for (const MapMarker& marker : mapMarkers) {
        if (marker.coordinate == playerSystem) hasHome = true;
    }
    if (!hasHome) {
        MapMarker marker;
        marker.coordinate = playerSystem;
        marker.label = currentSystem.name;
        marker.color = currentSystem.stars.empty() ? Vec3(1.0f) : currentSystem.stars[0].lightColor;
        marker.magnitude = 2.4f;
        marker.visited = true;
        marker.isVoidHeart = true;
        mapMarkers.push_back(marker);
    }
    galaxyMap.setMarkers(mapMarkers);
}

DVec3 GameApp::aggregateGravity(const DVec3& position) const {
    DVec3 total = DVec3::zero();
    total += OrbitalMechanics::gravitationalAcceleration(position, voidHeart.localPosition(),
                                                         voidHeart.massKilograms(),
                                                         voidHeart.horizonRadiusMeters() * 0.5);
    for (const StarProfile& star : currentSystem.stars) {
        total += OrbitalMechanics::gravitationalAcceleration(position, star.localOffset + DVec3(kVoidHeartSystemDistance, 0.0, 0.0),
                                                             star.massSolar * kSolarMass, star.radiusMeters);
    }
    return total;
}

void GameApp::gatherFlightInput() {
    const Input& input = window.input();
    FlightInput command;
    command.throttle = input.axis(Key::W, Key::S);
    command.strafeHorizontal = input.axis(Key::D, Key::A) * 0.0f;
    command.yaw = -input.axis(Key::D, Key::A);
    command.roll = input.axis(Key::E, Key::Q);
    command.afterburner = input.keyDown(Key::LeftShift);
    command.brake = input.keyDown(Key::LeftControl);
    command.holdThrust = input.keyDown(Key::Space);
    command.zeroThrust = input.keyPressed(Key::X);

    if (cursorCaptured) {
        const Vec2 delta = input.mouseDelta();
        command.pitch = clampValue(-delta.y * 0.0042f, -1.0f, 1.0f);
        command.yaw += clampValue(-delta.x * 0.0042f, -1.0f, 1.0f);
    }
    flightController.applyInput(command);

    if (input.keyPressed(Key::F1)) flightController.setMode(FlightMode::Newtonian);
    if (input.keyPressed(Key::F2)) flightController.setMode(FlightMode::Assisted);
    if (input.keyPressed(Key::F3)) flightController.setMode(FlightMode::Atmospheric);
    if (input.keyPressed(Key::F4)) flightController.setMode(FlightMode::Docking);

    if (input.keyPressed(Key::C)) ship.beginScan(0.5);
    if (input.keyDown(Key::Comma)) ship.tuneScanner(-0.35 * frameClock.deltaSeconds());
    if (input.keyDown(Key::Period)) ship.tuneScanner(0.35 * frameClock.deltaSeconds());

    if (input.keyPressed(Key::Digit1)) ship.fireGroup(0);
    if (input.keyPressed(Key::Digit2)) ship.fireGroup(1);
    if (input.keyPressed(Key::Digit3)) ship.fireGroup(2);
    if (input.keyPressed(Key::Digit4)) ship.fireGroup(3);
    if (input.keyPressed(Key::Digit5)) ship.fireGroup(4);

    if (input.keyPressed(Key::J)) jon.ask("Wie ist die Lage?", jonContext);
    if (input.keyPressed(Key::K)) jon.requestMission(jonContext);
    if (input.keyPressed(Key::H) && hyperdriveState.phase == HyperdrivePhase::Idle) requestHyperjump();
}

f64 GameApp::alignmentToDestinationDegrees() const {
    const SystemCoord destination = hyperdriveState.destination;
    const DVec3 direction(static_cast<f64>(destination.x - playerSystem.x),
                          static_cast<f64>(destination.y - playerSystem.y),
                          static_cast<f64>(destination.z - playerSystem.z));
    if (lengthSquared(direction) <= 0.0) return 0.0;
    const DVec3 target = normalize(direction);
    const DVec3 heading = fromFloat(flight.orientation.forward());
    const f64 alignment = clampValue(dot(target, heading), -1.0, 1.0);
    return std::acos(alignment) * (180.0 / kPiDouble);
}

void GameApp::requestHyperjump() {
    if (!galaxyMap.hasSelection()) return;
    const SystemCoord destination = galaxyMap.selection();
    const f64 distance = HyperdriveSystem::distanceLightYears(playerSystem, destination);
    const f64 massLock = clampValue(voidHeart.gravitationalRadiusMeters() * 600.0 /
                                        maxValue(length(flight.position), 1.0),
                                    0.0, 1.0);
    const JumpDenialReason reason =
        hyperdrive.evaluateJump(playerSystem, destination, flight.fuelKilograms, ship.massTonnes(), massLock,
                                ship.driveIntegrity(), voidState.voidDriveRequired);
    if (reason != JumpDenialReason::None) {
        routeDenialText = HyperdriveSystem::denialReasonText(reason);
        JonUtterance utterance;
        utterance.text = routeDenialText;
        utterance.urgency = JonUrgency::Warning;
        jon.say(utterance);
        return;
    }
    routeDenialText.clear();
    hyperdrive.beginJump(hyperdriveState, destination, distance, voidState.hyperdriveChargeMultiplier);
}

void GameApp::refreshJonContext() {
    jonContext.systemName = currentSystem.name;
    jonContext.starClass = currentSystem.stars.empty()
                               ? "unbekannt"
                               : StarSystemGenerator::starClassName(currentSystem.stars[0].starClass);
    jonContext.speedMetresPerSecond = length(flight.velocity);
    jonContext.hullIntegrity = ship.hullIntegrity();
    jonContext.shieldCharge = ship.totalShieldCharge();
    jonContext.fuelKilograms = flight.fuelKilograms;
    jonContext.fuelCapacity = ship.specification().fuelCapacity;
    jonContext.heatFraction = ship.heatFraction();
    jonContext.oxygenFraction = oxygenFraction;
    jonContext.timeDilation = voidState.timeDilation;
    jonContext.voidZone = voidState.zone;
    jonContext.hullStress = flight.hullStress;
    jonContext.tidalStress = voidState.tidalStressPerSecond;
    jonContext.communicationBlackout = flight.communicationBlackout;
    jonContext.voidDriveInstalled = hyperdrive.driveSpecification().worksInVoidZone;
    jonContext.discoveredStations = voidStations.discoveredCount();
    jonContext.completedEndgameMissions = endgame.completedCount();
    jonContext.researchTier = researchTier;

    f64 nearestDistance = 1.0e30;
    jonContext.nearestBodyName = "THE VOID HEART";
    jonContext.planetClass = "Supermassives Schwarzes Loch";
    jonContext.distanceToNearestBodyMeters = voidState.distanceMeters;
    jonContext.habitability = 0.0;
    jonContext.radiationSieverts = 0.0;
    jonContext.surfaceTemperatureKelvin = 0.0;
    jonContext.surfaceGravity = 0.0;

    for (usize index = 0; index < currentSystem.planets.size(); ++index) {
        const PlanetProfile& planet = currentSystem.planets[index];
        const f64 angle = universeSeconds / maxValue(planet.orbitalPeriodSeconds, 1.0) * kTwoPiDouble +
                          planet.meanAnomalyAtEpoch;
        const DVec3 position = DVec3(std::cos(angle), std::sin(angle) * std::sin(planet.orbitalInclinationRadians),
                                     std::sin(angle)) *
                                   planet.semiMajorAxisMeters +
                               DVec3(kVoidHeartSystemDistance, 0.0, 0.0);
        const f64 distance = length(position - flight.position);
        if (distance >= nearestDistance) continue;
        nearestDistance = distance;
        jonContext.nearestBodyName = planet.name;
        jonContext.planetClass = PlanetGenerator::planetClassName(planet.planetClass);
        jonContext.distanceToNearestBodyMeters = distance - planet.radiusMeters;
        jonContext.habitability = planet.habitabilityIndex();
        jonContext.radiationSieverts = planet.radiationLevelSieverts;
        jonContext.surfaceTemperatureKelvin = planet.meanSurfaceTemperatureKelvin;
        jonContext.surfaceGravity = planet.surfaceGravity;
    }
}

void GameApp::stepSimulation(f64 stepSeconds) {
    voidState = voidHeart.evaluate(flight.position);
    const f64 personalStep = stepSeconds * maxValue(voidState.timeDilation, 0.0);
    universeSeconds += stepSeconds;
    personalSeconds += personalStep;

    const DVec3 gravity = aggregateGravity(flight.position);
    flightController.step(flight, gravity, stepSeconds);

    if (voidState.frameDraggingAngularRate > 0.0) {
        const DVec3 radial = flight.position - voidHeart.localPosition();
        const DVec3 spinAxis = DVec3::unitY();
        const DVec3 drag = cross(spinAxis, radial) * voidState.frameDraggingAngularRate;
        flight.velocity += drag * stepSeconds;
    }

    ship.step(stepSeconds, voidState.shieldDrainPerSecond, voidState.tidalStressPerSecond * 0.0002);
    ship.setCargoTonnes(exoticResources.totalMassKilograms() / 1000.0);

    hyperdrive.update(hyperdriveState, stepSeconds, alignmentToDestinationDegrees(), universeSeed.value());
    if (hyperdriveState.phase == HyperdrivePhase::Exiting && playerSystem != hyperdriveState.destination) {
        playerSystem = hyperdriveState.destination;
        currentSystem = systemGenerator.generate(universeSeed, currentGalaxy.seed, playerSystem);
        flight.position = DVec3(kVoidHeartSystemDistance * 1.2, 0.0, 0.0);
        flight.velocity = DVec3::zero();
        floatingOrigin.forceOrigin(flight.position);
        buildMapMarkers();
    }

    for (usize index = 0; index < voidStations.stations().size(); ++index) {
        const VoidStationProfile& station = voidStations.stations()[index];
        const DVec3 position = station.positionAt(voidHeart, universeSeconds);
        if (length(position - flight.position) > station.radiusMeters * 40.0) continue;
        if (voidStations.markDiscovered(static_cast<VoidStationId>(index))) {
            jon.announceDiscovery(station.name, jonContext);
        }
    }

    if (voidState.zone <= VoidZone::Distortion) {
        for (u32 index = 0; index < static_cast<u32>(ExoticResourceId::Count); ++index) {
            const ExoticResourceId id = static_cast<ExoticResourceId>(index);
            const f64 rate = ExoticResourceLedger::harvestRatePerSecond(id, voidState.radiusInGravitationalRadii,
                                                                       ship.scannerState().lockQuality + 0.4);
            exoticResources.add(id, rate * stepSeconds);
        }
    }

    oxygenFraction = clampValue(oxygenFraction - 0.0004 * stepSeconds, 0.0, 1.0);
    researchProgress += personalStep * 0.0016 * (1.0 + exoticResources.totalValue() * 1.0e-7);
    researchTier = clampValue(static_cast<u32>(1 + researchProgress), 1u, 5u);
    endgame.evaluateUnlocks(researchTier, recognizedCivilizations, voidStations);

    if (voidState.zone == VoidZone::EventHorizon) {
        endgame.completeMission(EndgameMissionId::BeyondTheVoid);
    }

    CoopLocalState coopState;
    coopState.position = flight.position;
    coopState.velocity = flight.velocity;
    coopState.orientation = flight.orientation;
    coopState.system = playerSystem;
    coopState.timeDilation = voidState.timeDilation;
    coopState.hullIntegrity = ship.hullIntegrity();
    coop.pushLocalState(coopState);
    coop.update(stepSeconds);

    refreshJonContext();
    jon.update(jonContext, stepSeconds);
    floatingOrigin.update(flight.position);
}

void GameApp::updateMenu(f64 stepSeconds) {
    mainMenu.update(stepSeconds, window.input());
    switch (mainMenu.consumeAction()) {
        case MainMenuAction::Continue:
        case MainMenuAction::NewGame:
            enterState(GameStateId::Loading);
            enterState(GameStateId::Flight);
            break;
        case MainMenuAction::Multiplayer:
            coop.hostGame(universeSeed.value());
            mainMenu.setSubmenuText("KOOP-SITZUNG WIRD GEOEFFNET");
            break;
        case MainMenuAction::Catalogue:
            mainMenu.setSubmenuText(std::string("GALAXIE ") + currentGalaxy.name + " - " +
                                    GalaxyGenerator::galaxyTypeName(currentGalaxy.type));
            break;
        case MainMenuAction::Settings:
            mainMenu.setSubmenuText(std::string("GRAFIK ") + QualitySettings::presetName(quality.preset()) +
                                    "  F5 NIEDRIGER  F6 HOEHER  F7 AUTO  F8 SPARMODUS  F11 VOLLBILD");
            break;
        case MainMenuAction::Quit:
            window.requestClose();
            break;
        default:
            break;
    }
}

void GameApp::updateFlight(f64 stepSeconds) {
    gatherFlightInput();
    const Input& input = window.input();
    if (input.keyPressed(Key::M)) enterState(GameStateId::GalaxyMap);
    if (input.keyPressed(Key::Escape)) enterState(GameStateId::MainMenu);
    if (input.keyPressed(Key::L)) {
        f64 distance = 0.0;
        const u32 candidate = nearestLandablePlanet(distance);
        if (candidate == kInvalidIndex32) {
            footFrame.statusMessage = "KEIN LANDBARER KOERPER IN REICHWEITE";
            statusMessageTimer = 4.0;
        } else if (distance > currentSystem.planets[candidate].radiusMeters * 60.0) {
            JonUtterance utterance;
            utterance.text = "Zu weit weg fuer einen Anflug. Erst naeher heran, dann L.";
            utterance.urgency = JonUrgency::Notice;
            jon.say(utterance);
        } else {
            beginLanding(candidate);
        }
    }
    (void)stepSeconds;
}

EnvironmentReading GameApp::readEnvironment() const {
    EnvironmentReading environment;
    if (landedPlanetIndex == kInvalidIndex32) return environment;

    const DVec3 up = landingBody.upAt(player.localPosition());
    const SurfaceSample sample = landingBody.sampleSurface(up, surfaceDayPhase);
    const f64 altitude = landingBody.altitudeAt(player.localPosition());

    environment.temperatureKelvin = sample.temperatureKelvin;
    environment.radiationSieverts = landingBody.radiationAt(up, surfaceDayPhase);
    environment.toxicity = landingBody.toxicityAt(up);
    environment.pressureBar = landingBody.atmosphericDensityAt(maxValue(altitude, 0.0)) / 1.225;
    environment.oxygenFraction = landingBody.profile().oxygenFraction;
    environment.underWater = sample.underWater && altitude < 0.5;
    environment.inShelter = homeBase.sheltersPoint(player.localPosition()) ||
                            length(player.localPosition() - shipLandingPosition) < 6.0;
    return environment;
}

DVec3 GameApp::planetLocalOfPlayer() const {
    return player.localPosition();
}

void GameApp::gatherFootInput(FootInput& out) {
    const Input& input = window.input();
    out.forward = input.axis(Key::W, Key::S);
    out.strafe = input.axis(Key::D, Key::A);
    out.sprint = input.keyDown(Key::LeftShift);
    out.crouch = input.keyDown(Key::LeftControl);
    out.jump = input.keyPressed(Key::Space);
    out.jetpack = input.keyDown(Key::Space) && !out.jump;
    out.useTool = input.mouseDown(MouseButton::Left);
    out.interact = input.keyPressed(Key::E);

    if (cursorCaptured && activePanel == FootPanel::None) {
        const Vec2 delta = input.mouseDelta();
        out.lookYaw = clampValue(delta.x * 0.0032f, -0.6f, 0.6f);
        out.lookPitch = clampValue(-delta.y * 0.0032f, -0.6f, 0.6f);
    }
}

void GameApp::applyMiningBeam(f64 stepSeconds) {
    if (landedPlanetIndex == kInvalidIndex32) return;
    ResourceNode* node = planetSurface.nearestResource(player.eyePosition() + player.lookDirection() * 4.0, 7.0);
    if (!node) {
        const DVec3 up = landingBody.upAt(player.localPosition());
        const ItemId ambient = landingBody.dominantResource(up);
        if (player.beamCharge() > 1.2f) return;
        player.setBeamCharge(player.beamCharge() + static_cast<f32>(stepSeconds * 0.5));
        const u32 gained = player.inventory().add(ambient, 1);
        if (gained == 0) {
            footFrame.statusMessage = "ANZUG VOLL";
            statusMessageTimer = 3.0;
        }
        return;
    }

    player.setBeamCharge(player.beamCharge() + static_cast<f32>(stepSeconds * 0.7));
    if (player.beamCharge() > 1.25f) {
        footFrame.statusMessage = "STRAHL UEBERHITZT";
        statusMessageTimer = 2.5;
        return;
    }

    const u32 amount = static_cast<u32>(maxValue(1.0, stepSeconds * 42.0));
    const u32 available = minValue(node->remainingUnits, amount);
    const u32 stored = player.inventory().add(node->resource, available);
    node->remainingUnits -= stored;
    if (node->remainingUnits == 0) node->depleted = true;

    if (stored > 0) {
        const u64 key = hashCombine(landingBody.profile().seed, static_cast<u64>(node->resource) + 0x4D494Eull);
        discoveries.record(DiscoveryKind::Mineral, key,
                           ItemDatabase::instance().definition(node->resource).name, currentSystem.name,
                           "Oberflaechenvorkommen", 1200.0);
    }
}

void GameApp::applyScanner(f64 stepSeconds) {
    if (landedPlanetIndex == kInvalidIndex32) return;
    footFrame.scanning = true;
    footFrame.scanProgress = clampValue(footFrame.scanProgress + stepSeconds * 1.6, 0.0, 1.0);
    if (footFrame.scanProgress < 1.0) return;

    footFrame.scanProgress = 0.0;
    footFrame.scanning = false;

    const DVec3 focus = player.eyePosition() + player.lookDirection() * 12.0;
    CreatureInstance* creature = planetSurface.nearestCreature(focus, 42.0);
    if (creature && !creature->scanned) {
        creature->scanned = true;
        const u64 key = hashCombine(landingBody.profile().seed, creature->speciesIndex + 0x4641554Eull);
        const std::string name = DiscoveryCatalog::generateCreatureName(landingBody.profile().seed,
                                                                       creature->speciesIndex);
        if (discoveries.record(DiscoveryKind::Fauna, key, name, currentSystem.name, "Landlebewesen", 3400.0)) {
            footFrame.statusMessage = "ART ERFASST: " + name;
            statusMessageTimer = 5.0;
            jon.announceDiscovery(name, jonContext);
        }
        return;
    }

    if (!planetSurface.scatter().empty()) {
        const ScatterInstance& plant = planetSurface.scatter()[0];
        const u64 key = hashCombine(landingBody.profile().seed, plant.kind + 0x464C4F52ull);
        const std::string name = DiscoveryCatalog::generatePlantName(landingBody.profile().seed, plant.kind);
        if (discoveries.record(DiscoveryKind::Flora, key, name, currentSystem.name, "Bodenvegetation", 2100.0)) {
            footFrame.statusMessage = "FLORA ERFASST: " + name;
            statusMessageTimer = 5.0;
            return;
        }
    }

    footFrame.statusMessage = "NICHTS NEUES IN REICHWEITE";
    statusMessageTimer = 3.0;
}

void GameApp::applyBuildAction(bool place, bool remove) {
    if (landedPlanetIndex == kInvalidIndex32 || panelParts.empty()) return;
    const BuildPartId partId = panelParts[minValue(selectedPartIndex, static_cast<u32>(panelParts.size() - 1))]->id;
    const DVec3 target = player.localPosition() + player.lookDirection() * 6.0;
    const DVec3 snapped = homeBase.snapPosition(landingBody, target, partId);

    const PlacementResult result =
        homeBase.evaluatePlacement(landingBody, partId, snapped, player.inventory(), researchTier);
    footFrame.buildMessage = BaseGrid::placementMessage(result);

    if (place && result == PlacementResult::Ok) {
        homeBase.place(landingBody, partId, snapped, player.headingYaw(), player.inventory(), researchTier);
        footFrame.statusMessage = "BAUTEIL GESETZT";
        statusMessageTimer = 2.0;
    }
    if (remove && homeBase.removeNearest(target, 8.0, player.inventory())) {
        footFrame.statusMessage = "BAUTEIL ABGEBAUT";
        statusMessageTimer = 2.0;
    }
}

void GameApp::refreshPanelLists() {
    panelRecipes = RecipeDatabase::instance().craftableFrom(player.inventory(), researchTier);
    if (panelRecipes.empty()) panelRecipes = RecipeDatabase::instance().ofKind(RecipeKind::Handcraft);
    panelParts.clear();
    for (const BuildPartDefinition& definition : BuildPartCatalog::instance().all()) {
        if (definition.requiredResearchTier <= researchTier) panelParts.push_back(&definition);
    }
    if (selectedRecipeIndex >= panelRecipes.size()) selectedRecipeIndex = 0;
    if (selectedPartIndex >= panelParts.size()) selectedPartIndex = 0;
    const usize offerCount = stationMarket.entries().size();
    if (offerCount > 0 && selectedTradeIndex >= offerCount) selectedTradeIndex = 0;
}

void GameApp::updateOnFoot(f64 stepSeconds) {
    const Input& input = window.input();

    if (input.keyPressed(Key::Tab)) {
        activePanel = activePanel == FootPanel::Inventory ? FootPanel::None : FootPanel::Inventory;
    }
    if (input.keyPressed(Key::X)) {
        activePanel = activePanel == FootPanel::Crafting ? FootPanel::None : FootPanel::Crafting;
    }
    if (input.keyPressed(Key::B)) {
        activePanel = activePanel == FootPanel::Build ? FootPanel::None : FootPanel::Build;
        player.setToolMode(activePanel == FootPanel::Build ? ToolMode::BuildMode : ToolMode::MiningBeam);
    }
    if (input.keyPressed(Key::T) && marketAvailable) {
        activePanel = activePanel == FootPanel::Trade ? FootPanel::None : FootPanel::Trade;
    }
    if (input.keyPressed(Key::K)) {
        activePanel = activePanel == FootPanel::Catalog ? FootPanel::None : FootPanel::Catalog;
    }
    if (input.keyPressed(Key::Q)) player.cycleTool();
    if (input.keyPressed(Key::J)) jon.ask("Wie ist die Lage?", jonContext);
    if (input.keyPressed(Key::M)) enterState(GameStateId::GalaxyMap);
    if (input.keyPressed(Key::Escape)) {
        if (activePanel != FootPanel::None) activePanel = FootPanel::None;
        else enterState(GameStateId::MainMenu);
    }

    window.setCursorCaptured(activePanel == FootPanel::None);
    cursorCaptured = activePanel == FootPanel::None;

    const bool up = input.keyPressed(Key::Up);
    const bool down = input.keyPressed(Key::Down);
    const bool confirm = input.keyPressed(Key::Enter);
    const bool cancel = input.keyPressed(Key::Backspace);

    if (activePanel == FootPanel::Crafting && !panelRecipes.empty()) {
        if (down) selectedRecipeIndex = (selectedRecipeIndex + 1) % static_cast<u32>(panelRecipes.size());
        if (up) selectedRecipeIndex = (selectedRecipeIndex + static_cast<u32>(panelRecipes.size()) - 1) %
                                      static_cast<u32>(panelRecipes.size());
        if (confirm) {
            const Recipe& recipe = *panelRecipes[selectedRecipeIndex];
            if (performCraft(recipe, player.inventory(), researchTier)) {
                footFrame.statusMessage = "HERGESTELLT: " + recipe.name;
                statusMessageTimer = 3.0;
            } else {
                footFrame.statusMessage = "MATERIAL FEHLT";
                statusMessageTimer = 3.0;
            }
        }
    } else if (activePanel == FootPanel::Build && !panelParts.empty()) {
        if (down) selectedPartIndex = (selectedPartIndex + 1) % static_cast<u32>(panelParts.size());
        if (up) selectedPartIndex = (selectedPartIndex + static_cast<u32>(panelParts.size()) - 1) %
                                    static_cast<u32>(panelParts.size());
        applyBuildAction(input.mousePressed(MouseButton::Left), input.mousePressed(MouseButton::Right));
    } else if (activePanel == FootPanel::Trade && !stationMarket.entries().empty()) {
        const u32 offerCount = static_cast<u32>(stationMarket.entries().size());
        if (down) selectedTradeIndex = (selectedTradeIndex + 1) % offerCount;
        if (up) selectedTradeIndex = (selectedTradeIndex + offerCount - 1) % offerCount;
        const ItemId id = stationMarket.entries()[selectedTradeIndex].id;
        if (confirm && stationMarket.buy(id, 10, player.inventory(), credits)) {
            footFrame.statusMessage = "GEKAUFT";
            statusMessageTimer = 2.0;
        }
        if (cancel && stationMarket.sell(id, 10, player.inventory(), credits)) {
            footFrame.statusMessage = "VERKAUFT";
            statusMessageTimer = 2.0;
        }
    } else if (activePanel == FootPanel::Catalog) {
        if (input.keyPressed(Key::U)) {
            const f64 reward = discoveries.uploadAll();
            credits += reward;
            footFrame.statusMessage = "ENTDECKUNGEN GEMELDET";
            statusMessageTimer = 3.0;
        }
    } else if (activePanel == FootPanel::Inventory) {
        const ItemId consumables[] = {ItemId::LifeSupportGel, ItemId::HazardCapsule, ItemId::Ration,
                                      ItemId::Oxygen, ItemId::CondensedCarbon};
        const Key keys[] = {Key::Digit1, Key::Digit2, Key::Digit3, Key::Digit4, Key::Digit5};
        for (u32 index = 0; index < 5; ++index) {
            if (!input.keyPressed(keys[index])) continue;
            if (player.survival().consumeItem(consumables[index], player.inventory())) {
                footFrame.statusMessage = "VERBRAUCHT";
                statusMessageTimer = 2.0;
            }
        }
    }

    if (activePanel == FootPanel::None) {
        if (player.toolMode() == ToolMode::Scanner && input.mouseDown(MouseButton::Left)) {
            applyScanner(stepSeconds);
        } else {
            footFrame.scanning = false;
            footFrame.scanProgress = maxValue(footFrame.scanProgress - stepSeconds, 0.0);
        }
        if (player.toolMode() == ToolMode::MiningBeam && input.mouseDown(MouseButton::Left)) {
            applyMiningBeam(stepSeconds);
        }
        if (input.keyPressed(Key::E) && length(player.localPosition() - shipLandingPosition) < 12.0) {
            enterShip();
        }
    }
}

void GameApp::stepSurfaceSimulation(f64 stepSeconds) {
    if (landedPlanetIndex == kInvalidIndex32) return;

    universeSeconds += stepSeconds;
    personalSeconds += stepSeconds;
    surfaceDayPhase = std::fmod(universeSeconds / maxValue(landingBody.dayLengthSeconds(), 1.0), 1.0);

    FootInput command;
    gatherFootInput(command);
    if (activePanel != FootPanel::None) {
        command.forward = 0.0f;
        command.strafe = 0.0f;
        command.jump = false;
        command.jetpack = false;
    }

    player.step(landingBody, command, stepSeconds);

    const EnvironmentReading environment = readEnvironment();
    player.survival().step(stepSeconds, environment, command.sprint, command.jetpack);
    if (player.survival().dead()) {
        player.spawnOn(landingBody, landingBody.upAt(shipLandingPosition));
        footFrame.statusMessage = "ANZUG WIEDERHERGESTELLT AM SCHIFF";
        statusMessageTimer = 5.0;
    }

    planetSurface.update(player.localPosition(), surfaceDayPhase,
                         quality.settings().preset == QualityPreset::Sparmodus ? 3u : 8u, 1.0f);
    planetSurface.updateLife(stepSeconds, player.localPosition());
    stationMarket.step(stepSeconds);

    flight.position = shipLandingPosition;
    floatingOrigin.update(player.localPosition());
    statusMessageTimer = maxValue(statusMessageTimer - stepSeconds, 0.0);
    if (statusMessageTimer <= 0.0) footFrame.statusMessage.clear();

    coop.update(stepSeconds);
    refreshJonContext();
    jonContext.nearestBodyName = landingBody.profile().name;
    jonContext.planetClass = PlanetGenerator::planetClassName(landingBody.profile().planetClass);
    jonContext.oxygenFraction = player.survival().oxygenReserve();
    jonContext.surfaceTemperatureKelvin = environment.temperatureKelvin;
    jonContext.radiationSieverts = environment.radiationSieverts;
    jonContext.surfaceGravity = landingBody.profile().surfaceGravity;
    jon.update(jonContext, stepSeconds);

    refreshPanelLists();
}

void GameApp::updateGalaxyMap(f64 stepSeconds) {
    galaxyMap.update(stepSeconds, window.input(), window.width(), window.height());
    if (galaxyMap.consumeRouteRequest() && galaxyMap.hasSelection()) {
        activeRoute = routeSolver.solve(playerSystem, galaxyMap.selection(),
                                        hyperdrive.driveSpecification().rangeLightYears, flight.fuelKilograms,
                                        RoutePreference::Shortest);
        if (!activeRoute.reachable) routeDenialText = "Kein Pfad innerhalb der Sprungreichweite gefunden.";
    }
    if (galaxyMap.consumeJumpRequest()) requestHyperjump();
    if (window.input().keyPressed(Key::M) || window.input().keyPressed(Key::Escape)) {
        enterState(GameStateId::Flight);
    }
}

void GameApp::buildVisibleBodies() {
    visibleBodies.clear();
    const DVec3 systemCenter(kVoidHeartSystemDistance, 0.0, 0.0);

    for (const StarProfile& star : currentSystem.stars) {
        CelestialBodyDraw draw;
        draw.worldPosition = systemCenter + star.localOffset;
        draw.radiusMeters = star.radiusMeters;
        draw.primaryColor = star.lightColor;
        draw.secondaryColor = star.lightColor;
        draw.emissiveStrength = static_cast<f32>(clampValue(std::pow(star.luminositySolar, 0.25) * 9.0, 2.0, 34.0));
        draw.atmosphereDensity = 0.0f;
        draw.surfaceType = CelestialSurface::Star;
        draw.surfaceSeed = star.seed;
        visibleBodies.push_back(draw);
    }

    const usize bodyBudget = quality.settings().maximumVisibleBodies;
    for (const PlanetProfile& planet : currentSystem.planets) {
        if (visibleBodies.size() >= bodyBudget) break;
        const f64 angle = universeSeconds / maxValue(planet.orbitalPeriodSeconds, 1.0) * kTwoPiDouble +
                          planet.meanAnomalyAtEpoch;
        const DVec3 position = systemCenter + DVec3(std::cos(angle), std::sin(angle) * std::sin(planet.orbitalInclinationRadians),
                                                    std::sin(angle)) *
                                                  planet.semiMajorAxisMeters;
        const f64 distance = length(position - flight.position);
        if (distance > planet.radiusMeters * 8000.0) continue;
        const f64 rotationPhase = universeSeconds / maxValue(planet.rotationPeriodSeconds, 1.0) * kTwoPiDouble;
        visibleBodies.push_back(planet.toDrawParameters(position, rotationPhase));
    }

    for (usize index = 0; index < voidStations.stations().size(); ++index) {
        const VoidStationProfile& station = voidStations.stations()[index];
        const DVec3 position = station.positionAt(voidHeart, universeSeconds);
        if (length(position - flight.position) > station.radiusMeters * 4000.0) continue;
        CelestialBodyDraw draw;
        draw.worldPosition = position;
        draw.radiusMeters = station.radiusMeters;
        draw.primaryColor = Vec3(0.42f, 0.46f, 0.5f);
        draw.secondaryColor = Vec3(0.22f, 0.26f, 0.3f);
        draw.metallic = 0.72f;
        draw.roughness = 0.34f;
        draw.emissiveStrength = 0.12f;
        draw.atmosphereDensity = 0.0f;
        draw.surfaceType = CelestialSurface::Metal;
        draw.surfaceSeed = station.id == VoidStationId::LastLight ? 7777 : 4200 + index;
        visibleBodies.push_back(draw);
    }
}

void GameApp::renderScene(bool menuMode) {
    sceneTarget.bindForDrawing();
    sceneTarget.clear(0.0f, 0.0f, 0.0f, 1.0f, true);

    const QualitySettings& settings = quality.settings();

    StarfieldParameters starfield;
    starfield.elapsedSeconds = static_cast<f32>(universeSeconds);
    starfield.exposureScale = 1.0f;
    starfield.warpFactor = static_cast<f32>(hyperdriveState.warpFactor);
    starfield.warpDirection = flight.orientation.forward();
    starfield.skyDetail = menuMode ? maxValue(settings.skyDetail, 1) : settings.skyDetail;
    if (menuMode) {
        starfield.localStarIntensity = 0.0f;
        starfield.nebulaIntensity = 1.15f;
        starfield.galaxyIntensity = 1.05f;
        starfield.starIntensity = 1.35f;
        starfield.exposureScale = 2.6f;
    } else if (!currentSystem.stars.empty()) {
        const DVec3 starPosition = DVec3(kVoidHeartSystemDistance, 0.0, 0.0) + currentSystem.stars[0].localOffset;
        starfield.localStarDirection = normalize(starPosition - camera.position()).toFloat();
        starfield.localStarColor = currentSystem.stars[0].lightColor;
        const f64 distance = maxValue(length(starPosition - camera.position()), 1.0);
        starfield.localStarAngularRadius =
            static_cast<f32>(clampValue(currentSystem.stars[0].radiusMeters / distance, 0.0006, 0.10));
        starfield.localStarIntensity =
            static_cast<f32>(clampValue(currentSystem.stars[0].luminositySolar * 90.0 /
                                            maxValue(distance / kAstronomicalUnit, 0.1),
                                        1.0, 220.0));
    }
    starfieldPass.render(camera, starfield);

    const DVec3 blackHoleWorld = voidHeart.localPosition();
    const f64 distanceToHeart = length(camera.position() - blackHoleWorld);
    const bool renderHeart = distanceToHeart < voidHeart.influenceRadiusMeters() * 30.0;

    if (renderHeart) {
        BlackHoleRenderParameters parameters =
            voidHeart.renderParameters(blackHoleWorld, static_cast<f32>(universeSeconds),
                                       settings.blackHoleResolutionScale);
        parameters.resolutionScale = settings.blackHoleResolutionScale;
        parameters.maximumSteps = settings.blackHoleMaximumSteps;
        parameters.stepFraction = settings.blackHoleStepFraction;
        parameters.integratorOrder = settings.blackHoleIntegratorOrder;
        parameters.skyDetail = settings.skyDetail;
        parameters.jetStrength = settings.blackHoleJetStrength;
        if (menuMode) {
            parameters.resolutionScale = maxValue(parameters.resolutionScale, 0.42f);
            parameters.maximumSteps = maxValue(parameters.maximumSteps, 150u);
            parameters.skyDetail = maxValue(parameters.skyDetail, 1);
            parameters.jetStrength = maxValue(parameters.jetStrength, 0.85f);
        }
        blackHolePass.render(camera, parameters, sceneTarget.width(), sceneTarget.height());

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
    }

    CelestialLighting lighting;
    lighting.elapsedSeconds = static_cast<f32>(universeSeconds);
    if (!currentSystem.stars.empty()) {
        const DVec3 starPosition = DVec3(kVoidHeartSystemDistance, 0.0, 0.0) + currentSystem.stars[0].localOffset;
        lighting.starDirection = normalize(camera.position() - starPosition).toFloat();
        lighting.starColor = currentSystem.stars[0].lightColor;
        lighting.starIntensity = static_cast<f32>(clampValue(currentSystem.stars[0].luminositySolar * 2.4, 0.4, 40.0));
    }
    lighting.secondaryColor = Vec3(0.42f, 0.16f, 0.06f) * static_cast<f32>(clampValue(20.0 / maxValue(voidState.radiusInGravitationalRadii, 1.0), 0.0, 1.0));
    lighting.secondaryDirection = normalize(camera.position() - blackHoleWorld).toFloat();

    bodyPass.render(camera, visibleBodies, lighting);
    if (currentState == GameStateId::OnFoot) renderSurface();
}

void GameApp::renderSurface() {
    if (landedPlanetIndex == kInvalidIndex32) return;
    const QualitySettings& settings = quality.settings();
    const PlanetProfile& planet = landingBody.profile();

    const DVec3 systemCenter(kVoidHeartSystemDistance, 0.0, 0.0);
    const DVec3 starPosition = currentSystem.stars.empty() ? systemCenter
                                                           : systemCenter + currentSystem.stars[0].localOffset;
    const DVec3 up = landingBody.upAt(player.localPosition());
    const f64 sunElevation = landingBody.sunElevationAt(up, universeSeconds, starPosition);
    const f64 daylight = clampValue(sunElevation * 1.6 + 0.18, 0.0, 1.0);

    CelestialLighting lighting;
    lighting.elapsedSeconds = static_cast<f32>(universeSeconds);
    lighting.starDirection = (landingBody.center() - starPosition).toFloat();
    lighting.starDirection = normalize(lighting.starDirection);
    if (!currentSystem.stars.empty()) {
        lighting.starColor = currentSystem.stars[0].lightColor;
        lighting.starIntensity = static_cast<f32>(clampValue(currentSystem.stars[0].luminositySolar * 2.2, 0.5, 8.0) *
                                                  maxValue(daylight, 0.04));
    } else {
        lighting.starIntensity = static_cast<f32>(maxValue(daylight, 0.04));
    }
    lighting.starIntensity = maxValue(lighting.starIntensity, 0.06f);
    lighting.ambientColor = planet.skyColor * static_cast<f32>(0.05 + daylight * 0.22) +
                            Vec3(0.020f, 0.024f, 0.034f);

    TerrainRenderParameters terrain;
    terrain.planetCenter = landingBody.center();
    terrain.planetRadius = static_cast<f32>(landingBody.seaLevelRadius());
    terrain.terrainAmplitude = static_cast<f32>(landingBody.terrainAmplitude());
    terrain.waterColor = planet.waterColor;
    terrain.fogColor = lerp(planet.skyColor, Vec3(0.55f, 0.58f, 0.62f), 0.35f) *
                       static_cast<f32>(0.15 + daylight * 0.85);
    terrain.fogDensity = static_cast<f32>(clampValue(planet.atmospherePressureBar * 0.00016, 0.0, 0.0016));
    terrain.elapsedSeconds = static_cast<f32>(universeSeconds);
    terrain.detailStrength = settings.preset == QualityPreset::Sparmodus ? 0.45f : 1.0f;
    terrain.waterEnabled = planet.waterFraction > 0.02;

    planetSurface.collectVisible(camera.origin(), camera.frustum(), visibleChunks);
    terrainPass.renderChunks(camera, visibleChunks, terrain, lighting);

    scatterItems.clear();
    const usize scatterBudget = settings.preset == QualityPreset::Sparmodus ? 60u : 320u;
    for (const ScatterInstance& instance : planetSurface.scatter()) {
        if (scatterItems.size() >= scatterBudget) break;
        const DVec3 relative = instance.localPosition - camera.origin();
        if (lengthSquared(relative) > 620.0 * 620.0) continue;
        ScatterRenderItem item;
        item.relativePosition = relative.toFloat();
        item.upDirection = instance.upDirection.toFloat();
        item.tint = instance.tint;
        item.scale = instance.scale;
        item.rotation = instance.rotation;
        item.kind = instance.kind;
        scatterItems.push_back(item);
    }

    for (const CreatureInstance& creature : planetSurface.creatures()) {
        if (scatterItems.size() >= scatterBudget + 32) break;
        const DVec3 relative = creature.localPosition - camera.origin();
        if (lengthSquared(relative) > 420.0 * 420.0) continue;
        ScatterRenderItem item;
        item.relativePosition = relative.toFloat();
        item.upDirection = normalize(creature.localPosition - landingBody.center()).toFloat();
        item.tint = lerp(planet.vegetationColor, Vec3(0.72f, 0.52f, 0.34f), 0.55f);
        item.scale = creature.scale * 1.6f;
        item.rotation = 0.0f;
        item.kind = 2;
        scatterItems.push_back(item);
    }

    for (const ResourceNode& node : planetSurface.resources()) {
        if (node.depleted) continue;
        const DVec3 relative = node.localPosition - camera.origin();
        if (lengthSquared(relative) > 320.0 * 320.0) continue;
        ScatterRenderItem item;
        item.relativePosition = relative.toFloat();
        item.upDirection = node.upDirection.toFloat();
        item.tint = ItemDatabase::instance().definition(node.resource).tint;
        item.scale = node.radiusMeters;
        item.rotation = 0.0f;
        item.kind = 1;
        scatterItems.push_back(item);
    }

    for (const BasePart& part : homeBase.parts()) {
        const BuildPartDefinition& definition = BuildPartCatalog::instance().definition(part.partId);
        const DVec3 relative = part.localPosition - camera.origin();
        if (lengthSquared(relative) > 900.0 * 900.0) continue;
        ScatterRenderItem item;
        item.relativePosition = relative.toFloat();
        item.upDirection = part.upDirection.toFloat();
        item.tint = definition.tint;
        item.scale = definition.footprintMeters * 0.5f;
        item.rotation = part.rotation;
        item.kind = 2;
        scatterItems.push_back(item);
    }

    const DVec3 shipRelative = shipLandingPosition - camera.origin();
    if (lengthSquared(shipRelative) < 1200.0 * 1200.0) {
        ScatterRenderItem item;
        item.relativePosition = shipRelative.toFloat();
        item.upDirection = landingBody.upAt(shipLandingPosition).toFloat();
        item.tint = Vec3(0.52f, 0.58f, 0.66f);
        item.scale = 6.0f;
        item.rotation = 0.0f;
        item.kind = 2;
        scatterItems.push_back(item);
    }

    terrainPass.renderScatter(camera, scatterItems, terrain, lighting);
}

void GameApp::renderFrame(f64 interpolationAlpha) {
    (void)interpolationAlpha;
    if (window.resizedThisFrame()) applyQualitySettings();
    camera.setAspectRatio(window.aspectRatio());

    const bool menuMode = currentState == GameStateId::MainMenu || currentState == GameStateId::Booting;
    const bool footMode = currentState == GameStateId::OnFoot;
    if (menuMode) {
        mainMenu.configureCamera(camera, voidHeart.localPosition());
        mainMenu.collectBodies(visibleBodies, voidHeart.localPosition());
    } else if (footMode) {
        camera.setRenderOrigin(floatingOrigin.origin());
        camera.setWorldPosition(player.eyePosition());
        camera.setOrientation(player.orientation());
        camera.setPerspective(radians(74.0f), window.aspectRatio(), 0.12f, 4.0e7f);
        visibleBodies.clear();
    } else {
        camera.setRenderOrigin(floatingOrigin.origin());
        camera.setWorldPosition(flight.position);
        camera.setOrientation(flight.orientation);
        camera.setPerspective(radians(68.0f), window.aspectRatio(), 0.6f, 1.0e12f);
        buildVisibleBodies();
    }

    renderScene(menuMode);

    const QualitySettings& settings = quality.settings();
    PostProcessParameters post;
    post.exposure = menuMode ? mainMenu.exposureBias() : 0.85f;
    post.elapsedSeconds = static_cast<f32>(universeSeconds);
    post.distortionStrength = static_cast<f32>(clampValue(voidState.instrumentNoise * 0.08, 0.0, 0.09)) +
                              static_cast<f32>(hyperdriveState.warpFactor) * 0.16f;
    post.chromaticAberration = settings.chromaticAberration + static_cast<f32>(hyperdriveState.warpFactor) * 0.006f;
    post.vignetteStrength = 0.30f + static_cast<f32>(hyperdriveState.warpFactor) * 0.25f;
    post.bloomStrength = menuMode ? 0.075f : 0.055f;
    post.bloomLevels = settings.bloomEnabled ? settings.bloomLevels : 0;
    post.filmGrain = settings.filmGrain;
    post.desaturation = currentState == GameStateId::GalaxyMap ? 0.35f : 0.0f;
    postProcessPass.render(sceneTarget.colorTexture(), window.width(), window.height(), post);

    userInterface.beginFrame(window.width(), window.height());
    if (menuMode) {
        mainMenu.setQualityLine(std::string(QualitySettings::presetName(quality.preset())) +
                                (quality.automatic() ? "  AUTO" : "") + "   " +
                                std::to_string(static_cast<i32>(quality.smoothedFramesPerSecond())) + " fps");
        mainMenu.draw(userInterface, saveAvailable, jon.bridgeOnline());
    } else if (currentState == GameStateId::GalaxyMap) {
        galaxyMap.draw(userInterface, activeRoute, routeDenialText);
    } else if (currentState == GameStateId::OnFoot) {
        const DVec3 up = landingBody.upAt(player.localPosition());
        const SurfaceSample sample = landingBody.sampleSurface(up, surfaceDayPhase);
        const EnvironmentReading environment = readEnvironment();

        footFrame.planetName = landingBody.profile().name;
        footFrame.biomeName = PlanetGenerator::biomeName(sample.biome);
        footFrame.temperatureKelvin = environment.temperatureKelvin;
        footFrame.altitudeMeters = landingBody.altitudeAt(player.localPosition());
        footFrame.localTimeFraction = surfaceDayPhase;
        footFrame.shipDistanceMeters = length(player.localPosition() - shipLandingPosition);
        footFrame.credits = credits;
        footFrame.inShelter = environment.inShelter;
        footFrame.panel = activePanel;
        footFrame.selectedRecipeIndex = selectedRecipeIndex;
        footFrame.selectedPartIndex = selectedPartIndex;
        footFrame.selectedTradeIndex = selectedTradeIndex;
        footFrame.framesPerSecond = quality.smoothedFramesPerSecond();
        footFrame.qualityPreset = QualitySettings::presetName(quality.preset());
        footFrame.weatherLine = landingBody.profile().features.stormWorld ? "STURMWELT" : "";

        switch (player.toolMode()) {
            case ToolMode::MiningBeam: footFrame.toolLabel = "ABBAUSTRAHL"; break;
            case ToolMode::TerrainManipulator: footFrame.toolLabel = "GELAENDEFORMER"; break;
            case ToolMode::Scanner: footFrame.toolLabel = "SCANNER"; break;
            default: footFrame.toolLabel = "BAUMODUS"; break;
        }

        footFrame.interactionPrompt.clear();
        if (footFrame.shipDistanceMeters < 12.0) footFrame.interactionPrompt = "E  SCHIFF BESTEIGEN";
        else if (planetSurface.nearestResource(player.eyePosition() + player.lookDirection() * 4.0, 7.0)) {
            footFrame.interactionPrompt = "LMB  ABBAUEN";
        }

        footHud.draw(userInterface, player, footFrame, homeBase, marketAvailable ? &stationMarket : nullptr,
                     discoveries, panelRecipes, panelParts);
    } else {
        HudFrameData frame;
        frame.systemName = currentSystem.name;
        frame.speedMetresPerSecond = length(flight.velocity);
        frame.altitudeMeters = voidState.distanceMeters - voidHeart.horizonRadiusMeters();
        frame.oxygenFraction = oxygenFraction;
        frame.universeSeconds = universeSeconds;
        frame.coopPlayers = static_cast<u32>(coop.members().size());
        frame.coopStatus = coop.statusText();
        frame.qualityPreset = QualitySettings::presetName(quality.preset());
        frame.qualityNotice = quality.lastChangeReason();
        frame.qualityAutomatic = quality.automatic();
        frame.framesPerSecond = quality.smoothedFramesPerSecond();
        frame.showQualityNotice = quality.changedRecently();

        const KeplerElements orbit = OrbitalMechanics::fromStateVectors(
            flight.position - voidHeart.localPosition(), flight.velocity,
            kGravitationalConstant * voidHeart.massKilograms());
        frame.orbitValid = orbit.eccentricity < 0.999 && orbit.semiMajorAxisMeters > 0.0;
        frame.apoapsisMeters = orbit.apoapsisMeters();
        frame.periapsisMeters = orbit.periapsisMeters();
        frame.orbitalPeriodSeconds = orbit.orbitalPeriodSeconds();
        frame.inclinationDegrees = orbit.inclinationRadians * (180.0 / kPiDouble);

        hud.draw(userInterface, ship, flight, flightController, hyperdriveState, hyperdrive, voidState, jon, frame);
    }
    userInterface.endFrame();

    window.present();
    ++renderedFrames;

    if (!launch.screenshotPath.empty() && !screenshotTaken && renderedFrames > 3) {
        captureScreenshot(launch.screenshotPath);
        screenshotTaken = true;
    }
}

void GameApp::captureScreenshot(const std::string& path) {
    const u32 width = window.width();
    const u32 height = window.height();
    std::vector<u8> pixels(static_cast<usize>(width) * height * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, static_cast<GLsizei>(width), static_cast<GLsizei>(height), GL_RGB, GL_UNSIGNED_BYTE,
                 pixels.data());

    std::string header = "P6\n" + std::to_string(width) + " " + std::to_string(height) + "\n255\n";
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
    logInfo("app", "Bildschirmfoto gespeichert: %s", path.c_str());
}

void GameApp::run() {
    while (!window.shouldClose()) {
        window.pumpEvents();
        frameClock.tick();
        globalFrameAllocator().beginFrame();

        const f64 delta = frameClock.deltaSeconds();
        simulationClock.addTime(delta);
        const QualityPreset previousPreset = quality.preset();
        const f32 previousScale = quality.settings().sceneResolutionScale;
        quality.submitFrameTime(delta);
        handleQualityInput();
        if (quality.preset() != previousPreset ||
            std::fabs(quality.settings().sceneResolutionScale - previousScale) > 1.0e-4f) {
            applyQualitySettings();
        }

        switch (currentState) {
            case GameStateId::MainMenu: updateMenu(delta); break;
            case GameStateId::Flight: updateFlight(delta); break;
            case GameStateId::OnFoot: updateOnFoot(delta); break;
            case GameStateId::GalaxyMap: updateGalaxyMap(delta); break;
            default: break;
        }

        while (simulationClock.consumeStep()) {
            if (currentState == GameStateId::OnFoot) {
                stepSurfaceSimulation(simulationClock.stepSeconds());
            } else if (currentState == GameStateId::Flight || currentState == GameStateId::GalaxyMap) {
                stepSimulation(simulationClock.stepSeconds());
            } else if (currentState == GameStateId::MainMenu) {
                jon.update(jonContext, simulationClock.stepSeconds());
            }
        }

        if (window.input().keyPressed(Key::F11)) window.toggleFullscreen();
        renderFrame(simulationClock.interpolationAlpha());

        if (launch.frameLimit > 0 && renderedFrames >= launch.frameLimit) break;
    }
    MemoryTracker::instance().enforceBudgets();
}

}
