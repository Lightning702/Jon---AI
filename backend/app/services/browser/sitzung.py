from __future__ import annotations

import threading
import time
from contextvars import ContextVar

STANDARD = "standard"

_aktuelle: ContextVar[str] = ContextVar("jon_browser_sitzung", default=STANDARD)
_lock = threading.Lock()
_letzte = STANDARD
_beruehrt: dict[str, float] = {}


def setzen(kennung: str | None) -> str:
    schluessel = (str(kennung or "").strip() or STANDARD)[:40]
    _aktuelle.set(schluessel)
    return schluessel


def aktuell() -> str:
    schluessel = _aktuelle.get()
    with _lock:
        global _letzte
        _letzte = schluessel
        _beruehrt[schluessel] = time.time()
    return schluessel


def letzte() -> str:
    with _lock:
        return _letzte


def bekannte() -> list[str]:
    with _lock:
        return sorted(_beruehrt, key=lambda k: _beruehrt[k], reverse=True)


def alter(kennung: str) -> float:
    with _lock:
        stempel = _beruehrt.get(kennung, 0.0)
    return time.time() - stempel if stempel else 0.0


def vergessen(kennung: str) -> None:
    with _lock:
        _beruehrt.pop(kennung, None)
