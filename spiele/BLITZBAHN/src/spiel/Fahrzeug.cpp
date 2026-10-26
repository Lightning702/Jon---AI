#include "Fahrzeug.hpp"

#include <algorithm>
#include <cmath>

namespace blitzbahn {

using namespace fw;

namespace {

constexpr float HILFE_ABSTAND = 3.2f;
constexpr float HILFE_STAERKE = 3.4f;
constexpr float SPRUNG_HILFE = 0.45f;

struct Bahnlage {
    float gier = 0.0f;
    float abstand = 99.0f;
    Vec3 nachAussen;
};

bool bahnlage(const Strecke& strecke, int stueck, Vec3 ort, float gier, Bahnlage& lage) {
    if (stueck < 0 || stueck >= static_cast<int>(strecke.stuecke.size())) return false;
    const Stueck& s = strecke.stuecke[stueck];
    if (!teilHatWand(s.teil)) return false;
    Vec3 lokal = weltZuLokal(s, ort);
    Vec3 vorneLokal(0.0f, 0.0f, 1.0f);
    Vec3 aussenLokal(lokal.x >= 0.0f ? 1.0f : -1.0f, 0.0f, 0.0f);
    if (s.teil == KURVE) {
        float dx = lokal.x - ZELLE * 0.5f;
        float dz = lokal.z + ZELLE * 0.5f;
        float d = std::sqrt(dx * dx + dz * dz);
        if (d < 1e-3f) return false;
        Vec3 radial(dx / d, 0.0f, dz / d);
        vorneLokal = Vec3(-radial.z, 0.0f, radial.x);
        float innen = d - KURVE_INNEN;
        float aussen = KURVE_AUSSEN - d;
        lage.abstand = std::min(innen, aussen) - AUTO_RADIUS;
        aussenLokal = aussen < innen ? radial : -radial;
    } else {
        if (std::fabs(lokal.z) > ZELLE * 0.5f) return false;
        lage.abstand = HALBE_BREITE - std::fabs(lokal.x) - AUTO_RADIUS;
    }
    Vec3 vorne = richtungWelt(s.dreh, vorneLokal);
    float bahn = std::atan2(vorne.x, vorne.z);
    if (std::fabs(winkelDifferenz(gier, bahn)) > PI * 0.5f) bahn += PI;
    if (bahn > PI) bahn -= TAU;
    lage.gier = bahn;
    lage.nachAussen = richtungWelt(s.dreh, aussenLokal);
    return true;
}

}

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
    kontaktStueck = -1;
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
        kontaktStueck = b.stueck;
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
        float maxLenk = 0.5f / (1.0f + tempoBetrag / 30.0f);
        float lenkZiel = e.lenkung * maxLenk;
        bool zurueck = std::fabs(lenkZiel) < std::fabs(lenkwinkel) || lenkZiel * lenkwinkel < 0.0f;
        lenkwinkel = naehern(lenkwinkel, lenkZiel, dt * (zurueck ? 3.2f : 1.7f));

        bool willDriften = e.handbremse && tempoBetrag > 12.0f;
        drift = naehern(drift, willDriften ? 1.0f : 0.0f, dt * (willDriften ? 5.0f : 1.8f));
        if (tempoBetrag < 6.0f) drift = naehern(drift, 0.0f, dt * 4.0f);

        float griff = mische(92.0f, 55.0f, klemme((tempoBetrag - 26.0f) / 20.0f, 0.0f, 1.0f));
        float querGrenze = mische(griff, griff + 30.0f, drift);
        float gierRate = vf / RADSTAND * std::tan(lenkwinkel) * (1.0f + drift * 0.9f);
        float deckel = querGrenze / std::max(tempoBetrag, 4.0f);
        gierRate = klemme(gierRate, -deckel, deckel);
        Vec3 welt = f * vf + r * vs;
        gier += gierRate * dt;
        Bahnlage bahn;
        if (fahrhilfe && drift < 0.3f && tempoBetrag > 4.0f && bahnlage(strecke, b.stueck, ort, gier, bahn) && bahn.abstand < HILFE_ABSTAND) {
            float naehe = klemme(1.0f - bahn.abstand / HILFE_ABSTAND, 0.0f, 1.0f);
            float zurWand = punkt(welt, bahn.nachAussen);
            float abw = winkelDifferenz(gier, bahn.gier);
            Vec3 lenkRichtung(std::sin(gier + abw), 0.0f, std::cos(gier + abw));
            Vec3 jetzt(std::sin(gier), 0.0f, std::cos(gier));
            bool weg = punkt(lenkRichtung - jetzt, bahn.nachAussen) < 0.0f;
            Vec3 rechtsJetzt = kreuz(n, jetzt);
            float spielerZurWand = e.lenkung * punkt(rechtsJetzt, bahn.nachAussen);
            if (zurWand > 0.5f && weg && spielerZurWand < 0.1f) gier += abw * std::min(1.0f, naehe * naehe * HILFE_STAERKE * dt);
        }
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
        if (fahrhilfe && amBoden && kontaktStueck >= 0 && kontaktStueck < static_cast<int>(strecke.stuecke.size()) &&
            strecke.stuecke[kontaktStueck].teil == SCHANZE) {
            Vec3 sprungRichtung = richtungWelt(strecke.stuecke[kontaktStueck].dreh, Vec3(0.0f, 0.0f, 1.0f));
            float flug = std::atan2(fahrt.x, fahrt.z);
            float bahn = std::atan2(sprungRichtung.x, sprungRichtung.z);
            if (std::fabs(winkelDifferenz(flug, bahn)) > PI * 0.5f) bahn += PI;
            float abw = winkelDifferenz(flug, bahn);
            if (std::fabs(abw) < SPRUNG_HILFE) {
                float drehen = abw * 0.9f;
                float c = std::cos(drehen);
                float s = std::sin(drehen);
                fahrt = Vec3(fahrt.x * c + fahrt.z * s, fahrt.y, -fahrt.x * s + fahrt.z * c);
                gier += drehen;
            }
        }
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

    Vec3 wandNormale;
    float stoss = strecke.wand(vorher, ort, fahrt, AUTO_RADIUS, &wandNormale);
    if (stoss > 0.5f) {
        wandstoss = std::max(wandstoss, std::min(1.0f, stoss / 20.0f));
        float flach = std::sqrt(fahrt.x * fahrt.x + fahrt.z * fahrt.z);
        if (amBoden && flach > 2.0f) {
            float entlang = std::atan2(fahrt.x, fahrt.z);
            float abw = winkelDifferenz(gier, entlang);
            if (std::fabs(abw) < PI * 0.6f) gier += abw * std::min(1.0f, 0.35f + stoss / 25.0f);
            if (gier > PI) gier -= TAU;
            if (gier < -PI) gier += TAU;
        }
    }
}

}
