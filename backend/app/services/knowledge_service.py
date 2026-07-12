from __future__ import annotations

import re
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR

KNOWLEDGE_DB = DATA_DIR / "knowledge.db"

TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".html",
    ".css",
    ".csv",
    ".log",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".java",
    ".c",
    ".cpp",
    ".cs",
    ".sh",
    ".bat",
    ".ps1",
}


def _chunk_text(text: str, size: int = 1500, overlap: int = 200) -> list[str]:
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind("\n", start + size // 2, end)
            if cut == -1:
                cut = text.rfind(" ", start + size // 2, end)
            if cut > start:
                end = cut
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return parts


class KnowledgeService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fts = True
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(KNOWLEDGE_DB, timeout=10)

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS documents ("
                "id TEXT PRIMARY KEY, title TEXT, source TEXT, kind TEXT, "
                "chunks INTEGER, chars INTEGER, created_at TEXT)"
            )
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5("
                    "doc_id UNINDEXED, title, content)"
                )
            except sqlite3.OperationalError:
                self._fts = False
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS chunks ("
                    "doc_id TEXT, title TEXT, content TEXT)"
                )

    def _read_source(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n\n".join(
                page.extract_text() or "" for page in reader.pages[:100]
            )
        return path.read_bytes()[:500_000].decode("utf-8", errors="replace")

    def _store(self, title: str, source: str, kind: str, text: str) -> dict:
        pieces = _chunk_text(text)
        if not pieces:
            return {"error": f"Kein lesbarer Text in {title}"}
        doc_id = uuid.uuid4().hex[:12]
        with self._lock, self._connect() as conn:
            old = conn.execute(
                "SELECT id FROM documents WHERE source = ? AND source != ''",
                (source,),
            ).fetchall()
            for (old_id,) in old:
                conn.execute("DELETE FROM chunks WHERE doc_id = ?", (old_id,))
                conn.execute("DELETE FROM documents WHERE id = ?", (old_id,))
            conn.execute(
                "INSERT INTO documents (id, title, source, kind, chunks, chars, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    doc_id,
                    title,
                    source,
                    kind,
                    len(pieces),
                    len(text),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            conn.executemany(
                "INSERT INTO chunks (doc_id, title, content) VALUES (?, ?, ?)",
                [(doc_id, title, piece) for piece in pieces],
            )
        return {
            "id": doc_id,
            "title": title,
            "chunks": len(pieces),
            "chars": len(text),
        }

    def learn_path(self, path_str: str) -> dict:
        path = Path(path_str).expanduser()
        if not path.exists():
            return {"error": f"Pfad nicht gefunden: {path_str}"}
        if path.is_dir():
            learned: list[dict] = []
            skipped = 0
            for item in sorted(path.rglob("*")):
                if len(learned) >= 50:
                    skipped += 1
                    continue
                if not item.is_file():
                    continue
                if item.suffix.lower() not in TEXT_SUFFIXES | {".pdf"}:
                    continue
                if any(part in {"node_modules", ".git", "__pycache__"} for part in item.parts):
                    continue
                try:
                    text = self._read_source(item)
                except Exception:
                    continue
                result = self._store(item.name, str(item), item.suffix.lstrip("."), text)
                if "error" not in result:
                    learned.append(result)
            return {
                "folder": str(path),
                "learned": len(learned),
                "documents": [d["title"] for d in learned],
                "skipped": skipped,
            }
        try:
            text = self._read_source(path)
        except Exception as exc:
            return {"error": f"Konnte {path.name} nicht lesen: {exc}"}
        return self._store(path.name, str(path), path.suffix.lstrip(".") or "text", text)

    def learn_text(self, text: str, title: str = "") -> dict:
        clean_title = title.strip() or f"Notiz vom {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        return self._store(clean_title, "", "note", text)

    def search(self, query: str, limit: int = 6) -> list[dict]:
        tokens = re.findall(r"[\wÀ-ſ]+", query.lower())
        if not tokens:
            return []
        results: list[dict] = []
        with self._lock, self._connect() as conn:
            if self._fts:
                match = " OR ".join(f'"{t}"' for t in tokens[:12])
                try:
                    rows = conn.execute(
                        "SELECT doc_id, title, content FROM chunks "
                        "WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?",
                        (match, max(1, min(int(limit), 12))),
                    ).fetchall()
                except sqlite3.OperationalError:
                    rows = []
            else:
                rows = []
            if not rows:
                like = f"%{tokens[0]}%"
                rows = conn.execute(
                    "SELECT doc_id, title, content FROM chunks "
                    "WHERE lower(content) LIKE ? OR lower(title) LIKE ? LIMIT ?",
                    (like, like, max(1, min(int(limit), 12))),
                ).fetchall()
        for doc_id, title, content in rows:
            results.append(
                {"doc_id": doc_id, "title": title, "text": content[:1200]}
            )
        return results

    def list(self) -> list[dict]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, source, kind, chunks, chars, created_at "
                "FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "id": r[0],
                "title": r[1],
                "source": r[2],
                "kind": r[3],
                "chunks": r[4],
                "chars": r[5],
                "created_at": r[6],
            }
            for r in rows
        ]

    def forget(self, ref: str) -> int:
        ref = ref.strip()
        if not ref:
            return 0
        removed = 0
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM documents WHERE id = ? OR lower(title) LIKE ?",
                (ref, f"%{ref.lower()}%"),
            ).fetchall()
            for (doc_id,) in rows:
                conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
                conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                removed += 1
        return removed

    def prompt_block(self, limit: int = 15) -> str:
        docs = self.list()
        if not docs:
            return ""
        titles = ", ".join(d["title"] for d in docs[:limit])
        more = f" (und {len(docs) - limit} weitere)" if len(docs) > limit else ""
        return (
            "Du hast eine lokale Wissensbasis mit gelernten Dokumenten: "
            f"{titles}{more}. Wenn eine Frage dazu passen koennte, rufe zuerst "
            "ask_knowledge mit passenden Suchbegriffen auf und stuetze deine "
            "Antwort auf die Fundstellen."
        )


_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service
