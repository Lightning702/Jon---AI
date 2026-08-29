from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from app.core.config import DATA_DIR, ROOT_DIR, get_settings

RAW_CONFIG = (
    "https://raw.githubusercontent.com/Lightning702/Jon---AI/main/"
    "backend/app/core/config.py"
)
RELEASES_API = "https://api.github.com/repos/Lightning702/Jon---AI/releases/latest"
DOWNLOAD = "https://getjon.info"
INSTALLER_NAME = "Jon-Setup.exe"
CHECKSUM_NAME = "SHA256SUMS.txt"
UPDATE_DIR = DATA_DIR / "updates"
CACHE_TTL = 1800.0
ALLOWED_PREFIXES = ("https://",)

_cache: dict = {"at": 0.0, "data": None}


def _parse(version: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", version)[:3])


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_mode() -> str:
    if is_frozen():
        return "exe"
    return "git" if (ROOT_DIR / ".git").is_dir() else "manual"


def _fetch(url: str, timeout: float = 10.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Jon"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _release() -> dict:
    try:
        raw = json.loads(_fetch(RELEASES_API).decode("utf-8", errors="replace"))
    except Exception:
        return {}
    tag = str(raw.get("tag_name") or "").lstrip("vV")
    asset = None
    for entry in raw.get("assets") or []:
        if str(entry.get("name", "")).lower() == INSTALLER_NAME.lower():
            asset = entry
            break
    checksum = ""
    for entry in raw.get("assets") or []:
        if str(entry.get("name", "")).lower() == CHECKSUM_NAME.lower():
            checksum = str(entry.get("browser_download_url", ""))
            break
    if asset is None:
        return {"version": tag}
    return {
        "version": tag,
        "installer_url": asset.get("browser_download_url", ""),
        "installer_size": int(asset.get("size") or 0),
        "checksum_url": checksum,
        "notes": str(raw.get("body") or "")[:4000],
    }


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1_048_576), b""):
            sha.update(block)
    return sha.hexdigest()


def expected_digest(url: str, name: str = INSTALLER_NAME) -> str:
    if not url.startswith(ALLOWED_PREFIXES):
        return ""
    try:
        text = _fetch(url, 15.0).decode("utf-8", errors="replace")
    except Exception:
        return ""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*").lower() == name.lower():
            candidate = parts[0].strip().lower()
            if len(candidate) == 64 and all(c in "0123456789abcdef" for c in candidate):
                return candidate
    return ""


def check_update(force: bool = False) -> dict:
    settings = get_settings()
    current = settings.app_version
    now = time.monotonic()
    if not force and _cache["data"] and now - _cache["at"] < CACHE_TTL:
        return _cache["data"]

    mode = install_mode()
    result = {
        "current": current,
        "latest": current,
        "update": False,
        "url": DOWNLOAD,
        "mode": mode,
        "installer_url": "",
        "installer_size": 0,
        "checksum_url": "",
        "can_install": False,
    }
    published = ""
    try:
        text = _fetch(RAW_CONFIG, 8.0).decode("utf-8", errors="replace")
        match = re.search(r'app_version:\s*str\s*=\s*"([^"]+)"', text)
        if match:
            published = match.group(1)
            result["latest"] = published
    except Exception as exc:
        result["error"] = str(exc)

    if mode == "exe":
        release = _release()
        installer = release.get("installer_url", "")
        version = release.get("version", "")
        result["latest"] = version or published or current
        result["installer_url"] = installer
        result["installer_size"] = release.get("installer_size", 0)
        result["checksum_url"] = release.get("checksum_url", "")
        if release.get("notes"):
            result["notes"] = release["notes"]
        if published and version and _parse(published) > _parse(version):
            result["announced"] = published
        if not installer:
            result["latest"] = published or current

    result["update"] = _parse(result["latest"]) > _parse(current)
    result["can_install"] = bool(
        result["update"] and (mode == "git" or (mode == "exe" and result["installer_url"]))
    )
    _cache["at"] = now
    _cache["data"] = result
    return result


def installer_path(version: str) -> Path:
    safe = re.sub(r"[^0-9A-Za-z.\-]", "", version) or "neu"
    return UPDATE_DIR / f"Jon-Setup-{safe}.exe"


def download_installer(
    url: str,
    version: str,
    expected: int = 0,
    progress=None,
    checksum_url: str = "",
) -> Path:
    if not url.startswith(ALLOWED_PREFIXES):
        raise ValueError("Unerwartete Download-Adresse")
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    target = installer_path(version)
    partial = target.with_suffix(".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Jon"})
    done = 0
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get("Content-Length") or expected or 0)
        with partial.open("wb") as handle:
            while True:
                chunk = response.read(262_144)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total)
    if done < 1_000_000:
        partial.unlink(missing_ok=True)
        raise ValueError(f"Download unvollstaendig ({done} Bytes)")
    if expected and abs(done - expected) > 4096:
        partial.unlink(missing_ok=True)
        raise ValueError(f"Groesse passt nicht: {done} statt {expected} Bytes")
    with partial.open("rb") as handle:
        magic = handle.read(2)
    if magic != b"MZ":
        partial.unlink(missing_ok=True)
        raise ValueError("Datei ist kein Windows-Programm")
    wanted = expected_digest(checksum_url) if checksum_url else ""
    if wanted:
        got = _digest(partial)
        if got != wanted:
            partial.unlink(missing_ok=True)
            raise ValueError(
                "Pruefsumme stimmt nicht - die Datei wurde unterwegs veraendert "
                f"(erwartet {wanted[:12]}…, bekommen {got[:12]}…)"
            )
    target.unlink(missing_ok=True)
    partial.rename(target)
    for old in UPDATE_DIR.glob("Jon-Setup-*.exe"):
        if old != target:
            old.unlink(missing_ok=True)
    return target
