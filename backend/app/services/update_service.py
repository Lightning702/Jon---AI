from __future__ import annotations

import re
import time
import urllib.request

from app.core.config import get_settings

RAW_CONFIG = (
    "https://raw.githubusercontent.com/Lightning702/Jon---AI/main/"
    "backend/app/core/config.py"
)
DOWNLOAD = "https://getjon.netlify.app"
CACHE_TTL = 1800.0

_cache: dict = {"at": 0.0, "data": None}


def _parse(version: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", version)[:3])


def check_update() -> dict:
    settings = get_settings()
    current = settings.app_version
    now = time.monotonic()
    if _cache["data"] and now - _cache["at"] < CACHE_TTL:
        return _cache["data"]
    result = {"current": current, "latest": current, "update": False, "url": DOWNLOAD}
    try:
        request = urllib.request.Request(RAW_CONFIG, headers={"User-Agent": "Jon"})
        with urllib.request.urlopen(request, timeout=8) as response:
            text = response.read().decode("utf-8", errors="replace")
        match = re.search(r'app_version:\s*str\s*=\s*"([^"]+)"', text)
        if match:
            latest = match.group(1)
            result["latest"] = latest
            result["update"] = _parse(latest) > _parse(current)
    except Exception as exc:
        result["error"] = str(exc)
    _cache["at"] = now
    _cache["data"] = result
    return result
