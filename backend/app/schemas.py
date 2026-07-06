from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatIn(BaseModel):
    messages: list[MessageIn]
    provider: str | None = None
    model: str | None = None
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: int = 16384
    seed: int | None = None
    conversation_id: str | None = None
    persist: bool = True


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    reasoning: str | None = None
    position: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: str
    title: str
    provider: str
    model: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ProviderStatus(BaseModel):
    provider: str
    configured: bool
    env_var: str
    models: list[str] = []


class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    default_provider: str
    default_model: str
    available_providers: list[str]
