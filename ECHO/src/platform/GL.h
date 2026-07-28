#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <gl/GL.h>

#include "../core/Common.h"

typedef char GLchar;
typedef ptrdiff_t GLsizeiptr;
typedef ptrdiff_t GLintptr;
typedef int64_t GLint64;
typedef uint64_t GLuint64;
typedef struct __GLsync* GLsync;
typedef void (APIENTRY* GLDEBUGPROC)(GLenum source, GLenum type, GLuint id, GLenum severity, GLsizei length, const GLchar* message, const void* userParam);

#define APIENTRYP APIENTRY*

#define GL_TEXTURE0 0x84C0
#define GL_TEXTURE1 0x84C1
#define GL_TEXTURE2 0x84C2
#define GL_TEXTURE3 0x84C3
#define GL_TEXTURE4 0x84C4
#define GL_TEXTURE5 0x84C5
#define GL_TEXTURE6 0x84C6
#define GL_TEXTURE7 0x84C7
#define GL_TEXTURE8 0x84C8
#define GL_TEXTURE9 0x84C9
#define GL_TEXTURE10 0x84CA
#define GL_TEXTURE11 0x84CB
#define GL_TEXTURE12 0x84CC
#define GL_TEXTURE13 0x84CD
#define GL_TEXTURE14 0x84CE
#define GL_TEXTURE15 0x84CF

#define GL_ARRAY_BUFFER 0x8892
#define GL_ELEMENT_ARRAY_BUFFER 0x8893
#define GL_UNIFORM_BUFFER 0x8A11
#define GL_SHADER_STORAGE_BUFFER 0x90D2
#define GL_STATIC_DRAW 0x88E4
#define GL_DYNAMIC_DRAW 0x88E8
#define GL_STREAM_DRAW 0x88E0
#define GL_MAP_WRITE_BIT 0x0002
#define GL_MAP_INVALIDATE_BUFFER_BIT 0x0008
#define GL_MAP_UNSYNCHRONIZED_BIT 0x0020

#define GL_FRAGMENT_SHADER 0x8B30
#define GL_VERTEX_SHADER 0x8B31
#define GL_GEOMETRY_SHADER 0x8DD9
#define GL_COMPUTE_SHADER 0x91B9
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_INFO_LOG_LENGTH 0x8B84
#define GL_ACTIVE_UNIFORMS 0x8B86
#define GL_ACTIVE_UNIFORM_MAX_LENGTH 0x8B87

#define GL_FRAMEBUFFER 0x8D40
#define GL_READ_FRAMEBUFFER 0x8CA8
#define GL_DRAW_FRAMEBUFFER 0x8CA9
#define GL_RENDERBUFFER 0x8D41
#define GL_COLOR_ATTACHMENT0 0x8CE0
#define GL_COLOR_ATTACHMENT1 0x8CE1
#define GL_COLOR_ATTACHMENT2 0x8CE2
#define GL_COLOR_ATTACHMENT3 0x8CE3
#define GL_COLOR_ATTACHMENT4 0x8CE4
#define GL_COLOR_ATTACHMENT5 0x8CE5
#define GL_DEPTH_ATTACHMENT 0x8D00
#define GL_STENCIL_ATTACHMENT 0x8D20
#define GL_DEPTH_STENCIL_ATTACHMENT 0x821A
#define GL_FRAMEBUFFER_COMPLETE 0x8CD5
#define GL_DEPTH_COMPONENT16 0x81A5
#define GL_DEPTH_COMPONENT24 0x81A6
#define GL_DEPTH_COMPONENT32F 0x8CAC
#define GL_DEPTH24_STENCIL8 0x88F0
#define GL_DEPTH_STENCIL 0x84F9
#define GL_UNSIGNED_INT_24_8 0x84FA

#define GL_RGBA32F 0x8814
#define GL_RGB32F 0x8815
#define GL_RGBA16F 0x881A
#define GL_RGB16F 0x881B
#define GL_R11F_G11F_B10F 0x8C3A
#define GL_RGB10_A2 0x8059
#define GL_RGBA8 0x8058
#define GL_RGB8 0x8051
#define GL_SRGB8 0x8C41
#define GL_SRGB8_ALPHA8 0x8C43
#define GL_R8 0x8229
#define GL_R16F 0x822D
#define GL_R32F 0x822E
#define GL_RG8 0x822B
#define GL_RG16F 0x822F
#define GL_RG32F 0x8230
#define GL_RG 0x8227
#define GL_RED 0x1903
#define GL_HALF_FLOAT 0x140B
#define GL_UNSIGNED_INT_2_10_10_10_REV 0x8368

