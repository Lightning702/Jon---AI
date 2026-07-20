from __future__ import annotations

from app.core.config import get_settings
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
) -> str:
    settings = get_settings()
    provider = provider or settings.default_provider
    model = model or settings.jon_model
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
    )
    parts: list[str] = []
    async for chunk in prov.stream(request, None):
        if chunk.kind == "content":
            parts.append(chunk.delta)
    return "".join(parts).strip()
