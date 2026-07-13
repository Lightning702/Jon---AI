from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Request
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
    AttachmentIn,
    CapsuleIn,
    ChatIn,
    ConversationDetail,
    ConversationOut,
    DreamIn,
    HealthOut,
    HumanizeIn,
    KnowledgeLearnIn,
    KnowledgeSearchIn,
    ProviderStatus,
    ReminderIn,
    ScreenObserveIn,
    SettingsIn,
    SimulateIn,
    SkillWriteIn,
    SnapshotIn,
    TaskIn,
    TeamIn,
    WatcherIn,
    WebcamIn,
)
from app.services.account_service import LOCAL_PROVIDERS, SUPPORTED, get_account_service
from app.services.approval_service import get_approval_service
from app.services.attachment_service import get_attachment_service
from app.services.briefing_service import get_briefing_service
from app.services.capsule_service import get_capsule_service
from app.services.chat_service import ChatService
from app.services.clipboard_service import get_clipboard_service
from app.services.dream_service import get_dream_service
from app.services.knowledge_service import get_knowledge_service
from app.services.persona_service import get_persona_service
from app.services.reminder_service import get_reminder_service
from app.services.screen_service import get_screen_service
from app.services.settings_service import get_settings_service
from app.services.simulation_service import get_simulation_service
from app.services.skill_service import SkillService
from app.services.system_service import SystemService
from app.services.task_service import get_task_service
from app.services.team_service import TEAM, get_team_service
from app.services.timetravel_service import get_timetravel_service
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


@router.get("/persona")
async def persona() -> dict:
    return get_persona_service().state()


@router.get("/persona/memory")
async def persona_memory() -> dict:
    return {"memory": get_persona_service().read_memory_file(max_chars=20000)}


@router.get("/team/roster")
async def team_roster() -> list[dict]:
    return [
        {"key": k, "name": v["name"], "role": v["role"], "emoji": v["emoji"]}
        for k, v in TEAM.items()
    ]


@router.post("/team")
async def team(payload: TeamIn) -> dict:
    return await get_team_service().discuss(
        payload.topic, payload.members, payload.provider, payload.model
    )


@router.post("/simulate")
async def simulate(payload: SimulateIn) -> dict:
    return await get_simulation_service().simulate(
        payload.scenario, payload.context, payload.provider, payload.model
    )


@router.post("/humanize")
async def humanize(payload: HumanizeIn) -> dict:
    from app.services.humanize_service import humanize as run_humanize

    result = await run_humanize(
        payload.text,
        payload.style,
        payload.strength,
        payload.provider,
        payload.model,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/humanize/score")
async def humanize_score(payload: HumanizeIn) -> dict:
    from app.services.humanize_service import score

    return score(payload.text)


@router.get("/snapshots")
async def list_snapshots() -> list[dict]:
    return get_timetravel_service().list()


@router.post("/snapshots")
async def create_snapshot(payload: SnapshotIn) -> dict:
    return get_timetravel_service().snapshot(
        payload.label, payload.workspace, payload.note, kind="manual"
    )


@router.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str) -> dict:
    try:
        return get_timetravel_service().restore(snapshot_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str) -> dict:
    return {"deleted": get_timetravel_service().delete(snapshot_id)}


@router.get("/dreams")
async def list_dreams() -> list[dict]:
    return get_dream_service().list()


@router.post("/dreams")
async def add_dream(payload: DreamIn) -> dict:
    return get_dream_service().add(payload.task)


@router.post("/dreams/run")
async def run_dreams(payload: DreamIn | None = None) -> dict:
    provider = payload.provider if payload else None
    model = payload.model if payload else None
    return await get_dream_service().run_pending(provider, model)


@router.get("/dreams/reports")
async def dream_reports() -> list[dict]:
    return get_dream_service().unseen_reports()


@router.post("/screen/observe")
async def screen_observe(payload: ScreenObserveIn) -> dict:
    return await get_screen_service().observe(payload.provider, payload.model)


@router.post("/webcam/observe")
async def webcam_observe(payload: WebcamIn | None = None) -> dict:
    from app.services.webcam_service import get_webcam_service

    return await get_webcam_service().describe(payload.question if payload else "")


@router.delete("/dreams/{task_id}")
async def delete_dream(task_id: str) -> dict:
    return {"deleted": get_dream_service().delete(task_id)}


