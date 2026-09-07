from __future__ import annotations

import hashlib
import json
import threading
import time

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_text

DATEI = DATA_DIR / "werkzeug_cache.json"
MAX_EINTRAEGE = 400
MAX_ANTWORT = 20000

LEBENSDAUER = {
    "web_search": 900,
    "get_weather": 1800,
    "http_get": 600,
    "maps": 3600,
    "ask_knowledge": 600,
    "list_documents": 300,
    "read_pdf": 3600,
    "read_pptx": 3600,
    "system_info": 60,
    "list_printers": 3600,
    "scan_network": 600,
    "smarthome_devices": 120,
    "spotify_search": 900,
    "project_overview": 120,
}


def _schluessel(name: str, args: dict) -> str:
    roh = json.dumps(args or {}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.blake2b(f"{name}|{roh}".encode("utf-8"), digest_size=12).hexdigest()


class CacheService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._daten: dict[str, dict] = self._laden()
        self._treffer = 0
        self._fehlgriffe = 0

    def _laden(self) -> dict:
        if DATEI.exists():
            try:
                roh = json.loads(DATEI.read_text(encoding="utf-8"))
                if isinstance(roh, dict):
                    return roh
            except Exception as _fehler:
                leise(_fehler, "services/cache_service")
        return {}

    def _sichern(self) -> None:
        try:
            eintraege = sorted(
                self._daten.items(), key=lambda paar: paar[1].get("zeit", 0)
            )[-MAX_EINTRAEGE:]
            self._daten = dict(eintraege)
            atomic_write_text(
                DATEI, json.dumps(self._daten, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as _fehler:
            leise(_fehler, "services/cache_service")

    def dauer(self, name: str) -> int:
        return int(LEBENSDAUER.get(name, 0))

    def holen(self, name: str, args: dict) -> str | None:
        dauer = self.dauer(name)
        if dauer <= 0:
            return None
        schluessel = _schluessel(name, args)
        with self._lock:
            eintrag = self._daten.get(schluessel)
            if not eintrag:
                self._fehlgriffe += 1
                return None
            if time.time() - float(eintrag.get("zeit", 0)) > dauer:
                self._daten.pop(schluessel, None)
                self._fehlgriffe += 1
                return None
            self._treffer += 1
            return str(eintrag.get("wert", ""))

    def merken(self, name: str, args: dict, wert: str) -> None:
        if self.dauer(name) <= 0:
            return
        if not wert or len(wert) > MAX_ANTWORT:
            return
        if '"error"' in wert[:200] or '"fehler"' in wert[:200]:
            return
        schluessel = _schluessel(name, args)
        with self._lock:
            self._daten[schluessel] = {"zeit": time.time(), "wert": wert, "tool": name}
            self._sichern()

    def leeren(self, name: str = "") -> int:
        with self._lock:
            if not name:
                anzahl = len(self._daten)
                self._daten.clear()
            else:
                treffer = [k for k, v in self._daten.items() if v.get("tool") == name]
                for schluessel in treffer:
                    self._daten.pop(schluessel, None)
                anzahl = len(treffer)
            self._sichern()
            return anzahl

    def stand(self) -> dict:
        with self._lock:
            return {
                "eintraege": len(self._daten),
                "treffer": self._treffer,
                "fehlgriffe": self._fehlgriffe,
                "quote": round(
                    self._treffer / max(1, self._treffer + self._fehlgriffe), 3
                ),
            }


_service: CacheService | None = None


def get_cache_service() -> CacheService:
    global _service
    if _service is None:
        _service = CacheService()
    return _service
