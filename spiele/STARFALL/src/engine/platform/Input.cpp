#include "Input.hpp"

#include <cstring>

namespace sf {

void Input::beginFrame() {
    std::memcpy(previousKeys, currentKeys, sizeof(currentKeys));
    std::memcpy(previousButtons, currentButtons, sizeof(currentButtons));
    delta = Vec2(0.0f, 0.0f);
    wheel = 0.0f;
    characterCount = 0;
}

void Input::handleKey(u32 platformCode, bool down) {
    const Key key = keyFromPlatformCode(platformCode);
    if (key == Key::None) return;
    currentKeys[static_cast<usize>(key)] = down;
}

void Input::handleMouseButton(MouseButton button, bool down) {
    currentButtons[static_cast<usize>(button)] = down;
}

void Input::handleMouseMove(f32 x, f32 y) {
    const Vec2 next(x, y);
    if (hasPrevious) {
        delta += next - position;
    }
    previousPosition = position;
    position = next;
    hasPrevious = true;
}

void Input::handleMouseWheel(f32 deltaValue) {
    wheel += deltaValue;
}

void Input::handleTextCharacter(u32 codepoint) {
    if (characterCount >= 16) return;
    characters[characterCount++] = codepoint;
}

void Input::setMouseCaptured(bool capturedValue) {
    captured = capturedValue;
    hasPrevious = false;
}

bool Input::keyDown(Key key) const {
    return key != Key::None && currentKeys[static_cast<usize>(key)];
}

bool Input::keyPressed(Key key) const {
    return key != Key::None && currentKeys[static_cast<usize>(key)] && !previousKeys[static_cast<usize>(key)];
}

bool Input::keyReleased(Key key) const {
    return key != Key::None && !currentKeys[static_cast<usize>(key)] && previousKeys[static_cast<usize>(key)];
}

bool Input::mouseDown(MouseButton button) const {
    return currentButtons[static_cast<usize>(button)];
}

bool Input::mousePressed(MouseButton button) const {
    return currentButtons[static_cast<usize>(button)] && !previousButtons[static_cast<usize>(button)];
}

bool Input::mouseReleased(MouseButton button) const {
    return !currentButtons[static_cast<usize>(button)] && previousButtons[static_cast<usize>(button)];
}

Key Input::keyFromPlatformCode(u32 platformCode) {
    if (platformCode >= 'A' && platformCode <= 'Z') {
        return static_cast<Key>(static_cast<u32>(Key::A) + (platformCode - 'A'));
    }
    if (platformCode >= '0' && platformCode <= '9') {
        return static_cast<Key>(static_cast<u32>(Key::Digit0) + (platformCode - '0'));
    }
    switch (platformCode) {
        case 0x1B: return Key::Escape;
        case 0x20: return Key::Space;
        case 0x0D: return Key::Enter;
        case 0x09: return Key::Tab;
        case 0x08: return Key::Backspace;
        case 0x10: return Key::LeftShift;
        case 0x11: return Key::LeftControl;
        case 0x12: return Key::LeftAlt;
        case 0x25: return Key::Left;
        case 0x26: return Key::Up;
        case 0x27: return Key::Right;
        case 0x28: return Key::Down;
        case 0x70: return Key::F1;
        case 0x71: return Key::F2;
        case 0x72: return Key::F3;
        case 0x73: return Key::F4;
        case 0x74: return Key::F5;
        case 0x75: return Key::F6;
        case 0x76: return Key::F7;
        case 0x77: return Key::F8;
        case 0x78: return Key::F9;
        case 0x79: return Key::F10;
        case 0x7A: return Key::F11;
        case 0x7B: return Key::F12;
        case 0xBB: return Key::Plus;
        case 0xBD: return Key::Minus;
        case 0xBC: return Key::Comma;
        case 0xBE: return Key::Period;
        default: return Key::None;
    }
}

}
