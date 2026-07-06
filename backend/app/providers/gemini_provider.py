from __future__ import annotations

from typing import AsyncIterator

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

    def __init__(self, api_key: str | None, timeout: float = 180.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    def available(self) -> bool:
        return bool(self._api_key)

    def _configure(self):
        if not self._api_key:
            raise ProviderError("gemini: API key missing")
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ProviderError("google-generativeai package not installed") from exc
        genai.configure(api_key=self._api_key)
        return genai

    async def list_models(self) -> list[str]:
        try:
            genai = self._configure()
            names = [
                m.name.split("/")[-1]
                for m in genai.list_models()
                if "generateContent" in getattr(m, "supported_generation_methods", [])
            ]
            return sorted(set(names)) or self._DEFAULT_MODELS
        except Exception:
            return self._DEFAULT_MODELS

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
            "max_output_tokens": request.max_tokens,
        }
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
