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
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    seed: int | None = None
    conversation_id: str | None = None
    persist: bool = True
    tool_mode: str = Field(default="ask", pattern="^(ask|allow)$")
    mode: str = Field(default="chat", pattern="^(chat|coding)$")
    persona: str = Field(default="papa", pattern="^(papa|junior)$")
    slot: str = Field(default="", pattern="^(jon|emil)?$")
    workspace: str | None = None
    source: str = ""


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
    auto_failover: bool | None = None
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
    cowork_enabled: bool | None = None
    cowork_context: str | None = None
    cowork_app: str | None = None
    quickwrite_enabled: bool | None = None
    timeline_enabled: bool | None = None
    routine_enabled: bool | None = None
    telegram_morning: bool | None = None
    telegram_morning_time: str | None = None
    pet_roam: bool | None = None
    pet_companion: str | None = None
    wake_sensitivity: str | None = None


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


class DownloadAnalyzeIn(BaseModel):
    url: str


class DownloadStartIn(BaseModel):
    url: str
    format: str = Field(default="mp4", pattern="^(mp4|mp3)$")
    quality: str = Field(default="best", pattern="^(best|1080|720|480)$")
    title: str = ""


class FocusStartIn(BaseModel):
    minutes: int = 25
    goal: str = ""


class CoworkAnswerIn(BaseModel):
    accept: bool


class TimelineSearchIn(BaseModel):
    query: str = ""
    day: str = ""


class TimelineDescribeIn(BaseModel):
    file: str


class RoutineActionIn(BaseModel):
    id: str


class ShowIn(BaseModel):
    provider: str | None = None
    model: str | None = None


class QuickwriteApplyIn(BaseModel):
    mode: str = Field(default="verbessern")


class MediaDownloadIn(BaseModel):
    query: str


class GameCommandIn(BaseModel):
    message: str
    x: float = 0
    y: float = 0
    z: float = 0


class JournalAddIn(BaseModel):
    text: str


class JournalAskIn(BaseModel):
    query: str


class CleanupPreviewIn(BaseModel):
    folder: str = "downloads"
    by: str = Field(default="typ", pattern="^(typ|datum)$")


class CleanupApplyIn(BaseModel):
    plan: str


class RecipeSuggestIn(BaseModel):
    ingredients: str


class RecipeMakeIn(BaseModel):
    dish: str


class FlashcardsGenIn(BaseModel):
    topic: str


class FlashcardsAnswerIn(BaseModel):
    deck: str
    card: str
    answer: str = ""


class PomodoroStartIn(BaseModel):
    work: int = 25
    brk: int = 5
    rounds: int = 4
    goal: str = ""


class NoteAddIn(BaseModel):
    text: str = ""
    color: str = "gold"


class NoteUpdateIn(BaseModel):
    id: str
    text: str | None = None
    color: str | None = None
    pinned: bool | None = None
    done: bool | None = None


class VaultPasswordIn(BaseModel):
    password: str


class VaultAddIn(BaseModel):
    title: str
    username: str = ""
    secret: str


class VaultGenIn(BaseModel):
    length: int = 20
    symbols: bool = True


class SearchIn(BaseModel):
    query: str


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


class TrashRestoreIn(BaseModel):
    id: str


class PairRequestIn(BaseModel):
    name: str = "Geraet"


class PairClaimIn(BaseModel):
    request_id: str
    code: str


class PairDenyIn(BaseModel):
    request_id: str


class CalendarAddIn(BaseModel):
    title: str
    date: str
    time: str = ""
    duration_minutes: int = 0
    note: str = ""
    kind: str = "termin"


class CalendarUpdateIn(BaseModel):
    title: str | None = None
    date: str | None = None
    time: str | None = None
    duration_minutes: int | None = None
    note: str | None = None
    kind: str | None = None
    done: bool | None = None
