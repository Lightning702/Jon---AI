from __future__ import annotations

import base64
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import DATA_DIR, get_settings
from app.services.focus_service import active_window_title

TIMELINE_DIR = DATA_DIR / "timeline"
INDEX_FILE = TIMELINE_DIR / "index.json"
KEEP_DAYS = 7

DESCRIBE_PROMPT = (
    "Das ist ein frueheres Bildschirmfoto vom PC des Nutzers. Beschreibe auf Deutsch "
    "kurz und konkret, was darauf zu sehen ist: welche App oder Seite, worum es geht, "
    "wichtige sichtbare Texte oder Titel. Maximal 4 Saetze."
)


class TimelineService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        TIMELINE_DIR.mkdir(parents=True, exist_ok=True)
        self._index = self._load()
        self._last_title = ""
        self._last_capture = 0.0

    def _load(self) -> list[dict]:
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _save(self) -> None:
        try:
            INDEX_FILE.write_text(
                json.dumps(self._index, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _prune(self) -> None:
        cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).isoformat()
        keep = []
        for entry in self._index:
            if entry.get("ts", "") >= cutoff:
                keep.append(entry)
            else:
                try:
                    (TIMELINE_DIR / entry["file"]).unlink(missing_ok=True)
                except Exception:
                    pass
        self._index = keep

    def capture(self) -> None:
        from app.services.system_service import SystemService

        title = active_window_title().strip()
        if not title:
            return
        now = time.time()
        with self._lock:
            if title == self._last_title and now - self._last_capture < 900:
                return
        try:
            data_url = SystemService().screenshot_data_url(max_width=720, quality=55)
            raw = base64.b64decode(data_url.split(",", 1)[1])
        except Exception:
            return
        stamp = datetime.now()
        name = stamp.strftime("%Y%m%d_%H%M%S") + ".jpg"
        try:
            (TIMELINE_DIR / name).write_bytes(raw)
        except Exception:
            return
        with self._lock:
            self._last_title = title
            self._last_capture = now
            self._index.append(
                {"ts": stamp.isoformat(timespec="seconds"), "title": title[:200], "file": name}
            )
            self._prune()
            self._save()

    def search(self, query: str, day: str = "", limit: int = 12) -> list[dict]:
        words = [w for w in query.lower().split() if len(w) > 1]
        with self._lock:
            entries = list(reversed(self._index))
        results = []
        for entry in entries:
            if day and not entry["ts"].startswith(day):
                continue
            title = entry["title"].lower()
            if words and not any(w in title for w in words):
                continue
            results.append(
                {
                    "wann": entry["ts"].replace("T", " "),
                    "fenster": entry["title"],
                    "datei": entry["file"],
                }
            )
            if len(results) >= limit:
                break
        return results

    async def describe(self, file: str) -> dict:
        from app.providers.openai_compatible import OpenAICompatibleProvider
        from app.providers.registry import get_registry
        from app.services.screen_service import VISION_DEFAULTS
        from app.services.settings_service import get_settings_service

        path = TIMELINE_DIR / Path(file).name
        if not path.exists():
            return {"error": "Dieses Bildschirmfoto gibt es nicht mehr."}
        settings = get_settings()
        user = get_settings_service()
        provider_name = user.get().get("provider") or settings.default_provider
        vision_model = user.get().get("vision_model") or VISION_DEFAULTS.get(provider_name)
        provider = get_registry().all().get(provider_name)
        if not isinstance(provider, OpenAICompatibleProvider) or not vision_model:
            return {"error": "Dafuer braucht es einen Anbieter mit Vision-Modell (z.B. NVIDIA)."}
        data_url = "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
        try:
            text = await provider.describe_image(vision_model, data_url, DESCRIBE_PROMPT)
        except Exception as exc:
            return {"error": str(exc)}
        return {"beschreibung": text.strip()}

    def stats(self) -> dict:
        with self._lock:
            return {"eintraege": len(self._index), "tage": KEEP_DAYS}


_service: TimelineService | None = None


def get_timeline_service() -> TimelineService:
    global _service
    if _service is None:
        _service = TimelineService()
    return _service
