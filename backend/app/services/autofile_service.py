from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from app.services.settings_service import get_settings_service

SKIP_SUFFIXES = {".crdownload", ".part", ".tmp", ".partial", ".!ut"}
MIN_AGE_SECONDS = 15

CATEGORIES: dict[str, set[str]] = {
    "Bilder": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".flv"},
    "Musik": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"},
    "Dokumente": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md", ".epub"},
    "Tabellen": {".xls", ".xlsx", ".csv", ".ods"},
    "Praesentationen": {".ppt", ".pptx", ".odp"},
    "Programme": {".exe", ".msi", ".bat", ".cmd"},
    "Archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
}

NAME_RULES: list[tuple[tuple[str, ...], str]] = [
    (("rechnung", "invoice", "quittung", "receipt", "beleg"), "Rechnungen"),
    (("screenshot", "bildschirmfoto", "screen shot"), "Screenshots"),
]


def _category(path: Path) -> str | None:
    name = path.name.lower()
    for keywords, folder in NAME_RULES:
        if any(k in name for k in keywords):
            return folder
    suffix = path.suffix.lower()
    for folder, suffixes in CATEGORIES.items():
        if suffix in suffixes:
            return folder
    return None


class AutoFileService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recent: list[dict] = []
        self._running = False

    def _downloads(self) -> Path:
        return Path.home() / "Downloads"

    def recent(self) -> list[dict]:
        with self._lock:
            return list(self._recent)

    def tick(self) -> None:
        if self._running:
            return
        if not get_settings_service().get().get("autofile_enabled", False):
            return
        self._running = True
        try:
            folder = self._downloads()
            if not folder.is_dir():
                return
            from app.services.system_service import SystemService

            system = SystemService()
            now = time.time()
            for item in folder.iterdir():
                if not item.is_file():
                    continue
                if item.suffix.lower() in SKIP_SUFFIXES:
                    continue
                if item.name.startswith("."):
                    continue
                try:
                    if now - item.stat().st_mtime < MIN_AGE_SECONDS:
                        continue
                except Exception:
                    continue
                category = _category(item)
                if category is None:
                    continue
                target_dir = folder / category
                target = target_dir / item.name
                if target.exists():
                    stem, suffix = item.stem, item.suffix
                    target = target_dir / f"{stem}-{int(now)}{suffix}"
                try:
                    moved = system.move_path(str(item), str(target))
                except Exception:
                    continue
                entry = {
                    "datei": item.name,
                    "kategorie": category,
                    "ziel": moved,
                    "zeit": datetime.now().isoformat(timespec="seconds"),
                }
                with self._lock:
                    self._recent.insert(0, entry)
                    del self._recent[50:]
                from app.services.action_log_service import log_action

                log_action(
                    "autofile",
                    "auto_sortieren",
                    {"datei": item.name, "kategorie": category},
                    moved,
                )
        finally:
            self._running = False


_service: AutoFileService | None = None


def get_autofile_service() -> AutoFileService:
    global _service
    if _service is None:
        _service = AutoFileService()
    return _service
