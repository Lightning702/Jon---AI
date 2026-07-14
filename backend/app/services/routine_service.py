from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta

from app.core.config import DATA_DIR
from app.services.focus_service import active_window_title

LOG_FILE = DATA_DIR / "routine_log.json"
STATE_FILE = DATA_DIR / "routine_state.json"
KEEP_DAYS = 21
MIN_DAYS = 5

SLOTS = (
    (5, 11, "morgens", "08:30"),
    (11, 15, "mittags", "12:30"),
    (15, 19, "nachmittags", "16:00"),
    (19, 24, "abends", "20:00"),
)

IGNORED = (
    "explorer",
    "windows",
    "jon",
    "electron",
    "task-manager",
    "taskmgr",
    "einstellungen",
    "settings",
    "suche",
    "search",
    "startmenü",
)


def _slot(hour: int) -> tuple[str, str] | None:
    for start, end, name, default_time in SLOTS:
        if start <= hour < end:
            return name, default_time
    return None


def _app_name(title: str) -> str:
    parts = [p.strip() for p in title.split(" - ") if p.strip()]
    name = parts[-1] if parts else title.strip()
    return name[:60]


class RoutineService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._log = self._load(LOG_FILE, {})
        self._state = self._load(STATE_FILE, {"dismissed": [], "accepted": []})

    def _load(self, path, fallback):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, type(fallback)):
                return data
        except Exception:
            pass
        return fallback

    def _save(self) -> None:
        try:
            LOG_FILE.write_text(json.dumps(self._log, ensure_ascii=False), encoding="utf-8")
            STATE_FILE.write_text(
                json.dumps(self._state, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def tick(self) -> None:
        title = active_window_title()
        if not title:
            return
        app = _app_name(title)
        low = app.lower()
        if not app or any(marker in low for marker in IGNORED):
            return
        now = datetime.now()
        slot = _slot(now.hour)
        if slot is None:
            return
        day = now.strftime("%Y-%m-%d")
        with self._lock:
            day_log = self._log.setdefault(day, {})
            slot_log = day_log.setdefault(slot[0], {})
            slot_log[app] = 1
            cutoff = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
            for old_day in [d for d in self._log if d < cutoff]:
                self._log.pop(old_day, None)
            self._save()

    def suggestions(self) -> list[dict]:
        with self._lock:
            counts: dict[tuple[str, str], int] = {}
            for day_log in self._log.values():
                for slot_name, apps in day_log.items():
                    for app in apps:
                        counts[(slot_name, app)] = counts.get((slot_name, app), 0) + 1
            handled = set(self._state["dismissed"]) | set(self._state["accepted"])
            results = []
            for (slot_name, app), days in sorted(counts.items(), key=lambda kv: -kv[1]):
                key = f"{slot_name}|{app}"
                if days < MIN_DAYS or key in handled:
                    continue
                default_time = next(s[3] for s in SLOTS if s[2] == slot_name)
                results.append(
                    {
                        "id": key,
                        "app": app,
                        "slot": slot_name,
                        "days": days,
                        "time": default_time,
                        "text": (
                            f"Du nutzt {slot_name} fast immer {app} "
                            f"(an {days} der letzten Tage). Soll ich {app} künftig "
                            f"{slot_name} automatisch für dich öffnen?"
                        ),
                    }
                )
                if len(results) >= 2:
                    break
            return results

    def accept(self, suggestion_id: str) -> dict:
        matching = [s for s in self.suggestions() if s["id"] == suggestion_id]
        if not matching:
            return {"error": "Diesen Vorschlag gibt es nicht mehr."}
        suggestion = matching[0]
        from app.services.task_service import get_task_service

        task = get_task_service().add(
            f"Öffne {suggestion['app']} für den Nutzer (start_program oder open_url).",
            suggestion["time"],
            "daily",
        )
        with self._lock:
            self._state["accepted"].append(suggestion_id)
            self._save()
        return {"ok": True, "task": task, "app": suggestion["app"], "time": suggestion["time"]}

    def dismiss(self, suggestion_id: str) -> dict:
        with self._lock:
            if suggestion_id not in self._state["dismissed"]:
                self._state["dismissed"].append(suggestion_id)
            self._save()
        return {"ok": True}


_service: RoutineService | None = None


def get_routine_service() -> RoutineService:
    global _service
    if _service is None:
        _service = RoutineService()
    return _service
