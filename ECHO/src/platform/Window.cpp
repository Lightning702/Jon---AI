#include "Window.h"
#include "../core/Log.h"

#include <windowsx.h>

#pragma comment(lib, "opengl32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

namespace echo {

static const char* kClassName = "EchoWindowClass";

LRESULT CALLBACK Window::wndProcStatic(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    Window* self = nullptr;
    if (msg == WM_NCCREATE) {
        CREATESTRUCTA* cs = (CREATESTRUCTA*)lp;
        self = (Window*)cs->lpCreateParams;
        SetWindowLongPtrA(hwnd, GWLP_USERDATA, (LONG_PTR)self);
        self->hwnd = hwnd;
    } else {
        self = (Window*)GetWindowLongPtrA(hwnd, GWLP_USERDATA);
    }
    if (self) return self->wndProc(hwnd, msg, wp, lp);
    return DefWindowProcA(hwnd, msg, wp, lp);
}

LRESULT Window::wndProc(HWND wnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CLOSE:
        closeRequested = true;
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    case WM_SIZE: {
        int nw = LOWORD(lp), nh = HIWORD(lp);
        if (nw != w || nh != h) wasResized = true;
        w = nw; h = nh;
        if (locked && hasFocus) clipCursorToWindow();
        return 0;
    }
    case WM_ACTIVATEAPP:
        hasFocus = wp != 0;
        if (!hasFocus) {
            in.reset();
            ClipCursor(nullptr);
        } else if (locked) {
            clipCursorToWindow();
        }
        return 0;
    case WM_SETFOCUS:
        hasFocus = true;
        if (locked) clipCursorToWindow();
        return 0;
    case WM_KILLFOCUS:
        hasFocus = false;
        in.reset();
        ClipCursor(nullptr);
        return 0;
    case WM_SYSCOMMAND:
        if ((wp & 0xFFF0) == SC_KEYMENU || (wp & 0xFFF0) == SC_SCREENSAVE || (wp & 0xFFF0) == SC_MONITORPOWER) return 0;
        break;
    case WM_KEYDOWN:
    case WM_SYSKEYDOWN:
        if (!(lp & (1 << 30))) in.onKey((int)wp, true);
        if (wp == VK_F4 && (GetKeyState(VK_MENU) & 0x8000)) closeRequested = true;
        return 0;
    case WM_KEYUP:
    case WM_SYSKEYUP:
        in.onKey((int)wp, false);
        return 0;
    case WM_CHAR:
        in.onChar((unsigned int)wp);
        return 0;
    case WM_LBUTTONDOWN: in.onMouseButton(MOUSE_LEFT, true); SetCapture(wnd); return 0;
    case WM_LBUTTONUP:   in.onMouseButton(MOUSE_LEFT, false); ReleaseCapture(); return 0;
    case WM_RBUTTONDOWN: in.onMouseButton(MOUSE_RIGHT, true); return 0;
    case WM_RBUTTONUP:   in.onMouseButton(MOUSE_RIGHT, false); return 0;
    case WM_MBUTTONDOWN: in.onMouseButton(MOUSE_MIDDLE, true); return 0;
    case WM_MBUTTONUP:   in.onMouseButton(MOUSE_MIDDLE, false); return 0;
    case WM_MOUSEWHEEL:
        in.onScroll((float)GET_WHEEL_DELTA_WPARAM(wp) / (float)WHEEL_DELTA);
        return 0;
    case WM_MOUSEMOVE:
        in.onMousePos((float)GET_X_LPARAM(lp), (float)GET_Y_LPARAM(lp));
        return 0;
    case WM_INPUT: {
        UINT size = 0;
        GetRawInputData((HRAWINPUT)lp, RID_INPUT, nullptr, &size, sizeof(RAWINPUTHEADER));
        if (size == 0 || size > 512) break;
        BYTE buf[512];
        if (GetRawInputData((HRAWINPUT)lp, RID_INPUT, buf, &size, sizeof(RAWINPUTHEADER)) != size) break;
        RAWINPUT* ri = (RAWINPUT*)buf;
        if (ri->header.dwType == RIM_TYPEMOUSE) {
            if (ri->data.mouse.usFlags & MOUSE_MOVE_ABSOLUTE) break;
            in.onMouseMoveRaw((float)ri->data.mouse.lLastX, (float)ri->data.mouse.lLastY);
        }
        break;
    }
    case WM_SETCURSOR:
        if (locked && LOWORD(lp) == HTCLIENT) {
            SetCursor(nullptr);
            return TRUE;
        }
        break;
    }
    return DefWindowProcA(wnd, msg, wp, lp);
}

