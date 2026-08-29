from __future__ import annotations

import os
import secrets
import socket
import threading

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text

TOKEN_FILE = DATA_DIR / "access.token"
HEADER_NAME = "X-Jon-Token"
COOKIE_NAME = "jon_token"
QUERY_NAME = "token"

OPEN_PREFIXES = ("/api/health", "/api/mp/", "/api/auth/ping")

_lock = threading.Lock()
_cached: str | None = None


def _generate() -> str:
    return secrets.token_urlsafe(32)


def _restrict(path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def get_token() -> str:
    global _cached
    with _lock:
        if _cached:
            return _cached
        from_env = os.environ.get("JON_TOKEN", "").strip()
        if not from_env:
            from app.core.config import get_settings

            from_env = get_settings().jon_token.strip()
        if from_env:
            _cached = from_env
            return _cached
        if TOKEN_FILE.exists():
            try:
                stored = TOKEN_FILE.read_text(encoding="utf-8").strip()
            except OSError:
                stored = ""
            if stored:
                _cached = stored
                return _cached
        created = _generate()
        atomic_write_text(TOKEN_FILE, created + "\n")
        _restrict(TOKEN_FILE)
        _cached = created
        return _cached


def reset_token() -> str:
    global _cached
    with _lock:
        _cached = None
    os.environ.pop("JON_TOKEN", None)
    fresh = _generate()
    atomic_write_text(TOKEN_FILE, fresh + "\n")
    _restrict(TOKEN_FILE)
    with _lock:
        _cached = fresh
    return fresh


def token_matches(candidate: str | None) -> bool:
    if not candidate:
        return False
    return secrets.compare_digest(candidate.strip(), get_token())


def _presented(request: Request) -> str | None:
    header = request.headers.get(HEADER_NAME)
    if header:
        return header
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    query = request.query_params.get(QUERY_NAME)
    if query:
        return query
    return request.cookies.get(COOKIE_NAME)


def is_open_path(path: str) -> bool:
    if not path.startswith("/api"):
        return True
    return path.startswith(OPEN_PREFIXES)


class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or is_open_path(request.url.path):
            return await call_next(request)
        if token_matches(_presented(request)):
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={
                "detail": (
                    "Kein gültiger Jon-Zugang. Diese Anfrage braucht den "
                    "Geräte-Schlüssel aus Einstellungen → Diagnose."
                )
            },
        )


def lan_address() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return str(probe.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def pair_url(port: int, lan: bool) -> str:
    host = lan_address() if lan else "127.0.0.1"
    return f"http://{host}:{port}/app/?{QUERY_NAME}={get_token()}"
