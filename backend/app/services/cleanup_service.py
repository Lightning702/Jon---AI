from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path

CATEGORIES = {
    "Bilder": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg", ".tiff"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v"},
    "Musik": {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"},
    "Dokumente": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
    "Archive": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso"},
    "Programme": {".exe", ".msi", ".bat", ".cmd", ".sh"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".java", ".c", ".cpp", ".cs", ".go", ".rs"},
}


def _category(suffix: str) -> str:
    suffix = suffix.lower()
    for name, exts in CATEGORIES.items():
        if suffix in exts:
            return name
    return "Sonstiges"


class CleanupService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._plans: dict[str, dict] = {}

    def _known_folder(self, name: str) -> Path:
        home = Path.home()
        table = {
            "downloads": home / "Downloads",
            "desktop": home / "Desktop",
            "dokumente": home / "Documents",
            "documents": home / "Documents",
            "bilder": home / "Pictures",
            "pictures": home / "Pictures",
        }
        return table.get(name.strip().lower(), Path(name))

    def preview(self, folder: str, by: str = "typ") -> dict:
        base = self._known_folder(folder)
        if not base.exists() or not base.is_dir():
            return {"error": f"Den Ordner „{folder}“ gibt es nicht."}
        moves = []
        try:
            items = list(base.iterdir())
        except Exception as exc:
            return {"error": f"Ordner nicht lesbar: {exc}"}
        for item in items:
            if not item.is_file():
                continue
            if item.name.startswith("."):
                continue
            if by == "datum":
                stamp = time.localtime(item.stat().st_mtime)
                target = f"{stamp.tm_year}-{stamp.tm_mon:02d}"
            else:
                target = _category(item.suffix)
            if item.parent.name == target:
                continue
            moves.append({"name": item.name, "target": target})
        if not moves:
            return {"error": "Hier gibt es nichts aufzuräumen — alles schon sortiert."}
        summary: dict[str, int] = {}
        for m in moves:
            summary[m["target"]] = summary.get(m["target"], 0) + 1
        plan_id = str(int(time.time() * 1000))
        with self._lock:
            self._plans[plan_id] = {"base": str(base), "moves": moves, "created": time.time()}
            for pid in [p for p, v in self._plans.items() if time.time() - v["created"] > 600]:
                self._plans.pop(pid, None)
        return {
            "plan": plan_id,
            "folder": str(base),
            "count": len(moves),
            "summary": [{"ordner": k, "dateien": v} for k, v in sorted(summary.items())],
            "sample": moves[:12],
        }

    def apply(self, plan_id: str) -> dict:
        with self._lock:
            plan = self._plans.pop(plan_id, None)
        if not plan:
            return {"error": "Dieser Aufräum-Plan ist abgelaufen. Bitte neu erstellen."}
        base = Path(plan["base"])
        moved = 0
        failed = 0
        for m in plan["moves"]:
            src = base / m["name"]
            dst_dir = base / m["target"]
            if not src.exists():
                continue
            try:
                dst_dir.mkdir(exist_ok=True)
                dst = dst_dir / m["name"]
                if dst.exists():
                    stem, suffix = os.path.splitext(m["name"])
                    dst = dst_dir / f"{stem}_{int(time.time())}{suffix}"
                shutil.move(str(src), str(dst))
                moved += 1
            except Exception:
                failed += 1
        return {"moved": moved, "failed": failed}


_service: CleanupService | None = None


def get_cleanup_service() -> CleanupService:
    global _service
    if _service is None:
        _service = CleanupService()
    return _service
