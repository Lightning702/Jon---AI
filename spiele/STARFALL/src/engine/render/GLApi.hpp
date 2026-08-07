#pragma once

#include "../core/Types.hpp"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <GL/gl.h>

#include <cstddef>

namespace sf {

using GLchar = char;
using GLsizeiptr = std::ptrdiff_t;
using GLintptr = std::ptrdiff_t;

}

#define GL_ARRAY_BUFFER 0x8892
#define GL_ELEMENT_ARRAY_BUFFER 0x8893
#define GL_UNIFORM_BUFFER 0x8A11
#define GL_SHADER_STORAGE_BUFFER 0x90D2
#define GL_STATIC_DRAW 0x88E4
#define GL_DYNAMIC_DRAW 0x88E8
#define GL_STREAM_DRAW 0x88E0
#define GL_FRAGMENT_SHADER 0x8B30
#define GL_VERTEX_SHADER 0x8B31
#define GL_GEOMETRY_SHADER 0x8DD9
#define GL_COMPUTE_SHADER 0x91B9
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_INFO_LOG_LENGTH 0x8B84
#define GL_TEXTURE0 0x84C0
#define GL_TEXTURE_3D 0x806F
#define GL_TEXTURE_CUBE_MAP 0x8513
#define GL_TEXTURE_WRAP_R 0x8072
#define GL_CLAMP_TO_EDGE 0x812F
#define GL_MIRRORED_REPEAT 0x8370
#define GL_TEXTURE_MAX_ANISOTROPY 0x84FE
#define GL_FRAMEBUFFER 0x8D40
#define GL_READ_FRAMEBUFFER 0x8CA8
#define GL_DRAW_FRAMEBUFFER 0x8CA9
#define GL_RENDERBUFFER 0x8D41
#define GL_COLOR_ATTACHMENT0 0x8CE0
#define GL_COLOR_ATTACHMENT1 0x8CE1
#define GL_COLOR_ATTACHMENT2 0x8CE2
#define GL_COLOR_ATTACHMENT3 0x8CE3
#define GL_DEPTH_ATTACHMENT 0x8D00
#define GL_DEPTH_STENCIL_ATTACHMENT 0x821A
#define GL_DEPTH24_STENCIL8 0x88F0
#define GL_DEPTH_COMPONENT24 0x81A6
#define GL_DEPTH_COMPONENT32F 0x8CAC
#define GL_FRAMEBUFFER_COMPLETE 0x8CD5
#define GL_RGBA16F 0x881A
#define GL_RGBA32F 0x8814
#define GL_RGB16F 0x881B
#define GL_RG16F 0x822F
#define GL_R16F 0x822D
#define GL_R32F 0x822E
#define GL_RG32F 0x8230
#define GL_RGB32F 0x8815
#define GL_R8 0x8229
#define GL_RG8 0x822B
#define GL_RGBA8 0x8058
#define GL_SRGB8_ALPHA8 0x8C43
#define GL_RG 0x8227
#define GL_RED 0x1903
#define GL_HALF_FLOAT 0x140B
#define GL_MULTISAMPLE 0x809D
#define GL_TEXTURE_MAX_LEVEL 0x813D
#define GL_TEXTURE_BASE_LEVEL 0x813C
#define GL_MAJOR_VERSION 0x821B
#define GL_MINOR_VERSION 0x821C
#define GL_NUM_EXTENSIONS 0x821D
#define GL_SHADING_LANGUAGE_VERSION 0x8B8C
#define GL_FUNC_ADD 0x8006
#define GL_MAX_TEXTURE_MAX_ANISOTROPY 0x84FF
#define GL_DEBUG_OUTPUT 0x92E0
#define GL_DEBUG_OUTPUT_SYNCHRONOUS 0x8242
#define GL_TEXTURE_COMPARE_MODE 0x884C
#define GL_TEXTURE_COMPARE_FUNC 0x884D
#define GL_COMPARE_REF_TO_TEXTURE 0x884E
#define GL_CLIP_DISTANCE0 0x3000
#define GL_PROGRAM_POINT_SIZE 0x8642
#define GL_FRAMEBUFFER_SRGB 0x8DB9
#define GL_CONSTANT_COLOR 0x8001
#define GL_ONE_MINUS_CONSTANT_COLOR 0x8002
#define GL_CONSTANT_ALPHA 0x8003
#define GL_ONE_MINUS_CONSTANT_ALPHA 0x8004

