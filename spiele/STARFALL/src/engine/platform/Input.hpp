#pragma once

#include "../core/Types.hpp"
#include "../math/Vec2.hpp"

namespace sf {

enum class Key : u32 {
    None = 0,
    A, B, C, D, E, F, G, H, I, J, K, L, M,
    N, O, P, Q, R, S, T, U, V, W, X, Y, Z,
    Digit0, Digit1, Digit2, Digit3, Digit4, Digit5, Digit6, Digit7, Digit8, Digit9,
    Escape, Space, Enter, Tab, Backspace,
    LeftShift, LeftControl, LeftAlt,
    Left, Right, Up, Down,
    F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12,
    Plus, Minus, Comma, Period,
    Count
};

enum class MouseButton : u32 {
    Left = 0,
    Right,
    Middle,
    Count
};

class Input {
public:
    void beginFrame();
    void handleKey(u32 platformCode, bool down);
    void handleMouseButton(MouseButton button, bool down);
    void handleMouseMove(f32 x, f32 y);
    void handleMouseWheel(f32 delta);
    void handleTextCharacter(u32 codepoint);
    void setMouseCaptured(bool captured);

    bool keyDown(Key key) const;
    bool keyPressed(Key key) const;
    bool keyReleased(Key key) const;
    bool mouseDown(MouseButton button) const;
    bool mousePressed(MouseButton button) const;
    bool mouseReleased(MouseButton button) const;

    Vec2 mousePosition() const { return position; }
    Vec2 mouseDelta() const { return delta; }
    f32 wheelDelta() const { return wheel; }
    bool mouseCaptured() const { return captured; }

    f32 axis(Key positiveKey, Key negativeKey) const {
        return (keyDown(positiveKey) ? 1.0f : 0.0f) - (keyDown(negativeKey) ? 1.0f : 0.0f);
    }

    const u32* textInput() const { return characters; }
    u32 textInputCount() const { return characterCount; }

    static Key keyFromPlatformCode(u32 platformCode);

private:
    bool currentKeys[static_cast<usize>(Key::Count)] = {};
    bool previousKeys[static_cast<usize>(Key::Count)] = {};
    bool currentButtons[static_cast<usize>(MouseButton::Count)] = {};
    bool previousButtons[static_cast<usize>(MouseButton::Count)] = {};
    Vec2 position;
    Vec2 previousPosition;
    Vec2 delta;
    f32 wheel = 0.0f;
    bool captured = false;
    bool hasPrevious = false;
    u32 characters[16] = {};
    u32 characterCount = 0;
};

}
