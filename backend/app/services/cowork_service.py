from __future__ import annotations

import asyncio
import threading
import time

from app.core.config import get_settings
from app.services.settings_service import get_settings_service

WORK_APPS = (
    ("visual studio code", "VS Code"),
    ("vscodium", "VS Code"),
    ("word", "Word"),
    ("winword", "Word"),
    ("google docs", "Google Docs"),
    ("docs.google", "Google Docs"),
    ("libreoffice writer", "LibreOffice"),
    ("obsidian", "Obsidian"),
    ("onenote", "OneNote"),
    ("excel", "Excel"),
    ("powerpoint", "PowerPoint"),
    ("notion", "Notion"),
    ("editor", "Editor"),
    ("notepad++", "Notepad++"),
    ("pycharm", "PyCharm"),
    ("intellij", "IntelliJ"),
)

APP_MARKERS = {
    "vscode": (["visual studio code", "vscodium"], "VS Code"),
    "word": (["word", "winword"], "Word"),
    "docs": (["google docs", "docs.google"], "Google Docs"),
    "libreoffice": (["libreoffice writer"], "LibreOffice Writer"),
    "obsidian": (["obsidian"], "Obsidian"),
    "onenote": (["onenote"], "OneNote"),
    "excel": (["excel"], "Excel"),
    "powerpoint": (["powerpoint"], "PowerPoint"),
    "notion": (["notion"], "Notion"),
    "notepad": (["notepad", "editor"], "Editor"),
    "notepadpp": (["notepad++"], "Notepad++"),
    "pycharm": (["pycharm"], "PyCharm"),
    "intellij": (["intellij"], "IntelliJ"),
}

CHECK_INTERVAL = 300
REASK_AFTER_SECONDS = 900
TIP_INTERVAL = 200
AWAY_RESET = 600

TIP_PROMPT = (
    "Du bist Mini Jon und arbeitest gerade mit dem Nutzer zusammen. Auf dem Bildschirm "
    "siehst du seine aktuelle Arbeit in {app}. Gib EINEN kurzen, konkreten, hilfreichen "
    "Hinweis auf Deutsch (maximal 2 Saetze, locker und freundlich, wie ein aufmerksamer "
    "Kollege): ein Tippfehler, ein Logikproblem, eine bessere Formulierung, eine Idee "
    "oder der naechste sinnvolle Schritt. Beziehe dich NUR auf das, was wirklich sichtbar "
    "ist. Wenn gerade nichts wirklich Hilfreiches zu sagen ist, antworte AUSSCHLIESSLICH "
    "mit dem Wort: nichts"
)


def detect_work_app(title: str) -> str:
    low = title.lower()
    for marker, name in WORK_APPS:
        if marker in low:
            return name
    return ""


def open_window_titles() -> list[str]:
    try:
        import pygetwindow as gw

        return [t for t in gw.getAllTitles() if t and t.strip()]
    except Exception:
        return []


def app_open(target: str) -> str:
    titles = open_window_titles()
    if target in ("", "auto"):
        for t in titles:
            name = detect_work_app(t)
            if name:
                return name
        return ""
    markers, label = APP_MARKERS.get(target, (None, None))
    if not markers:
        return ""
    for t in titles:
        low = t.lower()
        if any(m in low for m in markers):
            return label
    return ""


class CoworkService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mode = "idle"
        self._app = ""
        self._last_check = 0.0
        self._snoozed_at = 0.0
        self._last_tip = 0.0
        self._ask_pending = False
        self._events: list[dict] = []

    def _push(self, kind: str, say: str) -> None:
        self._events.append({"kind": kind, "say": say})
        del self._events[:-4]

    def _enabled(self) -> bool:
        return bool(get_settings_service().get().get("cowork_enabled", False))

    def _target(self) -> str:
        return str(get_settings_service().get().get("cowork_app", "auto")).strip() or "auto"

    async def tick(self) -> None:
        if not self._enabled():
            with self._lock:
                if self._mode != "idle":
                    self._mode = "idle"
                self._ask_pending = False
            return
        now = time.time()
        with self._lock:
            mode = self._mode
        if mode == "active":
            with self._lock:
                if now - self._last_tip < TIP_INTERVAL:
                    return
                self._last_tip = now
                current_app = self._app
            label = await asyncio.to_thread(app_open, self._target())
            if not label:
                with self._lock:
                    if now - self._last_check > AWAY_RESET:
                        self._mode = "idle"
                        self._ask_pending = False
                return
            self._last_check = now
            tip = await self._make_tip(current_app)
            if tip:
                with self._lock:
                    if self._mode == "active":
                        self._push("cowork_tip", tip)
            return
        with self._lock:
            if now - self._last_check < CHECK_INTERVAL:
                return
            self._last_check = now
        label = await asyncio.to_thread(app_open, self._target())
        if not label:
            return
        with self._lock:
            if self._ask_pending:
                return
            if self._mode == "idle":
                self._app = label
                self._ask_pending = True
                self._push(
                    "cowork_ask",
                    f"Ich sehe, du hast {label} offen — soll ich mitarbeiten und ab und "
                    "zu über deine Schulter schauen?",
                )
            elif self._mode == "snoozed" and now - self._snoozed_at >= REASK_AFTER_SECONDS:
                self._app = label
                self._ask_pending = True
                self._push(
                    "cowork_ask",
                    f"{label} ist noch offen — soll ich jetzt mithelfen?",
                )

    async def _make_tip(self, app: str) -> str:
        from app.providers.openai_compatible import OpenAICompatibleProvider
        from app.providers.registry import get_registry
        from app.services.screen_service import VISION_DEFAULTS
        from app.services.system_service import SystemService

        settings = get_settings()
        user = get_settings_service().get()
        provider_name = user.get("provider") or settings.default_provider
        vision_model = user.get("vision_model") or VISION_DEFAULTS.get(provider_name)
        provider = get_registry().all().get(provider_name)
        if not isinstance(provider, OpenAICompatibleProvider) or not vision_model:
            return ""
        try:
            data_url = await asyncio.to_thread(SystemService().screenshot_data_url)
            text = await provider.describe_image(
                vision_model,
                data_url,
                TIP_PROMPT.format(app=app or "seiner App"),
                max_tokens=180,
            )
        except Exception:
            return ""
        clean = text.strip()
        if clean.lower().strip(" .!\"'") in ("nichts", "nothing", ""):
            return ""
        return clean[:400]

    def answer(self, accept: bool) -> dict:
        with self._lock:
            self._ask_pending = False
            if accept:
                self._mode = "active"
                self._last_tip = time.time() - TIP_INTERVAL + 20
                self._last_check = time.time()
                self._push(
                    "cowork",
                    f"Super, ich bin dabei! Arbeite ganz normal in {self._app or 'deiner App'} "
                    "weiter — ich melde mich, wenn mir was auffällt. 🤝",
                )
            else:
                self._mode = "snoozed"
                self._snoozed_at = time.time()
                self._push("cowork", "Alles klar, ich halte mich raus. Ich frag später nochmal.")
            return self.state()

    def poll_events(self) -> list[dict]:
        with self._lock:
            events = self._events
            self._events = []
            return events

    def state(self) -> dict:
        with self._lock:
            return {
                "mode": self._mode,
                "app": self._app,
                "ask_pending": self._ask_pending,
            }


_service: CoworkService | None = None


def get_cowork_service() -> CoworkService:
    global _service
    if _service is None:
        _service = CoworkService()
    return _service
