#pragma once

#include "../core/Math.h"

namespace echo {

enum Key {
    KEY_UNKNOWN = 0,
    KEY_A = 'A', KEY_B, KEY_C, KEY_D, KEY_E, KEY_F, KEY_G, KEY_H, KEY_I, KEY_J,
    KEY_K, KEY_L, KEY_M, KEY_N, KEY_O, KEY_P, KEY_Q, KEY_R, KEY_S, KEY_T,
    KEY_U, KEY_V, KEY_W, KEY_X, KEY_Y, KEY_Z,
    KEY_0 = '0', KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9,
    KEY_SPACE = 0x20,
    KEY_ESCAPE = 0x1B,
    KEY_ENTER = 0x0D,
    KEY_TAB = 0x09,
    KEY_BACKSPACE = 0x08,
    KEY_SHIFT = 0x10,
    KEY_CONTROL = 0x11,
    KEY_ALT = 0x12,
    KEY_LEFT = 0x25, KEY_UP = 0x26, KEY_RIGHT = 0x27, KEY_DOWN = 0x28,
    KEY_F1 = 0x70, KEY_F2, KEY_F3, KEY_F4, KEY_F5, KEY_F6, KEY_F7, KEY_F8,
    KEY_F9, KEY_F10, KEY_F11, KEY_F12,
    KEY_COUNT = 256
};

enum MouseButton { MOUSE_LEFT = 0, MOUSE_RIGHT = 1, MOUSE_MIDDLE = 2, MOUSE_BUTTON_COUNT = 3 };

class Input {
public:
    void beginFrame();
    void onKey(int key, bool down);
    void onMouseButton(int btn, bool down);
    void onMouseMoveRaw(float dx, float dy);
    void onMousePos(float x, float y);
    void onScroll(float d);
    void onChar(unsigned int c);
    void reset();

    bool key(int k) const { return k >= 0 && k < KEY_COUNT && keys[k]; }
    bool keyPressed(int k) const { return k >= 0 && k < KEY_COUNT && keys[k] && !prevKeys[k]; }
    bool keyReleased(int k) const { return k >= 0 && k < KEY_COUNT && !keys[k] && prevKeys[k]; }
    bool mouse(int b) const { return b >= 0 && b < MOUSE_BUTTON_COUNT && btns[b]; }
    bool mousePressed(int b) const { return b >= 0 && b < MOUSE_BUTTON_COUNT && btns[b] && !prevBtns[b]; }
    bool mouseReleased(int b) const { return b >= 0 && b < MOUSE_BUTTON_COUNT && !btns[b] && prevBtns[b]; }

    em::Vec2 mouseDelta() const { return delta; }
    em::Vec2 mousePos() const { return pos; }
    float scroll() const { return scrollDelta; }
    const std::string& textInput() const { return text; }
    bool anyKeyPressed() const;

private:
    bool keys[KEY_COUNT] = {};
    bool prevKeys[KEY_COUNT] = {};
    bool btns[MOUSE_BUTTON_COUNT] = {};
    bool prevBtns[MOUSE_BUTTON_COUNT] = {};
    em::Vec2 delta;
    em::Vec2 pos;
    float scrollDelta = 0.0f;
    std::string text;
};

}
