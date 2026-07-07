from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.keys import KeyManager
from app.db.database import session_scope
from app.db.models import Conversation
from app.providers.registry import get_registry
from app.schemas import (
    AccountConnectIn,
    AccountModelIn,
    ApproveIn,
    ChatIn,
    ConversationDetail,
    ConversationOut,
    HealthOut,
    ProviderStatus,
    ReminderIn,
    SettingsIn,
    SkillWriteIn,
)
from app.services.account_service import LOCAL_PROVIDERS, SUPPORTED, get_account_service
from app.services.approval_service import get_approval_service
from app.services.chat_service import ChatService
from app.services.reminder_service import get_reminder_service
from app.services.settings_service import get_settings_service
from app.services.skill_service import SkillService
from app.services.system_service import SystemService
from app.services.usage_service import get_usage_service

router = APIRouter(prefix="/api")
_chat_service = ChatService()
_skills = SkillService()
_system = SystemService()


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    settings = get_settings()
    registry = get_registry()
    return HealthOut(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        default_provider=settings.default_provider,
        default_model=settings.default_model,
        available_providers=registry.available(),
    )


_local_probe_cache: dict[str, tuple[float, dict]] = {}


async def _local_status(base_url: str) -> dict:
    now = time.monotonic()
    hit = _local_probe_cache.get(base_url)
    if hit and now - hit[0] < 30:
        return hit[1]
    probe = await asyncio.to_thread(_system.local_llm_status, base_url)
    _local_probe_cache[base_url] = (time.monotonic(), probe)
    return probe


async def _models_for(provider, timeout: float) -> list[str]:
    if provider is None or not provider.available():
        return []
    try:
        return await asyncio.wait_for(provider.list_models(), timeout=timeout)
    except Exception:
        return []


@router.get("/providers", response_model=list[ProviderStatus])
async def providers() -> list[ProviderStatus]:
    registry = get_registry()
    keys = KeyManager()
    timeout = get_settings().models_timeout
    statuses = keys.status()
    model_lists = await asyncio.gather(
        *(
            _models_for(registry.all().get(status.provider), timeout)
            for status in statuses
        )
    )
    return [
        ProviderStatus(
            provider=status.provider,
            configured=status.configured,
            env_var=status.env_var,
            models=models,
        )
        for status, models in zip(statuses, model_lists)
    ]


@router.get("/providers/{name}/models", response_model=list[str])
async def provider_models(name: str) -> list[str]:
    registry = get_registry()
    provider = registry.all().get(name)
    if provider is None:
        raise HTTPException(status_code=404, detail="Unknown provider")
    return await provider.list_models()


@router.post("/chat")
async def chat(payload: ChatIn) -> StreamingResponse:
    async def event_stream():
        async for event in _chat_service.stream(payload):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/approve")
async def approve_tool(payload: ApproveIn) -> dict:
    resolved = get_approval_service().resolve(payload.id, payload.approved)
    return {"status": "ok" if resolved else "unknown"}


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations() -> list[ConversationOut]:
    with session_scope() as session:
        rows = (
            session.query(Conversation)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        return [ConversationOut.model_validate(r) for r in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str) -> ConversationDetail:
    with session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Not found")
        return ConversationDetail.model_validate(conv)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    with session_scope() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Not found")
        session.delete(conv)
    return {"status": "deleted", "id": conversation_id}


@router.get("/skills")
async def list_skills() -> list[dict]:
    return _skills.list()


@router.get("/skills/{name}")
async def read_skill(name: str) -> dict:
    try:
        return _skills.read(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Skill nicht gefunden")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/skills/{name}")
async def write_skill(name: str, payload: SkillWriteIn) -> dict:
    try:
        return _skills.write(name, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/skills/{name}")
async def delete_skill(name: str) -> dict:
    try:
        return {"deleted": _skills.delete(name)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/usage")
async def usage(provider: str | None = None) -> dict:
    return {
        "usage": get_usage_service().summary(provider),
        "note": (
            "Werte werden lokal aus den offiziellen API-Antworten gemessen. "
            "Kosten, Rate-Limits und Restkontingent werden von den meisten APIs "
            "nicht direkt bereitgestellt und daher hier nicht erfunden."
        ),
    }


@router.delete("/usage")
async def reset_usage(provider: str | None = None) -> dict:
    get_usage_service().reset(provider)
    return {"status": "reset"}


@router.get("/accounts")
async def accounts() -> list[dict]:
    registry = get_registry()
    keys = KeyManager()
    account = get_account_service()
    settings = get_settings()
    timeout = settings.models_timeout
    local_urls = {
        "ollama": settings.ollama_base_url,
        "lmstudio": settings.lmstudio_base_url,
    }

    async def build(name: str) -> dict:
        env_configured = keys.env_key_for(name) is not None
        if name in LOCAL_PROVIDERS:
            probe = await _local_status(local_urls[name])
            status = account.status(name, env_configured, probe["reachable"])
            status["models"] = probe["models"]
        else:
            status = account.status(name, env_configured)
            status["models"] = await _models_for(registry.all().get(name), timeout)
        return status

    return list(await asyncio.gather(*(build(name) for name in SUPPORTED)))


@router.post("/accounts/connect")
async def connect_account(payload: AccountConnectIn) -> dict:
    try:
        return get_account_service().connect(
            payload.provider, payload.api_key, payload.default_model
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/accounts/{provider}/default-model")
async def set_account_model(provider: str, payload: AccountModelIn) -> dict:
    return get_account_service().set_default_model(provider, payload.model)


@router.delete("/accounts/{provider}")
async def disconnect_account(provider: str) -> dict:
    return {"disconnected": get_account_service().disconnect(provider)}


@router.get("/settings")
async def get_user_settings() -> dict:
    return get_settings_service().get()


@router.put("/settings")
async def update_user_settings(payload: SettingsIn) -> dict:
    return get_settings_service().update(payload.model_dump(exclude_none=True))


@router.get("/reminders")
async def list_reminders() -> list[dict]:
    return get_reminder_service().list()


@router.post("/reminders")
async def add_reminder(payload: ReminderIn) -> dict:
    return get_reminder_service().add(
        payload.text, payload.time, payload.repeat, payload.phone
    )


@router.get("/reminders/due")
async def due_reminders() -> list[dict]:
    return get_reminder_service().due()


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str) -> dict:
    return {"deleted": get_reminder_service().delete(reminder_id)}