bool Window::create(const WindowDesc& desc) {
    hinst = GetModuleHandleA(nullptr);
    msaaSamples = desc.msaa;

    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);

    WNDCLASSEXA wc = {};
    wc.cbSize = sizeof(wc);
    wc.style = CS_OWNDC | CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = wndProcStatic;
    wc.hInstance = hinst;
    wc.hCursor = LoadCursorA(nullptr, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    wc.lpszClassName = kClassName;
    wc.hIcon = LoadIconA(nullptr, IDI_APPLICATION);
    if (!RegisterClassExA(&wc)) {
        LOG_ERROR("RegisterClassEx failed: %lu", GetLastError());
        return false;
    }

    RECT work = { 0, 0, 1280, 720 };
    SystemParametersInfoA(SPI_GETWORKAREA, 0, &work, 0);
    int workW = work.right - work.left;
    int workH = work.bottom - work.top;

    int wantW = desc.width > 0 ? desc.width : (int)(workW * 0.86f);
    int wantH = desc.height > 0 ? desc.height : (int)(workH * 0.86f);
    wantW = std::max(640, std::min(wantW, workW));
    wantH = std::max(360, std::min(wantH, workH));

    DWORD style = WS_OVERLAPPEDWINDOW;
    RECT r = { 0, 0, wantW, wantH };
    AdjustWindowRect(&r, style, FALSE);

    int px = work.left + (workW - (r.right - r.left)) / 2;
    int py = work.top + (workH - (r.bottom - r.top)) / 2;
    if (px < work.left) px = work.left;
    if (py < work.top) py = work.top;

    hwnd = CreateWindowExA(0, kClassName, desc.title.c_str(), style,
                           px, py, r.right - r.left, r.bottom - r.top,
                           nullptr, nullptr, hinst, this);
    if (!hwnd) {
        LOG_ERROR("CreateWindowEx failed: %lu", GetLastError());
        return false;
    }

    hdc = GetDC(hwnd);
    if (!createContext()) return false;

    RAWINPUTDEVICE rid = {};
    rid.usUsagePage = 0x01;
    rid.usUsage = 0x02;
    rid.dwFlags = 0;
    rid.hwndTarget = hwnd;
    if (!RegisterRawInputDevices(&rid, 1, sizeof(rid))) LOG_WARN("Raw mouse input unavailable");

    ShowWindow(hwnd, SW_SHOW);
    UpdateWindow(hwnd);
    SetForegroundWindow(hwnd);
    SetFocus(hwnd);

    RECT cr;
    GetClientRect(hwnd, &cr);
    w = cr.right - cr.left;
    h = cr.bottom - cr.top;

    setVSync(desc.vsync);
    if (desc.fullscreen) setFullscreen(true);

    LOG_INFO("GL vendor: %s", glVendorString());
    LOG_INFO("GL renderer: %s", glRendererString());
    LOG_INFO("GL version: %s", (const char*)glGetString(GL_VERSION));
    return true;
}

