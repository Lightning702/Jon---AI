from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR

WATCHERS_FILE = DATA_DIR / "watchers.json"


class WatcherService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()
        self._running = False

    def _load(self) -> dict:
        base = {"watchers": []}
        if WATCHERS_FILE.exists():
            try:
                base.update(json.loads(WATCHERS_FILE.read_text(encoding="utf-8")))
            except Exception:
                pass
        return base

    def _save(self) -> None:
        try:
            WATCHERS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def add(self, path: str, task: str) -> dict:
        folder = Path(path).expanduser()
        if not folder.is_dir():
            return {"error": f"Ordner nicht gefunden: {path}"}
        if not task.strip():
            return {"error": "Aufgabe angeben"}
        try:
            seen = [p.name for p in folder.iterdir() if p.is_file()]
        except Exception:
            seen = []
        item = {
            "id": uuid.uuid4().hex[:10],
            "path": str(folder),
            "task": task.strip(),
            "active": True,
            "seen_files": seen[:3000],
            "last_result": None,
            "last_run_at": None,
            "seen": True,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self._lock:
            self._data["watchers"].insert(0, item)
            self._save()
        return {k: v for k, v in item.items() if k != "seen_files"}

    def list(self) -> list[dict]:
        with self._lock:
            return [
                {k: v for k, v in w.items() if k != "seen_files"}
                for w in self._data["watchers"]
            ]

    def delete(self, watcher_id: str) -> bool:
        with self._lock:
            before = len(self._data["watchers"])
            self._data["watchers"] = [
                w for w in self._data["watchers"] if w["id"] != watcher_id
            ]
            self._save()
            return len(self._data["watchers"]) < before

    def unseen_reports(self) -> list[dict]:
        with self._lock:
            reports = [
                {k: v for k, v in w.items() if k != "seen_files"}
                for w in self._data["watchers"]
                if w.get("last_result") and not w.get("seen")
            ]
            for w in self._data["watchers"]:
                if w.get("last_result"):
                    w["seen"] = True
            if reports:
                self._save()
            return reports

    async def tick(self, provider: str | None, model: str | None) -> None:
        if self._running:
            return
        self._running = True
        try:
            with self._lock:
                watchers = list(self._data["watchers"])
            for w in watchers:
                if not w.get("active", True):
                    continue
                folder = Path(w["path"])
                if not folder.is_dir():
                    continue
                try:
                    names = [p.name for p in folder.iterdir() if p.is_file()]
                except Exception:
                    continue
                new = sorted(set(names) - set(w.get("seen_files", [])))
                with self._lock:
                    w["seen_files"] = names[:3000]
                    self._save()
                if not new:
                    continue
                from app.services.task_service import get_task_service

                prompt = (
                    f"Datei-Waechter: Im ueberwachten Ordner {w['path']} sind "
                    f"neue Dateien aufgetaucht: {', '.join(new[:30])}. "
                    f"Deine Aufgabe dazu: {w['task']}"
                )
                try:
                    result = await get_task_service()._run_task(
                        prompt, provider or "", model or ""
                    )
                except Exception as exc:
                    result = f"Datei-Waechter fehlgeschlagen: {exc}"
                with self._lock:
                    w["last_result"] = f"Neue Dateien: {', '.join(new[:10])}\n{result}"
                    w["last_run_at"] = datetime.now().isoformat(timespec="seconds")
                    w["seen"] = False
                    self._save()
        finally:
            self._running = False


_service: WatcherService | None = None


def get_watcher_service() -> WatcherService:
    global _service
    if _service is None:
        _service = WatcherService()
    return _service
