from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.core.fehler import leise

WARTEZEIT = 75.0
FRISCH = 45.0
MAX_OFFEN = 12

SCHREIB_OPS = {"click", "fill", "press", "select", "upload"}
KENNT = {
    "goto",
    "read",
    "beschreiben",
    "click",
    "fill",
    "press",
    "select",
    "scroll",
    "wait_element",
    "wait_navigation",
    "back",
    "forward",
    "reload",
    "tab_new",
    "tab_switch",
    "tab_close",
    "screenshot",
    "status",
    "zustimmung",
    "close",
}


class Auftrag:
    __slots__ = ("kennung", "op", "args", "fertig", "ergebnis", "fehler", "gestellt")

    def __init__(self, op: str, args: dict) -> None:
        self.kennung = uuid.uuid4().hex[:12]
        self.op = op
        self.args = args
        self.fertig = threading.Event()
        self.ergebnis: dict[str, Any] = {}
        self.fehler = ""
        self.gestellt = time.time()

    def als_dict(self) -> dict:
        return {"id": self.kennung, "op": self.op, "args": self.args}


_lock = threading.Lock()
_wartend: list[Auftrag] = []
_laufend: dict[str, Auftrag] = {}
_letzter_poll = 0.0
_fenster = False
_zuletzt_gesehen: dict[str, Any] = {}


def melden(fenster_offen: bool, seite: dict | None = None) -> None:
    global _letzter_poll, _fenster, _zuletzt_gesehen
    with _lock:
        _letzter_poll = time.time()
        _fenster = bool(fenster_offen)
        if isinstance(seite, dict) and seite:
            _zuletzt_gesehen = seite


def verbunden() -> bool:
    with _lock:
        return (time.time() - _letzter_poll) < FRISCH


def fenster_offen() -> bool:
    with _lock:
        return _fenster and (time.time() - _letzter_poll) < FRISCH


def aktiv() -> bool:
    if not verbunden():
        return False
    try:
        from app.services.settings_service import get_settings_service

        motor = str(
            get_settings_service().get().get("browser_motor", "privat")
        ).strip().lower()
    except Exception as _fehler:
        leise(_fehler, "services/browser/privatbruecke")
        motor = "privat"
    return motor != "playwright"


def abholen() -> dict | None:
    with _lock:
        if not _wartend:
            return None
        auftrag = _wartend.pop(0)
        _laufend[auftrag.kennung] = auftrag
        return auftrag.als_dict()


def antworten(kennung: str, ok: bool, daten: dict | None, fehler: str = "") -> bool:
    with _lock:
        auftrag = _laufend.pop(str(kennung or ""), None)
    if auftrag is None:
        return False
    auftrag.ergebnis = daten if isinstance(daten, dict) else {}
    auftrag.fehler = "" if ok else (fehler or "Der private Browser meldete einen Fehler.")
    auftrag.fertig.set()
    return True


def aufrufen(op: str, args: dict | None = None, wartezeit: float = WARTEZEIT) -> dict:
    from app.services.browser.manager import BrowserFehler

    name = str(op or "").strip()
    if name not in KENNT:
        raise BrowserFehler(
            f"Der private Browser kann '{name}' nicht - dafuer braucht Jon den "
            "Playwright-Browser (Einstellungen: Browser-Motor)."
        )
    auftrag = Auftrag(name, dict(args or {}))
    with _lock:
        if len(_wartend) >= MAX_OFFEN:
            raise BrowserFehler(
                "Im privaten Browser stauen sich zu viele Auftraege - warte kurz."
            )
        _wartend.append(auftrag)
    if not auftrag.fertig.wait(timeout=wartezeit):
        with _lock:
            _laufend.pop(auftrag.kennung, None)
            if auftrag in _wartend:
                _wartend.remove(auftrag)
        raise BrowserFehler(
            "Der private Browser hat nicht geantwortet. Ist das Fenster noch offen?"
        )
    if auftrag.fehler:
        raise BrowserFehler(auftrag.fehler)
    return auftrag.ergebnis


def stand() -> dict:
    motor = "privat" if aktiv() else "playwright"
    with _lock:
        return {
            "verbunden": (time.time() - _letzter_poll) < FRISCH,
            "fenster": _fenster,
            "motor": motor,
            "wartend": len(_wartend),
            "laufend": len(_laufend),
            "seite": dict(_zuletzt_gesehen),
        }


def zuruecksetzen() -> None:
    global _letzter_poll, _fenster
    with _lock:
        for auftrag in list(_wartend) + list(_laufend.values()):
            auftrag.fehler = "Der private Browser wurde getrennt."
            auftrag.fertig.set()
        _wartend.clear()
        _laufend.clear()
        _letzter_poll = 0.0
        _fenster = False


class PrivatManager:
    def __init__(self, sitzung: str = "standard") -> None:
        self.sitzung = sitzung

    @property
    def offen(self) -> bool:
        return fenster_offen()

    def aufrufen(self, op: str, args: dict | None = None) -> dict:
        from app.services.browser.manager import BrowserFehler

        try:
            daten = aufrufen(op, args)
        except BrowserFehler as exc:
            return {"ok": False, "fehler": str(exc), "veraltet": "gibt es" in str(exc)}
        if op == "screenshot" and daten.get("bild"):
            daten["datei"] = _bild_sichern(str(daten.pop("bild")))
        if op == "status":
            daten["aktiv"] = fenster_offen()
        daten["ok"] = True
        return daten

    def schliessen(self) -> dict:
        try:
            aufrufen("close", {}, wartezeit=10.0)
        except Exception as _fehler:
            leise(_fehler, "services/browser/privatbruecke")
        return {"ok": True, "geschlossen": True, "browser": "Jons privater Browser"}


_manager = PrivatManager()


def manager(sitzung: str = "standard") -> PrivatManager:
    _manager.sitzung = sitzung or "standard"
    return _manager


def skripte() -> dict:
    from app.services.browser.elemente import (
        BESCHREIBUNG_JS,
        ELEMENTE_JS,
        MAX_ELEMENTE,
        SEITE_JS,
        TEXT_LIMIT,
        ZUSTIMMUNG_JS,
    )

    return {
        "elemente": ELEMENTE_JS,
        "seite": SEITE_JS,
        "beschreibung": BESCHREIBUNG_JS,
        "zustimmung": ZUSTIMMUNG_JS,
        "max_elemente": MAX_ELEMENTE,
        "text_limit": TEXT_LIMIT,
    }


def _bild_sichern(datenurl: str) -> str:
    import base64
    from datetime import datetime

    from app.core.config import DATA_DIR

    roh = datenurl.split(",", 1)[-1]
    ordner = DATA_DIR / "browser" / "screenshots"
    ordner.mkdir(parents=True, exist_ok=True)
    datei = ordner / f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
    datei.write_bytes(base64.b64decode(roh))
    return str(datei)