bool Window::createContext() {
    PIXELFORMATDESCRIPTOR pfd = {};
    pfd.nSize = sizeof(pfd);
    pfd.nVersion = 1;
    pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    pfd.iPixelType = PFD_TYPE_RGBA;
    pfd.cColorBits = 32;
    pfd.cDepthBits = 24;
    pfd.cStencilBits = 8;

    int pf = ChoosePixelFormat(hdc, &pfd);
    if (!pf || !SetPixelFormat(hdc, pf, &pfd)) {
        LOG_ERROR("SetPixelFormat failed");
        return false;
    }

    HGLRC dummy = wglCreateContext(hdc);
    if (!dummy) {
        LOG_ERROR("wglCreateContext failed");
        return false;
    }
    wglMakeCurrent(hdc, dummy);

    if (!glLoadFunctions()) LOG_WARN("Some GL functions failed to load");

    if (echo_wglCreateContextAttribsARB) {
        const int versions[][2] = { {4,6},{4,5},{4,3},{4,1},{3,3} };
        for (auto& v : versions) {
            int attribs[] = {
                WGL_CONTEXT_MAJOR_VERSION_ARB, v[0],
                WGL_CONTEXT_MINOR_VERSION_ARB, v[1],
                WGL_CONTEXT_PROFILE_MASK_ARB, WGL_CONTEXT_CORE_PROFILE_BIT_ARB,
                0
            };
            HGLRC modern = echo_wglCreateContextAttribsARB(hdc, nullptr, attribs);
            if (modern) {
                wglMakeCurrent(nullptr, nullptr);
                wglDeleteContext(dummy);
                wglMakeCurrent(hdc, modern);
                hglrc = modern;
                glLoadFunctions();
                LOG_INFO("Created OpenGL %d.%d core context", v[0], v[1]);
                break;
            }
        }
    }
    if (!hglrc) {
        hglrc = dummy;
        LOG_WARN("Falling back to legacy GL context");
    }
    return true;
}

void Window::destroy() {
    ClipCursor(nullptr);
    if (hglrc) { wglMakeCurrent(nullptr, nullptr); wglDeleteContext(hglrc); hglrc = nullptr; }
    if (hdc && hwnd) { ReleaseDC(hwnd, hdc); hdc = nullptr; }
    if (hwnd) { DestroyWindow(hwnd); hwnd = nullptr; }
    UnregisterClassA(kClassName, hinst);
}

