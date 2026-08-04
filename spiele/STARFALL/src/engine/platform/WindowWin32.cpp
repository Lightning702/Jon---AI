#include "Window.hpp"

#include "../core/Log.hpp"
#include "../render/GLApi.hpp"

#include <windowsx.h>

namespace sf {
namespace {

constexpr const char* kWindowClassName = "StarfallWindowClass";

using PFN_wglCreateContextAttribsARB = HGLRC(WINAPI*)(HDC, HGLRC, const int*);
using PFN_wglSwapIntervalEXT = BOOL(WINAPI*)(int);

PFN_wglSwapIntervalEXT wglSwapIntervalExtension = nullptr;

constexpr int kContextMajorVersion = 0x2091;
constexpr int kContextMinorVersion = 0x2092;
constexpr int kContextProfileMask = 0x9126;
constexpr int kContextCoreProfileBit = 0x00000001;
constexpr int kContextFlags = 0x2094;
constexpr int kContextDebugBit = 0x00000001;

LRESULT CALLBACK windowProcedure(HWND handle, UINT message, WPARAM wparam, LPARAM lparam);

}

Window::~Window() {
    close();
}

Status Window::open(const WindowSettings& settings) {
    instanceHandle = GetModuleHandleA(nullptr);

    WNDCLASSEXA windowClass = {};
    windowClass.cbSize = sizeof(WNDCLASSEXA);
    windowClass.style = CS_OWNDC | CS_HREDRAW | CS_VREDRAW;
    windowClass.lpfnWndProc = windowProcedure;
    windowClass.hInstance = static_cast<HINSTANCE>(instanceHandle);
    windowClass.hCursor = LoadCursor(nullptr, IDC_ARROW);
    windowClass.hbrBackground = reinterpret_cast<HBRUSH>(GetStockObject(BLACK_BRUSH));
    windowClass.lpszClassName = kWindowClassName;
    RegisterClassExA(&windowClass);

    RECT desired = {0, 0, static_cast<LONG>(settings.width), static_cast<LONG>(settings.height)};
    const DWORD style = WS_OVERLAPPEDWINDOW;
    AdjustWindowRect(&desired, style, FALSE);

    HWND handle = CreateWindowExA(0, kWindowClassName, settings.title.c_str(), style, CW_USEDEFAULT, CW_USEDEFAULT,
                                  desired.right - desired.left, desired.bottom - desired.top, nullptr, nullptr,
                                  static_cast<HINSTANCE>(instanceHandle), this);
    if (!handle) {
        return statusError(StatusCode::DeviceFailure, "Fenster konnte nicht erstellt werden");
    }
    windowHandle = handle;
    SetWindowLongPtrA(handle, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(this));

    HDC device = GetDC(handle);
    deviceContext = device;

    PIXELFORMATDESCRIPTOR descriptor = {};
    descriptor.nSize = sizeof(PIXELFORMATDESCRIPTOR);
    descriptor.nVersion = 1;
    descriptor.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    descriptor.iPixelType = PFD_TYPE_RGBA;
    descriptor.cColorBits = 32;
    descriptor.cDepthBits = 24;
    descriptor.cStencilBits = 8;

    int pixelFormat = ChoosePixelFormat(device, &descriptor);
    if (pixelFormat == 0 || !SetPixelFormat(device, pixelFormat, &descriptor)) {
        return statusError(StatusCode::DeviceFailure, "Kein passendes Pixelformat gefunden");
    }

    HGLRC legacyContext = wglCreateContext(device);
    if (!legacyContext) {
        return statusError(StatusCode::DeviceFailure, "OpenGL-Kontext konnte nicht erstellt werden");
    }
    wglMakeCurrent(device, legacyContext);

    auto createContextAttribs =
        reinterpret_cast<PFN_wglCreateContextAttribsARB>(wglGetProcAddress("wglCreateContextAttribsARB"));
    wglSwapIntervalExtension = reinterpret_cast<PFN_wglSwapIntervalEXT>(wglGetProcAddress("wglSwapIntervalEXT"));

    HGLRC modernContext = nullptr;
    if (createContextAttribs) {
        const int versionPairs[][2] = {{4, 6}, {4, 5}, {4, 3}, {4, 1}, {3, 3}};
        for (const int* pair : versionPairs) {
            int attributes[] = {kContextMajorVersion, pair[0],
                                kContextMinorVersion, pair[1],
                                kContextProfileMask, kContextCoreProfileBit,
                                kContextFlags, settings.debugContext ? kContextDebugBit : 0,
                                0};
            modernContext = createContextAttribs(device, nullptr, attributes);
            if (modernContext) break;
        }
    }

    if (modernContext) {
        wglMakeCurrent(device, modernContext);
        wglDeleteContext(legacyContext);
        renderContext = modernContext;
    } else {
        renderContext = legacyContext;
        logWarning("window", "Kein moderner Kontext verfuegbar, nutze Kompatibilitaetskontext");
    }

    if (!loadGLApi()) {
        return statusError(StatusCode::DeviceFailure,
                           "Der Grafiktreiber unterstuetzt die benoetigten OpenGL-Funktionen nicht");
    }

    RECT client;
    GetClientRect(handle, &client);
    currentWidth = static_cast<u32>(client.right - client.left);
    currentHeight = static_cast<u32>(client.bottom - client.top);
    windowedWidth = currentWidth;
    windowedHeight = currentHeight;

    ShowWindow(handle, SW_SHOW);
    UpdateWindow(handle);
    setVerticalSync(settings.verticalSync);
    if (settings.fullscreen) toggleFullscreen();

    logInfo("window", "Fenster geoeffnet: %ux%u", currentWidth, currentHeight);
    return statusOk();
}

void Window::close() {
    if (renderContext) {
        wglMakeCurrent(nullptr, nullptr);
        wglDeleteContext(static_cast<HGLRC>(renderContext));
        renderContext = nullptr;
    }
    if (deviceContext && windowHandle) {
        ReleaseDC(static_cast<HWND>(windowHandle), static_cast<HDC>(deviceContext));
        deviceContext = nullptr;
    }
    if (windowHandle) {
        DestroyWindow(static_cast<HWND>(windowHandle));
        windowHandle = nullptr;
    }
}

void Window::pumpEvents() {
    resized = false;
    inputState.beginFrame();
    MSG message;
    while (PeekMessageA(&message, nullptr, 0, 0, PM_REMOVE)) {
        TranslateMessage(&message);
        DispatchMessageA(&message);
    }
    applyCursorState();
}

void Window::applyCursorState() {
    if (!cursorCaptured || !hasFocus || !windowHandle) return;
    HWND handle = static_cast<HWND>(windowHandle);
    RECT client;
    GetClientRect(handle, &client);
    POINT center = {(client.right - client.left) / 2, (client.bottom - client.top) / 2};
    POINT screenCenter = center;
    ClientToScreen(handle, &screenCenter);
    POINT cursor;
    GetCursorPos(&cursor);
    if (cursor.x != screenCenter.x || cursor.y != screenCenter.y) {
        SetCursorPos(screenCenter.x, screenCenter.y);
        inputState.handleMouseMove(static_cast<f32>(center.x), static_cast<f32>(center.y));
    }
}

void Window::present() {
    if (deviceContext) SwapBuffers(static_cast<HDC>(deviceContext));
}

void Window::setTitle(const std::string& title) {
    if (windowHandle) SetWindowTextA(static_cast<HWND>(windowHandle), title.c_str());
}

void Window::setVerticalSync(bool enabled) {
    verticalSyncEnabled = enabled;
    if (wglSwapIntervalExtension) wglSwapIntervalExtension(enabled ? 1 : 0);
}

void Window::setCursorCaptured(bool captured) {
    if (cursorCaptured == captured) return;
    cursorCaptured = captured;
    inputState.setMouseCaptured(captured);
    ShowCursor(captured ? FALSE : TRUE);
    if (captured && windowHandle) {
        SetCapture(static_cast<HWND>(windowHandle));
    } else {
        ReleaseCapture();
    }
}

void Window::toggleFullscreen() {
    if (!windowHandle) return;
    HWND handle = static_cast<HWND>(windowHandle);
    if (!fullscreenActive) {
        RECT bounds;
        GetWindowRect(handle, &bounds);
        windowedPositionX = bounds.left;
        windowedPositionY = bounds.top;
        windowedWidth = currentWidth;
        windowedHeight = currentHeight;

        MONITORINFO monitor = {};
        monitor.cbSize = sizeof(MONITORINFO);
        GetMonitorInfoA(MonitorFromWindow(handle, MONITOR_DEFAULTTONEAREST), &monitor);
        SetWindowLongA(handle, GWL_STYLE, WS_POPUP | WS_VISIBLE);
        SetWindowPos(handle, HWND_TOP, monitor.rcMonitor.left, monitor.rcMonitor.top,
                     monitor.rcMonitor.right - monitor.rcMonitor.left,
                     monitor.rcMonitor.bottom - monitor.rcMonitor.top, SWP_FRAMECHANGED);
        fullscreenActive = true;
    } else {
        SetWindowLongA(handle, GWL_STYLE, WS_OVERLAPPEDWINDOW | WS_VISIBLE);
        RECT desired = {0, 0, static_cast<LONG>(windowedWidth), static_cast<LONG>(windowedHeight)};
        AdjustWindowRect(&desired, WS_OVERLAPPEDWINDOW, FALSE);
        SetWindowPos(handle, HWND_TOP, windowedPositionX, windowedPositionY, desired.right - desired.left,
                     desired.bottom - desired.top, SWP_FRAMECHANGED);
        fullscreenActive = false;
    }
}

void Window::notifyResize(u32 width, u32 height) {
    if (width == 0 || height == 0) return;
    if (width == currentWidth && height == currentHeight) return;
    currentWidth = width;
    currentHeight = height;
    resized = true;
}

void Window::notifyFocus(bool focusedValue) {
    hasFocus = focusedValue;
    if (!focusedValue && cursorCaptured) setCursorCaptured(false);
}

namespace {

LRESULT CALLBACK windowProcedure(HWND handle, UINT message, WPARAM wparam, LPARAM lparam) {
    Window* window = reinterpret_cast<Window*>(GetWindowLongPtrA(handle, GWLP_USERDATA));
    if (!window) return DefWindowProcA(handle, message, wparam, lparam);

    switch (message) {
        case WM_SIZE:
            window->notifyResize(static_cast<u32>(LOWORD(lparam)), static_cast<u32>(HIWORD(lparam)));
            return 0;
        case WM_SETFOCUS:
            window->notifyFocus(true);
            return 0;
        case WM_KILLFOCUS:
            window->notifyFocus(false);
            return 0;
        case WM_CLOSE:
            window->requestClose();
            return 0;
        case WM_DESTROY:
            window->requestClose();
            PostQuitMessage(0);
            return 0;
        case WM_KEYDOWN:
        case WM_SYSKEYDOWN:
            window->input().handleKey(static_cast<u32>(wparam), true);
            return 0;
        case WM_KEYUP:
        case WM_SYSKEYUP:
            window->input().handleKey(static_cast<u32>(wparam), false);
            return 0;
        case WM_CHAR:
            window->input().handleTextCharacter(static_cast<u32>(wparam));
            return 0;
        case WM_LBUTTONDOWN:
            window->input().handleMouseButton(MouseButton::Left, true);
            return 0;
        case WM_LBUTTONUP:
            window->input().handleMouseButton(MouseButton::Left, false);
            return 0;
        case WM_RBUTTONDOWN:
            window->input().handleMouseButton(MouseButton::Right, true);
            return 0;
        case WM_RBUTTONUP:
            window->input().handleMouseButton(MouseButton::Right, false);
            return 0;
        case WM_MBUTTONDOWN:
            window->input().handleMouseButton(MouseButton::Middle, true);
            return 0;
        case WM_MBUTTONUP:
            window->input().handleMouseButton(MouseButton::Middle, false);
            return 0;
        case WM_MOUSEMOVE:
            window->input().handleMouseMove(static_cast<f32>(GET_X_LPARAM(lparam)),
                                            static_cast<f32>(GET_Y_LPARAM(lparam)));
            return 0;
        case WM_MOUSEWHEEL:
            window->input().handleMouseWheel(static_cast<f32>(GET_WHEEL_DELTA_WPARAM(wparam)) / 120.0f);
            return 0;
        default:
            break;
    }
    return DefWindowProcA(handle, message, wparam, lparam);
}

}

}
