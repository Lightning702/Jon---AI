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
    dream_auto: bool | None = None
    dream_idle_minutes: int | None = None
    vision_model: str | None = None
    briefing_city: str | None = None
    clipboard_history: bool | None = None
    webcam_enabled: bool | None = None
    mail_imap_host: str | None = None
    mail_imap_user: str | None = None
    mail_imap_password: str | None = None
    mail_smtp_host: str | None = None
    mail_smtp_port: int | None = None
    calendar_ics_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_provider: str | None = None
    telegram_model: str | None = None
    pet_provider: str | None = None
    pet_model: str | None = None
    relay_enabled: bool | None = None
    relay_broker: str | None = None
    relay_port: int | None = None
    ha_url: str | None = None
    ha_token: str | None = None
    natural_voice: bool | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None


class WatcherIn(BaseModel):
    path: str
    task: str


class ScreenObserveIn(BaseModel):
    provider: str | None = None
    model: str | None = None


class WebcamIn(BaseModel):
    question: str = ""


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


class HumanizeIn(BaseModel):
    text: str
    style: str = "neutral"
    strength: int = 2
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


class KnowledgeLearnIn(BaseModel):
    path: str = ""
    text: str = ""
    title: str = ""


class KnowledgeSearchIn(BaseModel):
    query: str
    max_results: int = 6


class TaskIn(BaseModel):
    task: str
    time: str
    repeat: str = "daily"


class CapsuleIn(BaseModel):
    text: str
    date: str


class AttachmentIn(BaseModel):
    name: str
    mime: str = ""
    data: str
    provider: str | None = None


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