void Window::pollEvents() {
    in.beginFrame();
    MSG msg;
    while (PeekMessageA(&msg, nullptr, 0, 0, PM_REMOVE)) {
        if (msg.message == WM_QUIT) closeRequested = true;
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    if (locked && hasFocus) {
        RECT cr;
        GetClientRect(hwnd, &cr);
        POINT c = { (cr.right - cr.left) / 2, (cr.bottom - cr.top) / 2 };
        ClientToScreen(hwnd, &c);
        SetCursorPos(c.x, c.y);
    }
}

void Window::swapBuffers() {
    SwapBuffers(hdc);
}

void Window::clipCursorToWindow() {
    RECT cr;
    GetClientRect(hwnd, &cr);
    POINT tl = { cr.left, cr.top }, br = { cr.right, cr.bottom };
    ClientToScreen(hwnd, &tl);
    ClientToScreen(hwnd, &br);
    RECT screen = { tl.x, tl.y, br.x, br.y };
    ClipCursor(&screen);
}

void Window::setCursorLocked(bool lock) {
    if (locked == lock) return;
    locked = lock;
    if (lock) {
        while (ShowCursor(FALSE) >= 0) {}
        clipCursorToWindow();
    } else {
        ClipCursor(nullptr);
        while (ShowCursor(TRUE) < 0) {}
    }
}

void Window::setVSync(bool on) {
    vsyncOn = on;
    if (echo_wglSwapIntervalEXT) echo_wglSwapIntervalEXT(on ? 1 : 0);
}

static BOOL CALLBACK collectMonitor(HMONITOR mon, HDC, LPRECT, LPARAM data) {
    MONITORINFO mi = { sizeof(mi) };
    if (GetMonitorInfoA(mon, &mi)) ((std::vector<MONITORINFO>*)data)->push_back(mi);
    return TRUE;
}

static std::vector<MONITORINFO> enumerateMonitors() {
    std::vector<MONITORINFO> list;
    EnumDisplayMonitors(nullptr, nullptr, collectMonitor, (LPARAM)&list);
    return list;
}

int Window::monitorCount() const {
    return (int)enumerateMonitors().size();
}

void Window::setFullscreen(bool on) {
    if (isFullscreen == on) return;
    isFullscreen = on;

    HMONITOR mon = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
    MONITORINFO mi = { sizeof(mi) };
    GetMonitorInfoA(mon, &mi);

    if (on) {
        RECT wr;
        GetWindowRect(hwnd, &wr);
        windowedX = wr.left; windowedY = wr.top;
        windowedW = wr.right - wr.left; windowedH = wr.bottom - wr.top;

        SetWindowLongA(hwnd, GWL_STYLE, WS_POPUP | WS_VISIBLE);
        SetWindowPos(hwnd, HWND_TOP, mi.rcMonitor.left, mi.rcMonitor.top,
                     mi.rcMonitor.right - mi.rcMonitor.left,
                     mi.rcMonitor.bottom - mi.rcMonitor.top, SWP_FRAMECHANGED);
    } else {
        int areaW = mi.rcWork.right - mi.rcWork.left;
        int areaH = mi.rcWork.bottom - mi.rcWork.top;

        int targetW = windowedW > 0 ? windowedW : (int)(areaW * 0.86f);
        int targetH = windowedH > 0 ? windowedH : (int)(areaH * 0.86f);
        targetW = std::max(640, std::min(targetW, areaW));
        targetH = std::max(400, std::min(targetH, areaH));

        int targetX = windowedX;
        int targetY = windowedY;
        bool onScreen = targetX >= mi.rcWork.left && targetY >= mi.rcWork.top &&
                        targetX + targetW <= mi.rcWork.right && targetY + targetH <= mi.rcWork.bottom;
        if (!onScreen) {
            targetX = mi.rcWork.left + (areaW - targetW) / 2;
            targetY = mi.rcWork.top + (areaH - targetH) / 2;
        }

        SetWindowLongA(hwnd, GWL_STYLE, WS_OVERLAPPEDWINDOW | WS_VISIBLE);
        SetWindowPos(hwnd, HWND_NOTOPMOST, targetX, targetY, targetW, targetH, SWP_FRAMECHANGED);
    }

    RECT cr;
    GetClientRect(hwnd, &cr);
    w = cr.right - cr.left;
    h = cr.bottom - cr.top;
    wasResized = true;
    if (locked) clipCursorToWindow();
}

void Window::moveToNextMonitor() {
    std::vector<MONITORINFO> mons = enumerateMonitors();
    if (mons.size() < 2) return;

    RECT wr;
    GetWindowRect(hwnd, &wr);
    int cx = (wr.left + wr.right) / 2;
    int cy = (wr.top + wr.bottom) / 2;

    int current = 0;
    for (int i = 0; i < (int)mons.size(); i++) {
        const RECT& m = mons[(size_t)i].rcMonitor;
        if (cx >= m.left && cx < m.right && cy >= m.top && cy < m.bottom) { current = i; break; }
    }

    const MONITORINFO& target = mons[(size_t)((current + 1) % mons.size())];

    if (isFullscreen) {
        SetWindowPos(hwnd, HWND_TOP, target.rcMonitor.left, target.rcMonitor.top,
                     target.rcMonitor.right - target.rcMonitor.left,
                     target.rcMonitor.bottom - target.rcMonitor.top, SWP_FRAMECHANGED);
    } else {
        int areaW = target.rcWork.right - target.rcWork.left;
        int areaH = target.rcWork.bottom - target.rcWork.top;
        int newW = std::max(640, std::min((int)(wr.right - wr.left), areaW));
        int newH = std::max(400, std::min((int)(wr.bottom - wr.top), areaH));
        windowedW = newW;
        windowedH = newH;
        windowedX = target.rcWork.left + (areaW - newW) / 2;
        windowedY = target.rcWork.top + (areaH - newH) / 2;
        SetWindowPos(hwnd, HWND_NOTOPMOST, windowedX, windowedY, newW, newH, SWP_FRAMECHANGED);
    }

    RECT cr;
    GetClientRect(hwnd, &cr);
    w = cr.right - cr.left;
    h = cr.bottom - cr.top;
    wasResized = true;
    SetForegroundWindow(hwnd);
    SetFocus(hwnd);
    if (locked) clipCursorToWindow();
}

void Window::setTitle(const std::string& t) {
    SetWindowTextA(hwnd, t.c_str());
}

}
