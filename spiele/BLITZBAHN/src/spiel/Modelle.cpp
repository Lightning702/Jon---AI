#include "Modelle.hpp"

#include <algorithm>
#include <cmath>

#include "fw/Zufall.hpp"

namespace blitzbahn {

using namespace fw;

namespace {

const Vec3 ASPHALT(0.34f, 0.36f, 0.41f);
const Vec3 ASPHALT_HELL(0.4f, 0.42f, 0.47f);
const Vec3 BORD_ROT(0.86f, 0.16f, 0.13f);
const Vec3 BORD_WEISS(0.94f, 0.94f, 0.96f);
const Vec3 WAND(0.15f, 0.16f, 0.21f);
const Vec3 WAND_KANTE(0.95f, 0.74f, 0.2f);
const Vec3 UNTERSEITE(0.2f, 0.21f, 0.25f);
const Vec3 BETON(0.56f, 0.57f, 0.61f);
const Vec3 GELB(0.98f, 0.8f, 0.12f);
const Vec3 SCHWARZ(0.05f, 0.05f, 0.06f);
const Vec3 TURBO(1.0f, 0.46f, 0.08f);

void flaeche(Bauer& b, Vec3 p0, Vec3 p1, Vec3 p2, Vec3 p3, Vec3 farbe, Vec3 aussen, float rauheit = 0.1f) {
    Vec3 n = kreuz(p1 - p0, p2 - p0);
    if (punkt(n, aussen) < 0.0f) {
        b.viereck(p3, p2, p1, p0, farbe, rauheit);
    } else {
        b.viereck(p0, p1, p2, p3, farbe, rauheit);
    }
}

void dreieckAussen(Bauer& b, Vec3 p0, Vec3 p1, Vec3 p2, Vec3 farbe, Vec3 aussen) {
    Vec3 n = kreuz(p1 - p0, p2 - p0);
    if (punkt(n, aussen) < 0.0f) b.dreieck(p2, p1, p0, farbe);
    else b.dreieck(p0, p1, p2, farbe);
}

float profil(int teil, float lz) {
    bool drin = false;
    Vec3 n;
    return teilHoehe(teil, 0.0f, lz, drin, n);
}

void quaderLokal(Bauer& b, const Stueck& s, Vec3 mitte, Vec3 halb, Vec3 farbe) {
    Vec3 ecken[8];
    int i = 0;
    for (int dy = 0; dy < 2; ++dy)
        for (int dz = 0; dz < 2; ++dz)
            for (int dx = 0; dx < 2; ++dx)
                ecken[i++] = lokalZuWelt(s, mitte + Vec3(dx ? halb.x : -halb.x, dy ? halb.y : -halb.y, dz ? halb.z : -halb.z));
    Vec3 c = lokalZuWelt(s, mitte);
    auto seite = [&](int a, int bb, int cc, int d) {
        Vec3 m = (ecken[a] + ecken[bb] + ecken[cc] + ecken[d]) * 0.25f;
        flaeche(b, ecken[a], ecken[bb], ecken[cc], ecken[d], farbe, m - c);
    };
    seite(0, 1, 3, 2);
    seite(4, 5, 7, 6);
    seite(0, 1, 5, 4);
    seite(2, 3, 7, 6);
    seite(0, 2, 6, 4);
    seite(1, 3, 7, 5);
}

void pfeiler(Bauer& b, const Stueck& s, Vec3 lokal, float boden) {
    Vec3 oben = lokalZuWelt(s, lokal);
    float unten = boden;
    if (oben.y - unten < 0.5f) return;
    Vec3 mitte((oben.x), (oben.y + unten) * 0.5f, oben.z);
    b.quader(mitte, Vec3(0.45f, (oben.y - unten) * 0.5f, 0.45f), BETON, 0.0f, 0.05f);
}

void geradeBauen(Bauer& b, Bauer& l, const Stueck& s, float boden) {
    const int teil = s.teil;
    const int schritte = 8;
    const float dicke = 0.9f;
    const float bord = 0.8f;
    for (int k = 0; k < schritte; ++k) {
        float z0 = -ZELLE * 0.5f + ZELLE * k / schritte;
        float z1 = -ZELLE * 0.5f + ZELLE * (k + 1) / schritte;
        float h0 = profil(teil, z0);
        float h1 = profil(teil, z1);
        if (teil == SCHANZE && z0 >= 0.0f) {
            for (int f = 0; f < 4; ++f) {
                float za = z0 + (z1 - z0) * f / 4.0f;
                float zb = z0 + (z1 - z0) * (f + 1) / 4.0f;
                float ha = profil(teil, za);
                float hb = profil(teil, zb);
                Vec3 p0 = lokalZuWelt(s, Vec3(-HALBE_BREITE + bord, ha, za));
                Vec3 p1 = lokalZuWelt(s, Vec3(HALBE_BREITE - bord, ha, za));
                Vec3 p2 = lokalZuWelt(s, Vec3(HALBE_BREITE - bord, hb, zb));
                Vec3 p3 = lokalZuWelt(s, Vec3(-HALBE_BREITE + bord, hb, zb));
                flaeche(b, p0, p1, p2, p3, k == schritte - 1 && f == 3 ? GELB : ASPHALT_HELL, Vec3(0, 1, 0));
            }
        } else if (teil == WELLEN) {
            for (int f = 0; f < 3; ++f) {
                float za = z0 + (z1 - z0) * f / 3.0f;
                float zb = z0 + (z1 - z0) * (f + 1) / 3.0f;
                float ha = profil(teil, za);
                float hb = profil(teil, zb);
                Vec3 p0 = lokalZuWelt(s, Vec3(-HALBE_BREITE + bord, ha, za));
                Vec3 p1 = lokalZuWelt(s, Vec3(HALBE_BREITE - bord, ha, za));
                Vec3 p2 = lokalZuWelt(s, Vec3(HALBE_BREITE - bord, hb, zb));
                Vec3 p3 = lokalZuWelt(s, Vec3(-HALBE_BREITE + bord, hb, zb));
                flaeche(b, p0, p1, p2, p3, ASPHALT, Vec3(0, 1, 0));
            }
        } else {
            Vec3 p0 = lokalZuWelt(s, Vec3(-HALBE_BREITE + bord, h0, z0));
            Vec3 p1 = lokalZuWelt(s, Vec3(HALBE_BREITE - bord, h0, z0));
            Vec3 p2 = lokalZuWelt(s, Vec3(HALBE_BREITE - bord, h1, z1));
            Vec3 p3 = lokalZuWelt(s, Vec3(-HALBE_BREITE + bord, h1, z1));
            flaeche(b, p0, p1, p2, p3, ASPHALT, Vec3(0, 1, 0));
        }
        Vec3 bordFarbe = (k % 2 == 0) ? BORD_ROT : BORD_WEISS;
        for (float seite : {-1.0f, 1.0f}) {
            float xa = seite * HALBE_BREITE;
            float xb = seite * (HALBE_BREITE - bord);
            int feiner = (teil == WELLEN || (teil == SCHANZE && z0 >= 0.0f)) ? 4 : 1;
            for (int f = 0; f < feiner; ++f) {
                float za = z0 + (z1 - z0) * f / feiner;
                float zb = z0 + (z1 - z0) * (f + 1) / feiner;
                float ha = profil(teil, za) + 0.03f;
                float hb = profil(teil, zb) + 0.03f;
                flaeche(b, lokalZuWelt(s, Vec3(xa, ha, za)), lokalZuWelt(s, Vec3(xb, ha, za)),
                        lokalZuWelt(s, Vec3(xb, hb, zb)), lokalZuWelt(s, Vec3(xa, hb, zb)), bordFarbe, Vec3(0, 1, 0));
                float wa = seite * (HALBE_BREITE + 0.6f);
                Vec3 i0 = lokalZuWelt(s, Vec3(xa, ha - 0.03f, za));
                Vec3 i1 = lokalZuWelt(s, Vec3(xa, hb - 0.03f, zb));
                Vec3 o0 = lokalZuWelt(s, Vec3(xa, ha + WAND_HOEHE, za));
                Vec3 o1 = lokalZuWelt(s, Vec3(xa, hb + WAND_HOEHE, zb));
                Vec3 a0 = lokalZuWelt(s, Vec3(wa, ha + WAND_HOEHE, za));
                Vec3 a1 = lokalZuWelt(s, Vec3(wa, hb + WAND_HOEHE, zb));
                Vec3 u0 = lokalZuWelt(s, Vec3(wa, ha - dicke, za));
                Vec3 u1 = lokalZuWelt(s, Vec3(wa, hb - dicke, zb));
                Vec3 innen = richtungWelt(s.dreh, Vec3(-seite, 0.0f, 0.0f));
                flaeche(b, i0, i1, o1, o0, WAND, innen);
                flaeche(b, o0, o1, a1, a0, WAND_KANTE, Vec3(0, 1, 0), 0.4f);
                flaeche(b, a0, a1, u1, u0, WAND, -innen);
            }
        }
        Vec3 u0 = lokalZuWelt(s, Vec3(-HALBE_BREITE - 0.6f, h0 - dicke, z0));
        Vec3 u1 = lokalZuWelt(s, Vec3(HALBE_BREITE + 0.6f, h0 - dicke, z0));
        Vec3 u2 = lokalZuWelt(s, Vec3(HALBE_BREITE + 0.6f, h1 - dicke, z1));
        Vec3 u3 = lokalZuWelt(s, Vec3(-HALBE_BREITE - 0.6f, h1 - dicke, z1));
        flaeche(b, u0, u1, u2, u3, UNTERSEITE, Vec3(0, -1, 0));
        if (teil == GERADE && k % 2 == 0) {
            float za = z0 + 0.4f;
            float zb = z1 - 0.4f;
            flaeche(b, lokalZuWelt(s, Vec3(-0.14f, h0 + 0.02f, za)), lokalZuWelt(s, Vec3(0.14f, h0 + 0.02f, za)),
                    lokalZuWelt(s, Vec3(0.14f, h1 + 0.02f, zb)), lokalZuWelt(s, Vec3(-0.14f, h1 + 0.02f, zb)),
                    Vec3(0.86f, 0.86f, 0.82f), Vec3(0, 1, 0));
        }
    }
    for (float ende : {-ZELLE * 0.5f, ZELLE * 0.5f}) {
        float h = profil(teil, ende);
        Vec3 a = lokalZuWelt(s, Vec3(-HALBE_BREITE - 0.6f, h - dicke, ende));
        Vec3 bb = lokalZuWelt(s, Vec3(HALBE_BREITE + 0.6f, h - dicke, ende));
        Vec3 c = lokalZuWelt(s, Vec3(HALBE_BREITE + 0.6f, h, ende));
        Vec3 d = lokalZuWelt(s, Vec3(-HALBE_BREITE - 0.6f, h, ende));
        flaeche(b, a, bb, c, d, UNTERSEITE, richtungWelt(s.dreh, Vec3(0, 0, ende)));
    }
    if (teil == START || teil == ZIEL) {
        float z = teil == START ? 2.0f : 0.0f;
        for (int i = 0; i < 12; ++i) {
            for (int j = 0; j < 2; ++j) {
                float xa = -HALBE_BREITE + 0.8f + (2.0f * (HALBE_BREITE - 0.8f)) * i / 12.0f;
                float xb = -HALBE_BREITE + 0.8f + (2.0f * (HALBE_BREITE - 0.8f)) * (i + 1) / 12.0f;
                float za = z - 1.0f + j;
                float zb = za + 1.0f;
                Vec3 farbe = ((i + j) % 2 == 0) ? SCHWARZ : BORD_WEISS;
                flaeche(b, lokalZuWelt(s, Vec3(xa, 0.025f, za)), lokalZuWelt(s, Vec3(xb, 0.025f, za)),
                        lokalZuWelt(s, Vec3(xb, 0.025f, zb)), lokalZuWelt(s, Vec3(xa, 0.025f, zb)), farbe, Vec3(0, 1, 0));
            }
        }
        if (teil == START) {
            for (float x : {-2.6f, 2.6f}) {
                for (float zz : {-6.0f, -1.5f}) {
                    float zv = x < 0.0f ? zz : zz - 2.2f;
                    flaeche(b, lokalZuWelt(s, Vec3(x - 1.2f, 0.025f, zv)), lokalZuWelt(s, Vec3(x + 1.2f, 0.025f, zv)),
                            lokalZuWelt(s, Vec3(x + 1.2f, 0.025f, zv + 0.25f)),
                            lokalZuWelt(s, Vec3(x - 1.2f, 0.025f, zv + 0.25f)), BORD_WEISS, Vec3(0, 1, 0));
                }
            }
        }
    }
    if (teil == KONTROLLE) {
        flaeche(b, lokalZuWelt(s, Vec3(-HALBE_BREITE + 0.8f, 0.025f, -0.4f)),
                lokalZuWelt(s, Vec3(HALBE_BREITE - 0.8f, 0.025f, -0.4f)),
                lokalZuWelt(s, Vec3(HALBE_BREITE - 0.8f, 0.025f, 0.4f)),
                lokalZuWelt(s, Vec3(-HALBE_BREITE + 0.8f, 0.025f, 0.4f)), GELB, Vec3(0, 1, 0));
    }
    if (teil == SCHUB) {
        for (int i = 0; i < 4; ++i) {
            float z = -7.0f + i * 4.6f;
            for (float seite : {-1.0f, 1.0f}) {
                Vec3 a = lokalZuWelt(s, Vec3(seite * 0.4f, 0.04f, z + 2.0f));
                Vec3 bb = lokalZuWelt(s, Vec3(seite * 4.6f, 0.04f, z - 0.6f));
                Vec3 c = lokalZuWelt(s, Vec3(seite * 4.6f, 0.04f, z + 0.6f));
                Vec3 d = lokalZuWelt(s, Vec3(seite * 0.4f, 0.04f, z + 3.2f));
                flaeche(l, a, bb, c, d, TURBO, Vec3(0, 1, 0));
            }
        }
    }
    if (teil == SCHANZE) {
        for (int i = 0; i < 8; ++i) {
            float xa = -HALBE_BREITE + 0.8f + (2.0f * (HALBE_BREITE - 0.8f)) * i / 8.0f;
            float xb = -HALBE_BREITE + 0.8f + (2.0f * (HALBE_BREITE - 0.8f)) * (i + 1) / 8.0f;
            Vec3 farbe = i % 2 == 0 ? GELB : SCHWARZ;
            float h = SCHANZE_HOEHE;
            flaeche(b, lokalZuWelt(s, Vec3(xa, h - 0.9f, ZELLE * 0.5f + 0.01f)), lokalZuWelt(s, Vec3(xb, h - 0.9f, ZELLE * 0.5f + 0.01f)),
                    lokalZuWelt(s, Vec3(xb, h + 0.01f, ZELLE * 0.5f + 0.01f)), lokalZuWelt(s, Vec3(xa, h + 0.01f, ZELLE * 0.5f + 0.01f)),
                    farbe, richtungWelt(s.dreh, Vec3(0, 0, 1)));
        }
    }
    if (s.y * STUFE > boden + 1.0f) {
        pfeiler(b, s, Vec3(-HALBE_BREITE + 2.0f, profil(teil, 0.0f) - dicke, 0.0f), boden);
        pfeiler(b, s, Vec3(HALBE_BREITE - 2.0f, profil(teil, 0.0f) - dicke, 0.0f), boden);
    }
}

void kurveBauen(Bauer& b, const Stueck& s, float boden) {
    const int schritte = 12;
    const float dicke = 0.9f;
    const float bord = 0.8f;
    auto punktBei = [&](float radius, float winkel, float hoehe) {
        return lokalZuWelt(s, Vec3(ZELLE * 0.5f - radius * std::cos(winkel), hoehe, -ZELLE * 0.5f + radius * std::sin(winkel)));
    };
    Vec3 mitte = lokalZuWelt(s, Vec3(ZELLE * 0.5f, 0.0f, -ZELLE * 0.5f));
    for (int k = 0; k < schritte; ++k) {
        float a0 = (PI * 0.5f) * k / schritte;
        float a1 = (PI * 0.5f) * (k + 1) / schritte;
        flaeche(b, punktBei(KURVE_INNEN + bord, a0, 0.0f), punktBei(KURVE_AUSSEN - bord, a0, 0.0f),
                punktBei(KURVE_AUSSEN - bord, a1, 0.0f), punktBei(KURVE_INNEN + bord, a1, 0.0f), ASPHALT, Vec3(0, 1, 0));
        Vec3 bordFarbe = (k % 2 == 0) ? BORD_ROT : BORD_WEISS;
        flaeche(b, punktBei(KURVE_INNEN, a0, 0.03f), punktBei(KURVE_INNEN + bord, a0, 0.03f),
                punktBei(KURVE_INNEN + bord, a1, 0.03f), punktBei(KURVE_INNEN, a1, 0.03f), bordFarbe, Vec3(0, 1, 0));
        flaeche(b, punktBei(KURVE_AUSSEN - bord, a0, 0.03f), punktBei(KURVE_AUSSEN, a0, 0.03f),
                punktBei(KURVE_AUSSEN, a1, 0.03f), punktBei(KURVE_AUSSEN - bord, a1, 0.03f), bordFarbe, Vec3(0, 1, 0));
        for (int seite = 0; seite < 2; ++seite) {
            float r = seite == 0 ? KURVE_INNEN : KURVE_AUSSEN;
            float ra = seite == 0 ? KURVE_INNEN - 0.6f : KURVE_AUSSEN + 0.6f;
            Vec3 i0 = punktBei(r, a0, 0.0f);
            Vec3 i1 = punktBei(r, a1, 0.0f);
            Vec3 o0 = punktBei(r, a0, WAND_HOEHE);
            Vec3 o1 = punktBei(r, a1, WAND_HOEHE);
            Vec3 x0 = punktBei(ra, a0, WAND_HOEHE);
            Vec3 x1 = punktBei(ra, a1, WAND_HOEHE);
            Vec3 u0 = punktBei(ra, a0, -dicke);
            Vec3 u1 = punktBei(ra, a1, -dicke);
            Vec3 radial = normiert(Vec3((i0.x + i1.x) * 0.5f - mitte.x, 0.0f, (i0.z + i1.z) * 0.5f - mitte.z));
            Vec3 innen = seite == 0 ? radial : -radial;
            flaeche(b, i0, i1, o1, o0, WAND, innen);
            flaeche(b, o0, o1, x1, x0, WAND_KANTE, Vec3(0, 1, 0), 0.4f);
            flaeche(b, x0, x1, u1, u0, WAND, -innen);
        }
        flaeche(b, punktBei(KURVE_INNEN - 0.6f, a0, -dicke), punktBei(KURVE_AUSSEN + 0.6f, a0, -dicke),
                punktBei(KURVE_AUSSEN + 0.6f, a1, -dicke), punktBei(KURVE_INNEN - 0.6f, a1, -dicke), UNTERSEITE, Vec3(0, -1, 0));
    }
    if (s.y * STUFE > boden + 1.0f) {
        float w = PI * 0.25f;
        pfeiler(b, s, Vec3(ZELLE * 0.5f - 10.0f * std::cos(w), -dicke, -ZELLE * 0.5f + 10.0f * std::sin(w)), boden);
    }
}

void platteBauen(Bauer& b, const Stueck& s, float boden) {
    const float h = ZELLE * 0.5f;
    const float dicke = 0.9f;
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) {
            float xa = -h + ZELLE * i / 4.0f;
            float xb = -h + ZELLE * (i + 1) / 4.0f;
            float za = -h + ZELLE * j / 4.0f;
            float zb = -h + ZELLE * (j + 1) / 4.0f;
            Vec3 farbe = ((i + j) % 2 == 0) ? ASPHALT : ASPHALT_HELL;
            flaeche(b, lokalZuWelt(s, Vec3(xa, 0, za)), lokalZuWelt(s, Vec3(xb, 0, za)), lokalZuWelt(s, Vec3(xb, 0, zb)),
                    lokalZuWelt(s, Vec3(xa, 0, zb)), farbe, Vec3(0, 1, 0));
        }
    }
    flaeche(b, lokalZuWelt(s, Vec3(-h, -dicke, -h)), lokalZuWelt(s, Vec3(h, -dicke, -h)), lokalZuWelt(s, Vec3(h, -dicke, h)),
            lokalZuWelt(s, Vec3(-h, -dicke, h)), UNTERSEITE, Vec3(0, -1, 0));
    for (int seite = 0; seite < 4; ++seite) {
        Vec3 n = richtungWelt(seite, Vec3(0, 0, 1));
        Vec3 q = richtungWelt(seite, Vec3(1, 0, 0));
        Vec3 m = lokalZuWelt(s, Vec3(0, 0, 0));
        Vec3 a = m + n * h - q * h;
        Vec3 bb = m + n * h + q * h;
        flaeche(b, a + Vec3(0, -dicke, 0), bb + Vec3(0, -dicke, 0), bb + Vec3(0, 0.05f, 0), a + Vec3(0, 0.05f, 0), WAND_KANTE, n);
    }
    if (s.y * STUFE > boden + 1.0f) {
        pfeiler(b, s, Vec3(-5.0f, -dicke, -5.0f), boden);
        pfeiler(b, s, Vec3(5.0f, -dicke, 5.0f), boden);
    }
}

}

