from __future__ import annotations

from typing import AsyncIterator

from app.providers.base import (
    ChatRequest,
    LLMProvider,
    ProviderError,
    StreamChunk,
    ToolExecutor,
)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    _DEFAULT_MODELS = [
        "claude-opus-4-8",
        "claude-sonnet-5",
        "claude-haiku-4-5-20251001",
    ]

    def __init__(self, api_key: str | None, timeout: float = 180.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    def available(self) -> bool:
        return bool(self._api_key)

    def _client(self):
        if not self._api_key:
            raise ProviderError("anthropic: API key missing")
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise ProviderError("anthropic package not installed") from exc
        return AsyncAnthropic(api_key=self._api_key, timeout=self._timeout)

    async def list_models(self) -> list[str]:
        return self._DEFAULT_MODELS

    async def stream(
        self, request: ChatRequest, tool_executor: ToolExecutor | None = None
    ) -> AsyncIterator[StreamChunk]:
        client = self._client()
        system_parts = [m.content for m in request.messages if m.role == "system"]
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in ("user", "assistant")
        ]
        kwargs = dict(
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=min(request.temperature, 1.0),
            top_p=request.top_p,
            messages=messages,
        )
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        try:
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    if text:
                        yield StreamChunk(delta=text, kind="content")
        except Exception as exc:
            raise ProviderError(f"anthropic: {exc}") from exc
