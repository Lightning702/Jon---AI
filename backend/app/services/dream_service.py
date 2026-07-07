from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime

from app.core.config import DATA_DIR
from app.services.llm import complete

DREAMS_FILE = DATA_DIR / "dreams.json"

DREAM_SYSTEM = (
    "Du bist Jon im 'Dream Mode'. Waehrend der Nutzer weg ist, arbeitest du "
    "eigenstaendig an einer Aufgabe und bereitest ein Ergebnis vor, das du ihm "
    "praesentierst, wenn er zurueckkommt. Denke gruendlich, recherchiere gedanklich, "
    "entwickle Ideen. Liefere ein fertiges, konkretes Ergebnis auf Deutsch: kurze "
    "Zusammenfassung oben, dann die Ausarbeitung. Handle nichts am PC an, produziere "
    "nur das Ergebnis als Text."
)


class DreamService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        base = {"tasks": [], "running": False}
        if DREAMS_FILE.exists():
            try:
                base.update(json.loads(DREAMS_FILE.read_text(encoding="utf-8")))
            except Exception:
                pass
        base["running"] = False
        return base

    def _save(self) -> None:
        try:
            DREAMS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def add(self, task: str) -> dict:
        item = {
            "id": uuid.uuid4().hex[:10],
            "task": task.strip(),
            "status": "pending",
            "result": None,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "done_at": None,
            "seen": False,
        }
        with self._lock:
            self._data["tasks"].insert(0, item)
            self._save()
        return item

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._data["tasks"])

    def unseen_reports(self) -> list[dict]:
        with self._lock:
            reports = [
                dict(t)
                for t in self._data["tasks"]
                if t["status"] == "done" and not t.get("seen")
            ]
            for t in self._data["tasks"]:
                if t["status"] == "done":
                    t["seen"] = True
            if reports:
                self._save()
            return reports

    def delete(self, task_id: str) -> bool:
        with self._lock:
            before = len(self._data["tasks"])
            self._data["tasks"] = [t for t in self._data["tasks"] if t["id"] != task_id]
            self._save()
            return len(self._data["tasks"]) < before

    async def run_pending(
        self, provider: str | None = None, model: str | None = None, limit: int = 3
    ) -> dict:
        with self._lock:
            if self._data.get("running"):
                return {"started": False, "reason": "laeuft bereits"}
            pending = [t for t in self._data["tasks"] if t["status"] == "pending"][:limit]
            if not pending:
                return {"started": False, "reason": "keine offenen Aufgaben"}
            self._data["running"] = True
            for t in pending:
                t["status"] = "working"
            self._save()
        done = 0
        try:
            for t in pending:
                try:
                    result = await complete(
                        DREAM_SYSTEM, t["task"], provider, model, max_tokens=2000
                    )
                    t["result"] = result
                    t["status"] = "done"
                    done += 1
                except Exception as exc:
                    t["result"] = f"Konnte nicht fertig werden: {exc}"
                    t["status"] = "done"
                t["done_at"] = datetime.now().isoformat(timespec="seconds")
                with self._lock:
                    self._save()
        finally:
            with self._lock:
                self._data["running"] = False
                self._save()
        return {"started": True, "completed": done}


_service: DreamService | None = None


def get_dream_service() -> DreamService:
    global _service
    if _service is None:
        _service = DreamService()
    return _service