void streckeBauen(const Strecke& strecke, Bauer& fest, Bauer& leucht) {
    fest.leeren();
    leucht.leeren();
    float boden = std::min(0.0f, strecke.tiefstes()) - 0.6f;
    for (const Stueck& s : strecke.stuecke) {
        if (s.teil == KURVE) kurveBauen(fest, s, boden);
        else if (s.teil == PLATTE) platteBauen(fest, s, boden);
        else geradeBauen(fest, leucht, s, boden);
    }
}

void torBauen(Bauer& tor, Bauer& tafel) {
    tor.leeren();
    tafel.leeren();
    const Vec3 weiss(0.92f, 0.92f, 0.94f);
    for (float x : {-8.4f, 8.4f}) {
        tor.quader(Vec3(x, 3.7f, 0.0f), Vec3(0.45f, 3.7f, 0.45f), weiss, 0.0f, 0.3f);
        tor.quader(Vec3(x, 0.2f, 0.0f), Vec3(0.75f, 0.2f, 0.75f), Vec3(0.3f, 0.3f, 0.34f));
    }
    tor.quader(Vec3(0.0f, 7.3f, 0.0f), Vec3(8.85f, 0.55f, 0.5f), weiss, 0.0f, 0.3f);
    for (int i = 0; i < 16; ++i) {
        for (int j = 0; j < 2; ++j) {
            float xa = -8.4f + 16.8f * i / 16.0f;
            float xb = -8.4f + 16.8f * (i + 1) / 16.0f;
            float ya = 6.85f + 0.45f * j;
            float yb = ya + 0.45f;
            Vec3 farbe = ((i + j) % 2 == 0) ? Vec3(0.05f, 0.05f, 0.06f) : Vec3(0.96f, 0.96f, 0.96f);
            for (float z : {-0.52f, 0.52f}) {
                flaeche(tafel, Vec3(xa, ya, z), Vec3(xb, ya, z), Vec3(xb, yb, z), Vec3(xa, yb, z), farbe, Vec3(0, 0, z));
            }
        }
    }
}

