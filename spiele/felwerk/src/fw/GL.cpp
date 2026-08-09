#include "GL.hpp"

namespace fw {

PfnGenBuffers glGenBuffers = nullptr;
PfnBindBuffer glBindBuffer = nullptr;
PfnBufferData glBufferData = nullptr;
PfnBufferSubData glBufferSubData = nullptr;
PfnDeleteBuffers glDeleteBuffers = nullptr;
PfnGenVertexArrays glGenVertexArrays = nullptr;
PfnBindVertexArray glBindVertexArray = nullptr;
PfnDeleteVertexArrays glDeleteVertexArrays = nullptr;
PfnVertexAttribPointer glVertexAttribPointer = nullptr;
PfnEnableVertexAttribArray glEnableVertexAttribArray = nullptr;
PfnCreateShader glCreateShader = nullptr;
PfnShaderSource glShaderSource = nullptr;
PfnCompileShader glCompileShader = nullptr;
PfnGetShaderiv glGetShaderiv = nullptr;
PfnGetShaderInfoLog glGetShaderInfoLog = nullptr;
PfnDeleteShader glDeleteShader = nullptr;
PfnCreateProgram glCreateProgram = nullptr;
PfnAttachShader glAttachShader = nullptr;
PfnLinkProgram glLinkProgram = nullptr;
PfnGetProgramiv glGetProgramiv = nullptr;
PfnGetProgramInfoLog glGetProgramInfoLog = nullptr;
PfnUseProgram glUseProgram = nullptr;
PfnDeleteProgram glDeleteProgram = nullptr;
PfnGetUniformLocation glGetUniformLocation = nullptr;
PfnUniform1i glUniform1i = nullptr;
PfnUniform1f glUniform1f = nullptr;
PfnUniform2f glUniform2f = nullptr;
PfnUniform3f glUniform3f = nullptr;
PfnUniform4f glUniform4f = nullptr;
PfnUniformMatrix4fv glUniformMatrix4fv = nullptr;
PfnActiveTexture glActiveTexture = nullptr;
PfnGenerateMipmap glGenerateMipmap = nullptr;

namespace {

const char* fehlend = nullptr;
HMODULE opengl = nullptr;

void* hole(const char* name) {
    void* zeiger = reinterpret_cast<void*>(wglGetProcAddress(name));
    const intptr_t roh = reinterpret_cast<intptr_t>(zeiger);
    if (roh == 0 || roh == 1 || roh == 2 || roh == 3 || roh == -1) {
        if (!opengl) opengl = LoadLibraryA("opengl32.dll");
        zeiger = opengl ? reinterpret_cast<void*>(GetProcAddress(opengl, name)) : nullptr;
    }
    if (!zeiger && !fehlend) fehlend = name;
    return zeiger;
}

template <typename T>
void binde(T& ziel, const char* name) {
    ziel = reinterpret_cast<T>(hole(name));
}

}

const char* fehlendeFunktion() { return fehlend ? fehlend : ""; }

bool ladeGL() {
    fehlend = nullptr;
    binde(glGenBuffers, "glGenBuffers");
    binde(glBindBuffer, "glBindBuffer");
    binde(glBufferData, "glBufferData");
    binde(glBufferSubData, "glBufferSubData");
    binde(glDeleteBuffers, "glDeleteBuffers");
    binde(glGenVertexArrays, "glGenVertexArrays");
    binde(glBindVertexArray, "glBindVertexArray");
    binde(glDeleteVertexArrays, "glDeleteVertexArrays");
    binde(glVertexAttribPointer, "glVertexAttribPointer");
    binde(glEnableVertexAttribArray, "glEnableVertexAttribArray");
    binde(glCreateShader, "glCreateShader");
    binde(glShaderSource, "glShaderSource");
    binde(glCompileShader, "glCompileShader");
    binde(glGetShaderiv, "glGetShaderiv");
    binde(glGetShaderInfoLog, "glGetShaderInfoLog");
    binde(glDeleteShader, "glDeleteShader");
    binde(glCreateProgram, "glCreateProgram");
    binde(glAttachShader, "glAttachShader");
    binde(glLinkProgram, "glLinkProgram");
    binde(glGetProgramiv, "glGetProgramiv");
    binde(glGetProgramInfoLog, "glGetProgramInfoLog");
    binde(glUseProgram, "glUseProgram");
    binde(glDeleteProgram, "glDeleteProgram");
    binde(glGetUniformLocation, "glGetUniformLocation");
    binde(glUniform1i, "glUniform1i");
    binde(glUniform1f, "glUniform1f");
    binde(glUniform2f, "glUniform2f");
    binde(glUniform3f, "glUniform3f");
    binde(glUniform4f, "glUniform4f");
    binde(glUniformMatrix4fv, "glUniformMatrix4fv");
    binde(glActiveTexture, "glActiveTexture");
    binde(glGenerateMipmap, "glGenerateMipmap");
    return fehlend == nullptr;
}

}