#define GL_TEXTURE_3D 0x806F
#define GL_TEXTURE_2D_ARRAY 0x8C1A
#define GL_TEXTURE_CUBE_MAP 0x8513
#define GL_TEXTURE_CUBE_MAP_POSITIVE_X 0x8515
#define GL_TEXTURE_CUBE_MAP_SEAMLESS 0x884F
#define GL_TEXTURE_WRAP_R 0x8072
#define GL_CLAMP_TO_EDGE 0x812F
#define GL_CLAMP_TO_BORDER 0x812D
#define GL_MIRRORED_REPEAT 0x8370
#define GL_TEXTURE_BORDER_COLOR 0x1004
#define GL_TEXTURE_MAX_ANISOTROPY 0x84FE
#define GL_MAX_TEXTURE_MAX_ANISOTROPY 0x84FF
#define GL_TEXTURE_COMPARE_MODE 0x884C
#define GL_TEXTURE_COMPARE_FUNC 0x884D
#define GL_COMPARE_REF_TO_TEXTURE 0x884E
#define GL_TEXTURE_MAX_LEVEL 0x813D
#define GL_TEXTURE_BASE_LEVEL 0x813C
#define GL_TEXTURE_LOD_BIAS 0x8501
#define GL_MAX_TEXTURE_IMAGE_UNITS 0x8872

#define GL_FUNC_ADD 0x8006
#define GL_FUNC_SUBTRACT 0x800A
#define GL_MIN 0x8007
#define GL_MAX 0x8008
#define GL_MULTISAMPLE 0x809D
#define GL_FRAMEBUFFER_SRGB 0x8DB9
#define GL_DEPTH_CLAMP 0x864F
#define GL_TEXTURE_CUBE_MAP_ARRAY 0x9009

#define GL_DEBUG_OUTPUT 0x92E0
#define GL_DEBUG_OUTPUT_SYNCHRONOUS 0x8242
#define GL_DEBUG_SEVERITY_HIGH 0x9146
#define GL_DEBUG_SEVERITY_MEDIUM 0x9147
#define GL_DEBUG_SEVERITY_LOW 0x9148
#define GL_DEBUG_SEVERITY_NOTIFICATION 0x826B

#define GL_TIME_ELAPSED 0x88BF
#define GL_QUERY_RESULT 0x8866
#define GL_QUERY_RESULT_AVAILABLE 0x8867

#define WGL_CONTEXT_MAJOR_VERSION_ARB 0x2091
#define WGL_CONTEXT_MINOR_VERSION_ARB 0x2092
#define WGL_CONTEXT_FLAGS_ARB 0x2094
#define WGL_CONTEXT_PROFILE_MASK_ARB 0x9126
#define WGL_CONTEXT_CORE_PROFILE_BIT_ARB 0x00000001
#define WGL_CONTEXT_DEBUG_BIT_ARB 0x00000001
#define WGL_DRAW_TO_WINDOW_ARB 0x2001
#define WGL_SUPPORT_OPENGL_ARB 0x2010
#define WGL_DOUBLE_BUFFER_ARB 0x2011
#define WGL_PIXEL_TYPE_ARB 0x2013
#define WGL_TYPE_RGBA_ARB 0x202B
#define WGL_COLOR_BITS_ARB 0x2014
#define WGL_DEPTH_BITS_ARB 0x2022
#define WGL_STENCIL_BITS_ARB 0x2023
#define WGL_SAMPLE_BUFFERS_ARB 0x2041
#define WGL_SAMPLES_ARB 0x2042
#define WGL_ACCELERATION_ARB 0x2003
#define WGL_FULL_ACCELERATION_ARB 0x2027

