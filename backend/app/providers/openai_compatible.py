from __future__ import annotations

from app.services.tool_result import succeeded

import asyncio
import json
import re
import time

import httpx
from typing import AsyncIterator, Callable

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
)

from app.core.config import get_settings, lebendes_modell
from app.providers.base import (
    ChatRequest,
    LLMProvider,
    ProviderError,
    StreamChunk,
    ToolExecutor,
)

MAX_TOOL_ROUNDS = 30
UNBEGRENZT_RUNDEN = 1_000_000


def tool_runden() -> int:
    from app.services.premium import unbegrenzt

    return UNBEGRENZT_RUNDEN if unbegrenzt() else MAX_TOOL_ROUNDS
TRANSIENT_RETRIES = 2
RATE_RETRIES = 3
DEFAULT_MAX_TOKENS = 32768
MIN_MAX_TOKENS = 4096
MODELS_CACHE_TTL = 300.0
MODELS_FAIL_TTL = 30.0
REASONING_MODELS = ("gpt-oss",)
DENK_SCHALTER = ("nemotron-3", "nemotron-nano-3", "nemotron-3.5")


def denk_extra(modell: str, denken: bool | None) -> dict:
    name = (modell or "").lower()
    if not any(marke in name for marke in DENK_SCHALTER):
        return {}
    if denken is None:
        try:
            from app.services.settings_service import get_settings_service

            denken = not get_settings_service().get().get("blitzschnell", False)
        except Exception:
            denken = True
    return {"chat_template_kwargs": {"enable_thinking": bool(denken)}}
PATIENT_PROVIDERS = ("ollama", "lmstudio")
LEAD_GATE = 40
TEMPLATE_TOKEN = re.compile(r"<\|[a-z_]+\|>")
ROLE_PREFIX = re.compile(
    r"^\s*(?:assistant|system|user|model)\s*[:\n]+", re.IGNORECASE
)
STOP_SEQUENCES = ["<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>"]
STREAM_PAUSE_S = 180.0


