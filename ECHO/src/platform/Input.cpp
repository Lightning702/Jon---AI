#include "Input.h"

namespace echo {

void Input::beginFrame() {
    std::memcpy(prevKeys, keys, sizeof(keys));
    std::memcpy(prevBtns, btns, sizeof(btns));
    delta = em::Vec2(0, 0);
    scrollDelta = 0.0f;
    text.clear();
}

void Input::onKey(int key, bool down) {
    if (key >= 0 && key < KEY_COUNT) keys[key] = down;
}

void Input::onMouseButton(int btn, bool down) {
    if (btn >= 0 && btn < MOUSE_BUTTON_COUNT) btns[btn] = down;
}

void Input::onMouseMoveRaw(float dx, float dy) {
    delta.x += dx;
    delta.y += dy;
}

void Input::onMousePos(float x, float y) {
    pos = em::Vec2(x, y);
}

void Input::onScroll(float d) {
    scrollDelta += d;
}

void Input::onChar(unsigned int c) {
    if (c >= 32 && c < 127) text.push_back((char)c);
}

void Input::reset() {
    std::memset(keys, 0, sizeof(keys));
    std::memset(prevKeys, 0, sizeof(prevKeys));
    std::memset(btns, 0, sizeof(btns));
    std::memset(prevBtns, 0, sizeof(prevBtns));
    delta = em::Vec2(0, 0);
    scrollDelta = 0.0f;
    text.clear();
}

bool Input::anyKeyPressed() const {
    for (int i = 0; i < KEY_COUNT; i++) if (keys[i] && !prevKeys[i]) return true;
    for (int i = 0; i < MOUSE_BUTTON_COUNT; i++) if (btns[i] && !prevBtns[i]) return true;
    return false;
}

}
