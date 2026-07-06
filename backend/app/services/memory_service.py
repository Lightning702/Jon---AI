from __future__ import annotations

from app.db.database import session_scope
from app.db.models import Memory


class MemoryService:
    def add(self, content: str, source: str = "chat") -> dict:
        text = content.strip()
        if not text:
            return {"error": "leerer Inhalt"}
        with session_scope() as session:
            existing = (
                session.query(Memory)
                .filter(Memory.content == text)
                .first()
            )
            if existing:
                return {"id": existing.id, "content": existing.content, "duplicate": True}
            mem = Memory(content=text[:1000], source=source)
            session.add(mem)
            session.flush()
            return {"id": mem.id, "content": mem.content, "duplicate": False}

    def list(self, limit: int = 200) -> list[dict]:
        with session_scope() as session:
            rows = (
                session.query(Memory)
                .order_by(Memory.created_at.asc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "content": r.content,
                    "source": r.source,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    def search(self, query: str, limit: int = 50) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return self.list(limit)
        return [m for m in self.list() if q in m["content"].lower()][:limit]

    def delete(self, memory_id: str) -> bool:
        with session_scope() as session:
            mem = session.get(Memory, memory_id)
            if mem is None:
                return False
            session.delete(mem)
            return True

    def forget(self, query: str) -> int:
        q = query.strip().lower()
        if not q:
            return 0
        removed = 0
        with session_scope() as session:
            for mem in session.query(Memory).all():
                if q in mem.content.lower():
                    session.delete(mem)
                    removed += 1
        return removed

    def clear(self) -> int:
        with session_scope() as session:
            count = session.query(Memory).count()
            session.query(Memory).delete()
            return count

    def prompt_block(self, limit: int = 60) -> str:
        items = self.list(limit)
        if not items:
            return ""
        lines = "\n".join(f"- {m['content']}" for m in items)
        return (
            "Das weisst du dauerhaft ueber den Nutzer und aus frueheren Gespraechen "
            "(nutze es aktiv, ohne es staendig zu erwaehnen):\n" + lines
        )
