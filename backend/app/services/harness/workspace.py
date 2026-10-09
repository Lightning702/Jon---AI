from __future__ import annotations

import difflib
import hashlib
import os
from pathlib import Path

from app.services.coding import IGNORE_DIRS
from app.services.system_service import SystemService

EXCLUDED = set(IGNORE_DIRS) | {".git", ".svn", ".hg", ".ssh", ".aws", ".azure", ".idea"}
MAX_BYTES = 300_000


class Workspace:
    def __init__(self, root: str) -> None:
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Der Arbeitsordner muss ein Verzeichnis sein.")
        self.seen: dict[str, str] = {}
        self.system = SystemService()

    @staticmethod
    def excluded(name: str) -> bool:
        lower = name.lower()
        return lower in EXCLUDED or lower.startswith(".env") or lower in {
            "credentials", "credentials.json", "secrets.json", "access.token",
        } or lower.endswith((".pem", ".key", ".p12", ".pfx"))

    def path(self, value: str) -> Path:
        candidate = self.root / value
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise PermissionError("Pfad liegt außerhalb des Arbeitsordners.")
        for part in candidate.relative_to(self.root).parts:
            if part in ("..", ".") or self.excluded(part):
                raise PermissionError("Geschützter oder ausgeschlossener Pfad.")
        current = candidate
        while current != self.root:
            if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
                raise PermissionError("Verknüpfungen werden nicht bearbeitet.")
            current = current.parent
        if resolved.is_file() and resolved.stat().st_nlink > 1:
            raise PermissionError("Dateien mit mehreren Hardlinks werden nicht bearbeitet.")
        return resolved

    def files(self, directory: str = ".", limit: int = 1500) -> list[str]:
        base = self.path(directory)
        result: list[str] = []
        for parent, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not self.excluded(d) and not (Path(parent) / d).is_symlink() and not (hasattr(Path(parent) / d, "is_junction") and (Path(parent) / d).is_junction()))
            for name in sorted(files):
                if self.excluded(name):
                    continue
                rel = str((Path(parent) / name).relative_to(self.root)).replace("\\", "/")
                try:
                    self.path(rel)
                except (PermissionError, OSError):
                    continue
                result.append(rel)
                if len(result) >= limit:
                    return result
        return result

    def read(self, value: str, start: int = 1, count: int = 250) -> dict:
        path = self.path(value)
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("Datei zu groß; maximal 300 KB pro Textdatei.")
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        if "\0" in text:
            raise ValueError("Binärdatei wird nicht gelesen.")
        digest = hashlib.sha256(raw).hexdigest()
        self.seen[str(path)] = digest
        lines = text.splitlines()
        start = max(1, start)
        return {"path": value, "sha256": digest, "start": start, "total_lines": len(lines), "content": "\n".join(lines[start - 1:start - 1 + min(500, max(1, count))])}

    def edit(self, value: str, old: str, new: str) -> dict:
        path = self.path(value)
        raw = path.read_bytes()
        if self.seen.get(str(path)) != hashlib.sha256(raw).hexdigest():
            raise ValueError("Datei zuerst erneut lesen: nicht gelesen oder inzwischen verändert.")
        text = raw.decode("utf-8-sig")
        if not old or text.count(old) != 1:
            raise ValueError("Der zu ersetzende Text muss genau einmal vorkommen.")
        updated = text.replace(old, new, 1)
        if len(updated.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Änderung überschreitet 300 KB.")
        if raw.startswith(b"\xef\xbb\xbf"):
            updated = "\ufeff" + updated
        self.system.write_file(str(path), updated)
        self.seen[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"path": value, "diff": "".join(difflib.unified_diff(text.splitlines(True), updated.splitlines(True), fromfile=value, tofile=value))[:20000]}

    def create(self, value: str, content: str, overwrite: bool = False) -> dict:
        path = self.path(value)
        if len(content.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Datei überschreitet 300 KB.")
        if overwrite and path.is_file():
            raw = path.read_bytes()
            if self.seen.get(str(path)) != hashlib.sha256(raw).hexdigest():
                raise ValueError("Datei zuerst lesen: nicht gelesen oder inzwischen verändert. Danach create mit overwrite=true.")
            alt = raw.decode("utf-8-sig", errors="replace")
            self.system.write_file(str(path), content)
            self.seen[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            return {"path": value, "overwritten": True, "diff": "".join(difflib.unified_diff(alt.splitlines(True), content.splitlines(True), fromfile=value, tofile=value))[:20000]}
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8", newline="") as handle:
                handle.write(content)
        except FileExistsError:
            raise FileExistsError("Datei existiert bereits. Zum vollständigen Neuschreiben erst lesen, dann create mit overwrite=true; für kleine Änderungen edit.") from None
        self.seen[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"path": value, "created": True, "diff": "".join(difflib.unified_diff([], content.splitlines(True), fromfile="/dev/null", tofile=value))[:20000]}

    def search(self, text: str) -> dict:
        if not text:
            raise ValueError("Suchtext fehlt.")
        matches = []
        for value in self.files():
            path = self.path(value)
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                contents = path.read_text(encoding="utf-8-sig")
            except (UnicodeError, OSError):
                continue
            for number, line in enumerate(contents.splitlines(), 1):
                if text.casefold() in line.casefold():
                    matches.append({"path": value, "line": number, "text": line[:350]})
                    if len(matches) >= 80:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}
