from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime

from app.core.config import DATA_DIR

STATS_FILE = DATA_DIR / "focus_stats.json"

DISTRACTION_MARKERS = (
    "youtube",
    "netflix",
    "tiktok",
    "instagram",
    "twitter",
    "x.com",
    "reddit",
    "twitch",
    "9gag",
    "disney+",
    "prime video",
    "crunchyroll",
    "steam",
    "epic games",
    "9anime",
)

NUDGES = (
    "Hey, {app} läuft — wir wollten doch {goal}. Komm, noch {minutes} Minuten!",
    "Psst … {app}? Jetzt nicht. Du schaffst das, noch {minutes} Minuten.",
    "Ich sehe {app} 👀 Zurück an die Arbeit, wir sind fast durch!",
    "Kurz schwach geworden? Macht nichts. {app} zu, weiter gehts — noch {minutes} Minuten.",
)


def active_window_title() -> str:
    try:
        import pygetwindow as gw

        window = gw.getActiveWindow()
        return str(window.title or "") if window else ""
    except Exception:
        return ""


class FocusService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session: dict | None = None
        self._events: list[dict] = []
        self._stats = self._load_stats()

    def _load_stats(self) -> dict:
        try:
            data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_stats(self) -> None:
        try:
            STATS_FILE.write_text(
                json.dumps(self._stats, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _push(self, kind: str, say: str) -> None:
        self._events.append({"kind": kind, "say": say})
        del self._events[:-6]

    def start(self, minutes: int = 25, goal: str = "") -> dict:
        minutes = max(5, min(int(minutes or 25), 240))
        with self._lock:
            now = time.time()
            self._session = {
                "goal": goal.strip() or "konzentriert arbeiten",
                "started": now,
                "ends": now + minutes * 60,
                "minutes": minutes,
                "distractions": 0,
                "last_nudge": 0.0,
            }
            self._push(
                "focus",
                f"Fokus-Modus an: {minutes} Minuten für „{self._session['goal']}“. "
                "Ich passe auf — los gehts! 💪",
            )
            return self.state()

    def stop(self, completed: bool = False) -> dict:
        with self._lock:
            session = self._session
            self._session = None
            if session is None:
                return {"active": False}
            worked = int(min(time.time(), session["ends"]) - session["started"])
            day = datetime.now().strftime("%Y-%m-%d")
            entry = self._stats.setdefault(day, {"seconds": 0, "distractions": 0, "sessions": 0})
            entry["seconds"] += max(worked, 0)
            entry["distractions"] += session["distractions"]
            entry["sessions"] += 1
            self._save_stats()
            minutes_done = max(worked, 0) // 60
            if completed:
                self._push(
                    "focus",
                    f"Zeit um — {session['minutes']} Minuten voll durchgezogen! "
                    f"{session['distractions']}x kurz abgelenkt. Stark! 🎉",
                )
            else:
                self._push(
                    "focus",
                    f"Fokus beendet nach {minutes_done} Minuten. "
                    f"Heute gesamt: {entry['seconds'] // 60} Minuten.",
                )
            return {"active": False, "worked_minutes": minutes_done}

    def tick(self) -> None:
        with self._lock:
            session = self._session
            if session is None:
                return
            now = time.time()
        if now >= session["ends"]:
            self.stop(completed=True)
            return
        title = active_window_title().lower()
        if not title:
            return
        hit = next((m for m in DISTRACTION_MARKERS if m in title), "")
        if not hit:
            return
        with self._lock:
            if self._session is None or now - self._session["last_nudge"] < 75:
                return
            self._session["last_nudge"] = now
            self._session["distractions"] += 1
            remaining = max(1, int((self._session["ends"] - now) / 60))
            line = random.choice(NUDGES).format(
                app=hit.title(), goal=self._session["goal"], minutes=remaining
            )
            self._push("nudge", line)

    def poll_events(self) -> list[dict]:
        with self._lock:
            events = self._events
            self._events = []
            return events

    def state(self) -> dict:
        with self._lock:
            day = datetime.now().strftime("%Y-%m-%d")
            today = self._stats.get(day, {"seconds": 0, "distractions": 0, "sessions": 0})
            if self._session is None:
                return {"active": False, "today": today}
            return {
                "active": True,
                "goal": self._session["goal"],
                "minutes": self._session["minutes"],
                "remaining_seconds": max(0, int(self._session["ends"] - time.time())),
                "distractions": self._session["distractions"],
                "today": today,
            }


_service: FocusService | None = None


def get_focus_service() -> FocusService:
    global _service
    if _service is None:
        _service = FocusService()
    return _service
