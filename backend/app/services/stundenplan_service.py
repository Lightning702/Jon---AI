from __future__ import annotations

import json
import re
import threading
import time
from datetime import date, datetime
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text

DATEI = DATA_DIR / "stundenplan.json"
TAGE = ("montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag")
KURZ = {"mo": "montag", "di": "dienstag", "mi": "mittwoch", "do": "donnerstag", "fr": "freitag", "sa": "samstag", "so": "sonntag",
        "monday": "montag", "tuesday": "dienstag", "wednesday": "mittwoch", "thursday": "donnerstag", "friday": "freitag", "saturday": "samstag", "sunday": "sonntag"}
ZEIT = re.compile(r"^\s*(\d{1,2})[:.](\d{2})\s*$")

AUFTRAG = (
    "Wandle den folgenden Stundenplan in JSON um. Antworte NUR mit JSON in genau dieser Form: "
    '{"tage": {"montag": [{"stunde": 1, "von": "08:00", "bis": "08:50", "fach": "Mathematik", "raum": "", "lehrer": ""}], '
    '"dienstag": [], "mittwoch": [], "donnerstag": [], "freitag": []}}. '
    "Zeiten im Format HH:MM, fehlende Angaben als leere Zeichenkette, Freistunden weglassen. Erfinde nichts."
)


def _tag(name) -> str:
    text = str(name or "").strip().lower()
    if text in TAGE:
        return text
    return KURZ.get(text[:2], KURZ.get(text, "")) if text else ""


def _zeit(wert) -> str:
    treffer = ZEIT.match(str(wert or ""))
    return f"{int(treffer.group(1)):02d}:{treffer.group(2)}" if treffer else str(wert or "").strip()[:5]


def _eintrag(roh) -> dict | None:
    if isinstance(roh, str):
        roh = {"fach": roh}
    if not isinstance(roh, dict):
        return None
    fach = str(roh.get("fach") or roh.get("subject") or roh.get("name") or "").strip()
    if not fach:
        return None
    eintrag = {"fach": fach[:80], "von": _zeit(roh.get("von") or roh.get("start")), "bis": _zeit(roh.get("bis") or roh.get("ende") or roh.get("end"))}
    for feld, alias in (("raum", "room"), ("lehrer", "teacher"), ("stunde", "periode")):
        wert = roh.get(feld) or roh.get(alias)
        if wert not in (None, ""):
            eintrag[feld] = wert if feld == "stunde" else str(wert)[:60]
    return eintrag


def _letztes_json(text: str) -> dict:
    dekoder = json.JSONDecoder()
    gefunden: dict = {}
    position = 0
    while True:
        start = text.find("{", position)
        if start < 0:
            return gefunden
        try:
            wert, ende = dekoder.raw_decode(text, start)
        except ValueError:
            position = start + 1
            continue
        if isinstance(wert, dict) and isinstance(wert.get("tage"), dict):
            gefunden = wert
        position = ende


class StundenplanService:
    def __init__(self, datei: Path | None = None) -> None:
        self.datei = Path(datei or DATEI)
        self._lock = threading.Lock()

    def laden(self) -> dict:
        try:
            daten = json.loads(self.datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"tage": {}}
        return daten if isinstance(daten, dict) and isinstance(daten.get("tage"), dict) else {"tage": {}}

    def setzen(self, tage: dict, quelle: str = "") -> dict:
        sauber: dict[str, list] = {}
        for name, eintraege in (tage or {}).items():
            tag = _tag(name)
            if not tag or not isinstance(eintraege, list):
                continue
            liste = [e for e in (_eintrag(r) for r in eintraege) if e]
            liste.sort(key=lambda e: (e.get("von") or "99:99", e.get("stunde") or 0))
            sauber[tag] = liste
        if not any(sauber.values()):
            raise ValueError("Im Stundenplan stehen keine Fächer.")
        daten = {"tage": sauber, "quelle": quelle[:200], "aktualisiert": time.time()}
        with self._lock:
            self.datei.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self.datei, json.dumps(daten, ensure_ascii=False))
        return daten

    def tag_aendern(self, tag: str, eintraege: list) -> dict:
        daten = self.laden()
        name = _tag(tag)
        if not name:
            raise ValueError("Unbekannter Wochentag.")
        tage = dict(daten.get("tage") or {})
        tage[name] = eintraege
        return self.setzen(tage, daten.get("quelle", ""))

    def loeschen(self) -> bool:
        with self._lock:
            if self.datei.exists():
                self.datei.unlink()
                return True
        return False

    def fuer(self, tag: date | datetime | str | None = None) -> tuple[str, list[dict]]:
        if isinstance(tag, str) and _tag(tag):
            name = _tag(tag)
        else:
            stichtag = tag if isinstance(tag, (date, datetime)) else date.today()
            name = TAGE[stichtag.weekday()]
        return name, list(self.laden().get("tage", {}).get(name, []))

    def text(self, tag: date | datetime | str | None = None) -> str:
        name, eintraege = self.fuer(tag)
        if not eintraege:
            return ""
        zeilen = []
        for e in eintraege:
            zeit = f"{e['von']}–{e['bis']}" if e.get("von") and e.get("bis") else e.get("von", "")
            zusatz = ", ".join(x for x in (e.get("raum", ""), e.get("lehrer", "")) if x)
            zeilen.append(f"{zeit + ' ' if zeit else ''}{e['fach']}{f' ({zusatz})' if zusatz else ''}".strip())
        return f"Stundenplan {name.capitalize()}: " + "; ".join(zeilen)

    async def aus_text(self, text: str, quelle: str = "Text") -> dict:
        from app.services.llm import complete

        antwort = await complete(AUFTRAG, str(text)[:12000], max_tokens=4000, temperature=0.1)
        daten = _letztes_json(antwort)
        if not daten:
            raise ValueError("Ich konnte daraus keinen Stundenplan lesen. Schreib ihn zum Beispiel als 'Montag: 8:00 Mathe, 8:50 Deutsch'.")
        return self.setzen(daten["tage"], quelle)

    async def aus_datei(self, pfad: str) -> dict:
        from app.services.attachment_service import _art, get_attachment_service

        ziel = Path(str(pfad or "")).expanduser()
        if not ziel.is_file():
            raise ValueError(f"Datei nicht gefunden: {ziel}")
        dienst = get_attachment_service()
        art = _art(ziel.name, "")
        if art == "image":
            gelesen = await dienst.beschreiben(ziel)
        else:
            gelesen = await dienst.auswerten(ziel, ziel.name, "")
        inhalt = str(gelesen.get("content") or "")
        if not inhalt.strip():
            raise ValueError("Die Datei enthält keinen lesbaren Stundenplan.")
        return await self.aus_text(inhalt, ziel.name)


_service: StundenplanService | None = None


def get_stundenplan_service() -> StundenplanService:
    global _service
    if _service is None:
        _service = StundenplanService()
    return _service
