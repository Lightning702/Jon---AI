from __future__ import annotations

import threading
from datetime import datetime, timedelta

from app.db.database import session_scope
from app.db.models import Ziel
from app.services.zeitraum import verstehen

OFFEN = "offen"
LAEUFT = "laeuft"
WARTET = "wartet"
ERLEDIGT = "erledigt"
VERWORFEN = "verworfen"

AKTIV = (OFFEN, LAEUFT, WARTET)


def _jetzt() -> datetime:
    return datetime.now()


class ZielService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _zeile(self, eintrag: Ziel) -> dict:
        frist = eintrag.frist
        tage = None
        if frist is not None:
            tage = (frist.date() - _jetzt().date()).days
        return {
            "id": eintrag.id,
            "titel": eintrag.titel,
            "beschreibung": eintrag.beschreibung or "",
            "zustand": eintrag.zustand,
            "naechster_schritt": eintrag.naechster_schritt or "",
            "frist": frist.isoformat(timespec="minutes") if frist else "",
            "tage_bis_frist": tage,
            "haengt_an": eintrag.haengt_an or "",
            "wichtigkeit": float(eintrag.wichtigkeit or 0.5),
            "fortschritt": float(eintrag.fortschritt or 0.0),
            "quelle": eintrag.quelle,
            "aktualisiert": eintrag.aktualisiert.isoformat(timespec="seconds")
            if eintrag.aktualisiert
            else "",
        }

    def anlegen(
        self,
        titel: str,
        beschreibung: str = "",
        frist: str = "",
        naechster_schritt: str = "",
        wichtigkeit: float = 0.5,
        haengt_an: str = "",
        quelle: str = "nutzer",
    ) -> dict:
        sauber = str(titel or "").strip()[:200]
        if not sauber:
            return {"error": "Kein Titel angegeben."}
        stichtag = None
        if frist.strip():
            spanne = verstehen(frist)
            stichtag = spanne.bis
        with session_scope() as session:
            vorhanden = (
                session.query(Ziel)
                .filter(Ziel.titel == sauber, Ziel.zustand.in_(list(AKTIV)))
                .first()
            )
            if vorhanden is not None:
                return self._zeile(vorhanden)
            eintrag = Ziel(
                titel=sauber,
                beschreibung=beschreibung[:2000],
                frist=stichtag,
                naechster_schritt=naechster_schritt[:500],
                wichtigkeit=float(max(0.0, min(1.0, wichtigkeit))),
                haengt_an=haengt_an[:32],
                quelle=quelle[:24],
            )
            session.add(eintrag)
            session.flush()
            return self._zeile(eintrag)

    def aktualisieren(
        self,
        kennung: str,
        zustand: str = "",
        naechster_schritt: str = "",
        fortschritt: float | None = None,
        frist: str = "",
        beschreibung: str = "",
    ) -> dict:
        with session_scope() as session:
            eintrag = session.get(Ziel, kennung)
            if eintrag is None:
                return {"error": f"Ziel {kennung} gibt es nicht."}
            if zustand:
                eintrag.zustand = zustand
            if naechster_schritt:
                eintrag.naechster_schritt = naechster_schritt[:500]
            if fortschritt is not None:
                eintrag.fortschritt = float(max(0.0, min(1.0, fortschritt)))
            if beschreibung:
                eintrag.beschreibung = beschreibung[:2000]
            if frist:
                eintrag.frist = verstehen(frist).bis
            eintrag.aktualisiert = _jetzt()
            return self._zeile(eintrag)

    def liste(self, zustaende: tuple[str, ...] = AKTIV, limit: int = 50) -> list[dict]:
        with session_scope() as session:
            frage = session.query(Ziel)
            if zustaende:
                frage = frage.filter(Ziel.zustand.in_(list(zustaende)))
            zeilen = (
                frage.order_by(Ziel.wichtigkeit.desc(), Ziel.aktualisiert.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def faellig(self, tage: int = 2) -> list[dict]:
        grenze = _jetzt() + timedelta(days=max(0, tage))
        offen = self.liste()
        return [
            z
            for z in offen
            if z["frist"] and datetime.fromisoformat(z["frist"]) <= grenze
        ]

    def bereit(self) -> list[dict]:
        alle = {z["id"]: z for z in self.liste()}
        ergebnis = []
        for ziel in alle.values():
            haengt = ziel["haengt_an"]
            if haengt and haengt in alle:
                continue
            ergebnis.append(ziel)
        return sorted(ergebnis, key=lambda z: z["wichtigkeit"], reverse=True)

    def loeschen(self, kennung: str) -> bool:
        with session_scope() as session:
            eintrag = session.get(Ziel, kennung)
            if eintrag is None:
                return False
            session.delete(eintrag)
            return True

    def prompt_block(self, limit: int = 6) -> str:
        offen = self.bereit()[:limit]
        if not offen:
            return ""
        zeilen = []
        for ziel in offen:
            frist = f", faellig {ziel['frist'][:10]}" if ziel["frist"] else ""
            schritt = (
                f" Naechster Schritt: {ziel['naechster_schritt']}"
                if ziel["naechster_schritt"]
                else ""
            )
            zeilen.append(f"- {ziel['titel']} ({ziel['zustand']}{frist}).{schritt}")
        return (
            "Daran arbeitet ihr gerade (Jons Ziele - sprich sie an, wenn es passt):\n"
            + "\n".join(zeilen)
        )


_service: ZielService | None = None


def get_ziel_service() -> ZielService:
    global _service
    if _service is None:
        _service = ZielService()
    return _service
