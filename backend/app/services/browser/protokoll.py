from __future__ import annotations

import logging
import re
import threading
from collections import deque
from datetime import datetime

MAX_ZEILEN = 200

_zeilen: deque[dict] = deque(maxlen=MAX_ZEILEN)
_guard = threading.Lock()
_logger = logging.getLogger("jon.browser")

_MUSTER: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?i)\b(passwor[dt]|kennwort|secret|token|api[_-]?key|"
            r"authorization|cookie|session[_-]?id|csrf|cvv|cvc)\b"
            r"\s*[:=]\s*\S+"
        ),
        r"\1=***",
    ),
    (re.compile(r"\bey[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"), "***"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "***"),
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,28}\b"), "***"),
]


def redigieren(text: str) -> str:
    sauber = str(text)
    for muster, ersatz in _MUSTER:
        sauber = muster.sub(ersatz, sauber)
    return sauber


def notieren(aktion: str, detail: str = "") -> None:
    eintrag = {
        "zeit": datetime.now().isoformat(timespec="seconds"),
        "aktion": redigieren(aktion)[:80],
        "detail": redigieren(detail)[:240],
    }
    with _guard:
        _zeilen.append(eintrag)
    _logger.info("Browser Agent: %s %s", eintrag["aktion"], eintrag["detail"])


def verlauf(limit: int = 40) -> list[dict]:
    with _guard:
        return list(_zeilen)[-max(1, limit) :]


def leeren() -> None:
    with _guard:
        _zeilen.clear()