void autoBauen(const Lackierung& f, Bauer& b, Bauer& glut) {
    b.leeren();
    glut.leeren();
    const Vec3 dunkel(0.06f, 0.06f, 0.08f);
    auto hexa = [&](Vec3 hu0, Vec3 hu1, Vec3 ho0, Vec3 ho1, Vec3 vu0, Vec3 vu1, Vec3 vo0, Vec3 vo1, Vec3 farbe, Vec3 oben) {
        Vec3 m = (hu0 + hu1 + ho0 + ho1 + vu0 + vu1 + vo0 + vo1) * 0.125f;
        auto seite = [&](Vec3 a, Vec3 bb, Vec3 c, Vec3 d, Vec3 fa) {
            flaeche(b, a, bb, c, d, fa, (a + bb + c + d) * 0.25f - m, 0.55f);
        };
        seite(hu0, hu1, vu1, vu0, farbe * 0.6f);
        seite(ho0, ho1, vo1, vo0, oben);
        seite(hu0, hu1, ho1, ho0, farbe * 0.85f);
        seite(vu0, vu1, vo1, vo0, farbe);
        seite(hu0, vu0, vo0, ho0, farbe * 0.92f);
        seite(hu1, vu1, vo1, ho1, farbe * 0.92f);
    };
    hexa(Vec3(-0.62f, 0.18f, -1.9f), Vec3(0.62f, 0.18f, -1.9f), Vec3(-0.58f, 0.66f, -1.9f), Vec3(0.58f, 0.66f, -1.9f),
         Vec3(-0.42f, 0.18f, 1.6f), Vec3(0.42f, 0.18f, 1.6f), Vec3(-0.38f, 0.56f, 1.6f), Vec3(0.38f, 0.56f, 1.6f), f.primaer,
         f.primaer * 1.05f);
    hexa(Vec3(-0.42f, 0.18f, 1.6f), Vec3(0.42f, 0.18f, 1.6f), Vec3(-0.38f, 0.56f, 1.6f), Vec3(0.38f, 0.56f, 1.6f),
         Vec3(-0.1f, 0.2f, 2.65f), Vec3(0.1f, 0.2f, 2.65f), Vec3(-0.08f, 0.34f, 2.65f), Vec3(0.08f, 0.34f, 2.65f), f.primaer,
         f.primaer * 1.05f);
    hexa(Vec3(-0.12f, 0.57f, 0.9f), Vec3(0.12f, 0.57f, 0.9f), Vec3(-0.1f, 0.58f, 0.9f), Vec3(0.1f, 0.58f, 0.9f),
         Vec3(-0.06f, 0.36f, 2.6f), Vec3(0.06f, 0.36f, 2.6f), Vec3(-0.05f, 0.37f, 2.6f), Vec3(0.05f, 0.37f, 2.6f), f.sekundaer,
         f.sekundaer);
    for (float seite : {-1.0f, 1.0f}) {
        hexa(Vec3(seite * 0.55f, 0.2f, -1.15f), Vec3(seite * 1.0f, 0.2f, -1.15f), Vec3(seite * 0.55f, 0.62f, -1.15f),
             Vec3(seite * 0.95f, 0.58f, -1.15f), Vec3(seite * 0.55f, 0.2f, 0.55f), Vec3(seite * 0.95f, 0.2f, 0.55f),
             Vec3(seite * 0.55f, 0.6f, 0.55f), Vec3(seite * 0.9f, 0.52f, 0.55f), f.sekundaer, f.sekundaer * 1.08f);
        flaeche(b, Vec3(seite * 0.6f, 0.26f, 0.56f), Vec3(seite * 0.9f, 0.26f, 0.56f), Vec3(seite * 0.86f, 0.48f, 0.56f),
                Vec3(seite * 0.6f, 0.54f, 0.56f), dunkel, Vec3(0, 0, 1));
        b.quader(Vec3(seite * 0.66f, 0.43f, 1.45f), Vec3(0.28f, 0.03f, 0.05f), f.rahmen, 0.0f, 0.3f);
        b.quader(Vec3(seite * 0.66f, 0.43f, -1.45f), Vec3(0.28f, 0.03f, 0.05f), f.rahmen, 0.0f, 0.3f);
        b.quader(Vec3(seite * 1.08f, 0.33f, 2.45f), Vec3(0.03f, 0.13f, 0.28f), f.rahmen, 0.0f, 0.3f);
        b.quader(Vec3(seite * 0.97f, 1.0f, -2.05f), Vec3(0.03f, 0.22f, 0.34f), f.rahmen, 0.0f, 0.3f);
    }
    b.quader(Vec3(0.0f, 0.635f, 0.2f), Vec3(0.3f, 0.025f, 0.5f), dunkel);
    b.kugel(Vec3(0.0f, 0.86f, 0.0f), Vec3(0.21f, 0.2f, 0.23f), f.sekundaer * 1.1f + Vec3(0.08f), 8, 12, 0.7f);
    b.kugel(Vec3(0.0f, 0.88f, 0.1f), Vec3(0.16f, 0.08f, 0.16f), Vec3(0.08f, 0.1f, 0.14f), 6, 10, 0.9f);
    hexa(Vec3(-0.34f, 0.6f, -1.85f), Vec3(0.34f, 0.6f, -1.85f), Vec3(-0.18f, 0.72f, -1.85f), Vec3(0.18f, 0.72f, -1.85f),
         Vec3(-0.26f, 0.6f, -0.35f), Vec3(0.26f, 0.6f, -0.35f), Vec3(-0.16f, 1.02f, -0.35f), Vec3(0.16f, 1.02f, -0.35f), f.primaer,
         f.sekundaer);
    b.quader(Vec3(0.0f, 1.17f, -2.05f), Vec3(1.0f, 0.04f, 0.3f), f.sekundaer, 0.0f, 0.5f);
    b.quader(Vec3(0.0f, 0.9f, -1.95f), Vec3(0.05f, 0.26f, 0.06f), f.rahmen);
    b.quader(Vec3(0.0f, 0.22f, 2.45f), Vec3(1.08f, 0.03f, 0.24f), f.sekundaer, 0.0f, 0.5f);
    b.quader(Vec3(0.0f, 0.5f, -1.98f), Vec3(0.12f, 0.08f, 0.08f), dunkel);
    glut.quader(Vec3(0.0f, 0.5f, -2.07f), Vec3(0.08f, 0.05f, 0.02f), Vec3(1.0f, 0.55f, 0.15f));
}

