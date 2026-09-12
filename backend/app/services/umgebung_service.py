from __future__ import annotations

import shutil
import sys
import threading
import time
from importlib import util as modul_util

from app.core.fehler import leise
from app.services import plattform

CACHE_SEKUNDEN = 300

BEFEHLE = (
    ("python", "Python", "Damit laeuft Jon selbst und fuehrt Code aus."),
    ("node", "Node.js", "Fuer JavaScript- und TypeScript-Projekte."),
    ("npm", "npm", "Installiert Abhaengigkeiten fuer Web-Projekte."),
    ("git", "Git", "Versioniert Code und holt Projekte aus dem Netz."),
    ("ffmpeg", "FFmpeg", "Wandelt Audio und Video um."),
    ("blender", "Blender", "Erzeugt und rendert 3D-Szenen."),
)

PAKETE = (
    ("reportlab", "PDF schreiben", "reportlab"),
    ("docx", "Word-Dateien schreiben", "python-docx"),
    ("openpyxl", "Excel-Dateien schreiben", "openpyxl"),
    ("pptx", "Praesentationen schreiben", "python-pptx"),
    ("odf", "OpenDocument schreiben", "odfpy"),
    ("PIL", "Bilder bearbeiten", "pillow"),
    ("playwright", "Browser steuern", "playwright"),
    ("yt_dlp", "Videos herunterladen", "yt-dlp"),
)


class UmgebungService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stand: dict = {}
        self._zeit = 0.0

    @staticmethod
    def _paket_da(modul: str) -> bool:
        try:
            return modul_util.find_spec(modul) is not None
        except Exception as fehler:
            leise(fehler, "services/umgebung_service")
            return False

    def _blender(self) -> dict:
        try:
            from app.services.blender_service import get_blender_service

            stand = get_blender_service().gefunden()
            return {
                "befehl": "blender",
                "da": bool(stand.get("da")),
                "pfad": stand.get("pfad", ""),
                "version": stand.get("version", ""),
            }
        except Exception as fehler:
            leise(fehler, "services/umgebung_service")
            return {"befehl": "blender", "da": False}

    def _llm(self) -> dict:
        try:
            from app.core.keys import get_key_manager

            verwalter = get_key_manager()
            bereit = [
                eintrag.provider
                for eintrag in verwalter.status()
                if getattr(eintrag, "configured", False)
            ]
        except Exception as fehler:
            leise(fehler, "services/umgebung_service")
            bereit = []
        lokal = bool(shutil.which("ollama"))
        return {
            "anbieter": bereit,
            "ollama": lokal,
            "bereit": bool(bereit) or lokal,
            "hinweis": ""
            if (bereit or lokal)
            else (
                "Noch kein Modell eingerichtet. Trage in der App unter Konten einen "
                "Schluessel ein oder installiere Ollama fuer ein lokales Modell."
            ),
        }

    def _telegram(self) -> dict:
        try:
            from app.services.settings_service import get_settings_service

            werte = get_settings_service().get()
            token = bool(str(werte.get("telegram_bot_token", "") or "").strip())
            gebunden = bool(str(werte.get("telegram_chat_id", "") or "").strip())
        except Exception as fehler:
            leise(fehler, "services/umgebung_service")
            token, gebunden = False, False
        return {
            "token": token,
            "gebunden": gebunden,
            "bereit": token and gebunden,
            "hinweis": ""
            if token
            else "Kein Telegram-Bot eingerichtet (Einstellungen -> Verbindungen).",
        }

    def pruefen(self, neu: bool = False) -> dict:
        with self._lock:
            frisch = self._stand and time.time() - self._zeit < CACHE_SEKUNDEN
            if frisch and not neu:
                return self._stand
        werkzeuge = []
        for befehl, titel, wozu in BEFEHLE:
            eintrag = self._blender() if befehl == "blender" else plattform.werkzeug_da(befehl)
            eintrag["titel"] = titel
            eintrag["wozu"] = wozu
            werkzeuge.append(eintrag)
        pakete = [
            {
                "modul": modul,
                "wozu": wozu,
                "paket": paket,
                "da": self._paket_da(modul),
                "installieren": f"pip install {paket}",
            }
            for modul, wozu, paket in PAKETE
        ]
        fehlend = [w["titel"] for w in werkzeuge if not w["da"]]
        fehlende_pakete = [p["paket"] for p in pakete if not p["da"]]
        stand = {
            "plattform": plattform.name(),
            "dateimanager": plattform.dateimanager(),
            "python": sys.version.split()[0],
            "werkzeuge": werkzeuge,
            "pakete": pakete,
            "llm": self._llm(),
            "telegram": self._telegram(),
            "fehlt": fehlend,
            "fehlende_pakete": fehlende_pakete,
            "geprueft": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            from app.services.dateiraum_service import get_dateiraum_service

            stand["dateiraum"] = str(get_dateiraum_service().sicherstellen())
        except Exception as fehler:
            leise(fehler, "services/umgebung_service")
        with self._lock:
            self._stand = stand
            self._zeit = time.time()
        return stand

    def bericht(self) -> str:
        stand = self.pruefen()
        zeilen = [f"Jon laeuft auf {stand['plattform']} mit Python {stand['python']}."]
        for werkzeug in stand["werkzeuge"]:
            zeichen = "ja" if werkzeug["da"] else "fehlt"
            zusatz = f" ({werkzeug['version']})" if werkzeug.get("version") else ""
            zeilen.append(f"- {werkzeug['titel']}: {zeichen}{zusatz} - {werkzeug['wozu']}")
        if stand["fehlende_pakete"]:
            zeilen.append(
                "Fehlende Python-Pakete: pip install "
                + " ".join(stand["fehlende_pakete"])
            )
        if not stand["llm"]["bereit"]:
            zeilen.append(stand["llm"]["hinweis"])
        return "\n".join(zeilen)


_service: UmgebungService | None = None


def get_umgebung_service() -> UmgebungService:
    global _service
    if _service is None:
        _service = UmgebungService()
    return _service
