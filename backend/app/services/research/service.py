from __future__ import annotations

import asyncio
import re
from typing import Any

from app.core.config import get_settings

from . import storage
from .engine import ResearchEngine
from .models import (
    ACTIVE_STATES,
    RESUMABLE_STATES,
    STATUS_PAUSED,
    STATUS_RUNNING,
    ResearchTask,
)
from .store import ResearchStore

MIN_RESUME_S = 120.0

_NUMBER_WORDS = {
    "eine": 1,
    "einen": 1,
    "ein": 1,
    "anderthalb": 1.5,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fuenf": 5,
    "fünf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "zwoelf": 12,
    "zwölf": 12,
    "halbe": 0.5,
}

_HOUR_RE = re.compile(
    r"(\d+(?:[.,]\d+)?|[a-zäöüß]+)\s*(?:std|stunde|stunden|h)\b", re.IGNORECASE
)
_MIN_RE = re.compile(
    r"(\d+(?:[.,]\d+)?|[a-zäöüß]+)\s*(?:min|minute|minuten)\b", re.IGNORECASE
)


def _value(token: str) -> float:
    text = token.strip().lower().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return float(_NUMBER_WORDS.get(text, 0))


def parse_minutes(text: str, default: int = 0) -> int:
    total = 0.0
    for match in _HOUR_RE.finditer(text or ""):
        total += _value(match.group(1)) * 60
    for match in _MIN_RE.finditer(text or ""):
        total += _value(match.group(1))
    if total <= 0:
        return default
    return int(max(1, min(round(total), 24 * 60)))


