from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request

from app.services.settings_service import get_settings_service

KINDS = {"track", "album", "playlist", "artist"}

MOODS = {
    "entspannt": "chill relax",
    "chillig": "chill",
    "ruhig": "calm quiet",
    "fokus": "focus concentration",
    "konzentration": "focus",
    "party": "party hits",
    "gute laune": "good mood happy",
    "traurig": "sad",
    "sport": "workout",
    "schlafen": "sleep",
}


class SpotifyService:
    def __init__(self) -> None:
        self._token = ""
        self._expires = 0.0

    def _credentials(self) -> tuple[str, str]:
        cfg = get_settings_service().get()
        client_id = str(cfg.get("spotify_client_id", "")).strip()
        secret = str(cfg.get("spotify_client_secret", "")).strip()
        if not client_id or not secret:
            raise RuntimeError(
                "Spotify ist nicht eingerichtet. Hol dir kostenlos eine Client-ID "
                "und ein Secret auf developer.spotify.com/dashboard (App anlegen) "
                "und trage beides im Zahnrad-Menue unter 'Verbindungen' ein."
            )
        return client_id, secret

    def _access_token(self) -> str:
        if self._token and time.time() < self._expires - 30:
            return self._token
        client_id, secret = self._credentials()
        auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        request = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            data = json.loads(response.read())
        self._token = str(data["access_token"])
        self._expires = time.time() + float(data.get("expires_in", 3600))
        return self._token

    def search(self, query: str, kind: str = "track", limit: int = 5) -> list[dict]:
        query = query.strip()
        if not query:
            return []
        kind = kind.strip().lower()
        if kind not in KINDS:
            kind = "track"
        term = MOODS.get(query.lower(), query)
        url = "https://api.spotify.com/v1/search?" + urllib.parse.urlencode(
            {
                "q": term,
                "type": kind,
                "limit": max(1, min(int(limit), 20)),
                "market": "DE",
            }
        )
        request = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self._access_token()}"}
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            data = json.loads(response.read())
        items = (data.get(f"{kind}s") or {}).get("items") or []
        results = []
        for item in items:
            if not item:
                continue
            artists = ", ".join(
                a.get("name", "") for a in (item.get("artists") or [])
            )
            if kind == "playlist":
                artists = (item.get("owner") or {}).get("display_name", "Spotify")
            results.append(
                {
                    "name": item.get("name"),
                    "kuenstler": artists,
                    "uri": item.get("uri"),
                    "typ": kind,
                }
            )
        return results

    def _desktop_app(self) -> bool:
        if os.name != "nt":
            return False
        try:
            import winreg

            winreg.CloseKey(
                winreg.OpenKey(
                    winreg.HKEY_CLASSES_ROOT, "spotify\\shell\\open\\command"
                )
            )
            return True
        except Exception:
            return False

    def _web_url(self, uri: str) -> str:
        parts = uri.split(":")
        if len(parts) == 3:
            return f"https://open.spotify.com/{parts[1]}/{parts[2]}"
        return "https://open.spotify.com"

    def _open(self, target: str) -> None:
        if os.name == "nt":
            os.startfile(target)
            return
        subprocess.Popen(["xdg-open", target])

    def _launch(self, uri: str) -> str:
        from app.services.system_service import SystemService

        if self._desktop_app():
            self._open(uri)
            return "app"
        self._open(self._web_url(uri))
        time.sleep(6)
        try:
            SystemService().media_control("play_pause")
        except Exception:
            pass
        return "web"

    def play(self, query: str = "", kind: str = "track") -> dict:
        from app.services.system_service import SystemService

        query = query.strip()
        if not query:
            if self._desktop_app():
                self._open("spotify:")
                time.sleep(2)
            SystemService().media_control("play_pause")
            return {"gestartet": "zuletzt gespielte Musik"}
        hits = self.search(query, kind, 1)
        if not hits:
            raise ValueError(f"Nichts gefunden fuer: {query}")
        hit = hits[0]
        where = self._launch(str(hit["uri"]))
        result = {
            "gestartet": hit["name"],
            "kuenstler": hit["kuenstler"],
            "typ": hit["typ"],
            "wo": "Spotify-App" if where == "app" else "Spotify Web Player",
        }
        if where == "web":
            result["hinweis"] = (
                "Die Spotify-App ist nicht installiert - ich habe den Web Player "
                "im Browser geoeffnet und Play gedrueckt. Falls nichts laeuft, "
                "musst du dort einmal eingeloggt sein."
            )
        return result

    def now_playing(self) -> dict:
        from app.services.system_service import SystemService

        result = SystemService().run_powershell(
            "Get-Process -Name Spotify -ErrorAction SilentlyContinue | "
            "Where-Object { $_.MainWindowTitle } | "
            "Select-Object -ExpandProperty MainWindowTitle -First 1"
        )
        title = (result.stdout or "").strip()
        if title and title.lower() not in ("spotify", "spotify premium", "spotify free"):
            artist, _, song = title.partition(" - ")
            if song:
                return {
                    "laeuft": True,
                    "kuenstler": artist.strip(),
                    "titel": song.strip(),
                    "wo": "Spotify-App",
                }
        try:
            import pygetwindow

            for raw in pygetwindow.getAllTitles():
                if not raw:
                    continue
                match = re.match(
                    r"^(.*?)\s*[-·|]\s*Spotify.*?(?:Google Chrome|Mozilla Firefox|"
                    r"Microsoft.?\s?Edge|Opera|Brave)\s*$",
                    raw,
                    re.I,
                )
                if match and match.group(1).strip():
                    text = match.group(1).strip()
                    artist, _, song = text.partition(" · ")
                    if not song:
                        artist, _, song = text.partition(" - ")
                    return {
                        "laeuft": True,
                        "titel": (song or text).strip(),
                        "kuenstler": artist.strip() if song else "",
                        "wo": "Spotify Web Player",
                    }
        except Exception:
            pass
        if title:
            return {"laeuft": False, "hinweis": "Spotify ist offen, spielt aber nichts"}
        return {"laeuft": False, "hinweis": "Spotify laeuft gerade nicht"}


_service: SpotifyService | None = None


def get_spotify_service() -> SpotifyService:
    global _service
    if _service is None:
        _service = SpotifyService()
    return _service
