from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
import time
import traceback
from collections import deque
from datetime import datetime, timezone

from app.core.config import DATA_DIR

LOG_FILE = DATA_DIR / "jon.log"
MAX_BYTES = 2_000_000
BACKUPS = 3
RING_SIZE = 400

_ring: deque[str] = deque(maxlen=RING_SIZE)
_ring_guard = threading.Lock()
_states: dict[str, dict] = {}
_states_guard = threading.Lock()
_ready = False


class _RingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:
            return
        with _ring_guard:
            _ring.append(line)


def setup_logging() -> None:
    global _ready
    if _ready:
        return
    _ready = True
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        pass
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    root.addHandler(stream)
    ring = _RingHandler()
    ring.setFormatter(fmt)
    root.addHandler(ring)
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    sys.excepthook = _hook


def _hook(kind, value, tb) -> None:
    logging.getLogger("jon").error(
        "Unbehandelter Fehler: %s", "".join(traceback.format_exception(kind, value, tb))
    )


def logger(name: str) -> logging.Logger:
    return logging.getLogger(f"jon.{name}")


def note_ok(name: str) -> None:
    with _states_guard:
        entry = _states.setdefault(name, {"ok": 0, "fehler": 0})
        entry["ok"] += 1
        entry["zuletzt_ok"] = _stamp()


def note_error(name: str, exc: BaseException) -> None:
    with _states_guard:
        entry = _states.setdefault(name, {"ok": 0, "fehler": 0})
        entry["fehler"] += 1
        entry["zuletzt_fehler"] = _stamp()
        entry["meldung"] = f"{type(exc).__name__}: {exc}"[:400]
    logger(name).warning("Hintergrunddienst %s: %s", name, exc, exc_info=True)


def _stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def snapshot() -> list[dict]:
    with _states_guard:
        return [
            {"dienst": name, **dict(entry)}
            for name, entry in sorted(_states.items())
        ]


def recent(limit: int = 200) -> list[str]:
    with _ring_guard:
        lines = list(_ring)
    return lines[-limit:]


def export_text() -> str:
    head = [
        f"Jon-Protokoll  {_stamp()}",
        f"Python {sys.version.split()[0]}  PID {os.getpid()}",
        f"Datei {LOG_FILE}",
        "",
        "Hintergrunddienste:",
    ]
    for entry in snapshot():
        head.append(
            f"  {entry['dienst']}: ok={entry.get('ok', 0)} "
            f"fehler={entry.get('fehler', 0)} {entry.get('meldung', '')}".rstrip()
        )
    head.append("")
    head.append("Letzte Meldungen:")
    body: list[str] = []
    if LOG_FILE.exists():
        try:
            body = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[
                -600:
            ]
        except OSError:
            body = []
    if not body:
        body = recent(600)
    return "\n".join(head + body) + "\n"


def watch(name: str):
    def wrap(exc: BaseException) -> None:
        note_error(name, exc)

    return wrap


def since_boot() -> float:
    return time.time() - _BOOT


_BOOT = time.time()