void radBauen(Bauer& rad, Vec3 felge, float breite) {
    rad.leeren();
    const int teile = 16;
    const float r = 0.42f;
    const float innen = 0.25f;
    const Vec3 reifen(0.07f, 0.07f, 0.08f);
    const float h = breite * 0.5f;
    for (int i = 0; i < teile; ++i) {
        float a0 = TAU * i / teile;
        float a1 = TAU * (i + 1) / teile;
        Vec3 p0(0.0f, std::cos(a0) * r, std::sin(a0) * r);
        Vec3 p1(0.0f, std::cos(a1) * r, std::sin(a1) * r);
        Vec3 q0(0.0f, std::cos(a0) * innen, std::sin(a0) * innen);
        Vec3 q1(0.0f, std::cos(a1) * innen, std::sin(a1) * innen);
        Vec3 aussen = normiert(Vec3(0.0f, (p0.y + p1.y) * 0.5f, (p0.z + p1.z) * 0.5f));
        flaeche(rad, p0 + Vec3(-h, 0, 0), p1 + Vec3(-h, 0, 0), p1 + Vec3(h, 0, 0), p0 + Vec3(h, 0, 0), reifen, aussen, 0.05f);
        for (float seite : {-1.0f, 1.0f}) {
            Vec3 x(seite * h, 0.0f, 0.0f);
            flaeche(rad, p0 + x, p1 + x, q1 + x, q0 + x, reifen * 1.3f, Vec3(seite, 0, 0), 0.05f);
            Vec3 mitte = x * 0.92f;
            Vec3 farbe = (i % 4 < 2) ? felge : felge * 0.55f;
            dreieckAussen(rad, mitte, q0 + x * 0.92f, q1 + x * 0.92f, farbe, Vec3(seite, 0, 0));
        }
    }
}

