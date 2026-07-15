from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime

from app.core.config import DATA_DIR
from app.services.llm import complete
from app.services.settings_service import get_settings_service

JOURNAL_FILE = DATA_DIR / "journal.json"

SUMMARY_SYSTEM = (
    "Du hilfst dem Nutzer, sein gesprochenes Tagebuch zu ordnen. Aus seinem Text "
    "machst du einen kurzen Titel (max 6 Wörter) und 2-4 Themen-Stichworte. "
    "Antworte AUSSCHLIESSLICH mit JSON: "
    '{"title": "...", "tags": ["...", "..."], "mood": "gut|neutral|schlecht"}'
)

SEARCH_SYSTEM = (
    "Du beantwortest eine Frage des Nutzers über seine eigenen Tagebucheinträge. "
    "Nutze nur die gegebenen Einträge, erfinde nichts. Antworte kurz, warm und "
    "persönlich auf Deutsch. Wenn nichts passt, sag das ehrlich."
)


class JournalService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries = self._load()

    def _load(self) -> list[dict]:
        try:
            data = json.loads(JOURNAL_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _save(self) -> None:
        try:
            JOURNAL_FILE.write_text(
                json.dumps(self._entries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    async def add(self, text: str) -> dict:
        body = text.strip()
        if len(body) < 3:
            return {"error": "Der Eintrag ist zu kurz."}
        title, tags, mood = "Eintrag", [], "neutral"
        try:
            import re

            provider, model = get_settings_service().selection()
            raw = await complete(
                SUMMARY_SYSTEM,
                body[:4000],
                provider=provider or None,
                model=model or None,
                max_tokens=200,
                temperature=0.4,
            )
            match = re.search(r"\{.*\}", raw, re.S)
            if match:
                data = json.loads(match.group(0))
                title = str(data.get("title") or title)[:80]
                tags = [str(t)[:24] for t in (data.get("tags") or [])][:4]
                mood = str(data.get("mood") or "neutral")
        except Exception:
            pass
        now = datetime.now()
        entry = {
            "id": uuid.uuid4().hex,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "title": title,
            "tags": tags,
            "mood": mood,
            "text": body,
        }
        with self._lock:
            self._entries.append(entry)
            self._save()
        return entry

    def list(self, limit: int = 100) -> list[dict]:
        with self._lock:
            return list(reversed(self._entries[-limit:]))

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            before = len(self._entries)
            self._entries = [e for e in self._entries if e["id"] != entry_id]
            if len(self._entries) != before:
                self._save()
                return True
        return False

    async def ask(self, query: str) -> dict:
        q = query.strip()
        if not q:
            return {"error": "Keine Frage angegeben."}
        with self._lock:
            entries = list(self._entries)
        if not entries:
            return {"answer": "Du hast noch keine Tagebucheinträge."}
        low = q.lower()
        words = [w for w in low.split() if len(w) > 2]
        scored = []
        for e in entries:
            hay = (e["text"] + " " + e["title"] + " " + " ".join(e["tags"])).lower()
            score = sum(1 for w in words if w in hay)
            scored.append((score, e))
        scored.sort(key=lambda s: s[0], reverse=True)
        picked = [e for score, e in scored if score > 0][:8] or entries[-8:]
        context = "\n\n".join(
            f"[{e['date']} {e['time']}] {e['title']}\n{e['text'][:600]}" for e in picked
        )
        provider, model = get_settings_service().selection()
        try:
            answer = await complete(
                SEARCH_SYSTEM,
                f"Einträge:\n{context}\n\nFrage: {q}",
                provider=provider or None,
                model=model or None,
                max_tokens=600,
                temperature=0.6,
            )
        except Exception as exc:
            return {"error": f"Suche fehlgeschlagen: {exc}"}
        return {"answer": answer.strip() or "Dazu finde ich nichts."}


_service: JournalService | None = None


def get_journal_service() -> JournalService:
    global _service
    if _service is None:
        _service = JournalService()
    return _service
