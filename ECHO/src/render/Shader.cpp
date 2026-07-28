#include "Shader.h"
#include "../core/FileSystem.h"
#include "../core/Log.h"

namespace echo {

std::string Shader::preprocess(const std::string& src, const std::string& dir, int depth) {
    if (depth > 8) return src;
    std::string out;
    out.reserve(src.size() + 1024);
    size_t pos = 0;
    while (pos < src.size()) {
        size_t eol = src.find('\n', pos);
        if (eol == std::string::npos) eol = src.size();
        std::string line = src.substr(pos, eol - pos);

        size_t nonSpace = line.find_first_not_of(" \t");
        bool isInclude = false;
        if (nonSpace != std::string::npos && line.compare(nonSpace, 8, "#include") == 0) {
            size_t q1 = line.find('"', nonSpace);
            size_t q2 = q1 == std::string::npos ? std::string::npos : line.find('"', q1 + 1);
            if (q1 != std::string::npos && q2 != std::string::npos) {
                std::string incName = line.substr(q1 + 1, q2 - q1 - 1);
                std::string incSrc;
                if (fs::readText(dir + "/" + incName, incSrc)) {
                    out += preprocess(incSrc, dir, depth + 1);
                    out += "\n";
                    isInclude = true;
                } else {
                    LOG_WARN("Shader include not found: %s", incName.c_str());
                }
            }
        }
        if (!isInclude) {
            out += line;
            out += "\n";
        }
        pos = eol + 1;
    }
    return out;
}

GLuint Shader::compile(GLenum type, const std::string& src, const std::string& tag) {
    GLuint s = glCreateShader(type);
    const char* p = src.c_str();
    GLint len = (GLint)src.size();
    glShaderSource(s, 1, &p, &len);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        GLint logLen = 0;
        glGetShaderiv(s, GL_INFO_LOG_LENGTH, &logLen);
        std::string log((size_t)std::max(logLen, 1), '\0');
        glGetShaderInfoLog(s, logLen, nullptr, log.data());
        const char* kind = type == GL_VERTEX_SHADER ? "vertex" : (type == GL_FRAGMENT_SHADER ? "fragment" : "geometry");
        LOG_ERROR("Shader compile failed [%s %s]:\n%s", tag.c_str(), kind, log.c_str());
        glDeleteShader(s);
        return 0;
    }
    return s;
}

bool Shader::loadFromSource(const std::string& vs, const std::string& fs, const std::string& tag) {
    GLuint v = compile(GL_VERTEX_SHADER, vs, tag);
    if (!v) return false;
    GLuint f = compile(GL_FRAGMENT_SHADER, fs, tag);
    if (!f) { glDeleteShader(v); return false; }

    GLuint p = glCreateProgram();
    glAttachShader(p, v);
    glAttachShader(p, f);
    glLinkProgram(p);
    glDeleteShader(v);
    glDeleteShader(f);

    GLint ok = 0;
    glGetProgramiv(p, GL_LINK_STATUS, &ok);
    if (!ok) {
        GLint logLen = 0;
        glGetProgramiv(p, GL_INFO_LOG_LENGTH, &logLen);
        std::string log((size_t)std::max(logLen, 1), '\0');
        glGetProgramInfoLog(p, logLen, nullptr, log.data());
        LOG_ERROR("Shader link failed [%s]:\n%s", tag.c_str(), log.c_str());
        glDeleteProgram(p);
        return false;
    }

    destroy();
    program = p;
    tagName = tag;
    uniforms.clear();
    return true;
}

bool Shader::loadFromFiles(const std::string& vsPath, const std::string& fsPath, const std::string& defines) {
    vsFile = vsPath;
    fsFile = fsPath;
    defineBlock = defines;

    std::string vsSrc, fsSrc;
    if (!fs::readText(vsPath, vsSrc)) { LOG_ERROR("Missing shader file: %s", vsPath.c_str()); return false; }
    if (!fs::readText(fsPath, fsSrc)) { LOG_ERROR("Missing shader file: %s", fsPath.c_str()); return false; }

    std::string dir = fs::parentPath(vsPath);
    vsSrc = preprocess(vsSrc, dir, 0);
    fsSrc = preprocess(fsSrc, fs::parentPath(fsPath), 0);

    if (!defines.empty()) {
        auto inject = [&](std::string& s) {
            size_t v = s.find("#version");
            size_t eol = v == std::string::npos ? 0 : s.find('\n', v) + 1;
            s.insert(eol, defines + "\n");
        };
        inject(vsSrc);
        inject(fsSrc);
    }

    size_t slash = fsPath.find_last_of("/\\");
    std::string tag = slash == std::string::npos ? fsPath : fsPath.substr(slash + 1);
    return loadFromSource(vsSrc, fsSrc, tag);
}

bool Shader::reload() {
    if (vsFile.empty() || fsFile.empty()) return false;
    return loadFromFiles(vsFile, fsFile, defineBlock);
}

void Shader::destroy() {
    if (program) { glDeleteProgram(program); program = 0; }
    uniforms.clear();
}

void Shader::bind() const {
    glUseProgram(program);
}

GLint Shader::location(const char* n) {
    auto it = uniforms.find(n);
    if (it != uniforms.end()) return it->second;
    GLint loc = glGetUniformLocation(program, n);
    uniforms.emplace(n, loc);
    return loc;
}

void Shader::setInt(const char* n, int v) { GLint l = location(n); if (l >= 0) glUniform1i(l, v); }
void Shader::setFloat(const char* n, float v) { GLint l = location(n); if (l >= 0) glUniform1f(l, v); }
void Shader::setVec2(const char* n, const em::Vec2& v) { GLint l = location(n); if (l >= 0) glUniform2f(l, v.x, v.y); }
void Shader::setVec3(const char* n, const em::Vec3& v) { GLint l = location(n); if (l >= 0) glUniform3f(l, v.x, v.y, v.z); }
void Shader::setVec4(const char* n, const em::Vec4& v) { GLint l = location(n); if (l >= 0) glUniform4f(l, v.x, v.y, v.z, v.w); }
void Shader::setMat3(const char* n, const em::Mat3& v) { GLint l = location(n); if (l >= 0) glUniformMatrix3fv(l, 1, GL_FALSE, v.m); }
void Shader::setMat4(const char* n, const em::Mat4& v) { GLint l = location(n); if (l >= 0) glUniformMatrix4fv(l, 1, GL_FALSE, v.m); }
void Shader::setFloatArray(const char* n, const float* v, int c) { GLint l = location(n); if (l >= 0) glUniform1fv(l, c, v); }
void Shader::setVec3Array(const char* n, const float* v, int c) { GLint l = location(n); if (l >= 0) glUniform3fv(l, c, v); }
void Shader::setVec4Array(const char* n, const float* v, int c) { GLint l = location(n); if (l >= 0) glUniform4fv(l, c, v); }
void Shader::setIntArray(const char* n, const int* v, int c) { GLint l = location(n); if (l >= 0) glUniform1iv(l, c, v); }

void Shader::setTexture(const char* n, int unit, GLuint tex, GLenum target) {
    GLint l = location(n);
    if (l < 0) return;
    glActiveTexture(GL_TEXTURE0 + unit);
    glBindTexture(target, tex);
    glUniform1i(l, unit);
}

}
