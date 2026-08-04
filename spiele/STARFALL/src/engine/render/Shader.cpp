#include "Shader.hpp"

#include "../core/Log.hpp"

#include <vector>

namespace sf {
namespace {

GLuint compileStage(GLenum stage, const char* source, const std::string& debugName, std::string& errorOut) {
    GLApi& api = gl();
    const GLuint shader = api.createShader(stage);
    api.shaderSource(shader, 1, &source, nullptr);
    api.compileShader(shader);

    GLint status = 0;
    api.getShaderiv(shader, GL_COMPILE_STATUS, &status);
    if (status == GL_TRUE) return shader;

    GLint logLength = 0;
    api.getShaderiv(shader, GL_INFO_LOG_LENGTH, &logLength);
    std::vector<char> log(logLength > 1 ? static_cast<usize>(logLength) : 1, '\0');
    api.getShaderInfoLog(shader, logLength, nullptr, log.data());
    errorOut = std::string(log.data());
    logError("shader", "%s (%s): %s", debugName.c_str(),
             stage == GL_VERTEX_SHADER ? "vertex" : "fragment", errorOut.c_str());
    api.deleteShader(shader);
    return 0;
}

}

Shader::~Shader() {
    release();
}

Status Shader::compile(const std::string& debugName, const char* vertexSource, const char* fragmentSource) {
    release();
    debugLabel = debugName;
    GLApi& api = gl();

    std::string errorText;
    const GLuint vertexShader = compileStage(GL_VERTEX_SHADER, vertexSource, debugName, errorText);
    if (vertexShader == 0) {
        return statusError(StatusCode::ShaderFailure, debugName + " Vertex: " + errorText);
    }
    const GLuint fragmentShader = compileStage(GL_FRAGMENT_SHADER, fragmentSource, debugName, errorText);
    if (fragmentShader == 0) {
        api.deleteShader(vertexShader);
        return statusError(StatusCode::ShaderFailure, debugName + " Fragment: " + errorText);
    }

    program = api.createProgram();
    api.attachShader(program, vertexShader);
    api.attachShader(program, fragmentShader);
    api.linkProgram(program);

    GLint status = 0;
    api.getProgramiv(program, GL_LINK_STATUS, &status);
    api.deleteShader(vertexShader);
    api.deleteShader(fragmentShader);

    if (status != GL_TRUE) {
        GLint logLength = 0;
        api.getProgramiv(program, GL_INFO_LOG_LENGTH, &logLength);
        std::vector<char> log(logLength > 1 ? static_cast<usize>(logLength) : 1, '\0');
        api.getProgramInfoLog(program, logLength, nullptr, log.data());
        const std::string message = std::string(log.data());
        logError("shader", "%s Link: %s", debugName.c_str(), message.c_str());
        api.deleteProgram(program);
        program = 0;
        return statusError(StatusCode::ShaderFailure, debugName + " Link: " + message);
    }

    logInfo("shader", "%s uebersetzt", debugName.c_str());
    return statusOk();
}

void Shader::release() {
    if (program != 0) {
        gl().deleteProgram(program);
        program = 0;
    }
    uniformCache.clear();
}

void Shader::bind() const {
    gl().useProgram(program);
}

GLint Shader::uniformLocation(const char* name) {
    auto found = uniformCache.find(name);
    if (found != uniformCache.end()) return found->second;
    const GLint location = gl().getUniformLocation(program, name);
    uniformCache.emplace(name, location);
    return location;
}

void Shader::setInt(const char* name, i32 value) {
    const GLint location = uniformLocation(name);
    if (location >= 0) gl().uniform1i(location, value);
}

void Shader::setFloat(const char* name, f32 value) {
    const GLint location = uniformLocation(name);
    if (location >= 0) gl().uniform1f(location, value);
}

void Shader::setVec2(const char* name, f32 x, f32 y) {
    const GLint location = uniformLocation(name);
    if (location >= 0) gl().uniform2f(location, x, y);
}

void Shader::setVec3(const char* name, const Vec3& value) {
    const GLint location = uniformLocation(name);
    if (location >= 0) gl().uniform3f(location, value.x, value.y, value.z);
}

void Shader::setVec4(const char* name, const Vec4& value) {
    const GLint location = uniformLocation(name);
    if (location >= 0) gl().uniform4f(location, value.x, value.y, value.z, value.w);
}

void Shader::setMat4(const char* name, const Mat4& value) {
    const GLint location = uniformLocation(name);
    if (location >= 0) gl().uniformMatrix4fv(location, 1, GL_FALSE, value.m);
}

void Shader::setTextureUnit(const char* name, i32 unit) {
    setInt(name, unit);
}

}
