from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BrowserZustand:
    aktiv: bool = False
    url: str = ""
    titel: str = ""
    tab: str = ""
    tabs: list[dict] = field(default_factory=list)
    laden: str = "leer"
    beschreibung: str = ""
    ueberschriften: list[str] = field(default_factory=list)
    text: str = ""
    elemente: list[dict] = field(default_factory=list)
    letzte_aktion: str = ""
    fehler: str = ""
    plan_schritt: int = 0
    plan_schritte: int = 0
    plan_ziel: str = ""
    status: str = "bereit"
    hinweise: list[str] = field(default_factory=list)
    aktualisiert: str = ""

    def kompakt(self, mit_text: bool = True, max_elemente: int = 40) -> dict:
        daten: dict = {
            "url": self.url,
            "titel": self.titel,
            "tab": self.tab,
            "laden": self.laden,
        }
        if len(self.tabs) > 1:
            daten["tabs"] = self.tabs
        if self.beschreibung:
            daten["beschreibung"] = self.beschreibung
        if self.ueberschriften:
            daten["ueberschriften"] = self.ueberschriften[:8]
        if mit_text and self.text:
            daten["seitentext"] = self.text
        if self.elemente:
            daten["interaktive_elemente"] = self.elemente[:max_elemente]
        if self.fehler:
            daten["fehler"] = self.fehler
        if self.hinweise:
            daten["hinweise"] = self.hinweise
        return daten

    def als_dict(self) -> dict:
        return {
            "aktiv": self.aktiv,
            "url": self.url,
            "titel": self.titel,
            "tab": self.tab,
            "tabs": self.tabs,
            "laden": self.laden,
            "beschreibung": self.beschreibung,
            "ueberschriften": self.ueberschriften[:8],
            "elemente": len(self.elemente),
            "letzte_aktion": self.letzte_aktion,
            "fehler": self.fehler,
            "plan_schritt": self.plan_schritt,
            "plan_schritte": self.plan_schritte,
            "plan_ziel": self.plan_ziel,
            "status": self.status,
            "hinweise": self.hinweise,
            "aktualisiert": self.aktualisiert,
        }


class Zustandsspeicher:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._zustand = BrowserZustand()

    def lesen(self) -> BrowserZustand:
        with self._lock:
            return self._zustand

    def setzen(self, **felder) -> BrowserZustand:
        with self._lock:
            for name, wert in felder.items():
                if hasattr(self._zustand, name):
                    setattr(self._zustand, name, wert)
            self._zustand.aktualisiert = datetime.now().isoformat(timespec="seconds")
            return self._zustand

    def uebernehmen(self, daten: dict, aktion: str) -> BrowserZustand:
        return self.setzen(
            aktiv=True,
            url=str(daten.get("url", "")),
            titel=str(daten.get("titel", "")),
            tab=str(daten.get("tab", "")),
            tabs=list(daten.get("tabs", []) or []),
            laden=str(daten.get("laden", "bereit")),
            beschreibung=str(daten.get("beschreibung", "")),
            ueberschriften=list(daten.get("ueberschriften", []) or []),
            text=str(daten.get("seitentext", "") or daten.get("text", "")),
            elemente=list(daten.get("interaktive_elemente", []) or []),
            letzte_aktion=aktion,
            fehler=str(daten.get("fehler", "")),
            hinweise=list(daten.get("hinweise", []) or []),
        )

    def zuruecksetzen(self) -> None:
        with self._lock:
            self._zustand = BrowserZustand()


_speicher: dict[str, Zustandsspeicher] = {}
_speicher_lock = threading.Lock()


def get_zustand(sitzung: str = "") -> Zustandsspeicher:
    from app.services.browser.sitzung import aktuell

    schluessel = sitzung or aktuell()
    with _speicher_lock:
        if schluessel not in _speicher:
            _speicher[schluessel] = Zustandsspeicher()
        return _speicher[schluessel]


def alle_zustaende() -> dict[str, Zustandsspeicher]:
    with _speicher_lock:
        return dict(_speicher)
