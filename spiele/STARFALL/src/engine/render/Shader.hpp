#pragma once

#include "../core/Result.hpp"
#include "../math/Mat4.hpp"
#include "../math/Vec4.hpp"
#include "GLApi.hpp"

#include <string>
#include <unordered_map>

namespace sf {

class Shader {
public:
    Shader() = default;
    ~Shader();

    Shader(const Shader&) = delete;
    Shader& operator=(const Shader&) = delete;

    Status compile(const std::string& debugName, const char* vertexSource, const char* fragmentSource);
    void release();
    void bind() const;

    void setInt(const char* name, i32 value);
    void setFloat(const char* name, f32 value);
    void setVec2(const char* name, f32 x, f32 y);
    void setVec3(const char* name, const Vec3& value);
    void setVec4(const char* name, const Vec4& value);
    void setMat4(const char* name, const Mat4& value);
    void setTextureUnit(const char* name, i32 unit);

    bool valid() const { return program != 0; }
    GLuint handle() const { return program; }
    const std::string& name() const { return debugLabel; }

private:
    GLint uniformLocation(const char* name);

    GLuint program = 0;
    std::string debugLabel;
    std::unordered_map<std::string, GLint> uniformCache;
};

}
