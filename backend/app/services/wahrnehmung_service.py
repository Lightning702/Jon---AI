from __future__ import annotations

import threading
from datetime import datetime

from app.core.fehler import leise
from app.services.kern import WAHRNEHMUNG, get_kern

MIN_FENSTER_S = 45


class WahrnehmungService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._letztes_fenster = ""
        self._letzte_mails = -1
        self._letzte_nachrichten = -1
        self._seit = datetime.now()

    def _an(self) -> bool:
        try:
            from app.services.settings_service import get_settings_service

            return bool(
                get_settings_service().get().get("wahrnehmung_enabled", False)
            )
        except Exception as _fehler:
            leise(_fehler, "services/wahrnehmung_service")
            return False

    def _fenster(self) -> dict | None:
        try:
            from app.services.automation_service import AutomationService

            fenster = AutomationService().list_windows()
            if not isinstance(fenster, list) or not fenster:
                return None
            titel = str(fenster[0].get("title", ""))[:120]
            if not titel or titel == self._letztes_fenster:
                return None
            vorher = self._letztes_fenster
            self._letztes_fenster = titel
            if not vorher:
                return None
            return {"titel": titel, "vorher": vorher}
        except Exception as _fehler:
            leise(_fehler, "services/wahrnehmung_service")
            return None

    def _mails(self) -> dict | None:
        try:
            from app.services.mail_service import get_mail_service

            stand = get_mail_service().check_mail(limit=5)
            anzahl = int(stand.get("ungelesen", 0) or 0) if isinstance(stand, dict) else 0
            if self._letzte_mails < 0:
                self._letzte_mails = anzahl
                return None
            if anzahl > self._letzte_mails:
                neu = anzahl - self._letzte_mails
                self._letzte_mails = anzahl
                return {"neu": neu, "gesamt": anzahl}
            self._letzte_mails = anzahl
            return None
        except Exception as _fehler:
            leise(_fehler, "services/wahrnehmung_service")
            return None

    def _handy(self) -> dict | None:
        try:
            from app.services.handy_service import get_handy_service

            geraete = get_handy_service().geraete()
            anzahl = len(geraete) if isinstance(geraete, list) else 0
            if self._letzte_nachrichten < 0:
                self._letzte_nachrichten = anzahl
                return None
            if anzahl > self._letzte_nachrichten:
                neu = anzahl - self._letzte_nachrichten
                self._letzte_nachrichten = anzahl
                return {"neu": neu}
            self._letzte_nachrichten = anzahl
            return None
        except Exception as _fehler:
            leise(_fehler, "services/wahrnehmung_service")
            return None

    def takt(self) -> dict:
        if not self._an():
            return {"aktiv": False}
        kern = get_kern()
        gemeldet: list[str] = []
        with self._lock:
            fenster = self._fenster()
            mails = self._mails()
            handy = self._handy()
        if fenster:
            kern.melden(WAHRNEHMUNG, "bildschirm", fenster, quelle="wahrnehmung")
            gemeldet.append("bildschirm")
        if mails:
            kern.melden(WAHRNEHMUNG, "mail", mails, quelle="wahrnehmung")
            gemeldet.append("mail")
        if handy:
            kern.melden(WAHRNEHMUNG, "handy", handy, quelle="wahrnehmung")
            gemeldet.append("handy")
        return {"aktiv": True, "gemeldet": gemeldet}


_service: WahrnehmungService | None = None


def get_wahrnehmung_service() -> WahrnehmungService:
    global _service
    if _service is None:
        _service = WahrnehmungService()
    return _service
