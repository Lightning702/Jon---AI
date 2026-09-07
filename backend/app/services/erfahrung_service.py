from __future__ import annotations

import threading
from datetime import datetime
from urllib.parse import urlparse

from app.db.database import session_scope
from app.db.models import Erfahrung

KLAPPT = "klappt"
KLAPPT_NICHT = "klappt_nicht"
MAX_JE_BEREICH = 12


def _jetzt() -> datetime:
    return datetime.now()


def bereich_fuer(werkzeug: str, args: dict | None = None) -> str:
    werte = args or {}
    if werkzeug.startswith("browser_"):
        ziel = str(werte.get("url") or werte.get("ziel") or "")
        if ziel:
            try:
                host = urlparse(ziel if "://" in ziel else f"https://{ziel}").netloc
                if host:
                    return f"web:{host.lower().removeprefix('www.')}"
            except Exception:
                return "web:unbekannt"
        try:
            from app.services.browser.zustand import get_zustand

            host = urlparse(get_zustand().lesen().url).netloc
            if host:
                return f"web:{host.lower().removeprefix('www.')}"
        except Exception:
            return "web:unbekannt"
    return f"werkzeug:{werkzeug}"


class ErfahrungService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _zeile(self, eintrag: Erfahrung) -> dict:
        return {
            "id": eintrag.id,
            "bereich": eintrag.bereich,
            "art": eintrag.art,
            "text": eintrag.text,
            "treffer": int(eintrag.treffer or 1),
            "gewicht": float(eintrag.gewicht or 0.5),
            "aktualisiert": eintrag.aktualisiert.isoformat(timespec="seconds")
            if eintrag.aktualisiert
            else "",
        }

    def notieren(
        self, bereich: str, text: str, art: str = KLAPPT, gewicht: float = 0.5
    ) -> dict:
        sauber = " ".join(str(text or "").split())[:400]
        if not sauber or not bereich:
            return {"error": "leer"}
        with session_scope() as session:
            vorhanden = (
                session.query(Erfahrung)
                .filter(
                    Erfahrung.bereich == bereich[:80],
                    Erfahrung.art == art,
                    Erfahrung.text == sauber,
                )
                .first()
            )
            if vorhanden is not None:
                vorhanden.treffer = int(vorhanden.treffer or 1) + 1
                vorhanden.gewicht = min(1.0, float(vorhanden.gewicht or 0.5) + 0.08)
                vorhanden.aktualisiert = _jetzt()
                return self._zeile(vorhanden)
            eintrag = Erfahrung(
                bereich=bereich[:80], art=art, text=sauber, gewicht=gewicht
            )
            session.add(eintrag)
            session.flush()
            return self._zeile(eintrag)

    def fuer(self, bereich: str, limit: int = MAX_JE_BEREICH) -> list[dict]:
        with session_scope() as session:
            zeilen = (
                session.query(Erfahrung)
                .filter(Erfahrung.bereich == bereich[:80])
                .order_by(Erfahrung.gewicht.desc(), Erfahrung.treffer.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def alle(self, limit: int = 200) -> list[dict]:
        with session_scope() as session:
            zeilen = (
                session.query(Erfahrung)
                .order_by(Erfahrung.aktualisiert.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def aus_ergebnis(self, werkzeug: str, args: dict, ergebnis: str, ok: bool) -> None:
        bereich = bereich_fuer(werkzeug, args)
        text = ""
        if ok:
            if werkzeug.startswith("browser_"):
                ziel = str(args.get("element") or args.get("url") or "").strip()
                if ziel:
                    text = f"{werkzeug} mit '{ziel[:80]}' hat funktioniert."
        else:
            grund = " ".join(str(ergebnis or "").split())[:160]
            text = f"{werkzeug} scheiterte: {grund}"
        if not text:
            return
        self.notieren(bereich, text, KLAPPT if ok else KLAPPT_NICHT, 0.5 if ok else 0.7)

    def prompt_block(self, bereich: str, limit: int = 5) -> str:
        eintraege = self.fuer(bereich, limit)
        if not eintraege:
            return ""
        zeilen = [
            f"- {'funktioniert' if e['art'] == KLAPPT else 'Achtung'}: {e['text']}"
            for e in eintraege
        ]
        return f"Deine Erfahrungen mit {bereich}:\n" + "\n".join(zeilen)

    def vergessen(self, bereich: str = "") -> int:
        with session_scope() as session:
            frage = session.query(Erfahrung)
            if bereich:
                frage = frage.filter(Erfahrung.bereich == bereich[:80])
            zeilen = frage.all()
            for eintrag in zeilen:
                session.delete(eintrag)
            return len(zeilen)


_service: ErfahrungService | None = None


def get_erfahrung_service() -> ErfahrungService:
    global _service
    if _service is None:
        _service = ErfahrungService()
    return _service
