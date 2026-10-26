#pragma once

#include "Strecke.hpp"
#include "fw/Mathe.hpp"

namespace blitzbahn {

constexpr float SCHWERKRAFT = 24.0f;
constexpr float HOECHSTTEMPO = 74.0f;
constexpr float RADSTAND = 2.7f;
constexpr float RADRADIUS = 0.42f;
constexpr float AUTO_RADIUS = 1.05f;

struct Eingabe {
    float gas = 0.0f;
    float bremse = 0.0f;
    float lenkung = 0.0f;
    bool handbremse = false;
};

struct Lage {
    fw::Vec3 ort;
    fw::Vec3 vorne = fw::Vec3(0.0f, 0.0f, 1.0f);
    fw::Vec3 oben = fw::Vec3(0.0f, 1.0f, 0.0f);
};

fw::Mat4 lageMatrix(const Lage& lage);

class Fahrzeug {
public:
    void setzen(fw::Vec3 ort, float gier);
    void schritt(const Strecke& strecke, const Eingabe& eingabe, float dt);

    float tempo() const;
    float vorwaerts() const;
    Lage lage() const;
    fw::Mat4 matrix() const { return lageMatrix(lage()); }
    fw::Vec3 vorne() const;
    fw::Vec3 obenVektor() const { return oben; }

    fw::Vec3 ort;
    fw::Vec3 fahrt;
    float gier = 0.0f;
    float nick = 0.0f;
    float rollen = 0.0f;
    float lenkwinkel = 0.0f;
    float radDrehung = 0.0f;
    float luftzeit = 0.0f;
    float aufprall = 0.0f;
    float wandstoss = 0.0f;
    float schub = 0.0f;
    bool amBoden = false;
    bool driftet = false;
    bool fahrhilfe = true;
    float drift = 0.0f;
    int bodenTeil = LEER;
    int bodenStueck = -1;
    int kontaktStueck = -1;
    float bodenLz = 0.0f;
    float bodenHoehe = 0.0f;

private:
    fw::Vec3 oben = fw::Vec3(0.0f, 1.0f, 0.0f);
};

}