void schattenBauen(Bauer& schatten) {
    schatten.leeren();
    const int teile = 20;
    for (int i = 0; i < teile; ++i) {
        float a0 = TAU * i / teile;
        float a1 = TAU * (i + 1) / teile;
        Vec3 p0(std::cos(a0) * 1.25f, 0.0f, std::sin(a0) * 2.6f);
        Vec3 p1(std::cos(a1) * 1.25f, 0.0f, std::sin(a1) * 2.6f);
        dreieckAussen(schatten, Vec3(0, 0, 0), p0, p1, Vec3(0.0f, 0.0f, 0.0f), Vec3(0, 1, 0));
    }
}

float landHoehe(float x, float z, float x0, float z0, float x1, float z1, float flach, unsigned saat) {
    float dx = std::max(0.0f, std::max(x0 - x, x - x1));
    float dz = std::max(0.0f, std::max(z0 - z, z - z1));
    float d = std::sqrt(dx * dx + dz * dz);
    float berg = bergRauschen(x / 300.0f, z / 300.0f, static_cast<int>(saat), 4, 0.5f);
    float huegel = bergRauschen(x / 90.0f, z / 90.0f, static_cast<int>(saat) + 77, 3, 0.5f);
    float anstieg = sanft(40.0f, 420.0f, d);
    float hoehe = flach + anstieg * (berg * 260.0f - 40.0f) + sanft(10.0f, 120.0f, d) * huegel * 14.0f;
    float see = wertRauschen(x / 430.0f + 3.1f, z / 430.0f - 7.3f, static_cast<int>(saat) + 911);
    float tiefe = sanft(0.56f, 0.68f, see) * sanft(130.0f, 230.0f, d);
    return mische(std::max(flach, hoehe), flach - 7.0f, tiefe);
}

