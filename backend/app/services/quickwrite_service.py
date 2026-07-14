from __future__ import annotations

import asyncio
import threading
import time

from app.services.llm import complete
from app.services.settings_service import get_settings_service

PROMPTS = {
    "verbessern": (
        "Verbessere den folgenden Text: Rechtschreibung, Grammatik, Zeichensetzung und "
        "Stil. Behalte Sprache, Bedeutung, Ton und ungefähre Länge bei. Gib NUR den "
        "verbesserten Text aus, ohne Anführungszeichen, ohne Kommentar."
    ),
    "uebersetzen": (
        "Übersetze den folgenden Text: Ist er Deutsch, übersetze ihn in natürliches "
        "Englisch. Ist er in einer anderen Sprache, übersetze ihn in natürliches "
        "Deutsch. Gib NUR die Übersetzung aus."
    ),
    "kuerzen": (
        "Kürze den folgenden Text auf etwa die Hälfte, ohne wichtige Inhalte zu "
        "verlieren. Behalte Sprache und Ton bei. Gib NUR den gekürzten Text aus."
    ),
    "antworten": (
        "Der folgende Text ist eine Nachricht an den Nutzer. Schreibe eine passende, "
        "freundliche, natürliche Antwort darauf in derselben Sprache. Gib NUR die "
        "Antwort aus."
    ),
}


class QuickwriteService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending = ""
        self._busy = False
        self._listener_started = False

    def _enabled(self) -> bool:
        return bool(get_settings_service().get().get("quickwrite_enabled", True))

    def grab_selection(self) -> dict:
        import pyautogui
        import pyperclip

        with self._lock:
            if self._busy:
                return {"error": "Der Schreib-Assistent arbeitet gerade schon."}
        old = ""
        try:
            old = pyperclip.paste()
        except Exception:
            pass
        try:
            pyperclip.copy("")
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.25)
            text = pyperclip.paste()
        except Exception as exc:
            return {"error": f"Konnte den markierten Text nicht lesen: {exc}"}
        if not text.strip():
            try:
                pyperclip.copy(old)
            except Exception:
                pass
            return {"error": "Kein Text markiert — erst Text markieren, dann Jon rufen."}
        with self._lock:
            self._pending = text
        return {"ok": True, "preview": text.strip()[:120], "chars": len(text)}

    async def apply(self, mode: str) -> dict:
        with self._lock:
            text = self._pending.strip()
        if not text:
            return {"error": "Kein Text übernommen — erst Text markieren."}
        return await self._transform(mode, text)

    async def run_direct(self, mode: str) -> dict:
        grabbed = self.grab_selection()
        if "error" in grabbed:
            return grabbed
        return await self.apply(mode)

    async def _transform(self, mode: str, text: str) -> dict:
        import pyautogui
        import pyperclip

        if mode == "humanisieren":
            from app.services.humanize_service import humanize

            with self._lock:
                self._busy = True
            try:
                result = await humanize(text, "neutral", 2)
            finally:
                with self._lock:
                    self._busy = False
            if "error" in result:
                return result
            output = result["text"]
        else:
            prompt = PROMPTS.get(mode)
            if prompt is None:
                return {"error": "Unbekannter Modus."}
            saved_provider, saved_model = get_settings_service().selection()
            with self._lock:
                self._busy = True
            try:
                output = await complete(
                    prompt,
                    text[:12000],
                    provider=saved_provider or None,
                    model=saved_model or None,
                    max_tokens=4096,
                    temperature=0.6,
                )
            except Exception as exc:
                return {"error": f"Umschreiben fehlgeschlagen: {exc}"}
            finally:
                with self._lock:
                    self._busy = False
            output = output.strip().strip('"').strip()
        if not output:
            return {"error": "Das Modell hat nichts zurückgegeben."}
        old = ""
        try:
            old = pyperclip.paste()
        except Exception:
            pass
        try:
            await asyncio.sleep(0.5)
            pyautogui.press("esc")
            pyperclip.copy(output)
            await asyncio.sleep(0.15)
            pyautogui.hotkey("ctrl", "v")
            await asyncio.sleep(0.6)
            pyperclip.copy(old)
        except Exception as exc:
            return {"error": f"Einfügen fehlgeschlagen: {exc}", "text": output}
        with self._lock:
            self._pending = ""
        return {"ok": True, "chars": len(output)}

    def start_mouse_listener(self) -> None:
        with self._lock:
            if self._listener_started:
                return
            self._listener_started = True
        try:
            from pynput import keyboard, mouse
        except Exception:
            return
        pressed_keys: set = set()

        def on_press(key) -> None:
            pressed_keys.add(key)

        def on_release(key) -> None:
            pressed_keys.discard(key)

        def ctrl_down() -> bool:
            return any(
                k in pressed_keys
                for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.ctrl)
            )

        def alt_down() -> bool:
            return any(
                k in pressed_keys
                for k in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr)
            )

        def on_click(x, y, button, is_pressed) -> None:
            if not is_pressed or button != mouse.Button.right:
                return
            if not (ctrl_down() and alt_down()):
                return
            if not self._enabled():
                return
            threading.Thread(
                target=lambda: asyncio.run(self.run_direct("verbessern")),
                daemon=True,
            ).start()

        keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True).start()
        mouse.Listener(on_click=on_click, daemon=True).start()


_service: QuickwriteService | None = None


def get_quickwrite_service() -> QuickwriteService:
    global _service
    if _service is None:
        _service = QuickwriteService()
    return _service