class ResearchService:
    def __init__(self) -> None:
        self._store = ResearchStore()
        self._engines: dict[str, ResearchEngine] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def boot(self) -> list[str]:
        return self._store.mark_interrupted()

    def _defaults(self, provider: str | None, model: str | None) -> tuple[str, str]:
        settings = get_settings()
        chosen = provider or ""
        chosen_model = model or ""
        if not chosen or not chosen_model:
            try:
                from app.services.settings_service import get_settings_service

                data = get_settings_service().get()
            except Exception:
                data = {}
            chosen = chosen or str(data.get("provider") or settings.default_provider)
            chosen_model = chosen_model or str(data.get("model") or settings.jon_model)
        return chosen, chosen_model

    async def start(
        self,
        topic: str,
        minutes: int = 0,
        provider: str | None = None,
        model: str | None = None,
        depth: str = "normal",
    ) -> dict[str, Any]:
        text = topic.strip()
        if not text:
            raise ValueError("Ohne Thema kann Jon nicht lernen")
        settings = get_settings()
        chosen, chosen_model = self._defaults(provider, model)
        budget = minutes if minutes > 0 else parse_minutes(text, 0)
        if budget <= 0:
            budget = settings.research_default_minutes
        task = ResearchTask.create(text, budget, chosen, chosen_model, depth)
        self._store.save(task)
        await self._launch(task)
        return task.to_dict()

    async def _launch(self, task: ResearchTask) -> None:
        async with self._lock:
            engine = ResearchEngine(task, self._store)
            self._engines[task.id] = engine
            runner = asyncio.create_task(engine.run())
            self._tasks[task.id] = runner
            runner.add_done_callback(lambda _: self._tasks.pop(task.id, None))

    async def resume_task(self, task_id: str) -> dict[str, Any]:
        engine = self._engines.get(task_id)
        if engine is not None and task_id in self._tasks:
            engine.resume()
            return engine.task.to_dict()
        stored = self._store.load(task_id)
        if stored is None:
            raise KeyError(task_id)
        if stored.status not in RESUMABLE_STATES:
            return stored.to_dict()
        for subtopic in stored.subtopics:
            if subtopic.status in ("uebersprungen", "laeuft", "leer"):
                subtopic.status = "offen"
        if stored.remaining_s() < MIN_RESUME_S and any(
            subtopic.status == "offen" for subtopic in stored.subtopics
        ):
            stored.minutes += max(
                1, int((MIN_RESUME_S - stored.remaining_s()) / 60) + 1
            )
        stored.status = STATUS_RUNNING
        stored.error = ""
        stored.ended_at = 0.0
        self._store.save(stored)
        await self._launch(stored)
        return stored.to_dict()

    def pause(self, task_id: str) -> dict[str, Any]:
        engine = self._engines.get(task_id)
        if engine is None:
            raise KeyError(task_id)
        engine.pause()
        return engine.task.to_dict()

    def resume(self, task_id: str) -> dict[str, Any]:
        engine = self._engines.get(task_id)
        if engine is None:
            raise KeyError(task_id)
        engine.resume()
        return engine.task.to_dict()

    def stop(self, task_id: str) -> dict[str, Any]:
        engine = self._engines.get(task_id)
        if engine is None:
            stored = self._store.load(task_id)
            if stored is None:
                raise KeyError(task_id)
            return stored.to_dict()
        engine.stop()
        return engine.task.to_dict()

    def get(self, task_id: str) -> dict[str, Any]:
        engine = self._engines.get(task_id)
        if engine is not None:
            return engine.task.to_dict()
        stored = self._store.load(task_id)
        if stored is None:
            raise KeyError(task_id)
        return stored.to_dict()

    def list(self) -> list[dict[str, Any]]:
        live = {task_id: engine.task for task_id, engine in self._engines.items()}
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        for task in self._store.all():
            current = live.get(task.id, task)
            entries.append(current.summary_dict())
            seen.add(task.id)
        for task_id, task in live.items():
            if task_id not in seen:
                entries.append(task.summary_dict())
        entries.sort(key=lambda item: item["erstellt_at"], reverse=True)
        return entries

    def active(self) -> list[dict[str, Any]]:
        return [
            engine.task.to_dict()
            for engine in self._engines.values()
            if engine.task.status in ACTIVE_STATES
        ]

    def delete(self, task_id: str) -> bool:
        engine = self._engines.get(task_id)
        if engine is not None:
            engine.stop()
            runner = self._tasks.get(task_id)
            if runner is not None:
                runner.cancel()
            self._engines.pop(task_id, None)
        return self._store.delete(task_id)

    def files(self, task_id: str) -> list[dict[str, Any]]:
        task = self._engines.get(task_id)
        slug = task.task.slug if task else None
        if slug is None:
            stored = self._store.load(task_id)
            if stored is None:
                raise KeyError(task_id)
            slug = stored.slug
        return storage.list_files(slug)

    def read_file(self, task_id: str, name: str) -> str:
        engine = self._engines.get(task_id)
        if engine is not None:
            slug = engine.task.slug
        else:
            stored = self._store.load(task_id)
            if stored is None:
                raise KeyError(task_id)
            slug = stored.slug
        return storage.read_file(slug, name)

    async def stream(self, task_id: str):
        engine = self._engines.get(task_id)
        if engine is None:
            yield self.get(task_id)
            return
        queue = engine.subscribe()
        try:
            yield engine.task.to_dict()
            while True:
                try:
                    snapshot = await asyncio.wait_for(queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    snapshot = engine.task.to_dict()
                yield snapshot
                if snapshot["status"] not in ACTIVE_STATES:
                    return
        finally:
            engine.unsubscribe(queue)

    def status_text(self, task: dict[str, Any]) -> str:
        remaining = int(task.get("verbleibend_s") or 0)
        minutes, seconds = divmod(remaining, 60)
        hours, minutes = divmod(minutes, 60)
        clock = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        percent = int(round(float(task.get("fortschritt") or 0.0) * 100))
        return (
            f"{task.get('titel')} · {task.get('status')} · {percent}% · "
            f"noch {clock}"
        )


_service: ResearchService | None = None


def get_research_service() -> ResearchService:
    global _service
    if _service is None:
        _service = ResearchService()
    return _service
