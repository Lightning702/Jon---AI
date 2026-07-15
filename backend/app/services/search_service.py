from __future__ import annotations


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


def universal_search(query: str, limit: int = 8) -> dict:
    q = query.strip()
    if len(q) < 2:
        return {"groups": []}
    low = q.lower()
    words = [w for w in low.split() if len(w) > 1]
    groups = []

    def matches(text: str) -> bool:
        t = text.lower()
        return any(w in t for w in words) if words else low in t

    try:
        from app.db.database import session_scope
        from app.db.models import Conversation, Message

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
    except Exception:
        pass

    try:
        from app.services.memory_service import MemoryService

        hits = [
            {"snippet": m["content"]}
            for m in MemoryService().list(500)
            if matches(m["content"])
        ][:limit]
        if hits:
            groups.append({"kind": "memory", "label": "Gedächtnis", "items": hits})
    except Exception:
        pass

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
    except Exception:
        pass

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
    except Exception:
        pass

    return {"groups": groups}