void landschaftBauen(const Strecke& strecke, unsigned saat, Bauer& land, Bauer& baeume) {
    land.leeren();
    baeume.leeren();
    int gx0 = 0, gz0 = 0, gx1 = 0, gz1 = 0;
    strecke.grenzen(gx0, gz0, gx1, gz1);
    float x0 = gx0 * ZELLE - 50.0f;
    float z0 = gz0 * ZELLE - 50.0f;
    float x1 = gx1 * ZELLE + 50.0f;
    float z1 = gz1 * ZELLE + 50.0f;
    float flach = std::min(0.0f, strecke.tiefstes()) - 0.6f;
    const float rand = 900.0f;
    const float masche = 36.0f;
    int nx = static_cast<int>((x1 - x0 + 2.0f * rand) / masche) + 1;
    int nz = static_cast<int>((z1 - z0 + 2.0f * rand) / masche) + 1;
    nx = std::min(nx, 160);
    nz = std::min(nz, 160);
    float sx = (x1 - x0 + 2.0f * rand) / (nx - 1);
    float sz = (z1 - z0 + 2.0f * rand) / (nz - 1);
    std::vector<Vec3> punkte(static_cast<size_t>(nx) * nz);
    for (int j = 0; j < nz; ++j) {
        for (int i = 0; i < nx; ++i) {
            float x = x0 - rand + i * sx;
            float z = z0 - rand + j * sz;
            float wackel = (streu(i, j, static_cast<int>(saat)) - 0.5f) * 0.35f;
            float px = x + wackel * sx;
            float pz = z + (streu(j, i, static_cast<int>(saat) + 3) - 0.5f) * 0.35f * sz;
            punkte[static_cast<size_t>(j) * nx + i] = Vec3(px, landHoehe(px, pz, x0, z0, x1, z1, flach, saat), pz);
        }
    }
    auto farbeFuer = [&](Vec3 a, Vec3 b, Vec3 c, int i, int j) {
        float h = (a.y + b.y + c.y) / 3.0f - flach;
        Vec3 n = normiert(kreuz(b - a, c - a));
        float steil = 1.0f - std::fabs(n.y);
        float zufall = streu(i * 3 + 1, j * 5 + 2, static_cast<int>(saat));
        Vec3 gras = mische(Vec3(0.36f, 0.6f, 0.3f), Vec3(0.28f, 0.52f, 0.27f), zufall);
        if (h < 1.0f) gras = mische(Vec3(0.42f, 0.64f, 0.33f), Vec3(0.38f, 0.6f, 0.31f), zufall);
        Vec3 wald(0.2f, 0.42f, 0.24f);
        Vec3 fels = mische(Vec3(0.5f, 0.48f, 0.45f), Vec3(0.42f, 0.4f, 0.38f), zufall);
        Vec3 schnee(0.94f, 0.95f, 0.98f);
        Vec3 farbe = mische(gras, wald, sanft(30.0f, 90.0f, h));
        farbe = mische(farbe, Vec3(0.66f, 0.6f, 0.44f), sanft(-0.2f, -1.2f, h));
        farbe = mische(farbe, fels, sanft(0.35f, 0.6f, steil) * sanft(20.0f, 60.0f, h));
        farbe = mische(farbe, fels, sanft(120.0f, 160.0f, h));
        farbe = mische(farbe, schnee, sanft(185.0f, 215.0f, h));
        return farbe;
    };
    for (int j = 0; j + 1 < nz; ++j) {
        for (int i = 0; i + 1 < nx; ++i) {
            Vec3 a = punkte[static_cast<size_t>(j) * nx + i];
            Vec3 b = punkte[static_cast<size_t>(j) * nx + i + 1];
            Vec3 c = punkte[static_cast<size_t>(j + 1) * nx + i + 1];
            Vec3 d = punkte[static_cast<size_t>(j + 1) * nx + i];
            dreieckAussen(land, a, b, c, farbeFuer(a, b, c, i, j), Vec3(0, 1, 0));
            dreieckAussen(land, a, c, d, farbeFuer(a, c, d, i + 7, j), Vec3(0, 1, 0));
        }
    }
    Zufall zufall(saat * 7919ull + 13ull);
    int gesetzt = 0;
    for (int versuch = 0; versuch < 6000 && gesetzt < 520; ++versuch) {
        float x = zufall.bereich(x0 - rand * 0.7f, x1 + rand * 0.7f);
        float z = zufall.bereich(z0 - rand * 0.7f, z1 + rand * 0.7f);
        bool nah = false;
        for (const Stueck& s : strecke.stuecke) {
            float dx = x - s.x * ZELLE;
            float dz = z - s.z * ZELLE;
            if (dx * dx + dz * dz < 26.0f * 26.0f) {
                nah = true;
                break;
            }
        }
        if (nah) continue;
        float y = landHoehe(x, z, x0, z0, x1, z1, flach, saat);
        if (y - flach > 120.0f || y < flach - 0.4f) continue;
        float groesse = zufall.bereich(0.8f, 1.5f);
        Vec3 stamm(0.36f, 0.24f, 0.15f);
        Vec3 nadel = mische(Vec3(0.13f, 0.36f, 0.2f), Vec3(0.2f, 0.46f, 0.22f), zufall.einheit());
        baeume.roehre(Vec3(x, y - 0.5f, z), 0.45f * groesse, 0.35f * groesse, 3.0f * groesse, stamm, 6);
        baeume.roehre(Vec3(x, y + 2.2f * groesse, z), 3.4f * groesse, 0.0f, 6.5f * groesse, nadel, 7);
        baeume.roehre(Vec3(x, y + 5.6f * groesse, z), 2.5f * groesse, 0.0f, 5.0f * groesse, nadel * 1.08f, 7);
        ++gesetzt;
    }
}

