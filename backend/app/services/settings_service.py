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
    "auto_failover": True,
    "provider": "",
    "model": "",
    "theme": "dark",
    "pet_accent": "#d4af37",
    "pet_face": "#0a0a0e",
    "pet_cheeks": False,
    "pet_scale": 1.0,
    "pet_eyes": "round",
    "dream_auto": True,
    "dream_idle_minutes": 5,
    "vision_model": "",
    "briefing_city": "",
    "clipboard_history": True,
    "webcam_enabled": False,
    "mail_imap_host": "",
    "mail_imap_user": "",
    "mail_imap_password": "",
    "mail_smtp_host": "",
    "mail_smtp_port": 587,
    "calendar_ics_url": "",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "telegram_provider": "",
    "telegram_model": "",
    "mini_jon_bot_token": "",
    "pet_provider": "",
    "pet_model": "",
    "ha_url": "",
    "ha_token": "",
    "natural_voice": True,
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "p2p_user_id": "",
    "p2p_username": "",
    "p2p_avatar": "🙂",
    "p2p_enabled": True,
    "relay_enabled": False,
    "relay_broker": "broker.hivemq.com",
    "relay_port": 1883,
    "cowork_enabled": False,
    "cowork_context": "",
    "cowork_app": "auto",
    "quickwrite_enabled": True,
    "timeline_enabled": False,
    "routine_enabled": True,
    "telegram_morning": False,
    "telegram_morning_time": "07:30",
    "pet_roam": False,
    "pet_companion": "none",
    "wake_sensitivity": "mittel",
    "pet_wellness": True,
    "autofile_enabled": False,
    "app_usage_enabled": False,
    "language": "de",
    "netlify_token": "",
    "netlify_site_id": "",
    "netlify_site_name": "",
    "netlify_site_url": "",
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

    def _companion_selection(
        self, provider_key: str, model_key: str
    ) -> tuple[str, str]:
        main_provider = self._data.get("provider", "")
        main_model = self._data.get("model", "")
        if main_provider and main_provider != "nvidia":
            return main_provider, main_model
        provider = self._data.get(provider_key, "") or main_provider
        return provider, self._data.get(model_key, "")

    def pet_selection(self) -> tuple[str, str]:
        with self._lock:
            return self._companion_selection("pet_provider", "pet_model")

    def telegram_selection(self) -> tuple[str, str]:
        with self._lock:
            return self._companion_selection("telegram_provider", "telegram_model")


_service: SettingsService | None = None


def get_settings_service() -> SettingsService:
    global _service
    if _service is None:
        _service = SettingsService()
    return _service
