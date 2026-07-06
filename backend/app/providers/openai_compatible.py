from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Callable

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
)

from app.providers.base import (
    ChatRequest,
    LLMProvider,
    ProviderError,
    StreamChunk,
    ToolExecutor,
)

MAX_TOOL_ROUNDS = 30
TRANSIENT_RETRIES = 4
DEFAULT_MAX_TOKENS = 32768
MIN_MAX_TOKENS = 4096
TRANSIENT_ERRORS = (
    InternalServerError,
    APITimeoutError,
    APIConnectionError,
)


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str | None = None,
        default_models: list[str] | None = None,
        timeout: float = 180.0,
        key_resolver: Callable[[], str | None] | None = None,
    ) -> None:
        self.name = name
        self._base_url = base_url
        self._static_key = api_key
        self._key_resolver = key_resolver
        self._default_models = default_models or []
        self._timeout = timeout
        self._client_cache: AsyncOpenAI | None = None
        self._cached_key: str | None = None

    def _key(self) -> str | None:
        if self._key_resolver is not None:
            return self._key_resolver()
        return self._static_key

    def available(self) -> bool:
        return bool(self._key())

    def _client(self) -> AsyncOpenAI:
        key = self._key()
        if not key:
            raise ProviderError(f"{self.name}: API key missing")
        if self._client_cache is None or self._cached_key != key:
            self._client_cache = AsyncOpenAI(
                base_url=self._base_url,
                api_key=key,
                timeout=self._timeout,
                max_retries=1,
            )
            self._cached_key = key
        return self._client_cache

    async def list_models(self) -> list[str]:
        try:
            client = self._client()
            response = await client.models.list()
            remote = sorted({item.id for item in response.data})
            if not remote:
                return self._default_models
            curated = [m for m in self._default_models if m in remote]
            rest = [m for m in remote if m not in curated]
            return curated + rest
        except Exception:
            return self._default_models

    async def _create_with_retry(self, client: AsyncOpenAI, payload: dict):
        last: Exception | None = None
        for attempt in range(TRANSIENT_RETRIES):
            try:
                return await client.chat.completions.create(**payload)
            except TRANSIENT_ERRORS as exc:
                last = exc
                await asyncio.sleep(0.6 * (attempt + 1))
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                if status is not None and status >= 500:
                    last = exc
                    await asyncio.sleep(0.6 * (attempt + 1))
                    continue
                tokens = payload.get("max_tokens")
                if (
                    status == 400
                    and tokens
                    and tokens > MIN_MAX_TOKENS
                    and "token" in str(exc).lower()
                ):
                    payload["max_tokens"] = max(MIN_MAX_TOKENS, tokens // 2)
                    last = exc
                    continue
                raise ProviderError(f"{self.name}: {exc}") from exc
        raise ProviderError(
            f"{self.name}: Server ueberlastet (mehrere Fehlversuche): {last}"
        ) from last

    async def stream(
        self, request: ChatRequest, tool_executor: ToolExecutor | None = None
    ) -> AsyncIterator[StreamChunk]:
        client = self._client()
        messages: list[dict] = [
            {"role": m.role, "content": m.content} for m in request.messages
        ]
        tools = request.tools or None
        use_tools = bool(tools and tool_executor)
        rounds = MAX_TOOL_ROUNDS if use_tools else 1
        max_tokens = request.max_tokens or DEFAULT_MAX_TOKENS

        for _ in range(rounds):
            payload = dict(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=max_tokens,
                stream=True,
            )
            if use_tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            payload["stream_options"] = {"include_usage": True}
            if request.seed is not None:
                payload["seed"] = request.seed
            if request.stop:
                payload["stop"] = request.stop

            completion = await self._create_with_retry(client, payload)
            max_tokens = payload["max_tokens"]

            content_acc: list[str] = []
            calls: dict[int, dict] = {}

            try:
                async for chunk in completion:
                    usage = getattr(chunk, "usage", None)
                    if usage is not None:
                        yield StreamChunk(
                            kind="usage",
                            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                        )
                    choices = getattr(chunk, "choices", None)
                    if not choices:
                        continue
                    delta = getattr(choices[0], "delta", None)
                    if delta is None:
                        continue
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        yield StreamChunk(delta=reasoning, kind="reasoning")
                    content = getattr(delta, "content", None)
                    if content:
                        content_acc.append(content)
                        yield StreamChunk(delta=content, kind="content")
                    for tc in getattr(delta, "tool_calls", None) or []:
                        slot = calls.setdefault(
                            tc.index, {"id": None, "name": "", "args": ""}
                        )
                        if getattr(tc, "id", None):
                            slot["id"] = tc.id
                        fn = getattr(tc, "function", None)
                        if fn is not None:
                            if getattr(fn, "name", None):
                                slot["name"] += fn.name
                            if getattr(fn, "arguments", None):
                                slot["args"] += fn.arguments
            except TRANSIENT_ERRORS as exc:
                if content_acc or calls:
                    raise ProviderError(f"{self.name}: {exc}") from exc
                await asyncio.sleep(0.6)
                continue
            except Exception as exc:
                raise ProviderError(f"{self.name}: {exc}") from exc

            if not calls:
                return

            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(content_acc) or None,
                    "tool_calls": [
                        {
                            "id": slot["id"] or f"call_{idx}",
                            "type": "function",
                            "function": {
                                "name": slot["name"],
                                "arguments": slot["args"] or "{}",
                            },
                        }
                        for idx, slot in sorted(calls.items())
                    ],
                }
            )

            for idx, slot in sorted(calls.items()):
                name = slot["name"]
                raw = slot["args"].strip() or "{}"
                try:
                    args = json.loads(raw)
                except Exception:
                    args = {}
                yield StreamChunk(kind="tool", name=name, args=args)
                try:
                    result = await tool_executor(name, args)
                    ok = True
                except Exception as exc:
                    result = f"Fehler: {exc}"
                    ok = False
                yield StreamChunk(kind="tool_result", name=name, ok=ok)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": slot["id"] or f"call_{idx}",
                        "content": str(result)[:8000],
                    }
                )
