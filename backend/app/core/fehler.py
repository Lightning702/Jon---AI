from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime

MAX_ZEILEN = 120

_log = logging.getLogger("jon.still")
_lock = threading.Lock()
_zeilen: deque[dict] = deque(maxlen=MAX_ZEILEN)
_zaehler: dict[str, int] = {}


def leise(exc: BaseException, kontext: str = "") -> None:
    stelle = kontext or "unbekannt"
    with _lock:
        _zaehler[stelle] = _zaehler.get(stelle, 0) + 1
        _zeilen.append(
            {
                "zeit": datetime.now().isoformat(timespec="seconds"),
                "stelle": stelle,
                "fehler": f"{type(exc).__name__}: {exc}"[:240],
            }
        )
    _log.debug("Stiller Fehler in %s: %s", stelle, exc, exc_info=False)


def bericht(limit: int = 30) -> dict:
    with _lock:
        haeufig = sorted(_zaehler.items(), key=lambda paar: paar[1], reverse=True)
        return {
            "gesamt": sum(_zaehler.values()),
            "stellen": haeufig[:limit],
            "letzte": list(_zeilen)[-limit:],
        }


def leeren() -> None:
    with _lock:
        _zeilen.clear()
        _zaehler.clear()
