from __future__ import annotations

import base64
import re
import secrets
import threading
import time
import zipfile
from pathlib import Path

from app.core.config import DATA_DIR

ORDNER = DATA_DIR / "handy-sicherungen"
GRENZE = 120 * 1024 * 1024
BEHALTEN = 10
TEIL = 512 * 1024
_KENNUNG = re.compile(r"[A-Za-z0-9_-]{1,64}")
_NAME = re.compile(r"\d{8}-\d{6}\.zip")


class SicherungFehler(ValueError):
    pass


class SicherungService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._offen: dict[str, dict] = {}

    def _ordner(self, geraet: str) -> Path:
        if not _KENNUNG.fullmatch(geraet or ""):
            raise SicherungFehler("Unbekanntes Gerät.")
        pfad = ORDNER / geraet
        pfad.mkdir(parents=True, exist_ok=True)
        return pfad

    def starten(self, geraet: str, groesse: int) -> dict:
        if groesse <= 0 or groesse > GRENZE:
            raise SicherungFehler("Die Sicherung ist zu groß.")
        ordner = self._ordner(geraet)
        marke = secrets.token_hex(12)
        teil = ordner / f".{marke}.teil"
        teil.write_bytes(b"")
        with self._lock:
            self._aufraeumen()
            self._offen[marke] = {"geraet": geraet, "pfad": teil, "groesse": groesse, "zeit": time.time()}
        return {"marke": marke}

    def anhaengen(self, geraet: str, marke: str, daten: str) -> dict:
        with self._lock:
            lauf = self._offen.get(marke)
        if not lauf or lauf["geraet"] != geraet:
            raise SicherungFehler("Diese Übertragung ist abgelaufen.")
        roh = base64.b64decode(daten or "")
        pfad: Path = lauf["pfad"]
        if pfad.stat().st_size + len(roh) > min(GRENZE, lauf["groesse"]):
            raise SicherungFehler("Mehr Daten als angekündigt.")
        with pfad.open("ab") as datei:
            datei.write(roh)
        return {"empfangen": pfad.stat().st_size}

    def abschliessen(self, geraet: str, marke: str) -> dict:
        with self._lock:
            lauf = self._offen.pop(marke, None)
        if not lauf or lauf["geraet"] != geraet:
            raise SicherungFehler("Diese Übertragung ist abgelaufen.")
        pfad: Path = lauf["pfad"]
        try:
            with zipfile.ZipFile(pfad) as archiv:
                if "jon-sicherung.json" not in archiv.namelist():
                    raise SicherungFehler("Das ist keine Jon-Sicherung.")
        except zipfile.BadZipFile as fehler:
            pfad.unlink(missing_ok=True)
            raise SicherungFehler("Die Sicherung ist beschädigt.") from fehler
        except SicherungFehler:
            pfad.unlink(missing_ok=True)
            raise
        ziel = pfad.parent / time.strftime("%Y%m%d-%H%M%S.zip")
        pfad.replace(ziel)
        alle = sorted((p for p in pfad.parent.glob("*.zip") if _NAME.fullmatch(p.name)), reverse=True)
        for alt in alle[BEHALTEN:]:
            alt.unlink(missing_ok=True)
        return self._eintrag(ziel)

    def _eintrag(self, pfad: Path) -> dict:
        zeit = time.mktime(time.strptime(pfad.stem, "%Y%m%d-%H%M%S"))
        return {"name": pfad.name, "groesse": pfad.stat().st_size, "zeit": zeit}

    def liste(self, geraet: str) -> list[dict]:
        ordner = self._ordner(geraet)
        return [self._eintrag(p) for p in sorted(ordner.glob("*.zip"), reverse=True) if _NAME.fullmatch(p.name)]

    def teil(self, geraet: str, name: str, offset: int) -> dict:
        if not _NAME.fullmatch(name or ""):
            raise SicherungFehler("Unbekannte Sicherung.")
        pfad = self._ordner(geraet) / name
        if not pfad.is_file():
            raise SicherungFehler("Unbekannte Sicherung.")
        groesse = pfad.stat().st_size
        start = max(0, min(int(offset), groesse))
        with pfad.open("rb") as datei:
            datei.seek(start)
            roh = datei.read(TEIL)
        return {"data": base64.b64encode(roh).decode("ascii"), "offset": start + len(roh), "size": groesse}

    def _aufraeumen(self) -> None:
        jetzt = time.time()
        for marke, lauf in list(self._offen.items()):
            if jetzt - lauf["zeit"] > 3600:
                Path(lauf["pfad"]).unlink(missing_ok=True)
                self._offen.pop(marke, None)


_dienst: SicherungService | None = None


def get_sicherung_service() -> SicherungService:
    global _dienst
    if _dienst is None:
        _dienst = SicherungService()
    return _dienst
