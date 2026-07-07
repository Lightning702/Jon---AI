from __future__ import annotations

import ctypes
import os
import time

try:
    import pyautogui
    import pygetwindow
    import pyperclip

    AUTOMATION_ERROR = ""
except Exception as _exc:
    pyautogui = None
    pygetwindow = None
    pyperclip = None
    AUTOMATION_ERROR = str(_exc)

if pyautogui is not None:
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

if os.name == "nt":
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _require_automation() -> None:
    if pyautogui is None:
        raise RuntimeError(
            "Maus-/Tastatursteuerung nicht verfuegbar "
            f"({AUTOMATION_ERROR}). Installiere: pip install pyautogui pygetwindow pyperclip"
        )


def _virtual_bounds() -> tuple[int, int, int, int]:
    if os.name == "nt":
        user32 = ctypes.windll.user32
        return (
            user32.GetSystemMetrics(76),
            user32.GetSystemMetrics(77),
            user32.GetSystemMetrics(78),
            user32.GetSystemMetrics(79),
        )
    size = pyautogui.size()
    return 0, 0, size.width, size.height


class AutomationService:
    def screen_info(self) -> dict:
        _require_automation()
        size = pyautogui.size()
        pos = pyautogui.position()
        left, top, width, height = _virtual_bounds()
        return {
            "primary_width": size.width,
            "primary_height": size.height,
            "virtual_left": left,
            "virtual_top": top,
            "virtual_width": width,
            "virtual_height": height,
            "mouse_x": pos.x,
            "mouse_y": pos.y,
        }

    def _resolve(self, x: float, y: float) -> tuple[int, int]:
        size = pyautogui.size()
        left, top, width, height = _virtual_bounds()
        px = x * size.width if 0 <= x <= 1 and isinstance(x, float) else x
        py = y * size.height if 0 <= y <= 1 and isinstance(y, float) else y
        px = min(max(int(px), left), left + width - 1)
        py = min(max(int(py), top), top + height - 1)
        return px, py

    def mouse_move(self, x: float, y: float, duration: float = 0.3) -> dict:
        _require_automation()
        px, py = self._resolve(x, y)
        pyautogui.moveTo(px, py, duration=min(max(duration, 0.0), 3.0))
        return {"moved_to": [px, py]}

    def mouse_click(
        self,
        x: float | None = None,
        y: float | None = None,
        button: str = "left",
        clicks: int = 1,
    ) -> dict:
        _require_automation()
        if button not in ("left", "right", "middle"):
            button = "left"
        clicks = min(max(int(clicks), 1), 3)
        if x is not None and y is not None:
            px, py = self._resolve(x, y)
            pyautogui.moveTo(px, py, duration=0.25)
        pyautogui.click(button=button, clicks=clicks, interval=0.1)
        pos = pyautogui.position()
        return {"clicked_at": [pos.x, pos.y], "button": button, "clicks": clicks}

    def mouse_scroll(self, amount: int) -> dict:
        _require_automation()
        pyautogui.scroll(min(max(int(amount), -5000), 5000))
        return {"scrolled": amount}

    def keyboard_type(self, text: str, press_enter: bool = False) -> dict:
        _require_automation()
        if text:
            if text.isascii():
                pyautogui.write(text, interval=0.02)
            else:
                old = None
                try:
                    old = pyperclip.paste()
                except Exception:
                    pass
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.15)
                if old is not None:
                    pyperclip.copy(old)
        if press_enter:
            time.sleep(0.1)
            pyautogui.press("enter")
        return {"typed": text, "enter": press_enter}

    def keyboard_press(self, key: str, presses: int = 1) -> dict:
        _require_automation()
        key = key.strip().lower()
        if key not in pyautogui.KEYBOARD_KEYS:
            return {"error": f"unbekannte Taste: {key}"}
        presses = min(max(int(presses), 1), 25)
        pyautogui.press(key, presses=presses, interval=0.05)
        return {"pressed": key, "presses": presses}

    def keyboard_hotkey(self, keys: list[str]) -> dict:
        _require_automation()
        cleaned = [k.strip().lower() for k in keys if k and k.strip()]
        if not cleaned:
            return {"error": "keine Tasten angegeben"}
        invalid = [k for k in cleaned if k not in pyautogui.KEYBOARD_KEYS]
        if invalid:
            return {"error": f"unbekannte Tasten: {', '.join(invalid)}"}
        pyautogui.hotkey(*cleaned)
        return {"hotkey": "+".join(cleaned)}

    def list_windows(self) -> list[dict]:
        _require_automation()
        windows = []
        for w in pygetwindow.getAllWindows():
            if not w.title.strip():
                continue
            windows.append(
                {
                    "title": w.title,
                    "active": w.isActive,
                    "minimized": w.isMinimized,
                }
            )
        return windows

    def focus_window(self, title: str) -> dict:
        _require_automation()
        needle = title.strip().lower()
        for w in pygetwindow.getAllWindows():
            if needle in w.title.lower():
                try:
                    if w.isMinimized:
                        w.restore()
                    w.activate()
                except Exception:
                    try:
                        w.minimize()
                        w.restore()
                    except Exception as exc:
                        return {"error": str(exc), "title": w.title}
                time.sleep(0.3)
                return {"focused": w.title}
        return {"error": f"kein Fenster mit Titel '{title}' gefunden"}

    def wait(self, seconds: float) -> dict:
        seconds = min(max(float(seconds), 0.1), 15.0)
        time.sleep(seconds)
        return {"waited": seconds}
