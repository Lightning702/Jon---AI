from __future__ import annotations

import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_json, read_json

STORE = DATA_DIR / "ausloeser.json"
ARTEN = ("taeglich", "intervall", "ordner", "start")
WOCHENTAGE = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
    "mo": 0,
    "di": 1,
    "mi": 2,
    "do": 3,
    "fr": 4,
    "sa": 5,
    "so": 6,
}
MAX_REGELN = 40
MAX_BEKANNT = 400
MAX_NEUE_DATEIEN = 5
ZEIT_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class AusloeserFehler(Exception):
    pass


def _jetzt() -> float:
    return time.time()


def tage_lesen(wert) -> list[int]:
    if wert in (None, "", []):
        return []
    roh = wert if isinstance(wert, (list, tuple)) else str(wert).split(",")
    tage: list[int] = []
    for teil in roh:
        if isinstance(teil, int) and 0 <= teil <= 6:
            tage.append(teil)
            continue
        name = str(teil).strip().lower()
        if not name:
            continue
        if name.isdigit() and 0 <= int(name) <= 6:
            tage.append(int(name))
        elif name in WOCHENTAGE:
            tage.append(WOCHENTAGE[name])
        elif name in ("werktags", "wochentags"):
            tage.extend([0, 1, 2, 3, 4])
        elif name in ("wochenende",):
            tage.extend([5, 6])
    return sorted(set(tage))


