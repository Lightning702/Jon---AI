#pragma once

#include <string>

#include "GL.hpp"
#include "Mathe.hpp"

namespace fw {

class Shader {
public:
    ~Shader();

    bool bauen(const char* eckenQuelle, const char* farbQuelle);
    void benutzen() const;
    void freigeben();

    void setze(const char* name, float wert) const;
    void setze(const char* name, int wert) const;
    void setze(const char* name, Vec2 wert) const;
    void setze(const char* name, Vec3 wert) const;
    void setze(const char* name, const Mat4& wert) const;
    void setze(const char* name, float a, float b, float c, float d) const;

    unsigned kennung() const { return programm; }
    const std::string& fehler() const { return meldung; }

private:
    unsigned programm = 0;
    std::string meldung;
};

}
