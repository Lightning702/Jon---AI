from __future__ import annotations

import socket
import threading
import time

from app.core.fehler import leise

PRUEFZIELE = (
    ("1.1.1.1", 53),
    ("8.8.8.8", 53),
    ("9.9.9.9", 53),
)
FRISCH_S = 20.0
FEHLER_FRISCH_S = 5.0
TIMEOUT_S = 1.2

_lock = threading.Lock()
_stand = {"online": True, "geprueft": 0.0, "grund": ""}


def _messen() -> bool:
    for host, port in PRUEFZIELE:
        try:
            with socket.create_connection((host, port), timeout=TIMEOUT_S):
                return True
        except Exception as _fehler:
            leise(_fehler, "services/netz_service")
    return False


def online(erzwingen: bool = False) -> bool:
    with _lock:
        alter = time.time() - float(_stand["geprueft"])
        frisch = FRISCH_S if _stand["online"] else FEHLER_FRISCH_S
        if not erzwingen and _stand["geprueft"] and alter < frisch:
            return bool(_stand["online"])
    ergebnis = _messen()
    with _lock:
        _stand["online"] = ergebnis
        _stand["geprueft"] = time.time()
        _stand["grund"] = "" if ergebnis else "Keine Verbindung zum Internet."
    return ergebnis


def stand() -> dict:
    with _lock:
        return dict(_stand)


def pruefen(was: str = "Diese Aktion") -> str:
    if online():
        return ""
    return (
        f"{was} braucht Internet, und gerade ist keine Verbindung da. "
        "Pruef dein WLAN oder Kabel - sobald du wieder online bist, klappt es sofort."
    )


def setzen(wert: bool) -> None:
    with _lock:
        _stand["online"] = bool(wert)
        _stand["geprueft"] = time.time()
