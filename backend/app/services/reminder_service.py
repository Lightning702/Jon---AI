from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime

from app.core.config import DATA_DIR

REMINDERS_FILE = DATA_DIR / "reminders.json"


class ReminderService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if REMINDERS_FILE.exists():
            try:
                return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self) -> None:
        try:
            REMINDERS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def add(
        self,
        text: str,
        time: str = "",
        repeat: str = "daily",
        phone: str = "",
    ) -> dict:
        item = {
            "id": uuid.uuid4().hex,
            "text": text.strip(),
            "time": time.strip(),
            "repeat": repeat if repeat in ("daily", "once") else "daily",
            "phone": phone.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_fired": None,
            "active": True,
        }
        with self._lock:
            self._data.append(item)
            self._save()
        return item

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._data)

    def delete(self, reminder_id: str) -> bool:
        with self._lock:
            before = len(self._data)
            self._data = [r for r in self._data if r["id"] != reminder_id]
            self._save()
            return len(self._data) < before

    def _due(self, reminder: dict, now: datetime) -> bool:
        if not reminder.get("active"):
            return False
        time_str = reminder.get("time", "")
        today = now.strftime("%Y-%m-%d")
        last = reminder.get("last_fired") or ""
        if not time_str:
            return False
        try:
            hour, minute = [int(x) for x in time_str.split(":")[:2]]
        except Exception:
            return False
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now < scheduled:
            return False
        if reminder["repeat"] == "once":
            return not last
        return not last.startswith(today)

    def due(self) -> list[dict]:
        now = datetime.now()
        fired: list[dict] = []
        with self._lock:
            for reminder in self._data:
                if self._due(reminder, now):
                    reminder["last_fired"] = now.isoformat(timespec="seconds")
                    if reminder["repeat"] == "once":
                        reminder["active"] = False
                    fired.append(dict(reminder))
            if fired:
                self._save()
        return fired


_service: ReminderService | None = None


def get_reminder_service() -> ReminderService:
    global _service
    if _service is None:
        _service = ReminderService()
    return _service
