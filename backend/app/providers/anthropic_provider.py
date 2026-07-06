from __future__ import annotations

from typing import AsyncIterator, Callable

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

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 180.0,
        key_resolver: Callable[[], str | None] | None = None,
    ) -> None:
        self._static_key = api_key
        self._key_resolver = key_resolver
        self._timeout = timeout

    def _key(self) -> str | None:
        if self._key_resolver is not None:
            return self._key_resolver()
        return self._static_key

    def available(self) -> bool:
        return bool(self._key())

    def _client(self):
        key = self._key()
        if not key:
            raise ProviderError("anthropic: API key missing")
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise ProviderError("anthropic package not installed") from exc
        return AsyncAnthropic(api_key=key, timeout=self._timeout)

    async def list_models(self) -> list[str]:
        try:
            client = self._client()
            response = await client.models.list(limit=100)
            ids = [m.id for m in getattr(response, "data", [])]
            return ids or self._DEFAULT_MODELS
        except Exception:
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
        fallback = 8192 if "haiku" in request.model.lower() else 32000
        kwargs = dict(
            model=request.model,
            max_tokens=request.max_tokens or fallback,
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
                final = await stream.get_final_message()
                usage = getattr(final, "usage", None)
                if usage is not None:
                    yield StreamChunk(
                        kind="usage",
                        prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
                        completion_tokens=getattr(usage, "output_tokens", 0) or 0,
                    )
        except Exception as exc:
            raise ProviderError(f"anthropic: {exc}") from exc
