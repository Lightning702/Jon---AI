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
    max_tokens: int | None = None
    seed: int | None = None
    conversation_id: str | None = None
    persist: bool = True
    tool_mode: str = Field(default="ask", pattern="^(ask|allow)$")
    mode: str = Field(default="chat", pattern="^(chat|coding)$")
    persona: str = Field(default="papa", pattern="^(papa|junior)$")
    workspace: str | None = None


class ApproveIn(BaseModel):
    id: str
    approved: bool


class SkillWriteIn(BaseModel):
    content: str


class AccountConnectIn(BaseModel):
    provider: str
    api_key: str
    default_model: str | None = None


class AccountModelIn(BaseModel):
    model: str


class SettingsIn(BaseModel):
    custom_prompt: str | None = None
    prompt_mode: str | None = None
    tool_mode: str | None = None
    personality: bool | None = None
    provider: str | None = None
    model: str | None = None
    theme: str | None = None
    pet_accent: str | None = None
    pet_face: str | None = None
    pet_cheeks: bool | None = None
    pet_scale: float | None = None
    pet_eyes: str | None = None


class ReminderIn(BaseModel):
    text: str
    time: str = ""
    repeat: str = "daily"
    phone: str = ""


class TeamIn(BaseModel):
    topic: str
    members: list[str] | None = None
    provider: str | None = None
    model: str | None = None


class SimulateIn(BaseModel):
    scenario: str
    context: str = ""
    provider: str | None = None
    model: str | None = None


class SnapshotIn(BaseModel):
    label: str
    workspace: str | None = None
    note: str = ""


class DreamIn(BaseModel):
    task: str
    provider: str | None = None
    model: str | None = None


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
