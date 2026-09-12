from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import ActionLog, Fertigkeit

LUECKE_SEKUNDEN = 180
MIN_LAENGE = 2
MAX_LAENGE = 4
MIN_WIEDERHOLUNGEN = 3
FENSTER_TAGE = 30
MAX_SCHRITTE = 12
PLATZHALTER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

UNINTERESSANT = {
    "get_time",
    "netz_status",
    "was_war",
    "verlauf_heute",
    "list_memories",
    "search_memory",
}


def _jetzt() -> datetime:
    return datetime.now()


def _name_aus(kette: tuple[str, ...]) -> str:
    return " dann ".join(kette)[:80]


class FertigkeitService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _zeile(self, eintrag: Fertigkeit) -> dict:
        try:
            schritte = json.loads(eintrag.schritte or "[]")
        except Exception as fehler:
            leise(fehler, "services/fertigkeit_service")
            schritte = []
        versuche = int(eintrag.versuche or 0)
        return {
            "id": eintrag.id,
            "name": eintrag.name,
            "beschreibung": eintrag.beschreibung or "",
            "ausloeser": eintrag.ausloeser or "",
            "schritte": schritte,
            "versuche": versuche,
            "erfolge": int(eintrag.erfolge or 0),
            "erfolgsquote": round(int(eintrag.erfolge or 0) / versuche, 2)
            if versuche
            else None,
            "aktiv": bool(eintrag.aktiv),
            "quelle": eintrag.quelle,
            "benutzt": eintrag.benutzt.isoformat(timespec="seconds")
            if eintrag.benutzt
            else "",
        }

    def anlegen(
        self,
        name: str,
        schritte: list[dict],
        beschreibung: str = "",
        ausloeser: str = "",
        quelle: str = "nutzer",
    ) -> dict:
        sauber = " ".join(str(name or "").split())[:80]
        if not sauber:
            return {"error": "Die Fertigkeit braucht einen Namen."}
        gereinigt = self._schritte_pruefen(schritte)
        if isinstance(gereinigt, dict):
            return gereinigt
        with session_scope() as session:
            vorhanden = (
                session.query(Fertigkeit).filter(Fertigkeit.name == sauber).first()
            )
            eintrag = vorhanden or Fertigkeit(name=sauber)
            eintrag.beschreibung = " ".join(str(beschreibung or "").split())[:400]
            eintrag.ausloeser = " ".join(str(ausloeser or "").split())[:300]
            eintrag.schritte = json.dumps(gereinigt, ensure_ascii=False)
            eintrag.quelle = (quelle or "nutzer")[:24]
            eintrag.aktiv = 1
            if vorhanden is None:
                session.add(eintrag)
            session.flush()
            return self._zeile(eintrag)

    @staticmethod
    def _schritte_pruefen(schritte: list[dict]) -> list[dict] | dict:
        from app.services.tools import werkzeugnamen

        if not isinstance(schritte, list) or not schritte:
            return {"error": "Die Fertigkeit braucht mindestens einen Schritt."}
        if len(schritte) > MAX_SCHRITTE:
            return {"error": f"Hoechstens {MAX_SCHRITTE} Schritte."}
        bekannt = werkzeugnamen()
        gereinigt: list[dict] = []
        for schritt in schritte:
            if not isinstance(schritt, dict):
                return {"error": "Jeder Schritt ist ein Objekt mit werkzeug und args."}
            werkzeug = str(schritt.get("werkzeug", "")).strip()
            if not werkzeug:
                return {"error": "Ein Schritt ohne Werkzeug geht nicht."}
            args = schritt.get("args") or {}
            if not isinstance(args, dict):
                return {"error": f"args von {werkzeug} muss ein Objekt sein."}
            gereinigt.append(
                {
                    "werkzeug": werkzeug[:64],
                    "args": args,
                    "notiz": str(schritt.get("notiz", ""))[:200],
                    "bekannt": werkzeug in bekannt,
                }
            )
        return gereinigt

    def liste(self, nur_aktiv: bool = True, limit: int = 60) -> list[dict]:
        with session_scope() as session:
            frage = session.query(Fertigkeit)
            if nur_aktiv:
                frage = frage.filter(Fertigkeit.aktiv == 1)
            zeilen = (
                frage.order_by(
                    Fertigkeit.erfolge.desc(), Fertigkeit.erstellt.desc()
                )
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def holen(self, name: str) -> dict | None:
        with session_scope() as session:
            eintrag = (
                session.query(Fertigkeit)
                .filter(Fertigkeit.name == str(name or "").strip()[:80])
                .first()
            )
            if eintrag is None:
                eintrag = session.get(Fertigkeit, str(name or ""))
            return self._zeile(eintrag) if eintrag is not None else None

    def loeschen(self, name: str) -> bool:
        with session_scope() as session:
            eintrag = (
                session.query(Fertigkeit)
                .filter(Fertigkeit.name == str(name or "").strip()[:80])
                .first()
            )
            if eintrag is None:
                return False
            session.delete(eintrag)
            return True

    def bewerten(self, name: str, gelungen: bool) -> dict:
        with session_scope() as session:
            eintrag = (
                session.query(Fertigkeit)
                .filter(Fertigkeit.name == str(name or "").strip()[:80])
                .first()
            )
            if eintrag is None:
                return {"error": "unbekannt"}
            eintrag.versuche = int(eintrag.versuche or 0) + 1
            if gelungen:
                eintrag.erfolge = int(eintrag.erfolge or 0) + 1
            eintrag.benutzt = _jetzt()
            return self._zeile(eintrag)

    def _ketten(self, tage: int) -> list[list[tuple[str, str, bool]]]:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        with session_scope() as session:
            zeilen = (
                session.query(
                    ActionLog.tool, ActionLog.args, ActionLog.ok, ActionLog.created_at
                )
                .filter(ActionLog.created_at >= grenze)
                .order_by(ActionLog.created_at.asc())
                .all()
            )
        ketten: list[list[tuple[str, str, bool]]] = []
        aktuell: list[tuple[str, str, bool]] = []
        letzte: datetime | None = None
        for werkzeug, args, ok, zeit in zeilen:
            if letzte is not None and (zeit - letzte).total_seconds() > LUECKE_SEKUNDEN:
                if len(aktuell) >= MIN_LAENGE:
                    ketten.append(aktuell)
                aktuell = []
            aktuell.append((str(werkzeug), str(args or "{}"), bool(ok)))
            letzte = zeit
        if len(aktuell) >= MIN_LAENGE:
            ketten.append(aktuell)
        return ketten

    def entdecken(
        self, tage: int = FENSTER_TAGE, mindest: int = MIN_WIEDERHOLUNGEN
    ) -> list[dict]:
        try:
            ketten = self._ketten(tage)
        except Exception as fehler:
            leise(fehler, "services/fertigkeit_service")
            return []
        zaehler: dict[tuple[str, ...], int] = {}
        muster: dict[tuple[str, ...], list[dict]] = {}
        for kette in ketten:
            gefiltert = [
                eintrag
                for eintrag in kette
                if eintrag[2] and eintrag[0] not in UNINTERESSANT
            ]
            namen_kette = [e[0] for e in gefiltert]
            for laenge in range(MIN_LAENGE, MAX_LAENGE + 1):
                for start in range(0, len(namen_kette) - laenge + 1):
                    teil = tuple(namen_kette[start : start + laenge])
                    if len(set(teil)) < 2:
                        continue
                    zaehler[teil] = zaehler.get(teil, 0) + 1
                    if teil not in muster:
                        muster[teil] = [
                            {
                                "werkzeug": e[0],
                                "args": self._args_lesen(e[1]),
                                "notiz": "",
                            }
                            for e in gefiltert[start : start + laenge]
                        ]
        bekannt = {f["name"] for f in self.liste(nur_aktiv=False, limit=200)}
        vorschlaege = []
        for teil, anzahl in sorted(zaehler.items(), key=lambda e: -e[1]):
            if anzahl < mindest:
                continue
            name = _name_aus(teil)
            if name in bekannt:
                continue
            if any(name.startswith(v["name"][:20]) for v in vorschlaege):
                continue
            vorschlaege.append(
                {
                    "name": name,
                    "anzahl": anzahl,
                    "schritte": muster[teil],
                    "beschreibung": (
                        f"Diese {len(teil)} Schritte liefen {anzahl} Mal "
                        "hintereinander erfolgreich."
                    ),
                }
            )
            if len(vorschlaege) >= 8:
                break
        return vorschlaege

    @staticmethod
    def _args_lesen(roh: str) -> dict:
        try:
            daten = json.loads(roh)
            return daten if isinstance(daten, dict) else {}
        except Exception:
            return {}

    def uebernehmen(self, vorschlag: dict) -> dict:
        return self.anlegen(
            str(vorschlag.get("name", "")),
            list(vorschlag.get("schritte") or []),
            str(vorschlag.get("beschreibung", "")),
            str(vorschlag.get("ausloeser", "")),
            quelle="entdeckt",
        )

    def platzhalter(self, name: str) -> list[str]:
        eintrag = self.holen(name)
        if not eintrag:
            return []
        gefunden: list[str] = []
        for schritt in eintrag["schritte"]:
            for wert in schritt.get("args", {}).values():
                for treffer in PLATZHALTER.findall(str(wert)):
                    if treffer not in gefunden:
                        gefunden.append(treffer)
        return gefunden

    @staticmethod
    def _einsetzen(args: dict, werte: dict) -> dict:
        gefuellt: dict = {}
        for schluessel, wert in args.items():
            if isinstance(wert, str):
                gefuellt[schluessel] = PLATZHALTER.sub(
                    lambda treffer: str(werte.get(treffer.group(1), treffer.group(0))),
                    wert,
                )
            else:
                gefuellt[schluessel] = wert
        return gefuellt

    def passende(self, text: str, limit: int = 3) -> list[dict]:
        eintraege = self.liste()
        if not eintraege or not text.strip():
            return []
        try:
            from app.services.semantik import aehnlichkeit, vektor

            ziel = vektor(text)
            bewertet = []
            for eintrag in eintraege:
                vergleich = " ".join(
                    [
                        eintrag["name"],
                        eintrag.get("ausloeser", ""),
                        eintrag.get("beschreibung", ""),
                    ]
                )
                wert = aehnlichkeit(ziel, vektor(vergleich))
                if wert > 0.55:
                    eintrag = dict(eintrag)
                    eintrag["passung"] = round(wert, 2)
                    bewertet.append(eintrag)
            return sorted(bewertet, key=lambda e: -e["passung"])[:limit]
        except Exception as fehler:
            leise(fehler, "services/fertigkeit_service")
            return []

    async def ausfuehren(
        self,
        name: str,
        werte: dict | None = None,
        bestaetigt: bool = False,
        quelle: str = "app",
    ) -> dict:
        eintrag = self.holen(name)
        if not eintrag:
            return {"error": f"Fertigkeit '{name}' kenne ich nicht."}
        if not eintrag.get("aktiv"):
            return {"error": f"Fertigkeit '{name}' ist abgeschaltet."}
        from app.services.risiko import bewerten
        from app.services.tools import ToolBox

        schritte = eintrag["schritte"]
        vorbereitet = []
        for schritt in schritte:
            args = self._einsetzen(schritt.get("args", {}), werte or {})
            offen = [
                wert
                for wert in args.values()
                if isinstance(wert, str) and PLATZHALTER.search(wert)
            ]
            if offen:
                return {
                    "error": "Es fehlen Werte fuer die Platzhalter.",
                    "platzhalter": self.platzhalter(name),
                }
            stufe = bewerten(schritt["werkzeug"], args)
            vorbereitet.append((schritt["werkzeug"], args, stufe.risiko))
        riskant = [w for w, _a, r in vorbereitet if r == "hoch"]
        if riskant and not bestaetigt:
            return {
                "error": "Diese Fertigkeit enthaelt riskante Schritte.",
                "freigabe_noetig": riskant,
                "schritte": [
                    {"werkzeug": w, "args": a, "risiko": r} for w, a, r in vorbereitet
                ],
            }
        box = ToolBox(source=quelle)
        protokoll = []
        gelungen = True
        for werkzeug, args, risiko in vorbereitet:
            try:
                ergebnis = await box.execute(werkzeug, args, source=quelle)
            except Exception as exc:
                ergebnis = json.dumps({"error": str(exc)}, ensure_ascii=False)
            ok = '"error"' not in ergebnis[:200]
            protokoll.append(
                {
                    "werkzeug": werkzeug,
                    "risiko": risiko,
                    "ok": ok,
                    "ergebnis": ergebnis[:400],
                }
            )
            if not ok:
                gelungen = False
                break
        self.bewerten(name, gelungen)
        try:
            from app.services.ereignis_service import get_ereignis_service

            get_ereignis_service().notieren(
                "fertigkeit",
                f"Fertigkeit '{name}' ausgefuehrt",
                f"{len(protokoll)} Schritte, {'geklappt' if gelungen else 'abgebrochen'}",
                quelle=quelle,
                bedeutung=0.4,
                gelungen=gelungen,
            )
        except Exception as fehler:
            leise(fehler, "services/fertigkeit_service")
        return {"ok": gelungen, "name": name, "schritte": protokoll}

    def prompt_block(self, text: str = "", limit: int = 3) -> str:
        treffer = self.passende(text, limit) if text.strip() else self.liste()[:limit]
        if not treffer:
            return ""
        zeilen = []
        for eintrag in treffer:
            quote = eintrag.get("erfolgsquote")
            wert = f", bisher {int(quote * 100)}% Erfolg" if quote is not None else ""
            zeilen.append(f"- {eintrag['name']}: {eintrag.get('beschreibung', '')[:120]}{wert}")
        return (
            "Gelernte Fertigkeiten - nutze fertigkeit_nutzen statt die Schritte "
            "einzeln zu wiederholen:\n" + "\n".join(zeilen)
        )

    def stand(self) -> dict:
        eintraege = self.liste(nur_aktiv=False, limit=200)
        return {
            "anzahl": len(eintraege),
            "aktiv": len([e for e in eintraege if e["aktiv"]]),
            "fertigkeiten": eintraege[:20],
        }


_service: FertigkeitService | None = None


def get_fertigkeit_service() -> FertigkeitService:
    global _service
    if _service is None:
        _service = FertigkeitService()
    return _service
