from __future__ import annotations

import threading
import time
import uuid

from app.core.config import DATA_DIR
from app.core.store import atomic_write_json, read_json

STORE = DATA_DIR / "zeiten.json"
ARTEN = ("stoppuhr", "timer")
MAX_UHREN = 12


class ZeitFehler(Exception):
    pass


class ZeitService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        roh = read_json(STORE, None)
        self._uhren: list[dict] = roh if isinstance(roh, list) else []

    def _sichern(self) -> None:
        atomic_write_json(STORE, self._uhren)

    def _verstrichen(self, uhr: dict) -> float:
        pause = float(uhr.get("pause_gesamt", 0.0))
        if uhr.get("pausiert_seit"):
            pause += time.time() - float(uhr["pausiert_seit"])
        return max(0.0, time.time() - float(uhr["gestartet"]) - pause)

    def _ansicht(self, uhr: dict) -> dict:
        verstrichen = self._verstrichen(uhr)
        daten = {
            "id": uhr["id"],
            "art": uhr["art"],
            "titel": uhr.get("titel", ""),
            "gestartet": uhr["gestartet"],
            "laeuft": not uhr.get("pausiert_seit"),
            "verstrichen": round(verstrichen, 1),
        }
        if uhr["art"] == "timer":
            dauer = float(uhr.get("dauer", 0))
            daten["dauer"] = dauer
            daten["rest"] = round(max(0.0, dauer - verstrichen), 1)
            daten["fertig"] = verstrichen >= dauer
        else:
            daten["fertig"] = False
        return daten

    def starten(self, art: str, sekunden: int = 0, titel: str = "") -> dict:
        art = (art or "stoppuhr").strip().lower()
        if art not in ARTEN:
            raise ZeitFehler("Art muss stoppuhr oder timer sein.")
        if art == "timer" and sekunden <= 0:
            raise ZeitFehler("Ein Timer braucht eine Dauer.")
        uhr = {
            "id": uuid.uuid4().hex[:8],
            "art": art,
            "titel": titel.strip(),
            "gestartet": time.time(),
            "dauer": float(sekunden),
            "pause_gesamt": 0.0,
            "pausiert_seit": 0.0,
        }
        with self._lock:
            self._uhren = self._uhren[-(MAX_UHREN - 1):] + [uhr]
            self._sichern()
        return self._ansicht(uhr)

    def stand(self) -> dict:
        with self._lock:
            return {"uhren": [self._ansicht(uhr) for uhr in self._uhren]}

    def _finden(self, uhr_id: str) -> dict:
        for uhr in self._uhren:
            if uhr["id"] == uhr_id:
                return uhr
        raise ZeitFehler("Diese Uhr gibt es nicht.")

    def pausieren(self, uhr_id: str) -> dict:
        with self._lock:
            uhr = self._finden(uhr_id)
            if not uhr.get("pausiert_seit"):
                uhr["pausiert_seit"] = time.time()
                self._sichern()
            return self._ansicht(uhr)

    def weiter(self, uhr_id: str) -> dict:
        with self._lock:
            uhr = self._finden(uhr_id)
            if uhr.get("pausiert_seit"):
                uhr["pause_gesamt"] = float(uhr.get("pause_gesamt", 0.0)) + (
                    time.time() - float(uhr["pausiert_seit"])
                )
                uhr["pausiert_seit"] = 0.0
                self._sichern()
            return self._ansicht(uhr)

    def stoppen(self, uhr_id: str = "") -> dict:
        with self._lock:
            if not uhr_id:
                letzte = [self._ansicht(uhr) for uhr in self._uhren]
                self._uhren = []
                self._sichern()
                return {"gestoppt": letzte}
            uhr = self._finden(uhr_id)
            ansicht = self._ansicht(uhr)
            self._uhren = [e for e in self._uhren if e["id"] != uhr_id]
            self._sichern()
            return {"gestoppt": [ansicht]}


_service: ZeitService | None = None


def get_zeit_service() -> ZeitService:
    global _service
    if _service is None:
        _service = ZeitService()
    return _service


def lesbar(sekunden: float) -> str:
    ganz = int(max(0, sekunden))
    stunden, rest = divmod(ganz, 3600)
    minuten, sek = divmod(rest, 60)
    if stunden:
        return f"{stunden}:{minuten:02d}:{sek:02d}"
    return f"{minuten}:{sek:02d}"