void himmelBauen(Bauer& himmel, Bauer& wolken, Bauer& sonne, Vec3 sonnenRichtung) {
    himmel.leeren();
    wolken.leeren();
    sonne.leeren();
    const float r = 5200.0f;
    const int ringe = 14;
    const int teile = 28;
    Vec3 zenit(0.16f, 0.36f, 0.72f);
    Vec3 horizont(0.62f, 0.78f, 0.92f);
    Vec3 unten(0.55f, 0.66f, 0.74f);
    auto farbe = [&](float hoehe) {
        if (hoehe < 0.0f) return unten;
        return mische(horizont, zenit, std::pow(klemme(hoehe, 0.0f, 1.0f), 0.55f));
    };
    for (int j = 0; j < ringe; ++j) {
        float v0 = -0.25f + 1.25f * j / ringe;
        float v1 = -0.25f + 1.25f * (j + 1) / ringe;
        float b0 = v0 * PI * 0.5f;
        float b1 = v1 * PI * 0.5f;
        for (int i = 0; i < teile; ++i) {
            float u0 = TAU * i / teile;
            float u1 = TAU * (i + 1) / teile;
            Vec3 p00(std::cos(b0) * std::cos(u0) * r, std::sin(b0) * r, std::cos(b0) * std::sin(u0) * r);
            Vec3 p10(std::cos(b0) * std::cos(u1) * r, std::sin(b0) * r, std::cos(b0) * std::sin(u1) * r);
            Vec3 p11(std::cos(b1) * std::cos(u1) * r, std::sin(b1) * r, std::cos(b1) * std::sin(u1) * r);
            Vec3 p01(std::cos(b1) * std::cos(u0) * r, std::sin(b1) * r, std::cos(b1) * std::sin(u0) * r);
            Vec3 n(0.0f, -1.0f, 0.0f);
            himmel.ecke(p00, n, farbe(std::sin(b0)) * 0.62f);
            himmel.ecke(p10, n, farbe(std::sin(b0)) * 0.62f);
            himmel.ecke(p11, n, farbe(std::sin(b1)) * 0.62f);
            himmel.ecke(p00, n, farbe(std::sin(b0)) * 0.62f);
            himmel.ecke(p11, n, farbe(std::sin(b1)) * 0.62f);
            himmel.ecke(p01, n, farbe(std::sin(b1)) * 0.62f);
        }
    }
    Zufall zufall(424242ull);
    for (int w = 0; w < 26; ++w) {
        float winkel = zufall.bereich(0.0f, TAU);
        float weite = zufall.bereich(900.0f, 2600.0f);
        Vec3 mitte(std::cos(winkel) * weite, zufall.bereich(420.0f, 760.0f), std::sin(winkel) * weite);
        int teile2 = zufall.ganz(3, 7);
        for (int k = 0; k < teile2; ++k) {
            Vec3 versatz(zufall.bereich(-140.0f, 140.0f), zufall.bereich(-12.0f, 22.0f), zufall.bereich(-70.0f, 70.0f));
            float g = zufall.bereich(60.0f, 120.0f);
            wolken.kugel(mitte + versatz, Vec3(g, g * 0.38f, g * 0.7f), Vec3(0.96f, 0.97f, 1.0f), 5, 9);
        }
    }
    Vec3 ort = normiert(sonnenRichtung) * 4600.0f;
    sonne.kugel(ort, Vec3(150.0f), Vec3(1.0f, 0.95f, 0.8f), 8, 12);
}

