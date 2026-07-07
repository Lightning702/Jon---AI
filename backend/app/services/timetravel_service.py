from __future__ import annotations

import json
import os
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR

SNAP_DIR = DATA_DIR / "snapshots"
INDEX_FILE = SNAP_DIR / "index.json"
SKIP = {".git", "node_modules", "__pycache__", "dist", "venv", ".venv", "data"}


class TimeTravelService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        self._index = self._load()

    def _load(self) -> list[dict]:
        if INDEX_FILE.exists():
            try:
                return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self) -> None:
        try:
            INDEX_FILE.write_text(
                json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def snapshot(
        self,
        label: str,
        workspace: str | None = None,
        note: str = "",
        kind: str = "auto",
    ) -> dict:
        snap_id = uuid.uuid4().hex[:10]
        entry = {
            "id": snap_id,
            "label": label.strip() or "Snapshot",
            "note": note.strip(),
            "kind": kind,
            "workspace": workspace or "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "files": 0,
            "archive": None,
        }
        if workspace:
            root = Path(workspace).expanduser()
            if root.is_dir():
                archive = SNAP_DIR / f"{snap_id}.zip"
                count = 0
                with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                    for dirpath, dirnames, filenames in os.walk(root):
                        dirnames[:] = [d for d in dirnames if d not in SKIP]
                        for fn in filenames:
                            full = Path(dirpath) / fn
                            try:
                                if full.stat().st_size > 20_000_000:
                                    continue
                                zf.write(full, full.relative_to(root))
                                count += 1
                            except Exception:
                                continue
                entry["files"] = count
                entry["archive"] = archive.name
        with self._lock:
            self._index.insert(0, entry)
            self._save()
        return entry

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._index)

    def get(self, snap_id: str) -> dict | None:
        with self._lock:
            return next((e for e in self._index if e["id"] == snap_id), None)

    def restore(self, snap_id: str) -> dict:
        entry = self.get(snap_id)
        if entry is None:
            raise ValueError("Snapshot nicht gefunden")
        if not entry.get("archive"):
            return {"restored": False, "reason": "Dieser Snapshot enthaelt keine Dateien"}
        archive = SNAP_DIR / entry["archive"]
        if not archive.exists():
            raise ValueError("Snapshot-Archiv fehlt")
        workspace = entry.get("workspace")
        if not workspace:
            raise ValueError("Kein Zielordner im Snapshot")
        root = Path(workspace).expanduser()
        if root.is_dir():
            self.snapshot(
                f"Vor Wiederherstellung von {entry['label']}",
                workspace,
                "Automatisches Sicherungs-Snapshot vor dem Zurueckspielen",
                kind="backup",
            )
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(root)
        return {"restored": True, "workspace": str(root), "files": entry.get("files", 0)}

    def delete(self, snap_id: str) -> bool:
        with self._lock:
            entry = next((e for e in self._index if e["id"] == snap_id), None)
            if entry is None:
                return False
            if entry.get("archive"):
                try:
                    (SNAP_DIR / entry["archive"]).unlink(missing_ok=True)
                except Exception:
                    pass
            self._index = [e for e in self._index if e["id"] != snap_id]
            self._save()
            return True


_service: TimeTravelService | None = None


def get_timetravel_service() -> TimeTravelService:
    global _service
    if _service is None:
        _service = TimeTravelService()
    return _service
