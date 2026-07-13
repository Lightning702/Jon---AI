from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable, Literal

ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[str]]


@dataclass
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class ChatRequest:
    messages: list[ChatMessage]
    model: str
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: int | None = None
    seed: int | None = None
    stop: list[str] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    slot: str = "jon"


@dataclass
class StreamChunk:
    delta: str = ""
    kind: Literal["content", "reasoning", "tool", "tool_result", "usage"] = "content"
    name: str | None = None
    ok: bool | None = None
    args: dict[str, Any] | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class ModelInfo:
    id: str
    provider: str


class ProviderError(RuntimeError):
    pass


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self, request: ChatRequest, tool_executor: ToolExecutor | None = None
    ) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def complete(self, request: ChatRequest) -> str:
        parts: list[str] = []
        async for chunk in self.stream(request):
            if chunk.kind == "content":
                parts.append(chunk.delta)
        return "".join(parts)
