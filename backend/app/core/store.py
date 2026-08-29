from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

REPLACE_TRIES = 25
REPLACE_PAUSE = 0.02

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path)
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


def _temp_for(path: Path) -> Path:
    marke = f"{os.getpid()}.{threading.get_ident()}"
    return path.with_name(f"{path.name}.{marke}.tmp")


def _replace(temp: Path, path: Path) -> None:
    letzter: OSError | None = None
    for versuch in range(REPLACE_TRIES):
        try:
            os.replace(temp, path)
            return
        except PermissionError as exc:
            letzter = exc
            time.sleep(REPLACE_PAUSE * (1 + versuch // 5))
    raise letzter if letzter else OSError("Umbenennen fehlgeschlagen")


def _commit(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = _temp_for(path)
    with _lock_for(path):
        try:
            with temp.open("wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            _replace(temp, path)
        finally:
            if temp.exists():
                try:
                    temp.unlink()
                except OSError:
                    pass


def atomic_write_bytes(path: Path | str, data: bytes) -> None:
    _commit(Path(path), data)


def atomic_write_text(
    path: Path | str,
    data: str,
    encoding: str = "utf-8",
    errors: str | None = None,
    newline: str | None = None,
) -> None:
    if newline:
        data = data.replace("\n", newline)
    _commit(Path(path), data.encode(encoding, errors or "strict"))


def atomic_write_json(path: Path | str, data: Any, indent: int | None = 2) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=indent))


def read_json(path: Path | str, default: Any = None) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
