from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from app.core.config import get_settings

from . import stages, storage
from .models import (
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_PAUSED,
    STATUS_PLANNING,
    STATUS_RUNNING,
    STATUS_STOPPED,
    LogEntry,
    ResearchTask,
    SourceRecord,
    Subtopic,
    slugify,
)
from .store import ResearchStore
from .web import UnsafeUrl, domain_of, get_research_web

MIN_TAIL_S = 55.0


class ResearchEngine:
    def __init__(self, task: ResearchTask, store: ResearchStore) -> None:
        self.task = task
        self._store = store
        self._gate = asyncio.Event()
        self._gate.set()
        self._stop = False
        self._web = get_research_web()
        self._settings = get_settings()
        self._listeners: set[asyncio.Queue] = set()
        self._notes: dict[str, list[dict[str, Any]]] = {}

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._listeners.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._listeners.discard(queue)

    def _publish(self) -> None:
        snapshot = self.task.to_dict()
        for queue in list(self._listeners):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                continue

    def log(self, kind: str, icon: str, title: str, detail: str = "") -> None:
        self.task.log.append(
            LogEntry(ts=time.time(), kind=kind, icon=icon, title=title, detail=detail)
        )
        if len(self.task.log) > 600:
            self.task.log = self.task.log[-400:]
        self._save()

    def _save(self) -> None:
        self._store.save(self.task)
        self._publish()

    def _stage(self, text: str) -> None:
        self.task.stage = text
        self._save()

    def pause(self) -> None:
        if self.task.status != STATUS_RUNNING:
            return
        self.task.consumed_s = self.task.elapsed_s()
        self.task.started_at = 0.0
        self.task.status = STATUS_PAUSED
        self._gate.clear()
        self.log("pause", "⏸️", "Recherche pausiert", "Fortschritt ist gespeichert")

    def resume(self) -> None:
        if self.task.status != STATUS_PAUSED:
            return
        self.task.started_at = time.time()
        self.task.status = STATUS_RUNNING
        self._gate.set()
        self.log("resume", "▶️", "Recherche fortgesetzt", "")

    def stop(self) -> None:
        self._stop = True
        self._gate.set()

    @property
    def stopping(self) -> bool:
        return self._stop

    async def _checkpoint(self) -> bool:
        await self._gate.wait()
        if self._stop:
            return False
        return self.task.remaining_s() > MIN_TAIL_S

    def _time_left(self) -> float:
        return self.task.remaining_s()

    def _source_budget(self) -> int:
        base = self._settings.research_sources_per_topic
        depth = {"schnell": -2, "normal": 0, "tief": 2}.get(self.task.depth, 0)
        return max(2, base + depth)

    async def run(self) -> None:
        try:
            self.task.status = STATUS_RUNNING
            self.task.started_at = time.time()
            self.task.error = ""
            self.log(
                "start",
                "🚀",
                f"Lernauftrag: {self.task.topic}",
                f"Zeitbudget {self.task.minutes} Minuten",
            )
            if not self.task.subtopics:
                await self._analyze()
            else:
                self.log(
                    "resume",
                    "🔁",
                    "Recherche wird fortgesetzt",
                    f"{len(self.task.subtopics)} Unterthemen aus dem gespeicherten Stand",
                )
            await self._work()
            await self._finish()
        except asyncio.CancelledError:
            self.task.consumed_s = self.task.elapsed_s()
            self.task.started_at = 0.0
            self.task.status = STATUS_STOPPED
            self.task.stage = "Abgebrochen — Fortschritt gespeichert"
            self._save()
            raise
        except Exception as exc:
            self.task.consumed_s = self.task.elapsed_s()
            self.task.started_at = 0.0
            self.task.status = STATUS_ERROR
            self.task.error = str(exc)
            self.task.stage = "Fehler"
            self.log("fehler", "⚠️", "Recherche abgebrochen", str(exc)[:400])

    async def _analyze(self) -> None:
        self.task.status = STATUS_PLANNING
        self._stage("Thema wird analysiert")
        self.log("plan", "🧭", "Thema wird analysiert", self.task.topic)
        data = await stages.analyze_topic(
            self.task.topic,
            self.task.minutes,
            self.task.depth,
            self._settings.research_max_subtopics,
            self.task.provider,
            self.task.model,
        )
        self.task.title = str(data.get("titel") or self.task.topic).strip()
        self.task.slug = slugify(self.task.title or self.task.topic)
        self.task.summary = str(data.get("zusammenfassung") or "").strip()
        raw_topics = data.get("unterthemen") or []
        subtopics: list[Subtopic] = []
        for item in raw_topics:
            if not isinstance(item, dict):
                continue
            title = str(item.get("titel") or "").strip()
            if not title:
                continue
            subtopics.append(
                Subtopic(
                    id=uuid.uuid4().hex[:8],
                    title=title,
                    question=str(item.get("frage") or title).strip(),
                    importance=int(item.get("wichtigkeit") or 3),
                )
            )
        subtopics.sort(key=lambda sub: -sub.importance)
        self.task.subtopics = subtopics[: self._settings.research_max_subtopics]
        self.task.status = STATUS_RUNNING
        self._stage("Recherche-Plan steht")
        self.log(
            "plan",
            "🗺️",
            "Research-Plan erstellt",
            " · ".join(sub.title for sub in self.task.subtopics),
        )

    async def _work(self) -> None:
        pending = [sub for sub in self.task.subtopics if sub.status == "offen"]
        for index, sub in enumerate(pending):
            if not await self._checkpoint():
                break
            share = self._time_left() / max(1, len(pending) - index)
            await self._research_subtopic(sub, share)
        for sub in self.task.subtopics:
            if sub.status == "offen":
                sub.status = "uebersprungen"
        self._save()

    async def _research_subtopic(self, sub: Subtopic, share_s: float) -> None:
        self.task.current_subtopic = sub.title
        sub.status = "laeuft"
        deadline = time.time() + max(60.0, share_s)
        self._stage(f"Unterthema: {sub.title}")
        self.log("thema", "📌", sub.title, sub.question)
        queries = await stages.plan_queries(
            self.task.topic, sub.title, sub.question, self.task.provider, self.task.model
        )
        notes: list[dict[str, Any]] = self._notes.setdefault(sub.id, [])
        used_urls = {note["url"] for note in notes}
        budget = self._source_budget()
        candidates: list[dict] = []
        for query in queries:
            if not await self._checkpoint():
                break
            self.log("suche", "🔎", "Suche läuft", query)
            try:
                found = await self._web.search(query, 6)
            except Exception as exc:
                self.log("fehler", "⚠️", "Suche fehlgeschlagen", str(exc)[:200])
                continue
            for hit in found:
                if hit["url"] not in used_urls and all(
                    hit["url"] != item["url"] for item in candidates
                ):
                    candidates.append(hit)
            if len(candidates) >= budget * 2:
                break
        seen_domains: dict[str, int] = {}
        for hit in candidates:
            if len(notes) >= budget or time.time() > deadline:
                break
            if not await self._checkpoint():
                break
            domain = domain_of(hit["url"])
            if seen_domains.get(domain, 0) >= 2:
                continue
            seen_domains[domain] = seen_domains.get(domain, 0) + 1
            note = await self._read_source(sub, hit)
            if note is not None:
                notes.append(note)
                used_urls.add(hit["url"])
        if not notes:
            sub.status = "leer"
            sub.findings = "Keine brauchbare Quelle gefunden."
            self.log("leer", "🚫", f"{sub.title}: keine brauchbare Quelle", "")
            self._save()
            return
        self.log(
            "vergleich",
            "⚖️",
            "Quellen werden verglichen",
            f"{len(notes)} Quellen zu {sub.title}",
        )
        validation = await stages.validate_findings(
            sub.title, notes, self.task.provider, self.task.model
        )
        conflicts = [str(item) for item in validation.get("widersprueche") or []]
        needs_more = bool(validation.get("braucht_mehr_quellen")) or bool(conflicts)
        if needs_more and await self._checkpoint() and time.time() < deadline:
            self.log(
                "gegenpruefung",
                "🔬",
                "Widerspruch gefunden — Jon prüft nach",
                conflicts[0][:200] if conflicts else "Quellenlage noch dünn",
            )
            extra_query = f"{self.task.topic} {sub.title} Kritik Belege"
            try:
                extra = await self._web.search(extra_query, 4)
            except Exception:
                extra = []
            for hit in extra:
                if len(notes) >= budget + 3 or time.time() > deadline:
                    break
                if hit["url"] in used_urls:
                    continue
                note = await self._read_source(sub, hit)
                if note is not None:
                    notes.append(note)
                    used_urls.add(hit["url"])
            validation = await stages.validate_findings(
                sub.title, notes, self.task.provider, self.task.model
            )
            conflicts = [str(item) for item in validation.get("widersprueche") or []]
        sub.conflicts = conflicts
        sub.confidence = str(validation.get("vertrauen") or "mittel")
        self._stage(f"Wissen wird geschrieben: {sub.title}")
        markdown = await stages.write_subtopic(
            self.task.topic,
            sub.title,
            sub.question,
            notes,
            validation,
            self.task.provider,
            self.task.model,
        )
        if not markdown:
            sub.status = "leer"
            self._save()
            return
        file_name = storage.write_file(
            self.task.slug, slugify(sub.title, 'thema'), markdown
        )
        sub.file = file_name
        sub.status = "fertig"
        sub.findings = " ".join(
            str(item) for item in (validation.get("gesichert") or [])[:4]
        )
        sub.sources = [note["url"] for note in notes]
        if file_name not in self.task.files:
            self.task.files.append(file_name)
        self.log("speichern", "💾", file_name, "Gespeichert")
        self._index_file(file_name, sub.title, markdown)
        self._save()

    async def _read_source(self, sub: Subtopic, hit: dict) -> dict[str, Any] | None:
        url = str(hit.get("url") or "")
        record = SourceRecord(
            url=url,
            title=str(hit.get("title") or url),
            domain=domain_of(url),
            subtopic=sub.title,
            fetched_at=time.time(),
        )
        self.task.sources.append(record)
        self.log("quelle", "🌐", record.domain or url, "Quelle wird geöffnet")
        try:
            page = await self._web.fetch(url, self._settings.research_page_chars)
        except UnsafeUrl as exc:
            record.status = "verworfen"
            record.reason = str(exc)
            self.log("uebersprungen", "🛡️", record.domain, str(exc))
            self._save()
            return None
        except Exception as exc:
            record.status = "fehler"
            record.reason = type(exc).__name__
            self.log(
                "fehler", "⚠️", record.domain or url, "Nicht erreichbar — nächste Quelle"
            )
            self._save()
            return None
        record.chars = int(page.get("chars") or 0)
        if record.chars < 400:
            record.status = "verworfen"
            record.reason = "Zu wenig Text"
            self.log("uebersprungen", "➖", record.domain, "Zu wenig Inhalt")
            self._save()
            return None
        if page.get("title"):
            record.title = str(page["title"])[:180]
        self.log("lesen", "📖", record.domain, f"{record.chars} Zeichen werden gelesen")
        analysis = await stages.analyze_source(
            self.task.topic,
            sub.title,
            sub.question,
            record.title,
            url,
            str(page.get("text") or ""),
            self.task.provider,
            self.task.model,
        )
        relevance = int(analysis.get("relevanz") or 0)
        if not analysis.get("brauchbar") or relevance < 4:
            record.status = "verworfen"
            record.reason = f"Relevanz {relevance}/10"
            self.log(
                "uebersprungen",
                "➖",
                record.domain,
                "Nicht brauchbar — Jon nimmt die nächste Quelle",
            )
            self._save()
            return None
        record.status = "genutzt"
        record.summary = str(analysis.get("zusammenfassung") or "")[:600]
        record.reason = f"Relevanz {relevance}/10"
        self.log("analyse", "🧠", record.domain, "Wissen wird extrahiert")
        self._save()
        return {
            "url": url,
            "domain": record.domain,
            "title": record.title,
            "zusammenfassung": analysis.get("zusammenfassung", ""),
            "kernaussagen": analysis.get("kernaussagen", []),
            "zahlen_und_daten": analysis.get("zahlen_und_daten", []),
            "begriffe": analysis.get("begriffe", []),
            "unsicher": analysis.get("unsicher", []),
            "relevanz": relevance,
        }

    def _index_file(self, file_name: str, title: str, content: str) -> None:
        try:
            from app.services.knowledge_service import get_knowledge_service

            get_knowledge_service().learn_text(
                content, f"{self.task.title or self.task.topic} — {title}"
            )
        except Exception:
            pass

    async def _finish(self) -> None:
        done = [sub for sub in self.task.subtopics if sub.status == "fertig"]
        self.task.current_subtopic = ""
        if done:
            self._stage("Wissen wird zusammengefasst")
            listing = [
                {
                    "titel": sub.title,
                    "datei": sub.file,
                    "frage": sub.question,
                    "vertrauen": sub.confidence,
                }
                for sub in done
            ]
            try:
                overview = await stages.write_overview(
                    self.task.topic,
                    self.task.title or self.task.topic,
                    listing,
                    self.task.provider,
                    self.task.model,
                )
                readme = storage.write_index(self.task, overview)
                if readme not in self.task.files:
                    self.task.files.append(readme)
                self.log("speichern", "💾", readme, "Übersicht gespeichert")
            except Exception as exc:
                self.log("fehler", "⚠️", "README", str(exc)[:200])
            try:
                sources_file = storage.write_sources(self.task)
                if sources_file not in self.task.files:
                    self.task.files.append(sources_file)
                self.log("speichern", "💾", sources_file, "Quellen gespeichert")
            except Exception as exc:
                self.log("fehler", "⚠️", "sources.md", str(exc)[:200])
            self._stage("Skill wird erstellt")
            try:
                skill_text = await stages.write_skill(
                    self.task.topic,
                    self.task.title or self.task.topic,
                    self.task.slug,
                    self.task.summary,
                    listing,
                    [source.to_dict() for source in self.task.sources],
                    self.task.provider,
                    self.task.model,
                )
                skill_file = storage.write_file(self.task.slug, "skill", skill_text)
                if skill_file not in self.task.files:
                    self.task.files.append(skill_file)
                self.task.skill = self.task.slug
                self.log(
                    "skill",
                    "🧠",
                    self.task.slug,
                    "Skill erstellt — Jon nutzt das Wissen ab sofort",
                )
                self._index_file(skill_file, "Skill", skill_text)
            except Exception as exc:
                self.log("fehler", "⚠️", "Skill", str(exc)[:200])
            try:
                self.task.summary = await stages.final_summary(
                    self.task.topic, listing, self.task.provider, self.task.model
                )
            except Exception:
                pass
        self.task.consumed_s = self.task.elapsed_s()
        self.task.started_at = 0.0
        self.task.ended_at = time.time()
        if self._stop and not done:
            self.task.status = STATUS_STOPPED
            self.task.stage = "Abgebrochen — Fortschritt gespeichert"
        elif self._stop:
            self.task.status = STATUS_STOPPED
            self.task.stage = f"Abgebrochen · {len(done)} Unterthemen gesichert"
        else:
            self.task.status = STATUS_DONE
            self.task.stage = "Recherche abgeschlossen"
        self.log(
            "fertig",
            "✅",
            "Research abgeschlossen",
            f"{len(done)} Unterthemen · {len(self.task.files)} Dateien · "
            f"{sum(1 for s in self.task.sources if s.status == 'genutzt')} Quellen",
        )
