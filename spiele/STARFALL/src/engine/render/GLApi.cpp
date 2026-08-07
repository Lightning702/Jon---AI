#include "GLApi.hpp"

#include "../core/Log.hpp"

#include <cstdio>

namespace sf {
namespace {

void* loadProcedure(const char* name) {
    void* pointer = reinterpret_cast<void*>(wglGetProcAddress(name));
    if (pointer == nullptr || pointer == reinterpret_cast<void*>(1) || pointer == reinterpret_cast<void*>(2) ||
        pointer == reinterpret_cast<void*>(3) || pointer == reinterpret_cast<void*>(-1)) {
        static HMODULE library = LoadLibraryA("opengl32.dll");
        pointer = library ? reinterpret_cast<void*>(GetProcAddress(library, name)) : nullptr;
    }
    return pointer;
}

u32 missingCount = 0;

template <typename T>
void bindProcedure(T& target, const char* name) {
    target = reinterpret_cast<T>(loadProcedure(name));
    if (!target) {
        ++missingCount;
        logWarning("gl", "Funktion fehlt: %s", name);
    }
}

}

GLApi& gl() {
    static GLApi api;
    return api;
}

bool loadGLApi() {
    GLApi& api = gl();
    if (api.loaded) return true;
    missingCount = 0;

    bindProcedure(api.genBuffers, "glGenBuffers");
    bindProcedure(api.deleteBuffers, "glDeleteBuffers");
    bindProcedure(api.bindBuffer, "glBindBuffer");
    bindProcedure(api.bufferData, "glBufferData");
    bindProcedure(api.bufferSubData, "glBufferSubData");
    bindProcedure(api.bindBufferBase, "glBindBufferBase");
    bindProcedure(api.genVertexArrays, "glGenVertexArrays");
    bindProcedure(api.deleteVertexArrays, "glDeleteVertexArrays");
    bindProcedure(api.bindVertexArray, "glBindVertexArray");
    bindProcedure(api.enableVertexAttribArray, "glEnableVertexAttribArray");
    bindProcedure(api.vertexAttribPointer, "glVertexAttribPointer");
    bindProcedure(api.vertexAttribIPointer, "glVertexAttribIPointer");
    bindProcedure(api.vertexAttribDivisor, "glVertexAttribDivisor");
    bindProcedure(api.createShader, "glCreateShader");
    bindProcedure(api.deleteShader, "glDeleteShader");
    bindProcedure(api.shaderSource, "glShaderSource");
    bindProcedure(api.compileShader, "glCompileShader");
    bindProcedure(api.getShaderiv, "glGetShaderiv");
    bindProcedure(api.getShaderInfoLog, "glGetShaderInfoLog");
    bindProcedure(api.createProgram, "glCreateProgram");
    bindProcedure(api.deleteProgram, "glDeleteProgram");
    bindProcedure(api.attachShader, "glAttachShader");
    bindProcedure(api.linkProgram, "glLinkProgram");
    bindProcedure(api.getProgramiv, "glGetProgramiv");
    bindProcedure(api.getProgramInfoLog, "glGetProgramInfoLog");
    bindProcedure(api.useProgram, "glUseProgram");
    bindProcedure(api.getUniformLocation, "glGetUniformLocation");
    bindProcedure(api.uniform1i, "glUniform1i");
    bindProcedure(api.uniform1ui, "glUniform1ui");
    bindProcedure(api.uniform1f, "glUniform1f");
    bindProcedure(api.uniform2f, "glUniform2f");
    bindProcedure(api.uniform3f, "glUniform3f");
    bindProcedure(api.uniform4f, "glUniform4f");
    bindProcedure(api.uniform1fv, "glUniform1fv");
    bindProcedure(api.uniform3fv, "glUniform3fv");
    bindProcedure(api.uniform4fv, "glUniform4fv");
    bindProcedure(api.uniformMatrix4fv, "glUniformMatrix4fv");
    bindProcedure(api.uniformMatrix3fv, "glUniformMatrix3fv");
    bindProcedure(api.activeTexture, "glActiveTexture");
    bindProcedure(api.generateMipmap, "glGenerateMipmap");
    bindProcedure(api.texImage3D, "glTexImage3D");
    bindProcedure(api.genFramebuffers, "glGenFramebuffers");
    bindProcedure(api.deleteFramebuffers, "glDeleteFramebuffers");
    bindProcedure(api.bindFramebuffer, "glBindFramebuffer");
    bindProcedure(api.framebufferTexture2D, "glFramebufferTexture2D");
    bindProcedure(api.checkFramebufferStatus, "glCheckFramebufferStatus");
    bindProcedure(api.genRenderbuffers, "glGenRenderbuffers");
    bindProcedure(api.deleteRenderbuffers, "glDeleteRenderbuffers");
    bindProcedure(api.bindRenderbuffer, "glBindRenderbuffer");
    bindProcedure(api.renderbufferStorage, "glRenderbufferStorage");
    bindProcedure(api.framebufferRenderbuffer, "glFramebufferRenderbuffer");
    bindProcedure(api.drawBuffers, "glDrawBuffers");
    bindProcedure(api.blitFramebuffer, "glBlitFramebuffer");
    bindProcedure(api.drawArraysInstanced, "glDrawArraysInstanced");
    bindProcedure(api.drawElementsInstanced, "glDrawElementsInstanced");
    bindProcedure(api.blendFuncSeparate, "glBlendFuncSeparate");
    bindProcedure(api.blendEquation, "glBlendEquation");
    bindProcedure(api.blendColor, "glBlendColor");
    bindProcedure(api.getStringi, "glGetStringi");
    bindProcedure(api.dispatchCompute, "glDispatchCompute");
    bindProcedure(api.memoryBarrier, "glMemoryBarrier");

    glGetIntegerv(GL_MAJOR_VERSION, &api.majorVersion);
    glGetIntegerv(GL_MINOR_VERSION, &api.minorVersion);

    const GLubyte* renderer = glGetString(GL_RENDERER);
    const GLubyte* vendor = glGetString(GL_VENDOR);
    const GLubyte* version = glGetString(GL_VERSION);
    std::snprintf(api.rendererName, sizeof(api.rendererName), "%s",
                  renderer ? reinterpret_cast<const char*>(renderer) : "unbekannt");
    std::snprintf(api.vendorName, sizeof(api.vendorName), "%s",
                  vendor ? reinterpret_cast<const char*>(vendor) : "unbekannt");
    logInfo("gl", "Renderer: %s", api.rendererName);
    logInfo("gl", "Hersteller: %s", api.vendorName);
    logInfo("gl", "Version: %s", version ? reinterpret_cast<const char*>(version) : "unbekannt");

    api.loaded = missingCount < 8;
    if (!api.loaded) {
        logError("gl", "%u OpenGL-Funktionen fehlen, Treiber zu alt", missingCount);
    }
    return api.loaded;
}

}
