from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class ProviderKey:
    provider: str
    env_var: str
    configured: bool


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

    def env_key_for(self, provider: str) -> str | None:
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

    def key_for(self, provider: str) -> str | None:
        from app.services.account_service import get_account_service

        runtime = get_account_service().runtime_key(provider)
        if runtime:
            return runtime
        return self.env_key_for(provider)

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
                )
            )
        return result
