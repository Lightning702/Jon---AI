from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI

from app.providers.base import ChatRequest, ProviderError, StreamChunk, ToolExecutor
from app.providers.openai_compatible import (
    LEAD_GATE,
    MAX_TOOL_ROUNDS,
    MODELS_CACHE_TTL,
    MODELS_FAIL_TTL,
    TEMPLATE_TOKEN,
    OpenAICompatibleProvider,
    clean_lead,
)

RECONNECT_TRIES = 3
RECONNECT_DELAY = 0.8
CONNECT_TIMEOUT = 10.0


class OllamaProvider(OpenAICompatibleProvider):
    def __init__(self, timeout: float = 180.0) -> None:
        from app.services.ollama_service import get_ollama_service

        service = get_ollama_service()
        super().__init__(
            name="ollama",
            base_url=service.openai_base_url(),
            api_key="ollama",
            default_models=[],
            timeout=timeout,
        )

    @property
    def _service(self):
        from app.services.ollama_service import get_ollama_service

        return get_ollama_service()

    def available(self) -> bool:
        return self._service.enabled()

    def _client(self, slot: str = "jon") -> AsyncOpenAI:
        url = self._service.openai_base_url()
        client = self._clients.get(url)
        if client is None:
            client = AsyncOpenAI(
                base_url=url,
                api_key="ollama",
                timeout=self._service.timeout(),
                max_retries=1,
            )
            self._clients[url] = client
        return client

    async def list_models(self) -> list[str]:
        service = self._service
        if not service.enabled():
            return []
        now = time.monotonic()
        if (
            self._models_cache is not None
            and now - self._models_cached_at < self._models_cache_ttl
        ):
            return self._models_cache
        if not service.auto_load_models():
            known = service.known_models()
            selected = service.selected_model()
            if not known and selected:
                known = [selected]
            return known
        try:
            result = await service.fetch_models()
            ttl = MODELS_CACHE_TTL if result else MODELS_FAIL_TTL
        except Exception:
            result = []
            ttl = MODELS_FAIL_TTL
        self._models_cache = result
        self._models_cached_at = now
        self._models_cache_ttl = ttl
        return result

    def _payload(self, request: ChatRequest, config: dict, model: str) -> dict:
        messages: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content} for m in request.messages
        ]
        extra = str(config["system_prompt"]).strip()
        if extra:
            position = 1 if messages and messages[0]["role"] == "system" else 0
            messages.insert(position, {"role": "system", "content": extra})
        options = self._service.chat_options()
        options["temperature"] = float(request.temperature)
        options["top_p"] = float(request.top_p)
        if request.max_tokens:
            options["num_predict"] = int(request.max_tokens)
        if request.seed is not None:
            options["seed"] = int(request.seed)
        if request.stop:
            options["stop"] = list(request.stop)
        return {
            "model": model,
            "messages": messages,
            "stream": bool(config["stream"]),
            "keep_alive": config["keep_alive"],
            "options": options,
        }

    def _error(self, exc: Exception) -> ProviderError:
        return ProviderError("Ollama: " + self._service.friendly_error(exc))

    def _status_error(self, status: int, body: str, model: str) -> ProviderError:
        text = body.strip()
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and payload.get("error"):
                text = str(payload["error"])
        except Exception:
            pass
        lowered = text.lower()
        if status == 404 or "not found" in lowered:
            return ProviderError(
                f"Ollama: Das Modell {model} ist auf dem Server nicht installiert. "
                f"Dort einmal ausführen: ollama pull {model}"
            )
        if "memory" in lowered or "system memory" in lowered:
            return ProviderError(
                f"Ollama: {text} — das Modell passt nicht in den Speicher. Nimm ein "
                "kleineres Modell oder verringere die Context Length."
            )
        return ProviderError(f"Ollama: {text or f'Fehler {status}'}")

    async def _open(self, client: httpx.AsyncClient, url: str, payload: dict):
        tries = RECONNECT_TRIES if self._service.config()["auto_reconnect"] else 1
        last: Exception | None = None
        for attempt in range(tries):
            context = client.stream("POST", url, json=payload)
            try:
                response = await context.__aenter__()
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError) as exc:
                last = exc
                if attempt + 1 < tries:
                    await asyncio.sleep(RECONNECT_DELAY * (attempt + 1))
                continue
            except httpx.HTTPError as exc:
                raise self._error(exc) from exc
            return context, response
        raise self._error(last) from last

    async def _lines(
        self, client: httpx.AsyncClient, url: str, payload: dict, model: str
    ) -> AsyncIterator[dict]:
        if not payload["stream"]:
            try:
                response = await client.post(url, json=payload)
            except httpx.HTTPError as exc:
                raise self._error(exc) from exc
            if response.status_code >= 400:
                raise self._status_error(response.status_code, response.text, model)
            try:
                yield response.json()
            except ValueError as exc:
                raise ProviderError("Ollama: Unlesbare Antwort vom Server.") from exc
            return
        context, response = await self._open(client, url, payload)
        try:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", "replace")
                raise self._status_error(response.status_code, body, model)
            async for line in response.aiter_lines():
                text = line.strip()
                if not text:
                    continue
                try:
                    yield json.loads(text)
                except ValueError:
                    continue
        except httpx.HTTPError as exc:
            raise self._error(exc) from exc
        finally:
            await context.__aexit__(None, None, None)

    async def stream(
        self, request: ChatRequest, tool_executor: ToolExecutor | None = None
    ) -> AsyncIterator[StreamChunk]:
        service = self._service
        config = service.config()
        if not config["enabled"]:
            raise ProviderError(
                "Ollama ist ausgeschaltet. Schalte es in den Einstellungen unter "
                "Ollama wieder ein."
            )
        model = request.model or str(config["model"])
        if not model:
            raise ProviderError(
                "Für Ollama ist kein Modell gewählt. Wähle in den Einstellungen "
                "unter Ollama ein Modell aus."
            )
        payload = self._payload(request, config, model)
        tools = request.tools or None
        use_tools = bool(
            tools and tool_executor and model not in self._no_tool_models
        )
        if use_tools:
            payload["tools"] = tools
        url = service.base_url() + "/api/chat"
        timeout = httpx.Timeout(float(config["timeout"]), connect=CONNECT_TIMEOUT)
        rounds = MAX_TOOL_ROUNDS if use_tools else 1

        async with httpx.AsyncClient(timeout=timeout) as client:
            for _ in range(rounds):
                content_acc: list[str] = []
                calls: list[dict] = []
                lead = ""
                lead_open = True
                answered = False
                while True:
                    iterator = self._lines(client, url, payload, model)
                    try:
                        async for data in iterator:
                            answered = True
                            if data.get("error"):
                                raise self._status_error(
                                    400, str(data["error"]), model
                                )
                            message = data.get("message") or {}
                            thinking = message.get("thinking")
                            if thinking:
                                yield StreamChunk(delta=thinking, kind="reasoning")
                            content = message.get("content")
                            if content:
                                if lead_open:
                                    lead += content
                                    if len(lead) < LEAD_GATE and not data.get("done"):
                                        continue
                                    lead_open = False
                                    cleaned = clean_lead(lead)
                                    lead = ""
                                    if cleaned:
                                        content_acc.append(cleaned)
                                        yield StreamChunk(
                                            delta=cleaned, kind="content"
                                        )
                                else:
                                    piece = TEMPLATE_TOKEN.sub("", content)
                                    if piece:
                                        content_acc.append(piece)
                                        yield StreamChunk(delta=piece, kind="content")
                            for call in message.get("tool_calls") or []:
                                function = call.get("function") or {}
                                name = str(function.get("name", "")).strip()
                                if name:
                                    calls.append(
                                        {
                                            "name": name,
                                            "args": function.get("arguments") or {},
                                        }
                                    )
                            if data.get("done"):
                                prompt_tokens = int(data.get("prompt_eval_count") or 0)
                                completion_tokens = int(data.get("eval_count") or 0)
                                if prompt_tokens or completion_tokens:
                                    yield StreamChunk(
                                        kind="usage",
                                        prompt_tokens=prompt_tokens,
                                        completion_tokens=completion_tokens,
                                    )
                    except ProviderError as exc:
                        text = str(exc).lower()
                        if (
                            use_tools
                            and not answered
                            and "tool" in text
                            and ("support" in text or "unsupported" in text)
                        ):
                            self._no_tool_models.add(model)
                            payload.pop("tools", None)
                            use_tools = False
                            tools = None
                            continue
                        raise
                    finally:
                        await iterator.aclose()
                    break

                if lead_open and lead:
                    cleaned = clean_lead(lead)
                    if cleaned:
                        content_acc.append(cleaned)
                        yield StreamChunk(delta=cleaned, kind="content")

                if not calls:
                    return

                payload["messages"].append(
                    {
                        "role": "assistant",
                        "content": "".join(content_acc),
                        "tool_calls": [
                            {"function": {"name": c["name"], "arguments": c["args"]}}
                            for c in calls
                        ],
                    }
                )
                for call in calls:
                    name = call["name"]
                    args = call["args"]
                    if isinstance(args, str):
                        try:
                            args = json.loads(args or "{}")
                        except ValueError:
                            args = {}
                    if not isinstance(args, dict):
                        args = {}
                    yield StreamChunk(kind="tool", name=name, args=args)
                    try:
                        result = await tool_executor(name, args)
                        ok = True
                    except Exception as exc:
                        result = f"Fehler: {exc}"
                        ok = False
                    yield StreamChunk(kind="tool_result", name=name, ok=ok)
                    payload["messages"].append(
                        {
                            "role": "tool",
                            "tool_name": name,
                            "content": str(result)[:8000],
                        }
                    )
