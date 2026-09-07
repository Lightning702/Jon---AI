from __future__ import annotations

import threading
from datetime import datetime, timedelta

from app.db.database import session_scope
from app.db.models import Notiz

MAX_ZEICHEN = 4000
MAX_BEREICHE = 40


def _jetzt() -> datetime:
    return datetime.now()


class NotizblockService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _zeile(self, eintrag: Notiz) -> dict:
        return {
            "id": eintrag.id,
            "bereich": eintrag.bereich,
            "inhalt": eintrag.inhalt,
            "aktualisiert": eintrag.aktualisiert.isoformat(timespec="seconds")
            if eintrag.aktualisiert
            else "",
        }

    def lesen(self, bereich: str = "allgemein") -> str:
        with session_scope() as session:
            eintrag = (
                session.query(Notiz)
                .filter(Notiz.bereich == bereich[:48])
                .order_by(Notiz.aktualisiert.desc())
                .first()
            )
            return eintrag.inhalt if eintrag is not None else ""

    def schreiben(self, inhalt: str, bereich: str = "allgemein") -> dict:
        text = str(inhalt or "").strip()[:MAX_ZEICHEN]
        with session_scope() as session:
            eintrag = (
                session.query(Notiz)
                .filter(Notiz.bereich == bereich[:48])
                .order_by(Notiz.aktualisiert.desc())
                .first()
            )
            if eintrag is None:
                eintrag = Notiz(bereich=bereich[:48], inhalt=text)
                session.add(eintrag)
                session.flush()
            else:
                eintrag.inhalt = text
                eintrag.aktualisiert = _jetzt()
            return self._zeile(eintrag)

    def ergaenzen(self, zeile: str, bereich: str = "allgemein") -> dict:
        vorher = self.lesen(bereich)
        neu = (vorher + "\n" if vorher else "") + f"- {str(zeile).strip()}"
        return self.schreiben(neu[-MAX_ZEICHEN:], bereich)

    def leeren(self, bereich: str = "allgemein") -> bool:
        with session_scope() as session:
            zeilen = session.query(Notiz).filter(Notiz.bereich == bereich[:48]).all()
            for eintrag in zeilen:
                session.delete(eintrag)
            return bool(zeilen)

    def bereiche(self, limit: int = MAX_BEREICHE) -> list[dict]:
        with session_scope() as session:
            zeilen = (
                session.query(Notiz)
                .order_by(Notiz.aktualisiert.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def aufraeumen(self, tage: int = 45) -> int:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        with session_scope() as session:
            zeilen = session.query(Notiz).filter(Notiz.aktualisiert < grenze).all()
            for eintrag in zeilen:
                session.delete(eintrag)
            return len(zeilen)

    def prompt_block(self, bereich: str = "allgemein") -> str:
        inhalt = self.lesen(bereich)
        if not inhalt.strip():
            return ""
        return (
            "Dein Notizblock zu dieser Sache (dein Arbeitsgedaechtnis, gilt weiter):\n"
            + inhalt[:1500]
        )


_service: NotizblockService | None = None


def get_notizblock_service() -> NotizblockService:
    global _service
    if _service is None:
        _service = NotizblockService()
    return _service