namespace sf {

using PFN_glGenBuffers = void(APIENTRY*)(GLsizei, GLuint*);
using PFN_glDeleteBuffers = void(APIENTRY*)(GLsizei, const GLuint*);
using PFN_glBindBuffer = void(APIENTRY*)(GLenum, GLuint);
using PFN_glBufferData = void(APIENTRY*)(GLenum, GLsizeiptr, const void*, GLenum);
using PFN_glBufferSubData = void(APIENTRY*)(GLenum, GLintptr, GLsizeiptr, const void*);
using PFN_glBindBufferBase = void(APIENTRY*)(GLenum, GLuint, GLuint);
using PFN_glGenVertexArrays = void(APIENTRY*)(GLsizei, GLuint*);
using PFN_glDeleteVertexArrays = void(APIENTRY*)(GLsizei, const GLuint*);
using PFN_glBindVertexArray = void(APIENTRY*)(GLuint);
using PFN_glEnableVertexAttribArray = void(APIENTRY*)(GLuint);
using PFN_glVertexAttribPointer = void(APIENTRY*)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void*);
using PFN_glVertexAttribIPointer = void(APIENTRY*)(GLuint, GLint, GLenum, GLsizei, const void*);
using PFN_glVertexAttribDivisor = void(APIENTRY*)(GLuint, GLuint);
using PFN_glCreateShader = GLuint(APIENTRY*)(GLenum);
using PFN_glDeleteShader = void(APIENTRY*)(GLuint);
using PFN_glShaderSource = void(APIENTRY*)(GLuint, GLsizei, const GLchar* const*, const GLint*);
using PFN_glCompileShader = void(APIENTRY*)(GLuint);
using PFN_glGetShaderiv = void(APIENTRY*)(GLuint, GLenum, GLint*);
using PFN_glGetShaderInfoLog = void(APIENTRY*)(GLuint, GLsizei, GLsizei*, GLchar*);
using PFN_glCreateProgram = GLuint(APIENTRY*)(void);
using PFN_glDeleteProgram = void(APIENTRY*)(GLuint);
using PFN_glAttachShader = void(APIENTRY*)(GLuint, GLuint);
using PFN_glLinkProgram = void(APIENTRY*)(GLuint);
using PFN_glGetProgramiv = void(APIENTRY*)(GLuint, GLenum, GLint*);
using PFN_glGetProgramInfoLog = void(APIENTRY*)(GLuint, GLsizei, GLsizei*, GLchar*);
using PFN_glUseProgram = void(APIENTRY*)(GLuint);
using PFN_glGetUniformLocation = GLint(APIENTRY*)(GLuint, const GLchar*);
using PFN_glUniform1i = void(APIENTRY*)(GLint, GLint);
using PFN_glUniform1ui = void(APIENTRY*)(GLint, GLuint);
using PFN_glUniform1f = void(APIENTRY*)(GLint, GLfloat);
using PFN_glUniform2f = void(APIENTRY*)(GLint, GLfloat, GLfloat);
using PFN_glUniform3f = void(APIENTRY*)(GLint, GLfloat, GLfloat, GLfloat);
using PFN_glUniform4f = void(APIENTRY*)(GLint, GLfloat, GLfloat, GLfloat, GLfloat);
using PFN_glUniform1fv = void(APIENTRY*)(GLint, GLsizei, const GLfloat*);
using PFN_glUniform3fv = void(APIENTRY*)(GLint, GLsizei, const GLfloat*);
using PFN_glUniform4fv = void(APIENTRY*)(GLint, GLsizei, const GLfloat*);
using PFN_glUniformMatrix4fv = void(APIENTRY*)(GLint, GLsizei, GLboolean, const GLfloat*);
using PFN_glUniformMatrix3fv = void(APIENTRY*)(GLint, GLsizei, GLboolean, const GLfloat*);
using PFN_glActiveTexture = void(APIENTRY*)(GLenum);
using PFN_glGenerateMipmap = void(APIENTRY*)(GLenum);
using PFN_glTexImage3D = void(APIENTRY*)(GLenum, GLint, GLint, GLsizei, GLsizei, GLsizei, GLint, GLenum, GLenum, const void*);
using PFN_glGenFramebuffers = void(APIENTRY*)(GLsizei, GLuint*);
using PFN_glDeleteFramebuffers = void(APIENTRY*)(GLsizei, const GLuint*);
using PFN_glBindFramebuffer = void(APIENTRY*)(GLenum, GLuint);
using PFN_glFramebufferTexture2D = void(APIENTRY*)(GLenum, GLenum, GLenum, GLuint, GLint);
using PFN_glCheckFramebufferStatus = GLenum(APIENTRY*)(GLenum);
using PFN_glGenRenderbuffers = void(APIENTRY*)(GLsizei, GLuint*);
using PFN_glDeleteRenderbuffers = void(APIENTRY*)(GLsizei, const GLuint*);
using PFN_glBindRenderbuffer = void(APIENTRY*)(GLenum, GLuint);
using PFN_glRenderbufferStorage = void(APIENTRY*)(GLenum, GLenum, GLsizei, GLsizei);
using PFN_glFramebufferRenderbuffer = void(APIENTRY*)(GLenum, GLenum, GLenum, GLuint);
using PFN_glDrawBuffers = void(APIENTRY*)(GLsizei, const GLenum*);
using PFN_glBlitFramebuffer = void(APIENTRY*)(GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLbitfield, GLenum);
using PFN_glDrawArraysInstanced = void(APIENTRY*)(GLenum, GLint, GLsizei, GLsizei);
using PFN_glDrawElementsInstanced = void(APIENTRY*)(GLenum, GLsizei, GLenum, const void*, GLsizei);
using PFN_glBlendFuncSeparate = void(APIENTRY*)(GLenum, GLenum, GLenum, GLenum);
using PFN_glBlendEquation = void(APIENTRY*)(GLenum);
using PFN_glBlendColor = void(APIENTRY*)(GLfloat, GLfloat, GLfloat, GLfloat);
using PFN_glGetStringi = const GLubyte*(APIENTRY*)(GLenum, GLuint);
using PFN_glDispatchCompute = void(APIENTRY*)(GLuint, GLuint, GLuint);
using PFN_glMemoryBarrier = void(APIENTRY*)(GLbitfield);

