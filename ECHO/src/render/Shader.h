#pragma once

#include "../platform/GL.h"
#include "../core/Math.h"

namespace echo {

class Shader {
public:
    Shader() {}
    ~Shader() { destroy(); }
    Shader(const Shader&) = delete;
    Shader& operator=(const Shader&) = delete;

    bool loadFromFiles(const std::string& vsPath, const std::string& fsPath, const std::string& defines = "");
    bool loadFromSource(const std::string& vs, const std::string& fs, const std::string& tag);
    void destroy();
    void bind() const;
    bool valid() const { return program != 0; }
    GLuint id() const { return program; }
    const std::string& name() const { return tagName; }
    bool reload();

    void setInt(const char* n, int v);
    void setFloat(const char* n, float v);
    void setVec2(const char* n, const em::Vec2& v);
    void setVec3(const char* n, const em::Vec3& v);
    void setVec4(const char* n, const em::Vec4& v);
    void setMat3(const char* n, const em::Mat3& v);
    void setMat4(const char* n, const em::Mat4& v);
    void setFloatArray(const char* n, const float* v, int count);
    void setVec3Array(const char* n, const float* v, int count);
    void setVec4Array(const char* n, const float* v, int count);
    void setIntArray(const char* n, const int* v, int count);
    void setTexture(const char* n, int unit, GLuint tex, GLenum target = GL_TEXTURE_2D);

private:
    GLint location(const char* n);
    static GLuint compile(GLenum type, const std::string& src, const std::string& tag);
    static std::string preprocess(const std::string& src, const std::string& dir, int depth);

    GLuint program = 0;
    std::string tagName;
    std::string vsFile, fsFile, defineBlock;
    std::unordered_map<std::string, GLint> uniforms;
};

}
