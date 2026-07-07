from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Callable

from app.providers.base import (
    ChatRequest,
    LLMProvider,
    ProviderError,
    StreamChunk,
    ToolExecutor,
)


class GeminiProvider(LLMProvider):
    name = "gemini"

    _DEFAULT_MODELS = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 180.0,
        key_resolver: Callable[[], str | None] | None = None,
    ) -> None:
        self._static_key = api_key
        self._key_resolver = key_resolver
        self._timeout = timeout
        self._models_cache: list[str] | None = None
        self._models_cached_at = 0.0

    def _key(self) -> str | None:
        if self._key_resolver is not None:
            return self._key_resolver()
        return self._static_key

    def available(self) -> bool:
        return bool(self._key())

    def _configure(self):
        key = self._key()
        if not key:
            raise ProviderError("gemini: API key missing")
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ProviderError("google-generativeai package not installed") from exc
        genai.configure(api_key=key)
        return genai

    async def list_models(self) -> list[str]:
        now = time.monotonic()
        if self._models_cache is not None and now - self._models_cached_at < 300:
            return self._models_cache

        def fetch() -> list[str]:
            genai = self._configure()
            names = [
                m.name.split("/")[-1]
                for m in genai.list_models()
                if "generateContent" in getattr(m, "supported_generation_methods", [])
            ]
            return sorted(set(names)) or self._DEFAULT_MODELS

        try:
            result = await asyncio.to_thread(fetch)
        except Exception:
            result = self._DEFAULT_MODELS
        self._models_cache = result
        self._models_cached_at = now
        return result

    async def stream(
        self, request: ChatRequest, tool_executor: ToolExecutor | None = None
    ) -> AsyncIterator[StreamChunk]:
        genai = self._configure()
        system_parts = [m.content for m in request.messages if m.role == "system"]
        history = []
        for m in request.messages:
            if m.role == "system":
                continue
            role = "model" if m.role == "assistant" else "user"
            history.append({"role": role, "parts": [m.content]})

        generation_config = {
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if request.max_tokens:
            generation_config["max_output_tokens"] = request.max_tokens
        model = genai.GenerativeModel(
            model_name=request.model,
            system_instruction="\n\n".join(system_parts) or None,
            generation_config=generation_config,
        )

        try:
            response = await model.generate_content_async(history, stream=True)
            async for chunk in response:
                text = getattr(chunk, "text", None)
                if text:
                    yield StreamChunk(delta=text, kind="content")
        except Exception as exc:
            raise ProviderError(f"gemini: {exc}") from exc
