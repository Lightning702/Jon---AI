from __future__ import annotations

import json
import threading
import time
import uuid

from app.core.config import DATA_DIR

NOTES_FILE = DATA_DIR / "sticky_notes.json"
COLORS = ("gold", "blau", "gruen", "rosa", "lila")


class NotesService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._notes = self._load()

    def _load(self) -> list[dict]:
        try:
            data = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _save(self) -> None:
        try:
            NOTES_FILE.write_text(
                json.dumps(self._notes, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def list(self) -> list[dict]:
        with self._lock:
            return sorted(
                self._notes,
                key=lambda n: (not n.get("pinned"), -n.get("updated", 0)),
            )

    def add(self, text: str, color: str = "gold") -> dict:
        note = {
            "id": uuid.uuid4().hex,
            "text": text.strip(),
            "color": color if color in COLORS else "gold",
            "pinned": False,
            "done": False,
            "updated": time.time(),
        }
        with self._lock:
            self._notes.append(note)
            self._save()
        return note

    def update(self, note_id: str, **fields) -> dict:
        with self._lock:
            note = next((n for n in self._notes if n["id"] == note_id), None)
            if note is None:
                return {"error": "Notiz nicht gefunden."}
            if "text" in fields and fields["text"] is not None:
                note["text"] = str(fields["text"]).strip()
            if "color" in fields and fields["color"] in COLORS:
                note["color"] = fields["color"]
            if "pinned" in fields and fields["pinned"] is not None:
                note["pinned"] = bool(fields["pinned"])
            if "done" in fields and fields["done"] is not None:
                note["done"] = bool(fields["done"])
            note["updated"] = time.time()
            self._save()
            return note

    def delete(self, note_id: str) -> bool:
        with self._lock:
            before = len(self._notes)
            self._notes = [n for n in self._notes if n["id"] != note_id]
            if len(self._notes) != before:
                self._save()
                return True
        return False


_service: NotesService | None = None


def get_notes_service() -> NotesService:
    global _service
    if _service is None:
        _service = NotesService()
    return _service
