from __future__ import annotations

import asyncio
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from app.core.fehler import leise

MAX_VERLAUF = 300

WAHRNEHMUNG = "wahrnehmung"
HANDLUNG = "handlung"
GEDANKE = "gedanke"
ZIEL = "ziel"
FEHLER = "fehler"


@dataclass
class Signal:
    art: str
    name: str
    daten: dict = field(default_factory=dict)
    quelle: str = "app"
    zeit: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def als_dict(self) -> dict:
        return {
            "art": self.art,
            "name": self.name,
            "daten": self.daten,
            "quelle": self.quelle,
            "zeit": self.zeit,
        }


Hoerer = Callable[[Signal], Any]


class Kern:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hoerer: dict[str, list[Hoerer]] = {}
        self._verlauf: deque[Signal] = deque(maxlen=MAX_VERLAUF)
        self._zaehler: dict[str, int] = {}

    def hoeren(self, art: str, hoerer: Hoerer) -> None:
        with self._lock:
            self._hoerer.setdefault(art, []).append(hoerer)

    def vergessen(self, art: str) -> None:
        with self._lock:
            self._hoerer.pop(art, None)

    def senden(self, signal: Signal) -> int:
        with self._lock:
            self._verlauf.append(signal)
            self._zaehler[signal.art] = self._zaehler.get(signal.art, 0) + 1
            hoerer = list(self._hoerer.get(signal.art, [])) + list(
                self._hoerer.get("*", [])
            )
        erreicht = 0
        for eintrag in hoerer:
            try:
                ergebnis = eintrag(signal)
                if asyncio.iscoroutine(ergebnis):
                    try:
                        schleife = asyncio.get_running_loop()
                        schleife.create_task(ergebnis)
                    except RuntimeError:
                        ergebnis.close()
                erreicht += 1
            except Exception as _fehler:
                leise(_fehler, "services/kern")
        return erreicht

    def melden(self, art: str, name: str, daten: dict | None = None, quelle: str = "app") -> Signal:
        signal = Signal(art=art, name=name, daten=daten or {}, quelle=quelle)
        self.senden(signal)
        return signal

    def verlauf(self, limit: int = 50, art: str = "") -> list[dict]:
        with self._lock:
            eintraege = list(self._verlauf)
        if art:
            eintraege = [s for s in eintraege if s.art == art]
        return [s.als_dict() for s in eintraege[-limit:]]

    def stand(self) -> dict:
        with self._lock:
            return {
                "signale": dict(self._zaehler),
                "hoerer": {art: len(liste) for art, liste in self._hoerer.items()},
                "verlauf": len(self._verlauf),
            }


_kern: Kern | None = None
_verdrahtet = False


def get_kern() -> Kern:
    global _kern
    if _kern is None:
        _kern = Kern()
    return _kern


def _auf_handlung(signal: Signal) -> None:
    from app.services.ereignis_service import get_ereignis_service

    daten = signal.daten or {}
    get_ereignis_service().notieren(
        "werkzeug" if daten.get("gelungen", True) else "fehler",
        signal.name,
        str(daten.get("detail", ""))[:400],
        quelle=signal.quelle,
        bedeutung=float(daten.get("bedeutung", 0.4)),
        gelungen=bool(daten.get("gelungen", True)),
    )


def _auf_wahrnehmung(signal: Signal) -> None:
    from app.services.handlungsraum_service import get_handlungsraum_service

    get_handlungsraum_service().melden(signal.name, signal.daten or {})


def _auf_ziel(signal: Signal) -> None:
    from app.services.ereignis_service import get_ereignis_service

    get_ereignis_service().notieren(
        "ziel",
        signal.name,
        str((signal.daten or {}).get("detail", ""))[:400],
        quelle=signal.quelle,
        bedeutung=0.6,
    )


def verdrahten() -> None:
    global _verdrahtet
    if _verdrahtet:
        return
    kern = get_kern()
    kern.hoeren(HANDLUNG, _auf_handlung)
    kern.hoeren(WAHRNEHMUNG, _auf_wahrnehmung)
    kern.hoeren(ZIEL, _auf_ziel)
    _verdrahtet = True
