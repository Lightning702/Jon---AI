from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.core.fehler import leise
from app.core.store import atomic_write_text

MARKE = "# Jon Terminal"
PROFILZEILE = 'export PATH="$HOME/.local/bin:$PATH"'


def _windows() -> bool:
    return os.name == "nt"


def bin_ordner() -> Path:
    if _windows():
        wurzel = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(wurzel) / "Jon" / "bin"
    return Path.home() / ".local" / "bin"


def befehl_pfad() -> Path:
    return bin_ordner() / ("jon.cmd" if _windows() else "jon")


def _gebuendelt() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    kandidat = Path(sys.executable)
    return kandidat if kandidat.exists() else None


def _backend_wurzel() -> Path:
    return Path(__file__).resolve().parents[2]


def starter() -> tuple[str, str]:
    exe = _gebuendelt()
    if exe is not None:
        return str(exe), "cli"
    python = sys.executable or shutil.which("python") or "python"
    return python, str(_backend_wurzel())


def _inhalt() -> str:
    ziel, zusatz = starter()
    if _gebuendelt() is not None:
        if _windows():
            return f'@echo off\r\n"{ziel}" cli %*\r\n'
        return f'#!/bin/sh\nexec "{ziel}" cli "$@"\n'
    if _windows():
        return (
            "@echo off\r\n"
            "setlocal\r\n"
            f'set "PYTHONPATH={zusatz};%PYTHONPATH%"\r\n'
            "set PYTHONIOENCODING=utf-8\r\n"
            f'"{ziel}" -m app.cli %*\r\n'
        )
    return (
        "#!/bin/sh\n"
        f'PYTHONPATH="{zusatz}:$PYTHONPATH"\n'
        "PYTHONIOENCODING=utf-8\n"
        "export PYTHONPATH PYTHONIOENCODING\n"
        f'exec "{ziel}" -m app.cli "$@"\n'
    )


def _pfad_eintraege() -> list[str]:
    return [e for e in (os.environ.get("PATH") or "").split(os.pathsep) if e]


def im_pfad(ordner: Path) -> bool:
    ziel = str(ordner).rstrip("\\/").lower()
    return any(e.rstrip("\\/").lower() == ziel for e in _pfad_eintraege())


def _nutzerpfad_windows() -> str:
    befehl = "[Environment]::GetEnvironmentVariable('Path','User')"
    ergebnis = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", befehl],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return (ergebnis.stdout or "").strip()


def _pfad_setzen_windows(wert: str) -> bool:
    sicher = wert.replace("'", "''")
    befehl = (
        f"[Environment]::SetEnvironmentVariable('Path','{sicher}','User')"
    )
    ergebnis = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", befehl],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return ergebnis.returncode == 0


def _profile() -> list[Path]:
    heim = Path.home()
    return [heim / ".profile", heim / ".bashrc", heim / ".zshrc"]


def _profil_ergaenzen(ordner: Path) -> list[str]:
    geaendert = []
    for datei in _profile():
        try:
            text = datei.read_text(encoding="utf-8") if datei.exists() else ""
        except OSError:
            continue
        if MARKE in text or str(ordner) in text:
            continue
        neu = text.rstrip("\n") + f"\n\n{MARKE}\n{PROFILZEILE}\n"
        try:
            atomic_write_text(datei, neu.lstrip("\n"))
            geaendert.append(str(datei))
        except OSError as fehler:
            leise(fehler, "services/terminal")
    return geaendert


def _profil_saeubern() -> None:
    for datei in _profile():
        if not datei.exists():
            continue
        try:
            zeilen = datei.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        sauber = []
        i = 0
        while i < len(zeilen):
            if zeilen[i].strip() == MARKE:
                i += 1
                while i < len(zeilen) and zeilen[i].strip() == PROFILZEILE:
                    i += 1
                continue
            sauber.append(zeilen[i])
            i += 1
        try:
            atomic_write_text(datei, "\n".join(sauber).rstrip("\n") + "\n")
        except OSError as fehler:
            leise(fehler, "services/terminal")


def stand() -> dict:
    pfad = befehl_pfad()
    ordner = bin_ordner()
    gefunden = shutil.which("jon") or ""
    return {
        "installiert": pfad.exists(),
        "befehl": str(pfad),
        "ordner": str(ordner),
        "im_pfad": im_pfad(ordner),
        "gefunden": gefunden,
        "gebuendelt": _gebuendelt() is not None,
        "system": "windows" if _windows() else sys.platform,
        "neustart_noetig": pfad.exists() and not gefunden,
    }


def einrichten() -> dict:
    ordner = bin_ordner()
    pfad = befehl_pfad()
    try:
        ordner.mkdir(parents=True, exist_ok=True)
        atomic_write_text(pfad, _inhalt())
    except OSError as fehler:
        leise(fehler, "services/terminal")
        return {"error": f"Der Befehl liess sich nicht anlegen: {fehler}"}
    hinweise: list[str] = []
    if not _windows():
        try:
            pfad.chmod(0o755)
        except OSError as fehler:
            leise(fehler, "services/terminal")
    if not im_pfad(ordner):
        if _windows():
            alt = _nutzerpfad_windows()
            teile = [e for e in alt.split(os.pathsep) if e.strip()]
            if not any(e.rstrip("\\/").lower() == str(ordner).lower() for e in teile):
                teile.append(str(ordner))
                if _pfad_setzen_windows(os.pathsep.join(teile)):
                    hinweise.append("Zum PATH hinzugefuegt.")
                else:
                    hinweise.append(
                        "Der PATH liess sich nicht aendern - trag "
                        f"{ordner} von Hand ein."
                    )
        else:
            geaendert = _profil_ergaenzen(ordner)
            if geaendert:
                hinweise.append("In " + ", ".join(geaendert) + " eingetragen.")
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(ordner)
    ergebnis = stand()
    ergebnis["hinweise"] = hinweise
    ergebnis["installiert"] = True
    return ergebnis


def _gleich(einer: str, anderer: str) -> bool:
    zeichen = chr(13) + chr(10)
    return einer.replace(zeichen, chr(10)) == anderer.replace(zeichen, chr(10))


def automatisch() -> dict:
    if _gebuendelt() is None:
        return {"gemacht": False, "grund": "nur in der fertigen App"}
    if os.environ.get("JON_KEIN_TERMINAL_BEFEHL"):
        return {"gemacht": False, "grund": "abgeschaltet"}
    pfad = befehl_pfad()
    soll = _inhalt()
    try:
        if pfad.exists() and _gleich(pfad.read_text(encoding="utf-8"), soll):
            return {"gemacht": False, "grund": "schon eingerichtet"}
    except OSError as fehler:
        leise(fehler, "services/terminal")
    ergebnis = einrichten()
    ergebnis["gemacht"] = "error" not in ergebnis
    return ergebnis


def entfernen() -> dict:
    pfad = befehl_pfad()
    try:
        pfad.unlink(missing_ok=True)
    except OSError as fehler:
        leise(fehler, "services/terminal")
        return {"error": f"Der Befehl liess sich nicht entfernen: {fehler}"}
    ordner = bin_ordner()
    if _windows():
        alt = _nutzerpfad_windows()
        teile = [
            e
            for e in alt.split(os.pathsep)
            if e.strip() and e.rstrip("\\/").lower() != str(ordner).lower()
        ]
        _pfad_setzen_windows(os.pathsep.join(teile))
    else:
        _profil_saeubern()
    return stand()
