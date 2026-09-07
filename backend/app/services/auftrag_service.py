from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import Auftrag

OFFEN = "offen"
LAEUFT = "laeuft"
PAUSIERT = "pausiert"
UNTERBROCHEN = "unterbrochen"
FERTIG = "fertig"
FEHLER = "fehler"
ABGEBROCHEN = "abgebrochen"

AKTIV = (OFFEN, LAEUFT, PAUSIERT, UNTERBROCHEN)


def _jetzt() -> datetime:
    return datetime.now()


class AuftragService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _zeile(self, eintrag: Auftrag) -> dict:
        try:
            eingabe = json.loads(eintrag.eingabe or "{}")
        except Exception as _fehler:
            leise(_fehler, "services/auftrag_service")
            eingabe = {}
        return {
            "id": eintrag.id,
            "art": eintrag.art,
            "titel": eintrag.titel,
            "zustand": eintrag.zustand,
            "fortschritt": eintrag.fortschritt,
            "schritt": eintrag.schritt,
            "schritte": eintrag.schritte,
            "eingabe": eingabe,
            "ergebnis": eintrag.ergebnis or "",
            "fehler": eintrag.fehler or "",
            "versuche": int(eintrag.versuche or 0),
            "erstellt": eintrag.erstellt.isoformat(timespec="seconds")
            if eintrag.erstellt
            else "",
            "aktualisiert": eintrag.aktualisiert.isoformat(timespec="seconds")
            if eintrag.aktualisiert
            else "",
            "gespraech": eintrag.gespraech or "",
        }

    def anlegen(
        self, art: str, titel: str, eingabe: dict | None = None, gespraech: str = ""
    ) -> str:
        with session_scope() as session:
            eintrag = Auftrag(
                art=str(art)[:32],
                titel=str(titel)[:200],
                eingabe=json.dumps(eingabe or {}, ensure_ascii=False)[:4000],
                zustand=LAEUFT,
                gespraech=str(gespraech or "")[:32],
                erstellt=_jetzt(),
                aktualisiert=_jetzt(),
            )
            session.add(eintrag)
            session.flush()
            return eintrag.id

    def melden(
        self,
        kennung: str,
        zustand: str | None = None,
        schritt: int | None = None,
        schritte: int | None = None,
        ergebnis: str | None = None,
        fehler: str | None = None,
    ) -> None:
        if not kennung:
            return
        with session_scope() as session:
            eintrag = session.get(Auftrag, kennung)
            if eintrag is None:
                return
            if zustand:
                eintrag.zustand = zustand
            if schritt is not None:
                eintrag.schritt = int(schritt)
            if schritte is not None:
                eintrag.schritte = int(schritte)
            if ergebnis is not None:
                eintrag.ergebnis = str(ergebnis)[:4000]
            if fehler is not None:
                eintrag.fehler = str(fehler)[:1000]
            if eintrag.schritte:
                eintrag.fortschritt = round(
                    min(1.0, max(0.0, eintrag.schritt / max(1, eintrag.schritte))), 3
                )
            eintrag.aktualisiert = _jetzt()

    def holen(self, kennung: str) -> dict | None:
        with session_scope() as session:
            eintrag = session.get(Auftrag, kennung)
            return self._zeile(eintrag) if eintrag is not None else None

    def liste(self, zustaende: tuple[str, ...] = (), limit: int = 30) -> list[dict]:
        with session_scope() as session:
            frage = session.query(Auftrag)
            if zustaende:
                frage = frage.filter(Auftrag.zustand.in_(list(zustaende)))
            zeilen = frage.order_by(Auftrag.aktualisiert.desc()).limit(limit).all()
            return [self._zeile(z) for z in zeilen]

    def offene(self) -> list[dict]:
        return self.liste(AKTIV)

    def unterbrochene_markieren(self) -> int:
        with session_scope() as session:
            zeilen = session.query(Auftrag).filter(Auftrag.zustand == LAEUFT).all()
            for eintrag in zeilen:
                eintrag.zustand = UNTERBROCHEN
                eintrag.fehler = "Jon wurde beendet, waehrend der Auftrag lief."
                eintrag.aktualisiert = _jetzt()
            return len(zeilen)

    def versuch_zaehlen(self, kennung: str) -> int:
        with session_scope() as session:
            eintrag = session.get(Auftrag, kennung)
            if eintrag is None:
                return 0
            eintrag.versuche = int(eintrag.versuche or 0) + 1
            eintrag.zustand = LAEUFT
            eintrag.aktualisiert = _jetzt()
            return int(eintrag.versuche)

    def aufraeumen(self, tage: int = 30) -> int:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        with session_scope() as session:
            zeilen = (
                session.query(Auftrag)
                .filter(
                    Auftrag.aktualisiert < grenze,
                    Auftrag.zustand.in_([FERTIG, ABGEBROCHEN, FEHLER]),
                )
                .all()
            )
            for eintrag in zeilen:
                session.delete(eintrag)
            return len(zeilen)


_service: AuftragService | None = None


def get_auftrag_service() -> AuftragService:
    global _service
    if _service is None:
        _service = AuftragService()
    return _service
