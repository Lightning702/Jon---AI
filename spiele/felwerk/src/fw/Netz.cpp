#include "Netz.hpp"

namespace fw {

void Bauer::leeren() {
    ecken.clear();
    indizes.clear();
}

void Bauer::ecke(Vec3 ort, Vec3 normale, Vec3 farbe, float rauheit) {
    ecke(ort, normale, farbe, rauheit, Vec2(0.0f, 0.0f));
}

void Bauer::ecke(Vec3 ort, Vec3 normale, Vec3 farbe, float rauheit, Vec2 bild) {
    Ecke e;
    e.ort = ort;
    e.normale = normale;
    e.farbe = farbe;
    e.rauheit = rauheit;
    e.bild = bild;
    indizes.push_back(static_cast<uint32_t>(ecken.size()));
    ecken.push_back(e);
}

void Bauer::dreieck(Vec3 a, Vec3 b, Vec3 c, Vec3 farbe, float rauheit) {
    Vec3 normale = normiert(kreuz(b - a, c - a));
    ecke(a, normale, farbe, rauheit);
    ecke(b, normale, farbe, rauheit);
    ecke(c, normale, farbe, rauheit);
}

void Bauer::viereck(Vec3 a, Vec3 b, Vec3 c, Vec3 d, Vec3 farbe, float rauheit) {
    dreieck(a, b, c, farbe, rauheit);
    dreieck(a, c, d, farbe, rauheit);
}

void Bauer::quader(Vec3 mitte, Vec3 halb, Vec3 farbe, float drehung, float rauheit) {
    float s = std::sin(drehung);
    float c = std::cos(drehung);
    auto punktAt = [&](float x, float y, float z) {
        return Vec3(mitte.x + x * c + z * s, mitte.y + y, mitte.z - x * s + z * c);
    };
    Vec3 v000 = punktAt(-halb.x, -halb.y, -halb.z);
    Vec3 v100 = punktAt(halb.x, -halb.y, -halb.z);
    Vec3 v110 = punktAt(halb.x, halb.y, -halb.z);
    Vec3 v010 = punktAt(-halb.x, halb.y, -halb.z);
    Vec3 v001 = punktAt(-halb.x, -halb.y, halb.z);
    Vec3 v101 = punktAt(halb.x, -halb.y, halb.z);
    Vec3 v111 = punktAt(halb.x, halb.y, halb.z);
    Vec3 v011 = punktAt(-halb.x, halb.y, halb.z);
    Vec3 oben = farbe * 1.06f;
    Vec3 unten = farbe * 0.7f;
    Vec3 seite = farbe * 0.9f;
    viereck(v011, v111, v110, v010, oben, rauheit);
    viereck(v000, v100, v101, v001, unten, rauheit);
    viereck(v001, v101, v111, v011, farbe, rauheit);
    viereck(v100, v000, v010, v110, seite, rauheit);
    viereck(v000, v001, v011, v010, seite, rauheit);
    viereck(v101, v100, v110, v111, farbe, rauheit);
}

void Bauer::kugel(Vec3 mitte, Vec3 radien, Vec3 farbe, int ringe, int segmente, float rauheit) {
    for (int r = 0; r < ringe; ++r) {
        float t0 = static_cast<float>(r) / static_cast<float>(ringe);
        float t1 = static_cast<float>(r + 1) / static_cast<float>(ringe);
        float phi0 = t0 * PI;
        float phi1 = t1 * PI;
        for (int s = 0; s < segmente; ++s) {
            float u0 = static_cast<float>(s) / static_cast<float>(segmente) * TAU;
            float u1 = static_cast<float>(s + 1) / static_cast<float>(segmente) * TAU;
            auto richtung = [](float phi, float u) {
                return Vec3(std::sin(phi) * std::cos(u), std::cos(phi), std::sin(phi) * std::sin(u));
            };
            Vec3 n00 = richtung(phi0, u0);
            Vec3 n01 = richtung(phi0, u1);
            Vec3 n10 = richtung(phi1, u0);
            Vec3 n11 = richtung(phi1, u1);
            Vec3 p00 = mitte + n00 * radien;
            Vec3 p01 = mitte + n01 * radien;
            Vec3 p10 = mitte + n10 * radien;
            Vec3 p11 = mitte + n11 * radien;
            ecke(p00, n00, farbe, rauheit);
            ecke(p11, n11, farbe, rauheit);
            ecke(p10, n10, farbe, rauheit);
            ecke(p00, n00, farbe, rauheit);
            ecke(p01, n01, farbe, rauheit);
            ecke(p11, n11, farbe, rauheit);
        }
    }
}

void Bauer::halbkugel(Vec3 mitte, Vec3 radien, Vec3 farbe, int ringe, int segmente, float rauheit) {
    for (int r = 0; r < ringe; ++r) {
        float phi0 = static_cast<float>(r) / static_cast<float>(ringe) * PI * 0.5f;
        float phi1 = static_cast<float>(r + 1) / static_cast<float>(ringe) * PI * 0.5f;
        for (int s = 0; s < segmente; ++s) {
            float u0 = static_cast<float>(s) / static_cast<float>(segmente) * TAU;
            float u1 = static_cast<float>(s + 1) / static_cast<float>(segmente) * TAU;
            auto richtung = [](float phi, float u) {
                return Vec3(std::sin(phi) * std::cos(u), std::cos(phi), std::sin(phi) * std::sin(u));
            };
            Vec3 n00 = richtung(phi0, u0);
            Vec3 n01 = richtung(phi0, u1);
            Vec3 n10 = richtung(phi1, u0);
            Vec3 n11 = richtung(phi1, u1);
            ecke(mitte + n00 * radien, n00, farbe, rauheit);
            ecke(mitte + n11 * radien, n11, farbe, rauheit);
            ecke(mitte + n10 * radien, n10, farbe, rauheit);
            ecke(mitte + n00 * radien, n00, farbe, rauheit);
            ecke(mitte + n01 * radien, n01, farbe, rauheit);
            ecke(mitte + n11 * radien, n11, farbe, rauheit);
        }
    }
}

void Bauer::roehre(Vec3 fuss, float radiusUnten, float radiusOben, float hoehe, Vec3 farbe,
                   int segmente, float rauheit) {
    Vec3 spitzeMitte = fuss + Vec3(0.0f, hoehe, 0.0f);
    for (int s = 0; s < segmente; ++s) {
        float u0 = static_cast<float>(s) / static_cast<float>(segmente) * TAU;
        float u1 = static_cast<float>(s + 1) / static_cast<float>(segmente) * TAU;
        Vec3 r0(std::cos(u0), 0.0f, std::sin(u0));
        Vec3 r1(std::cos(u1), 0.0f, std::sin(u1));
        Vec3 a = fuss + r0 * radiusUnten;
        Vec3 b = fuss + r1 * radiusUnten;
        Vec3 c = spitzeMitte + r1 * radiusOben;
        Vec3 d = spitzeMitte + r0 * radiusOben;
        Vec3 n0 = normiert(Vec3(r0.x, (radiusUnten - radiusOben) / (hoehe + 1e-4f), r0.z));
        Vec3 n1 = normiert(Vec3(r1.x, (radiusUnten - radiusOben) / (hoehe + 1e-4f), r1.z));
        if (radiusOben > 0.001f) {
            ecke(a, n0, farbe, rauheit);
            ecke(c, n1, farbe, rauheit);
            ecke(b, n1, farbe, rauheit);
            ecke(a, n0, farbe, rauheit);
            ecke(d, n0, farbe, rauheit);
            ecke(c, n1, farbe, rauheit);
            ecke(spitzeMitte, Vec3(0.0f, 1.0f, 0.0f), farbe * 1.05f, rauheit);
            ecke(c, Vec3(0.0f, 1.0f, 0.0f), farbe * 1.05f, rauheit);
            ecke(d, Vec3(0.0f, 1.0f, 0.0f), farbe * 1.05f, rauheit);
        } else {
            ecke(a, n0, farbe, rauheit);
            ecke(spitzeMitte, normiert(n0 + n1), farbe * 1.05f, rauheit);
            ecke(b, n1, farbe, rauheit);
        }
        ecke(fuss, Vec3(0.0f, -1.0f, 0.0f), farbe * 0.65f, rauheit);
        ecke(a, Vec3(0.0f, -1.0f, 0.0f), farbe * 0.65f, rauheit);
        ecke(b, Vec3(0.0f, -1.0f, 0.0f), farbe * 0.65f, rauheit);
    }
}

void Bauer::scheibe(Vec3 mitte, float radius, Vec3 farbe, int segmente, float rauheit) {
    Vec3 oben(0.0f, 1.0f, 0.0f);
    for (int s = 0; s < segmente; ++s) {
        float u0 = static_cast<float>(s) / static_cast<float>(segmente) * TAU;
        float u1 = static_cast<float>(s + 1) / static_cast<float>(segmente) * TAU;
        Vec3 a = mitte + Vec3(std::cos(u0) * radius, 0.0f, std::sin(u0) * radius);
        Vec3 b = mitte + Vec3(std::cos(u1) * radius, 0.0f, std::sin(u1) * radius);
        ecke(mitte, oben, farbe, rauheit);
        ecke(b, oben, farbe, rauheit);
        ecke(a, oben, farbe, rauheit);
    }
}

void Bauer::band(Vec3 von, Vec3 bis, float breite, float dicke, Vec3 farbe) {
    Vec3 richtung = bis - von;
    float laengeXZ = std::sqrt(richtung.x * richtung.x + richtung.z * richtung.z);
    if (laengeXZ < 1e-4f) return;
    Vec3 quer = normiert(Vec3(-richtung.z, 0.0f, richtung.x)) * (breite * 0.5f);
    Vec3 hoch(0.0f, dicke, 0.0f);
    Vec3 a = von - quer;
    Vec3 b = von + quer;
    Vec3 c = bis + quer;
    Vec3 d = bis - quer;
    viereck(a + hoch, b + hoch, c + hoch, d + hoch, farbe * 1.05f);
    viereck(d, c, b, a, farbe * 0.6f);
    viereck(a, b, b + hoch, a + hoch, farbe * 0.85f);
    viereck(c, d, d + hoch, c + hoch, farbe * 0.85f);
    viereck(b, c, c + hoch, b + hoch, farbe * 0.9f);
    viereck(d, a, a + hoch, d + hoch, farbe * 0.9f);
}

void Bauer::anhaengen(const Bauer& anderer, Vec3 versatz, float drehung, float mass) {
    float s = std::sin(drehung);
    float c = std::cos(drehung);
    uint32_t basis = static_cast<uint32_t>(ecken.size());
    for (const Ecke& e : anderer.daten()) {
        Ecke neu = e;
        Vec3 p = e.ort * mass;
        neu.ort = Vec3(p.x * c + p.z * s, p.y, -p.x * s + p.z * c) + versatz;
        Vec3 n = e.normale;
        neu.normale = Vec3(n.x * c + n.z * s, n.y, -n.x * s + n.z * c);
        ecken.push_back(neu);
    }
    for (uint32_t i : anderer.reihenfolge()) indizes.push_back(basis + i);
}

Netz::~Netz() { freigeben(); }

void Netz::hochladen(const Bauer& bauer, bool dynamisch) {
    const std::vector<Ecke>& ecken = bauer.daten();
    const std::vector<uint32_t>& folge = bauer.reihenfolge();
    anzahl = static_cast<int>(folge.size());
    if (ecken.empty() || folge.empty() || !glGenVertexArrays) return;
    if (!feld) {
        glGenVertexArrays(1, &feld);
        glGenBuffers(1, &puffer);
        glGenBuffers(1, &reihung);
    }
    const GLenum verwendung = dynamisch ? GL_DYNAMIC_DRAW : GL_STATIC_DRAW;
    glBindVertexArray(feld);
    glBindBuffer(GL_ARRAY_BUFFER, puffer);
    const ptrdiff_t eckenBytes = static_cast<ptrdiff_t>(ecken.size() * sizeof(Ecke));
    if (dynamisch && static_cast<int>(ecken.size()) <= kapazitaetEcken) {
        glBufferSubData(GL_ARRAY_BUFFER, 0, eckenBytes, ecken.data());
    } else {
        glBufferData(GL_ARRAY_BUFFER, eckenBytes, ecken.data(), verwendung);
        kapazitaetEcken = static_cast<int>(ecken.size());
    }
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, reihung);
    const ptrdiff_t folgeBytes = static_cast<ptrdiff_t>(folge.size() * sizeof(uint32_t));
    if (dynamisch && static_cast<int>(folge.size()) <= kapazitaetIndizes) {
        glBufferSubData(GL_ELEMENT_ARRAY_BUFFER, 0, folgeBytes, folge.data());
    } else {
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, folgeBytes, folge.data(), verwendung);
        kapazitaetIndizes = static_cast<int>(folge.size());
    }
    const GLsizei schritt = static_cast<GLsizei>(sizeof(Ecke));
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, schritt, reinterpret_cast<void*>(0));
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, schritt, reinterpret_cast<void*>(sizeof(Vec3)));
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, schritt, reinterpret_cast<void*>(sizeof(Vec3) * 2));
    glEnableVertexAttribArray(3);
    glVertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, schritt, reinterpret_cast<void*>(sizeof(Vec3) * 3));
    glEnableVertexAttribArray(4);
    glVertexAttribPointer(4, 2, GL_FLOAT, GL_FALSE, schritt,
                          reinterpret_cast<void*>(sizeof(Vec3) * 3 + sizeof(float)));
    glBindVertexArray(0);
}

void Netz::zeichnen() const {
    if (!feld || anzahl <= 0 || !glBindVertexArray) return;
    glBindVertexArray(feld);
    glDrawElements(GL_TRIANGLES, anzahl, GL_UNSIGNED_INT, nullptr);
    glBindVertexArray(0);
}

void Netz::freigeben() {
    if (!glDeleteBuffers || !glDeleteVertexArrays) {
        reihung = 0;
        puffer = 0;
        feld = 0;
        anzahl = 0;
        return;
    }
    if (reihung) glDeleteBuffers(1, &reihung);
    if (puffer) glDeleteBuffers(1, &puffer);
    if (feld) glDeleteVertexArrays(1, &feld);
    reihung = 0;
    puffer = 0;
    feld = 0;
    anzahl = 0;
    kapazitaetEcken = 0;
    kapazitaetIndizes = 0;
}

}
