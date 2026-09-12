from __future__ import annotations

import threading
from collections import deque
from datetime import datetime

from app.core.fehler import leise

SCHNELL = "schnell"
NORMAL = "normal"
GRUENDLICH = "gruendlich"

BUDGETS = {SCHNELL: 1100, NORMAL: 2600, GRUENDLICH: 4200}
KRITIKER_SCHWELLE = {SCHNELL: 0.0, NORMAL: 0.5, GRUENDLICH: 0.8}

MEHRSCHRITT = (
    "und dann",
    "danach",
    "anschliessend",
    "anschließend",
    "zuerst",
    "schritt fuer schritt",
    "schritt für schritt",
    "nacheinander",
    "plane",
    "organisiere",
    "recherchiere",
    "vergleiche",
    "sammle",
    "erstelle mir",
    "richte ein",
    "kuemmere dich",
    "kümmere dich",
)

SCHWER = (
    "warum",
    "wieso",
    "erklaer",
    "erklär",
    "analysiere",
    "bewerte",
    "entscheide",
    "strategie",
    "konzept",
    "architektur",
    "abwaegen",
    "abwägen",
)

LEICHT = (
    "danke",
    "hallo",
    "hi ",
    "ok",
    "wie spaet",
    "wie spät",
    "uhrzeit",
    "wetter",
    "ja",
    "nein",
)


class MetakognitionService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._verlauf: deque[dict] = deque(maxlen=50)

    @staticmethod
    def _merkmale(text: str) -> dict:
        sauber = (text or "").strip().lower()
        laenge = min(1.0, len(sauber) / 420.0)
        mehrschritt = sum(1 for wort in MEHRSCHRITT if wort in sauber)
        schwer = sum(1 for wort in SCHWER if wort in sauber)
        leicht = any(sauber.startswith(wort) for wort in LEICHT) and len(sauber) < 40
        fragen = sauber.count("?")
        return {
            "laenge": round(laenge, 2),
            "mehrschritt": mehrschritt,
            "schwer": schwer,
            "leicht": leicht,
            "fragen": fragen,
        }

    def _werkzeuglage(self, text: str) -> dict:
        try:
            from app.services.erwartung_service import get_erwartung_service
            from app.services.risiko import bewerten
            from app.services.tool_index import passende_werkzeuge

            treffer = sorted(passende_werkzeuge(text, top_k=4))
            if not treffer:
                return {"werkzeuge": [], "zutrauen": None, "riskant": False}
            dienst = get_erwartung_service()
            werte = [dienst.schaetzen(name)["zutrauen"] for name in treffer]
            riskant = any(bewerten(name, {}).risiko == "hoch" for name in treffer)
            return {
                "werkzeuge": treffer,
                "zutrauen": round(sum(werte) / len(werte), 2),
                "riskant": riskant,
            }
        except Exception as fehler:
            leise(fehler, "services/metakognition_service")
            return {"werkzeuge": [], "zutrauen": None, "riskant": False}

    def einschaetzen(self, text: str, mit_werkzeugen: bool = True) -> dict:
        merkmale = self._merkmale(text)
        lage = self._werkzeuglage(text) if mit_werkzeugen else {
            "werkzeuge": [],
            "zutrauen": None,
            "riskant": False,
        }
        punkte = 0.0
        gruende: list[str] = []
        punkte += 0.3 * merkmale["laenge"]
        if merkmale["mehrschritt"]:
            punkte += min(0.45, 0.13 * merkmale["mehrschritt"])
            gruende.append("mehrere Schritte im Auftrag")
        if merkmale["schwer"]:
            punkte += min(0.25, 0.1 * merkmale["schwer"])
            gruende.append("verlangt Begruendung oder Abwaegung")
        if merkmale["fragen"] > 1:
            punkte += 0.1
            gruende.append("mehrere Fragen auf einmal")
        if lage["riskant"]:
            punkte += 0.15
            gruende.append("riskante Werkzeuge im Spiel")
        zutrauen = lage.get("zutrauen")
        if zutrauen is not None and zutrauen < 0.6:
            punkte += 0.2
            gruende.append(f"wackelige Werkzeuge (Zutrauen {zutrauen})")
        if merkmale["leicht"]:
            punkte -= 0.35
            gruende.append("kurze Alltagsfrage")
        punkte = round(max(0.0, min(1.0, punkte)), 2)
        stufe = (
            SCHNELL if punkte < 0.28 else NORMAL if punkte < 0.62 else GRUENDLICH
        )
        plan = stufe == GRUENDLICH and merkmale["mehrschritt"] >= 1
        urteil = {
            "stufe": stufe,
            "punkte": punkte,
            "gruende": gruende or ["nichts Auffaelliges"],
            "budget": BUDGETS[stufe],
            "kritiker": stufe != SCHNELL,
            "kritiker_schwelle": KRITIKER_SCHWELLE[stufe],
            "plan_empfohlen": plan,
            "werkzeuge": lage["werkzeuge"],
            "zutrauen": zutrauen,
            "zeit": datetime.now().isoformat(timespec="seconds"),
            "text": text[:120],
        }
        with self._lock:
            self._verlauf.append(urteil)
        return urteil

    def letzte(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return list(self._verlauf)[-limit:]

    def stand(self) -> dict:
        eintraege = self.letzte(50)
        if not eintraege:
            return {"anzahl": 0, "verteilung": {}, "letzte": []}
        verteilung: dict[str, int] = {}
        for eintrag in eintraege:
            verteilung[eintrag["stufe"]] = verteilung.get(eintrag["stufe"], 0) + 1
        return {
            "anzahl": len(eintraege),
            "verteilung": verteilung,
            "letzte": eintraege[-8:],
        }


_service: MetakognitionService | None = None


def get_metakognition_service() -> MetakognitionService:
    global _service
    if _service is None:
        _service = MetakognitionService()
    return _service
