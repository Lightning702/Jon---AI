from __future__ import annotations

import json
import re
import threading
from datetime import datetime

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import Beziehung, Entitaet
from app.services.semantik import aehnlichkeit, normieren, vektor

ARTEN = ("person", "projekt", "geraet", "ort", "firma", "sache", "termin", "konto")

GLEICH_SCHWELLE = 0.86

MUSTER = (
    (re.compile(r"(?i)\b(mein|meine|unser|unsere)\s+(\w{3,30})\s+hei(?:ss|ß)t\s+([A-ZÄÖÜ][\w-]{1,30})"), "sache"),
    (re.compile(r"(?i)\bich\s+arbeite\s+(?:bei|fuer|für)\s+([A-ZÄÖÜ][\w &.-]{2,40})"), "firma"),
    (re.compile(r"(?i)\bich\s+wohne\s+in\s+([A-ZÄÖÜ][\w -]{2,40})"), "ort"),
    (re.compile(r"(?i)\bprojekt\s+([A-ZÄÖÜ][\w -]{2,40})"), "projekt"),
)


def _jetzt() -> datetime:
    return datetime.now()


class WeltmodellService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vektoren: dict[str, list[float]] = {}

    def _zeile(self, eintrag: Entitaet) -> dict:
        try:
            merkmale = json.loads(eintrag.merkmale or "{}")
        except Exception as _fehler:
            leise(_fehler, "services/weltmodell_service")
            merkmale = {}
        return {
            "id": eintrag.id,
            "art": eintrag.art,
            "name": eintrag.name,
            "beschreibung": eintrag.beschreibung,
            "merkmale": merkmale,
            "wichtigkeit": float(eintrag.wichtigkeit or 0.5),
            "erwaehnungen": int(eintrag.erwaehnungen or 1),
            "gesehen": eintrag.gesehen.isoformat(timespec="seconds")
            if eintrag.gesehen
            else "",
        }

    def alle(self, art: str = "", limit: int = 300) -> list[dict]:
        with session_scope() as session:
            frage = session.query(Entitaet)
            if art:
                frage = frage.filter(Entitaet.art == art)
            zeilen = (
                frage.order_by(Entitaet.wichtigkeit.desc(), Entitaet.gesehen.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def _finden(self, name: str, art: str) -> dict | None:
        gesucht = normieren(name).strip()
        if not gesucht:
            return None
        kandidaten = self.alle(art)
        for eintrag in kandidaten:
            if normieren(eintrag["name"]).strip() == gesucht:
                return eintrag
        gefragt = vektor(name)
        bester: tuple[dict | None, float] = (None, 0.0)
        for eintrag in kandidaten:
            wert = aehnlichkeit(gefragt, vektor(eintrag["name"]))
            if wert > bester[1]:
                bester = (eintrag, wert)
        if bester[0] and bester[1] >= GLEICH_SCHWELLE:
            return bester[0]
        return None

    def merken(
        self,
        name: str,
        art: str = "sache",
        beschreibung: str = "",
        merkmale: dict | None = None,
        wichtigkeit: float = 0.5,
    ) -> dict:
        sauber = str(name or "").strip()[:120]
        if not sauber:
            return {"error": "kein Name"}
        art = art if art in ARTEN else "sache"
        vorhanden = self._finden(sauber, art)
        with session_scope() as session:
            if vorhanden:
                eintrag = session.get(Entitaet, vorhanden["id"])
                if eintrag is not None:
                    eintrag.erwaehnungen = int(eintrag.erwaehnungen or 1) + 1
                    eintrag.gesehen = _jetzt()
                    eintrag.wichtigkeit = max(
                        float(eintrag.wichtigkeit or 0.5), wichtigkeit
                    )
                    if beschreibung:
                        eintrag.beschreibung = beschreibung[:1000]
                    if merkmale:
                        try:
                            alt = json.loads(eintrag.merkmale or "{}")
                        except Exception as _fehler:
                            leise(_fehler, "services/weltmodell_service")
                            alt = {}
                        alt.update(merkmale)
                        eintrag.merkmale = json.dumps(alt, ensure_ascii=False)[:2000]
                    return self._zeile(eintrag)
            eintrag = Entitaet(
                art=art,
                name=sauber,
                beschreibung=beschreibung[:1000],
                merkmale=json.dumps(merkmale or {}, ensure_ascii=False)[:2000],
                wichtigkeit=wichtigkeit,
            )
            session.add(eintrag)
            session.flush()
            return self._zeile(eintrag)

    def verbinden(self, von: str, nach: str, art: str = "gehoert_zu", notiz: str = "") -> dict:
        a = self.merken(von)
        b = self.merken(nach)
        if a.get("error") or b.get("error"):
            return {"error": "Namen fehlen"}
        with session_scope() as session:
            vorhanden = (
                session.query(Beziehung)
                .filter(
                    Beziehung.von == a["id"],
                    Beziehung.nach == b["id"],
                    Beziehung.art == art,
                )
                .first()
            )
            if vorhanden is not None:
                if notiz:
                    vorhanden.notiz = notiz[:500]
                return {"id": vorhanden.id, "von": a["name"], "nach": b["name"], "art": art}
            eintrag = Beziehung(von=a["id"], nach=b["id"], art=art[:40], notiz=notiz[:500])
            session.add(eintrag)
            session.flush()
            return {"id": eintrag.id, "von": a["name"], "nach": b["name"], "art": art}

    def umfeld(self, name: str) -> dict:
        eintrag = self._finden(name, "")
        if eintrag is None:
            return {"gefunden": False, "name": name}
        namen = {e["id"]: e["name"] for e in self.alle()}
        with session_scope() as session:
            raus = session.query(Beziehung).filter(Beziehung.von == eintrag["id"]).all()
            rein = session.query(Beziehung).filter(Beziehung.nach == eintrag["id"]).all()
            beziehungen = [
                {"art": b.art, "zu": namen.get(b.nach, "?"), "notiz": b.notiz}
                for b in raus
            ] + [
                {"art": b.art, "von": namen.get(b.von, "?"), "notiz": b.notiz}
                for b in rein
            ]
        return {"gefunden": True, "entitaet": eintrag, "beziehungen": beziehungen}

    def erkennen(self, text: str) -> list[dict]:
        gefunden: list[dict] = []
        for muster, art in MUSTER:
            for treffer in muster.finditer(text or ""):
                name = treffer.groups()[-1].strip()
                if len(name) < 2:
                    continue
                gefunden.append(self.merken(name, art, treffer.group(0)[:200]))
        return gefunden

    def prompt_block(self, text: str = "", limit: int = 8) -> str:
        eintraege = self.alle(limit=200)
        if not eintraege:
            return ""
        if text:
            gefragt = vektor(text)
            bewertet = [
                (
                    aehnlichkeit(gefragt, vektor(f"{e['name']} {e['beschreibung']}"))
                    + 0.1 * e["wichtigkeit"],
                    e,
                )
                for e in eintraege
            ]
            bewertet.sort(key=lambda paar: paar[0], reverse=True)
            eintraege = [e for wert, e in bewertet if wert >= 0.14][:limit]
        else:
            eintraege = eintraege[:limit]
        if not eintraege:
            return ""
        zeilen = []
        for eintrag in eintraege:
            beschreibung = eintrag["beschreibung"] or ""
            zeilen.append(
                f"- {eintrag['name']} ({eintrag['art']})"
                + (f": {beschreibung[:120]}" if beschreibung else "")
            )
        return "Das kennst du aus Jons Weltmodell:\n" + "\n".join(zeilen)


_service: WeltmodellService | None = None


def get_weltmodell_service() -> WeltmodellService:
    global _service
    if _service is None:
        _service = WeltmodellService()
    return _service