#define ECHO_GL_FUNCTIONS(X) \
    X(GLuint, glCreateShader, (GLenum)) \
    X(void, glShaderSource, (GLuint, GLsizei, const GLchar* const*, const GLint*)) \
    X(void, glCompileShader, (GLuint)) \
    X(void, glGetShaderiv, (GLuint, GLenum, GLint*)) \
    X(void, glGetShaderInfoLog, (GLuint, GLsizei, GLsizei*, GLchar*)) \
    X(void, glDeleteShader, (GLuint)) \
    X(GLuint, glCreateProgram, (void)) \
    X(void, glAttachShader, (GLuint, GLuint)) \
    X(void, glLinkProgram, (GLuint)) \
    X(void, glGetProgramiv, (GLuint, GLenum, GLint*)) \
    X(void, glGetProgramInfoLog, (GLuint, GLsizei, GLsizei*, GLchar*)) \
    X(void, glDeleteProgram, (GLuint)) \
    X(void, glUseProgram, (GLuint)) \
    X(GLint, glGetUniformLocation, (GLuint, const GLchar*)) \
    X(void, glGetActiveUniform, (GLuint, GLuint, GLsizei, GLsizei*, GLint*, GLenum*, GLchar*)) \
    X(void, glUniform1i, (GLint, GLint)) \
    X(void, glUniform1f, (GLint, GLfloat)) \
    X(void, glUniform2f, (GLint, GLfloat, GLfloat)) \
    X(void, glUniform3f, (GLint, GLfloat, GLfloat, GLfloat)) \
    X(void, glUniform4f, (GLint, GLfloat, GLfloat, GLfloat, GLfloat)) \
    X(void, glUniform1iv, (GLint, GLsizei, const GLint*)) \
    X(void, glUniform1fv, (GLint, GLsizei, const GLfloat*)) \
    X(void, glUniform2fv, (GLint, GLsizei, const GLfloat*)) \
    X(void, glUniform3fv, (GLint, GLsizei, const GLfloat*)) \
    X(void, glUniform4fv, (GLint, GLsizei, const GLfloat*)) \
    X(void, glUniformMatrix3fv, (GLint, GLsizei, GLboolean, const GLfloat*)) \
    X(void, glUniformMatrix4fv, (GLint, GLsizei, GLboolean, const GLfloat*)) \
    X(GLuint, glGetUniformBlockIndex, (GLuint, const GLchar*)) \
    X(void, glUniformBlockBinding, (GLuint, GLuint, GLuint)) \
    X(void, glBindAttribLocation, (GLuint, GLuint, const GLchar*)) \
    X(void, glGenBuffers, (GLsizei, GLuint*)) \
    X(void, glBindBuffer, (GLenum, GLuint)) \
    X(void, glBufferData, (GLenum, GLsizeiptr, const void*, GLenum)) \
    X(void, glBufferSubData, (GLenum, GLintptr, GLsizeiptr, const void*)) \
    X(void, glDeleteBuffers, (GLsizei, const GLuint*)) \
    X(void, glBindBufferBase, (GLenum, GLuint, GLuint)) \
    X(void, glBindBufferRange, (GLenum, GLuint, GLuint, GLintptr, GLsizeiptr)) \
    X(void*, glMapBufferRange, (GLenum, GLintptr, GLsizeiptr, GLbitfield)) \
    X(GLboolean, glUnmapBuffer, (GLenum)) \
    X(void, glGenVertexArrays, (GLsizei, GLuint*)) \
    X(void, glBindVertexArray, (GLuint)) \
    X(void, glDeleteVertexArrays, (GLsizei, const GLuint*)) \
    X(void, glEnableVertexAttribArray, (GLuint)) \
    X(void, glDisableVertexAttribArray, (GLuint)) \
    X(void, glVertexAttribPointer, (GLuint, GLint, GLenum, GLboolean, GLsizei, const void*)) \
    X(void, glVertexAttribIPointer, (GLuint, GLint, GLenum, GLsizei, const void*)) \
    X(void, glVertexAttribDivisor, (GLuint, GLuint)) \
    X(void, glActiveTexture, (GLenum)) \
    X(void, glGenerateMipmap, (GLenum)) \
    X(void, glTexImage3D, (GLenum, GLint, GLint, GLsizei, GLsizei, GLsizei, GLint, GLenum, GLenum, const void*)) \
    X(void, glTexSubImage3D, (GLenum, GLint, GLint, GLint, GLint, GLsizei, GLsizei, GLsizei, GLenum, GLenum, const void*)) \
    X(void, glTexStorage2D, (GLenum, GLsizei, GLenum, GLsizei, GLsizei)) \
    X(void, glTexStorage3D, (GLenum, GLsizei, GLenum, GLsizei, GLsizei, GLsizei)) \
    X(void, glGenFramebuffers, (GLsizei, GLuint*)) \
    X(void, glBindFramebuffer, (GLenum, GLuint)) \
    X(void, glDeleteFramebuffers, (GLsizei, const GLuint*)) \
    X(void, glFramebufferTexture2D, (GLenum, GLenum, GLenum, GLuint, GLint)) \
    X(void, glFramebufferTexture, (GLenum, GLenum, GLuint, GLint)) \
    X(void, glFramebufferTextureLayer, (GLenum, GLenum, GLuint, GLint, GLint)) \
    X(GLenum, glCheckFramebufferStatus, (GLenum)) \
    X(void, glDrawBuffers, (GLsizei, const GLenum*)) \
    X(void, glGenRenderbuffers, (GLsizei, GLuint*)) \
    X(void, glBindRenderbuffer, (GLenum, GLuint)) \
    X(void, glRenderbufferStorage, (GLenum, GLenum, GLsizei, GLsizei)) \
    X(void, glFramebufferRenderbuffer, (GLenum, GLenum, GLenum, GLuint)) \
    X(void, glDeleteRenderbuffers, (GLsizei, const GLuint*)) \
    X(void, glBlitFramebuffer, (GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLbitfield, GLenum)) \
    X(void, glClearBufferfv, (GLenum, GLint, const GLfloat*)) \
    X(void, glClearBufferfi, (GLenum, GLint, GLfloat, GLint)) \
    X(void, glDrawElementsInstanced, (GLenum, GLsizei, GLenum, const void*, GLsizei)) \
    X(void, glDrawArraysInstanced, (GLenum, GLint, GLsizei, GLsizei)) \
    X(void, glDrawElementsBaseVertex, (GLenum, GLsizei, GLenum, const void*, GLint)) \
    X(void, glBlendFuncSeparate, (GLenum, GLenum, GLenum, GLenum)) \
    X(void, glBlendEquation, (GLenum)) \
    X(void, glBlendEquationSeparate, (GLenum, GLenum)) \
    X(void, glDebugMessageCallback, (GLDEBUGPROC, const void*)) \
    X(void, glGenQueries, (GLsizei, GLuint*)) \
    X(void, glDeleteQueries, (GLsizei, const GLuint*)) \
    X(void, glBeginQuery, (GLenum, GLuint)) \
    X(void, glEndQuery, (GLenum)) \
    X(void, glGetQueryObjectuiv, (GLuint, GLenum, GLuint*)) \
    X(void, glGetQueryObjectui64v, (GLuint, GLenum, GLuint64*))

