from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import DATA_DIR, ENV_FILE, ROOT_DIR

BESTAETIGUNG = "JON LOESCHEN"

_VERBOTEN = {
    Path(os.environ.get("SystemDrive", "C:") + "\\"),
    Path.home(),
    Path(os.environ.get("LOCALAPPDATA", "")) if os.environ.get("LOCALAPPDATA") else None,
    Path(os.environ.get("APPDATA", "")) if os.environ.get("APPDATA") else None,
    Path(os.environ.get("USERPROFILE", "")) if os.environ.get("USERPROFILE") else None,
}


def _sicher(pfad: Path) -> bool:
    try:
        ziel = pfad.resolve()
    except Exception:
        return False
    if not ziel.exists():
        return False
    if len(ziel.parts) <= 2:
        return False
    for tabu in _VERBOTEN:
        if tabu is None:
            continue
        try:
            if ziel == tabu.resolve():
                return False
        except Exception:
            continue
    return True


def _groesse(pfad: Path) -> tuple[int, int]:
    if not pfad.exists():
        return (0, 0)
    if pfad.is_file():
        return (1, pfad.stat().st_size)
    dateien = 0
    bytes_gesamt = 0
    for eintrag in pfad.rglob("*"):
        try:
            if eintrag.is_file():
                dateien += 1
                bytes_gesamt += eintrag.stat().st_size
        except OSError:
            continue
    return (dateien, bytes_gesamt)


def uninstaller_pfad() -> str:
    if not sys.platform.startswith("win"):
        return ""
    try:
        import winreg
    except ImportError:
        return ""
    wurzeln = (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    for hive, pfad in wurzeln:
        try:
            with winreg.OpenKey(hive, pfad) as schluessel:
                anzahl = winreg.QueryInfoKey(schluessel)[0]
                for index in range(anzahl):
                    name = winreg.EnumKey(schluessel, index)
                    try:
                        with winreg.OpenKey(schluessel, name) as eintrag:
                            anzeige = str(winreg.QueryValueEx(eintrag, "DisplayName")[0])
                            if not anzeige.lower().startswith("jon"):
                                continue
                            befehl = str(
                                winreg.QueryValueEx(eintrag, "UninstallString")[0]
                            )
                            return befehl
                    except OSError:
                        continue
        except OSError:
            continue
    return ""


def _ziele() -> list[dict[str, Any]]:
    eintraege: list[dict[str, Any]] = []

    dateien, bytes_gesamt = _groesse(DATA_DIR)
    eintraege.append(
        {
            "id": "daten",
            "titel": "Jons Daten",
            "beschreibung": "Unterhaltungen, Gedächtnis, Einstellungen, Wissensbasis, "
            "Tresor, Kalender, Freunde und Schlüssel",
            "pfad": str(DATA_DIR),
            "dateien": dateien,
            "bytes": bytes_gesamt,
            "vorhanden": DATA_DIR.exists(),
        }
    )

    if ENV_FILE.exists():
        eintraege.append(
            {
                "id": "env",
                "titel": "API-Schlüssel (.env)",
                "beschreibung": "Deine Zugangsdaten für die KI-Anbieter",
                "pfad": str(ENV_FILE),
                "dateien": 1,
                "bytes": ENV_FILE.stat().st_size,
                "vorhanden": True,
            }
        )

    return eintraege


def plan() -> dict[str, Any]:
    eintraege = _ziele()
    befehl = uninstaller_pfad()
    return {
        "bestaetigung": BESTAETIGUNG,
        "eintraege": eintraege,
        "bytes_gesamt": sum(int(e["bytes"]) for e in eintraege),
        "dateien_gesamt": sum(int(e["dateien"]) for e in eintraege),
        "programm_entfernbar": bool(befehl),
        "programm_hinweis": (
            "Danach startet der Windows-Deinstallierer und entfernt das Programm."
            if befehl
            else (
                "Jon läuft hier aus dem Quellordner. Der Ordner "
                + ROOT_DIR.name
                + " bleibt liegen und kann von Hand gelöscht werden."
            )
        ),
        "quellordner": str(ROOT_DIR),
        "autostart": True,
    }


def _loeschen(pfad: Path) -> tuple[bool, str]:
    if not pfad.exists():
        return (True, "war nicht vorhanden")
    if not _sicher(pfad):
        return (False, "aus Sicherheitsgründen abgelehnt")
    try:
        if pfad.is_file():
            pfad.unlink()
        else:
            shutil.rmtree(pfad, ignore_errors=False)
        return (True, "gelöscht")
    except Exception as exc:
        return (False, str(exc))


def ausfuehren(bestaetigung: str, programm_entfernen: bool) -> dict[str, Any]:
    if bestaetigung.strip().upper() != BESTAETIGUNG:
        raise ValueError(
            "Zum Löschen muss " + BESTAETIGUNG + " eingetippt werden."
        )

    schritte: list[dict[str, Any]] = []

    try:
        from app.services.system_service import SystemService

        SystemService().set_autostart(False)
        schritte.append({"schritt": "Autostart", "ok": True, "hinweis": "entfernt"})
    except Exception as exc:
        schritte.append({"schritt": "Autostart", "ok": False, "hinweis": str(exc)})

    try:
        from app.db.database import dispose_engine

        dispose_engine()
    except Exception:
        pass

    for eintrag in _ziele():
        pfad = Path(str(eintrag["pfad"]))
        ok, hinweis = _loeschen(pfad)
        schritte.append({"schritt": str(eintrag["titel"]), "ok": ok, "hinweis": hinweis})

    befehl = uninstaller_pfad() if programm_entfernen else ""
    gestartet = False
    if befehl:
        try:
            subprocess.Popen(
                befehl,
                shell=True,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
            )
            gestartet = True
            schritte.append(
                {"schritt": "Deinstallierer", "ok": True, "hinweis": "gestartet"}
            )
        except Exception as exc:
            schritte.append(
                {"schritt": "Deinstallierer", "ok": False, "hinweis": str(exc)}
            )

    return {
        "erledigt": True,
        "schritte": schritte,
        "deinstallierer_gestartet": gestartet,
        "beendet_sich": True,
    }