struct GLApi {
    PFN_glGenBuffers genBuffers = nullptr;
    PFN_glDeleteBuffers deleteBuffers = nullptr;
    PFN_glBindBuffer bindBuffer = nullptr;
    PFN_glBufferData bufferData = nullptr;
    PFN_glBufferSubData bufferSubData = nullptr;
    PFN_glBindBufferBase bindBufferBase = nullptr;
    PFN_glGenVertexArrays genVertexArrays = nullptr;
    PFN_glDeleteVertexArrays deleteVertexArrays = nullptr;
    PFN_glBindVertexArray bindVertexArray = nullptr;
    PFN_glEnableVertexAttribArray enableVertexAttribArray = nullptr;
    PFN_glVertexAttribPointer vertexAttribPointer = nullptr;
    PFN_glVertexAttribIPointer vertexAttribIPointer = nullptr;
    PFN_glVertexAttribDivisor vertexAttribDivisor = nullptr;
    PFN_glCreateShader createShader = nullptr;
    PFN_glDeleteShader deleteShader = nullptr;
    PFN_glShaderSource shaderSource = nullptr;
    PFN_glCompileShader compileShader = nullptr;
    PFN_glGetShaderiv getShaderiv = nullptr;
    PFN_glGetShaderInfoLog getShaderInfoLog = nullptr;
    PFN_glCreateProgram createProgram = nullptr;
    PFN_glDeleteProgram deleteProgram = nullptr;
    PFN_glAttachShader attachShader = nullptr;
    PFN_glLinkProgram linkProgram = nullptr;
    PFN_glGetProgramiv getProgramiv = nullptr;
    PFN_glGetProgramInfoLog getProgramInfoLog = nullptr;
    PFN_glUseProgram useProgram = nullptr;
    PFN_glGetUniformLocation getUniformLocation = nullptr;
    PFN_glUniform1i uniform1i = nullptr;
    PFN_glUniform1ui uniform1ui = nullptr;
    PFN_glUniform1f uniform1f = nullptr;
    PFN_glUniform2f uniform2f = nullptr;
    PFN_glUniform3f uniform3f = nullptr;
    PFN_glUniform4f uniform4f = nullptr;
    PFN_glUniform1fv uniform1fv = nullptr;
    PFN_glUniform3fv uniform3fv = nullptr;
    PFN_glUniform4fv uniform4fv = nullptr;
    PFN_glUniformMatrix4fv uniformMatrix4fv = nullptr;
    PFN_glUniformMatrix3fv uniformMatrix3fv = nullptr;
    PFN_glActiveTexture activeTexture = nullptr;
    PFN_glGenerateMipmap generateMipmap = nullptr;
    PFN_glTexImage3D texImage3D = nullptr;
    PFN_glGenFramebuffers genFramebuffers = nullptr;
    PFN_glDeleteFramebuffers deleteFramebuffers = nullptr;
    PFN_glBindFramebuffer bindFramebuffer = nullptr;
    PFN_glFramebufferTexture2D framebufferTexture2D = nullptr;
    PFN_glCheckFramebufferStatus checkFramebufferStatus = nullptr;
    PFN_glGenRenderbuffers genRenderbuffers = nullptr;
    PFN_glDeleteRenderbuffers deleteRenderbuffers = nullptr;
    PFN_glBindRenderbuffer bindRenderbuffer = nullptr;
    PFN_glRenderbufferStorage renderbufferStorage = nullptr;
    PFN_glFramebufferRenderbuffer framebufferRenderbuffer = nullptr;
    PFN_glDrawBuffers drawBuffers = nullptr;
    PFN_glBlitFramebuffer blitFramebuffer = nullptr;
    PFN_glDrawArraysInstanced drawArraysInstanced = nullptr;
    PFN_glDrawElementsInstanced drawElementsInstanced = nullptr;
    PFN_glBlendFuncSeparate blendFuncSeparate = nullptr;
    PFN_glBlendEquation blendEquation = nullptr;
    PFN_glBlendColor blendColor = nullptr;
    PFN_glGetStringi getStringi = nullptr;
    PFN_glDispatchCompute dispatchCompute = nullptr;
    PFN_glMemoryBarrier memoryBarrier = nullptr;
    bool loaded = false;
    i32 majorVersion = 0;
    i32 minorVersion = 0;
    char rendererName[128] = {};
    char vendorName[128] = {};
};

GLApi& gl();
bool loadGLApi();

}
