from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime

from app.core.config import DATA_DIR

CAPSULES_FILE = DATA_DIR / "capsules.json"


class CapsuleService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if CAPSULES_FILE.exists():
            try:
                data = json.loads(CAPSULES_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    def _save(self) -> None:
        try:
            CAPSULES_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def add(self, text: str, deliver_date: str) -> dict:
        text = text.strip()
        if not text:
            return {"error": "Nachricht angeben"}
        try:
            target = datetime.strptime(deliver_date.strip(), "%Y-%m-%d")
        except Exception:
            return {"error": "deliver_date muss das Format JJJJ-MM-TT haben"}
        if target.date() <= datetime.now().date():
            return {"error": "Das Datum muss in der Zukunft liegen"}
        mood = ""
        try:
            from app.services.persona_service import get_persona_service

            mood = str(get_persona_service().state().get("mood_label", ""))
        except Exception:
            pass
        item = {
            "id": uuid.uuid4().hex[:10],
            "text": text,
            "deliver_date": target.strftime("%Y-%m-%d"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "mood": mood,
            "delivered": False,
        }
        with self._lock:
            self._data.insert(0, item)
            self._save()
        return item

    def list(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": c["id"],
                    "deliver_date": c["deliver_date"],
                    "created_at": c["created_at"],
                    "delivered": c.get("delivered", False),
                    "preview": (c["text"][:40] + "…")
                    if len(c["text"]) > 40 and not c.get("delivered")
                    else (c["text"] if c.get("delivered") else c["text"][:40]),
                }
                for c in self._data
            ]

    def due(self) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        delivered: list[dict] = []
        with self._lock:
            for c in self._data:
                if not c.get("delivered") and c["deliver_date"] <= today:
                    c["delivered"] = True
                    delivered.append(dict(c))
            if delivered:
                self._save()
        return delivered

    def delete(self, capsule_id: str) -> bool:
        with self._lock:
            before = len(self._data)
            self._data = [c for c in self._data if c["id"] != capsule_id]
            if len(self._data) < before:
                self._save()
                return True
        return False


_service: CapsuleService | None = None


def get_capsule_service() -> CapsuleService:
    global _service
    if _service is None:
        _service = CapsuleService()
    return _service
