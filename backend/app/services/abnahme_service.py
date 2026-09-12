from __future__ import annotations

import json
import re
from pathlib import Path

from app.core.fehler import leise

ABNAHME_SYSTEM = (
    "Du bist Jons Abnahme. Du bekommst einen Auftrag, die ausgefuehrten Schritte und "
    "die dabei entstandenen Dateien. Pruefe streng, ob der Auftrag WIRKLICH erfuellt "
    "ist - nicht, ob Jon sich Muehe gegeben hat.\n"
    "Antworte AUSSCHLIESSLICH mit JSON:\n"
    '{"fertig": true|false, "fehlt": "was konkret fehlt, sonst leer", '
    '"naechster_schritt": "was zu tun waere, sonst leer", "note": 1-5}\n'
    "fertig ist nur true, wenn ein Mensch das Ergebnis ohne Nacharbeit abnehmen wuerde. "
    "Fehlende Dateien, leere Dateien, Platzhaltertexte, abgebrochene Schritte oder nur "
    "teilweise erledigte Auftraege sind NICHT fertig. note 5 heisst tadellos, 1 heisst "
    "unbrauchbar."
)

MAX_DATEIEN = 12
MAX_TEXT = 3000


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
        leise(fehler, "services/abnahme_service")
        return None
    return daten if isinstance(daten, dict) else None


class AbnahmeService:
    @staticmethod
    def _dateien(seit: float) -> list[dict]:
        try:
            from app.services.dateiindex_service import get_dateiindex_service

            eintraege = get_dateiindex_service().liste(limit=MAX_DATEIEN)
        except Exception as fehler:
            leise(fehler, "services/abnahme_service")
            return []
        gefunden = []
        for eintrag in eintraege:
            pfad = Path(eintrag.get("pfad", ""))
            try:
                if not pfad.is_file() or pfad.stat().st_mtime < seit:
                    continue
            except OSError:
                continue
            gefunden.append(
                {
                    "name": eintrag.get("name", pfad.name),
                    "art": eintrag.get("art", ""),
                    "groesse": eintrag.get("groesse", 0),
                    "leer": int(eintrag.get("groesse", 0)) < 32,
                }
            )
        return gefunden

    @staticmethod
    def _schritte(plan: str) -> tuple[list[str], list[str], str]:
        try:
            from app.services.planer_service import get_planer_service

            daten = get_planer_service().holen(plan) if plan else None
        except Exception as fehler:
            leise(fehler, "services/abnahme_service")
            daten = None
        if not daten:
            return [], [], ""
        fertig = [
            f"{s['titel']}: {str(s.get('ergebnis', ''))[:200]}"
            for s in daten["schritte"]
            if s["zustand"] == "erledigt"
        ]
        offen = [
            s["titel"] for s in daten["schritte"] if s["zustand"] != "erledigt"
        ]
        return fertig, offen, daten.get("zustand", "")

    def hart_gepruefte_maengel(
        self, dateien: list[dict], offen: list[str], zustand: str
    ) -> str:
        if zustand == "gescheitert":
            return "Der Plan ist gescheitert."
        if offen:
            return "Nicht alle Schritte sind erledigt: " + ", ".join(offen[:3])
        leere = [d["name"] for d in dateien if d["leer"]]
        if leere:
            return "Leere Dateien entstanden: " + ", ".join(leere[:3])
        return ""

    async def pruefen(
        self, auftrag: str, plan: str = "", ergebnis: str = "", seit: float = 0.0
    ) -> dict:
        fertig, offen, zustand = self._schritte(plan)
        dateien = self._dateien(seit)
        mangel = self.hart_gepruefte_maengel(dateien, offen, zustand)
        if mangel:
            return {
                "fertig": False,
                "fehlt": mangel,
                "naechster_schritt": "",
                "note": 2,
                "quelle": "pruefung",
                "dateien": dateien,
            }
        from app.services.llm import complete

        eingabe = (
            f"Auftrag:\n{str(auftrag)[:1200]}\n\n"
            f"Erledigte Schritte:\n" + ("\n".join(fertig[:12]) or "keine") + "\n\n"
            f"Entstandene Dateien:\n"
            + (
                "\n".join(
                    f"- {d['name']} ({d['art']}, {d['groesse']} Bytes)" for d in dateien
                )
                or "keine"
            )
            + f"\n\nZusammenfassung:\n{str(ergebnis)[:MAX_TEXT]}"
        )
        try:
            roh = await complete(
                ABNAHME_SYSTEM, eingabe, max_tokens=400, temperature=0.1
            )
        except Exception as exc:
            leise(exc, "services/abnahme_service")
            return {
                "fertig": True,
                "fehlt": "",
                "note": 3,
                "quelle": "uebersprungen",
                "dateien": dateien,
            }
        daten = _json_aus(roh)
        if not daten:
            return {
                "fertig": True,
                "fehlt": "",
                "note": 3,
                "quelle": "unlesbar",
                "dateien": dateien,
            }
        try:
            note = int(daten.get("note", 3))
        except (TypeError, ValueError):
            note = 3
        return {
            "fertig": bool(daten.get("fertig", True)),
            "fehlt": str(daten.get("fehlt", ""))[:400],
            "naechster_schritt": str(daten.get("naechster_schritt", ""))[:300],
            "note": max(1, min(5, note)),
            "quelle": "modell",
            "dateien": dateien,
        }


_service: AbnahmeService | None = None


def get_abnahme_service() -> AbnahmeService:
    global _service
    if _service is None:
        _service = AbnahmeService()
    return _service
