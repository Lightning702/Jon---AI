from __future__ import annotations

import json
import threading
from datetime import date, datetime

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_text

DATEI = DATA_DIR / "budget.json"

PREISE = {
    "openai": 0.6,
    "anthropic": 3.0,
    "google": 0.3,
    "deepseek": 0.14,
    "mistral": 0.25,
    "glm": 0.2,
    "qwen": 0.2,
    "openrouter": 0.5,
    "groq": 0.1,
    "together": 0.3,
    "xai": 2.0,
    "nvidia": 0.0,
    "ollama": 0.0,
    "lmstudio": 0.0,
}


def _heute() -> str:
    return date.today().isoformat()


def _monat() -> str:
    return date.today().strftime("%Y-%m")


class BudgetService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._daten = self._laden()

    def _laden(self) -> dict:
        if DATEI.exists():
            try:
                roh = json.loads(DATEI.read_text(encoding="utf-8"))
                if isinstance(roh, dict):
                    return roh
            except Exception as _fehler:
                leise(_fehler, "services/budget_service")
        return {"tage": {}, "monate": {}, "gestoppt": ""}

    def _sichern(self) -> None:
        try:
            atomic_write_text(
                DATEI,
                json.dumps(self._daten, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as _fehler:
            leise(_fehler, "services/budget_service")

    def _grenzen(self) -> dict:
        try:
            from app.services.settings_service import get_settings_service

            werte = get_settings_service().get()
        except Exception as _fehler:
            leise(_fehler, "services/budget_service")
            werte = {}
        return {
            "tokens_tag": int(werte.get("budget_tokens_tag", 0) or 0),
            "euro_monat": float(werte.get("budget_euro_monat", 0.0) or 0.0),
            "warnung": float(werte.get("budget_warnung", 0.8) or 0.8),
        }

    def buchen(
        self, provider: str, tokens: int, modell: str = "", anfragen: int = 1
    ) -> None:
        if tokens <= 0 and anfragen <= 0:
            return
        preis = PREISE.get(provider, 0.4)
        kosten = (max(0, tokens) / 1_000_000.0) * preis
        with self._lock:
            tag = self._daten.setdefault("tage", {}).setdefault(
                _heute(), {"tokens": 0, "euro": 0.0, "anfragen": 0}
            )
            tag["tokens"] += max(0, tokens)
            tag["euro"] = round(tag["euro"] + kosten, 6)
            tag["anfragen"] += max(0, anfragen)
            monat = self._daten.setdefault("monate", {}).setdefault(
                _monat(), {"tokens": 0, "euro": 0.0, "anfragen": 0}
            )
            monat["tokens"] += max(0, tokens)
            monat["euro"] = round(monat["euro"] + kosten, 6)
            monat["anfragen"] += max(0, anfragen)
            self._daten["tage"] = dict(list(self._daten["tage"].items())[-90:])
            self._daten["monate"] = dict(list(self._daten["monate"].items())[-24:])
            self._sichern()

    def stand(self) -> dict:
        grenzen = self._grenzen()
        with self._lock:
            tag = dict(
                self._daten.get("tage", {}).get(
                    _heute(), {"tokens": 0, "euro": 0.0, "anfragen": 0}
                )
            )
            monat = dict(
                self._daten.get("monate", {}).get(
                    _monat(), {"tokens": 0, "euro": 0.0, "anfragen": 0}
                )
            )
        anteil_tag = (
            tag["tokens"] / grenzen["tokens_tag"] if grenzen["tokens_tag"] > 0 else 0.0
        )
        anteil_monat = (
            monat["euro"] / grenzen["euro_monat"] if grenzen["euro_monat"] > 0 else 0.0
        )
        return {
            "heute": tag,
            "monat": monat,
            "grenzen": grenzen,
            "anteil_tag": round(anteil_tag, 3),
            "anteil_monat": round(anteil_monat, 3),
            "gesperrt": anteil_tag >= 1.0 or anteil_monat >= 1.0,
            "warnung": max(anteil_tag, anteil_monat) >= grenzen["warnung"]
            and max(anteil_tag, anteil_monat) < 1.0,
        }

    def pruefen(self) -> tuple[bool, str]:
        stand = self.stand()
        if not stand["gesperrt"]:
            if stand["warnung"]:
                return True, (
                    "Achtung: Das Budget ist zu "
                    f"{int(max(stand['anteil_tag'], stand['anteil_monat']) * 100)}% "
                    "aufgebraucht."
                )
            return True, ""
        grenzen = stand["grenzen"]
        if stand["anteil_tag"] >= 1.0:
            return False, (
                f"Das Tagesbudget von {grenzen['tokens_tag']} Tokens ist "
                f"aufgebraucht ({stand['heute']['tokens']} verbraucht). Du kannst es "
                "unter Einstellungen -> Budget anheben oder bis morgen warten."
            )
        return False, (
            f"Das Monatsbudget von {grenzen['euro_monat']:.2f} Euro ist aufgebraucht "
            f"({stand['monat']['euro']:.2f} Euro verbraucht). Du kannst es unter "
            "Einstellungen -> Budget anheben."
        )

    def zuruecksetzen(self) -> None:
        with self._lock:
            self._daten = {"tage": {}, "monate": {}, "gestoppt": ""}
            self._sichern()


_service: BudgetService | None = None


def get_budget_service() -> BudgetService:
    global _service
    if _service is None:
        _service = BudgetService()
    return _service
