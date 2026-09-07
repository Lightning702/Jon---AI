from __future__ import annotations

import threading

from app.services.semantik import get_index

TOP_K = 10
SCHWELLE = 0.16
GRUPPEN_SCHWELLE = 0.2

_gebaut = False
_lock = threading.Lock()
_gruppe_von: dict[str, str] = {}
_gruppen_namen: dict[str, set[str]] = {}


def _texte() -> dict[str, str]:
    from app.services.tools import TOOL_GROUPS, ToolBox, _gruppe_fuer

    box = ToolBox()
    daten: dict[str, str] = {}
    _gruppe_von.clear()
    _gruppen_namen.clear()
    for gruppe, (namen, woerter) in TOOL_GROUPS.items():
        _gruppen_namen[gruppe] = set(namen)
        for name in namen:
            _gruppe_von[name] = gruppe
    for eintrag in box._all_tools():
        funktion = eintrag.get("function", {})
        name = str(funktion.get("name", ""))
        if not name:
            continue
        beschreibung = str(funktion.get("description", ""))
        felder = " ".join(
            (funktion.get("parameters", {}) or {}).get("properties", {}).keys()
        )
        gruppe = _gruppe_von.get(name) or _gruppe_fuer(name)
        stichworte = ""
        for schluessel, (namen, woerter) in TOOL_GROUPS.items():
            if name in namen:
                stichworte = " ".join(woerter)
                break
        daten[name] = f"{name} {beschreibung} {felder} {gruppe} {stichworte}"
    return daten


def aufbauen(erzwingen: bool = False) -> None:
    global _gebaut
    with _lock:
        if _gebaut and not erzwingen:
            return
        index = get_index("werkzeuge")
        if erzwingen:
            index.leeren()
        for name, text in _texte().items():
            index.setzen(name, text)
        _gebaut = True


def passende_werkzeuge(text: str, top_k: int = TOP_K) -> set[str]:
    frage = str(text or "").strip()
    if len(frage) < 3:
        return set()
    try:
        aufbauen()
    except Exception:
        return set()
    treffer = get_index("werkzeuge").suchen(frage, top_k=top_k, schwelle=SCHWELLE)
    namen: set[str] = set()
    for name, wert in treffer:
        namen.add(name)
        gruppe = _gruppe_von.get(name)
        if gruppe and wert >= GRUPPEN_SCHWELLE:
            namen |= _gruppen_namen.get(gruppe, set())
    return namen
