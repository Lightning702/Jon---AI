from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

from app.core.config import DATA_DIR, FROZEN, ROOT_DIR
from app.core.logbook import logger as logbook_logger

_log = logbook_logger("geraet_app")

ORDNER = DATA_DIR / "geraet-app"
TEIL = 512 * 1024
RELEASES = "https://api.github.com/repos/Lightning702/Jon---AI/releases/latest"


def _pruefsumme(pfad: Path) -> str:
    summe = hashlib.sha256()
    with pfad.open("rb") as datei:
        for stueck in iter(lambda: datei.read(1 << 16), b""):
            summe.update(stueck)
    return summe.hexdigest()


class GeraetAppService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._update: dict = {"laeuft": False, "schritt": "", "fehler": "", "fertig": False, "seit": 0.0}

    def _meta(self) -> dict:
        pfad = ORDNER / "jon-geraet.json"
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return daten if isinstance(daten, dict) else {}

    def datei(self) -> Path | None:
        meta = self._meta()
        name = Path(str(meta.get("apk") or "")).name
        if not name.endswith(".apk"):
            return None
        pfad = ORDNER / name
        return pfad if pfad.is_file() else None

    def info(self) -> dict:
        meta = self._meta()
        pfad = self.datei()
        if pfad is None:
            return {"verfuegbar": False}
        return {
            "verfuegbar": True,
            "version": str(meta.get("version") or ""),
            "code": int(meta.get("code") or 0),
            "groesse": pfad.stat().st_size,
            "sha256": str(meta.get("sha256") or ""),
            "name": pfad.name,
        }

    def teil(self, offset: int) -> dict:
        pfad = self.datei()
        if pfad is None:
            raise FileNotFoundError("Auf diesem Jon liegt keine App zum Aktualisieren.")
        groesse = pfad.stat().st_size
        start = max(0, min(int(offset), groesse))
        with pfad.open("rb") as datei:
            datei.seek(start)
            roh = datei.read(TEIL)
        return {"data": base64.b64encode(roh).decode("ascii"), "offset": start + len(roh), "size": groesse}

    def ablegen(self, quelle: Path, version: str, code: int) -> dict:
        ORDNER.mkdir(parents=True, exist_ok=True)
        ziel = ORDNER / f"Jon-Geraet-{version}.apk"
        if quelle.resolve() != ziel.resolve():
            shutil.copyfile(quelle, ziel)
        for alt in ORDNER.glob("Jon-Geraet-*.apk"):
            if alt.name != ziel.name:
                alt.unlink(missing_ok=True)
        meta = {"version": version, "code": int(code), "apk": ziel.name, "sha256": _pruefsumme(ziel), "groesse": ziel.stat().st_size}
        (ORDNER / "jon-geraet.json").write_text(json.dumps(meta), encoding="utf-8")
        return self.info()

    async def von_github_holen(self) -> dict:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": "Jon"}) as client:
            antwort = await client.get(RELEASES)
            antwort.raise_for_status()
            assets = {a.get("name"): a.get("browser_download_url") for a in antwort.json().get("assets", []) if isinstance(a, dict)}
            meta_url = assets.get("jon-geraet.json")
            if not meta_url:
                return {**self.info(), "neu": False, "hinweis": "Im neuesten Release liegt keine App."}
            meta = (await client.get(meta_url)).json()
            code = int(meta.get("code") or 0)
            if code <= int(self.info().get("code") or 0):
                return {**self.info(), "neu": False}
            apk_url = assets.get(str(meta.get("apk") or ""))
            if not apk_url:
                return {**self.info(), "neu": False, "hinweis": "Die APK fehlt im Release."}
            ORDNER.mkdir(parents=True, exist_ok=True)
            teil = ORDNER / "download.teil"
            async with client.stream("GET", apk_url) as strom:
                strom.raise_for_status()
                with teil.open("wb") as datei:
                    async for stueck in strom.aiter_bytes(1 << 16):
                        datei.write(stueck)
        if _pruefsumme(teil) != str(meta.get("sha256") or ""):
            teil.unlink(missing_ok=True)
            raise ValueError("Die heruntergeladene App ist beschädigt.")
        ergebnis = self.ablegen(teil, str(meta.get("version") or "0"), code)
        teil.unlink(missing_ok=True)
        _log.info("Jon Gerät %s von GitHub geholt", ergebnis.get("version"))
        return {**ergebnis, "neu": True}

    def pi_update_moeglich(self) -> tuple[bool, str]:
        if FROZEN or sys.platform.startswith("win"):
            return False, "Das geht nur bei Jon auf dem Raspberry Pi. Am PC aktualisiert sich Jon über das Setup."
        if not (ROOT_DIR / ".git").exists():
            return False, "Jon läuft hier nicht aus einem Git-Ordner."
        if shutil.which("git") is None:
            return False, "git fehlt auf diesem Gerät."
        return True, ""

    def pi_update_stand(self) -> dict:
        moeglich, grund = self.pi_update_moeglich()
        with self._lock:
            return {**self._update, "moeglich": moeglich, "grund": grund}

    def pi_update_starten(self) -> dict:
        moeglich, grund = self.pi_update_moeglich()
        if not moeglich:
            raise ValueError(grund)
        with self._lock:
            if self._update["laeuft"]:
                return dict(self._update)
            self._update = {"laeuft": True, "schritt": "Starte …", "fehler": "", "fertig": False, "seit": time.time()}
        threading.Thread(target=self._pi_update, name="pi-update", daemon=True).start()
        return self.pi_update_stand()

    def _schritt(self, text: str) -> None:
        with self._lock:
            self._update["schritt"] = text
        _log.info("Pi-Update: %s", text)

    def _befehl(self, *teile: str) -> subprocess.CompletedProcess:
        return subprocess.run(list(teile), cwd=ROOT_DIR, capture_output=True, text=True, timeout=900)

    def _pi_update(self) -> None:
        try:
            self._schritt("Hole die neueste Version …")
            self._befehl("git", "stash", "push", "-u", "-m", "jon-update-autostash")
            gezogen = self._befehl("git", "pull", "--rebase")
            if gezogen.returncode != 0:
                self._befehl("git", "rebase", "--abort")
                self._befehl("git", "stash", "pop")
                raise RuntimeError((gezogen.stderr or gezogen.stdout or "git pull ist fehlgeschlagen.").strip()[-400:])
            self._befehl("git", "stash", "pop")
            anforderungen = ROOT_DIR / "backend" / "requirements-pi.txt"
            if anforderungen.is_file():
                self._schritt("Aktualisiere Bibliotheken …")
                pip = self._befehl(sys.executable, "-m", "pip", "install", "-q", "-r", str(anforderungen))
                if pip.returncode != 0:
                    _log.warning("pip-Update unvollständig: %s", (pip.stderr or "")[-400:])
            self._schritt("Starte Jon neu …")
            with self._lock:
                self._update.update({"fertig": True})
            time.sleep(2.5)
            os._exit(0)
        except Exception as fehler:
            with self._lock:
                self._update.update({"laeuft": False, "fehler": str(fehler), "schritt": ""})
            _log.warning("Pi-Update fehlgeschlagen: %s", fehler)


_dienst: GeraetAppService | None = None


def get_geraet_app_service() -> GeraetAppService:
    global _dienst
    if _dienst is None:
        _dienst = GeraetAppService()
    return _dienst
