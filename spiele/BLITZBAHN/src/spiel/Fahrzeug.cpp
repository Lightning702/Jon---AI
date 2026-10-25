#include "Fahrzeug.hpp"

#include <algorithm>
#include <cmath>

namespace blitzbahn {

using namespace fw;

Mat4 lageMatrix(const Lage& lage) {
    Vec3 f = normiert(lage.vorne);
    Vec3 u = normiert(lage.oben - f * punkt(lage.oben, f));
    Vec3 r = kreuz(u, f);
    Mat4 m;
    m.m[0] = r.x;
    m.m[1] = r.y;
    m.m[2] = r.z;
    m.m[4] = u.x;
    m.m[5] = u.y;
    m.m[6] = u.z;
    m.m[8] = f.x;
    m.m[9] = f.y;
    m.m[10] = f.z;
    m.m[12] = lage.ort.x;
    m.m[13] = lage.ort.y;
    m.m[14] = lage.ort.z;
    return m;
}

void Fahrzeug::setzen(Vec3 neuerOrt, float neueGier) {
    ort = neuerOrt;
    fahrt = Vec3(0.0f, 0.0f, 0.0f);
    gier = neueGier;
    nick = 0.0f;
    rollen = 0.0f;
    lenkwinkel = 0.0f;
    luftzeit = 0.0f;
    aufprall = 0.0f;
    wandstoss = 0.0f;
    schub = 0.0f;
    amBoden = true;
    driftet = false;
    drift = 0.0f;
    oben = Vec3(0.0f, 1.0f, 0.0f);
}

float Fahrzeug::tempo() const { return laenge(fahrt); }

Vec3 Fahrzeug::vorne() const {
    Vec3 flach(std::sin(gier), 0.0f, std::cos(gier));
    if (amBoden) return normiert(flach - oben * punkt(flach, oben));
    float c = std::cos(nick);
    return Vec3(flach.x * c, std::sin(nick), flach.z * c);
}

float Fahrzeug::vorwaerts() const { return punkt(fahrt, vorne()); }

Lage Fahrzeug::lage() const {
    Lage l;
    l.ort = ort;
    l.vorne = vorne();
    Vec3 hoch = amBoden ? oben : normiert(kreuz(l.vorne, normiert(kreuz(Vec3(0.0f, 1.0f, 0.0f), l.vorne))));
    if (!amBoden && punkt(hoch, Vec3(0.0f, 1.0f, 0.0f)) < 0.0f) hoch = -hoch;
    Vec3 seite = normiert(kreuz(hoch, l.vorne));
    float s = std::sin(rollen);
    float c = std::cos(rollen);
    l.oben = normiert(hoch * c + seite * s);
    return l;
}

void Fahrzeug::schritt(const Strecke& strecke, const Eingabe& e, float dt) {
    const Vec3 schwere(0.0f, -SCHWERKRAFT, 0.0f);
    aufprall = std::max(0.0f, aufprall - dt * 6.0f);
    wandstoss = std::max(0.0f, wandstoss - dt * 4.0f);
    schub = std::max(0.0f, schub - dt * 2.0f);

    Boden b = strecke.boden(ort + Vec3(0.0f, 0.05f, 0.0f), 0.9f);
    float abstand = b.da ? ort.y - b.hoehe : 999.0f;
    bool kontakt = b.da && abstand <= 0.12f;
    if (!kontakt && amBoden && b.da && abstand <= 0.85f && punkt(fahrt, b.normale) < 3.0f) kontakt = true;

    bodenTeil = b.da ? b.teil : LEER;
    bodenStueck = b.stueck;
    bodenLz = b.lz;
    bodenHoehe = b.da ? b.hoehe : -9999.0f;

    if (kontakt) {
        if (!amBoden) {
            float vn = punkt(fahrt, b.normale);
            if (vn < 0.0f) aufprall = std::max(aufprall, -vn);
            float flach = std::sqrt(fahrt.x * fahrt.x + fahrt.z * fahrt.z);
            if (flach > 2.0f) {
                float bewegung = std::atan2(fahrt.x, fahrt.z);
                float abw = winkelDifferenz(gier, bewegung);
                if (std::fabs(abw) < 1.2f) gier += abw * 0.25f;
            }
        }
        amBoden = true;
        luftzeit = 0.0f;
        ort.y = b.hoehe;
        Vec3 n = b.normale;
        oben = normiert(mische(oben, n, std::min(1.0f, dt * 16.0f)));
        float vn = punkt(fahrt, n);
        fahrt -= n * vn;
        fahrt += (schwere - n * punkt(schwere, n)) * dt;

        Vec3 flachVorne(std::sin(gier), 0.0f, std::cos(gier));
        Vec3 f = normiert(flachVorne - n * punkt(flachVorne, n));
        Vec3 r = kreuz(n, f);
        float vf = punkt(fahrt, f);
        float vs = punkt(fahrt, r);

        float grenze = HOECHSTTEMPO;
        if (e.gas > 0.0f) {
            if (vf >= -0.5f) {
                float anteil = klemme(vf / grenze, 0.0f, 1.3f);
                float zug = 27.0f * std::max(0.0f, 1.0f - anteil * anteil * 0.92f) + 1.5f;
                vf += e.gas * zug * dt;
            } else {
                vf += e.gas * 36.0f * dt;
            }
        }
        if (e.bremse > 0.0f) {
            if (vf > 0.5f) {
                vf -= e.bremse * 38.0f * dt;
            } else if (vf > -15.0f) {
                vf -= e.bremse * 14.0f * dt;
            }
        }
        float reibung = 0.5f + 0.0026f * vf * vf;
        if (e.gas <= 0.0f && e.bremse <= 0.0f) reibung += 2.2f;
        vf -= (vf > 0.0f ? 1.0f : -1.0f) * std::min(std::fabs(vf), reibung * dt);
        if (b.teil == SCHUB && std::fabs(b.lx) < HALBE_BREITE) {
            vf += 46.0f * dt;
            schub = 1.0f;
        }
        vf = klemme(vf, -18.0f, 150.0f);

        float tempoBetrag = std::fabs(vf);
        float maxLenk = 0.5f / (1.0f + tempoBetrag / 18.0f);
        float lenkZiel = e.lenkung * maxLenk;
        bool zurueck = std::fabs(lenkZiel) < std::fabs(lenkwinkel) || lenkZiel * lenkwinkel < 0.0f;
        lenkwinkel = naehern(lenkwinkel, lenkZiel, dt * (zurueck ? 3.2f : 1.7f));

        bool willDriften = e.handbremse && tempoBetrag > 12.0f;
        drift = naehern(drift, willDriften ? 1.0f : 0.0f, dt * (willDriften ? 5.0f : 1.8f));
        if (tempoBetrag < 6.0f) drift = naehern(drift, 0.0f, dt * 4.0f);

        float querGrenze = mische(55.0f, 85.0f, drift);
        float gierRate = vf / RADSTAND * std::tan(lenkwinkel) * (1.0f + drift * 0.9f);
        float deckel = querGrenze / std::max(tempoBetrag, 4.0f);
        gierRate = klemme(gierRate, -deckel, deckel);
        Vec3 welt = f * vf + r * vs;
        gier += gierRate * dt;
        if (gier > PI) gier -= TAU;
        if (gier < -PI) gier += TAU;
        Vec3 neuVorne = normiert(Vec3(std::sin(gier), 0.0f, std::cos(gier)) - n * punkt(Vec3(std::sin(gier), 0.0f, std::cos(gier)), n));
        Vec3 neuRechts = kreuz(n, neuVorne);
        vf = punkt(welt, neuVorne);
        vs = punkt(welt, neuRechts);

        float halt = mische(62.0f, 10.0f, drift);
        float vorherVs = vs;
        vs = naehern(vs, 0.0f, halt * dt);
        float gewonnen = std::fabs(vorherVs - vs) * mische(0.3f, 0.55f, drift);
        vf += gewonnen * (vf >= 0.0f ? 1.0f : -1.0f);
        if (drift > 0.0f) vf -= (vf > 0.0f ? 1.0f : -1.0f) * std::min(std::fabs(vf), drift * 3.0f * dt);
        driftet = std::fabs(vs) > 3.5f;

        Vec3 f2 = normiert(Vec3(std::sin(gier), 0.0f, std::cos(gier)) - n * punkt(Vec3(std::sin(gier), 0.0f, std::cos(gier)), n));
        Vec3 r2 = kreuz(n, f2);
        fahrt = f2 * vf + r2 * vs;
        nick = std::asin(klemme(f2.y, -1.0f, 1.0f));
        rollen = mische(rollen, klemme(-vs * 0.012f + gierRate * vf * 0.0009f, -0.18f, 0.18f), std::min(1.0f, dt * 6.0f));
        radDrehung += vf / RADRADIUS * dt;
    } else {
        amBoden = false;
        luftzeit += dt;
        fahrt += schwere * dt;
        gier += e.lenkung * 0.9f * dt;
        drift = naehern(drift, 0.0f, dt);
        float flach = std::sqrt(fahrt.x * fahrt.x + fahrt.z * fahrt.z);
        float zielNick = klemme(std::atan2(fahrt.y, std::max(flach, 1.0f)), -0.7f, 0.7f);
        zielNick += (e.gas - e.bremse) * 0.25f;
        nick = mische(nick, zielNick, std::min(1.0f, dt * 2.2f));
        rollen = mische(rollen, 0.0f, std::min(1.0f, dt * 2.0f));
        oben = normiert(mische(oben, Vec3(0.0f, 1.0f, 0.0f), std::min(1.0f, dt * 3.0f)));
        radDrehung += (e.gas * 60.0f) * dt;
    }

    Vec3 vorher = ort;
    ort += fahrt * dt;

    if (!amBoden) {
        Boden unten = strecke.boden(ort + Vec3(0.0f, 0.2f, 0.0f), 0.6f);
        if (unten.da && ort.y <= unten.hoehe && vorher.y >= unten.hoehe - 1.2f) {
            float vn = punkt(fahrt, unten.normale);
            if (vn < 0.0f) {
                fahrt -= unten.normale * (vn * 1.08f);
                aufprall = std::max(aufprall, -vn);
            }
            ort.y = unten.hoehe;
            amBoden = true;
            oben = normiert(mische(oben, unten.normale, 0.5f));
        }
    }

    float stoss = strecke.wand(vorher, ort, fahrt, AUTO_RADIUS);
    if (stoss > 0.5f) wandstoss = std::max(wandstoss, std::min(1.0f, stoss / 20.0f));
}

}
