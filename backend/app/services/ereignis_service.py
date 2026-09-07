from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

from app.db.database import session_scope
from app.db.models import Ereignis
from app.services.semantik import aehnlichkeit, vektor
from app.services.zeitraum import Spanne, verstehen

ARTEN = (
    "chat",
    "werkzeug",
    "browser",
    "datei",
    "termin",
    "nachricht",
    "bildschirm",
    "system",
    "ziel",
    "erkenntnis",
    "fehler",
)

STILL = {
    "wait",
    "recall",
    "list_skills",
    "read_skill",
    "browser_status",
    "browser_read",
    "get_screen_info",
    "list_windows",
    "was_war",
    "verlauf_heute",
}

MAX_DETAIL = 600
AUFBEWAHRUNG_TAGE = 400


def _jetzt() -> datetime:
    return datetime.now()


def _kurz(wert, grenze: int = MAX_DETAIL) -> str:
    if isinstance(wert, str):
        text = wert
    else:
        try:
            text = json.dumps(wert, ensure_ascii=False, default=str)
        except Exception:
            text = str(wert)
    text = " ".join(text.split())
    return text if len(text) <= grenze else text[: grenze - 1] + "…"


class EreignisService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vektoren: dict[int, list[float]] = {}

    def notieren(
        self,
        art: str,
        titel: str,
        detail: str = "",
        quelle: str = "app",
        bedeutung: float = 0.4,
        gespraech: str = "",
        gelungen: bool = True,
    ) -> int:
        if not titel.strip():
            return 0
        try:
            with session_scope() as session:
                eintrag = Ereignis(
                    art=str(art or "system")[:24],
                    titel=_kurz(titel, 200),
                    detail=_kurz(detail),
                    quelle=str(quelle or "app")[:24],
                    bedeutung=float(max(0.0, min(1.0, bedeutung))),
                    gespraech=str(gespraech or "")[:32],
                    gelungen=1 if gelungen else 0,
                    zeit=_jetzt(),
                )
                session.add(eintrag)
                session.flush()
                return int(eintrag.id)
        except Exception:
            return 0

    def _zeile(self, eintrag: Ereignis) -> dict:
        return {
            "id": int(eintrag.id),
            "zeit": eintrag.zeit.isoformat(timespec="seconds") if eintrag.zeit else "",
            "art": eintrag.art,
            "titel": eintrag.titel,
            "detail": eintrag.detail,
            "quelle": eintrag.quelle,
            "bedeutung": float(eintrag.bedeutung or 0.0),
            "gelungen": bool(eintrag.gelungen),
            "gespraech": eintrag.gespraech or "",
        }

    def spanne(
        self,
        von: datetime,
        bis: datetime,
        arten: tuple[str, ...] = (),
        limit: int = 200,
        mindest_bedeutung: float = 0.0,
    ) -> list[dict]:
        with session_scope() as session:
            frage = session.query(Ereignis).filter(
                Ereignis.zeit >= von, Ereignis.zeit <= bis
            )
            if arten:
                frage = frage.filter(Ereignis.art.in_(list(arten)))
            if mindest_bedeutung > 0:
                frage = frage.filter(Ereignis.bedeutung >= mindest_bedeutung)
            zeilen = frage.order_by(Ereignis.zeit.asc()).limit(limit).all()
            return [self._zeile(z) for z in zeilen]

    def zeitraum(self, text: str, limit: int = 200) -> dict:
        gefunden: Spanne = verstehen(text)
        eintraege = self.spanne(gefunden.von, gefunden.bis, limit=limit)
        return {
            "zeitraum": gefunden.als_dict(),
            "anzahl": len(eintraege),
            "ereignisse": eintraege,
        }

    def suchen(self, text: str, limit: int = 20, tage: int = 120) -> list[dict]:
        frage = str(text or "").strip()
        if not frage:
            return []
        bis = _jetzt()
        von = bis - timedelta(days=max(1, tage))
        kandidaten = self.spanne(von, bis, limit=2000)
        gefragt = vektor(frage)
        bewertet = []
        for eintrag in kandidaten:
            werte = vektor(f"{eintrag['titel']} {eintrag['detail']}")
            bewertet.append((aehnlichkeit(gefragt, werte), eintrag))
        bewertet.sort(key=lambda paar: paar[0], reverse=True)
        return [e for wert, e in bewertet if wert >= 0.06][:limit]

    def tagesbild(self, text: str = "heute") -> dict:
        gefunden = verstehen(text)
        eintraege = self.spanne(gefunden.von, gefunden.bis, limit=500)
        nach_art: dict[str, int] = {}
        werkzeuge: dict[str, int] = {}
        fehler = []
        for eintrag in eintraege:
            nach_art[eintrag["art"]] = nach_art.get(eintrag["art"], 0) + 1
            if eintrag["art"] == "werkzeug":
                werkzeuge[eintrag["titel"]] = werkzeuge.get(eintrag["titel"], 0) + 1
            if not eintrag["gelungen"]:
                fehler.append(eintrag["titel"])
        hoehepunkte = sorted(
            eintraege, key=lambda e: e["bedeutung"], reverse=True
        )[:12]
        return {
            "zeitraum": gefunden.als_dict(),
            "anzahl": len(eintraege),
            "nach_art": nach_art,
            "haeufigste_werkzeuge": sorted(
                werkzeuge.items(), key=lambda paar: paar[1], reverse=True
            )[:8],
            "fehler": fehler[:10],
            "hoehepunkte": [
                {
                    "zeit": e["zeit"][11:16],
                    "art": e["art"],
                    "titel": e["titel"],
                    "detail": e["detail"][:160],
                }
                for e in hoehepunkte
            ],
        }

    def aufraeumen(self, tage: int = AUFBEWAHRUNG_TAGE) -> int:
        grenze = _jetzt() - timedelta(days=max(30, tage))
        with session_scope() as session:
            treffer = (
                session.query(Ereignis)
                .filter(Ereignis.zeit < grenze, Ereignis.bedeutung < 0.7)
                .all()
            )
            for eintrag in treffer:
                session.delete(eintrag)
            return len(treffer)

    def werkzeug_notieren(
        self, quelle: str, werkzeug: str, args, ergebnis, gelungen: bool
    ) -> None:
        if werkzeug in STILL:
            return
        bedeutung = 0.35
        try:
            from app.services.risiko import bewerten

            stufe = bewerten(werkzeug, args if isinstance(args, dict) else {})
            bedeutung = {"niedrig": 0.25, "mittel": 0.45, "hoch": 0.75}.get(
                stufe.risiko, 0.4
            )
        except Exception:
            bedeutung = 0.35
        if not gelungen:
            bedeutung = max(bedeutung, 0.6)
        klartext = ""
        try:
            from app.services.tools import describe_tool

            klartext = describe_tool(werkzeug, args if isinstance(args, dict) else {})
        except Exception:
            klartext = ""
        self.notieren(
            "fehler" if not gelungen else "werkzeug",
            werkzeug,
            f"{klartext} ergebnis={_kurz(ergebnis, 220)}",
            quelle=quelle,
            bedeutung=bedeutung,
            gelungen=gelungen,
        )


_service: EreignisService | None = None


def get_ereignis_service() -> EreignisService:
    global _service
    if _service is None:
        _service = EreignisService()
    return _service
