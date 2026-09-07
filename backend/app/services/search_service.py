from __future__ import annotations

import os
from pathlib import Path
from app.core.fehler import leise

SEARCHABLE_SUFFIXES = {
    ".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    ".json", ".html", ".css", ".scss", ".yml", ".yaml", ".toml", ".ini",
    ".java", ".kt", ".cs", ".c", ".h", ".cpp", ".hpp", ".rs", ".go", ".php",
    ".rb", ".sql", ".sh", ".ps1", ".bat", ".env", ".cfg", ".xml", ".dart",
}
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "dist-electron", "build", ".vite", ".next", "target", ".idea", "release",
}
MAX_SCAN_FILES = 2500
MAX_FILE_BYTES = 400_000


def _snippet(text: str, query: str, size: int = 120) -> str:
    low = text.lower()
    pos = low.find(query.lower())
    if pos < 0:
        return text[:size].strip()
    start = max(0, pos - size // 3)
    end = min(len(text), pos + size)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def _roots() -> list[Path]:
    roots: list[Path] = []
    try:
        from app.services.project_service import get_project_service

        for project in get_project_service().list():
            path = Path(str(project.get("root", "")))
            if path.is_dir():
                roots.append(path)
    except Exception as _fehler:
        leise(_fehler, "services/search_service")
    return roots[:8]


def _file_hits(query: str, words: list[str], limit: int) -> list[dict]:
    hits: list[dict] = []
    scanned = 0
    low = query.lower()
    for root in _roots():
        label = root.name
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
            ]
            for name in filenames:
                if scanned >= MAX_SCAN_FILES or len(hits) >= limit:
                    return hits
                path = Path(dirpath) / name
                suffix = path.suffix.lower()
                if suffix not in SEARCHABLE_SUFFIXES:
                    continue
                scanned += 1
                relative = str(path.relative_to(root))
                if low in relative.lower() or any(
                    word in relative.lower() for word in words
                ):
                    hits.append(
                        {
                            "id": str(path),
                            "title": relative,
                            "snippet": label,
                            "path": str(path),
                        }
                    )
                    continue
                try:
                    if path.stat().st_size > MAX_FILE_BYTES:
                        continue
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if low in text.lower():
                    hits.append(
                        {
                            "id": str(path),
                            "title": relative,
                            "snippet": f"{label} · {_snippet(text, query)}",
                            "path": str(path),
                        }
                    )
    return hits


def universal_search(query: str, limit: int = 8) -> dict:
    q = query.strip()
    if len(q) < 2:
        return {"groups": []}
    low = q.lower()
    words = [w for w in low.split() if len(w) > 1]
    groups = []

    def matches(text: str) -> bool:
        t = (text or "").lower()
        return any(w in t for w in words) if words else low in t

    try:
        from app.services.project_service import get_project_service

        hits = []
        for project in get_project_service().search(q, limit):
            hits.append(
                {
                    "id": project["id"],
                    "title": project.get("name", ""),
                    "snippet": " · ".join(
                        part
                        for part in (
                            project.get("technik", ""),
                            project.get("root", ""),
                        )
                        if part
                    ),
                    "path": project.get("root", ""),
                }
            )
        if hits:
            groups.append({"kind": "projekt", "label": "Projekte", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        hits = _file_hits(q, words, limit)
        if hits:
            groups.append({"kind": "datei", "label": "Dateien", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.db.database import session_scope
        from app.db.models import Conversation

        with session_scope() as session:
            hits = []
            convs = session.query(Conversation).order_by(
                Conversation.updated_at.desc()
            ).limit(300).all()
            for conv in convs:
                found = None
                if matches(conv.title):
                    found = conv.title
                else:
                    for m in conv.messages:
                        if matches(m.content):
                            found = _snippet(m.content, q)
                            break
                if found:
                    hits.append(
                        {"id": conv.id, "title": conv.title or "Unterhaltung", "snippet": found}
                    )
                if len(hits) >= limit:
                    break
            if hits:
                groups.append({"kind": "chat", "label": "Unterhaltungen", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.services.memory_service import MemoryService

        hits = [
            {"snippet": m["content"]}
            for m in MemoryService().list(500)
            if matches(m["content"])
        ][:limit]
        if hits:
            groups.append({"kind": "memory", "label": "Gedächtnis", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.services.notes_service import get_notes_service

        hits = [
            {"id": n["id"], "title": n["text"][:60], "snippet": _snippet(n["text"], q)}
            for n in get_notes_service().list()
            if matches(n.get("text", ""))
        ][:limit]
        if hits:
            groups.append({"kind": "notiz", "label": "Notizen", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.services.calendar_service import get_calendar_service

        termine = []
        aufgaben = []
        for entry in get_calendar_service().search(q)[: limit * 2]:
            item = {
                "id": entry["id"],
                "title": entry["title"],
                "snippet": f"{entry['date']} {entry.get('time', '')}".strip()
                + (f" · {entry['note']}" if entry.get("note") else ""),
            }
            if entry.get("kind") == "task":
                aufgaben.append(item)
            else:
                termine.append(item)
        if termine:
            groups.append({"kind": "termin", "label": "Termine", "items": termine[:limit]})
        if aufgaben:
            groups.append({"kind": "aufgabe", "label": "Aufgaben", "items": aufgaben[:limit]})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.services.reminder_service import ReminderService

        hits = [
            {
                "id": r["id"],
                "title": r["text"],
                "snippet": f"{r.get('time', '')} · {r.get('repeat', '')}".strip(" ·"),
            }
            for r in ReminderService().list()
            if matches(r.get("text", ""))
        ][:limit]
        if hits:
            groups.append({"kind": "erinnerung", "label": "Erinnerungen", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.services.journal_service import get_journal_service

        hits = []
        for e in get_journal_service().list(500):
            blob = e["text"] + " " + e["title"] + " " + " ".join(e["tags"])
            if matches(blob):
                hits.append(
                    {
                        "id": e["id"],
                        "title": f"{e['title']} · {e['date']}",
                        "snippet": _snippet(e["text"], q),
                    }
                )
            if len(hits) >= limit:
                break
        if hits:
            groups.append({"kind": "journal", "label": "Tagebuch", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.services.knowledge_service import get_knowledge_service

        docs = get_knowledge_service().search(q, limit)
        hits = []
        for d in docs if isinstance(docs, list) else []:
            title = d.get("title") or d.get("name") or "Dokument"
            snippet = d.get("snippet") or d.get("text") or ""
            hits.append({"title": title, "snippet": str(snippet)[:160]})
        if hits:
            groups.append({"kind": "knowledge", "label": "Wissensbasis", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    try:
        from app.services.inbox_service import get_inbox_service

        hits = []
        for mail in get_inbox_service().feed(10).get("eintraege", []):
            if mail["kategorie"] != "email":
                continue
            blob = f"{mail.get('titel', '')} {mail.get('untertitel', '')} {mail.get('text', '')}"
            if matches(blob):
                hits.append(
                    {
                        "id": mail["id"],
                        "title": mail.get("titel") or mail.get("betreff", ""),
                        "snippet": mail.get("text") or mail.get("untertitel", ""),
                    }
                )
            if len(hits) >= limit:
                break
        if hits:
            groups.append({"kind": "email", "label": "E-Mails", "items": hits})
    except Exception as _fehler:
        leise(_fehler, "services/search_service")

    return {"groups": groups}
