from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime

from app.core.config import DATA_DIR

CLIPBOARD_FILE = DATA_DIR / "clipboard_history.json"
MAX_ENTRIES = 50
MAX_CHARS = 20_000


class ClipboardService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: list[dict] = self._load()
        self._last = self._entries[0]["text"] if self._entries else ""

    def _load(self) -> list[dict]:
        if CLIPBOARD_FILE.exists():
            try:
                data = json.loads(CLIPBOARD_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    def _save(self) -> None:
        try:
            CLIPBOARD_FILE.write_text(
                json.dumps(self._entries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def capture(self) -> None:
        try:
            import pyperclip

            text = pyperclip.paste()
        except Exception:
            return
        if not isinstance(text, str):
            return
        text = text[:MAX_CHARS]
        if not text.strip() or text == self._last:
            return
        with self._lock:
            self._last = text
            self._entries = [e for e in self._entries if e.get("text") != text]
            self._entries.insert(
                0,
                {
                    "id": uuid.uuid4().hex[:10],
                    "text": text,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                },
            )
            del self._entries[MAX_ENTRIES:]
            self._save()

    def list(self, query: str = "", limit: int = 50) -> list[dict]:
        q = query.strip().lower()
        with self._lock:
            entries = list(self._entries)
        if q:
            entries = [e for e in entries if q in e.get("text", "").lower()]
        return entries[: max(1, min(int(limit), MAX_ENTRIES))]

    def restore(self, entry_id: str) -> bool:
        with self._lock:
            entry = next((e for e in self._entries if e["id"] == entry_id), None)
        if entry is None:
            return False
        try:
            import pyperclip

            pyperclip.copy(entry["text"])
            self._last = entry["text"]
            return True
        except Exception:
            return False

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            before = len(self._entries)
            self._entries = [e for e in self._entries if e["id"] != entry_id]
            if len(self._entries) < before:
                self._save()
                return True
        return False

    def clear(self) -> int:
        with self._lock:
            count = len(self._entries)
            self._entries = []
            self._save()
        return count


_service: ClipboardService | None = None


def get_clipboard_service() -> ClipboardService:
    global _service
    if _service is None:
        _service = ClipboardService()
    return _service
