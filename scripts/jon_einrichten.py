from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

NAME = "Jon"
TITEL = "Jon einrichten"


def _ordner() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _sagen(text: str = "") -> None:
    try:
        print(text)
    except Exception:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")


def _fenstertitel() -> None:
    try:
        ctypes.windll.kernel32.SetConsoleTitleW(TITEL)
    except Exception:
        pass


def _warten(text: str = "Mit Enter schliessen ") -> None:
    try:
        input(f"\n  {text}")
    except (EOFError, KeyboardInterrupt):
        time.sleep(4)


def _bekannter_ordner(kennung: int, ersatz: Path) -> Path:
    try:
        puffer = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, kennung, None, 0, puffer) == 0:
            pfad = Path(puffer.value)
            if pfad.is_dir():
                return pfad
    except Exception:
        pass
    return ersatz


def schreibtisch() -> Path:
    return _bekannter_ordner(0, Path.home() / "Desktop")


def startmenue() -> Path:
    return _bekannter_ordner(
        2,
        Path(os.environ.get("APPDATA", Path.home()))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs",
    )


def verknuepfung(ziel: Path, exe: Path, symbol: Path, arbeitsordner: Path) -> str:
    skript = (
        "$ErrorActionPreference='Stop';"
        "$w = New-Object -ComObject WScript.Shell;"
        f"$s = $w.CreateShortcut('{ziel}');"
        f"$s.TargetPath = '{exe}';"
        f"$s.WorkingDirectory = '{arbeitsordner}';"
        f"$s.IconLocation = '{symbol},0';"
        "$s.Description = 'Jon - dein KI-Assistent';"
        "$s.Save()"
    )
    try:
        lauf = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", skript],
            capture_output=True,
            timeout=90,
        )
    except Exception as exc:
        return f"PowerShell liess sich nicht starten: {exc}"
    if not ziel.exists():
        meldung = (lauf.stderr or b"").decode("utf-8", "replace").strip()
        return meldung.splitlines()[0][:200] if meldung else "unbekannter Fehler"
    return ""


def starten(exe: Path, ordner: Path) -> str:
    try:
        subprocess.Popen([str(exe)], cwd=str(ordner))
    except Exception as exc:
        return str(exc)
    return ""


def main() -> int:
    _fenstertitel()
    hier = _ordner()
    exe = hier / "Jon.exe"

    _sagen()
    _sagen(f"  {TITEL}")
    _sagen("  " + "-" * len(TITEL))
    _sagen()

    if not exe.is_file():
        _sagen("  Jon.exe liegt nicht neben dieser Datei.")
        _sagen()
        _sagen("  Das passiert, wenn das ZIP noch nicht entpackt ist.")
        _sagen("  Entpacke den ganzen Jon-Ordner an einen festen Platz und")
        _sagen("  starte die Einrichtung dann aus diesem Ordner.")
        _sagen()
        _sagen(f"  Gesucht in: {hier}")
        _warten()
        return 1

    symbol = hier / "resources" / "icon.ico"
    if not symbol.is_file():
        symbol = exe

    fehler = []
    ziel = schreibtisch() / f"{NAME}.lnk"
    grund = verknuepfung(ziel, exe, symbol, hier)
    if grund:
        fehler.append(f"Desktop-Symbol: {grund}")
        _sagen(f"  Desktop-Symbol ging nicht: {grund}")
    else:
        _sagen(f"  Desktop-Symbol angelegt: {ziel}")

    menue = startmenue() / f"{NAME}.lnk"
    grund = verknuepfung(menue, exe, symbol, hier)
    if grund:
        _sagen(f"  Startmenue uebersprungen: {grund}")
    else:
        _sagen("  Startmenue-Eintrag angelegt")

    _sagen()
    if fehler:
        _sagen("  Jon laesst sich trotzdem starten: Doppelklick auf Jon.exe")
        _warten()
        return 1

    _sagen("  Fertig. Jon startet jetzt.")
    _sagen("  Der erste Start dauert einen Moment, bis alles oben ist.")
    _sagen()
    grund = starten(exe, hier)
    if grund:
        _sagen(f"  Jon liess sich nicht starten: {grund}")
        _warten()
        return 1
    time.sleep(3)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        _sagen(f"\n  Unerwarteter Fehler: {exc}")
        _warten()
        sys.exit(1)
