from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


SLOT_EMIL = "emil"
SLOT_JON = "jon"


def split_keys(raw: str | None) -> list[str]:
    if not isinstance(raw, str):
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def pick_key(raw: str | None, slot: str = SLOT_JON) -> str | None:
    parts = split_keys(raw)
    if not parts:
        return None
    if slot == SLOT_EMIL:
        return parts[0]
    return parts[1] if len(parts) > 1 else parts[0]


@dataclass(frozen=True)
class ProviderKey:
    provider: str
    env_var: str
    configured: bool
    keys: int = 0


class KeyManager:
    _ENV_MAP: dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "glm": "GLM_API_KEY",
        "qwen": "QWEN_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "groq": "GROQ_API_KEY",
        "together": "TOGETHER_API_KEY",
        "xai": "XAI_API_KEY",
        "ollama": "OLLAMA_BASE_URL",
        "lmstudio": "LMSTUDIO_BASE_URL",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _raw_env(self, provider: str) -> str | None:
        mapping = {
            "openai": self._settings.openai_api_key,
            "nvidia": self._settings.nvidia_api_key,
            "anthropic": self._settings.anthropic_api_key,
            "gemini": self._settings.google_api_key,
            "deepseek": self._settings.deepseek_api_key,
            "mistral": self._settings.mistral_api_key,
            "glm": self._settings.glm_api_key,
            "qwen": self._settings.qwen_api_key,
            "openrouter": self._settings.openrouter_api_key,
            "groq": self._settings.groq_api_key,
            "together": self._settings.together_api_key,
            "xai": self._settings.xai_api_key,
            "ollama": "ollama",
            "lmstudio": "lmstudio",
        }
        value = mapping.get(provider)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def env_key_for(self, provider: str, slot: str = SLOT_JON) -> str | None:
        return pick_key(self._raw_env(provider), slot)

    def _raw_key(self, provider: str) -> str | None:
        from app.services.account_service import get_account_service

        runtime = get_account_service().runtime_key(provider)
        if runtime:
            return runtime
        return self._raw_env(provider)

    def key_for(self, provider: str, slot: str = SLOT_JON) -> str | None:
        return pick_key(self._raw_key(provider), slot)

    def key_count(self, provider: str) -> int:
        return len(split_keys(self._raw_key(provider)))

    def env_var_for(self, provider: str) -> str:
        return self._ENV_MAP.get(provider, provider.upper() + "_API_KEY")

    def status(self) -> list[ProviderKey]:
        result: list[ProviderKey] = []
        for provider, env_var in self._ENV_MAP.items():
            result.append(
                ProviderKey(
                    provider=provider,
                    env_var=env_var,
                    configured=self.key_for(provider) is not None,
                    keys=self.key_count(provider),
                )
            )
        return result
