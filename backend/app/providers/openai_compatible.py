from __future__ import annotations

import asyncio
import json
import re
import time
from typing import AsyncIterator, Callable

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
)

from app.core.config import get_settings
from app.providers.base import (
    ChatRequest,
    LLMProvider,
    ProviderError,
    StreamChunk,
    ToolExecutor,
)

MAX_TOOL_ROUNDS = 30
TRANSIENT_RETRIES = 2
DEFAULT_MAX_TOKENS = 32768
MIN_MAX_TOKENS = 4096
MODELS_CACHE_TTL = 300.0
MODELS_FAIL_TTL = 30.0
REASONING_MODELS = ("gpt-oss",)
PATIENT_PROVIDERS = ("ollama", "lmstudio")
LEAD_GATE = 40
TEMPLATE_TOKEN = re.compile(r"<\|[a-z_]+\|>")
ROLE_PREFIX = re.compile(
    r"^\s*(?:assistant|system|user|model)\s*[:\n]+", re.IGNORECASE
)
STOP_SEQUENCES = ["<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>"]


def clean_lead(text: str) -> str:
    out = TEMPLATE_TOKEN.sub("", text)
    while True:
        stripped = ROLE_PREFIX.sub("", out, count=1)
        if stripped == out:
            break
        out = stripped
    return out.lstrip()
TRANSIENT_ERRORS = (InternalServerError,)
STALL_ERRORS = (
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
        key_resolver: Callable[..., str | None] | None = None,
    ) -> None:
        self.name = name
        self._base_url = base_url
        self._static_key = api_key
        self._key_resolver = key_resolver
        self._default_models = default_models or []
        self._timeout = timeout
        self._clients: dict[str, AsyncOpenAI] = {}
        self._models_cache: list[str] | None = None
        self._models_cached_at = 0.0
        self._models_cache_ttl = 0.0

    def _key(self, slot: str = "jon") -> str | None:
        if self._key_resolver is not None:
            return self._key_resolver(slot)
        return self._static_key

    def available(self) -> bool:
        return bool(self._key())

    def _client(self, slot: str = "jon") -> AsyncOpenAI:
        key = self._key(slot)
        if not key:
            raise ProviderError(f"{self.name}: API key missing")
        client = self._clients.get(key)
        if client is None:
            client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=key,
                timeout=self._timeout,
                max_retries=1,
            )
            self._clients[key] = client
        return client

    async def list_models(self) -> list[str]:
        now = time.monotonic()
        if (
            self._models_cache is not None
            and now - self._models_cached_at < self._models_cache_ttl
        ):
            return self._models_cache
        try:
            client = self._client()
            response = await client.with_options(
                timeout=4.0, max_retries=0
            ).models.list()
            remote = sorted({item.id for item in response.data})
            if not remote:
                result = self._default_models
                ttl = MODELS_FAIL_TTL
            else:
                curated = [m for m in self._default_models if m in remote]
                rest = [m for m in remote if m not in curated]
                result = curated + rest
                ttl = MODELS_CACHE_TTL
        except Exception:
            result = self._default_models
            ttl = MODELS_FAIL_TTL
        self._models_cache = result
        self._models_cached_at = now
        self._models_cache_ttl = ttl
        return result

    async def describe_image(
        self, model: str, data_url: str, prompt: str, max_tokens: int = 300
    ) -> str:
        client = self._client()
        completion = await client.with_options(
            timeout=45.0, max_retries=0
        ).chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        choices = getattr(completion, "choices", None)
        if not choices:
            return ""
        return (choices[0].message.content or "").strip()

    async def _create_with_retry(self, client: AsyncOpenAI, payload: dict):
        last: Exception | None = None
        for attempt in range(TRANSIENT_RETRIES):
            try:
                return await client.chat.completions.create(**payload)
            except STALL_ERRORS as exc:
                raise ProviderError(
                    f"{self.name}: {payload.get('model')} antwortet nicht "
                    "(Anbieter ueberlastet)"
                ) from exc
            except TRANSIENT_ERRORS as exc:
                last = exc
                await asyncio.sleep(0.6 * (attempt + 1))
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                if status is not None and status >= 500:
                    last = exc
                    await asyncio.sleep(0.6 * (attempt + 1))
                    continue
                if (
                    status == 400
                    and payload.get("extra_body")
                    and "reasoning" in str(exc).lower()
                ):
                    payload.pop("extra_body", None)
                    last = exc
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
        settings = get_settings()
        client = self._client(request.slot)
        messages: list[dict] = [
            {"role": m.role, "content": m.content} for m in request.messages
        ]
        tools = request.tools or None
        use_tools = bool(tools and tool_executor)
        rounds = MAX_TOOL_ROUNDS if use_tools else 1
        guard = (
            0.0
            if self.name in PATIENT_PROVIDERS
            else settings.first_token_timeout * (2.0 if tools else 1.0)
        )
        max_tokens = request.max_tokens or DEFAULT_MAX_TOKENS
        effort = get_settings().reasoning_effort.strip().lower()
        extra_body = (
            {"reasoning_effort": effort}
            if effort in ("low", "medium", "high")
            and any(marker in request.model.lower() for marker in REASONING_MODELS)
            else None
        )

        for round_index in range(rounds):
            watchdog = guard if round_index == 0 else 0.0
            caller = (
                client.with_options(
                    timeout=max(watchdog, 8.0), max_retries=0
                )
                if watchdog > 0
                else client
            )
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
            if extra_body:
                payload["extra_body"] = extra_body
            payload["stream_options"] = {"include_usage": True}
            if request.seed is not None:
                payload["seed"] = request.seed
            payload["stop"] = list(request.stop) + STOP_SEQUENCES

            completion = await self._create_with_retry(caller, payload)
            max_tokens = payload["max_tokens"]
            if extra_body and "extra_body" not in payload:
                extra_body = None

            content_acc: list[str] = []
            calls: dict[int, dict] = {}
            lead = ""
            lead_open = True
            iterator = completion.__aiter__()
            first_chunk = True

            try:
                while True:
                    try:
                        if first_chunk and watchdog > 0:
                            chunk = await asyncio.wait_for(
                                iterator.__anext__(), timeout=watchdog
                            )
                        else:
                            chunk = await iterator.__anext__()
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError as exc:
                        raise ProviderError(
                            f"Das Modell {request.model} antwortet nicht "
                            f"(keine Reaktion nach {watchdog:.0f} Sekunden). "
                            "Der Anbieter ist wahrscheinlich ueberlastet - waehle "
                            "oben ein anderes Modell."
                        ) from exc
                    first_chunk = False
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
                        if lead_open:
                            lead += content
                            if len(lead) < LEAD_GATE:
                                continue
                            lead_open = False
                            cleaned = clean_lead(lead)
                            lead = ""
                            if cleaned:
                                content_acc.append(cleaned)
                                yield StreamChunk(delta=cleaned, kind="content")
                            continue
                        piece = TEMPLATE_TOKEN.sub("", content)
                        if not piece:
                            continue
                        content_acc.append(piece)
                        yield StreamChunk(delta=piece, kind="content")
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

            if lead_open and lead:
                cleaned = clean_lead(lead)
                lead = ""
                lead_open = False
                if cleaned:
                    content_acc.append(cleaned)
                    yield StreamChunk(delta=cleaned, kind="content")

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
