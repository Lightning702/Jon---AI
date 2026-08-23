from __future__ import annotations

import re
import time
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

STATUS_PLANNING = "planung"
STATUS_RUNNING = "laeuft"
STATUS_PAUSED = "pausiert"
STATUS_DONE = "fertig"
STATUS_STOPPED = "abgebrochen"
STATUS_INTERRUPTED = "unterbrochen"
STATUS_ERROR = "fehler"

ACTIVE_STATES = (STATUS_PLANNING, STATUS_RUNNING, STATUS_PAUSED)
RESUMABLE_STATES = (STATUS_PAUSED, STATUS_STOPPED, STATUS_INTERRUPTED, STATUS_ERROR)

_SLUG_MAP = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
    "Ä": "ae",
    "Ö": "oe",
    "Ü": "ue",
}


def slugify(value: str, fallback: str = "thema") -> str:
    text = value.strip().lower()
    for source, target in _SLUG_MAP.items():
        text = text.replace(source, target)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    if not text:
        text = fallback
    if not text[0].isalnum():
        text = f"t{text}"
    return text[:48].rstrip("-") or fallback


@dataclass
class LogEntry:
    ts: float
    kind: str
    icon: str
    title: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceRecord:
    url: str
    title: str
    domain: str
    status: str = "offen"
    chars: int = 0
    subtopic: str = ""
    summary: str = ""
    reason: str = ""
    fetched_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Subtopic:
    id: str
    title: str
    question: str
    importance: int = 3
    status: str = "offen"
    file: str = ""
    sources: list[str] = field(default_factory=list)
    findings: str = ""
    conflicts: list[str] = field(default_factory=list)
    confidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchTask:
    id: str
    topic: str
    slug: str
    title: str = ""
    summary: str = ""
    minutes: int = 45
    depth: str = "normal"
    provider: str = ""
    model: str = ""
    status: str = STATUS_PLANNING
    stage: str = "Auftrag angenommen"
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    ended_at: float = 0.0
    consumed_s: float = 0.0
    current_subtopic: str = ""
    subtopics: list[Subtopic] = field(default_factory=list)
    sources: list[SourceRecord] = field(default_factory=list)
    log: list[LogEntry] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    skill: str = ""
    error: str = ""

    @staticmethod
    def create(
        topic: str,
        minutes: int,
        provider: str,
        model: str,
        depth: str = "normal",
    ) -> "ResearchTask":
        return ResearchTask(
            id=uuid.uuid4().hex[:12],
            topic=topic.strip(),
            slug=slugify(topic),
            title=topic.strip(),
            minutes=max(1, int(minutes)),
            depth=depth,
            provider=provider,
            model=model,
        )

    @property
    def budget_s(self) -> float:
        return float(self.minutes) * 60.0

    def elapsed_s(self, now: float | None = None) -> float:
        moment = now if now is not None else time.time()
        running = 0.0
        if self.status == STATUS_RUNNING and self.started_at:
            running = max(0.0, moment - self.started_at)
        return self.consumed_s + running

    def remaining_s(self, now: float | None = None) -> float:
        return max(0.0, self.budget_s - self.elapsed_s(now))

    def progress(self) -> float:
        if not self.subtopics:
            return 0.05 if self.status in ACTIVE_STATES else 0.0
        done = sum(1 for sub in self.subtopics if sub.status in ("fertig", "uebersprungen"))
        by_topic = done / len(self.subtopics)
        by_time = min(1.0, self.elapsed_s() / self.budget_s) if self.budget_s else 0.0
        if self.status in (STATUS_DONE,):
            return 1.0
        return max(0.02, min(0.99, max(by_topic, by_time * 0.85)))

    def to_dict(self) -> dict[str, Any]:
        now = time.time()
        return {
            "id": self.id,
            "thema": self.topic,
            "slug": self.slug,
            "titel": self.title or self.topic,
            "zusammenfassung": self.summary,
            "minuten": self.minutes,
            "tiefe": self.depth,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "phase": self.stage,
            "erstellt_at": self.created_at,
            "gestartet_at": self.started_at,
            "beendet_at": self.ended_at,
            "verbraucht_s": round(self.elapsed_s(now), 1),
            "verbleibend_s": round(self.remaining_s(now), 1),
            "fortschritt": round(self.progress(), 4),
            "aktuelles_thema": self.current_subtopic,
            "unterthemen": [sub.to_dict() for sub in self.subtopics],
            "quellen": [source.to_dict() for source in self.sources],
            "protokoll": [entry.to_dict() for entry in self.log[-160:]],
            "dateien": list(self.files),
            "skill": self.skill,
            "fehler": self.error,
            "ordner": f"skills/{self.slug}",
        }

    def summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "thema": self.topic,
            "titel": self.title or self.topic,
            "slug": self.slug,
            "status": self.status,
            "minuten": self.minutes,
            "verbraucht_s": round(self.elapsed_s(), 1),
            "fortschritt": round(self.progress(), 4),
            "quellen": len(self.sources),
            "dateien": len(self.files),
            "skill": self.skill,
            "erstellt_at": self.created_at,
            "beendet_at": self.ended_at,
            "unterthemen": len(self.subtopics),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ResearchTask":
        task = ResearchTask(
            id=str(data.get("id") or uuid.uuid4().hex[:12]),
            topic=str(data.get("topic") or data.get("thema") or ""),
            slug=str(data.get("slug") or slugify(str(data.get("topic") or "thema"))),
            title=str(data.get("title") or data.get("titel") or ""),
            summary=str(data.get("summary") or data.get("zusammenfassung") or ""),
            minutes=int(data.get("minutes") or data.get("minuten") or 45),
            depth=str(data.get("depth") or data.get("tiefe") or "normal"),
            provider=str(data.get("provider") or ""),
            model=str(data.get("model") or ""),
            status=str(data.get("status") or STATUS_INTERRUPTED),
            stage=str(data.get("stage") or data.get("phase") or ""),
            created_at=float(data.get("created_at") or time.time()),
            started_at=float(data.get("started_at") or 0.0),
            ended_at=float(data.get("ended_at") or 0.0),
            consumed_s=float(data.get("consumed_s") or 0.0),
            current_subtopic=str(data.get("current_subtopic") or ""),
            skill=str(data.get("skill") or ""),
            error=str(data.get("error") or ""),
            files=[str(item) for item in data.get("files") or []],
        )
        task.subtopics = [
            Subtopic(
                id=str(item.get("id") or uuid.uuid4().hex[:8]),
                title=str(item.get("title") or ""),
                question=str(item.get("question") or ""),
                importance=int(item.get("importance") or 3),
                status=str(item.get("status") or "offen"),
                file=str(item.get("file") or ""),
                sources=[str(source) for source in item.get("sources") or []],
                findings=str(item.get("findings") or ""),
                conflicts=[str(c) for c in item.get("conflicts") or []],
                confidence=str(item.get("confidence") or ""),
            )
            for item in data.get("subtopics") or []
        ]
        task.sources = [
            SourceRecord(
                url=str(item.get("url") or ""),
                title=str(item.get("title") or ""),
                domain=str(item.get("domain") or ""),
                status=str(item.get("status") or "offen"),
                chars=int(item.get("chars") or 0),
                subtopic=str(item.get("subtopic") or ""),
                summary=str(item.get("summary") or ""),
                reason=str(item.get("reason") or ""),
                fetched_at=float(item.get("fetched_at") or 0.0),
            )
            for item in data.get("sources") or []
        ]
        task.log = [
            LogEntry(
                ts=float(item.get("ts") or 0.0),
                kind=str(item.get("kind") or "info"),
                icon=str(item.get("icon") or "•"),
                title=str(item.get("title") or ""),
                detail=str(item.get("detail") or ""),
            )
            for item in data.get("log") or []
        ]
        return task

    def storage_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "minutes": self.minutes,
            "depth": self.depth,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "stage": self.stage,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "consumed_s": self.consumed_s,
            "current_subtopic": self.current_subtopic,
            "skill": self.skill,
            "error": self.error,
            "files": list(self.files),
            "subtopics": [sub.to_dict() for sub in self.subtopics],
            "sources": [source.to_dict() for source in self.sources],
            "log": [entry.to_dict() for entry in self.log[-400:]],
        }