#define X(ret, name, args) typedef ret (APIENTRYP PFN_ECHO_##name) args; extern PFN_ECHO_##name echo_##name;
ECHO_GL_FUNCTIONS(X)
#undef X

#define glCreateShader echo_glCreateShader
#define glShaderSource echo_glShaderSource
#define glCompileShader echo_glCompileShader
#define glGetShaderiv echo_glGetShaderiv
#define glGetShaderInfoLog echo_glGetShaderInfoLog
#define glDeleteShader echo_glDeleteShader
#define glCreateProgram echo_glCreateProgram
#define glAttachShader echo_glAttachShader
#define glLinkProgram echo_glLinkProgram
#define glGetProgramiv echo_glGetProgramiv
#define glGetProgramInfoLog echo_glGetProgramInfoLog
#define glDeleteProgram echo_glDeleteProgram
#define glUseProgram echo_glUseProgram
#define glGetUniformLocation echo_glGetUniformLocation
#define glGetActiveUniform echo_glGetActiveUniform
#define glUniform1i echo_glUniform1i
#define glUniform1f echo_glUniform1f
#define glUniform2f echo_glUniform2f
#define glUniform3f echo_glUniform3f
#define glUniform4f echo_glUniform4f
#define glUniform1iv echo_glUniform1iv
#define glUniform1fv echo_glUniform1fv
#define glUniform2fv echo_glUniform2fv
#define glUniform3fv echo_glUniform3fv
#define glUniform4fv echo_glUniform4fv
#define glUniformMatrix3fv echo_glUniformMatrix3fv
#define glUniformMatrix4fv echo_glUniformMatrix4fv
#define glGetUniformBlockIndex echo_glGetUniformBlockIndex
#define glUniformBlockBinding echo_glUniformBlockBinding
#define glBindAttribLocation echo_glBindAttribLocation
#define glGenBuffers echo_glGenBuffers
#define glBindBuffer echo_glBindBuffer
#define glBufferData echo_glBufferData
#define glBufferSubData echo_glBufferSubData
#define glDeleteBuffers echo_glDeleteBuffers
#define glBindBufferBase echo_glBindBufferBase
#define glBindBufferRange echo_glBindBufferRange
#define glMapBufferRange echo_glMapBufferRange
#define glUnmapBuffer echo_glUnmapBuffer
#define glGenVertexArrays echo_glGenVertexArrays
#define glBindVertexArray echo_glBindVertexArray
#define glDeleteVertexArrays echo_glDeleteVertexArrays
#define glEnableVertexAttribArray echo_glEnableVertexAttribArray
#define glDisableVertexAttribArray echo_glDisableVertexAttribArray
#define glVertexAttribPointer echo_glVertexAttribPointer
#define glVertexAttribIPointer echo_glVertexAttribIPointer
#define glVertexAttribDivisor echo_glVertexAttribDivisor
#define glActiveTexture echo_glActiveTexture
#define glGenerateMipmap echo_glGenerateMipmap
#define glTexImage3D echo_glTexImage3D
#define glTexSubImage3D echo_glTexSubImage3D
#define glTexStorage2D echo_glTexStorage2D
#define glTexStorage3D echo_glTexStorage3D
#define glGenFramebuffers echo_glGenFramebuffers
#define glBindFramebuffer echo_glBindFramebuffer
#define glDeleteFramebuffers echo_glDeleteFramebuffers
#define glFramebufferTexture2D echo_glFramebufferTexture2D
#define glFramebufferTexture echo_glFramebufferTexture
#define glFramebufferTextureLayer echo_glFramebufferTextureLayer
#define glCheckFramebufferStatus echo_glCheckFramebufferStatus
#define glDrawBuffers echo_glDrawBuffers
#define glGenRenderbuffers echo_glGenRenderbuffers
#define glBindRenderbuffer echo_glBindRenderbuffer
#define glRenderbufferStorage echo_glRenderbufferStorage
#define glFramebufferRenderbuffer echo_glFramebufferRenderbuffer
#define glDeleteRenderbuffers echo_glDeleteRenderbuffers
#define glBlitFramebuffer echo_glBlitFramebuffer
#define glClearBufferfv echo_glClearBufferfv
#define glClearBufferfi echo_glClearBufferfi
#define glDrawElementsInstanced echo_glDrawElementsInstanced
#define glDrawArraysInstanced echo_glDrawArraysInstanced
#define glDrawElementsBaseVertex echo_glDrawElementsBaseVertex
#define glBlendFuncSeparate echo_glBlendFuncSeparate
#define glBlendEquation echo_glBlendEquation
#define glBlendEquationSeparate echo_glBlendEquationSeparate
#define glDebugMessageCallback echo_glDebugMessageCallback
#define glGenQueries echo_glGenQueries
#define glDeleteQueries echo_glDeleteQueries
#define glBeginQuery echo_glBeginQuery
#define glEndQuery echo_glEndQuery
#define glGetQueryObjectuiv echo_glGetQueryObjectuiv
#define glGetQueryObjectui64v echo_glGetQueryObjectui64v

typedef HGLRC(WINAPI* PFN_wglCreateContextAttribsARB)(HDC, HGLRC, const int*);
typedef BOOL(WINAPI* PFN_wglChoosePixelFormatARB)(HDC, const int*, const FLOAT*, UINT, int*, UINT*);
typedef BOOL(WINAPI* PFN_wglSwapIntervalEXT)(int);
extern PFN_wglCreateContextAttribsARB echo_wglCreateContextAttribsARB;
extern PFN_wglChoosePixelFormatARB echo_wglChoosePixelFormatARB;
extern PFN_wglSwapIntervalEXT echo_wglSwapIntervalEXT;

namespace echo {
bool glLoadFunctions();
bool glHasAnisotropy();
float glMaxAnisotropy();
const char* glVendorString();
const char* glRendererString();
void glCheckError(const char* tag);
}
