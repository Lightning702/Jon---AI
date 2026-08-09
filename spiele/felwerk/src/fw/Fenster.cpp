#include "Fenster.hpp"

#include <windowsx.h>

#include "Protokoll.hpp"

namespace fw {
namespace {

const char* KLASSE = "FelwerkFensterKlasse";

using PfnCreateContextAttribs = HGLRC(WINAPI*)(HDC, HGLRC, const int*);
using PfnSwapInterval = BOOL(WINAPI*)(int);

PfnSwapInterval swapInterval = nullptr;

constexpr int ATTR_MAJOR = 0x2091;
constexpr int ATTR_MINOR = 0x2092;
constexpr int ATTR_PROFIL = 0x9126;
constexpr int PROFIL_KERN = 0x00000001;

LRESULT CALLBACK ablauf(HWND fenster, UINT nachricht, WPARAM wparam, LPARAM lparam);

}

Fenster::~Fenster() { schliessen(); }

bool Fenster::oeffnen(const FensterWunsch& wunsch) {
    HINSTANCE instanz = GetModuleHandleA(nullptr);

    WNDCLASSEXA klasse = {};
    klasse.cbSize = sizeof(WNDCLASSEXA);
    klasse.style = CS_OWNDC | CS_HREDRAW | CS_VREDRAW;
    klasse.lpfnWndProc = ablauf;
    klasse.hInstance = instanz;
    klasse.hCursor = LoadCursor(nullptr, IDC_ARROW);
    klasse.hbrBackground = reinterpret_cast<HBRUSH>(GetStockObject(BLACK_BRUSH));
    klasse.lpszClassName = KLASSE;
    RegisterClassExA(&klasse);

    RECT wunschgroesse = {0, 0, wunsch.breite, wunsch.hoehe};
    const DWORD stil = WS_OVERLAPPEDWINDOW;
    AdjustWindowRect(&wunschgroesse, stil, FALSE);

    HWND griff = CreateWindowExA(0, KLASSE, wunsch.titel.c_str(), stil, CW_USEDEFAULT, CW_USEDEFAULT,
                                 wunschgroesse.right - wunschgroesse.left,
                                 wunschgroesse.bottom - wunschgroesse.top, nullptr, nullptr, instanz, this);
    if (!griff) {
        warnung("Fenster konnte nicht erstellt werden");
        return false;
    }
    fenster = griff;
    SetWindowLongPtrA(griff, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(this));

    HDC dc = GetDC(griff);
    geraet = dc;

    PIXELFORMATDESCRIPTOR beschreibung = {};
    beschreibung.nSize = sizeof(PIXELFORMATDESCRIPTOR);
    beschreibung.nVersion = 1;
    beschreibung.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    beschreibung.iPixelType = PFD_TYPE_RGBA;
    beschreibung.cColorBits = 32;
    beschreibung.cDepthBits = 24;
    beschreibung.cStencilBits = 8;

    int format = ChoosePixelFormat(dc, &beschreibung);
    if (format == 0 || !SetPixelFormat(dc, format, &beschreibung)) {
        warnung("Kein passendes Pixelformat gefunden");
        return false;
    }

    HGLRC alt = wglCreateContext(dc);
    if (!alt) {
        warnung("OpenGL-Kontext konnte nicht erstellt werden");
        return false;
    }
    wglMakeCurrent(dc, alt);

    auto erzeuge = reinterpret_cast<PfnCreateContextAttribs>(wglGetProcAddress("wglCreateContextAttribsARB"));
    swapInterval = reinterpret_cast<PfnSwapInterval>(wglGetProcAddress("wglSwapIntervalEXT"));

    HGLRC modern = nullptr;
    if (erzeuge) {
        const int versionen[][2] = {{4, 5}, {4, 1}, {3, 3}};
        for (const int* paar : versionen) {
            int attribute[] = {ATTR_MAJOR, paar[0], ATTR_MINOR, paar[1], ATTR_PROFIL, PROFIL_KERN, 0};
            modern = erzeuge(dc, nullptr, attribute);
            if (modern) break;
        }
    }
    if (modern) {
        wglMakeCurrent(dc, modern);
        wglDeleteContext(alt);
        kontext = modern;
    } else {
        kontext = alt;
        warnung("Kein Kernkontext verfuegbar, es geht mit dem alten weiter");
    }

    if (!ladeGL()) {
        warnung("Der Grafiktreiber kennt %s nicht", fehlendeFunktion());
        return false;
    }

    RECT kunde;
    GetClientRect(griff, &kunde);
    fensterBreite = kunde.right - kunde.left;
    fensterHoehe = kunde.bottom - kunde.top;
    gemerkteBreite = fensterBreite;
    gemerkteHoehe = fensterHoehe;

    ShowWindow(griff, SW_SHOW);
    UpdateWindow(griff);
    vsyncSetzen(wunsch.vsync);
    if (wunsch.vollbild) vollbildUmschalten();

    const char* renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
    notiz("Fenster offen: %dx%d auf %s", fensterBreite, fensterHoehe, renderer ? renderer : "unbekannt");
    return true;
}

void Fenster::schliessen() {
    if (kontext) {
        wglMakeCurrent(nullptr, nullptr);
        wglDeleteContext(static_cast<HGLRC>(kontext));
        kontext = nullptr;
    }
    if (geraet && fenster) {
        ReleaseDC(static_cast<HWND>(fenster), static_cast<HDC>(geraet));
        geraet = nullptr;
    }
    if (fenster) {
        DestroyWindow(static_cast<HWND>(fenster));
        fenster = nullptr;
    }
}

void Fenster::ereignisse() {
    for (int i = 0; i < 256; ++i) tastenVorher[i] = tasten[i];
    for (int i = 0; i < 3; ++i) maustastenVorher[i] = maustasten[i];
    mausDeltaX = 0.0f;
    mausDeltaY = 0.0f;
    radDelta = 0.0f;
    MSG nachricht;
    while (PeekMessageA(&nachricht, nullptr, 0, 0, PM_REMOVE)) {
        TranslateMessage(&nachricht);
        DispatchMessageA(&nachricht);
    }
    mausMitteHalten();
}

void Fenster::mausMitteHalten() {
    if (!mausFang || !hatFokus || !fenster) return;
    HWND griff = static_cast<HWND>(fenster);
    RECT kunde;
    GetClientRect(griff, &kunde);
    POINT mitte = {(kunde.right - kunde.left) / 2, (kunde.bottom - kunde.top) / 2};
    POINT bildschirm = mitte;
    ClientToScreen(griff, &bildschirm);
    POINT zeiger;
    GetCursorPos(&zeiger);
    if (zeiger.x != bildschirm.x || zeiger.y != bildschirm.y) {
        SetCursorPos(bildschirm.x, bildschirm.y);
        mausX = static_cast<float>(mitte.x);
        mausY = static_cast<float>(mitte.y);
    }
}

void Fenster::zeigen() {
    if (geraet) SwapBuffers(static_cast<HDC>(geraet));
}

void Fenster::titelSetzen(const std::string& titel) {
    if (fenster) SetWindowTextA(static_cast<HWND>(fenster), titel.c_str());
}

void Fenster::vsyncSetzen(bool an) {
    if (swapInterval) swapInterval(an ? 1 : 0);
}

void Fenster::mausFangen(bool an) {
    if (mausFang == an) return;
    mausFang = an;
    ShowCursor(an ? FALSE : TRUE);
    if (an && fenster) {
        SetCapture(static_cast<HWND>(fenster));
    } else {
        ReleaseCapture();
    }
}

void Fenster::vollbildUmschalten() {
    if (!fenster) return;
    HWND griff = static_cast<HWND>(fenster);
    if (!vollbildAktiv) {
        RECT rahmen;
        GetWindowRect(griff, &rahmen);
        gemerktX = rahmen.left;
        gemerktY = rahmen.top;
        gemerkteBreite = fensterBreite;
        gemerkteHoehe = fensterHoehe;
        MONITORINFO monitor = {};
        monitor.cbSize = sizeof(MONITORINFO);
        GetMonitorInfoA(MonitorFromWindow(griff, MONITOR_DEFAULTTONEAREST), &monitor);
        SetWindowLongA(griff, GWL_STYLE, WS_POPUP | WS_VISIBLE);
        SetWindowPos(griff, HWND_TOP, monitor.rcMonitor.left, monitor.rcMonitor.top,
                     monitor.rcMonitor.right - monitor.rcMonitor.left,
                     monitor.rcMonitor.bottom - monitor.rcMonitor.top, SWP_FRAMECHANGED);
        vollbildAktiv = true;
    } else {
        SetWindowLongA(griff, GWL_STYLE, WS_OVERLAPPEDWINDOW | WS_VISIBLE);
        RECT wunsch = {0, 0, gemerkteBreite, gemerkteHoehe};
        AdjustWindowRect(&wunsch, WS_OVERLAPPEDWINDOW, FALSE);
        SetWindowPos(griff, HWND_TOP, gemerktX, gemerktY, wunsch.right - wunsch.left,
                     wunsch.bottom - wunsch.top, SWP_FRAMECHANGED);
        vollbildAktiv = false;
    }
}

void Fenster::tasteMelden(unsigned schluessel, bool gedrueckt) {
    if (schluessel < 256) tasten[schluessel] = gedrueckt;
}

void Fenster::maustasteMelden(Maustaste taste, bool gedrueckt) {
    maustasten[static_cast<int>(taste)] = gedrueckt;
}

void Fenster::mausMelden(float x, float y) {
    mausDeltaX += x - mausX;
    mausDeltaY += y - mausY;
    mausX = x;
    mausY = y;
}

void Fenster::radMelden(float wert) { radDelta += wert; }

void Fenster::groesseMelden(int breite, int hoehe) {
    if (breite <= 0 || hoehe <= 0) return;
    fensterBreite = breite;
    fensterHoehe = hoehe;
}

void Fenster::fokusMelden(bool wert) {
    hatFokus = wert;
    if (!wert) {
        for (int i = 0; i < 256; ++i) tasten[i] = false;
        if (mausFang) mausFangen(false);
    }
}

namespace {

LRESULT CALLBACK ablauf(HWND griff, UINT nachricht, WPARAM wparam, LPARAM lparam) {
    Fenster* fenster = reinterpret_cast<Fenster*>(GetWindowLongPtrA(griff, GWLP_USERDATA));
    if (!fenster) return DefWindowProcA(griff, nachricht, wparam, lparam);
    switch (nachricht) {
        case WM_SIZE:
            fenster->groesseMelden(LOWORD(lparam), HIWORD(lparam));
            return 0;
        case WM_SETFOCUS:
            fenster->fokusMelden(true);
            return 0;
        case WM_KILLFOCUS:
            fenster->fokusMelden(false);
            return 0;
        case WM_CLOSE:
            fenster->schliessenAnfordern();
            return 0;
        case WM_DESTROY:
            fenster->schliessenAnfordern();
            PostQuitMessage(0);
            return 0;
        case WM_KEYDOWN:
        case WM_SYSKEYDOWN:
            fenster->tasteMelden(static_cast<unsigned>(wparam), true);
            return 0;
        case WM_KEYUP:
        case WM_SYSKEYUP:
            fenster->tasteMelden(static_cast<unsigned>(wparam), false);
            return 0;
        case WM_LBUTTONDOWN:
            fenster->maustasteMelden(Maustaste::Links, true);
            return 0;
        case WM_LBUTTONUP:
            fenster->maustasteMelden(Maustaste::Links, false);
            return 0;
        case WM_RBUTTONDOWN:
            fenster->maustasteMelden(Maustaste::Rechts, true);
            return 0;
        case WM_RBUTTONUP:
            fenster->maustasteMelden(Maustaste::Rechts, false);
            return 0;
        case WM_MBUTTONDOWN:
            fenster->maustasteMelden(Maustaste::Mitte, true);
            return 0;
        case WM_MBUTTONUP:
            fenster->maustasteMelden(Maustaste::Mitte, false);
            return 0;
        case WM_MOUSEMOVE:
            fenster->mausMelden(static_cast<float>(GET_X_LPARAM(lparam)),
                                static_cast<float>(GET_Y_LPARAM(lparam)));
            return 0;
        case WM_MOUSEWHEEL:
            fenster->radMelden(static_cast<float>(GET_WHEEL_DELTA_WPARAM(wparam)) / 120.0f);
            return 0;
        default:
            break;
    }
    return DefWindowProcA(griff, nachricht, wparam, lparam);
}

}

}
