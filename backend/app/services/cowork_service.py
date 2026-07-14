from __future__ import annotations

import threading
import time

from app.core.config import get_settings
from app.services.focus_service import active_window_title
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

ASK_AFTER_SECONDS = 120
REASK_AFTER_SECONDS = 2700
TIP_INTERVAL = 200
AWAY_RESET = 600

TIP_PROMPT = (
    "Du bist Mini Jon und arbeitest gerade mit dem Nutzer zusammen. Er arbeitet an: "
    "{context}. Auf dem Bildschirm siehst du seine aktuelle Arbeit in {app}. Gib EINEN "
    "kurzen, konkreten, hilfreichen Hinweis auf Deutsch (maximal 2 Saetze, locker und "
    "freundlich, wie ein aufmerksamer Kollege): ein Tippfehler, ein Logikproblem, eine "
    "bessere Formulierung, eine Idee oder der naechste sinnvolle Schritt. Beziehe dich "
    "NUR auf das, was wirklich sichtbar ist. Wenn gerade nichts wirklich Hilfreiches zu "
    "sagen ist, antworte AUSSCHLIESSLICH mit dem Wort: nichts"
)


def detect_work_app(title: str) -> str:
    low = title.lower()
    for marker, name in WORK_APPS:
        if marker in low:
            return name
    return ""


class CoworkService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mode = "idle"
        self._app = ""
        self._work_since = 0.0
        self._last_seen = 0.0
        self._snoozed_at = 0.0
        self._last_tip = 0.0
        self._ask_pending = False
        self._events: list[dict] = []

    def _push(self, kind: str, say: str) -> None:
        self._events.append({"kind": kind, "say": say})
        del self._events[:-4]

    def _enabled(self) -> bool:
        return bool(get_settings_service().get().get("cowork_enabled", False))

    def _context(self) -> str:
        return str(get_settings_service().get().get("cowork_context", "")).strip() or (
            "sein aktuelles Projekt"
        )

    async def tick(self) -> None:
        if not self._enabled():
            with self._lock:
                self._mode = "idle"
                self._ask_pending = False
            return
        title = active_window_title()
        app = detect_work_app(title)
        now = time.time()
        with self._lock:
            if not app:
                if self._mode == "active" and now - self._last_seen > AWAY_RESET:
                    self._mode = "idle"
                    self._ask_pending = False
                if self._mode != "active":
                    self._work_since = 0.0
                return
            self._last_seen = now
            if self._app != app:
                self._app = app
                self._work_since = now
                if self._mode not in ("active", "snoozed"):
                    self._mode = "idle"
            if self._mode == "idle" and not self._ask_pending:
                if self._work_since and now - self._work_since >= ASK_AFTER_SECONDS:
                    self._ask_pending = True
                    self._push(
                        "cowork_ask",
                        f"Ich sehe, du arbeitest gerade in {app} — soll ich mitarbeiten "
                        "und ab und zu über deine Schulter schauen?",
                    )
                return
            if self._mode == "snoozed":
                if now - self._snoozed_at >= REASK_AFTER_SECONDS and not self._ask_pending:
                    self._ask_pending = True
                    self._push(
                        "cowork_ask",
                        f"Immer noch fleißig in {app}? Soll ich jetzt mithelfen?",
                    )
                return
            if self._mode != "active" or now - self._last_tip < TIP_INTERVAL:
                return
            self._last_tip = now
            context = self._context()
            current_app = app
        tip = await self._make_tip(current_app, context)
        if tip:
            with self._lock:
                if self._mode == "active":
                    self._push("cowork_tip", tip)

    async def _make_tip(self, app: str, context: str) -> str:
        import asyncio

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
                TIP_PROMPT.format(context=context, app=app),
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
                self._push(
                    "cowork",
                    f"Super, ich bin dabei! Arbeite ganz normal weiter an "
                    f"{self._context()} — ich melde mich, wenn mir was auffällt. 🤝",
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
