#include "GL.h"
#include "../core/Log.h"

#define X(ret, name, args) PFN_ECHO_##name echo_##name = nullptr;
ECHO_GL_FUNCTIONS(X)
#undef X

PFN_wglCreateContextAttribsARB echo_wglCreateContextAttribsARB = nullptr;
PFN_wglChoosePixelFormatARB echo_wglChoosePixelFormatARB = nullptr;
PFN_wglSwapIntervalEXT echo_wglSwapIntervalEXT = nullptr;

namespace echo {

static HMODULE g_opengl32 = nullptr;
static bool g_aniso = false;
static float g_maxAniso = 1.0f;
static std::string g_vendor, g_renderer;

static void* loadProc(const char* name) {
    void* p = (void*)wglGetProcAddress(name);
    if (p == nullptr || p == (void*)0x1 || p == (void*)0x2 || p == (void*)0x3 || p == (void*)-1) {
        if (!g_opengl32) g_opengl32 = LoadLibraryA("opengl32.dll");
        if (g_opengl32) p = (void*)GetProcAddress(g_opengl32, name);
        else p = nullptr;
    }
    return p;
}

static bool hasExtension(const char* ext) {
    const char* s = (const char*)glGetString(GL_EXTENSIONS);
    if (!s) return false;
    return std::string(s).find(ext) != std::string::npos;
}

bool glLoadFunctions() {
    int missing = 0;
#define X(ret, name, args) \
    echo_##name = (PFN_ECHO_##name)loadProc(#name); \
    if (!echo_##name) { LOG_ERROR("GL function missing: %s", #name); missing++; }
    ECHO_GL_FUNCTIONS(X)
#undef X

    echo_wglCreateContextAttribsARB = (PFN_wglCreateContextAttribsARB)loadProc("wglCreateContextAttribsARB");
    echo_wglChoosePixelFormatARB = (PFN_wglChoosePixelFormatARB)loadProc("wglChoosePixelFormatARB");
    echo_wglSwapIntervalEXT = (PFN_wglSwapIntervalEXT)loadProc("wglSwapIntervalEXT");

    const char* v = (const char*)glGetString(GL_VENDOR);
    const char* r = (const char*)glGetString(GL_RENDERER);
    g_vendor = v ? v : "unknown";
    g_renderer = r ? r : "unknown";

    g_aniso = hasExtension("GL_EXT_texture_filter_anisotropic") || hasExtension("GL_ARB_texture_filter_anisotropic");
    if (g_aniso) {
        GLfloat m = 1.0f;
        glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY, &m);
        if (m < 1.0f) m = 1.0f;
        g_maxAniso = m;
    }
    return missing == 0;
}

bool glHasAnisotropy() { return g_aniso; }
float glMaxAnisotropy() { return g_maxAniso; }
const char* glVendorString() { return g_vendor.c_str(); }
const char* glRendererString() { return g_renderer.c_str(); }

void glCheckError(const char* tag) {
    GLenum e;
    int guard = 0;
    while ((e = glGetError()) != GL_NO_ERROR && guard++ < 16) LOG_WARN("GL error 0x%04X at %s", e, tag);
}

}
