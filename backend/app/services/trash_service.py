from __future__ import annotations

import json
import re
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR

TRASH_DIR = DATA_DIR / "trash"
KEEP_DAYS = 30
_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{8}$")


class TrashService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        TRASH_DIR.mkdir(parents=True, exist_ok=True)

    def _new_entry(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        entry = TRASH_DIR / f"{stamp}-{uuid.uuid4().hex[:8]}"
        entry.mkdir(parents=True, exist_ok=True)
        return entry

    def _write_meta(self, entry: Path, meta: dict) -> None:
        meta["deleted_at"] = datetime.now().isoformat(timespec="seconds")
        (entry / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def stash_delete(self, path: Path) -> str | None:
        resolved = path.resolve()
        if TRASH_DIR.resolve() in (resolved, *resolved.parents):
            return None
        with self._lock:
            entry = self._new_entry()
            shutil.move(str(path), str(entry / path.name))
            self._write_meta(
                entry,
                {"action": "geloescht", "original": str(path), "name": path.name},
            )
            return entry.name

    def stash_overwrite(self, path: Path, action: str = "ueberschrieben") -> str | None:
        if not path.exists():
            return None
        with self._lock:
            entry = self._new_entry()
            payload = entry / path.name
            if path.is_dir():
                shutil.copytree(str(path), str(payload))
            else:
                shutil.copy2(str(path), str(payload))
            self._write_meta(
                entry,
                {"action": action, "original": str(path), "name": path.name},
            )
            return entry.name

    def record_move(self, source: Path, destination: Path) -> str:
        with self._lock:
            entry = self._new_entry()
            self._write_meta(
                entry,
                {
                    "action": "verschoben",
                    "original": str(source),
                    "destination": str(destination),
                    "name": source.name,
                },
            )
            return entry.name

    def entries(self) -> list[dict]:
        items: list[dict] = []
        for entry in sorted(TRASH_DIR.iterdir(), key=lambda p: p.name, reverse=True):
            meta_file = entry / "meta.json"
            if not entry.is_dir() or not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            meta["id"] = entry.name
            items.append(meta)
        return items

    def _free_target(self, target: Path) -> Path:
        if not target.exists():
            return target
        for i in range(1, 100):
            tag = " (wiederhergestellt)" if i == 1 else f" (wiederhergestellt {i})"
            candidate = target.with_name(f"{target.stem}{tag}{target.suffix}")
            if not candidate.exists():
                return candidate
        return target.with_name(f"{target.stem}-{uuid.uuid4().hex[:6]}{target.suffix}")

    def restore(self, entry_id: str) -> dict:
        if not _ID_RE.match(entry_id or ""):
            return {"error": "Unbekannter Papierkorb-Eintrag"}
        with self._lock:
            entry = TRASH_DIR / entry_id
            meta_file = entry / "meta.json"
            if not meta_file.exists():
                return {"error": "Eintrag nicht (mehr) im Papierkorb"}
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                return {"error": "Papierkorb-Eintrag ist beschaedigt"}
            if meta.get("action") == "verschoben":
                src = Path(meta.get("destination", ""))
                dst = Path(meta.get("original", ""))
                if not src.exists():
                    return {"error": f"{src} existiert nicht mehr"}
                target = self._free_target(dst)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(target))
                shutil.rmtree(entry, ignore_errors=True)
                return {"restored": str(target), "action": "verschoben"}
            payload = entry / str(meta.get("name", ""))
            if not payload.exists():
                return {"error": "Papierkorb-Eintrag ist beschaedigt"}
            target = self._free_target(Path(meta.get("original", "")))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(payload), str(target))
            shutil.rmtree(entry, ignore_errors=True)
            return {"restored": str(target), "action": meta.get("action", "")}

    def undo_last(self) -> dict:
        latest = self.entries()
        if not latest:
            return {"error": "Der Papierkorb ist leer - nichts zum Wiederherstellen"}
        return self.restore(latest[0]["id"])

    def cleanup(self, days: int = KEEP_DAYS) -> int:
        cutoff = time.time() - days * 86400
        removed = 0
        try:
            for entry in TRASH_DIR.iterdir():
                if not entry.is_dir():
                    continue
                try:
                    if entry.stat().st_mtime < cutoff:
                        shutil.rmtree(entry, ignore_errors=True)
                        removed += 1
                except Exception:
                    continue
        except Exception:
            pass
        return removed


_service: TrashService | None = None


def get_trash_service() -> TrashService:
    global _service
    if _service is None:
        _service = TrashService()
    return _service
