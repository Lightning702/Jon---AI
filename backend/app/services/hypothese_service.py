from __future__ import annotations

import json
import threading
from datetime import datetime

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_json, read_json

DATEI = DATA_DIR / "hypothesen.json"

OFFEN = "offen"
BESTAETIGT = "bestaetigt"
WIDERLEGT = "widerlegt"
UNKLAR = "unklar"

MAX = 80
MIN_BELEGE = 2

VORSCHLAG_SYSTEM = (
    "Du bist Jons Hypothesenbildner. Du bekommst eine Beobachtung aus Jons Protokoll - "
    "meist ein Werkzeug, das oefter scheitert als erwartet. Stelle EINE pruefbare "
    "Vermutung auf, woran es liegt, und nenne einen konkreten Test, den Jon selbst "
    "ausfuehren kann.\n"
    "Antworte AUSSCHLIESSLICH mit JSON:\n"
    '{"vermutung": "...", "test": "...", "werkzeug": "name", "args": {}, '
    '"erwartet_wenn_wahr": "was dann passiert", '
    '"erwartet_wenn_falsch": "was sonst passiert"}\n'
    "Der Test muss harmlos sein: nur lesen, pruefen oder etwas in einem Testordner "
    "anlegen. Niemals loeschen, senden, kaufen oder Systemdateien anfassen. Kennst du "
    "kein passendes Werkzeug, setze werkzeug auf 'keins'."
)


def _jetzt() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_aus(text: str) -> dict | None:
    import re

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
        leise(fehler, "services/hypothese_service")
        return None
    return daten if isinstance(daten, dict) else None


