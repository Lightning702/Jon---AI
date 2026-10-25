#include "Pilot.hpp"

#include <algorithm>
#include <cmath>

namespace blitzbahn {

using namespace fw;

namespace {

Vec3 mittelpunkt(const Stueck& s) {
    if (s.teil == KURVE) {
        float w = PI * 0.25f;
        return lokalZuWelt(s, Vec3(ZELLE * 0.5f - 10.0f * std::cos(w), 0.0f, -ZELLE * 0.5f + 10.0f * std::sin(w)));
    }
    return lokalZuWelt(s, Vec3(0.0f, 0.0f, 0.0f));
}

}

Eingabe Pilot::lenken(const Strecke& strecke, const Fahrzeug& wagen) {
    Eingabe e;
    const int anzahl = static_cast<int>(strecke.stuecke.size());
    if (anzahl == 0) return e;
    if (wagen.bodenStueck >= 0 && wagen.bodenStueck < anzahl && wagen.bodenStueck >= fortschritt - 1 &&
        wagen.bodenStueck <= fortschritt + 3) {
        fortschritt = std::max(fortschritt, wagen.bodenStueck);
    }
    int ziel = std::min(anzahl - 1, fortschritt + 1);
    Vec3 punktZiel = mittelpunkt(strecke.stuecke[ziel]);
    Vec3 aktuell = mittelpunkt(strecke.stuecke[std::min(fortschritt, anzahl - 1)]);
    Vec3 nachZiel = punktZiel - wagen.ort;
    float abstandZiel = std::sqrt(nachZiel.x * nachZiel.x + nachZiel.z * nachZiel.z);
    if (abstandZiel < 6.0f && ziel + 1 < anzahl) punktZiel = mittelpunkt(strecke.stuecke[ziel + 1]);
    Vec3 weg = punktZiel - wagen.ort;
    float wunsch = std::atan2(weg.x, weg.z);
    float abw = winkelDifferenz(wagen.gier, wunsch);
    e.lenkung = klemme(abw * 2.6f, -1.0f, 1.0f);
    float v = wagen.vorwaerts();
    bool kurveVorn = strecke.stuecke[ziel].teil == KURVE;
    bool kurveBald = ziel + 1 < anzahl && strecke.stuecke[ziel + 1].teil == KURVE;
    bool inKurve = fortschritt < anzahl && strecke.stuecke[fortschritt].teil == KURVE;
    float grenze = 200.0f;
    if (kurveBald) grenze = 38.0f;
    if (kurveVorn) grenze = 25.0f;
    if (inKurve) grenze = std::min(grenze, 24.0f);
    if (std::fabs(abw) > 0.5f) grenze = std::min(grenze, 20.0f);
    (void)aktuell;
    if (v > grenze) {
        e.gas = 0.0f;
        e.bremse = 0.7f;
    } else {
        e.gas = 1.0f;
    }
    return e;
}

}
