from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.core.config import ROOT_DIR
from app.core.fehler import leise
from app.services import plattform
from app.services.dateiraum_service import bekannte_ordner

NAME = "Jon"

LINUX_VORLAGE = """[Desktop Entry]
Type=Application
Name=Jon
Comment=Jon - dein KI-Assistent
Exec={exec}
Icon={icon}
Terminal=false
Categories=Utility;
"""


def _exe() -> Path | None:
    if getattr(sys, "frozen", False):
        kandidaten = [
            ROOT_DIR / "Jon.exe",
            ROOT_DIR.parent / "Jon.exe",
            ROOT_DIR / "Jon",
            ROOT_DIR.parent / "Jon",
        ]
    else:
        kandidaten = [
            ROOT_DIR / "Jon.exe",
            ROOT_DIR / "frontend" / "release" / "win-unpacked" / "Jon.exe",
        ]
    for pfad in kandidaten:
        if pfad.is_file():
            return pfad.resolve()
    return None


def _symbol(ziel: Path) -> str:
    for kandidat in (
        ziel.parent / "resources" / "icon.ico",
        ziel.parent / "resources" / "app" / "icon.ico",
        ROOT_DIR / "frontend" / "build" / "icon.ico",
        ROOT_DIR / "frontend" / "public" / "icon.ico",
    ):
        if kandidat.is_file():
            return str(kandidat)
    return str(ziel)


def _windows(ziel: Path, ordner: Path) -> dict:
    verknuepfung = ordner / f"{NAME}.lnk"
    symbol = _symbol(ziel)
    skript = (
        "$w = New-Object -ComObject WScript.Shell; "
        f"$s = $w.CreateShortcut('{verknuepfung}'); "
        f"$s.TargetPath = '{ziel}'; "
        f"$s.WorkingDirectory = '{ziel.parent}'; "
        f"$s.IconLocation = '{symbol},0'; "
        "$s.Description = 'Jon - dein KI-Assistent'; "
        "$s.Save()"
    )
    lauf = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", skript],
        capture_output=True,
        timeout=60,
    )
    if lauf.returncode != 0 or not verknuepfung.exists():
        fehler = (lauf.stderr or b"").decode("utf-8", "replace")[:300]
        return {"error": f"Die Verknuepfung liess sich nicht anlegen. {fehler}".strip()}
    return {"ok": True, "pfad": str(verknuepfung)}


def _macos(ziel: Path, ordner: Path) -> dict:
    verknuepfung = ordner / NAME
    try:
        if verknuepfung.exists() or verknuepfung.is_symlink():
            verknuepfung.unlink()
        verknuepfung.symlink_to(ziel)
    except Exception as exc:
        return {"error": f"Die Verknuepfung liess sich nicht anlegen: {exc}"}
    return {"ok": True, "pfad": str(verknuepfung)}


def _linux(ziel: Path, ordner: Path) -> dict:
    verknuepfung = ordner / f"{NAME}.desktop"
    try:
        verknuepfung.write_text(
            LINUX_VORLAGE.format(exec=ziel, icon=_symbol(ziel)), encoding="utf-8"
        )
        verknuepfung.chmod(0o755)
    except Exception as exc:
        return {"error": f"Die Verknuepfung liess sich nicht anlegen: {exc}"}
    return {"ok": True, "pfad": str(verknuepfung)}


def schreibtisch() -> Path:
    ordner = bekannte_ordner().get("desktop")
    if ordner and ordner.is_dir():
        return ordner
    heim = Path.home() / "Desktop"
    heim.mkdir(parents=True, exist_ok=True)
    return heim


def vorhanden() -> str:
    ordner = schreibtisch()
    for name in (f"{NAME}.lnk", f"{NAME}.desktop"):
        pfad = ordner / name
        if pfad.is_file():
            return str(pfad)
    bar = ordner / NAME
    if bar.is_symlink():
        return str(bar)
    return ""


def anlegen(ziel: str = "") -> dict:
    programm = Path(ziel).expanduser() if ziel else _exe()
    if programm is None or not programm.is_file():
        return {
            "error": (
                "Ich finde die Jon-Programmdatei nicht. In der portablen Fassung liegt "
                "sie als Jon.exe im entpackten Jon-Ordner - gib den Pfad dorthin an."
            )
        }
    ordner = schreibtisch()
    system = plattform.name()
    if system == "windows":
        ergebnis = _windows(programm, ordner)
    elif system == "macos":
        ergebnis = _macos(programm, ordner)
    else:
        ergebnis = _linux(programm, ordner)
    if ergebnis.get("ok"):
        ergebnis["ziel"] = str(programm)
        ergebnis["ordner"] = str(ordner)
    return ergebnis


def entfernen() -> dict:
    pfad = vorhanden()
    if not pfad:
        return {"ok": True, "entfernt": False}
    try:
        Path(pfad).unlink()
    except Exception as exc:
        return {"error": f"Die Verknuepfung liess sich nicht entfernen: {exc}"}
    return {"ok": True, "entfernt": True, "pfad": pfad}


def stand() -> dict:
    programm = _exe()
    da = vorhanden()
    return {
        "plattform": plattform.name(),
        "programm": str(programm) if programm else "",
        "programm_gefunden": programm is not None,
        "verknuepfung": da,
        "vorhanden": bool(da),
        "schreibtisch": str(schreibtisch()),
        "portabel": bool(programm)
        and not any(
            teil.lower() in ("program files", "program files (x86)")
            for teil in (programm.parts if programm else ())
        ),
    }
