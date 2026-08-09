#include "Shader.hpp"

#include <vector>

#include "Protokoll.hpp"

namespace fw {
namespace {

unsigned uebersetze(GLenum art, const char* quelle, std::string& meldung) {
    unsigned teil = glCreateShader(art);
    glShaderSource(teil, 1, &quelle, nullptr);
    glCompileShader(teil);
    GLint erfolg = 0;
    glGetShaderiv(teil, GL_COMPILE_STATUS, &erfolg);
    if (!erfolg) {
        GLint laenge = 0;
        glGetShaderiv(teil, GL_INFO_LOG_LENGTH, &laenge);
        std::vector<char> text(laenge > 1 ? laenge : 1, '\0');
        glGetShaderInfoLog(teil, laenge, nullptr, text.data());
        meldung = text.data();
        glDeleteShader(teil);
        return 0;
    }
    return teil;
}

}

Shader::~Shader() { freigeben(); }

bool Shader::bauen(const char* eckenQuelle, const char* farbQuelle) {
    freigeben();
    unsigned ecken = uebersetze(GL_VERTEX_SHADER, eckenQuelle, meldung);
    if (!ecken) {
        warnung("Eckenshader: %s", meldung.c_str());
        return false;
    }
    unsigned farben = uebersetze(GL_FRAGMENT_SHADER, farbQuelle, meldung);
    if (!farben) {
        warnung("Farbshader: %s", meldung.c_str());
        glDeleteShader(ecken);
        return false;
    }
    programm = glCreateProgram();
    glAttachShader(programm, ecken);
    glAttachShader(programm, farben);
    glLinkProgram(programm);
    GLint erfolg = 0;
    glGetProgramiv(programm, GL_LINK_STATUS, &erfolg);
    if (!erfolg) {
        GLint laenge = 0;
        glGetProgramiv(programm, GL_INFO_LOG_LENGTH, &laenge);
        std::vector<char> text(laenge > 1 ? laenge : 1, '\0');
        glGetProgramInfoLog(programm, laenge, nullptr, text.data());
        meldung = text.data();
        warnung("Shader verbinden: %s", meldung.c_str());
        glDeleteProgram(programm);
        programm = 0;
    }
    glDeleteShader(ecken);
    glDeleteShader(farben);
    return programm != 0;
}

void Shader::benutzen() const {
    if (programm) glUseProgram(programm);
}

void Shader::freigeben() {
    if (programm) {
        glDeleteProgram(programm);
        programm = 0;
    }
}

void Shader::setze(const char* name, float wert) const {
    glUniform1f(glGetUniformLocation(programm, name), wert);
}

void Shader::setze(const char* name, int wert) const {
    glUniform1i(glGetUniformLocation(programm, name), wert);
}

void Shader::setze(const char* name, Vec2 wert) const {
    glUniform2f(glGetUniformLocation(programm, name), wert.x, wert.y);
}

void Shader::setze(const char* name, Vec3 wert) const {
    glUniform3f(glGetUniformLocation(programm, name), wert.x, wert.y, wert.z);
}

void Shader::setze(const char* name, float a, float b, float c, float d) const {
    glUniform4f(glGetUniformLocation(programm, name), a, b, c, d);
}

void Shader::setze(const char* name, const Mat4& wert) const {
    glUniformMatrix4fv(glGetUniformLocation(programm, name), 1, GL_FALSE, wert.m);
}

}
