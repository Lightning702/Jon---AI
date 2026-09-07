from __future__ import annotations

import threading
from datetime import datetime

from app.core.fehler import leise

KANAELE = ("browser", "bildschirm", "dateien", "handy", "telefon", "musik", "system")


class HandlungsraumService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._zusatz: dict[str, dict] = {}

    def melden(self, kanal: str, daten: dict) -> None:
        with self._lock:
            eintrag = dict(daten)
            eintrag["zeit"] = datetime.now().isoformat(timespec="seconds")
            self._zusatz[kanal[:24]] = eintrag

    def _browser(self) -> dict:
        try:
            from app.services.browser.manager import alle_manager
            from app.services.browser.zustand import alle_zustaende

            offen = [k for k, m in alle_manager().items() if m.offen]
            zustaende = {
                k: {
                    "url": s.lesen().url,
                    "titel": s.lesen().titel,
                    "status": s.lesen().status,
                }
                for k, s in alle_zustaende().items()
                if s.lesen().url
            }
            return {"offen": offen, "sitzungen": zustaende}
        except Exception as _fehler:
            leise(_fehler, "services/handlungsraum_service")
            return {}

    def _bildschirm(self) -> dict:
        try:
            from app.services.automation_service import AutomationService
            from app.services.system_service import SystemService

            dienst = SystemService()
            fenster = AutomationService().list_windows()
            aktiv = fenster[0] if isinstance(fenster, list) and fenster else {}
            return {
                "fenster": len(fenster) if isinstance(fenster, list) else 0,
                "vorne": aktiv.get("title", "") if isinstance(aktiv, dict) else "",
                "leerlauf_s": round(dienst.idle_seconds(), 1),
            }
        except Exception as _fehler:
            leise(_fehler, "services/handlungsraum_service")
            return {}

    def _handy(self) -> dict:
        try:
            from app.services.connectors import get_connector_manager

            uebersicht = get_connector_manager().uebersicht()
            return {"geraete": len(uebersicht) if isinstance(uebersicht, list) else 0}
        except Exception as _fehler:
            leise(_fehler, "services/handlungsraum_service")
            return {}

    def _auftraege(self) -> dict:
        try:
            from app.services.auftrag_service import get_auftrag_service

            offen = get_auftrag_service().offene()
            return {
                "offen": len(offen),
                "titel": [a["titel"] for a in offen[:5]],
            }
        except Exception as _fehler:
            leise(_fehler, "services/handlungsraum_service")
            return {}

    def _ziele(self) -> dict:
        try:
            from app.services.ziel_service import get_ziel_service

            dienst = get_ziel_service()
            return {
                "offen": len(dienst.liste()),
                "faellig": [z["titel"] for z in dienst.faellig(2)][:5],
            }
        except Exception as _fehler:
            leise(_fehler, "services/handlungsraum_service")
            return {}

    def zustand(self) -> dict:
        with self._lock:
            zusatz = dict(self._zusatz)
        daten = {
            "zeit": datetime.now().isoformat(timespec="seconds"),
            "browser": self._browser(),
            "bildschirm": self._bildschirm(),
            "handy": self._handy(),
            "auftraege": self._auftraege(),
            "ziele": self._ziele(),
        }
        try:
            from app.services.netz_service import stand

            daten["netz"] = stand()
        except Exception as _fehler:
            leise(_fehler, "services/handlungsraum_service")
        try:
            from app.services.budget_service import get_budget_service

            daten["budget"] = get_budget_service().stand()["heute"]
        except Exception as _fehler:
            leise(_fehler, "services/handlungsraum_service")
        for kanal, eintrag in zusatz.items():
            daten.setdefault(kanal, eintrag)
        return daten

    def prompt_block(self) -> str:
        daten = self.zustand()
        zeilen: list[str] = []
        browser = daten.get("browser") or {}
        if browser.get("sitzungen"):
            for kennung, wert in list(browser["sitzungen"].items())[:2]:
                zeilen.append(
                    f"- Browser ({kennung}): {wert['titel'][:60]} - {wert['url'][:80]}"
                )
        bildschirm = daten.get("bildschirm") or {}
        if bildschirm.get("vorne"):
            zeilen.append(f"- Vorne am Bildschirm: {bildschirm['vorne'][:70]}")
        auftraege = daten.get("auftraege") or {}
        if auftraege.get("offen"):
            zeilen.append(
                f"- Offene Auftraege: {auftraege['offen']} "
                f"({', '.join(auftraege.get('titel', [])[:2])})"
            )
        ziele = daten.get("ziele") or {}
        if ziele.get("faellig"):
            zeilen.append("- Bald faellig: " + ", ".join(ziele["faellig"][:3]))
        if not daten.get("netz", {}).get("online", True):
            zeilen.append("- Gerade offline.")
        if not zeilen:
            return ""
        return "So sieht es bei dir gerade aus:\n" + "\n".join(zeilen)


_service: HandlungsraumService | None = None


def get_handlungsraum_service() -> HandlungsraumService:
    global _service
    if _service is None:
        _service = HandlungsraumService()
    return _service