void gitterBauen(Bauer& gitter, int mitteX, int mitteZ, int stufe, int weite) {
    gitter.leeren();
    const Vec3 farbe(0.55f, 0.75f, 1.0f);
    float y = stufe * STUFE + 0.06f;
    for (int i = -weite; i <= weite + 1; ++i) {
        float x = (mitteX + i) * ZELLE - ZELLE * 0.5f;
        float za = (mitteZ - weite) * ZELLE - ZELLE * 0.5f;
        float zb = (mitteZ + weite + 1) * ZELLE - ZELLE * 0.5f;
        gitter.viereck(Vec3(x - 0.12f, y, za), Vec3(x - 0.12f, y, zb), Vec3(x + 0.12f, y, zb), Vec3(x + 0.12f, y, za), farbe);
        float z = (mitteZ + i) * ZELLE - ZELLE * 0.5f;
        float xa = (mitteX - weite) * ZELLE - ZELLE * 0.5f;
        float xb = (mitteX + weite + 1) * ZELLE - ZELLE * 0.5f;
        gitter.viereck(Vec3(xa, y, z + 0.12f), Vec3(xb, y, z + 0.12f), Vec3(xb, y, z - 0.12f), Vec3(xa, y, z - 0.12f), farbe);
    }
}

void zeigerBauen(Bauer& zeiger) {
    zeiger.leeren();
    const Vec3 farbe(0.3f, 0.9f, 1.0f);
    float h = ZELLE * 0.5f;
    for (int seite = 0; seite < 4; ++seite) {
        Vec3 n = richtungWelt(seite, Vec3(0, 0, 1));
        Vec3 q = richtungWelt(seite, Vec3(1, 0, 0));
        Vec3 a = n * h - q * h + Vec3(0, 0.1f, 0);
        Vec3 b = n * h + q * h + Vec3(0, 0.1f, 0);
        Vec3 c = b - n * 0.6f;
        Vec3 d = a - n * 0.6f;
        flaeche(zeiger, a, b, c, d, farbe, Vec3(0, 1, 0));
    }
    flaeche(zeiger, Vec3(-1.0f, 0.12f, 6.0f), Vec3(1.0f, 0.12f, 6.0f), Vec3(0.0f, 0.12f, 9.0f), Vec3(-0.01f, 0.12f, 9.0f), farbe,
            Vec3(0, 1, 0));
    flaeche(zeiger, Vec3(-0.35f, 0.12f, 1.0f), Vec3(0.35f, 0.12f, 1.0f), Vec3(0.35f, 0.12f, 6.0f), Vec3(-0.35f, 0.12f, 6.0f),
            farbe, Vec3(0, 1, 0));
}

}
