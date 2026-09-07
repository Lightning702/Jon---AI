from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta

from app.core.fehler import leise

KRITIK_SYSTEM = (
    "Du bist Jons innerer Kritiker. Du bekommst den Auftrag des Nutzers und Jons "
    "geplante Antwort. Pruefe nuechtern: Beantwortet sie wirklich die Frage? Steht "
    "etwas darin, das nicht belegt ist? Fehlt ein Schritt? Ist etwas riskant?\n"
    "Antworte NUR mit JSON:\n"
    '{"passt": true, "sicherheit": 0.0, "probleme": ["..."], "besser": "..."}\n'
    "sicherheit ist deine Einschaetzung von 0 bis 1, wie verlaesslich die Antwort "
    "ist. probleme hoechstens 3 kurze Punkte. besser ist leer, wenn nichts zu "
    "aendern ist."
)

UNSICHER = (
    "vermutlich",
    "wahrscheinlich",
    "koennte",
    "könnte",
    "vielleicht",
    "ich glaube",
    "ich denke",
    "moeglicherweise",
    "möglicherweise",
    "schaetze",
    "schätze",
)


class SelbstService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def faehigkeiten(self) -> dict:
        from app.services.skill_service import SkillService
        from app.services.tools import ToolBox

        box = ToolBox()
        werkzeuge = [
            t.get("function", {}).get("name", "") for t in box._all_tools()
        ]
        try:
            skills = [s.get("name", "") for s in SkillService().list()]
        except Exception as _fehler:
            leise(_fehler, "services/selbst_service")
            skills = []
        return {
            "werkzeuge": sorted(w for w in werkzeuge if w),
            "anzahl_werkzeuge": len(werkzeuge),
            "skills": skills,
        }

    def bilanz(self, tage: int = 14) -> dict:
        from app.services.ereignis_service import get_ereignis_service

        dienst = get_ereignis_service()
        bis = datetime.now()
        von = bis - timedelta(days=max(1, tage))
        eintraege = dienst.spanne(von, bis, limit=3000)
        je_werkzeug: dict[str, dict] = {}
        for eintrag in eintraege:
            if eintrag["art"] not in ("werkzeug", "fehler"):
                continue
            name = eintrag["titel"]
            stand = je_werkzeug.setdefault(name, {"gut": 0, "schlecht": 0})
            if eintrag["gelungen"]:
                stand["gut"] += 1
            else:
                stand["schlecht"] += 1
        bewertet = []
        for name, stand in je_werkzeug.items():
            gesamt = stand["gut"] + stand["schlecht"]
            if gesamt < 2:
                continue
            bewertet.append(
                {
                    "werkzeug": name,
                    "laeufe": gesamt,
                    "erfolgsquote": round(stand["gut"] / gesamt, 2),
                }
            )
        bewertet.sort(key=lambda e: e["erfolgsquote"])
        return {
            "zeitraum_tage": tage,
            "aktionen": sum(e["laeufe"] for e in bewertet),
            "schwaechste": bewertet[:5],
            "staerkste": list(reversed(bewertet[-5:])),
        }

    def grenzen(self) -> list[str]:
        grenzen = [
            "Passwoerter, Zahlungsdaten und PINs gibt Jon nie ein.",
            "CAPTCHAs, 2FA und Sicherheitsabfragen umgeht Jon nicht.",
            "Kaeufe, Bestellungen, Nachrichten und Loeschungen brauchen eine "
            "ausdrueckliche Bestaetigung.",
            "In Windows-, Programm- und Systemordnern veraendert Jon nichts.",
            "Jon kann nur sehen, was auf diesem PC liegt oder was er im Netz "
            "aufrufen darf.",
        ]
        try:
            from app.services.netz_service import online

            if not online():
                grenzen.append("Gerade besteht keine Internetverbindung.")
        except Exception as _fehler:
            leise(_fehler, "services/selbst_service")
        try:
            from app.services.budget_service import get_budget_service

            stand = get_budget_service().stand()
            if stand["gesperrt"]:
                grenzen.append("Das Budget ist aufgebraucht.")
        except Exception as _fehler:
            leise(_fehler, "services/selbst_service")
        return grenzen

    def selbstbild(self) -> dict:
        faehig = self.faehigkeiten()
        return {
            "werkzeuge": faehig["anzahl_werkzeuge"],
            "skills": faehig["skills"],
            "bilanz": self.bilanz(),
            "grenzen": self.grenzen(),
        }

    def kann_ich(self, aufgabe: str) -> dict:
        from app.services.tool_index import passende_werkzeuge

        treffer = sorted(passende_werkzeuge(aufgabe, top_k=6))
        bilanz = {e["werkzeug"]: e for e in self.bilanz()["schwaechste"]}
        warnungen = [
            f"{name} klappt zuletzt nur in "
            f"{int(bilanz[name]['erfolgsquote'] * 100)}% der Faelle"
            for name in treffer
            if name in bilanz and bilanz[name]["erfolgsquote"] < 0.6
        ]
        return {
            "aufgabe": aufgabe,
            "passende_werkzeuge": treffer,
            "zutrauen": "hoch" if treffer and not warnungen else
            "mittel" if treffer else "niedrig",
            "warnungen": warnungen,
            "grenzen": self.grenzen(),
        }

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
            leise(_fehler, "services/selbst_service")
            return None
        return daten if isinstance(daten, dict) else None

    def sicherheit_schaetzen(self, antwort: str) -> float:
        text = (antwort or "").lower()
        treffer = sum(1 for wort in UNSICHER if wort in text)
        wert = 0.85 - 0.12 * treffer
        if "weiss ich nicht" in text or "weiß ich nicht" in text:
            wert = min(wert, 0.4)
        if len(text) < 40:
            wert -= 0.1
        return round(max(0.05, min(0.99, wert)), 2)

    async def kritik(self, auftrag: str, antwort: str) -> dict:
        from app.services.llm import complete

        grob = self.sicherheit_schaetzen(antwort)
        if not antwort.strip():
            return {"passt": False, "sicherheit": 0.0, "probleme": ["Leere Antwort."]}
        try:
            roh = await complete(
                KRITIK_SYSTEM,
                f"Auftrag:\n{auftrag[:2000]}\n\nGeplante Antwort:\n{antwort[:4000]}",
                max_tokens=500,
                temperature=0.2,
            )
        except Exception as exc:
            return {"passt": True, "sicherheit": grob, "fehler": str(exc)}
        daten = self._json(roh)
        if not daten:
            return {"passt": True, "sicherheit": grob}
        try:
            sicher = float(daten.get("sicherheit", grob))
        except Exception as _fehler:
            leise(_fehler, "services/selbst_service")
            sicher = grob
        return {
            "passt": bool(daten.get("passt", True)),
            "sicherheit": round(min(1.0, max(0.0, (sicher + grob) / 2)), 2),
            "probleme": [str(p)[:200] for p in (daten.get("probleme") or [])][:3],
            "besser": str(daten.get("besser", ""))[:2000],
        }


_service: SelbstService | None = None


def get_selbst_service() -> SelbstService:
    global _service
    if _service is None:
        _service = SelbstService()
    return _service
