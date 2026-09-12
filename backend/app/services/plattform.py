from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.core.fehler import leise

LINUX_MANAGER = (
    ("nautilus", ["--select"]),
    ("dolphin", ["--select"]),
    ("nemo", []),
    ("thunar", []),
    ("pcmanfm", []),
)


def name() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def dateimanager() -> str:
    system = name()
    if system == "windows":
        return "Explorer"
    if system == "macos":
        return "Finder"
    for befehl, _ in LINUX_MANAGER:
        if shutil.which(befehl):
            return befehl
    return "Dateimanager"


def _linux_oeffnen(ziel: Path, markieren: bool) -> bool:
    if markieren:
        for befehl, flaggen in LINUX_MANAGER:
            if not shutil.which(befehl):
                continue
            try:
                subprocess.Popen([befehl, *flaggen, str(ziel)])
                return True
            except Exception as fehler:
                leise(fehler, "services/plattform")
    oeffner = shutil.which("xdg-open") or shutil.which("gio")
    if not oeffner:
        return False
    try:
        pfad = ziel if ziel.is_dir() else ziel.parent
        if oeffner.endswith("gio"):
            subprocess.Popen([oeffner, "open", str(pfad)])
        else:
            subprocess.Popen([oeffner, str(pfad)])
        return True
    except Exception as fehler:
        leise(fehler, "services/plattform")
        return False


def datei_oeffnen(pfad: str | Path) -> dict:
    ziel = Path(pfad).expanduser()
    if not ziel.exists():
        return {"error": f"Das gibt es nicht: {ziel}"}
    system = name()
    try:
        if system == "windows":
            os.startfile(str(ziel))
        elif system == "macos":
            subprocess.Popen(["open", str(ziel)])
        else:
            if not _linux_oeffnen(ziel, markieren=False):
                return {
                    "error": (
                        "Auf diesem System ist kein Programm zum Oeffnen eingerichtet "
                        "(xdg-open fehlt)."
                    )
                }
    except Exception as exc:
        return {"error": f"Liess sich nicht oeffnen: {exc}"}
    return {"ok": True, "pfad": str(ziel), "womit": system}


def ordner_oeffnen(pfad: str | Path, markieren: bool = True) -> dict:
    ziel = Path(pfad).expanduser()
    if not ziel.exists():
        eltern = ziel.parent
        if not eltern.exists():
            return {"error": f"Den Ordner gibt es nicht: {ziel}"}
        ziel = eltern
        markieren = False
    system = name()
    try:
        if system == "windows":
            if markieren and ziel.is_file():
                subprocess.Popen(["explorer", "/select,", str(ziel)])
            else:
                ordner = ziel if ziel.is_dir() else ziel.parent
                subprocess.Popen(["explorer", str(ordner)])
        elif system == "macos":
            if markieren and ziel.is_file():
                subprocess.Popen(["open", "-R", str(ziel)])
            else:
                ordner = ziel if ziel.is_dir() else ziel.parent
                subprocess.Popen(["open", str(ordner)])
        else:
            if not _linux_oeffnen(ziel, markieren and ziel.is_file()):
                return {
                    "error": (
                        "Auf diesem System ist kein Dateimanager gefunden worden "
                        "(nautilus, dolphin, nemo, thunar oder xdg-open)."
                    )
                }
    except Exception as exc:
        return {"error": f"Der Ordner liess sich nicht oeffnen: {exc}"}
    ordner = ziel if ziel.is_dir() else ziel.parent
    return {"ok": True, "ordner": str(ordner), "womit": dateimanager()}


def programm_starten(pfad: str | Path, argumente: list[str] | None = None) -> dict:
    ziel = str(pfad)
    gefunden = shutil.which(ziel) or (str(Path(ziel).expanduser()) if Path(ziel).expanduser().exists() else "")
    if not gefunden:
        if name() == "windows":
            try:
                os.startfile(ziel)
                return {"ok": True, "gestartet": ziel}
            except Exception as exc:
                return {"error": f"Programm nicht gefunden: {ziel} ({exc})"}
        return {"error": f"Programm nicht gefunden: {ziel}"}
    try:
        subprocess.Popen([gefunden, *(argumente or [])])
    except Exception as exc:
        return {"error": f"Programm liess sich nicht starten: {exc}"}
    return {"ok": True, "gestartet": gefunden}


def werkzeug_da(befehl: str) -> dict:
    pfad = shutil.which(befehl)
    if not pfad:
        return {"befehl": befehl, "da": False}
    version = ""
    for flagge in ("--version", "-version", "-v"):
        try:
            lauf = subprocess.run(
                [pfad, flagge],
                capture_output=True,
                text=True,
                timeout=20,
                encoding="utf-8",
                errors="replace",
            )
            roh = (lauf.stdout or lauf.stderr or "").strip().splitlines()
            if roh:
                version = roh[0].strip()[:120]
                break
        except Exception as fehler:
            leise(fehler, "services/plattform")
    return {"befehl": befehl, "da": True, "pfad": pfad, "version": version}
