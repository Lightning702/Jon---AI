from __future__ import annotations

import json
import threading

from app.core.config import DATA_DIR

SETTINGS_FILE = DATA_DIR / "user_settings.json"

DEFAULTS = {
    "custom_prompt": "",
    "prompt_mode": "append",
    "tool_mode": "ask",
    "personality": True,
    "provider": "",
    "model": "",
}


class SettingsService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        data = dict(DEFAULTS)
        if SETTINGS_FILE.exists():
            try:
                data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
            except Exception:
                pass
        return data

    def _save(self) -> None:
        try:
            SETTINGS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def get(self) -> dict:
        with self._lock:
            return dict(self._data)

    def update(self, values: dict) -> dict:
        with self._lock:
            for key in DEFAULTS:
                if key in values and values[key] is not None:
                    self._data[key] = values[key]
            self._save()
            return dict(self._data)

    def custom_prompt(self) -> tuple[str, str]:
        with self._lock:
            return self._data.get("custom_prompt", ""), self._data.get(
                "prompt_mode", "append"
            )

    def personality(self) -> bool:
        with self._lock:
            return bool(self._data.get("personality", True))

    def selection(self) -> tuple[str, str]:
        with self._lock:
            return self._data.get("provider", ""), self._data.get("model", "")


_service: SettingsService | None = None


def get_settings_service() -> SettingsService:
    global _service
    if _service is None:
        _service = SettingsService()
    return _service