class HypotheseService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._daten = self._laden()

    def _laden(self) -> dict:
        daten = read_json(DATEI, {"hypothesen": []})
        if not isinstance(daten, dict):
            daten = {"hypothesen": []}
        daten.setdefault("hypothesen", [])
        return daten

    def _sichern(self) -> None:
        try:
            atomic_write_json(DATEI, self._daten)
        except Exception as fehler:
            leise(fehler, "services/hypothese_service")

    def alle(self, limit: int = 40) -> list[dict]:
        with self._lock:
            return list(self._daten["hypothesen"])[-limit:][::-1]

    def offene(self, limit: int = 10) -> list[dict]:
        return [h for h in self.alle(MAX) if h["zustand"] == OFFEN][:limit]

    def anlegen(
        self,
        vermutung: str,
        test: str = "",
        werkzeug: str = "keins",
        args: dict | None = None,
        bereich: str = "",
        erwartet_wahr: str = "",
        erwartet_falsch: str = "",
    ) -> dict:
        sauber = " ".join(str(vermutung or "").split())[:300]
        if len(sauber) < 8:
            return {"error": "Die Vermutung ist zu kurz."}
        with self._lock:
            for vorhanden in self._daten["hypothesen"]:
                if vorhanden["vermutung"].lower() == sauber.lower():
                    return vorhanden
            eintrag = {
                "id": f"h{len(self._daten['hypothesen']) + 1}-{int(datetime.now().timestamp())}",
                "vermutung": sauber,
                "test": " ".join(str(test or "").split())[:300],
                "werkzeug": str(werkzeug or "keins")[:64],
                "args": args if isinstance(args, dict) else {},
                "bereich": str(bereich or "")[:80],
                "erwartet_wahr": str(erwartet_wahr or "")[:200],
                "erwartet_falsch": str(erwartet_falsch or "")[:200],
                "zustand": OFFEN,
                "belege_dafuer": 0,
                "belege_dagegen": 0,
                "versuche": [],
                "erstellt": _jetzt(),
            }
            self._daten["hypothesen"].append(eintrag)
            self._daten["hypothesen"] = self._daten["hypothesen"][-MAX:]
            self._sichern()
            return eintrag

    def _finden(self, kennung: str) -> dict | None:
        for eintrag in self._daten["hypothesen"]:
            if eintrag["id"] == kennung:
                return eintrag
        return None

    def verbuchen(self, kennung: str, dafuer: bool, notiz: str = "") -> dict:
        with self._lock:
            eintrag = self._finden(kennung)
            if eintrag is None:
                return {"error": "Unbekannte Hypothese."}
            if dafuer:
                eintrag["belege_dafuer"] += 1
            else:
                eintrag["belege_dagegen"] += 1
            eintrag["versuche"].append(
                {"zeit": _jetzt(), "dafuer": bool(dafuer), "notiz": str(notiz)[:300]}
            )
            eintrag["versuche"] = eintrag["versuche"][-8:]
            dafuer_n = eintrag["belege_dafuer"]
            dagegen_n = eintrag["belege_dagegen"]
            if dafuer_n >= MIN_BELEGE and dafuer_n > dagegen_n:
                eintrag["zustand"] = BESTAETIGT
            elif dagegen_n >= MIN_BELEGE and dagegen_n > dafuer_n:
                eintrag["zustand"] = WIDERLEGT
            elif dafuer_n and dagegen_n:
                eintrag["zustand"] = UNKLAR
            self._sichern()
            ergebnis = dict(eintrag)
        if ergebnis["zustand"] == BESTAETIGT:
            self._merken(ergebnis)
        return ergebnis

    def _merken(self, eintrag: dict) -> None:
        try:
            from app.services.erfahrung_service import KLAPPT, get_erfahrung_service

            bereich = eintrag.get("bereich") or f"werkzeug:{eintrag.get('werkzeug', '')}"
            get_erfahrung_service().notieren(
                bereich, f"Bestaetigt: {eintrag['vermutung']}", KLAPPT, 0.9
            )
        except Exception as fehler:
            leise(fehler, "services/hypothese_service")

    async def vermuten(self, beobachtung: str, bereich: str = "") -> dict:
        from app.services.llm import complete

        try:
            roh = await complete(
                VORSCHLAG_SYSTEM, str(beobachtung)[:900], max_tokens=500, temperature=0.4
            )
        except Exception as exc:
            return {"error": f"Vermutung ging schief: {exc}"}
        daten = _json_aus(roh)
        if not daten or not str(daten.get("vermutung", "")).strip():
            return {"error": "Keine brauchbare Vermutung."}
        return self.anlegen(
            str(daten.get("vermutung", "")),
            str(daten.get("test", "")),
            str(daten.get("werkzeug", "keins")),
            daten.get("args") if isinstance(daten.get("args"), dict) else {},
            bereich,
            str(daten.get("erwartet_wenn_wahr", "")),
            str(daten.get("erwartet_wenn_falsch", "")),
        )

    async def pruefen(self, kennung: str, quelle: str = "app") -> dict:
        with self._lock:
            eintrag = self._finden(kennung)
            if eintrag is None:
                return {"error": "Unbekannte Hypothese."}
            werkzeug = eintrag.get("werkzeug", "keins")
            args = dict(eintrag.get("args") or {})
            vermutung = eintrag["vermutung"]
        if werkzeug in ("", "keins"):
            return {"error": "Diese Vermutung hat keinen ausfuehrbaren Test."}
        from app.services.risiko import bewerten
        from app.services.tools import ToolBox

        stufe = bewerten(werkzeug, args)
        if stufe.risiko != "niedrig":
            return {
                "error": (
                    f"Der Test waere {stufe.risiko} riskant - so pruefe ich nichts "
                    "von allein."
                ),
                "werkzeug": werkzeug,
            }
        try:
            ergebnis = await ToolBox(source=quelle).execute(werkzeug, args)
        except Exception as exc:
            return {"error": f"Der Test lief nicht: {exc}"}
        gelungen = '"error"' not in ergebnis[:200]
        return {
            **self.verbuchen(kennung, gelungen, ergebnis[:300]),
            "test_ergebnis": ergebnis[:600],
            "vermutung": vermutung,
        }

    async def lauf(self, anzahl: int = 2) -> dict:
        from app.services.erwartung_service import get_erwartung_service

        neu = 0
        for eintrag in get_erwartung_service().ueberraschungen(anzahl, tage=14):
            if eintrag.get("gelungen"):
                continue
            beobachtung = (
                f"{eintrag['werkzeug']} scheiterte, obwohl "
                f"{int(eintrag['zutrauen'] * 100)}% Erfolg erwartet waren. "
                f"Meldung: {eintrag.get('notiz', '')[:200]}"
            )
            ergebnis = await self.vermuten(beobachtung, eintrag.get("bereich", ""))
            if ergebnis.get("id"):
                neu += 1
        geprueft = 0
        for eintrag in self.offene(anzahl):
            if eintrag.get("werkzeug") in ("", "keins"):
                continue
            if not (await self.pruefen(eintrag["id"])).get("error"):
                geprueft += 1
        return {"neue_vermutungen": neu, "geprueft": geprueft}

    def stand(self) -> dict:
        alle = self.alle(MAX)
        return {
            "gesamt": len(alle),
            "offen": len([h for h in alle if h["zustand"] == OFFEN]),
            "bestaetigt": [h for h in alle if h["zustand"] == BESTAETIGT][:8],
            "widerlegt": len([h for h in alle if h["zustand"] == WIDERLEGT]),
            "neueste": alle[:8],
        }

    def prompt_block(self, limit: int = 3) -> str:
        bestaetigt = [h for h in self.alle(MAX) if h["zustand"] == BESTAETIGT][:limit]
        if not bestaetigt:
            return ""
        zeilen = [f"- {h['vermutung']}" for h in bestaetigt]
        return "Das hast du selbst nachgeprueft und es stimmt:\n" + "\n".join(zeilen)


_service: HypotheseService | None = None


def get_hypothese_service() -> HypotheseService:
    global _service
    if _service is None:
        _service = HypotheseService()
    return _service