class AusloeserService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        roh = read_json(STORE, None)
        self._regeln: list[dict] = roh if isinstance(roh, list) else []
        self._gestartet = False

    def _sichern(self) -> None:
        atomic_write_json(STORE, self._regeln[-MAX_REGELN:])

    def _finden(self, kennung: str) -> dict:
        gesucht = str(kennung or "").strip()
        for regel in self._regeln:
            if regel["id"] == gesucht:
                return regel
        raise AusloeserFehler(f"Den Ausloeser {gesucht} gibt es nicht.")

    def anlegen(
        self,
        art: str,
        auftrag: str,
        titel: str = "",
        zeit: str = "",
        tage=None,
        minuten: int = 0,
        ordner: str = "",
        muster: str = "*",
        budget: int = 15,
    ) -> dict:
        sauber = " ".join(str(auftrag or "").split())[:1500]
        if len(sauber) < 4:
            raise AusloeserFehler("Schreib dazu, was Jon dann tun soll.")
        form = str(art or "").strip().lower()
        if form not in ARTEN:
            raise AusloeserFehler(
                "art muss taeglich, intervall, ordner oder start sein."
            )
        regel: dict = {
            "id": uuid.uuid4().hex[:10],
            "art": form,
            "titel": (titel or sauber)[:120],
            "auftrag": sauber,
            "aktiv": True,
            "budget": max(1, min(120, int(budget or 15))),
            "angelegt": _jetzt(),
            "zuletzt": 0.0,
            "treffer": 0,
        }
        if form == "taeglich":
            wann = str(zeit or "").strip()
            if not ZEIT_RE.match(wann):
                raise AusloeserFehler("zeit muss HH:MM sein, zum Beispiel 07:30.")
            regel["zeit"] = wann if len(wann) == 5 else f"0{wann}"
            regel["tage"] = tage_lesen(tage)
        elif form == "intervall":
            takt = int(minuten or 0)
            if takt < 5:
                raise AusloeserFehler("intervall braucht mindestens 5 Minuten.")
            regel["minuten"] = min(takt, 7 * 24 * 60)
        elif form == "ordner":
            pfad = Path(str(ordner or "")).expanduser()
            if not pfad.is_dir():
                raise AusloeserFehler(f"Den Ordner gibt es nicht: {pfad}")
            regel["ordner"] = str(pfad)
            regel["muster"] = str(muster or "*").strip() or "*"
            regel["bekannt"] = sorted(
                str(p.name) for p in pfad.glob(regel["muster"]) if p.is_file()
            )[-MAX_BEKANNT:]
        with self._lock:
            if len(self._regeln) >= MAX_REGELN:
                raise AusloeserFehler(
                    f"Mehr als {MAX_REGELN} Ausloeser sind nicht vorgesehen."
                )
            self._regeln.append(regel)
            self._sichern()
        return self.ansicht(regel)

    def ansicht(self, regel: dict) -> dict:
        daten = {
            "id": regel["id"],
            "art": regel["art"],
            "titel": regel["titel"],
            "auftrag": regel["auftrag"],
            "aktiv": bool(regel.get("aktiv", True)),
            "treffer": int(regel.get("treffer", 0)),
            "beschreibung": self.beschreiben(regel),
        }
        if regel.get("zuletzt"):
            daten["zuletzt"] = datetime.fromtimestamp(regel["zuletzt"]).strftime(
                "%d.%m.%Y %H:%M"
            )
        return daten

    def beschreiben(self, regel: dict) -> str:
        art = regel["art"]
        if art == "taeglich":
            tage = regel.get("tage") or []
            namen = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            wann = ", ".join(namen[t] for t in tage) if tage else "jeden Tag"
            return f"{wann} um {regel.get('zeit', '')} Uhr"
        if art == "intervall":
            takt = int(regel.get("minuten", 0))
            if takt % 60 == 0 and takt >= 60:
                return f"alle {takt // 60} Stunden"
            return f"alle {takt} Minuten"
        if art == "ordner":
            return f"wenn etwas Neues in {regel.get('ordner', '')} landet"
        return "bei jedem Start von Jon"

    def liste(self) -> dict:
        with self._lock:
            return {"ausloeser": [self.ansicht(r) for r in self._regeln]}

    def schalten(self, kennung: str, an: bool) -> dict:
        with self._lock:
            regel = self._finden(kennung)
            regel["aktiv"] = bool(an)
            self._sichern()
            return self.ansicht(regel)

    def loeschen(self, kennung: str) -> dict:
        with self._lock:
            regel = self._finden(kennung)
            self._regeln = [r for r in self._regeln if r["id"] != regel["id"]]
            self._sichern()
            return {"geloescht": regel["id"], "titel": regel["titel"]}

    def _faellig_taeglich(self, regel: dict, jetzt: datetime) -> bool:
        stunde, minute = [int(t) for t in str(regel.get("zeit", "0:0")).split(":")[:2]]
        tage = regel.get("tage") or []
        zuletzt = float(regel.get("zuletzt", 0) or 0)
        heute = jetzt.replace(hour=stunde, minute=minute, second=0, microsecond=0)
        for ziel in (heute, heute - timedelta(days=1)):
            if tage and ziel.weekday() not in tage:
                continue
            if jetzt < ziel or jetzt - ziel > timedelta(hours=6):
                continue
            if zuletzt < ziel.timestamp():
                return True
        return False

    def _neue_dateien(self, regel: dict) -> list[str]:
        ordner = Path(str(regel.get("ordner", ""))).expanduser()
        if not ordner.is_dir():
            return []
        bekannt = set(regel.get("bekannt") or [])
        gefunden = []
        for pfad in sorted(ordner.glob(str(regel.get("muster", "*")))):
            if not pfad.is_file() or pfad.name in bekannt:
                continue
            try:
                if _jetzt() - pfad.stat().st_mtime > 86400:
                    bekannt.add(pfad.name)
                    continue
            except OSError:
                continue
            gefunden.append(str(pfad))
            bekannt.add(pfad.name)
        regel["bekannt"] = sorted(bekannt)[-MAX_BEKANNT:]
        return gefunden[:MAX_NEUE_DATEIEN]

    def faellige(self, start: bool = False) -> list[tuple[dict, str]]:
        jetzt = datetime.now()
        stempel = _jetzt()
        offen: list[tuple[dict, str]] = []
        with self._lock:
            for regel in self._regeln:
                if not regel.get("aktiv", True):
                    continue
                art = regel["art"]
                if art == "start":
                    if not start:
                        continue
                    offen.append((regel, regel["auftrag"]))
                elif art == "taeglich":
                    if self._faellig_taeglich(regel, jetzt):
                        offen.append((regel, regel["auftrag"]))
                elif art == "intervall":
                    takt = int(regel.get("minuten", 60)) * 60
                    if stempel - float(regel.get("zuletzt", 0) or 0) >= takt:
                        offen.append((regel, regel["auftrag"]))
                elif art == "ordner":
                    for datei in self._neue_dateien(regel):
                        offen.append(
                            (
                                regel,
                                f"{regel['auftrag']}\n\nNeue Datei: {datei}",
                            )
                        )
            if offen:
                self._sichern()
        return offen

    def pruefen(self, start: bool = False) -> dict:
        from app.services.aufgaben_service import get_aufgaben_service

        dienst = get_aufgaben_service()
        gestartet: list[dict] = []
        for regel, auftrag in self.faellige(start=start):
            try:
                aufgabe = dienst.anlegen(
                    auftrag,
                    budget_minuten=int(regel.get("budget", 15)),
                    titel=regel["titel"],
                    quelle="ausloeser",
                )
            except Exception as fehler:
                leise(fehler, "services/ausloeser_service")
                continue
            if aufgabe.get("error"):
                continue
            with self._lock:
                regel["zuletzt"] = _jetzt()
                regel["treffer"] = int(regel.get("treffer", 0)) + 1
                self._sichern()
            gestartet.append(
                {
                    "ausloeser": regel["id"],
                    "titel": regel["titel"],
                    "aufgabe": aufgabe.get("id"),
                }
            )
        return {"gestartet": gestartet, "anzahl": len(gestartet)}

    def beim_start(self) -> dict:
        with self._lock:
            if self._gestartet:
                return {"gestartet": [], "anzahl": 0}
            self._gestartet = True
        return self.pruefen(start=True)


_dienst: AusloeserService | None = None
_dienst_lock = threading.Lock()


def get_ausloeser_service() -> AusloeserService:
    global _dienst
    with _dienst_lock:
        if _dienst is None:
            _dienst = AusloeserService()
        return _dienst
