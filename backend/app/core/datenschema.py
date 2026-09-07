from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_text

SCHEMA_DATEI = DATA_DIR / "schema_stand.json"
SICHERUNG = DATA_DIR / "schema_sicherungen"

_lock = threading.Lock()
_stand: dict[str, int] | None = None

Wandler = Callable[[Any], Any]


def _stand_laden() -> dict[str, int]:
    global _stand
    if _stand is not None:
        return _stand
    daten: dict[str, int] = {}
    if SCHEMA_DATEI.exists():
        try:
            roh = json.loads(SCHEMA_DATEI.read_text(encoding="utf-8"))
            if isinstance(roh, dict):
                daten = {str(k): int(v) for k, v in roh.items()}
        except Exception as _fehler:
            leise(_fehler, "core/datenschema")
            daten = {}
    _stand = daten
    return _stand


def _stand_sichern() -> None:
    if _stand is None:
        return
    try:
        atomic_write_text(
            SCHEMA_DATEI,
            json.dumps(_stand, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as _fehler:
        leise(_fehler, "core/datenschema")


def version(name: str) -> int:
    with _lock:
        return int(_stand_laden().get(name, 0))


def setzen(name: str, nummer: int) -> None:
    with _lock:
        _stand_laden()[name] = int(nummer)
        _stand_sichern()


def sichern(datei: Path) -> Path | None:
    if not datei.exists():
        return None
    try:
        SICHERUNG.mkdir(parents=True, exist_ok=True)
        stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
        ziel = SICHERUNG / f"{datei.stem}-{stempel}{datei.suffix}"
        shutil.copy2(datei, ziel)
        return ziel
    except Exception as _fehler:
        leise(_fehler, "core/datenschema")
        return None


def wandeln(
    datei: Path,
    name: str,
    wandler: dict[int, Wandler],
    standard: Any = None,
) -> Any:
    ziel_version = max(wandler) if wandler else 0
    jetzige = version(name)
    if not datei.exists():
        if jetzige != ziel_version:
            setzen(name, ziel_version)
        return standard
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except Exception as _fehler:
        leise(_fehler, "core/datenschema")
        return standard
    if jetzige >= ziel_version:
        return daten
    sichern(datei)
    for schritt in sorted(wandler):
        if schritt <= jetzige:
            continue
        try:
            daten = wandler[schritt](daten)
        except Exception as _fehler:
            leise(_fehler, f"core/datenschema:{name}:{schritt}")
            return daten
    try:
        atomic_write_text(
            datei, json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as _fehler:
        leise(_fehler, "core/datenschema")
    setzen(name, ziel_version)
    return daten


def pruefen(daten: Any, felder: dict[str, Any]) -> dict:
    if not isinstance(daten, dict):
        return dict(felder)
    ergebnis = dict(felder)
    for schluessel, wert in daten.items():
        if schluessel in felder and wert is not None:
            vorlage = felder[schluessel]
            if vorlage is None or isinstance(wert, type(vorlage)):
                ergebnis[schluessel] = wert
        elif schluessel not in felder:
            ergebnis[schluessel] = wert
    return ergebnis
