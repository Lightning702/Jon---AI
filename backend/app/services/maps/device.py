from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time

_SCRIPT = (
    "Add-Type -AssemblyName System.Device;"
    "$acc = [System.Device.Location.GeoPositionAccuracy]::High;"
    "$w = New-Object System.Device.Location.GeoCoordinateWatcher($acc);"
    "$w.MovementThreshold = 0;"
    "$w.Start();"
    "$n = 0;"
    "while (($w.Status -ne 'Ready') -and ($n -lt 60)) "
    "{ Start-Sleep -Milliseconds 200; $n++ };"
    "$best = $null;"
    "for ($i = 0; $i -lt 8; $i++) {"
    "  $p = $w.Position.Location;"
    "  if (-not $p.IsUnknown) {"
    "    if (($best -eq $null) -or ($p.HorizontalAccuracy -lt $best.HorizontalAccuracy))"
    "      { $best = $p }"
    "  };"
    "  if (($best -ne $null) -and ($best.HorizontalAccuracy -le 25)) { break };"
    "  Start-Sleep -Milliseconds 300"
    "};"
    "if ($best -eq $null) { Write-Output 'null' } else "
    "{ Write-Output (ConvertTo-Json @{ lat = $best.Latitude; lon = $best.Longitude; "
    "acc = $best.HorizontalAccuracy } -Compress) };"
    "$w.Stop()"
)

_CACHE_SECONDS = 120.0
_cache: tuple[float, dict | None] = (0.0, None)
_lock = asyncio.Lock()


def _run() -> dict | None:
    if not sys.platform.startswith("win"):
        return None
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return None
    raw = (completed.stdout or "").strip()
    if not raw or raw == "null":
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if lat == 0.0 and lon == 0.0:
        return None
    accuracy = data.get("acc")
    return {
        "lat": lat,
        "lon": lon,
        "genauigkeit_m": float(accuracy) if accuracy is not None else None,
    }


async def locate(force: bool = False) -> dict | None:
    global _cache
    now = time.monotonic()
    stamp, value = _cache
    if not force and value is not None and now - stamp < _CACHE_SECONDS:
        return value
    async with _lock:
        stamp, value = _cache
        now = time.monotonic()
        if not force and value is not None and now - stamp < _CACHE_SECONDS:
            return value
        found = await asyncio.to_thread(_run)
        if found is not None:
            _cache = (time.monotonic(), found)
        return found


def available() -> bool:
    return sys.platform.startswith("win")
