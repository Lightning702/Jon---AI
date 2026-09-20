from __future__ import annotations

import shutil
import threading
import time
import urllib.request
import uuid
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_json, read_json

ORDNER = DATA_DIR / "mediathek"
INDEX = DATA_DIR / "mediathek.json"
VIDEO = {".mp4", ".webm", ".mkv", ".mov", ".m4v"}
MUSIK = {".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac"}
BILD_ZEIT = 8.0


def _art(pfad: Path) -> str:
    endung = pfad.suffix.lower()
    if endung in MUSIK:
        return "musik"
    if endung in VIDEO:
        return "video"
    return "datei"


def _frei(name: str) -> str:
    stamm = Path(name).stem[:80] or "aufnahme"
    endung = Path(name).suffix.lower() or ".mp4"
    kandidat = f"{stamm}{endung}"
    zaehler = 2
    while (ORDNER / kandidat).exists():
        kandidat = f"{stamm} ({zaehler}){endung}"
        zaehler += 1
    return kandidat


class MediathekService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        roh = read_json(INDEX, None)
        self._eintraege: list[dict] = [e for e in roh if isinstance(e, dict)] if isinstance(roh, list) else []

    def _sichern(self) -> None:
        atomic_write_json(INDEX, self._eintraege)

    def _pfad(self, eintrag: dict) -> Path:
        return ORDNER / str(eintrag.get("datei", ""))

    def _ansicht(self, eintrag: dict) -> dict:
        pfad = self._pfad(eintrag)
        return {
            "id": eintrag["id"],
            "name": eintrag.get("name", ""),
            "art": eintrag.get("art", "datei"),
            "groesse": eintrag.get("groesse", 0),
            "dauer": eintrag.get("dauer", 0),
            "quelle": eintrag.get("quelle", ""),
            "kanal": eintrag.get("kanal", ""),
            "erstellt": eintrag.get("erstellt", 0),
            "bild": bool(eintrag.get("bild")),
            "datei": str(pfad),
        }

    def _bild_holen(self, kennung: str, url: str) -> str:
        if not url.startswith("http"):
            return ""
        ziel = ORDNER / f"{kennung}.jpg"
        try:
            anfrage = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Jon)"}
            )
            with urllib.request.urlopen(anfrage, timeout=BILD_ZEIT) as antwort:
                daten = antwort.read(4_000_000)
            if not daten:
                return ""
            ziel.write_bytes(daten)
            return ziel.name
        except Exception as fehler:
            leise(fehler, "services/mediathek")
            return ""

    def aufnehmen(
        self,
        quelle_datei: Path | str,
        name: str = "",
        quelle: str = "",
        dauer: float = 0.0,
        kanal: str = "",
        bild: str = "",
        verschieben: bool = False,
    ) -> dict | None:
        pfad = Path(quelle_datei)
        if not pfad.is_file():
            return None
        art = _art(pfad)
        if art == "datei":
            return None
        ORDNER.mkdir(parents=True, exist_ok=True)
        kennung = uuid.uuid4().hex[:8]
        with self._lock:
            dateiname = _frei(name or pfad.name)
            ziel = ORDNER / dateiname
            try:
                if verschieben:
                    shutil.move(str(pfad), str(ziel))
                else:
                    shutil.copy2(str(pfad), str(ziel))
            except OSError as fehler:
                leise(fehler, "services/mediathek")
                return None
            eintrag = {
                "id": kennung,
                "name": (name or pfad.stem).rsplit(".", 1)[0][:120],
                "datei": dateiname,
                "art": art,
                "groesse": ziel.stat().st_size,
                "dauer": round(float(dauer or 0.0), 1),
                "quelle": quelle,
                "kanal": kanal,
                "bild": "",
                "erstellt": time.time(),
            }
            self._eintraege.append(eintrag)
            self._sichern()
        if bild:
            name_bild = self._bild_holen(kennung, bild)
            if name_bild:
                with self._lock:
                    eintrag["bild"] = name_bild
                    self._sichern()
        return self._ansicht(eintrag)

    def liste(self) -> dict:
        with self._lock:
            bleiben = [e for e in self._eintraege if self._pfad(e).is_file()]
            if len(bleiben) != len(self._eintraege):
                self._eintraege = bleiben
                self._sichern()
            eintraege = [
                self._ansicht(e)
                for e in sorted(
                    self._eintraege, key=lambda e: e.get("erstellt", 0), reverse=True
                )
            ]
        return {
            "eintraege": eintraege,
            "ordner": str(ORDNER),
            "groesse": sum(e["groesse"] for e in eintraege),
        }

    def finden(self, kennung: str) -> tuple[Path, dict] | None:
        with self._lock:
            for eintrag in self._eintraege:
                if eintrag["id"] == kennung:
                    pfad = self._pfad(eintrag)
                    return (pfad, self._ansicht(eintrag)) if pfad.is_file() else None
        return None

    def bild(self, kennung: str) -> Path | None:
        with self._lock:
            for eintrag in self._eintraege:
                if eintrag["id"] == kennung and eintrag.get("bild"):
                    pfad = ORDNER / str(eintrag["bild"])
                    return pfad if pfad.is_file() else None
        return None

    def loeschen(self, kennung: str) -> bool:
        with self._lock:
            treffer = [e for e in self._eintraege if e["id"] == kennung]
            if not treffer:
                return False
            for eintrag in treffer:
                try:
                    self._pfad(eintrag).unlink(missing_ok=True)
                    if eintrag.get("bild"):
                        (ORDNER / str(eintrag["bild"])).unlink(missing_ok=True)
                except OSError as fehler:
                    leise(fehler, "services/mediathek")
            self._eintraege = [e for e in self._eintraege if e["id"] != kennung]
            self._sichern()
        return True


_service: MediathekService | None = None


def get_mediathek_service() -> MediathekService:
    global _service
    if _service is None:
        _service = MediathekService()
    return _service
