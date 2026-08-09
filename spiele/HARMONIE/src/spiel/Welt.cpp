#include "Welt.hpp"

#include <algorithm>

#include "Farben.hpp"

namespace harmonie {
namespace {

using namespace fw;

float inselMaske(const Insel& stueck, float x, float z) {
    float dx = x - stueck.mitte.x;
    float dz = z - stueck.mitte.y;
    float r = std::sqrt(dx * dx + dz * dz);
    float wellig = bergRauschen(x * 0.045f, z * 0.045f, 91, 3) - 0.5f;
    float grenze = stueck.radius * (1.0f + wellig * 0.16f);
    return 1.0f - sanft(grenze * 0.68f, grenze, r);
}

float inselHoehe(const Insel& stueck, float x, float z) {
    float f = inselMaske(stueck, x, z);
    if (f <= 0.0f) return 0.0f;
    float dx = x - stueck.mitte.x;
    float dz = z - stueck.mitte.y;
    float r = std::sqrt(dx * dx + dz * dz) / stueck.radius;
    float rauschen = bergRauschen(x * 0.12f, z * 0.12f, 17, 4) - 0.5f;
    float h = stueck.hoehe * f;
    switch (stueck.art) {
        case Bezirk::Herz: {
            float stufe = std::floor(f * 3.0f);
            h = stueck.hoehe * f * 0.62f + stufe * 0.78f;
            if (r < 0.3f) h = stueck.hoehe * 0.62f + 2.34f;
            h += rauschen * 0.4f * f;
            break;
        }
        case Bezirk::Farm: {
            h = stueck.hoehe * f + rauschen * 1.05f * f;
            h += std::sin(x * 0.35f) * 0.12f * f;
            break;
        }
        case Bezirk::Berg: {
            float kegel = std::pow(f, 2.3f) * 15.5f;
            h = stueck.hoehe * f * 0.6f + kegel;
            h = std::floor(h / 1.7f) * 1.7f + rauschen * 0.5f * f;
            break;
        }
        case Bezirk::Werft: {
            h = stueck.hoehe * f * 0.85f + rauschen * 0.55f * f;
            break;
        }
        default:
            break;
    }
    return h > 0.0f ? h : 0.0f;
}

Vec3 landfarbe(Bezirk art, float hoehe, float neigung, float x, float z) {
    float fleck = bergRauschen(x * 0.28f, z * 0.28f, 55, 3);
    Vec3 sand = mische(FARBE_SAND, FARBE_SAND_DUNKEL, fleck);
    Vec3 wiese = mische(FARBE_GRAS_HELL, FARBE_GRAS_TIEF, fleck * 0.75f + 0.15f);
    Vec3 stein = mische(FARBE_FELS, FARBE_FELS_HELL, fleck);
    if (hoehe < 0.7f) return mische(sand, wiese, sanft(0.2f, 0.8f, hoehe));
    if (art == Bezirk::Berg && hoehe > 4.5f) {
        Vec3 boden = mische(wiese, stein, sanft(4.5f, 6.5f, hoehe));
        boden = mische(boden, FARBE_FELS_HELL, sanft(9.5f, 14.0f, hoehe));
        return mische(boden, stein * 0.92f, sanft(0.6f, 0.95f, neigung) * 0.5f);
    }
    Vec3 basis = mische(wiese, FARBE_GRAS_TIEF, sanft(2.0f, 7.0f, hoehe) * 0.45f);
    return mische(basis, FARBE_ERDE, sanft(0.72f, 0.99f, neigung) * 0.75f);
}

}

void Welt::erzeugen(unsigned saat) {
    saatwert = saat;
    inselnAnlegen();

    Zufall wuerfel(saat * 6364136223846793005ull + 1442695040888963407ull);
    fundListe.clear();
    tierListe.clear();

    const Insel& farm = insel(Bezirk::Farm);
    for (int i = 0; i < 26; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = std::sqrt(wuerfel.einheit()) * farm.radius * 0.62f;
        Vec3 ort(farm.mitte.x + std::cos(winkel) * weite, 0.0f, farm.mitte.y + std::sin(winkel) * weite);
        ort.y = hoeheBei(ort.x, ort.z);
        if (ort.y < 0.6f) continue;
        Fundort feld;
        feld.gabe = Gabe::Korn;
        feld.ort = ort;
        feld.reife = wuerfel.bereich(0.4f, 1.0f);
        fundListe.push_back(feld);
    }

    const Insel& berg = insel(Bezirk::Berg);
    for (int i = 0; i < 18; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = std::sqrt(wuerfel.einheit()) * berg.radius * 0.72f;
        Vec3 ort(berg.mitte.x + std::cos(winkel) * weite, 0.0f, berg.mitte.y + std::sin(winkel) * weite);
        ort.y = hoeheBei(ort.x, ort.z);
        if (ort.y < 0.8f) continue;
        Fundort ader;
        ader.gabe = Gabe::Stein;
        ader.ort = ort;
        ader.reife = wuerfel.bereich(0.5f, 1.0f);
        fundListe.push_back(ader);
    }

    const Insel& herz = insel(Bezirk::Herz);
    for (int i = 0; i < 10; ++i) {
        float winkel = static_cast<float>(i) / 10.0f * TAU + 0.3f;
        float weite = herz.radius * 0.55f;
        Vec3 ort(herz.mitte.x + std::cos(winkel) * weite, 0.0f, herz.mitte.y + std::sin(winkel) * weite);
        ort.y = hoeheBei(ort.x, ort.z);
        Fundort stapel;
        stapel.gabe = Gabe::Brett;
        stapel.ort = ort;
        stapel.reife = 1.0f;
        fundListe.push_back(stapel);
    }

    for (int i = 0; i < 14; ++i) {
        Tier tier;
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = std::sqrt(wuerfel.einheit()) * farm.radius * 0.55f;
        tier.ort = Vec3(farm.mitte.x + std::cos(winkel) * weite, 0.0f,
                        farm.mitte.y + std::sin(winkel) * weite);
        tier.ort.y = hoeheBei(tier.ort.x, tier.ort.z);
        tier.richtung = wuerfel.bereich(0.0f, TAU);
        tier.art = wuerfel.ganz(0, 3);
        tier.takt = wuerfel.bereich(0.0f, TAU);
        tierListe.push_back(tier);
    }
}

void Welt::inselnAnlegen() {
    inselListe.clear();
    Insel herz;
    herz.art = Bezirk::Herz;
    herz.mitte = Vec2(0.0f, 0.0f);
    herz.radius = 27.0f;
    herz.hoehe = 4.6f;
    herz.name = "Herzinsel";
    inselListe.push_back(herz);

    Insel farm;
    farm.art = Bezirk::Farm;
    farm.mitte = Vec2(-52.0f, -14.0f);
    farm.radius = 18.0f;
    farm.hoehe = 3.2f;
    farm.name = "Halminsel";
    inselListe.push_back(farm);

    Insel berg;
    berg.art = Bezirk::Berg;
    berg.mitte = Vec2(44.0f, -34.0f);
    berg.radius = 17.0f;
    berg.hoehe = 4.0f;
    berg.name = "Steinmutter";
    inselListe.push_back(berg);

    Insel werft;
    werft.art = Bezirk::Werft;
    werft.mitte = Vec2(40.0f, 34.0f);
    werft.radius = 16.0f;
    werft.hoehe = 3.0f;
    werft.name = "Werftinsel";
    inselListe.push_back(werft);

    brueckenListe.clear();
    for (const Insel& stueck : inselListe) {
        if (stueck.art == Bezirk::Herz) continue;
        Vec2 richtung = Vec2(stueck.mitte.x - herz.mitte.x, stueck.mitte.y - herz.mitte.y);
        float weite = laenge(richtung);
        if (weite < 1.0f) continue;
        Vec2 einheit = richtung * (1.0f / weite);
        Bruecke bruecke;
        float startWeite = herz.radius * 0.9f;
        float endWeite = weite - stueck.radius * 0.9f;
        bruecke.von = Vec3(herz.mitte.x + einheit.x * startWeite, 0.0f, herz.mitte.y + einheit.y * startWeite);
        bruecke.bis = Vec3(herz.mitte.x + einheit.x * endWeite, 0.0f, herz.mitte.y + einheit.y * endWeite);
        bruecke.von.y = hoeheBei(bruecke.von.x, bruecke.von.z);
        bruecke.bis.y = hoeheBei(bruecke.bis.x, bruecke.bis.z);
        brueckenListe.push_back(bruecke);
    }

    const Insel& werftInsel = insel(Bezirk::Werft);
    leuchtturm = Vec3(werftInsel.mitte.x + 2.0f, 0.0f, werftInsel.mitte.y - 1.0f);
    leuchtturm.y = hoeheBei(leuchtturm.x, leuchtturm.z);
    werkstatt = Vec3(0.0f, 0.0f, 0.0f);
    werkstatt.y = hoeheBei(0.0f, 0.0f);
    const Insel& bergInsel = insel(Bezirk::Berg);
    bogenOrt = Vec3(bergInsel.mitte.x, 0.5f, bergInsel.mitte.y);
}

const Insel& Welt::insel(Bezirk art) const {
    for (const Insel& stueck : inselListe) {
        if (stueck.art == art) return stueck;
    }
    return inselListe.front();
}

Vec3 Welt::mittelpunkt(Bezirk art) const {
    const Insel& stueck = insel(art);
    return Vec3(stueck.mitte.x, hoeheBei(stueck.mitte.x, stueck.mitte.y), stueck.mitte.y);
}

float Welt::hoeheBei(float x, float z) const {
    float hoechste = 0.0f;
    for (const Insel& stueck : inselListe) {
        float h = inselHoehe(stueck, x, z);
        if (h > hoechste) hoechste = h;
    }
    return hoechste;
}

bool Welt::aufLand(float x, float z, float rand) const {
    for (const Insel& stueck : inselListe) {
        float dx = x - stueck.mitte.x;
        float dz = z - stueck.mitte.y;
        if (std::sqrt(dx * dx + dz * dz) > stueck.radius - rand) continue;
        if (inselHoehe(stueck, x, z) > 0.32f) return true;
    }
    return false;
}

bool Welt::aufBruecke(float x, float z, float& hoehe) const {
    for (const Bruecke& bruecke : brueckenListe) {
        Vec3 richtung = bruecke.bis - bruecke.von;
        float laengeQuadratXZ = richtung.x * richtung.x + richtung.z * richtung.z;
        if (laengeQuadratXZ < 1e-4f) continue;
        float t = ((x - bruecke.von.x) * richtung.x + (z - bruecke.von.z) * richtung.z) / laengeQuadratXZ;
        if (t < -0.04f || t > 1.04f) continue;
        float klemmt = klemme(t, 0.0f, 1.0f);
        float px = bruecke.von.x + richtung.x * klemmt;
        float pz = bruecke.von.z + richtung.z * klemmt;
        float abstand = std::sqrt((x - px) * (x - px) + (z - pz) * (z - pz));
        if (abstand > 1.7f) continue;
        float bogenHub = std::sin(klemmt * PI) * 0.9f;
        hoehe = mische(bruecke.von.y, bruecke.bis.y, klemmt) + 0.45f + bogenHub;
        return true;
    }
    return false;
}

float Welt::bodenBei(float x, float z) const {
    float land = hoeheBei(x, z);
    float steg = 0.0f;
    if (aufBruecke(x, z, steg) && steg > land) return steg;
    return land;
}

void Welt::freigeben() {
    land.freigeben();
    bauten.freigeben();
    gruen.freigeben();
    wasser.freigeben();
    turm.freigeben();
    fern.freigeben();
    boote.freigeben();
    regenbogen.freigeben();
    schatten.freigeben();
}

void Welt::netzeBauen() {
    Bauer boden;
    landFormen(boden);
    land.hochladen(boden);

    Bauer haeuser;
    Bauer laub;
    schattenOrte.clear();
    bruecken(haeuser);
    herzBebauen(haeuser, laub);
    farmBebauen(haeuser, laub);
    bergBebauen(haeuser, laub);
    werftBebauen(haeuser, laub);
    bauten.hochladen(haeuser);
    gruen.hochladen(laub);

    Bauer dunkel;
    schattenFormen(dunkel);
    schatten.hochladen(dunkel);

    Bauer see;
    wasserFormen(see);
    wasser.hochladen(see);

    Bauer weite;
    ferneInseln(weite);
    fern.hochladen(weite);

    Bauer schiffe;
    booteBauen(schiffe);
    boote.hochladen(schiffe);

    Bauer bogen;
    regenbogenBauen(bogen);
    regenbogen.hochladen(bogen);

    turmBauen();
}

void Welt::landFormen(Bauer& bauer) {
    for (const Insel& stueck : inselListe) inselFormen(bauer, stueck);
}

void Welt::inselFormen(Bauer& bauer, const Insel& stueck) {
    const float schritt = detail >= 2 ? 0.85f : 1.25f;
    const float weite = stueck.radius * 1.12f;
    const int schritte = static_cast<int>(weite * 2.0f / schritt);
    std::vector<Vec3> punkte(static_cast<size_t>(schritte + 1) * (schritte + 1));
    for (int iz = 0; iz <= schritte; ++iz) {
        for (int ix = 0; ix <= schritte; ++ix) {
            float x = stueck.mitte.x - weite + static_cast<float>(ix) * schritt;
            float z = stueck.mitte.y - weite + static_cast<float>(iz) * schritt;
            punkte[static_cast<size_t>(iz) * (schritte + 1) + ix] = Vec3(x, inselHoehe(stueck, x, z), z);
        }
    }
    for (int iz = 0; iz < schritte; ++iz) {
        for (int ix = 0; ix < schritte; ++ix) {
            const Vec3& a = punkte[static_cast<size_t>(iz) * (schritte + 1) + ix];
            const Vec3& b = punkte[static_cast<size_t>(iz) * (schritte + 1) + ix + 1];
            const Vec3& c = punkte[static_cast<size_t>(iz + 1) * (schritte + 1) + ix + 1];
            const Vec3& d = punkte[static_cast<size_t>(iz + 1) * (schritte + 1) + ix];
            if (a.y <= 0.001f && b.y <= 0.001f && c.y <= 0.001f && d.y <= 0.001f) continue;
            Vec3 mitte = (a + b + c + d) * 0.25f;
            Vec3 normale = normiert(kreuz(d - a, b - a));
            float neigung = 1.0f - klemme(normale.y, 0.0f, 1.0f);
            Vec3 farbe = landfarbe(stueck.art, mitte.y, neigung, mitte.x, mitte.z);
            bauer.viereck(a, d, c, b, farbe);
        }
    }

    const int ringe = 40;
    float tiefe = stueck.radius * 0.85f;
    std::vector<Vec3> rand(ringe);
    for (int i = 0; i < ringe; ++i) {
        float winkel = static_cast<float>(i) / static_cast<float>(ringe) * TAU;
        float suche = stueck.radius * 1.05f;
        float x = stueck.mitte.x + std::cos(winkel) * suche;
        float z = stueck.mitte.y + std::sin(winkel) * suche;
        while (suche > stueck.radius * 0.4f && inselHoehe(stueck, x, z) < 0.02f) {
            suche -= 0.35f;
            x = stueck.mitte.x + std::cos(winkel) * suche;
            z = stueck.mitte.y + std::sin(winkel) * suche;
        }
        rand[i] = Vec3(x, inselHoehe(stueck, x, z), z);
    }
    Vec3 spitze(stueck.mitte.x, -tiefe, stueck.mitte.y);
    for (int i = 0; i < ringe; ++i) {
        const Vec3& a = rand[i];
        const Vec3& b = rand[(i + 1) % ringe];
        float welle = bergRauschen(a.x * 0.09f, a.z * 0.09f, 33, 2);
        Vec3 mitteA = mische(Vec3(a.x, -tiefe * 0.42f, a.z), spitze, 0.45f);
        mitteA.y += welle * 1.6f;
        Vec3 mitteB = mische(Vec3(b.x, -tiefe * 0.42f, b.z), spitze, 0.45f);
        mitteB.y += welle * 1.4f;
        bauer.viereck(a, b, mitteB, mitteA, FARBE_ERDE);
        bauer.dreieck(mitteA, mitteB, spitze, FARBE_FELS_TIEF);
    }
    for (int i = 0; i < 5; ++i) {
        float winkel = static_cast<float>(i) / 5.0f * TAU + 0.7f;
        float weiteWurzel = stueck.radius * 0.55f;
        Vec3 fuss(stueck.mitte.x + std::cos(winkel) * weiteWurzel, -tiefe * 0.35f,
                  stueck.mitte.y + std::sin(winkel) * weiteWurzel);
        bauer.roehre(Vec3(fuss.x, fuss.y - tiefe * 0.5f, fuss.z), 0.0f, 0.9f, tiefe * 0.5f,
                     FARBE_FELS_TIEF, 7);
    }
}

void Welt::wasserFormen(Bauer& bauer) {
    const float weite = 190.0f;
    const float schritt = detail >= 2 ? 5.0f : 8.0f;
    const int schritte = static_cast<int>(weite * 2.0f / schritt);
    for (int iz = 0; iz < schritte; ++iz) {
        for (int ix = 0; ix < schritte; ++ix) {
            float x0 = -weite + static_cast<float>(ix) * schritt;
            float z0 = -weite + static_cast<float>(iz) * schritt;
            float x1 = x0 + schritt;
            float z1 = z0 + schritt;
            auto tiefenfarbe = [&](float x, float z) {
                float naehe = 1000.0f;
                for (const Insel& stueck : inselListe) {
                    float dx = x - stueck.mitte.x;
                    float dz = z - stueck.mitte.y;
                    float abstand = std::sqrt(dx * dx + dz * dz) - stueck.radius;
                    if (abstand < naehe) naehe = abstand;
                }
                float flach = 1.0f - sanft(0.0f, 26.0f, naehe);
                return mische(FARBE_WASSER_TIEF, FARBE_WASSER_FLACH, flach * flach);
            };
            Vec3 a(x0, 0.0f, z0);
            Vec3 b(x1, 0.0f, z0);
            Vec3 c(x1, 0.0f, z1);
            Vec3 d(x0, 0.0f, z1);
            Vec3 farbe = tiefenfarbe((x0 + x1) * 0.5f, (z0 + z1) * 0.5f);
            bauer.viereck(a, d, c, b, farbe, 0.85f);
        }
    }
    for (const Insel& stueck : inselListe) {
        const int ringe = 46;
        for (int i = 0; i < ringe; ++i) {
            float w0 = static_cast<float>(i) / static_cast<float>(ringe) * TAU;
            float w1 = static_cast<float>(i + 1) / static_cast<float>(ringe) * TAU;
            float innen = stueck.radius * 0.97f;
            float aussen = stueck.radius * 1.14f;
            Vec3 a(stueck.mitte.x + std::cos(w0) * innen, 0.12f, stueck.mitte.y + std::sin(w0) * innen);
            Vec3 b(stueck.mitte.x + std::cos(w1) * innen, 0.12f, stueck.mitte.y + std::sin(w1) * innen);
            Vec3 c(stueck.mitte.x + std::cos(w1) * aussen, 0.08f, stueck.mitte.y + std::sin(w1) * aussen);
            Vec3 d(stueck.mitte.x + std::cos(w0) * aussen, 0.08f, stueck.mitte.y + std::sin(w0) * aussen);
            bauer.viereck(a, d, c, b, FARBE_SCHAUM, 0.4f);
        }
    }
}

void Welt::bruecken(Bauer& bauer) {
    for (const Bruecke& bruecke : brueckenListe) {
        const int felder = 16;
        Vec3 richtung = bruecke.bis - bruecke.von;
        for (int i = 0; i < felder; ++i) {
            float t0 = static_cast<float>(i) / felder;
            float t1 = static_cast<float>(i + 1) / felder;
            Vec3 a = bruecke.von + richtung * t0;
            Vec3 b = bruecke.von + richtung * t1;
            a.y = mische(bruecke.von.y, bruecke.bis.y, t0) + 0.45f + std::sin(t0 * PI) * 0.9f;
            b.y = mische(bruecke.von.y, bruecke.bis.y, t1) + 0.45f + std::sin(t1 * PI) * 0.9f;
            Vec3 holz = (i % 2 == 0) ? FARBE_HOLZ : FARBE_HOLZ_DUNKEL;
            bauer.band(a, b, 2.9f, 0.22f, holz);
        }
        Vec3 quer = normiert(Vec3(-richtung.z, 0.0f, richtung.x));
        for (int i = 0; i <= 8; ++i) {
            float t = static_cast<float>(i) / 8.0f;
            Vec3 mitte = bruecke.von + richtung * t;
            mitte.y = mische(bruecke.von.y, bruecke.bis.y, t) + 0.45f + std::sin(t * PI) * 0.9f;
            for (float seite : {-1.0f, 1.0f}) {
                Vec3 pfosten = mitte + quer * (seite * 1.45f);
                bauer.quader(pfosten + Vec3(0.0f, 0.55f, 0.0f), Vec3(0.11f, 0.55f, 0.11f),
                             FARBE_HOLZ_DUNKEL);
            }
        }
        for (float seite : {-1.0f, 1.0f}) {
            for (int i = 0; i < 8; ++i) {
                float t0 = static_cast<float>(i) / 8.0f;
                float t1 = static_cast<float>(i + 1) / 8.0f;
                Vec3 a = bruecke.von + richtung * t0 + quer * (seite * 1.45f);
                Vec3 b = bruecke.von + richtung * t1 + quer * (seite * 1.45f);
                a.y = mische(bruecke.von.y, bruecke.bis.y, t0) + 1.05f + std::sin(t0 * PI) * 0.9f;
                b.y = mische(bruecke.von.y, bruecke.bis.y, t1) + 1.05f + std::sin(t1 * PI) * 0.9f;
                bauer.band(a, b, 0.16f, 0.1f, FARBE_SEIL);
            }
        }
    }
}

void Welt::schattenMerken(Vec3 ort, float radius) {
    schattenOrte.push_back(Vec3(ort.x, radius, ort.z));
}

void Welt::schattenFormen(Bauer& bauer) {
    const Vec3 farbe(0.14f, 0.12f, 0.18f);
    for (const Vec3& eintrag : schattenOrte) {
        float radius = eintrag.y;
        float grund = hoeheBei(eintrag.x, eintrag.z);
        if (grund < 0.2f) continue;
        Vec3 mitte(eintrag.x + radius * 0.35f, grund + 0.07f, eintrag.z + radius * 0.25f);
        const int segmente = 12;
        for (int i = 0; i < segmente; ++i) {
            float w0 = static_cast<float>(i) / segmente * TAU;
            float w1 = static_cast<float>(i + 1) / segmente * TAU;
            Vec3 a = mitte + Vec3(std::cos(w0) * radius * 1.25f, 0.0f, std::sin(w0) * radius);
            Vec3 b = mitte + Vec3(std::cos(w1) * radius * 1.25f, 0.0f, std::sin(w1) * radius);
            a.y = hoeheBei(a.x, a.z) + 0.07f;
            b.y = hoeheBei(b.x, b.z) + 0.07f;
            bauer.dreieck(mitte, b, a, farbe);
        }
    }
}

void Welt::baum(Bauer& stamm, Bauer& laub, Vec3 fuss, float mass, Vec3 laubfarbe) {
    schattenMerken(fuss, 1.25f * mass);
    stamm.roehre(fuss, 0.28f * mass, 0.2f * mass, 1.9f * mass, FARBE_HOLZ_DUNKEL, 7);
    Vec3 krone = fuss + Vec3(0.0f, 2.3f * mass, 0.0f);
    laub.kugel(krone, Vec3(1.35f * mass, 1.15f * mass, 1.35f * mass), laubfarbe, 6, 9);
    laub.kugel(krone + Vec3(0.6f * mass, 0.55f * mass, -0.35f * mass),
               Vec3(0.95f * mass, 0.85f * mass, 0.95f * mass), laubfarbe * 1.08f, 5, 8);
    laub.kugel(krone + Vec3(-0.55f * mass, 0.35f * mass, 0.5f * mass),
               Vec3(0.85f * mass, 0.75f * mass, 0.85f * mass), laubfarbe * 0.92f, 5, 8);
}

void Welt::stand(Bauer& bauer, Vec3 fuss, float drehung, Vec3 stoff) {
    schattenMerken(fuss, 1.2f);
    float s = std::sin(drehung);
    float c = std::cos(drehung);
    auto dreh = [&](Vec3 p) { return Vec3(p.x * c + p.z * s, p.y, -p.x * s + p.z * c) + fuss; };
    for (float sx : {-1.0f, 1.0f}) {
        for (float sz : {-1.0f, 1.0f}) {
            bauer.quader(dreh(Vec3(sx * 0.95f, 0.75f, sz * 0.7f)), Vec3(0.09f, 0.75f, 0.09f),
                         FARBE_HOLZ_DUNKEL);
        }
    }
    bauer.quader(dreh(Vec3(0.0f, 0.95f, 0.0f)), Vec3(1.05f, 0.09f, 0.8f), FARBE_HOLZ);
    for (int i = 0; i < 5; ++i) {
        float x = -0.7f + static_cast<float>(i) * 0.35f;
        bauer.kugel(dreh(Vec3(x, 1.15f, 0.0f)), Vec3(0.16f, 0.16f, 0.16f),
                    i % 2 == 0 ? FARBE_FRUCHT : FARBE_FRUCHT_ZWEI, 5, 7);
    }
    Vec3 first = dreh(Vec3(0.0f, 1.95f, 0.0f));
    for (float sz : {-1.0f, 1.0f}) {
        Vec3 kante = dreh(Vec3(0.0f, 1.45f, sz * 0.95f));
        Vec3 links = dreh(Vec3(-1.15f, 1.45f, sz * 0.95f));
        Vec3 rechts = dreh(Vec3(1.15f, 1.45f, sz * 0.95f));
        Vec3 firstLinks = dreh(Vec3(-1.15f, 1.95f, 0.0f));
        Vec3 firstRechts = dreh(Vec3(1.15f, 1.95f, 0.0f));
        bauer.viereck(links, rechts, firstRechts, firstLinks, stoff);
        (void)kante;
    }
    bauer.quader(dreh(Vec3(0.0f, 1.97f, 0.0f)), Vec3(1.2f, 0.05f, 0.06f), stoff * 0.85f);
    (void)first;
}

void Welt::haus(Bauer& bauer, Vec3 fuss, float breite, float tiefe, float hoehe, float drehung,
                Vec3 wandfarbe, Vec3 dachfarbe) {
    schattenMerken(fuss, (breite + tiefe) * 0.62f);
    bauer.quader(fuss + Vec3(0.0f, hoehe * 0.5f, 0.0f), Vec3(breite, hoehe * 0.5f, tiefe), wandfarbe,
                 drehung);
    float s = std::sin(drehung);
    float c = std::cos(drehung);
    auto dreh = [&](Vec3 p) { return Vec3(p.x * c + p.z * s, p.y, -p.x * s + p.z * c) + fuss; };
    Vec3 firstA = dreh(Vec3(-breite - 0.25f, hoehe + tiefe * 0.85f, 0.0f));
    Vec3 firstB = dreh(Vec3(breite + 0.25f, hoehe + tiefe * 0.85f, 0.0f));
    Vec3 e00 = dreh(Vec3(-breite - 0.35f, hoehe, -tiefe - 0.35f));
    Vec3 e10 = dreh(Vec3(breite + 0.35f, hoehe, -tiefe - 0.35f));
    Vec3 e11 = dreh(Vec3(breite + 0.35f, hoehe, tiefe + 0.35f));
    Vec3 e01 = dreh(Vec3(-breite - 0.35f, hoehe, tiefe + 0.35f));
    bauer.viereck(e00, e10, firstB, firstA, dachfarbe);
    bauer.viereck(e11, e01, firstA, firstB, dachfarbe * 0.92f);
    bauer.dreieck(e00, firstA, e01, dachfarbe * 0.8f);
    bauer.dreieck(e10, e11, firstB, dachfarbe * 0.8f);
    bauer.quader(dreh(Vec3(0.0f, hoehe * 0.42f, tiefe + 0.02f)), Vec3(breite * 0.24f, hoehe * 0.42f, 0.06f),
                 FARBE_HOLZ_DUNKEL, drehung);
    for (float sx : {-1.0f, 1.0f}) {
        bauer.quader(dreh(Vec3(sx * breite * 0.55f, hoehe * 0.62f, tiefe + 0.02f)),
                     Vec3(breite * 0.16f, hoehe * 0.18f, 0.05f), FARBE_FENSTER, drehung);
    }
}

void Welt::zaun(Bauer& bauer, Vec3 von, Vec3 bis, Vec3 farbe) {
    Vec3 richtung = bis - von;
    float weite = std::sqrt(richtung.x * richtung.x + richtung.z * richtung.z);
    int pfosten = static_cast<int>(weite / 1.6f) + 1;
    for (int i = 0; i <= pfosten; ++i) {
        float t = static_cast<float>(i) / static_cast<float>(pfosten);
        Vec3 ort = von + richtung * t;
        ort.y = hoeheBei(ort.x, ort.z);
        bauer.quader(ort + Vec3(0.0f, 0.45f, 0.0f), Vec3(0.08f, 0.45f, 0.08f), farbe);
    }
    for (int i = 0; i < pfosten; ++i) {
        float t0 = static_cast<float>(i) / static_cast<float>(pfosten);
        float t1 = static_cast<float>(i + 1) / static_cast<float>(pfosten);
        Vec3 a = von + richtung * t0;
        Vec3 b = von + richtung * t1;
        a.y = hoeheBei(a.x, a.z) + 0.62f;
        b.y = hoeheBei(b.x, b.z) + 0.62f;
        bauer.band(a, b, 0.09f, 0.09f, farbe);
    }
}

void Welt::herzBebauen(Bauer& bauer, Bauer& laub) {
    const Insel& herz = insel(Bezirk::Herz);
    Zufall wuerfel(saatwert * 31u + 5u);
    Vec3 mitte(herz.mitte.x, hoeheBei(herz.mitte.x, herz.mitte.y), herz.mitte.y);

    for (int i = 0; i < 12; ++i) {
        float winkel = static_cast<float>(i) / 12.0f * TAU;
        Vec3 ort(mitte.x + std::cos(winkel) * 9.5f, 0.0f, mitte.z + std::sin(winkel) * 9.5f);
        ort.y = hoeheBei(ort.x, ort.z);
        bauer.roehre(ort, 0.32f, 0.26f, 2.4f, FARBE_HOLZ, 8);
        bauer.kugel(ort + Vec3(0.0f, 2.6f, 0.0f), Vec3(0.3f, 0.3f, 0.3f), FARBE_LATERNE, 5, 8);
    }

    bauer.roehre(mitte + Vec3(0.0f, 0.0f, 0.0f), 6.2f, 6.0f, 0.35f, FARBE_PFLASTER, 26);
    for (int i = 0; i < 10; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(11.0f, 17.0f);
        Vec3 ort(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        ort.y = hoeheBei(ort.x, ort.z);
        Vec3 stoff = FARBE_STAND[i % 5];
        stand(bauer, ort, winkel + PI * 0.5f, stoff);
    }

    Vec3 werkstattOrt(mitte.x - 2.5f, 0.0f, mitte.z + 3.5f);
    werkstattOrt.y = hoeheBei(werkstattOrt.x, werkstattOrt.z);
    for (int i = 0; i < 14; ++i) {
        float w0 = static_cast<float>(i) / 14.0f * TAU;
        float w1 = static_cast<float>(i + 1) / 14.0f * TAU;
        if (i >= 3 && i <= 5) continue;
        Vec3 a = werkstattOrt + Vec3(std::cos(w0) * 3.4f, 0.0f, std::sin(w0) * 3.4f);
        Vec3 b = werkstattOrt + Vec3(std::cos(w1) * 3.4f, 0.0f, std::sin(w1) * 3.4f);
        bauer.quader((a + b) * 0.5f + Vec3(0.0f, 1.1f, 0.0f), Vec3(0.85f, 1.1f, 0.16f), FARBE_LEHM,
                     -std::atan2(b.z - a.z, b.x - a.x));
    }
    bauer.roehre(werkstattOrt + Vec3(0.0f, 2.2f, 0.0f), 3.9f, 0.25f, 2.3f, FARBE_DACH_ZIEGEL, 16);
    bauer.roehre(werkstattOrt + Vec3(0.0f, 0.02f, 0.0f), 3.3f, 3.3f, 0.12f, FARBE_HOLZ, 16);
    bauer.quader(werkstattOrt + Vec3(1.4f, 0.55f, 0.0f), Vec3(0.8f, 0.55f, 0.5f), FARBE_HOLZ_DUNKEL);
    bauer.quader(werkstattOrt + Vec3(-1.3f, 0.35f, 0.9f), Vec3(0.55f, 0.35f, 0.55f), FARBE_HOLZ);

    Vec3 gilde(mitte.x + 8.5f, 0.0f, mitte.z - 7.5f);
    gilde.y = hoeheBei(gilde.x, gilde.z);
    haus(bauer, gilde, 3.1f, 2.6f, 5.4f, 0.35f, FARBE_LEHM_HELL, FARBE_DACH_TEAL);
    bauer.roehre(gilde + Vec3(0.0f, 5.4f, 0.0f), 0.16f, 0.12f, 4.2f, FARBE_HOLZ_DUNKEL, 6);
    for (int i = 0; i < 3; ++i) {
        float y = 6.4f + static_cast<float>(i) * 1.0f;
        Vec3 fahne = gilde + Vec3(0.0f, y, 0.0f);
        bauer.viereck(fahne, fahne + Vec3(1.5f, -0.18f, 0.0f), fahne + Vec3(1.5f, -0.85f, 0.0f),
                      fahne + Vec3(0.0f, -0.7f, 0.0f), FARBE_STAND[i % 5]);
    }

    for (int i = 0; i < 5; ++i) {
        Vec3 ort(mitte.x - 12.0f + static_cast<float>(i) * 5.5f, 0.0f, mitte.z + 12.0f);
        ort.y = hoeheBei(ort.x, ort.z);
        haus(bauer, ort, 2.1f, 1.9f, 3.0f, wuerfel.bereich(-0.4f, 0.4f), FARBE_LEHM,
             FARBE_DACH[i % 3]);
    }

    for (int i = 0; i < 22; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(17.0f, 24.5f);
        Vec3 fuss(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        fuss.y = hoeheBei(fuss.x, fuss.z);
        if (fuss.y < 0.6f) continue;
        baum(bauer, laub, fuss, wuerfel.bereich(0.8f, 1.35f),
             mische(FARBE_LAUB, FARBE_LAUB_WARM, wuerfel.einheit()));
    }
    for (int i = 0; i < 40; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(7.0f, 25.0f);
        Vec3 fuss(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        fuss.y = hoeheBei(fuss.x, fuss.z);
        if (fuss.y < 0.55f) continue;
        laub.kugel(fuss + Vec3(0.0f, 0.16f, 0.0f), Vec3(0.34f, 0.22f, 0.34f), FARBE_BUSCH, 4, 6);
        laub.kugel(fuss + Vec3(0.1f, 0.3f, 0.05f), Vec3(0.1f, 0.1f, 0.1f),
                   FARBE_BLUETE[i % 4], 4, 6);
    }
}

void Welt::farmBebauen(Bauer& bauer, Bauer& laub) {
    const Insel& farm = insel(Bezirk::Farm);
    Zufall wuerfel(saatwert * 71u + 13u);
    Vec3 mitte(farm.mitte.x, hoeheBei(farm.mitte.x, farm.mitte.y), farm.mitte.y);

    for (int feld = 0; feld < 6; ++feld) {
        float winkel = static_cast<float>(feld) / 6.0f * TAU + 0.4f;
        Vec3 ecke(mitte.x + std::cos(winkel) * 8.0f, 0.0f, mitte.z + std::sin(winkel) * 8.0f);
        Vec3 farbe = FARBE_ACKER[feld % 4];
        for (int i = 0; i < 5; ++i) {
            for (int j = 0; j < 5; ++j) {
                Vec3 ort = ecke + Vec3(static_cast<float>(i) * 0.95f - 2.0f, 0.0f,
                                       static_cast<float>(j) * 0.95f - 2.0f);
                ort.y = hoeheBei(ort.x, ort.z);
                if (ort.y < 0.5f) continue;
                bauer.quader(ort + Vec3(0.0f, 0.07f, 0.0f), Vec3(0.42f, 0.07f, 0.42f), farbe);
                if ((i + j) % 2 == 0) {
                    laub.kugel(ort + Vec3(0.0f, 0.3f, 0.0f), Vec3(0.22f, 0.28f, 0.22f),
                               FARBE_KORN, 4, 6);
                }
            }
        }
    }

    Vec3 scheune(mitte.x - 6.5f, 0.0f, mitte.z - 5.5f);
    scheune.y = hoeheBei(scheune.x, scheune.z);
    haus(bauer, scheune, 3.4f, 2.7f, 3.4f, 0.25f, FARBE_SCHEUNE, FARBE_DACH_ZIEGEL);

    Vec3 gewaechs(mitte.x + 6.0f, 0.0f, mitte.z + 4.5f);
    gewaechs.y = hoeheBei(gewaechs.x, gewaechs.z);
    bauer.quader(gewaechs + Vec3(0.0f, 0.12f, 0.0f), Vec3(2.6f, 0.12f, 1.9f), FARBE_HOLZ_DUNKEL);
    for (int i = 0; i <= 6; ++i) {
        float t = static_cast<float>(i) / 6.0f;
        float x = mische(-2.5f, 2.5f, t);
        bauer.quader(gewaechs + Vec3(x, 1.1f, 0.0f), Vec3(0.06f, 1.0f, 1.85f), FARBE_HOLZ_HELL);
    }
    bauer.viereck(gewaechs + Vec3(-2.6f, 2.1f, -1.9f), gewaechs + Vec3(2.6f, 2.1f, -1.9f),
                  gewaechs + Vec3(2.6f, 2.1f, 1.9f), gewaechs + Vec3(-2.6f, 2.1f, 1.9f),
                  FARBE_GLAS, 0.9f);
    for (int i = 0; i < 8; ++i) {
        Vec3 ort = gewaechs + Vec3(wuerfel.bereich(-2.2f, 2.2f), 0.35f, wuerfel.bereich(-1.5f, 1.5f));
        laub.kugel(ort, Vec3(0.28f, 0.3f, 0.28f), FARBE_LAUB, 4, 6);
    }

    zaun(bauer, Vec3(mitte.x - 2.0f, 0.0f, mitte.z + 7.5f), Vec3(mitte.x + 9.0f, 0.0f, mitte.z + 7.5f),
         FARBE_HOLZ);
    zaun(bauer, Vec3(mitte.x + 9.0f, 0.0f, mitte.z + 7.5f), Vec3(mitte.x + 9.0f, 0.0f, mitte.z - 1.5f),
         FARBE_HOLZ);
    zaun(bauer, Vec3(mitte.x - 2.0f, 0.0f, mitte.z + 7.5f), Vec3(mitte.x - 2.0f, 0.0f, mitte.z - 1.5f),
         FARBE_HOLZ);

    for (int i = 0; i < 12; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(11.0f, 15.5f);
        Vec3 fuss(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        fuss.y = hoeheBei(fuss.x, fuss.z);
        if (fuss.y < 0.55f) continue;
        baum(bauer, laub, fuss, wuerfel.bereich(0.7f, 1.1f), FARBE_LAUB_WARM);
    }
}

void Welt::bergBebauen(Bauer& bauer, Bauer& laub) {
    const Insel& berg = insel(Bezirk::Berg);
    Zufall wuerfel(saatwert * 97u + 3u);
    Vec3 mitte(berg.mitte.x, hoeheBei(berg.mitte.x, berg.mitte.y), berg.mitte.y);

    Vec3 hoehleFuss(mitte.x - 3.4f, 0.0f, mitte.z + 4.6f);
    hoehleFuss.y = hoeheBei(hoehleFuss.x, hoehleFuss.z);
    bauer.roehre(hoehleFuss, 2.4f, 1.9f, 3.1f, FARBE_FELS_TIEF, 12);
    bauer.quader(hoehleFuss + Vec3(0.0f, 1.05f, 1.75f), Vec3(1.0f, 1.05f, 0.35f), FARBE_HOEHLE);
    bauer.roehre(hoehleFuss + Vec3(0.0f, 2.1f, 1.6f), 1.05f, 0.0f, 1.0f, FARBE_HOEHLE, 10);

    for (int i = 0; i < 6; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(6.0f, 12.0f);
        Vec3 ort(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        ort.y = hoeheBei(ort.x, ort.z);
        float hoehe = wuerfel.bereich(1.4f, 3.4f);
        bauer.quader(ort + Vec3(0.0f, hoehe * 0.5f, 0.0f), Vec3(0.42f, hoehe * 0.5f, 0.42f),
                     FARBE_RUINE, wuerfel.bereich(-0.4f, 0.4f));
        if (wuerfel.chance(0.5f)) {
            bauer.quader(ort + Vec3(0.0f, hoehe + 0.12f, 0.0f), Vec3(0.6f, 0.12f, 0.6f), FARBE_RUINE);
        }
    }
    Vec3 bogenA(mitte.x + 4.5f, hoeheBei(mitte.x + 4.5f, mitte.z - 5.5f), mitte.z - 5.5f);
    Vec3 bogenB(mitte.x + 7.5f, hoeheBei(mitte.x + 7.5f, mitte.z - 5.5f), mitte.z - 5.5f);
    bauer.quader(bogenA + Vec3(0.0f, 1.7f, 0.0f), Vec3(0.35f, 1.7f, 0.35f), FARBE_RUINE);
    bauer.quader(bogenB + Vec3(0.0f, 1.7f, 0.0f), Vec3(0.35f, 1.7f, 0.35f), FARBE_RUINE);
    bauer.quader((bogenA + bogenB) * 0.5f + Vec3(0.0f, 3.6f, 0.0f), Vec3(2.1f, 0.28f, 0.4f),
                 FARBE_RUINE);

    for (int i = 0; i < 16; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(4.0f, 14.0f);
        Vec3 ort(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        ort.y = hoeheBei(ort.x, ort.z);
        if (ort.y < 0.6f) continue;
        float mass = wuerfel.bereich(0.35f, 0.95f);
        bauer.kugel(ort + Vec3(0.0f, mass * 0.45f, 0.0f), Vec3(mass, mass * 0.75f, mass * 0.9f),
                    mische(FARBE_FELS, FARBE_FELS_HELL, wuerfel.einheit()), 5, 7);
    }
    for (int i = 0; i < 10; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(10.0f, 15.0f);
        Vec3 fuss(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        fuss.y = hoeheBei(fuss.x, fuss.z);
        if (fuss.y < 0.55f || fuss.y > 5.0f) continue;
        baum(bauer, laub, fuss, wuerfel.bereich(0.6f, 0.95f), FARBE_LAUB_KUEHL);
    }
    for (int i = 0; i < 8; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(2.0f, 9.0f);
        Vec3 ort(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        ort.y = hoeheBei(ort.x, ort.z);
        laub.roehre(ort, 0.22f, 0.0f, wuerfel.bereich(0.5f, 1.1f), FARBE_KRISTALL, 6);
    }
}

void Welt::werftBebauen(Bauer& bauer, Bauer& laub) {
    const Insel& werft = insel(Bezirk::Werft);
    Zufall wuerfel(saatwert * 131u + 29u);
    Vec3 mitte(werft.mitte.x, hoeheBei(werft.mitte.x, werft.mitte.y), werft.mitte.y);

    Vec3 tisch(mitte.x - 5.0f, 0.0f, mitte.z + 3.0f);
    tisch.y = hoeheBei(tisch.x, tisch.z);
    bauer.quader(tisch + Vec3(0.0f, 0.85f, 0.0f), Vec3(1.3f, 0.08f, 0.9f), FARBE_HOLZ);
    for (float sx : {-1.0f, 1.0f}) {
        for (float sz : {-1.0f, 1.0f}) {
            bauer.quader(tisch + Vec3(sx * 1.1f, 0.42f, sz * 0.7f), Vec3(0.08f, 0.42f, 0.08f),
                         FARBE_HOLZ_DUNKEL);
        }
    }
    bauer.quader(tisch + Vec3(0.0f, 0.95f, 0.0f), Vec3(1.05f, 0.02f, 0.7f), FARBE_PLAN);

    for (int i = 0; i < 7; ++i) {
        Vec3 ort(mitte.x - 8.0f + static_cast<float>(i % 4) * 1.2f, 0.0f,
                 mitte.z - 4.0f + static_cast<float>(i / 4) * 1.4f);
        ort.y = hoeheBei(ort.x, ort.z);
        for (int lage = 0; lage < 3; ++lage) {
            bauer.quader(ort + Vec3(0.0f, 0.12f + static_cast<float>(lage) * 0.18f, 0.0f),
                         Vec3(0.9f, 0.09f, 0.28f), lage % 2 == 0 ? FARBE_HOLZ : FARBE_HOLZ_HELL,
                         wuerfel.bereich(-0.2f, 0.2f));
        }
    }

    Vec3 kai(mitte.x + 1.0f, 0.0f, mitte.z + 10.5f);
    kai.y = 0.35f;
    for (int i = 0; i < 5; ++i) {
        Vec3 ort = kai + Vec3(static_cast<float>(i) * 1.4f - 2.8f, 0.0f, 0.0f);
        bauer.quader(ort + Vec3(0.0f, 0.15f, 0.0f), Vec3(0.7f, 0.12f, 2.2f), FARBE_HOLZ);
        bauer.quader(ort + Vec3(0.0f, -0.4f, 1.9f), Vec3(0.12f, 0.6f, 0.12f), FARBE_HOLZ_DUNKEL);
    }

    for (int i = 0; i < 9; ++i) {
        float winkel = wuerfel.bereich(0.0f, TAU);
        float weite = wuerfel.bereich(10.0f, 14.0f);
        Vec3 fuss(mitte.x + std::cos(winkel) * weite, 0.0f, mitte.z + std::sin(winkel) * weite);
        fuss.y = hoeheBei(fuss.x, fuss.z);
        if (fuss.y < 0.55f) continue;
        baum(bauer, laub, fuss, wuerfel.bereich(0.7f, 1.15f), FARBE_LAUB);
    }
}

void Welt::turmBauen() {
    Bauer bauer;
    const float fussHoehe = leuchtturm.y;
    Vec3 fuss(leuchtturm.x, fussHoehe, leuchtturm.z);
    const int stufen = klemme(static_cast<float>(turmStufe), 0.0f, 6.0f) > 0.0f ? turmStufe : 0;

    bauer.roehre(fuss, 3.2f, 3.0f, 0.4f, FARBE_PFLASTER, 18);

    const float hoehePro = 1.9f;
    float gebaut = static_cast<float>(stufen) * hoehePro;
    if (gebaut > 0.0f) {
        int scheiben = stufen * 3;
        for (int i = 0; i < scheiben; ++i) {
            float t0 = static_cast<float>(i) / static_cast<float>(scheiben);
            float t1 = static_cast<float>(i + 1) / static_cast<float>(scheiben);
            float y0 = 0.4f + t0 * gebaut;
            float y1 = 0.4f + t1 * gebaut;
            float r0 = mische(2.6f, 1.5f, t0 * gebaut / (hoehePro * 6.0f));
            float r1 = mische(2.6f, 1.5f, t1 * gebaut / (hoehePro * 6.0f));
            Vec3 farbe = (i % 2 == 0) ? FARBE_TURM_HELL : FARBE_TURM_ROT;
            bauer.roehre(fuss + Vec3(0.0f, y0, 0.0f), r0, r1, y1 - y0, farbe, 18);
        }
    }

    if (stufen >= 6) {
        Vec3 kopf = fuss + Vec3(0.0f, 0.4f + gebaut, 0.0f);
        bauer.roehre(kopf, 1.9f, 1.9f, 0.25f, FARBE_HOLZ_DUNKEL, 16);
        bauer.roehre(kopf + Vec3(0.0f, 0.25f, 0.0f), 1.45f, 1.45f, 1.5f, FARBE_GLAS, 14);
        bauer.kugel(kopf + Vec3(0.0f, 1.0f, 0.0f), Vec3(0.85f, 0.85f, 0.85f), FARBE_LICHT, 7, 10);
        bauer.roehre(kopf + Vec3(0.0f, 1.75f, 0.0f), 1.7f, 0.0f, 1.4f, FARBE_DACH_ZIEGEL, 16);
    } else {
        float geruestHoehe = gebaut + 2.6f;
        for (int i = 0; i < 6; ++i) {
            float winkel = static_cast<float>(i) / 6.0f * TAU;
            Vec3 pfosten = fuss + Vec3(std::cos(winkel) * 3.1f, 0.0f, std::sin(winkel) * 3.1f);
            bauer.quader(pfosten + Vec3(0.0f, geruestHoehe * 0.5f, 0.0f),
                         Vec3(0.12f, geruestHoehe * 0.5f, 0.12f), FARBE_HOLZ);
        }
        for (int lage = 1; lage <= 3; ++lage) {
            float y = geruestHoehe * static_cast<float>(lage) / 3.5f;
            for (int i = 0; i < 6; ++i) {
                float w0 = static_cast<float>(i) / 6.0f * TAU;
                float w1 = static_cast<float>(i + 1) / 6.0f * TAU;
                Vec3 a = fuss + Vec3(std::cos(w0) * 3.1f, y, std::sin(w0) * 3.1f);
                Vec3 b = fuss + Vec3(std::cos(w1) * 3.1f, y, std::sin(w1) * 3.1f);
                bauer.band(a, b, 0.5f, 0.1f, FARBE_HOLZ_HELL);
            }
        }
    }
    turm.hochladen(bauer);
}

void Welt::leuchtturmStufe(int stufe) {
    int neu = static_cast<int>(klemme(static_cast<float>(stufe), 0.0f, 6.0f));
    if (neu == turmStufe) return;
    turmStufe = neu;
    turmBauen();
}

void Welt::ferneInseln(Bauer& bauer) {
    Zufall wuerfel(saatwert * 977u + 41u);
    for (int i = 0; i < 9; ++i) {
        float winkel = static_cast<float>(i) / 9.0f * TAU + wuerfel.bereich(-0.25f, 0.25f);
        float weite = wuerfel.bereich(128.0f, 172.0f);
        Vec3 mitte(std::cos(winkel) * weite, wuerfel.bereich(-0.6f, 1.2f), std::sin(winkel) * weite);
        float radius = wuerfel.bereich(6.0f, 15.0f);
        float hoehe = wuerfel.bereich(3.0f, 9.0f);
        bauer.roehre(mitte, radius, radius * 0.55f, hoehe * 0.35f, FARBE_FERN_TIEF, 12);
        bauer.roehre(mitte + Vec3(0.0f, hoehe * 0.35f, 0.0f), radius * 0.55f, radius * 0.18f,
                     hoehe * 0.65f, FARBE_FERN, 12);
        bauer.roehre(mitte + Vec3(0.0f, -hoehe * 0.7f, 0.0f), 0.0f, radius * 0.9f, hoehe * 0.7f,
                     FARBE_FERN_TIEF, 12);
        if (wuerfel.chance(0.6f)) {
            bauer.kugel(mitte + Vec3(radius * 0.2f, hoehe * 1.05f, 0.0f),
                        Vec3(radius * 0.22f, radius * 0.18f, radius * 0.22f), FARBE_FERN, 5, 8);
        }
    }
}

void Welt::regenbogenBauen(Bauer& bauer) {
    const Insel& berg = insel(Bezirk::Berg);
    Vec3 mitte(0.0f, 0.0f, 0.0f);
    Vec3 quer(1.0f, 0.0f, 0.0f);
    Vec3 hoch(0.0f, 1.0f, 0.0f);
    const Vec3 farben[7] = {ausByte(240, 88, 92),   ausByte(246, 154, 68), ausByte(248, 218, 96),
                            ausByte(118, 208, 122), ausByte(84, 178, 238), ausByte(96, 112, 226),
                            ausByte(178, 108, 226)};
    const float grundradius = berg.radius * 1.35f;
    const float bandbreite = 1.5f;
    const int schritte = 44;
    for (int band = 0; band < 7; ++band) {
        float innen = grundradius + static_cast<float>(band) * bandbreite;
        float aussen = innen + bandbreite;
        Vec3 farbe = farben[band];
        for (int i = 0; i < schritte; ++i) {
            float t0 = static_cast<float>(i) / static_cast<float>(schritte) * PI;
            float t1 = static_cast<float>(i + 1) / static_cast<float>(schritte) * PI;
            Vec3 richtung0 = quer * std::cos(t0) + hoch * std::sin(t0);
            Vec3 richtung1 = quer * std::cos(t1) + hoch * std::sin(t1);
            Vec3 a = mitte + richtung0 * innen;
            Vec3 b = mitte + richtung1 * innen;
            Vec3 c = mitte + richtung1 * aussen;
            Vec3 d = mitte + richtung0 * aussen;
            bauer.viereck(a, b, c, d, farbe);
        }
    }
}

void Welt::booteBauen(Bauer& bauer) {
    Zufall wuerfel(saatwert * 313u + 7u);
    for (int i = 0; i < 7; ++i) {
        float winkel = static_cast<float>(i) / 7.0f * TAU + 0.35f;
        float weite = wuerfel.bereich(46.0f, 88.0f);
        Vec3 ort(std::cos(winkel) * weite, 0.25f, std::sin(winkel) * weite);
        float drehung = wuerfel.bereich(0.0f, TAU);
        float s = std::sin(drehung);
        float c = std::cos(drehung);
        auto dreh = [&](Vec3 p) { return Vec3(p.x * c + p.z * s, p.y, -p.x * s + p.z * c) + ort; };
        bauer.quader(dreh(Vec3(0.0f, 0.2f, 0.0f)), Vec3(1.5f, 0.22f, 0.62f), FARBE_HOLZ, drehung);
        bauer.dreieck(dreh(Vec3(1.5f, 0.42f, -0.62f)), dreh(Vec3(2.5f, 0.32f, 0.0f)),
                      dreh(Vec3(1.5f, 0.42f, 0.62f)), FARBE_HOLZ_HELL);
        bauer.quader(dreh(Vec3(-0.2f, 1.15f, 0.0f)), Vec3(0.06f, 0.95f, 0.06f), FARBE_HOLZ_DUNKEL);
        bauer.dreieck(dreh(Vec3(-0.18f, 2.1f, 0.0f)), dreh(Vec3(-0.18f, 0.45f, 0.0f)),
                      dreh(Vec3(0.95f, 0.6f, 0.0f)), FARBE_SEGEL);
        bauer.dreieck(dreh(Vec3(-0.18f, 2.1f, 0.0f)), dreh(Vec3(0.95f, 0.6f, 0.0f)),
                      dreh(Vec3(-0.18f, 0.45f, 0.0f)), FARBE_SEGEL * 0.9f);
    }
}

}
