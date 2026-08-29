from __future__ import annotations

import json
import threading

from app.core.config import DATA_DIR

from .models import ACTIVE_STATES, STATUS_INTERRUPTED, ResearchTask
from app.core.store import atomic_write_text

RESEARCH_DIR = DATA_DIR / "research"


class ResearchStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str):
        safe = "".join(char for char in task_id if char.isalnum())
        return RESEARCH_DIR / f"{safe}.json"

    def save(self, task: ResearchTask) -> None:
        payload = json.dumps(task.storage_dict(), ensure_ascii=False, indent=2)
        with self._lock:
            atomic_write_text(self._path(task.id), payload)

    def load(self, task_id: str) -> ResearchTask | None:
        path = self._path(task_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return ResearchTask.from_dict(data)

    def all(self) -> list[ResearchTask]:
        tasks: list[ResearchTask] = []
        for path in RESEARCH_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            tasks.append(ResearchTask.from_dict(data))
        tasks.sort(key=lambda task: task.created_at, reverse=True)
        return tasks

    def delete(self, task_id: str) -> bool:
        path = self._path(task_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def mark_interrupted(self) -> list[str]:
        touched: list[str] = []
        for task in self.all():
            if task.status in ACTIVE_STATES:
                task.status = STATUS_INTERRUPTED
                task.stage = "Beim Neustart unterbrochen"
                self.save(task)
                touched.append(task.id)
        return touched
