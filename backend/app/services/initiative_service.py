from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_text

DATEI = DATA_DIR / "initiative.json"
MAX_VORSCHLAEGE = 40
MIN_ABSTAND_S = 900

SYSTEM = (
    "Du bist Jons vorausschauender Teil. Du bekommst: was gestern und heute "
    "passiert ist, die offenen Ziele, die Termine der naechsten Tage und offene "
    "Auftraege. Ueberlege, was dem Nutzer morgen hilft.\n"
    "Antworte NUR mit JSON:\n"
    '{"vorschlaege": [{"titel": "...", "warum": "...", "wann": "heute|morgen|diese '
    'woche", "selbst_machbar": true, "werkzeug": "web_search|browser_task|calendar_add'
    '|keins", "auftrag": "...", "risiko": "niedrig|mittel|hoch"}]}\n'
    "Hoechstens 4 Vorschlaege. selbst_machbar=true nur bei rein lesenden, "
    "harmlosen Schritten (nachschauen, vergleichen, vorbereiten). Alles, was Geld "
    "kostet, etwas verschickt, loescht oder bestellt, ist selbst_machbar=false. "
    "Wenn nichts ansteht, gib eine leere Liste zurueck."
)


def _jetzt() -> datetime:
    return datetime.now()


class InitiativeService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._daten = self._laden()
        self._laeuft = False

    def _laden(self) -> dict:
        if DATEI.exists():
            try:
                roh = json.loads(DATEI.read_text(encoding="utf-8"))
                if isinstance(roh, dict):
                    return roh
            except Exception as _fehler:
                leise(_fehler, "services/initiative_service")
        return {"vorschlaege": [], "letzter_lauf": "", "laeufe": 0}

    def _sichern(self) -> None:
        try:
            self._daten["vorschlaege"] = self._daten.get("vorschlaege", [])[
                -MAX_VORSCHLAEGE:
            ]
            atomic_write_text(
                DATEI,
                json.dumps(self._daten, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as _fehler:
            leise(_fehler, "services/initiative_service")

    def _an(self) -> bool:
        try:
            from app.services.settings_service import get_settings_service

            return bool(get_settings_service().get().get("initiative_enabled", False))
        except Exception as _fehler:
            leise(_fehler, "services/initiative_service")
            return False

    def faellig(self) -> bool:
        if not self._an():
            return False
        with self._lock:
            letzter = self._daten.get("letzter_lauf", "")
        if not letzter:
            return True
        try:
            vergangen = (_jetzt() - datetime.fromisoformat(letzter)).total_seconds()
        except Exception as _fehler:
            leise(_fehler, "services/initiative_service")
            return True
        return vergangen >= MIN_ABSTAND_S

    def offene(self) -> list[dict]:
        with self._lock:
            return [
                v
                for v in self._daten.get("vorschlaege", [])
                if v.get("zustand") == "offen"
            ]

    def alle(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return list(reversed(self._daten.get("vorschlaege", [])[-limit:]))

    def entscheiden(self, kennung: str, angenommen: bool) -> dict:
        with self._lock:
            for eintrag in self._daten.get("vorschlaege", []):
                if eintrag.get("id") == kennung:
                    eintrag["zustand"] = "angenommen" if angenommen else "verworfen"
                    eintrag["entschieden"] = _jetzt().isoformat(timespec="seconds")
                    self._sichern()
                    return dict(eintrag)
        return {"error": "Unbekannter Vorschlag."}

    def _kontext(self) -> str:
        from app.services.auftrag_service import get_auftrag_service
        from app.services.ereignis_service import get_ereignis_service
        from app.services.ziel_service import get_ziel_service

        teile: list[str] = []
        ereignisse = get_ereignis_service()
        for raum in ("gestern", "heute"):
            bild = ereignisse.tagesbild(raum)
            zeilen = [
                f"  {h['zeit']} {h['art']}: {h['titel']} {h['detail'][:100]}"
                for h in bild["hoehepunkte"][:8]
            ]
            teile.append(
                f"{raum.capitalize()} ({bild['anzahl']} Ereignisse):\n"
                + ("\n".join(zeilen) if zeilen else "  nichts")
            )
        ziele = get_ziel_service().bereit()[:8]
        teile.append(
            "Offene Ziele:\n"
            + (
                "\n".join(
                    f"  - {z['titel']} (Frist {z['frist'][:10] or 'keine'}, "
                    f"naechster Schritt: {z['naechster_schritt'] or 'unklar'})"
                    for z in ziele
                )
                or "  keine"
            )
        )
        try:
            from app.services.calendar_service import get_calendar_service

            termine = get_calendar_service().list(days=4)
            zeilen = [
                f"  - {t.get('date', '')} {t.get('time', '')} {t.get('title', '')}"
                for t in (termine if isinstance(termine, list) else [])[:10]
            ]
            teile.append("Termine der naechsten Tage:\n" + ("\n".join(zeilen) or "  keine"))
        except Exception as _fehler:
            leise(_fehler, "services/initiative_service")
        offen = get_auftrag_service().offene()[:5]
        teile.append(
            "Offene Auftraege:\n"
            + (
                "\n".join(f"  - {a['titel']} ({a['zustand']})" for a in offen)
                or "  keine"
            )
        )
        return "\n\n".join(teile)

    async def lauf(self, erzwingen: bool = False) -> dict:
        if not erzwingen and not self.faellig():
            return {"ok": False, "grund": "noch nicht faellig"}
        with self._lock:
            if self._laeuft:
                return {"ok": False, "grund": "laeuft bereits"}
            self._laeuft = True
        try:
            return await self._lauf_intern()
        finally:
            with self._lock:
                self._laeuft = False
                self._daten["letzter_lauf"] = _jetzt().isoformat(timespec="seconds")
                self._daten["laeufe"] = int(self._daten.get("laeufe", 0)) + 1
                self._sichern()

    async def _lauf_intern(self) -> dict:
        from app.services.ereignis_service import get_ereignis_service
        from app.services.llm import complete

        kontext = self._kontext()
        try:
            antwort = await complete(SYSTEM, kontext, max_tokens=900, temperature=0.4)
        except Exception as exc:
            return {"ok": False, "fehler": str(exc)}
        roh = antwort.strip()
        if roh.startswith("```"):
            roh = re.sub(r"^```[a-zA-Z]*\s*", "", roh)
            roh = re.sub(r"```\s*$", "", roh).strip()
        start, ende = roh.find("{"), roh.rfind("}")
        if start < 0 or ende <= start:
            return {"ok": True, "vorschlaege": []}
        try:
            daten = json.loads(roh[start : ende + 1])
        except Exception as _fehler:
            leise(_fehler, "services/initiative_service")
            return {"ok": True, "vorschlaege": []}

        neue: list[dict] = []
        bekannte = {v.get("titel", "") for v in self._daten.get("vorschlaege", [])}
        for eintrag in (daten.get("vorschlaege") or [])[:4]:
            if not isinstance(eintrag, dict):
                continue
            titel = str(eintrag.get("titel", "")).strip()[:200]
            if not titel or titel in bekannte:
                continue
            werkzeug = str(eintrag.get("werkzeug", "keins")).strip()
            selbst = bool(eintrag.get("selbst_machbar"))
            if werkzeug not in ("web_search", "browser_task", "calendar_add", "keins"):
                werkzeug = "keins"
            if werkzeug in ("calendar_add",):
                selbst = False
            vorschlag = {
                "id": f"iv{int(_jetzt().timestamp())}{len(neue)}",
                "titel": titel,
                "warum": str(eintrag.get("warum", ""))[:400],
                "wann": str(eintrag.get("wann", "morgen"))[:20],
                "selbst_machbar": selbst,
                "werkzeug": werkzeug,
                "auftrag": str(eintrag.get("auftrag", ""))[:400],
                "risiko": str(eintrag.get("risiko", "niedrig"))[:10],
                "zustand": "offen",
                "erstellt": _jetzt().isoformat(timespec="seconds"),
            }
            neue.append(vorschlag)

        with self._lock:
            self._daten.setdefault("vorschlaege", []).extend(neue)
            self._sichern()

        for vorschlag in neue:
            get_ereignis_service().notieren(
                "ziel",
                f"Vorschlag: {vorschlag['titel']}",
                vorschlag["warum"],
                quelle="initiative",
                bedeutung=0.55,
            )
        return {"ok": True, "vorschlaege": neue, "anzahl": len(neue)}

    async def ausfuehren(self, kennung: str) -> dict:
        from app.services.risiko import bewerten
        from app.services.tools import ToolBox

        vorschlag = None
        with self._lock:
            for eintrag in self._daten.get("vorschlaege", []):
                if eintrag.get("id") == kennung:
                    vorschlag = eintrag
                    break
        if vorschlag is None:
            return {"ok": False, "fehler": "Unbekannter Vorschlag."}
        werkzeug = vorschlag.get("werkzeug", "keins")
        if werkzeug == "keins" or not vorschlag.get("selbst_machbar"):
            return {
                "ok": False,
                "fehler": "Dieser Vorschlag braucht dich - Jon macht ihn nicht allein.",
            }
        args: dict = {}
        if werkzeug == "web_search":
            args = {"query": vorschlag.get("auftrag") or vorschlag["titel"]}
        elif werkzeug == "browser_task":
            args = {"auftrag": vorschlag.get("auftrag") or vorschlag["titel"], "dry_run": True}
        stufe = bewerten(werkzeug, args)
        if stufe.risiko != "niedrig":
            return {
                "ok": False,
                "fehler": f"Zu riskant fuer einen Alleingang ({stufe.grund}).",
            }
        ergebnis = await ToolBox(source="initiative").execute(werkzeug, args)
        with self._lock:
            vorschlag["zustand"] = "erledigt"
            vorschlag["ergebnis"] = str(ergebnis)[:1500]
            self._sichern()
        return {"ok": True, "werkzeug": werkzeug, "ergebnis": str(ergebnis)[:2000]}


_service: InitiativeService | None = None


def get_initiative_service() -> InitiativeService:
    global _service
    if _service is None:
        _service = InitiativeService()
    return _service
