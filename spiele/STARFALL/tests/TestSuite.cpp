#include "../src/engine/math/Mat4.hpp"
#include "../src/engine/math/Quat.hpp"
#include "../src/engine/math/Scalar.hpp"
#include "../src/engine/render/QualitySettings.hpp"
#include "../src/sim/BlackHoleModel.hpp"

#include <cstdio>
#include <string>
#include <vector>

namespace sf {
namespace {

u32 checksPassed = 0;
u32 checksFailed = 0;

void check(bool condition, const char* description) {
    if (condition) {
        ++checksPassed;
        return;
    }
    ++checksFailed;
    std::printf("  FEHLER  %s\n", description);
}

void checkNear(f64 actual, f64 expected, f64 tolerance, const char* description) {
    if (std::fabs(actual - expected) <= tolerance) {
        ++checksPassed;
        return;
    }
    ++checksFailed;
    std::printf("  FEHLER  %s (erwartet %.9g, erhalten %.9g)\n", description, expected, actual);
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
    checkNear((rotation * Vec3::unitX()).z, -1.0, 1.0e-4, "Quaternion-Rotation");

    const Mat4 projection = Mat4::perspective(radians(60.0f), 16.0f / 9.0f, 0.1f, 1000.0f);
    const Mat4 identity = projection * projection.inverted();
    checkNear(identity.at(0, 0), 1.0, 1.0e-3, "Matrixinversion Diagonale");
    checkNear(identity.at(1, 0), 0.0, 1.0e-3, "Matrixinversion Nebendiagonale");
    checkNear(clampValue(5.0, 0.0, 1.0), 1.0, 1.0e-9, "Clamp");
    checkNear(smoothStep(0.0, 1.0, 0.5), 0.5, 1.0e-9, "SmoothStep");
}

void testHorizonGeometry() {
    std::printf("Horizontgeometrie\n");
    checkNear(BlackHoleModel::horizonRadii(0.0), 2.0, 1.0e-9, "Schwarzschild-Horizont bei 2 r_g");
    checkNear(BlackHoleModel::photonSphereRadii(0.0), 3.0, 1.0e-6, "Photonensphaere bei 3 r_g");
    checkNear(BlackHoleModel::innermostStableOrbitRadii(0.0), 6.0, 1.0e-6, "ISCO bei 6 r_g");
    checkNear(BlackHoleModel::ergosphereRadii(0.0, 0.0), 2.0, 1.0e-9, "Ergosphaere ohne Spin gleich Horizont");

    checkNear(BlackHoleModel::horizonRadii(0.998), 1.0 + std::sqrt(1.0 - 0.998 * 0.998), 1.0e-9,
              "Horizont bei der Thorne-Grenze");
    checkNear(BlackHoleModel::horizonRadii(1.4), BlackHoleModel::horizonRadii(0.998), 1.0e-9,
              "Spin wird auf 0,998 begrenzt");
    checkNear(BlackHoleModel::innermostStableOrbitRadii(0.998), 1.2373, 2.0e-3, "ISCO bei Spin 0,998");
    checkNear(BlackHoleModel::photonSphereRadii(0.998), 1.0743, 5.0e-3, "Photonenbahn bei Spin 0,998");

    check(BlackHoleModel::horizonRadii(0.94) < BlackHoleModel::horizonRadii(0.5), "Horizont schrumpft mit Spin");
    check(BlackHoleModel::innermostStableOrbitRadii(0.94) < 6.0, "ISCO rueckt mit Spin nach innen");
    check(BlackHoleModel::ergosphereRadii(0.9, 1.0) < BlackHoleModel::ergosphereRadii(0.9, 0.0),
          "Ergosphaere am Pol enger als am Aequator");

    for (f64 spin = 0.0; spin <= 0.99; spin += 0.11) {
        check(BlackHoleModel::innermostStableOrbitRadii(spin) >= BlackHoleModel::photonSphereRadii(spin),
              "ISCO liegt nie innerhalb der Photonensphaere");
        check(BlackHoleModel::photonSphereRadii(spin) >= BlackHoleModel::horizonRadii(spin),
              "Photonensphaere liegt nie innerhalb des Horizonts");
    }
}

void testTimeDilation() {
    std::printf("Zeitdilatation\n");
    checkNear(BlackHoleModel::gravitationalTimeDilation(1.0e9), 1.0, 1.0e-6, "Fernfeld ohne Dilatation");
    checkNear(BlackHoleModel::gravitationalTimeDilation(4.0), std::sqrt(0.5), 1.0e-9, "Faktor bei 4 r_g");
    checkNear(BlackHoleModel::gravitationalTimeDilation(2.0), 0.0, 1.0e-9, "Null am Schwarzschild-Radius");
    check(BlackHoleModel::gravitationalTimeDilation(1.5) == 0.0, "Innerhalb des Radius null");
    check(BlackHoleModel::gravitationalTimeDilation(3.0) < BlackHoleModel::gravitationalTimeDilation(30.0),
          "Naeher am Horizont laeuft die Uhr langsamer");
}

void testMassScaling() {
    std::printf("Massenskalierung\n");
    BlackHoleModel model;
    BlackHoleParameters parameters;
    parameters.massSolar = 1.0;
    parameters.spin = 0.0;
    model.setParameters(parameters);

    checkNear(model.derived().schwarzschildRadiusMeters, 2953.25, 1.0, "Sonnenmasse ergibt 2,95 km");

    parameters.massSolar = 4.297e6;
    model.setParameters(parameters);
    checkNear(model.derived().gravitationalRadiusMeters, 6.345e9, 2.0e7, "Sagittarius A* r_g rund 6,3 Mio. km");

    parameters.massSolar = 2.0;
    model.setParameters(parameters);
    const f64 doubled = model.derived().gravitationalRadiusMeters;
    parameters.massSolar = 1.0;
    model.setParameters(parameters);
    checkNear(doubled / model.derived().gravitationalRadiusMeters, 2.0, 1.0e-9, "r_g waechst linear mit der Masse");

    check(model.derived().hawkingTemperatureKelvin > 0.0, "Hawking-Temperatur positiv");
    check(model.derived().evaporationYears > 1.0e60, "Verdampfungszeit einer Sonnenmasse ist astronomisch");

    parameters.massSolar = 1.0e9;
    model.setParameters(parameters);
    const f64 heavy = model.derived().hawkingTemperatureKelvin;
    parameters.massSolar = 1.0;
    model.setParameters(parameters);
    check(heavy < model.derived().hawkingTemperatureKelvin, "Schwerere Loecher sind kaelter");
}

void testDiskProfile() {
    std::printf("Akkretionsscheibe nach Page-Thorne\n");
    const f64 inner = 6.0;
    const f64 innerTemperature = 9800.0;

    checkNear(BlackHoleModel::pageThorneFlux(inner, inner, 0.0), 0.0, 1.0e-12,
              "Fluss verschwindet am Innenrand");
    check(BlackHoleModel::pageThorneFlux(3.0, inner, 0.0) == 0.0, "Innerhalb der ISCO gibt es keinen Fluss");
    check(BlackHoleModel::diskTemperatureAt(3.0, inner, innerTemperature, 0.0) == 0.0,
          "Innerhalb der ISCO gibt es keine Scheibe");

    for (f64 radius = inner + 0.01; radius < 400.0; radius *= 1.15) {
        check(BlackHoleModel::pageThorneFlux(radius, inner, 0.0) >= 0.0, "Fluss ist nie negativ");
    }

    const f64 nearTemperature = BlackHoleModel::diskTemperatureAt(9.0, inner, innerTemperature, 0.0);
    const f64 farTemperature = BlackHoleModel::diskTemperatureAt(40.0, inner, innerTemperature, 0.0);
    check(nearTemperature > farTemperature, "Die Scheibe kuehlt nach aussen ab");

    f64 peakRadius = inner;
    f64 peakFlux = 0.0;
    for (f64 radius = inner; radius < 60.0; radius += 0.01) {
        const f64 flux = BlackHoleModel::pageThorneFlux(radius, inner, 0.0);
        if (flux <= peakFlux) continue;
        peakFlux = flux;
        peakRadius = radius;
    }
    checkNear(peakRadius, 8.39, 0.15, "Maximum des Schwarzschild-Flusses bei rund 8,39 r_g");
    check(peakRadius > inner * 49.0 / 36.0,
          "Relativistisches Maximum liegt weiter aussen als das newtonsche bei 49/36");
    checkNear(BlackHoleModel::diskTemperatureAt(inner * 49.0 / 36.0, inner, innerTemperature, 0.0),
              innerTemperature, 1.0e-6, "Referenzradius traegt die eingestellte Temperatur");

    const f64 outerRatio = BlackHoleModel::pageThorneFlux(4000.0, inner, 0.0) /
                           BlackHoleModel::pageThorneFlux(1000.0, inner, 0.0);
    checkNear(outerRatio, std::pow(4.0, -3.0), 0.06, "Weit aussen faellt der Fluss mit r hoch minus drei");

    const f64 spinning = BlackHoleModel::innermostStableOrbitRadii(0.94);
    check(BlackHoleModel::pageThorneFlux(spinning * 2.0, spinning, 0.94) >
              BlackHoleModel::pageThorneFlux(12.0, 6.0, 0.0),
          "Rotierendes Loch heizt die Scheibe staerker");
    check(BlackHoleModel::diskTemperatureAt(spinning * 1.02, spinning, innerTemperature, 0.94) < innerTemperature,
          "Direkt an der ISCO bleibt es kuehl");
}

void testObserver() {
    std::printf("Beobachter\n");
    BlackHoleModel model;
    BlackHoleParameters parameters;
    parameters.massSolar = 4.1e6;
    parameters.spin = 0.94;
    model.setParameters(parameters);

    const ObserverReadout far = model.observerAt(1.0e6);
    checkNear(far.gravitationalTimeDilation, 1.0, 1.0e-5, "Fernfeld ohne Dilatation");
    check(!far.insideErgosphere && !far.insideHorizon, "Fernfeld ausserhalb aller Zonen");
    check(far.circularOrbitSpeedFraction < 0.01, "Weit draussen ist die Bahngeschwindigkeit klein");

    const ObserverReadout isco = model.observerAt(model.derived().innermostStableOrbitRadii);
    check(isco.belowInnermostStableOrbit, "An der ISCO ist die Grenze erreicht");
    check(isco.circularOrbitSpeedFraction > 0.4, "An der ISCO wird es relativistisch");

    const ObserverReadout inside = model.observerAt(1.1);
    check(inside.insideHorizon, "Unterhalb des Horizonts erkannt");
    checkNear(inside.gravitationalTimeDilation, 0.0, 1.0e-9, "Innerhalb des Horizonts steht die Uhr");

    const ObserverReadout near = model.observerAt(3.0);
    const ObserverReadout further = model.observerAt(30.0);
    check(near.tidalAccelerationPerMetre > further.tidalAccelerationPerMetre, "Gezeiten nehmen nach innen zu");
    check(near.orbitalPeriodSeconds < further.orbitalPeriodSeconds, "Innen wird schneller umrundet");

    checkNear(model.observerAt(6.0).escapeSpeedFraction,
              std::sqrt(2.0 / 6.0), 1.0e-9, "Fluchtgeschwindigkeit folgt der Formel");
}

void testPresets() {
    std::printf("Voreinstellungen\n");
    const std::vector<BlackHoleParameters>& catalogue = BlackHoleModel::presets();
    check(catalogue.size() >= 6, "Mindestens sechs Objekte");

    BlackHoleModel model;
    for (const BlackHoleParameters& parameters : catalogue) {
        model.setParameters(parameters);
        const BlackHoleDerived& derived = model.derived();
        check(!parameters.name.empty(), "Jedes Objekt hat einen Namen");
        check(derived.gravitationalRadiusMeters > 0.0, "r_g positiv");
        check(derived.horizonRadii >= 1.0 && derived.horizonRadii <= 2.0, "Horizont zwischen 1 und 2 r_g");
        check(derived.innermostStableOrbitRadii > derived.horizonRadii, "ISCO ausserhalb des Horizonts");
        check(model.parameters().diskOuterRadii > derived.diskInnerRadii, "Scheibe hat eine Ausdehnung");
        check(parameters.observerRadii > derived.innermostStableOrbitRadii, "Startabstand ausserhalb der ISCO");
    }

    model.setParameters(catalogue[0]);
    check(std::string(BlackHoleModel::zoneLabel(model.derived(), 1000.0)) == std::string("FERNFELD"),
          "Zonenbezeichnung im Fernfeld");
    check(std::string(BlackHoleModel::zoneLabel(model.derived(), 1.0)) ==
              std::string("INNERHALB DES HORIZONTS"),
          "Zonenbezeichnung am Horizont");
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

    for (u32 index = 0; index + 1 < static_cast<u32>(QualityPreset::Count); ++index) {
        const QualitySettings lower = QualitySettings::fromPreset(static_cast<QualityPreset>(index));
        const QualitySettings higher = QualitySettings::fromPreset(static_cast<QualityPreset>(index + 1));
        check(lower.blackHoleMaximumSteps <= higher.blackHoleMaximumSteps, "Stufen sind monoton");
    }

    check(QualitySettings::presetFromText("sparmodus", QualityPreset::Ultra) == QualityPreset::Sparmodus,
          "Textparser deutsch");
    check(QualitySettings::presetFromText("low", QualityPreset::Ultra) == QualityPreset::Niedrig,
          "Textparser englisch");
    check(AdaptiveQualityController::detectStartingPreset("Intel(R) UHD Graphics 620", "Intel") ==
              QualityPreset::Sparmodus,
          "Notebook-Grafik erkennt Sparmodus");
    check(AdaptiveQualityController::detectStartingPreset("NVIDIA GeForce RTX 4070", "NVIDIA") == QualityPreset::Hoch,
          "Aktuelle Karte erkennt hohe Stufe");

    AdaptiveQualityController controller;
    controller.configure(QualityPreset::Hoch, true, 60.0);
    for (u32 tick = 0; tick < 900; ++tick) controller.submitFrameTime(1.0 / 12.0);
    check(controller.preset() < QualityPreset::Hoch, "Automatik stuft bei Ruckeln herunter");

    AdaptiveQualityController fixedController;
    fixedController.configure(QualityPreset::Mittel, false, 60.0);
    for (u32 tick = 0; tick < 900; ++tick) fixedController.submitFrameTime(1.0 / 8.0);
    check(fixedController.preset() == QualityPreset::Mittel, "Ohne Automatik bleibt die Stufe stehen");
    fixedController.stepPreset(-1);
    fixedController.stepPreset(-1);
    check(fixedController.preset() == QualityPreset::Sparmodus, "Manuell bis Sparmodus");
    fixedController.stepPreset(-1);
    check(fixedController.preset() == QualityPreset::Sparmodus, "Sparmodus ist die unterste Stufe");
}

}

int runTestSuite() {
    std::printf("Schwarzloch-Simulation Testsuite\n\n");
    checksPassed = 0;
    checksFailed = 0;

    testMath();
    testHorizonGeometry();
    testTimeDilation();
    testMassScaling();
    testDiskProfile();
    testObserver();
    testPresets();
    testQuality();

    std::printf("\n%u Pruefungen bestanden, %u fehlgeschlagen\n", checksPassed, checksFailed);
    return static_cast<int>(checksFailed);
}

}
