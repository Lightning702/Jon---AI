#pragma once

#include "../core/Result.hpp"
#include "Input.hpp"

#include <string>

namespace sf {

struct WindowSettings {
    std::string title = "STARFALL: BEYOND THE VOID";
    u32 width = 1600;
    u32 height = 900;
    bool fullscreen = false;
    bool verticalSync = true;
    bool debugContext = false;
};

class Window {
public:
    Window() = default;
    ~Window();

    Window(const Window&) = delete;
    Window& operator=(const Window&) = delete;

    Status open(const WindowSettings& settings);
    void close();

    void pumpEvents();
    void present();
    void requestClose() { closeRequested = true; }

    void setTitle(const std::string& title);
    void setVerticalSync(bool enabled);
    void setCursorCaptured(bool captured);
    void toggleFullscreen();

    bool shouldClose() const { return closeRequested; }
    bool focused() const { return hasFocus; }
    u32 width() const { return currentWidth; }
    u32 height() const { return currentHeight; }
    f32 aspectRatio() const { return currentHeight > 0 ? static_cast<f32>(currentWidth) / static_cast<f32>(currentHeight) : 1.0f; }
    bool resizedThisFrame() const { return resized; }

    Input& input() { return inputState; }
    const Input& input() const { return inputState; }

    void notifyResize(u32 width, u32 height);
    void notifyFocus(bool focusedValue);

    void* nativeHandle() const { return windowHandle; }

private:
    void applyCursorState();

    void* windowHandle = nullptr;
    void* deviceContext = nullptr;
    void* renderContext = nullptr;
    void* instanceHandle = nullptr;
    u32 currentWidth = 0;
    u32 currentHeight = 0;
    u32 windowedWidth = 0;
    u32 windowedHeight = 0;
    i32 windowedPositionX = 0;
    i32 windowedPositionY = 0;
    bool closeRequested = false;
    bool hasFocus = true;
    bool resized = false;
    bool cursorCaptured = false;
    bool fullscreenActive = false;
    bool verticalSyncEnabled = true;
    Input inputState;
};

}
