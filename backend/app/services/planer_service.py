from __future__ import annotations

import json
import re
from datetime import datetime
from typing import AsyncIterator

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import Plan

ENTWORFEN = "entworfen"
LAEUFT = "laeuft"
FERTIG = "fertig"
GESCHEITERT = "gescheitert"
ABGEBROCHEN = "abgebrochen"

OFFEN = "offen"
ERLEDIGT = "erledigt"
FEHLER = "fehler"
UEBERSPRUNGEN = "uebersprungen"

MAX_SCHRITTE = 14
MAX_UMPLANUNGEN = 2
MAX_DENKZEICHEN = 1200

PLAN_SYSTEM = (
    "Du bist Jons Planer. Du zerlegst einen Auftrag in wenige, konkrete Schritte, "
    "die Jon wirklich ausfuehren kann.\n"
    "Antworte AUSSCHLIESSLICH mit JSON in dieser Form:\n"
    '{"schritte":[{"id":"s1","titel":"kurz","werkzeug":"name_oder_denken",'
    '"args":{},"haengt_von":[]}],"ergebnis":"was am Ende dasteht"}\n'
    "Regeln:\n"
    "- Hoechstens 8 Schritte. Lieber wenige grosse als viele winzige.\n"
    "- werkzeug ist entweder ein Name aus der Werkzeugliste oder 'denken', wenn "
    "der Schritt nur Nachdenken/Zusammenfassen ist.\n"
    "- Bei 'denken' gehoert die Denkaufgabe in args.frage.\n"
    "- haengt_von nennt die ids der Schritte, deren Ergebnis gebraucht wird.\n"
    "- Erfinde keine Werkzeuge. Kein Text ausserhalb des JSON."
)

UMPLAN_SYSTEM = (
    "Du bist Jons Planer und besserst einen gescheiterten Plan nach. Du bekommst "
    "den Auftrag, den bisherigen Plan, was schon erledigt ist und den Fehler.\n"
    "Antworte AUSSCHLIESSLICH mit JSON: "
    '{"schritte":[...],"ergebnis":"..."} wie beim ersten Plan, aber nur mit den '
    "noch offenen Schritten - erledigte Schritte nicht wiederholen. Reagiere auf "
    "den Fehler mit einem anderen Weg, nicht mit demselben Schritt."
)

DENK_SYSTEM = (
    "Du bist Jon und arbeitest einen Planschritt ab, der reines Nachdenken ist. "
    "Antworte auf Deutsch, knapp und konkret, ohne Vorrede."
)


def _jetzt() -> datetime:
    return datetime.now()


def _json_aus(text: str) -> dict | None:
    roh = (text or "").strip()
    if roh.startswith("```"):
        roh = re.sub(r"^```[a-zA-Z]*\s*", "", roh)
        roh = re.sub(r"```\s*$", "", roh).strip()
    start, ende = roh.find("{"), roh.rfind("}")
    if start < 0 or ende <= start:
        return None
    try:
        daten = json.loads(roh[start : ende + 1])
    except Exception as fehler:
        leise(fehler, "services/planer_service")
        return None
    return daten if isinstance(daten, dict) else None


