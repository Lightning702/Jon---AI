from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from . import netz

QUELLE = "https://github.com/Lightning702/Jon---AI/releases/latest/download"
INSTALLER_WINDOWS = "https://raw.githubusercontent.com/Lightning702/Jon---AI/main/website/install.ps1"
INSTALLER_UNIX = "https://raw.githubusercontent.com/Lightning702/Jon---AI/main/website/install.sh"


class UpdateFehler(Exception):
    pass


def eigene_datei() -> tuple[Path, str] | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve(), "jon-harness.exe"
    start = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    if start is not None and start.suffix == ".pyz" and start.is_file():
        return start, "jon-harness.pyz"
    return None


def pruefsumme(name: str, liste: str | None = None) -> str:
    text = liste if liste is not None else netz.anfrage("GET", f"{QUELLE}/SHA256SUMS.txt", zeit=30).text()
    for zeile in text.splitlines():
        teile = zeile.split()
        if len(teile) >= 2 and teile[-1].lstrip("*") == name:
            return teile[0].lower()
    raise UpdateFehler(f"Für {name} steht keine Prüfsumme im Release.")


def aktualisieren(ziel: tuple[Path, str] | None = None) -> Path:
    ziel = ziel or eigene_datei()
    if ziel is None:
        raise UpdateFehler("Dieser Harness läuft aus dem Quellcode – dort aktualisierst du mit git pull.")
    pfad, name = ziel
    erwartet = pruefsumme(name)
    daten = netz.anfrage("GET", f"{QUELLE}/{name}", zeit=300).inhalt()
    if hashlib.sha256(daten).hexdigest() != erwartet:
        raise UpdateFehler("Die Prüfsumme der neuen Version stimmt nicht – ich habe nichts verändert.")
    if name.endswith(".exe") and (len(daten) < 1_000_000 or daten[:2] != b"MZ"):
        raise UpdateFehler("Die heruntergeladene Datei ist kein gültiges Programm – ich habe nichts verändert.")
    neu = pfad.with_name(pfad.name + ".neu")
    alt = pfad.with_name(pfad.name + ".alt")
    neu.write_bytes(daten)
    try:
        if alt.exists():
            alt.unlink()
        if name.endswith(".exe"):
            os.replace(pfad, alt)
        os.replace(neu, pfad)
    except OSError as fehler:
        if alt.exists() and not pfad.exists():
            os.replace(alt, pfad)
        neu.unlink(missing_ok=True)
        raise UpdateFehler(f"Die neue Version ließ sich nicht einsetzen: {fehler}") from fehler
    return pfad


def aufraeumen() -> None:
    ziel = eigene_datei()
    if ziel is None:
        return
    for endung in (".alt", ".neu"):
        try:
            ziel[0].with_name(ziel[0].name + endung).unlink(missing_ok=True)
        except OSError:
            pass
