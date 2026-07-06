from __future__ import annotations

import json
import threading

from app.core.config import DATA_DIR

ACCOUNTS_FILE = DATA_DIR / "accounts.json"

SUPPORTED = {
    "openai": {
        "label": "OpenAI",
        "env_var": "OPENAI_API_KEY",
        "auth": "api_key",
        "docs": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "env_var": "ANTHROPIC_API_KEY",
        "auth": "api_key",
        "docs": "https://console.anthropic.com/settings/keys",
    },
    "nvidia": {
        "label": "NVIDIA NIM",
        "env_var": "NVIDIA_API_KEY",
        "auth": "api_key",
        "docs": "https://build.nvidia.com",
    },
    "gemini": {
        "label": "Google Gemini",
        "env_var": "GOOGLE_API_KEY",
        "auth": "api_key",
        "docs": "https://aistudio.google.com/apikey",
    },
    "deepseek": {
        "label": "DeepSeek",
        "env_var": "DEEPSEEK_API_KEY",
        "auth": "api_key",
        "docs": "https://platform.deepseek.com",
    },
    "mistral": {
        "label": "Mistral",
        "env_var": "MISTRAL_API_KEY",
        "auth": "api_key",
        "docs": "https://console.mistral.ai",
    },
    "glm": {
        "label": "Zhipu GLM",
        "env_var": "GLM_API_KEY",
        "auth": "api_key",
        "docs": "https://open.bigmodel.cn",
    },
    "qwen": {
        "label": "Alibaba Qwen",
        "env_var": "QWEN_API_KEY",
        "auth": "api_key",
        "docs": "https://dashscope.console.aliyun.com",
    },
}

UNAVAILABLE = "Über die offizielle API nicht verfügbar"


class AccountService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if ACCOUNTS_FILE.exists():
            try:
                return json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        try:
            ACCOUNTS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def runtime_key(self, provider: str) -> str | None:
        entry = self._data.get(provider)
        if entry and entry.get("api_key"):
            return str(entry["api_key"]).strip() or None
        return None

    def default_model(self, provider: str) -> str | None:
        entry = self._data.get(provider)
        if entry and entry.get("default_model"):
            return entry["default_model"]
        return None

    def connect(self, provider: str, api_key: str, default_model: str | None = None) -> dict:
        if provider not in SUPPORTED:
            raise ValueError("Nicht unterstützter Anbieter")
        with self._lock:
            entry = self._data.setdefault(provider, {})
            entry["api_key"] = api_key.strip()
            if default_model:
                entry["default_model"] = default_model
            self._save()
        return {"provider": provider, "connected": True}

    def set_default_model(self, provider: str, model: str) -> dict:
        with self._lock:
            entry = self._data.setdefault(provider, {})
            entry["default_model"] = model
            self._save()
        return {"provider": provider, "default_model": model}

    def disconnect(self, provider: str) -> bool:
        with self._lock:
            existed = provider in self._data
            self._data.pop(provider, None)
            self._save()
            return existed

    def status(self, provider: str, env_configured: bool) -> dict:
        meta = SUPPORTED[provider]
        entry = self._data.get(provider, {})
        connected = bool(entry.get("api_key")) or env_configured
        return {
            "provider": provider,
            "label": meta["label"],
            "auth": meta["auth"],
            "docs": meta["docs"],
            "connected": connected,
            "source": "account" if entry.get("api_key") else ("env" if env_configured else None),
            "default_model": entry.get("default_model"),
            "account_name": UNAVAILABLE,
            "avatar_url": None,
            "plan": UNAVAILABLE,
        }


_service: AccountService | None = None


def get_account_service() -> AccountService:
    global _service
    if _service is None:
        _service = AccountService()
    return _service
