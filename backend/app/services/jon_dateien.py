from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_json

FRIST = 12 * 3600
GRENZE = 300
ZUSATZ = re.compile(
    r"(?:[\s_-]+(?:v\d{1,3}|version[\s_-]*\d{1,3}|final|finale|endversion|neu|new|kopie|copy|"
    r"(?:ue|ü)berarbeitet|korrigiert|verbessert|aktualisiert|updated?)|\s*\(\d{1,3}\))+$",
    re.IGNORECASE,
)

_sperre = threading.Lock()


def _datei() -> Path:
    return DATA_DIR / "jon_dateien.json"


def grundname(name: str) -> str:
    stamm = Path(str(name or "")).stem.strip()
    rest = stamm
    while True:
        neu = ZUSATZ.sub("", rest).strip(" _-")
        if not neu or neu == rest:
            break
        rest = neu
    return (rest or stamm).casefold()


def _laden() -> list[dict]:
    try:
        daten = json.loads(_datei().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception as fehler:
        leise(fehler, "services/jon_dateien")
        return []
    return [e for e in daten if isinstance(e, dict) and e.get("pfad")] if isinstance(daten, list) else []


def _speichern(eintraege: list[dict]) -> None:
    try:
        atomic_write_json(_datei(), eintraege[-GRENZE:])
    except Exception as fehler:
        leise(fehler, "services/jon_dateien")


def _schluessel(pfad: Path) -> str:
    try:
        return str(pfad.resolve()).casefold()
    except OSError:
        return str(pfad).casefold()


def _stand(pfad: Path) -> tuple[float, int] | None:
    try:
        info = pfad.stat()
    except OSError:
        return None
    return info.st_mtime, info.st_size


def merken(pfad: str | Path, angefragt: str = "") -> None:
    ziel = Path(pfad)
    stand = _stand(ziel)
    if stand is None:
        return
    schluessel = _schluessel(ziel)
    with _sperre:
        eintraege = [e for e in _laden() if e.get("schluessel") != schluessel]
        eintraege.append({
            "pfad": str(ziel),
            "schluessel": schluessel,
            "ordner": _schluessel(ziel.parent),
            "endung": ziel.suffix.lower(),
            "grund": grundname(angefragt or ziel.name),
            "zeit": time.time(),
            "mtime": stand[0],
            "groesse": stand[1],
        })
        _speichern(eintraege)


def aktualisieren(pfad: str | Path) -> None:
    ziel = Path(pfad)
    stand = _stand(ziel)
    if stand is None:
        return
    schluessel = _schluessel(ziel)
    with _sperre:
        eintraege = _laden()
        for eintrag in eintraege:
            if eintrag.get("schluessel") == schluessel:
                eintrag.update(zeit=time.time(), mtime=stand[0], groesse=stand[1])
                _speichern(eintraege)
                return


def von_jon(pfad: str | Path) -> bool:
    ziel = Path(pfad)
    stand = _stand(ziel)
    if stand is None:
        return False
    schluessel = _schluessel(ziel)
    with _sperre:
        for eintrag in _laden():
            if eintrag.get("schluessel") == schluessel:
                return abs(float(eintrag.get("mtime", 0)) - stand[0]) < 2 and int(eintrag.get("groesse", -1)) == stand[1]
    return False


def wiederverwenden(ordner: str | Path, name: str) -> Path | None:
    grund = grundname(name)
    endung = Path(str(name or "")).suffix.lower()
    if not grund or not endung:
        return None
    ort = _schluessel(Path(ordner))
    jetzt = time.time()
    with _sperre:
        eintraege = _laden()
    for eintrag in reversed(eintraege):
        if eintrag.get("ordner") != ort or eintrag.get("endung") != endung or eintrag.get("grund") != grund:
            continue
        if jetzt - float(eintrag.get("zeit", 0)) > FRIST:
            continue
        pfad = Path(str(eintrag["pfad"]))
        stand = _stand(pfad)
        if stand is None:
            continue
        if abs(float(eintrag.get("mtime", 0)) - stand[0]) >= 2 or int(eintrag.get("groesse", -1)) != stand[1]:
            continue
        return pfad
    return None