def fehlertext(exc: BaseException) -> str:
    text = str(exc).strip()
    if isinstance(exc, httpx.ReadTimeout):
        return "Die Verbindung ist mitten in der Antwort abgerissen (mehrere Minuten keine Daten). Der Anbieter ist überlastet. Versuche es erneut oder wähle ein anderes Modell."
    if isinstance(exc, (httpx.RemoteProtocolError, httpx.ReadError)):
        return "Der Anbieter hat die Verbindung mitten in der Antwort getrennt. Versuche es erneut oder wähle ein anderes Modell."
    if isinstance(exc, httpx.TimeoutException):
        return "Zeitüberschreitung bei der Verbindung zum Anbieter. Versuche es erneut."
    return text or f"{type(exc).__name__} ohne Fehlermeldung"


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
        self._no_tool_models: set[str] = set()
        self._ohne_denkschalter: set[str] = set()
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
            from app.core.netzweg import async_client, umleitbar

            extra = {}
            if umleitbar(httpx.URL(self._base_url).host):
                extra["http_client"] = async_client(timeout=self._timeout)
            client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=key,
                timeout=self._timeout,
                max_retries=1,
                **extra,
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
                rest = [
                    m
                    for m in remote
                    if m not in curated and lebendes_modell(m, self.name) == m
                ]
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
        self, model: str, data_url: str, prompt: str, max_tokens: int = 300, slot: str = "jon"
    ) -> str:
        return await self.describe_images(model, [data_url], prompt, max_tokens, slot)

    async def describe_images(
        self, model: str, data_urls: list[str], prompt: str, max_tokens: int = 300, slot: str = "jon", system: str = ""
    ) -> str:
        client = self._client(slot)
        zusatz = denk_extra(model, False)
        nachrichten: list[dict] = [{"role": "system", "content": system}] if system else []
        nachrichten.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
                + [{"type": "image_url", "image_url": {"url": url}} for url in data_urls],
            }
        )
        completion = await client.with_options(
            timeout=45.0, max_retries=0
        ).chat.completions.create(
            **({"extra_body": zusatz} if zusatz else {}),
            model=model,
            messages=nachrichten,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        choices = getattr(completion, "choices", None)
        if not choices:
            return ""
        return (choices[0].message.content or "").strip()

    async def _create_with_retry(self, client: AsyncOpenAI, payload: dict):
        last: Exception | None = None
        gebremst = 0
        attempt = -1
        while attempt + 1 < TRANSIENT_RETRIES + gebremst:
            attempt += 1
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
                if status == 429 and gebremst < RATE_RETRIES:
                    gebremst += 1
                    last = exc
                    warten = 2.0 * (2 ** (gebremst - 1))
                    try:
                        warten = min(10.0, max(warten, float(getattr(getattr(exc, "response", None), "headers", {}).get("retry-after", 0) or 0)))
                    except (TypeError, ValueError):
                        pass
                    await asyncio.sleep(warten)
                    continue
                if status is not None and status >= 500:
                    last = exc
                    await asyncio.sleep(0.6 * (attempt + 1))
                    continue
                if (
                    status == 400
                    and payload.get("extra_body")
                    and any(w in str(exc).lower() for w in ("reasoning", "chat_template", "enable_thinking", "extra"))
                ):
                    if "chat_template_kwargs" in (payload.get("extra_body") or {}):
                        self.__dict__.setdefault("_ohne_denkschalter", set()).add(payload.get("model", ""))
                    payload.pop("extra_body", None)
                    last = exc
                    continue
                message = str(exc).lower()
                if (
                    status == 400
                    and payload.get("tools")
                    and "tool" in message
                    and ("support" in message or "unsupported" in message)
                ):
                    self._no_tool_models.add(payload.get("model", ""))
                    payload.pop("tools", None)
                    payload.pop("tool_choice", None)
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
                raise ProviderError(f"{self.name}: {fehlertext(exc)}") from exc
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
        use_tools = bool(
            tools and tool_executor and request.model not in self._no_tool_models
        )
        rounds = tool_runden() if use_tools else 1
        guard = (
            0.0
            if self.name in PATIENT_PROVIDERS
            else request.first_token_timeout
            or settings.first_token_timeout * (2.0 if tools else 1.0)
        )
        max_tokens = request.max_tokens or DEFAULT_MAX_TOKENS
        effort = get_settings().reasoning_effort.strip().lower()
        extra_body = (
            {"reasoning_effort": effort}
            if effort in ("low", "medium", "high")
            and any(marker in request.model.lower() for marker in REASONING_MODELS)
            else None
        )
        if request.model not in getattr(self, "_ohne_denkschalter", set()):
            schalter = denk_extra(request.model, request.denken)
            if schalter:
                extra_body = {**(extra_body or {}), **schalter}

        for round_index in range(rounds):
            watchdog = guard if round_index == 0 else guard * 1.5
            caller = (
                client.with_options(
                    timeout=httpx.Timeout(max(STREAM_PAUSE_S * (1.7 if use_tools else 1.0), watchdog), connect=max(watchdog, 8.0)), max_retries=0
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
            if use_tools and "tools" not in payload:
                use_tools = False
                tools = None

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
                    raise ProviderError(f"{self.name}: {fehlertext(exc)}") from exc
                await asyncio.sleep(0.6)
                continue
            except Exception as exc:
                raise ProviderError(f"{self.name}: {fehlertext(exc)}") from exc

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
                    ok = succeeded(result)
                except Exception as exc:
                    result = f"Fehler: {exc}"
                    ok = False
                yield StreamChunk(
                    kind="tool_result", name=name, ok=ok, result=str(result)
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": slot["id"] or f"call_{idx}",
                        "content": str(result)[:8000],
                    }
                )
