from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from dataclasses import dataclass, field

from app.core.fehler import leise

MAX_AGENTEN = 4
MAX_SCHRITTE_JE_AGENT = 8
GESAMT_TIMEOUT_S = 420.0

AUFTEILUNG_SYSTEM = (
    "Du teilst eine groessere Aufgabe in unabhaengige Teilaufgaben auf, die "
    "gleichzeitig bearbeitet werden koennen. Antworte NUR mit JSON:\n"
    '{"teile": [{"titel": "...", "auftrag": "...", "werkzeug": "web_search|'
    'browser_task|keins"}]}\n'
    "Hoechstens 4 Teile. Jeder Teil muss ohne die Ergebnisse der anderen loesbar "
    "sein. Nur lesende, harmlose Teilaufgaben. Laesst sich die Aufgabe nicht sinnvoll "
    "aufteilen, gib genau einen Teil zurueck."
)

ZUSAMMEN_SYSTEM = (
    "Du bist der Koordinator. Du bekommst die urspruengliche Aufgabe und die "
    "Ergebnisse mehrerer Teilagenten. Schreibe daraus eine einzige, klare Antwort "
    "auf Deutsch in Fliesstext. Nenne konkrete Zahlen, Namen und Quellen aus den "
    "Ergebnissen. Widersprechen sich Ergebnisse, sag das offen. Keine Tabellen."
)


@dataclass
class Teilergebnis:
    titel: str
    auftrag: str
    werkzeug: str
    ergebnis: str = ""
    fehler: str = ""
    dauer: float = 0.0

    def als_dict(self) -> dict:
        return {
            "titel": self.titel,
            "auftrag": self.auftrag,
            "werkzeug": self.werkzeug,
            "ergebnis": self.ergebnis[:2000],
            "fehler": self.fehler,
            "dauer": round(self.dauer, 1),
        }


@dataclass
class Lauf:
    aufgabe: str
    teile: list[Teilergebnis] = field(default_factory=list)
    zusammenfassung: str = ""
    gestartet: float = field(default_factory=time.time)


class AgentenService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._laeufe: dict[str, Lauf] = {}

    @staticmethod
    def _json(text: str) -> dict | None:
        roh = (text or "").strip()
        if roh.startswith("```"):
            roh = re.sub(r"^```[a-zA-Z]*\s*", "", roh)
            roh = re.sub(r"```\s*$", "", roh).strip()
        start, ende = roh.find("{"), roh.rfind("}")
        if start < 0 or ende <= start:
            return None
        try:
            daten = json.loads(roh[start : ende + 1])
        except Exception as _fehler:
            leise(_fehler, "services/agenten_service")
            return None
        return daten if isinstance(daten, dict) else None

    async def _aufteilen(self, aufgabe: str) -> list[dict]:
        from app.services.llm import complete

        try:
            antwort = await complete(
                AUFTEILUNG_SYSTEM, aufgabe, max_tokens=700, temperature=0.3
            )
        except Exception as _fehler:
            leise(_fehler, "services/agenten_service")
            return [{"titel": aufgabe[:80], "auftrag": aufgabe, "werkzeug": "web_search"}]
        daten = self._json(antwort) or {}
        teile = [t for t in (daten.get("teile") or []) if isinstance(t, dict)]
        if not teile:
            return [{"titel": aufgabe[:80], "auftrag": aufgabe, "werkzeug": "web_search"}]
        return teile[:MAX_AGENTEN]

    async def _teil_ausfuehren(self, teil: dict) -> Teilergebnis:
        from app.services.risiko import bewerten
        from app.services.tools import ToolBox

        start = time.time()
        titel = str(teil.get("titel", ""))[:120]
        auftrag = str(teil.get("auftrag", "")) or titel
        werkzeug = str(teil.get("werkzeug", "web_search"))
        if werkzeug not in ("web_search", "browser_task"):
            werkzeug = "web_search"
        args = (
            {"query": auftrag}
            if werkzeug == "web_search"
            else {"auftrag": auftrag, "max_schritte": MAX_SCHRITTE_JE_AGENT}
        )
        stufe = bewerten(werkzeug, args)
        if stufe.risiko == "hoch":
            return Teilergebnis(
                titel, auftrag, werkzeug, fehler=f"Zu riskant: {stufe.grund}"
            )
        try:
            ergebnis = await ToolBox(source="agenten").execute(werkzeug, args)
            return Teilergebnis(
                titel, auftrag, werkzeug, ergebnis=str(ergebnis), dauer=time.time() - start
            )
        except Exception as exc:
            return Teilergebnis(
                titel, auftrag, werkzeug, fehler=str(exc), dauer=time.time() - start
            )

    async def bearbeiten(self, aufgabe: str, max_agenten: int = MAX_AGENTEN) -> dict:
        from app.services.ereignis_service import get_ereignis_service
        from app.services.llm import complete

        text = str(aufgabe or "").strip()
        if not text:
            return {"ok": False, "fehler": "Keine Aufgabe angegeben."}
        teile = (await self._aufteilen(text))[: max(1, min(max_agenten, MAX_AGENTEN))]
        lauf = Lauf(aufgabe=text)
        with self._lock:
            self._laeufe[str(int(lauf.gestartet))] = lauf

        try:
            ergebnisse = await asyncio.wait_for(
                asyncio.gather(*[self._teil_ausfuehren(t) for t in teile]),
                timeout=GESAMT_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            ergebnisse = [
                Teilergebnis(
                    str(t.get("titel", "")), str(t.get("auftrag", "")), "", fehler="Zeitlimit"
                )
                for t in teile
            ]
        lauf.teile = list(ergebnisse)

        zusammen = "\n\n".join(
            f"### {t.titel}\n{t.ergebnis[:2500] or t.fehler}" for t in lauf.teile
        )
        try:
            lauf.zusammenfassung = await complete(
                ZUSAMMEN_SYSTEM,
                f"Aufgabe: {text}\n\nTeilergebnisse:\n{zusammen}",
                max_tokens=1200,
                temperature=0.3,
            )
        except Exception as exc:
            lauf.zusammenfassung = f"Zusammenfassung nicht moeglich: {exc}"

        get_ereignis_service().notieren(
            "werkzeug",
            f"Agententeam: {text[:80]}",
            f"{len(lauf.teile)} Teilagenten",
            quelle="agenten",
            bedeutung=0.5,
        )
        return {
            "ok": True,
            "aufgabe": text,
            "teile": [t.als_dict() for t in lauf.teile],
            "antwort": lauf.zusammenfassung,
            "dauer": round(time.time() - lauf.gestartet, 1),
        }


_service: AgentenService | None = None


def get_agenten_service() -> AgentenService:
    global _service
    if _service is None:
        _service = AgentenService()
    return _service
