#pragma once

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <windows.h>

#include <GL/gl.h>

#include <cstddef>

typedef char GLchar;
typedef ptrdiff_t GLsizeiptrARB2;
typedef ptrdiff_t GLintptrARB2;

#ifndef GL_ARRAY_BUFFER
#define GL_ARRAY_BUFFER 0x8892
#define GL_ELEMENT_ARRAY_BUFFER 0x8893
#define GL_STATIC_DRAW 0x88E4
#define GL_DYNAMIC_DRAW 0x88E8
#define GL_STREAM_DRAW 0x88E0
#endif

#ifndef GL_FRAGMENT_SHADER
#define GL_FRAGMENT_SHADER 0x8B30
#define GL_VERTEX_SHADER 0x8B31
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_INFO_LOG_LENGTH 0x8B84
#endif

#ifndef GL_TEXTURE0
#define GL_TEXTURE0 0x84C0
#endif

#ifndef GL_CLAMP_TO_EDGE
#define GL_CLAMP_TO_EDGE 0x812F
#endif

#ifndef GL_MULTISAMPLE
#define GL_MULTISAMPLE 0x809D
#endif

#ifndef GL_FRAMEBUFFER_SRGB
#define GL_FRAMEBUFFER_SRGB 0x8DB9
#endif

namespace fw {

using PfnGenBuffers = void(APIENTRY*)(GLsizei, GLuint*);
using PfnBindBuffer = void(APIENTRY*)(GLenum, GLuint);
using PfnBufferData = void(APIENTRY*)(GLenum, ptrdiff_t, const void*, GLenum);
using PfnBufferSubData = void(APIENTRY*)(GLenum, ptrdiff_t, ptrdiff_t, const void*);
using PfnDeleteBuffers = void(APIENTRY*)(GLsizei, const GLuint*);
using PfnGenVertexArrays = void(APIENTRY*)(GLsizei, GLuint*);
using PfnBindVertexArray = void(APIENTRY*)(GLuint);
using PfnDeleteVertexArrays = void(APIENTRY*)(GLsizei, const GLuint*);
using PfnVertexAttribPointer = void(APIENTRY*)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void*);
using PfnEnableVertexAttribArray = void(APIENTRY*)(GLuint);
using PfnCreateShader = GLuint(APIENTRY*)(GLenum);
using PfnShaderSource = void(APIENTRY*)(GLuint, GLsizei, const GLchar* const*, const GLint*);
using PfnCompileShader = void(APIENTRY*)(GLuint);
using PfnGetShaderiv = void(APIENTRY*)(GLuint, GLenum, GLint*);
using PfnGetShaderInfoLog = void(APIENTRY*)(GLuint, GLsizei, GLsizei*, GLchar*);
using PfnDeleteShader = void(APIENTRY*)(GLuint);
using PfnCreateProgram = GLuint(APIENTRY*)();
using PfnAttachShader = void(APIENTRY*)(GLuint, GLuint);
using PfnLinkProgram = void(APIENTRY*)(GLuint);
using PfnGetProgramiv = void(APIENTRY*)(GLuint, GLenum, GLint*);
using PfnGetProgramInfoLog = void(APIENTRY*)(GLuint, GLsizei, GLsizei*, GLchar*);
using PfnUseProgram = void(APIENTRY*)(GLuint);
using PfnDeleteProgram = void(APIENTRY*)(GLuint);
using PfnGetUniformLocation = GLint(APIENTRY*)(GLuint, const GLchar*);
using PfnUniform1i = void(APIENTRY*)(GLint, GLint);
using PfnUniform1f = void(APIENTRY*)(GLint, GLfloat);
using PfnUniform2f = void(APIENTRY*)(GLint, GLfloat, GLfloat);
using PfnUniform3f = void(APIENTRY*)(GLint, GLfloat, GLfloat, GLfloat);
using PfnUniform4f = void(APIENTRY*)(GLint, GLfloat, GLfloat, GLfloat, GLfloat);
using PfnUniformMatrix4fv = void(APIENTRY*)(GLint, GLsizei, GLboolean, const GLfloat*);
using PfnActiveTexture = void(APIENTRY*)(GLenum);
using PfnGenerateMipmap = void(APIENTRY*)(GLenum);

extern PfnGenBuffers glGenBuffers;
extern PfnBindBuffer glBindBuffer;
extern PfnBufferData glBufferData;
extern PfnBufferSubData glBufferSubData;
extern PfnDeleteBuffers glDeleteBuffers;
extern PfnGenVertexArrays glGenVertexArrays;
extern PfnBindVertexArray glBindVertexArray;
extern PfnDeleteVertexArrays glDeleteVertexArrays;
extern PfnVertexAttribPointer glVertexAttribPointer;
extern PfnEnableVertexAttribArray glEnableVertexAttribArray;
extern PfnCreateShader glCreateShader;
extern PfnShaderSource glShaderSource;
extern PfnCompileShader glCompileShader;
extern PfnGetShaderiv glGetShaderiv;
extern PfnGetShaderInfoLog glGetShaderInfoLog;
extern PfnDeleteShader glDeleteShader;
extern PfnCreateProgram glCreateProgram;
extern PfnAttachShader glAttachShader;
extern PfnLinkProgram glLinkProgram;
extern PfnGetProgramiv glGetProgramiv;
extern PfnGetProgramInfoLog glGetProgramInfoLog;
extern PfnUseProgram glUseProgram;
extern PfnDeleteProgram glDeleteProgram;
extern PfnGetUniformLocation glGetUniformLocation;
extern PfnUniform1i glUniform1i;
extern PfnUniform1f glUniform1f;
extern PfnUniform2f glUniform2f;
extern PfnUniform3f glUniform3f;
extern PfnUniform4f glUniform4f;
extern PfnUniformMatrix4fv glUniformMatrix4fv;
extern PfnActiveTexture glActiveTexture;
extern PfnGenerateMipmap glGenerateMipmap;

bool ladeGL();
const char* fehlendeFunktion();

}
