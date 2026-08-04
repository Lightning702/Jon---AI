#include "../src/engine/container/Array.hpp"
#include "../src/engine/container/BitSet.hpp"
#include "../src/engine/container/HashMap.hpp"
#include "../src/engine/container/RingBuffer.hpp"
#include "../src/engine/container/SparseSet.hpp"
#include "../src/engine/core/Log.hpp"
#include "../src/engine/ecs/Query.hpp"
#include "../src/engine/math/Noise.hpp"
#include "../src/engine/math/Quat.hpp"
#include "../src/engine/math/Scalar.hpp"
#include "../src/engine/memory/ArenaAllocator.hpp"
#include "../src/engine/memory/PoolAllocator.hpp"
#include "../src/engine/net/Json.hpp"
#include "../src/engine/render/BlackHolePass.hpp"
#include "../src/engine/render/QualitySettings.hpp"
#include "../src/game/space/HyperdriveSystem.hpp"
#include "../src/game/space/OrbitalMechanics.hpp"
#include "../src/game/universe/GalaxyGenerator.hpp"
#include "../src/game/voidheart/EndgameCampaign.hpp"
#include "../src/game/voidheart/VoidHeart.hpp"

#include <cstdio>
#include <string>
#include <vector>

namespace sf {
namespace {

u32 checksPassed = 0;
u32 checksFailed = 0;
std::vector<std::string> failureLog;

void check(bool condition, const char* description) {
    if (condition) {
        ++checksPassed;
        return;
    }
    ++checksFailed;
    failureLog.push_back(description);
    std::printf("  FEHLER  %s\n", description);
}

void checkNear(f64 actual, f64 expected, f64 tolerance, const char* description) {
    const bool ok = std::fabs(actual - expected) <= tolerance;
    if (!ok) {
        std::printf("  FEHLER  %s (erwartet %.9g, erhalten %.9g)\n", description, expected, actual);
        ++checksFailed;
        failureLog.push_back(description);
        return;
    }
    ++checksPassed;
}

void testMath() {
    std::printf("Mathematik\n");
    const Vec3 a(1.0f, 2.0f, 3.0f);
    const Vec3 b(4.0f, -5.0f, 6.0f);
    checkNear(dot(a, b), 12.0, 1.0e-5, "Skalarprodukt");
    const Vec3 crossProduct = cross(a, b);
    checkNear(crossProduct.x, 27.0, 1.0e-5, "Kreuzprodukt x");
    checkNear(crossProduct.y, 6.0, 1.0e-5, "Kreuzprodukt y");
    checkNear(crossProduct.z, -13.0, 1.0e-5, "Kreuzprodukt z");
    checkNear(length(normalize(b)), 1.0, 1.0e-5, "Normalisierung");

    const Quat rotation = Quat::fromAxisAngle(Vec3::unitY(), kHalfPi);
    const Vec3 rotated = rotation * Vec3::unitX();
    checkNear(rotated.z, -1.0, 1.0e-4, "Quaternion-Rotation");

    const Mat4 projection = Mat4::perspective(radians(60.0f), 16.0f / 9.0f, 0.1f, 1000.0f);
    const Mat4 inverse = projection.inverted();
    const Mat4 identity = projection * inverse;
    checkNear(identity.at(0, 0), 1.0, 1.0e-3, "Matrixinversion Diagonale");
    checkNear(identity.at(1, 0), 0.0, 1.0e-3, "Matrixinversion Nebendiagonale");

    checkNear(clampValue(5.0, 0.0, 1.0), 1.0, 1.0e-9, "Clamp");
    checkNear(smoothStep(0.0, 1.0, 0.5), 0.5, 1.0e-9, "SmoothStep");
}

void testContainers() {
    std::printf("Container\n");
    Array<i32> values;
    for (i32 index = 0; index < 100; ++index) values.push(index);
    check(values.size() == 100, "Array Groesse");
    values.removeAtSwap(0);
    check(values.size() == 99, "Array Entfernen");

    SparseSet<f32> sparse;
    sparse.insert(42, 3.5f);
    sparse.insert(7, 1.25f);
    check(sparse.contains(42) && sparse.contains(7), "SparseSet Einfuegen");
    sparse.remove(42);
    check(!sparse.contains(42) && sparse.contains(7), "SparseSet Entfernen");

    HashMap<u64, u32> map;
    for (u64 index = 0; index < 500; ++index) map.insert(index * 7919ull, static_cast<u32>(index));
    check(map.size() == 500, "HashMap Groesse");
    const u32* found = map.find(7919ull * 250ull);
    check(found != nullptr && *found == 250, "HashMap Suche");

    RingBuffer<i32> ring(4);
    ring.pushOverwrite(1);
    ring.pushOverwrite(2);
    ring.pushOverwrite(3);
    ring.pushOverwrite(4);
    ring.pushOverwrite(5);
    check(ring.size() == 4, "RingBuffer Ueberschreiben");

    BitSet bits(128);
    bits.set(3);
    bits.set(127);
    check(bits.test(3) && bits.test(127) && !bits.test(4), "BitSet");
    check(bits.countSet() == 2, "BitSet Zaehlung");
}

void testAllocators() {
    std::printf("Speicher\n");
    ArenaAllocator arena(4096, MemoryCategory::Scratch);
    void* first = arena.allocate(64, 16);
    void* second = arena.allocate(128, 32);
    check(first != nullptr && second != nullptr, "Arena Allokation");
    check(reinterpret_cast<usize>(second) % 32 == 0, "Arena Ausrichtung");
    const usize marker = arena.marker();
    arena.allocate(256, 8);
    arena.rewindTo(marker);
    check(arena.bytesInUse() == marker, "Arena Rueckspulen");

    PoolAllocator pool(sizeof(u64), alignof(u64), 8, MemoryCategory::Scratch);
    void* slots[8];
    for (u32 index = 0; index < 8; ++index) slots[index] = pool.acquire();
    check(pool.acquire() == nullptr, "Pool erschoepft");
    pool.recycle(slots[3]);
    check(pool.acquire() == slots[3], "Pool Wiederverwendung");
}

struct TestPosition {
    f64 x = 0.0;
    f64 y = 0.0;
};

struct TestVelocity {
    f64 x = 0.0;
};

void testEntityComponentSystem() {
    std::printf("ECS\n");
    World world;
    Entity first = world.createEntity();
    Entity second = world.createEntity();
    world.addComponent<TestPosition>(first, TestPosition{1.0, 2.0});
    world.addComponent<TestVelocity>(first, TestVelocity{3.0});
    world.addComponent<TestPosition>(second, TestPosition{7.0, 8.0});

    check(world.component<TestPosition>(first) != nullptr, "Komponente vorhanden");
    checkNear(world.component<TestPosition>(first)->y, 2.0, 1.0e-9, "Komponentenwert");
    check(world.component<TestVelocity>(second) == nullptr, "Komponente fehlt korrekt");

    Query query;
    query.with<TestPosition>();
    check(query.countMatches(world) == 2, "Query Treffer");

    Query movingQuery;
    movingQuery.with<TestPosition>().with<TestVelocity>();
    check(movingQuery.countMatches(world) == 1, "Query mit zwei Komponenten");

    world.destroyEntity(first);
    check(!world.alive(first), "Entitaet zerstoert");
    check(query.countMatches(world) == 1, "Query nach Zerstoerung");
}

void testNoiseDeterminism() {
    std::printf("Rauschen\n");
    const DVec3 sample(12.75, -3.5, 8.25);
    const f64 firstRun = simplexNoise3(1234, sample);
    const f64 secondRun = simplexNoise3(1234, sample);
    checkNear(firstRun, secondRun, 0.0, "Simplex deterministisch");
    check(std::fabs(firstRun) <= 1.0, "Simplex im Wertebereich");

    const f64 differentSeed = simplexNoise3(1235, sample);
    check(std::fabs(differentSeed - firstRun) > 1.0e-9, "Seed veraendert Rauschen");

    FractalSettings settings;
    const f64 fractal = fractalNoise3(99, sample, settings);
    check(std::fabs(fractal) <= 1.0, "Fraktales Rauschen im Wertebereich");

    const WorleyResult worley = worleyNoise3(7, sample);
    check(worley.nearestDistance <= worley.secondDistance, "Worley Reihenfolge");
}

void testUniverseDeterminism() {
    std::printf("Universum\n");
    UniverseSeed seed(0xC0FFEE);
    GalaxyGenerator galaxyGenerator;
    StarSystemGenerator systemGenerator;

    const GalaxyProfile firstGalaxy = galaxyGenerator.generate(seed, 3);
    const GalaxyProfile secondGalaxy = galaxyGenerator.generate(seed, 3);
    check(firstGalaxy.seed == secondGalaxy.seed, "Galaxie-Seed reproduzierbar");
    check(firstGalaxy.name == secondGalaxy.name, "Galaxiename reproduzierbar");

    SystemCoord coordinate;
    coordinate.x = 17;
    coordinate.y = -4;
    coordinate.z = 233;
    const StarSystemProfile firstSystem = systemGenerator.generate(seed, firstGalaxy.seed, coordinate);
    const StarSystemProfile secondSystem = systemGenerator.generate(seed, firstGalaxy.seed, coordinate);
    check(firstSystem.name == secondSystem.name, "Systemname reproduzierbar");
    check(firstSystem.planets.size() == secondSystem.planets.size(), "Planetenanzahl reproduzierbar");

    if (!firstSystem.planets.empty()) {
        checkNear(firstSystem.planets[0].radiusMeters, secondSystem.planets[0].radiusMeters, 0.0,
                  "Planetenradius reproduzierbar");
        check(firstSystem.planets[0].habitabilityIndex() >= 0.0 &&
                  firstSystem.planets[0].habitabilityIndex() <= 1.0,
              "Bewohnbarkeit im Wertebereich");
    }

    SystemCoord otherCoordinate = coordinate;
    otherCoordinate.x += 1;
    const StarSystemProfile otherSystem = systemGenerator.generate(seed, firstGalaxy.seed, otherCoordinate);
    check(otherSystem.seed != firstSystem.seed, "Nachbarsystem unterscheidet sich");

    const f64 density = GalaxyGenerator::stellarDensity(firstGalaxy, DVec3(0.0, 0.0, 0.0));
    check(density > 0.0, "Sterndichte im Zentrum positiv");
}

void testOrbitalMechanics() {
    std::printf("Orbitalmechanik\n");
    const f64 gravitationalParameter = kGravitationalConstant * kEarthMass;
    KeplerElements elements;
    elements.gravitationalParameter = gravitationalParameter;
    elements.semiMajorAxisMeters = kEarthRadius + 400000.0;
    elements.eccentricity = 0.0;

    const f64 period = elements.orbitalPeriodSeconds();
    check(period > 5000.0 && period < 6000.0, "Niedriger Erdorbit Umlaufzeit");

    const DVec3 startPosition = elements.positionAt(0.0);
    const DVec3 halfPosition = elements.positionAt(period * 0.5);
    checkNear(length(startPosition), elements.semiMajorAxisMeters, 1.0, "Kreisbahnradius");
    checkNear(dot(normalize(startPosition), normalize(halfPosition)), -1.0, 1.0e-4, "Halbe Umlaufbahn gegenueber");

    const f64 anomaly = OrbitalMechanics::solveKeplerEquation(1.0, 0.6);
    checkNear(anomaly - 0.6 * std::sin(anomaly), 1.0, 1.0e-9, "Kepler-Gleichung geloest");

    const DVec3 position(7.0e6, 0.0, 0.0);
    const f64 circular = OrbitalMechanics::circularOrbitSpeed(gravitationalParameter, 7.0e6);
    const DVec3 velocity(0.0, 0.0, circular);
    const KeplerElements recovered = OrbitalMechanics::fromStateVectors(position, velocity, gravitationalParameter);
    checkNear(recovered.semiMajorAxisMeters, 7.0e6, 1.0e3, "Zustandsvektoren zu Bahnelementen");
    check(recovered.eccentricity < 0.01, "Kreisbahn erkannt");

    const f64 escape = OrbitalMechanics::escapeSpeed(gravitationalParameter, kEarthRadius);
    check(escape > 11000.0 && escape < 11300.0, "Fluchtgeschwindigkeit Erde");
}

void testVoidHeart() {
    std::printf("Void Heart\n");
    VoidHeart heart;
    checkNear(heart.massSolar(), 4.1e6, 1.0, "Masse 4,1 Millionen Sonnenmassen");
    checkNear(heart.schwarzschildRadiusMeters(), 1.211e10, 6.0e7, "Schwarzschild-Radius rund 12,1 Millionen km");
    check(heart.spin() > 0.93 && heart.spin() < 0.95, "Kerr-Parameter 0,94");

    const f32 horizon = BlackHolePass::horizonRadius(0.94f);
    check(horizon > 1.0f && horizon < 1.35f, "Horizontradius bei hohem Spin");

    const f32 isco = BlackHolePass::innermostStableCircularOrbit(0.0f);
    checkNear(isco, 6.0, 1.0e-3, "ISCO bei Schwarzschild ist 6 M");

    const f32 iscoKerr = BlackHolePass::innermostStableCircularOrbit(0.94f);
    check(iscoKerr < 2.1f && iscoKerr > 1.6f, "ISCO bei Spin 0,94 rueckt nach innen");

    const f32 photonSphere = BlackHolePass::photonSphereRadius(0.0f);
    checkNear(photonSphere, 3.0, 1.0e-3, "Photonensphaere bei 3 M");

    checkNear(BlackHolePass::timeDilationFactor(1.0e9, 0.94), 1.0, 1.0e-6, "Zeitdilatation im Fernfeld");
    checkNear(BlackHolePass::timeDilationFactor(2.05, 0.94), std::sqrt(1.0 - 2.0 / 2.05), 1.0e-9,
              "Zeitdilatation folgt sqrt(1 - r_s/r)");
    check(BlackHolePass::timeDilationFactor(2.05, 0.94) < 0.2, "Zeitdilatation nahe dem Horizont sehr klein");
    check(BlackHolePass::timeDilationFactor(2.0, 0.94) <= 0.0, "Zeitdilatation am Schwarzschild-Radius null");

    const VoidHeartState farField = heart.evaluate(DVec3(heart.gravitationalRadiusMeters() * 100000.0, 0.0, 0.0));
    check(farField.zone == VoidZone::FarField, "Fernfeld erkannt");
    check(farField.escapePossible, "Flucht im Fernfeld moeglich");

    const VoidHeartState distortion = heart.evaluate(DVec3(heart.gravitationalRadiusMeters() * 50.0, 0.0, 0.0));
    check(distortion.zone == VoidZone::Distortion, "Verzerrungszone erkannt");
    check(distortion.hyperdriveChargeMultiplier > 1.0, "Ladezeit steigt in der Verzerrungszone");

    const VoidHeartState horizonZone = heart.evaluate(DVec3(heart.horizonRadiusMeters() * 0.5, 0.0, 0.0));
    check(horizonZone.zone == VoidZone::EventHorizon, "Ereignishorizont erkannt");
    check(!horizonZone.escapePossible, "Keine Flucht am Horizont");

    const f64 orbitSpeed = heart.orbitalSpeedAt(heart.gravitationalRadiusMeters() * 20.0);
    check(orbitSpeed < kSpeedOfLight, "Orbitalgeschwindigkeit unter Lichtgeschwindigkeit");
}

void testExoticResourcesAndCampaign() {
    std::printf("Endgame\n");
    ExoticResourceLedger ledger;
    ledger.add(ExoticResourceId::VoidMatter, 5.0);
    check(!ledger.consume(ExoticResourceId::VoidMatter, 6.0), "Zu viel verbrauchen scheitert");
    check(ledger.consume(ExoticResourceId::VoidMatter, 2.5), "Verbrauch erfolgreich");
    checkNear(ledger.quantity(ExoticResourceId::VoidMatter), 2.5, 1.0e-9, "Restmenge korrekt");
    check(ledger.totalValue() > 0.0, "Warenwert positiv");

    const f64 peak = ExoticResourceLedger::harvestRatePerSecond(ExoticResourceId::VoidMatter, 140.0, 1.0);
    const f64 away = ExoticResourceLedger::harvestRatePerSecond(ExoticResourceId::VoidMatter, 900.0, 1.0);
    check(peak > away, "Ernterate hat ein Optimum");

    VoidStationRegistry stations;
    check(stations.stations().size() == 4, "Vier Void-Stationen");
    check(stations.discoveredCount() == 0, "Zu Beginn nichts entdeckt");
    stations.markDiscovered(VoidStationId::HorizonWatch);
    check(stations.discoveredCount() == 1, "Entdeckung gezaehlt");
    for (u32 index = 0; index < 4; ++index) stations.solveStage(VoidStationId::HorizonWatch);
    check(stations.voidDriveBlueprintUnlocked(), "Void-Antrieb freigeschaltet");

    EndgameCampaign campaign;
    check(campaign.missions().size() == 6, "Sechs Endgame-Missionen");
    campaign.evaluateUnlocks(4, 2, stations);
    check(campaign.mission(EndgameMissionId::TheSignal).state == MissionState::Locked,
          "Ohne Forschungsstufe 5 gesperrt");
    campaign.evaluateUnlocks(5, 2, stations);
    check(campaign.mission(EndgameMissionId::TheSignal).state == MissionState::Available, "Mission eins freigegeben");
    check(campaign.startMission(EndgameMissionId::TheSignal), "Mission gestartet");
    for (usize index = 0; index < campaign.mission(EndgameMissionId::TheSignal).objectives.size(); ++index) {
        campaign.completeObjective(EndgameMissionId::TheSignal, index);
    }
    check(campaign.mission(EndgameMissionId::TheSignal).state == MissionState::Completed, "Mission abgeschlossen");
    check(!campaign.newGamePlusUnlocked(), "New Game Plus noch gesperrt");
}

void testHyperdrive() {
    std::printf("Hyperantrieb\n");
    HyperdriveSystem drive;
    drive.setSpecification(HyperdriveSystem::specificationFor(HyperdriveClass::MarkTwo));

    SystemCoord from;
    SystemCoord to;
    to.x = 12;
    checkNear(HyperdriveSystem::distanceLightYears(from, to), 12.0, 1.0e-9, "Distanz in Lichtjahren");

    check(drive.evaluateJump(from, to, 1000.0, 42.0, 0.0, 1.0, false) == JumpDenialReason::None,
          "Sprung in Reichweite erlaubt");

    SystemCoord tooFar;
    tooFar.x = 400;
    check(drive.evaluateJump(from, tooFar, 1000.0, 42.0, 0.0, 1.0, false) == JumpDenialReason::OutOfRange,
          "Zu weit wird abgelehnt");
    check(drive.evaluateJump(from, to, 0.01, 42.0, 0.0, 1.0, false) == JumpDenialReason::InsufficientFuel,
          "Zu wenig Treibstoff wird abgelehnt");
    check(drive.evaluateJump(from, to, 1000.0, 42.0, 0.9, 1.0, false) == JumpDenialReason::MassLock,
          "Massenverriegelung greift");
    check(drive.evaluateJump(from, to, 1000.0, 42.0, 0.0, 1.0, true) == JumpDenialReason::VoidDriveRequired,
          "Void-Zone braucht Void-Antrieb");

    const f64 nearCost = drive.energyCost(5.0, 42.0, 0.0, 1.0);
    const f64 farCost = drive.energyCost(20.0, 42.0, 0.0, 1.0);
    check(farCost > nearCost * 4.0, "Kosten wachsen ueberproportional");

    HyperdriveState state;
    check(drive.beginJump(state, to, 12.0, 1.0), "Sprung eingeleitet");
    check(state.phase == HyperdrivePhase::Charging, "Ladephase aktiv");
    for (u32 tick = 0; tick < 4000 && state.phase != HyperdrivePhase::Idle; ++tick) {
        drive.update(state, 1.0 / 60.0, 0.5, 12345);
    }
    check(state.phase == HyperdrivePhase::Idle, "Sprungzyklus endet wieder im Leerlauf");

    HyperRouteSolver solver;
    std::vector<HyperRouteSolver::StarNode> nodes;
    for (i64 index = 0; index <= 6; ++index) {
        HyperRouteSolver::StarNode node;
        node.coordinate.x = index * 10;
        node.surveyed = true;
        nodes.push_back(node);
    }
    solver.setNodes(nodes);
    SystemCoord goal;
    goal.x = 60;
    const HyperRoute route = solver.solve(from, goal, 25.0, 1000.0, RoutePreference::Shortest);
    check(route.reachable, "Route gefunden");
    check(route.legs.size() >= 3, "Mehrsprung-Route");
    checkNear(route.totalDistanceLightYears, 60.0, 1.0e-6, "Gesamtdistanz stimmt");
}

void testQuality() {
    std::printf("Qualitaetsstufen\n");
    const QualitySettings spar = QualitySettings::fromPreset(QualityPreset::Sparmodus);
    const QualitySettings ultra = QualitySettings::fromPreset(QualityPreset::Ultra);

    check(spar.blackHoleMaximumSteps < ultra.blackHoleMaximumSteps, "Sparmodus rechnet weniger Schritte");
    check(spar.blackHoleResolutionScale < ultra.blackHoleResolutionScale, "Sparmodus rendert kleiner");
    check(spar.blackHoleStepFraction > ultra.blackHoleStepFraction, "Sparmodus nimmt groebere Schritte");
    check(spar.blackHoleIntegratorOrder == 1, "Sparmodus nutzt den sparsamen Integrator");
    check(!spar.bloomEnabled && ultra.bloomEnabled, "Bloom nur ab hoeheren Stufen");
    check(!spar.atmosphereEnabled, "Sparmodus ohne Atmosphaerenschale");
    check(spar.sphereSubdivisions < ultra.sphereSubdivisions, "Sparmodus mit groberen Kugeln");
    check(spar.mapStarBudget < ultra.mapStarBudget, "Sparmodus mit weniger Kartensternen");

    for (u32 index = 0; index + 1 < static_cast<u32>(QualityPreset::Count); ++index) {
        const QualitySettings lower = QualitySettings::fromPreset(static_cast<QualityPreset>(index));
        const QualitySettings higher = QualitySettings::fromPreset(static_cast<QualityPreset>(index + 1));
        check(lower.blackHoleMaximumSteps <= higher.blackHoleMaximumSteps, "Stufen sind monoton");
    }

    check(QualitySettings::presetFromText("sparmodus", QualityPreset::Ultra) == QualityPreset::Sparmodus,
          "Textparser deutsch");
    check(QualitySettings::presetFromText("low", QualityPreset::Ultra) == QualityPreset::Niedrig,
          "Textparser englisch");
    check(QualitySettings::presetFromText("unsinn", QualityPreset::Hoch) == QualityPreset::Hoch,
          "Textparser mit Rueckfallwert");

    check(AdaptiveQualityController::detectStartingPreset("Intel(R) UHD Graphics 620", "Intel") ==
              QualityPreset::Sparmodus,
          "Notebook-Grafik erkennt Sparmodus");
    check(AdaptiveQualityController::detectStartingPreset("NVIDIA GeForce RTX 4070", "NVIDIA") ==
              QualityPreset::Hoch,
          "Aktuelle Karte erkennt hohe Stufe");
    check(AdaptiveQualityController::detectStartingPreset("llvmpipe (LLVM 15)", "Mesa") == QualityPreset::Sparmodus,
          "Software-Rasterizer erkennt Sparmodus");

    AdaptiveQualityController controller;
    controller.configure(QualityPreset::Hoch, true, 60.0);
    check(controller.preset() == QualityPreset::Hoch, "Startstufe uebernommen");
    for (u32 tick = 0; tick < 900; ++tick) controller.submitFrameTime(1.0 / 12.0);
    check(controller.preset() < QualityPreset::Hoch, "Automatik stuft bei Ruckeln herunter");
    check(controller.smoothedFramesPerSecond() < 20.0, "Bildrate wird gemessen");

    AdaptiveQualityController fixedController;
    fixedController.configure(QualityPreset::Mittel, false, 60.0);
    for (u32 tick = 0; tick < 900; ++tick) fixedController.submitFrameTime(1.0 / 8.0);
    check(fixedController.preset() == QualityPreset::Mittel, "Ohne Automatik bleibt die Stufe stehen");

    fixedController.stepPreset(-1);
    check(fixedController.preset() == QualityPreset::Niedrig, "Manuell herunterstufen");
    fixedController.stepPreset(-1);
    check(fixedController.preset() == QualityPreset::Sparmodus, "Manuell bis Sparmodus");
    fixedController.stepPreset(-1);
    check(fixedController.preset() == QualityPreset::Sparmodus, "Sparmodus ist die unterste Stufe");
    fixedController.setPreset(QualityPreset::Ultra);
    fixedController.stepPreset(1);
    check(fixedController.preset() == QualityPreset::Ultra, "Ultra ist die oberste Stufe");
}

void testJson() {
    std::printf("JSON\n");
    JsonValue root = JsonValue::makeObject();
    root.set("name", std::string("Jon"));
    root.set("wert", 42.5);
    root.set("aktiv", true);
    JsonValue liste = JsonValue::makeArray();
    liste.push(JsonValue(1.0));
    liste.push(JsonValue(std::string("zwei")));
    root.set("liste", liste);

    const std::string text = root.serialize();
    const JsonValue parsed = JsonValue::parse(text);
    check(parsed["name"].text() == "Jon", "JSON Text");
    checkNear(parsed["wert"].number(), 42.5, 1.0e-9, "JSON Zahl");
    check(parsed["aktiv"].boolean(), "JSON Wahrheitswert");
    check(parsed["liste"].size() == 2, "JSON Array");
    check(parsed["liste"].at(1).text() == "zwei", "JSON Arrayelement");
    check(parsed["fehlt"].isNull(), "JSON fehlender Schluessel");

    const JsonValue escaped = JsonValue::parse("{\"text\":\"Zeile\\nZeile\"}");
    check(escaped["text"].text() == "Zeile\nZeile", "JSON Escape");
}

}

int runTestSuite() {
    std::printf("STARFALL Testsuite\n\n");
    checksPassed = 0;
    checksFailed = 0;
    failureLog.clear();

    testMath();
    testContainers();
    testAllocators();
    testEntityComponentSystem();
    testNoiseDeterminism();
    testUniverseDeterminism();
    testOrbitalMechanics();
    testVoidHeart();
    testExoticResourcesAndCampaign();
    testHyperdrive();
    testQuality();
    testJson();

    std::printf("\n%u Pruefungen bestanden, %u fehlgeschlagen\n", checksPassed, checksFailed);
    return static_cast<int>(checksFailed);
}

}
