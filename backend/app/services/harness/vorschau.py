from __future__ import annotations

import asyncio
import http.server
import json
import os
import re
import signal
import subprocess
import threading
import time
from collections import deque
from functools import partial
from pathlib import Path
from urllib.parse import unquote, urlsplit

from app.services.harness.workspace import Workspace

SKRIPTE = ("dev", "start", "preview", "serve")
STATISCH = ("", "dist", "build", "public", "docs", "www", "site", "out")
ADRESSE = re.compile(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|\[::\]):(\d{2,5})[^\s'\"]*")
FARBE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
STARTZEIT_S = 240
GEHEIM = {"credentials", "credentials.json", "secrets.json", "access.token", "id_rsa", "id_ed25519"}


def geheim(name: str) -> bool:
    klein = name.lower()
    return (klein.startswith(".") and klein != ".well-known") or klein in GEHEIM or klein.endswith((".pem", ".key", ".p12", ".pfx", ".kdbx"))


def erkennen(root: Path) -> dict:
    paket = root / "package.json"
    if paket.is_file():
        try:
            skripte = json.loads(paket.read_text(encoding="utf-8")).get("scripts") or {}
        except (OSError, ValueError, AttributeError):
            skripte = {}
        for name in SKRIPTE:
            if isinstance(skripte, dict) and isinstance(skripte.get(name), str):
                installieren = not (root / "node_modules").is_dir()
                befehl = ("npm install && " if installieren else "") + f"npm run {name}"
                return {"art": "npm", "skript": name, "befehl": befehl, "installieren": installieren}
    for unterordner in STATISCH:
        ordner = root / unterordner if unterordner else root
        if (ordner / "index.html").is_file():
            return {"art": "statisch", "ordner": str(ordner), "datei": "index.html"}
    for datei in sorted(root.glob("*.html")) + sorted(root.glob("*/*.html")):
        if not any(Workspace.excluded(teil) or geheim(teil) for teil in datei.relative_to(root).parts):
            return {"art": "statisch", "ordner": str(datei.parent), "datei": datei.name}
    return {"art": ""}


class _Statisch(http.server.SimpleHTTPRequestHandler):
    erlaubt: set[str] = set()

    def log_message(self, *args) -> None:
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _pruefen(self) -> bool:
        if self.headers.get("Host", "") not in self.erlaubt:
            self.send_error(403)
            return False
        teile = [t for t in unquote(urlsplit(self.path).path).split("/") if t]
        if any(t == ".." or geheim(t) for t in teile):
            self.send_error(404)
            return False
        return True

    def do_GET(self) -> None:
        if self._pruefen():
            super().do_GET()

    def do_HEAD(self) -> None:
        if self._pruefen():
            super().do_HEAD()


class Vorschau:
    def __init__(self) -> None:
        self.laeufe: dict[str, dict] = {}

    @staticmethod
    def _schluessel(root: Path) -> str:
        return os.path.normcase(str(root))

    def zustand(self, root: Path) -> dict:
        lauf = self.laeufe.get(self._schluessel(root))
        if not lauf:
            return {"status": "aus", "erkannt": erkennen(root)}
        if lauf["status"] == "startet" and time.time() - lauf["seit"] > STARTZEIT_S and not lauf.get("url"):
            lauf["hinweis"] = "Der Server meldet noch keine Adresse. Sieh dir das Protokoll an."
        return {"status": lauf["status"], "url": lauf.get("url", ""), "art": lauf["art"], "befehl": lauf.get("befehl", ""), "log": list(lauf["log"])[-80:], "seit": lauf["seit"], "hinweis": lauf.get("hinweis", ""), "erkannt": lauf["erkannt"]}

    async def starten(self, root: Path) -> dict:
        schluessel = self._schluessel(root)
        vorhanden = self.laeufe.get(schluessel)
        if vorhanden and vorhanden["status"] in {"startet", "laeuft"}:
            return self.zustand(root)
        await self.stoppen(root)
        erkannt = erkennen(root)
        if not erkannt.get("art"):
            raise ValueError("Für dieses Projekt habe ich keine Vorschau gefunden. Lege eine index.html an oder ergänze in package.json ein dev-Skript.")
        lauf = {"art": erkannt["art"], "erkannt": erkannt, "log": deque(maxlen=400), "seit": time.time(), "status": "startet"}
        self.laeufe[schluessel] = lauf
        if erkannt["art"] == "statisch":
            self._statisch(lauf, Path(erkannt["ordner"]), erkannt["datei"])
        else:
            await self._npm(lauf, root, erkannt["befehl"])
        return self.zustand(root)

    def _statisch(self, lauf: dict, ordner: Path, datei: str) -> None:
        handler = type("Handler", (_Statisch,), {"erlaubt": set()})
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(handler, directory=str(ordner)))
        port = server.server_address[1]
        handler.erlaubt = {f"127.0.0.1:{port}", f"localhost:{port}"}
        threading.Thread(target=server.serve_forever, daemon=True).start()
        lauf.update(server=server, statisch=True, url=f"http://127.0.0.1:{port}/{datei}", status="laeuft")
        lauf["log"].append(f"Statische Vorschau aus {ordner}")

    async def _npm(self, lauf: dict, root: Path, befehl: str) -> None:
        umgebung = {**os.environ, "BROWSER": "none", "FORCE_COLOR": "0", "NO_COLOR": "1", "CI": "1"}
        if os.name == "nt":
            argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", befehl.replace("npm ", "npm.cmd ").replace(" && ", "; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; ")]
            optionen = {"creationflags": subprocess.CREATE_NO_WINDOW}
        else:
            argv = ["/bin/sh", "-c", befehl]
            optionen = {"start_new_session": True}
        prozess = await asyncio.create_subprocess_exec(*argv, cwd=str(root), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, stdin=asyncio.subprocess.DEVNULL, env=umgebung, **optionen)
        lauf.update(prozess=prozess, befehl=befehl)
        if os.name == "nt":
            from app.services.harness.windows_job import WindowsJob

            try:
                lauf["job"] = WindowsJob(prozess.pid)
            except OSError:
                lauf["job"] = None
        lauf["leser"] = asyncio.create_task(self._lesen(lauf, prozess))

    async def _lesen(self, lauf: dict, prozess) -> None:
        while True:
            zeile = await prozess.stdout.readline()
            if not zeile:
                break
            text = FARBE.sub("", zeile.decode("utf-8", errors="replace")).rstrip()
            if not text:
                continue
            lauf["log"].append(text[:500])
            treffer = ADRESSE.search(text)
            if treffer and not lauf.get("url"):
                lauf["url"] = re.sub(r"//(0\.0\.0\.0|\[::\])", "//127.0.0.1", treffer.group(0)).rstrip(".,;)")
                lauf["status"] = "laeuft"
        await prozess.wait()
        if lauf["status"] != "gestoppt":
            lauf["status"] = "beendet" if prozess.returncode == 0 else "fehler"
            lauf["log"].append(f"Server beendet (Code {prozess.returncode}).")

    async def stoppen(self, root: Path) -> dict:
        lauf = self.laeufe.get(self._schluessel(root))
        if lauf:
            await self._beenden(lauf)
        return self.zustand(root) if lauf else {"status": "aus", "erkannt": erkennen(root)}

    async def _beenden(self, lauf: dict) -> None:
        lauf["status"] = "gestoppt"
        server = lauf.pop("server", None)
        if server is not None:
            server.shutdown()
            server.server_close()
        prozess = lauf.get("prozess")
        if prozess is not None and prozess.returncode is None:
            job = lauf.pop("job", None)
            if job is not None:
                job.close()
            elif os.name != "nt":
                try:
                    os.killpg(prozess.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                prozess.kill()
            try:
                await asyncio.wait_for(prozess.wait(), 8)
            except asyncio.TimeoutError:
                if os.name != "nt":
                    try:
                        os.killpg(prozess.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                await prozess.wait()
        leser = lauf.pop("leser", None)
        if leser is not None:
            await asyncio.gather(leser, return_exceptions=True)

    async def close(self) -> None:
        for lauf in list(self.laeufe.values()):
            await self._beenden(lauf)


_vorschau: Vorschau | None = None


def get_vorschau() -> Vorschau:
    global _vorschau
    if _vorschau is None:
        _vorschau = Vorschau()
    return _vorschau
