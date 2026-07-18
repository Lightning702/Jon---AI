from __future__ import annotations

import json
import math
import re
import threading
import uuid
from datetime import datetime

from app.core.config import DATA_DIR

PLACES_FILE = DATA_DIR / "telegram_places.json"
GEO_REMINDERS_FILE = DATA_DIR / "telegram_geo_reminders.json"
DEFAULT_RADIUS_M = 180.0

_TRIGGER = re.compile(
    r"erinner\w*\s+mich\s+an\s+(?P<text>.+?)\s+wenn\s+ich\s+"
    r"(?:beim?|am|an|in|im|bei)\s+(?P<ort>.+?)\s+bin",
    re.IGNORECASE,
)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_geo_reminder(text: str) -> tuple[str, str] | None:
    match = _TRIGGER.search(text or "")
    if not match:
        return None
    what = match.group("text").strip().strip(".,!?")
    where = match.group("ort").strip().strip(".,!?")
    if not what or not where:
        return None
    return what, where


class LocationService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._places = self._load(PLACES_FILE)
        self._reminders = self._load(GEO_REMINDERS_FILE)

    def _load(self, path) -> list[dict]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, path, data) -> None:
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def add_place(self, chat_id: str, name: str, lat: float, lon: float) -> dict:
        entry = {
            "id": uuid.uuid4().hex,
            "chat_id": str(chat_id),
            "name": name.strip(),
            "lat": float(lat),
            "lon": float(lon),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self._lock:
            self._places = [
                p
                for p in self._places
                if not (
                    p["chat_id"] == str(chat_id)
                    and p["name"].lower() == name.strip().lower()
                )
            ]
            self._places.append(entry)
            self._save(PLACES_FILE, self._places)
        return entry

    def find_place(self, chat_id: str, name: str) -> dict | None:
        target = name.strip().lower()
        with self._lock:
            exact = [
                p
                for p in self._places
                if p["chat_id"] == str(chat_id) and p["name"].lower() == target
            ]
            if exact:
                return exact[0]
            partial = [
                p
                for p in self._places
                if p["chat_id"] == str(chat_id)
                and (target in p["name"].lower() or p["name"].lower() in target)
            ]
            return partial[0] if partial else None

    def places(self, chat_id: str) -> list[dict]:
        with self._lock:
            return [p for p in self._places if p["chat_id"] == str(chat_id)]

    def add_reminder(self, chat_id: str, text: str, place_name: str) -> dict | None:
        place = self.find_place(chat_id, place_name)
        entry = {
            "id": uuid.uuid4().hex,
            "chat_id": str(chat_id),
            "text": text.strip(),
            "place_name": place["name"] if place else place_name.strip(),
            "place_id": place["id"] if place else None,
            "done": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self._lock:
            self._reminders.append(entry)
            self._save(GEO_REMINDERS_FILE, self._reminders)
        return None if place else entry

    def reminders(self, chat_id: str, include_done: bool = False) -> list[dict]:
        with self._lock:
            return [
                r
                for r in self._reminders
                if r["chat_id"] == str(chat_id) and (include_done or not r["done"])
            ]

    def check(
        self, chat_id: str, lat: float, lon: float, radius: float = DEFAULT_RADIUS_M
    ) -> list[str]:
        triggered: list[str] = []
        with self._lock:
            near_ids = {
                p["id"]
                for p in self._places
                if p["chat_id"] == str(chat_id)
                and haversine(lat, lon, p["lat"], p["lon"]) <= radius
            }
            if not near_ids:
                return []
            changed = False
            for r in self._reminders:
                if (
                    r["chat_id"] == str(chat_id)
                    and not r["done"]
                    and r.get("place_id") in near_ids
                ):
                    r["done"] = True
                    changed = True
                    triggered.append(r["text"])
            if changed:
                self._save(GEO_REMINDERS_FILE, self._reminders)
        return triggered


_service: LocationService | None = None


def get_location_service() -> LocationService:
    global _service
    if _service is None:
        _service = LocationService()
    return _service
