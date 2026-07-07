from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.keys import KeyManager
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import LLMProvider, ProviderError
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


class ProviderRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._keys = KeyManager(self._settings)
        self._providers: dict[str, LLMProvider] = {}
        self._build()

    def _resolver(self, provider: str):
        return lambda: self._keys.key_for(provider)

    def _build(self) -> None:
        s = self._settings
        t = s.request_timeout

        self._providers["nvidia"] = OpenAICompatibleProvider(
            name="nvidia",
            base_url=s.nvidia_base_url,
            key_resolver=self._resolver("nvidia"),
            default_models=[
                "openai/gpt-oss-120b",
                "z-ai/glm-5.2",
                "meta/llama-3.3-70b-instruct",
                "deepseek-ai/deepseek-r1",
                "qwen/qwen2.5-coder-32b-instruct",
                "nvidia/llama-3.1-nemotron-70b-instruct",
            ],
            timeout=t,
        )
        self._providers["openai"] = OpenAICompatibleProvider(
            name="openai",
            base_url=s.openai_base_url,
            key_resolver=self._resolver("openai"),
            default_models=["gpt-4o", "gpt-4o-mini", "o3-mini"],
            timeout=t,
        )
        self._providers["deepseek"] = OpenAICompatibleProvider(
            name="deepseek",
            base_url=s.deepseek_base_url,
            key_resolver=self._resolver("deepseek"),
            default_models=["deepseek-chat", "deepseek-reasoner"],
            timeout=t,
        )
        self._providers["mistral"] = OpenAICompatibleProvider(
            name="mistral",
            base_url=s.mistral_base_url,
            key_resolver=self._resolver("mistral"),
            default_models=["mistral-large-latest", "mistral-small-latest"],
            timeout=t,
        )
        self._providers["glm"] = OpenAICompatibleProvider(
            name="glm",
            base_url=s.glm_base_url,
            key_resolver=self._resolver("glm"),
            default_models=["glm-4-plus", "glm-4-flash"],
            timeout=t,
        )
        self._providers["qwen"] = OpenAICompatibleProvider(
            name="qwen",
            base_url=s.qwen_base_url,
            key_resolver=self._resolver("qwen"),
            default_models=["qwen-max", "qwen-plus", "qwen2.5-coder-32b-instruct"],
            timeout=t,
        )
        self._providers["ollama"] = OpenAICompatibleProvider(
            name="ollama",
            base_url=s.ollama_base_url,
            api_key="ollama",
            default_models=["llama3.2", "qwen2.5", "mistral"],
            timeout=t,
        )
        self._providers["lmstudio"] = OpenAICompatibleProvider(
            name="lmstudio",
            base_url=s.lmstudio_base_url,
            api_key="lmstudio",
            default_models=[],
            timeout=t,
        )
        self._providers["openrouter"] = OpenAICompatibleProvider(
            name="openrouter",
            base_url=s.openrouter_base_url,
            key_resolver=self._resolver("openrouter"),
            default_models=[
                "openai/gpt-4o-mini",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-2.0-flash-exp",
                "meta-llama/llama-3.3-70b-instruct",
            ],
            timeout=t,
        )
        self._providers["groq"] = OpenAICompatibleProvider(
            name="groq",
            base_url=s.groq_base_url,
            key_resolver=self._resolver("groq"),
            default_models=[
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
            ],
            timeout=t,
        )
        self._providers["together"] = OpenAICompatibleProvider(
            name="together",
            base_url=s.together_base_url,
            key_resolver=self._resolver("together"),
            default_models=[
                "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "Qwen/Qwen2.5-72B-Instruct-Turbo",
            ],
            timeout=t,
        )
        self._providers["xai"] = OpenAICompatibleProvider(
            name="xai",
            base_url=s.xai_base_url,
            key_resolver=self._resolver("xai"),
            default_models=["grok-2-latest", "grok-2-vision-latest"],
            timeout=t,
        )
        self._providers["anthropic"] = AnthropicProvider(
            key_resolver=self._resolver("anthropic"),
            timeout=t,
        )
        self._providers["gemini"] = GeminiProvider(
            key_resolver=self._resolver("gemini"),
            timeout=t,
        )

    def get(self, name: str) -> LLMProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderError(f"Unknown provider: {name}")
        return provider

    def all(self) -> dict[str, LLMProvider]:
        return dict(self._providers)

    def available(self) -> list[str]:
        return [name for name, p in self._providers.items() if p.available()]


_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