@router.get("/briefing")
async def briefing() -> dict:
    return await asyncio.to_thread(get_briefing_service().build)


@router.get("/knowledge")
async def knowledge_docs() -> list[dict]:
    return get_knowledge_service().list()


@router.post("/knowledge/learn")
async def knowledge_learn(payload: KnowledgeLearnIn) -> dict:
    svc = get_knowledge_service()
    if payload.path.strip():
        return await asyncio.to_thread(svc.learn_path, payload.path)
    if payload.text.strip():
        return await asyncio.to_thread(svc.learn_text, payload.text, payload.title)
    raise HTTPException(status_code=400, detail="path oder text angeben")


@router.post("/knowledge/search")
async def knowledge_search(payload: KnowledgeSearchIn) -> list[dict]:
    return await asyncio.to_thread(
        get_knowledge_service().search, payload.query, payload.max_results
    )


@router.delete("/knowledge/{ref}")
async def knowledge_forget(ref: str) -> dict:
    return {"removed": get_knowledge_service().forget(ref)}


@router.get("/clipboard")
async def clipboard_history(query: str = "") -> list[dict]:
    return get_clipboard_service().list(query)


@router.post("/clipboard/{entry_id}/restore")
async def clipboard_restore(entry_id: str) -> dict:
    return {"restored": get_clipboard_service().restore(entry_id)}


@router.delete("/clipboard/{entry_id}")
async def clipboard_delete(entry_id: str) -> dict:
    return {"deleted": get_clipboard_service().delete(entry_id)}


@router.delete("/clipboard")
async def clipboard_clear() -> dict:
    return {"cleared": get_clipboard_service().clear()}


@router.get("/tasks")
async def list_tasks() -> list[dict]:
    return get_task_service().list()


@router.post("/tasks")
async def add_task(payload: TaskIn) -> dict:
    result = get_task_service().add(payload.task, payload.time, payload.repeat)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/tasks/reports")
async def task_reports() -> list[dict]:
    return get_task_service().unseen_reports()


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: str) -> dict:
    result = await get_task_service().run_now(task_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict:
    return {"deleted": get_task_service().delete(task_id)}


@router.get("/capsules")
async def list_capsules() -> list[dict]:
    return get_capsule_service().list()


@router.post("/capsules")
async def add_capsule(payload: CapsuleIn) -> dict:
    result = get_capsule_service().add(payload.text, payload.date)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/capsules/due")
async def due_capsules() -> list[dict]:
    return get_capsule_service().due()


@router.delete("/capsules/{capsule_id}")
async def delete_capsule(capsule_id: str) -> dict:
    return {"deleted": get_capsule_service().delete(capsule_id)}


@router.post("/attachments/extract")
async def extract_attachment(payload: AttachmentIn) -> dict:
    result = await get_attachment_service().extract(
        payload.name, payload.mime, payload.data, payload.provider
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/weekly")
async def weekly() -> dict:
    return await asyncio.to_thread(get_briefing_service().weekly_data)


@router.get("/update")
async def update_check() -> dict:
    from app.services.update_service import check_update

    return await asyncio.to_thread(check_update)


@router.get("/backup/export")
async def backup_export(include_keys: bool = False):
    from fastapi.responses import Response

    from app.services.backup_service import export_backup

    raw = await asyncio.to_thread(export_backup, include_keys)
    stamp = time.strftime("%Y-%m-%d")
    return Response(
        content=raw,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="jon-backup-{stamp}.zip"'
        },
    )


@router.post("/backup/import")
async def backup_import(request: Request) -> dict:
    from app.services.backup_service import import_backup

    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Keine Datei")
    result = await asyncio.to_thread(import_backup, raw)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/watchers")
async def list_watchers() -> list[dict]:
    from app.services.watcher_service import get_watcher_service

    return get_watcher_service().list()


@router.post("/watchers")
async def add_watcher(payload: WatcherIn) -> dict:
    from app.services.watcher_service import get_watcher_service

    result = get_watcher_service().add(payload.path, payload.task)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/watchers/reports")
async def watcher_reports() -> list[dict]:
    from app.services.watcher_service import get_watcher_service

    return get_watcher_service().unseen_reports()


@router.delete("/watchers/{watcher_id}")
async def delete_watcher(watcher_id: str) -> dict:
    from app.services.watcher_service import get_watcher_service

    return {"deleted": get_watcher_service().delete(watcher_id)}
