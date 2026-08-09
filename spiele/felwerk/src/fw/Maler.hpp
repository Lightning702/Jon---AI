#pragma once

#include "Mathe.hpp"
#include "Netz.hpp"
#include "Shader.hpp"

namespace fw {

class Maler {
public:
    bool erstellen();
    void freigeben();

    void beginnen(const Mat4& sicht, const Mat4& projektion, Vec3 auge, float zeit);
    void licht(Vec3 richtung, Vec3 sonne, Vec3 himmel, Vec3 boden);
    void nebel(Vec3 farbe, float dichte, float hoehenfall, Vec3 bezug, float start);
    void stufen(float wert);

    void modell(const Mat4& matrix);
    void toenung(Vec3 farbe);
    void leuchten(float wert);
    void deckkraft(float wert);
    void welle(float staerke, float weite);
    void zeichnen(const Netz& netz);

    const Shader& schattierer() const { return programm; }

private:
    Shader programm;
};

}