class PlanerService:
    def _zeile(self, eintrag: Plan) -> dict:
        try:
            schritte = json.loads(eintrag.schritte or "[]")
        except Exception as fehler:
            leise(fehler, "services/planer_service")
            schritte = []
        fertig = len([s for s in schritte if s.get("zustand") == ERLEDIGT])
        return {
            "id": eintrag.id,
            "auftrag": eintrag.auftrag,
            "ziel": eintrag.ziel or "",
            "zustand": eintrag.zustand,
            "schritte": schritte,
            "erledigt": fertig,
            "anzahl": len(schritte),
            "fortschritt": round(fertig / len(schritte), 2) if schritte else 0.0,
            "ergebnis": eintrag.ergebnis or "",
            "umplanungen": int(eintrag.umplanungen or 0),
            "erstellt": eintrag.erstellt.isoformat(timespec="seconds")
            if eintrag.erstellt
            else "",
        }

    @staticmethod
    def _saeubern(daten: dict, bekannt: set[str]) -> list[dict]:
        roh = daten.get("schritte") or daten.get("steps") or []
        schritte: list[dict] = []
        gesehen: set[str] = set()
        for stelle, eintrag in enumerate(roh[:MAX_SCHRITTE]):
            if not isinstance(eintrag, dict):
                continue
            kennung = str(eintrag.get("id") or f"s{stelle + 1}")[:16]
            if kennung in gesehen:
                kennung = f"{kennung}_{stelle}"
            gesehen.add(kennung)
            werkzeug = str(eintrag.get("werkzeug") or eintrag.get("tool") or "denken")
            args = eintrag.get("args")
            if not isinstance(args, dict):
                args = {}
            if werkzeug not in bekannt and werkzeug != "denken":
                args = {
                    "frage": str(eintrag.get("titel", ""))[:300]
                    or f"Erledige: {werkzeug}"
                }
                werkzeug = "denken"
            haengt = [
                str(w)[:16]
                for w in (eintrag.get("haengt_von") or eintrag.get("depends_on") or [])
                if str(w)[:16] in gesehen
            ]
            schritte.append(
                {
                    "id": kennung,
                    "titel": str(eintrag.get("titel") or eintrag.get("title") or "")[
                        :200
                    ]
                    or werkzeug,
                    "werkzeug": werkzeug[:64],
                    "args": args,
                    "haengt_von": haengt,
                    "zustand": OFFEN,
                    "ergebnis": "",
                }
            )
        return schritte

    async def entwerfen(
        self, auftrag: str, ziel: str = "", kontext: str = "", quelle: str = "app"
    ) -> dict:
        sauber = " ".join(str(auftrag or "").split())[:400]
        if len(sauber) < 4:
            return {"error": "Der Auftrag ist zu kurz."}
        from app.services.llm import complete
        from app.services.tool_index import passende_werkzeuge
        from app.services.tools import werkzeugnamen

        bekannt = werkzeugnamen()
        try:
            vorschlag = sorted(passende_werkzeuge(sauber, top_k=18))
        except Exception as fehler:
            leise(fehler, "services/planer_service")
            vorschlag = sorted(bekannt)[:18]
        eingabe = f"Auftrag: {sauber}"
        if kontext.strip():
            eingabe += f"\n\nKontext:\n{kontext.strip()[:1200]}"
        eingabe += "\n\nMoegliche Werkzeuge: " + ", ".join(vorschlag)
        try:
            roh = await complete(
                PLAN_SYSTEM, eingabe, max_tokens=1200, temperature=0.3
            )
        except Exception as exc:
            return {"error": f"Planen ging schief: {exc}"}
        daten = _json_aus(roh)
        if not daten:
            return {"error": "Der Plan kam nicht als JSON zurueck."}
        schritte = self._saeubern(daten, bekannt | {"denken"})
        if not schritte:
            return {"error": "Der Plan war leer."}
        with session_scope() as session:
            eintrag = Plan(
                auftrag=sauber[:200],
                ziel=str(ziel or "")[:32],
                zustand=ENTWORFEN,
                schritte=json.dumps(schritte, ensure_ascii=False),
                ergebnis=str(daten.get("ergebnis", ""))[:400],
                quelle=(quelle or "app")[:24],
            )
            session.add(eintrag)
            session.flush()
            return self._zeile(eintrag)

    def holen(self, kennung: str) -> dict | None:
        with session_scope() as session:
            eintrag = session.get(Plan, kennung)
            return self._zeile(eintrag) if eintrag is not None else None

    def liste(self, limit: int = 20) -> list[dict]:
        with session_scope() as session:
            zeilen = (
                session.query(Plan).order_by(Plan.erstellt.desc()).limit(limit).all()
            )
            return [self._zeile(z) for z in zeilen]

    def _sichern(
        self, kennung: str, schritte: list[dict], zustand: str = "", ergebnis: str = ""
    ) -> dict | None:
        with session_scope() as session:
            eintrag = session.get(Plan, kennung)
            if eintrag is None:
                return None
            eintrag.schritte = json.dumps(schritte, ensure_ascii=False)
            if zustand:
                eintrag.zustand = zustand
            if ergebnis:
                eintrag.ergebnis = ergebnis[:400]
            eintrag.aktualisiert = _jetzt()
            return self._zeile(eintrag)

    def abbrechen(self, kennung: str) -> dict | None:
        with session_scope() as session:
            eintrag = session.get(Plan, kennung)
            if eintrag is None:
                return None
            eintrag.zustand = ABGEBROCHEN
            eintrag.aktualisiert = _jetzt()
            return self._zeile(eintrag)

    @staticmethod
    def _naechster(schritte: list[dict]) -> dict | None:
        fertig = {s["id"] for s in schritte if s["zustand"] == ERLEDIGT}
        for schritt in schritte:
            if schritt["zustand"] != OFFEN:
                continue
            if all(abhaengig in fertig for abhaengig in schritt.get("haengt_von", [])):
                return schritt
        return None

    @staticmethod
    def _kontext(schritte: list[dict], schritt: dict) -> str:
        teile = []
        for anderer in schritte:
            if anderer["id"] in schritt.get("haengt_von", []) and anderer.get(
                "ergebnis"
            ):
                teile.append(f"{anderer['titel']}: {anderer['ergebnis'][:400]}")
        return "\n".join(teile)

    async def _denken(self, schritt: dict, kontext: str) -> tuple[bool, str]:
        from app.services.llm import complete

        frage = str(schritt.get("args", {}).get("frage") or schritt["titel"])
        eingabe = frage if not kontext else f"{frage}\n\nBisher:\n{kontext}"
        try:
            antwort = await complete(
                DENK_SYSTEM, eingabe, max_tokens=700, temperature=0.4
            )
        except Exception as exc:
            return False, str(exc)
        return bool(antwort.strip()), antwort.strip()[:MAX_DENKZEICHEN]

    async def _umplanen(
        self, kennung: str, schritte: list[dict], fehler: str
    ) -> list[dict] | None:
        with session_scope() as session:
            eintrag = session.get(Plan, kennung)
            if eintrag is None:
                return None
            if int(eintrag.umplanungen or 0) >= MAX_UMPLANUNGEN:
                return None
            eintrag.umplanungen = int(eintrag.umplanungen or 0) + 1
            auftrag = eintrag.auftrag
        from app.services.llm import complete
        from app.services.tools import werkzeugnamen

        bekannt = werkzeugnamen()
        erledigt = [
            f"{s['titel']}: {s.get('ergebnis', '')[:200]}"
            for s in schritte
            if s["zustand"] == ERLEDIGT
        ]
        offen = [s["titel"] for s in schritte if s["zustand"] == OFFEN]
        eingabe = (
            f"Auftrag: {auftrag}\n\nErledigt:\n"
            + ("\n".join(erledigt) or "nichts")
            + "\n\nNoch offen:\n"
            + ("\n".join(offen) or "nichts")
            + f"\n\nFehler:\n{fehler[:600]}"
            + "\n\nMoegliche Werkzeuge: "
            + ", ".join(sorted(bekannt)[:60])
        )
        try:
            roh = await complete(
                UMPLAN_SYSTEM, eingabe, max_tokens=1000, temperature=0.4
            )
        except Exception as exc:
            leise(exc, "services/planer_service")
            return None
        daten = _json_aus(roh)
        if not daten:
            return None
        neue = self._saeubern(daten, bekannt | {"denken"})
        if not neue:
            return None
        behalten = [s for s in schritte if s["zustand"] == ERLEDIGT]
        return behalten + neue

    async def ausfuehren(
        self, kennung: str, bestaetigt: bool = False, quelle: str = "app"
    ) -> AsyncIterator[dict]:
        plan = self.holen(kennung)
        if plan is None:
            yield {"art": "fehler", "text": "Diesen Plan kenne ich nicht."}
            return
        if plan["zustand"] in (FERTIG, ABGEBROCHEN):
            yield {"art": "fehler", "text": f"Der Plan ist schon {plan['zustand']}."}
            return
        from app.services.risiko import bewerten
        from app.services.tools import ToolBox

        schritte = plan["schritte"]
        riskant = [
            s["titel"]
            for s in schritte
            if s["werkzeug"] != "denken"
            and bewerten(s["werkzeug"], s.get("args", {})).risiko == "hoch"
        ]
        if riskant and not bestaetigt:
            yield {
                "art": "freigabe",
                "text": "Der Plan enthaelt riskante Schritte.",
                "schritte": riskant,
            }
            return
        self._sichern(kennung, schritte, LAEUFT)
        box = ToolBox(source=quelle)
        gescheitert = ""
        while True:
            aktueller = self._naechster(schritte)
            if aktueller is None:
                break
            zustand = self.holen(kennung)
            if zustand is not None and zustand["zustand"] == ABGEBROCHEN:
                yield {"art": "abgebrochen", "text": "Plan abgebrochen."}
                return
            yield {
                "art": "schritt",
                "id": aktueller["id"],
                "titel": aktueller["titel"],
                "werkzeug": aktueller["werkzeug"],
                "status": "laeuft",
            }
            kontext = self._kontext(schritte, aktueller)
            if aktueller["werkzeug"] == "denken":
                ok, ergebnis = await self._denken(aktueller, kontext)
            else:
                try:
                    ergebnis = await box.execute(
                        aktueller["werkzeug"], aktueller.get("args", {}), source=quelle
                    )
                except Exception as exc:
                    ergebnis = json.dumps({"error": str(exc)}, ensure_ascii=False)
                ok = '"error"' not in ergebnis[:200]
            aktueller["zustand"] = ERLEDIGT if ok else FEHLER
            aktueller["ergebnis"] = str(ergebnis)[:MAX_DENKZEICHEN]
            self._sichern(kennung, schritte)
            yield {
                "art": "schritt",
                "id": aktueller["id"],
                "titel": aktueller["titel"],
                "werkzeug": aktueller["werkzeug"],
                "status": "fertig" if ok else "fehler",
                "ergebnis": aktueller["ergebnis"][:600],
            }
            if ok:
                continue
            gescheitert = aktueller["ergebnis"]
            neue = await self._umplanen(kennung, schritte, gescheitert)
            if neue is None:
                self._sichern(kennung, schritte, GESCHEITERT)
                yield {"art": "ende", "ok": False, "text": gescheitert[:400]}
                self._merken(kennung, False)
                return
            schritte = neue
            self._sichern(kennung, schritte, LAEUFT)
            yield {
                "art": "umplanung",
                "text": "Neuer Weg nach dem Fehler.",
                "schritte": [s["titel"] for s in schritte if s["zustand"] == OFFEN],
            }
        offen = [s for s in schritte if s["zustand"] == OFFEN]
        ok = not offen and not any(s["zustand"] == FEHLER for s in schritte)
        for schritt in offen:
            schritt["zustand"] = UEBERSPRUNGEN
        zusammenfassung = "\n".join(
            f"{s['titel']}: {s.get('ergebnis', '')[:200]}"
            for s in schritte
            if s["zustand"] == ERLEDIGT
        )
        self._sichern(kennung, schritte, FERTIG if ok else GESCHEITERT)
        self._merken(kennung, ok)
        yield {"art": "ende", "ok": ok, "text": zusammenfassung[:1500]}

    def _merken(self, kennung: str, ok: bool) -> None:
        plan = self.holen(kennung)
        if plan is None:
            return
        try:
            from app.services.ereignis_service import get_ereignis_service

            get_ereignis_service().notieren(
                "plan",
                f"Plan '{plan['auftrag'][:120]}' {'fertig' if ok else 'gescheitert'}",
                f"{plan['erledigt']} von {plan['anzahl']} Schritten, "
                f"{plan['umplanungen']} Umplanungen",
                quelle="denken",
                bedeutung=0.55,
                gelungen=ok,
            )
        except Exception as fehler:
            leise(fehler, "services/planer_service")
        if not ok:
            return
        try:
            from app.services.fertigkeit_service import get_fertigkeit_service

            schritte = [
                {"werkzeug": s["werkzeug"], "args": s.get("args", {}), "notiz": s["titel"]}
                for s in plan["schritte"]
                if s["zustand"] == ERLEDIGT and s["werkzeug"] != "denken"
            ]
            if len(schritte) >= 2 and plan["umplanungen"] == 0:
                get_fertigkeit_service().anlegen(
                    plan["auftrag"][:80],
                    schritte,
                    beschreibung=f"Aus einem gelungenen Plan gelernt: {plan['auftrag'][:200]}",
                    ausloeser=plan["auftrag"][:200],
                    quelle="plan",
                )
        except Exception as fehler:
            leise(fehler, "services/planer_service")

    async def lauf(
        self, auftrag: str, ziel: str = "", kontext: str = "", bestaetigt: bool = False
    ) -> dict:
        plan = await self.entwerfen(auftrag, ziel, kontext)
        if plan.get("error"):
            return plan
        ereignisse = []
        async for eintrag in self.ausfuehren(plan["id"], bestaetigt=bestaetigt):
            ereignisse.append(eintrag)
        fertig = self.holen(plan["id"]) or plan
        fertig["ereignisse"] = ereignisse
        return fertig


_service: PlanerService | None = None


def get_planer_service() -> PlanerService:
    global _service
    if _service is None:
        _service = PlanerService()
    return _service
