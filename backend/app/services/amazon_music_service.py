from __future__ import annotations

import os
import re
import subprocess
import time
import urllib.parse

from app.services.spotify_service import MOODS

WEB = "https://music.amazon.de"


class AmazonMusicService:
    def _open(self, target: str) -> None:
        if os.name == "nt":
            os.startfile(target)
            return
        subprocess.Popen(["xdg-open", target])

    def _desktop_app(self) -> str:
        if os.name != "nt":
            return ""
        from app.services.system_service import SystemService

        result = SystemService().run_powershell(
            "(Get-Process -Name 'Amazon Music' -ErrorAction SilentlyContinue "
            "| Select-Object -First 1).ProcessName"
        )
        return (result.stdout or "").strip()

    def play(self, query: str = "") -> dict:
        from app.services.system_service import SystemService

        system = SystemService()
        query = query.strip()
        if not query:
            if not self._desktop_app():
                self._open(WEB)
                time.sleep(6)
            system.media_control("play_pause")
            return {"gestartet": "zuletzt gespielte Musik", "wo": "Amazon Music"}
        term = MOODS.get(query.lower(), query)
        self._open(f"{WEB}/search/{urllib.parse.quote(term)}")
        time.sleep(7)
        system.media_control("play_pause")
        return {
            "gesucht": term,
            "wo": "Amazon Music",
            "hinweis": (
                "Amazon Music hat keine offene Wiedergabe-Schnittstelle. Ich habe "
                "die Suche geoeffnet und Play gedrueckt. Falls nichts startet, "
                "klick einmal auf den ersten Treffer - danach kann ich mit "
                "media_control weiter steuern. Fuer vollautomatisches Abspielen "
                "ist Spotify der bessere Weg."
            ),
        }

    def now_playing(self) -> dict:
        from app.services.system_service import SystemService

        result = SystemService().run_powershell(
            "Get-Process -ErrorAction SilentlyContinue | Where-Object "
            "{ $_.MainWindowTitle -and $_.ProcessName -like '*Amazon*' } | "
            "Select-Object -ExpandProperty MainWindowTitle -First 1"
        )
        title = (result.stdout or "").strip()
        if title and title.lower() not in ("amazon music",):
            clean = re.sub(r"\s*[-|]\s*Amazon Music.*$", "", title, flags=re.I)
            if clean:
                return {"laeuft": True, "titel": clean.strip(), "wo": "Amazon Music"}
        try:
            import pygetwindow

            for raw in pygetwindow.getAllTitles():
                if not raw or "amazon music" not in raw.lower():
                    continue
                clean = re.sub(
                    r"\s*[-|·]\s*Amazon Music.*$", "", raw, flags=re.I
                ).strip()
                if clean and clean.lower() not in ("amazon music",):
                    return {
                        "laeuft": True,
                        "titel": clean,
                        "wo": "Amazon Music (Browser)",
                    }
        except Exception:
            pass
        return {"laeuft": False, "hinweis": "Amazon Music laeuft gerade nicht"}


_service: AmazonMusicService | None = None


def get_amazon_music_service() -> AmazonMusicService:
    global _service
    if _service is None:
        _service = AmazonMusicService()
    return _service
