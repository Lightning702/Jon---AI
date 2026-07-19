from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timedelta

from app.core.config import DATA_DIR

USAGE_FILE = DATA_DIR / "app_usage.json"
IDLE_THRESHOLD = 90.0
KEEP_DAYS = 60

PRETTY = {
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "brave.exe": "Brave",
    "code.exe": "VS Code",
    "windowsterminal.exe": "Terminal",
    "cmd.exe": "Terminal",
    "powershell.exe": "PowerShell",
    "winword.exe": "Word",
    "excel.exe": "Excel",
    "powerpnt.exe": "PowerPoint",
    "outlook.exe": "Outlook",
    "onenote.exe": "OneNote",
    "explorer.exe": "Explorer",
    "spotify.exe": "Spotify",
    "discord.exe": "Discord",
    "slack.exe": "Slack",
    "teams.exe": "Teams",
    "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp",
    "steam.exe": "Steam",
    "obs64.exe": "OBS",
    "photoshop.exe": "Photoshop",
    "notepad.exe": "Notepad",
    "electron.exe": "Jon",
    "jon.exe": "Jon",
    "jon-backend.exe": "Jon",
}


def _active_process() -> str | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(4096)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            return os.path.basename(buffer.value)
    finally:
        kernel32.CloseHandle(handle)
    return None


def _pretty(process: str) -> str:
    key = process.lower()
    if key in PRETTY:
        return PRETTY[key]
    name = process.rsplit(".", 1)[0]
    return name[:1].upper() + name[1:] if name else process


class AppUsageService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        try:
            USAGE_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _prune(self) -> None:
        cutoff = (date.today() - timedelta(days=KEEP_DAYS)).isoformat()
        for day in [d for d in self._data if d < cutoff]:
            del self._data[day]

    def tick(self, seconds: float) -> None:
        from app.services.system_service import SystemService

        try:
            if SystemService().idle_seconds() > IDLE_THRESHOLD:
                return
        except Exception:
            pass
        process = _active_process()
        if not process:
            return
        app = _pretty(process)
        today = date.today().isoformat()
        with self._lock:
            day = self._data.setdefault(today, {})
            day[app] = round(day.get(app, 0.0) + seconds, 1)
            self._prune()
            self._save()

    def report(self, days: int = 7) -> dict:
        today = date.today()
        totals: dict[str, float] = {}
        per_day: dict[str, float] = {}
        with self._lock:
            for offset in range(days):
                day = (today - timedelta(days=offset)).isoformat()
                entries = self._data.get(day, {})
                day_total = 0.0
                for app, secs in entries.items():
                    totals[app] = totals.get(app, 0.0) + secs
                    day_total += secs
                per_day[day] = round(day_total / 60.0, 1)
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
        return {
            "zeitraum_tage": days,
            "gesamt_minuten": round(sum(totals.values()) / 60.0, 1),
            "apps": [
                {"app": app, "minuten": round(secs / 60.0, 1)}
                for app, secs in ranked[:10]
            ],
            "pro_tag": per_day,
        }


_service: AppUsageService | None = None


def get_appusage_service() -> AppUsageService:
    global _service
    if _service is None:
        _service = AppUsageService()
    return _service
