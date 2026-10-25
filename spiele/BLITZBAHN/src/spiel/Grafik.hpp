#pragma once

#include "fw/Mathe.hpp"
#include "fw/Netz.hpp"
#include "fw/Shader.hpp"

namespace blitzbahn {

enum Stoff : int {
    STOFF_NORMAL = 0,
    STOFF_LAND = 1,
    STOFF_BAHN = 2,
    STOFF_WASSER = 3,
    STOFF_LACK = 4,
    STOFF_HIMMEL = 5,
    STOFF_TEILCHEN = 6,
    STOFF_WOLKE = 7
};

class Grafik {
public:
    bool erstellen(int schattenGroesse = 2048);
    void freigeben();
    bool schattenMoeglich() const { return schattenBereit; }

    void schattenBeginnen(fw::Vec3 mitte, fw::Vec3 sonne, float radius);
    void schattenModell(const fw::Mat4& matrix);
    void schattenZeichnen(const fw::Netz& netz);
    void schattenBeenden(int breite, int hoehe);

    void beginnen(const fw::Mat4& sicht, const fw::Mat4& projektion, fw::Vec3 auge, float zeit, fw::Vec3 sonne, bool mitSchatten);
    void stoff(int art);
    void modell(const fw::Mat4& matrix);
    void toenung(fw::Vec3 farbe);
    void leuchten(float wert);
    void deckkraft(float wert);
    void nebel(float dichte);
    void zeichnen(const fw::Netz& netz);

private:
    fw::Shader welt;
    fw::Shader tiefe;
    unsigned rahmen = 0;
    unsigned tiefenBild = 0;
    int groesse = 2048;
    bool schattenBereit = false;
    fw::Mat4 lichtMatrix;
};

}
