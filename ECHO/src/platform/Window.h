#pragma once

#include "GL.h"
#include "Input.h"

namespace echo {

struct WindowDesc {
    int width = 0;
    int height = 0;
    bool fullscreen = true;
    bool vsync = true;
    int msaa = 0;
    std::string title = ECHO_TITLE;
};

class Window {
public:
    bool create(const WindowDesc& desc);
    void destroy();

    void pollEvents();
    void swapBuffers();
    bool shouldClose() const { return closeRequested; }
    void requestClose() { closeRequested = true; }

    void setCursorLocked(bool locked);
    bool cursorLocked() const { return locked; }
    void setVSync(bool on);
    bool vsync() const { return vsyncOn; }
    void setFullscreen(bool on);
    bool fullscreen() const { return isFullscreen; }
    void toggleFullscreen() { setFullscreen(!isFullscreen); }
    void moveToNextMonitor();
    int monitorCount() const;
    void setTitle(const std::string& t);

    int width() const { return w; }
    int height() const { return h; }
    float aspect() const { return h > 0 ? (float)w / (float)h : 1.0f; }
    bool focused() const { return hasFocus; }
    bool minimized() const { return w <= 0 || h <= 0; }
    bool resized() const {
        bool changed = wasResized;
        wasResized = false;
        return changed;
    }

    Input& input() { return in; }
    HWND handle() const { return hwnd; }

private:
    static LRESULT CALLBACK wndProcStatic(HWND, UINT, WPARAM, LPARAM);
    LRESULT wndProc(HWND, UINT, WPARAM, LPARAM);
    bool createContext();
    void clipCursorToWindow();

    HWND hwnd = nullptr;
    HDC hdc = nullptr;
    HGLRC hglrc = nullptr;
    HINSTANCE hinst = nullptr;
    int w = 0, h = 0;
    int windowedX = 0, windowedY = 0, windowedW = 0, windowedH = 0;
    bool closeRequested = false;
    bool locked = false;
    bool vsyncOn = true;
    bool isFullscreen = false;
    bool hasFocus = true;
    mutable bool wasResized = false;
    int msaaSamples = 0;
    Input in;
};

}
