from __future__ import annotations

import asyncio

from app.core.config import get_settings, lebendes_modell
from app.providers.base import ChatMessage, ChatRequest
from app.providers.registry import get_registry


async def complete(
    system: str,
    user: str,
    provider: str | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.9,
    slot: str = "jon",
    first_token_timeout: float = 0.0,
) -> str:
    settings = get_settings()
    provider = provider or settings.default_provider
    model = lebendes_modell(model or settings.jon_model, provider)
    from app.services.offline import lokal_erzwingen

    provider, model = lokal_erzwingen(provider, model)
    prov = get_registry().get(provider)
    messages = []
    if system:
        messages.append(ChatMessage(role="system", content=system))
    messages.append(ChatMessage(role="user", content=user))
    request = ChatRequest(
        messages=messages,
        model=model,
        temperature=temperature,
        top_p=1.0,
        max_tokens=max_tokens,
        tools=[],
        slot=slot,
        first_token_timeout=first_token_timeout,
    )
    from app.services.premium import unbegrenzt

    if not unbegrenzt():
        return await _einmal(prov, request)
    wege = await _wege(provider, model)
    letzter: Exception | None = None
    from app.services.harness.modell import voruebergehend

    for runde in range(6):
        if runde and letzter is not None and not voruebergehend(letzter):
            break
        for name, kandidat in wege:
            request.model = kandidat
            try:
                return await _einmal(get_registry().get(name), request)
            except Exception as fehler:
                letzter = fehler
        await asyncio.sleep(min(20.0, 2.0 * (runde + 1)))
    raise letzter or RuntimeError("Kein Modell hat geantwortet.")


async def _einmal(prov, request: ChatRequest) -> str:
    parts: list[str] = []
    async for chunk in prov.stream(request, None):
        if chunk.kind == "content":
            parts.append(chunk.delta)
    return "".join(parts).strip()


async def _wege(provider: str, model: str) -> list[tuple[str, str]]:
    from app.services.chat_service import ZWEITER_ERSATZ
    from app.services.modell_router import get_model_router

    wege = await get_model_router().plan(provider, model)
    zweiter = ZWEITER_ERSATZ.get(provider, "")
    if zweiter and (provider, zweiter) not in wege:
        wege.insert(min(2, len(wege)), (provider, zweiter))
    return wege
