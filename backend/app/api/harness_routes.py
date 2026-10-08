from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.harness import get_harness_service
from app.services.harness.messages import handle, selection
from app.services.harness.vorschau import get_vorschau
from app.services.mini_jon_agent import get_mini_jon_agent
from app.services.premium import PremiumNoetig

router = APIRouter(prefix="/api")


class Freigabe(BaseModel):
    alles: bool


@router.get("/harness/freigabe")
async def freigabe_stand() -> dict:
    return {"alles": get_harness_service().alles_erlaubt()}


@router.post("/harness/freigabe")
async def freigabe_setzen(daten: Freigabe) -> dict:
    from app.services.settings_service import get_settings_service

    get_settings_service().update({"harness_alles_erlauben": daten.alles})
    return {"alles": get_harness_service().alles_erlaubt()}


@router.get("/mini-jon/memories")
async def daily_memories() -> dict:
    from app.services.daily_memory import get_daily_memory

    return {"items": get_daily_memory().list()}


@router.delete("/mini-jon/memories/{key}")
async def delete_daily_memory(key: str) -> dict:
    from app.services.daily_memory import get_daily_memory

    if not get_daily_memory().delete(key):
        raise HTTPException(404, "Erinnerung nicht gefunden")
    return {"ok": True}


class StartTask(BaseModel):
    goal: str = Field(min_length=1, max_length=12000)
    root: str = ""
    modus: str = Field(default="code", pattern="^(code|allgemein)$")
    source: str = Field(default="app", pattern="^(app|minijon|terminal)$")
    provider: str = ""
    model: str = ""
    max_steps: int = Field(default=0, ge=0)
    companion: bool = False
    thread: str = Field(default="", max_length=40, pattern="^[a-f0-9]*$")


class Approval(BaseModel):
    approval_id: str
    allow: bool


class Message(BaseModel):
    text: str = Field(max_length=12000)
    source: str = "minijon"


def task_or_404(task_id: str) -> dict:
    try:
        return get_harness_service().get(task_id)
    except KeyError:
        raise HTTPException(404, "Aufgabe nicht gefunden")


@router.post("/harness/tasks")
async def start(payload: StartTask) -> dict:
    try:
        return get_harness_service().start(**payload.model_dump())
    except PremiumNoetig:
        raise
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc))


@router.get("/harness/tasks")
async def tasks(source: str = "", brief: bool = False) -> list[dict]:
    values = get_harness_service().list(source)
    if brief:
        return [{**{key: task[key] for key in ("id", "goal", "root", "source", "status", "step", "created_at", "updated_at")}, "thread": task.get("thread") or task["id"]} for task in values]
    return values


@router.get("/harness/threads")
async def threads(source: str = "") -> list[dict]:
    return get_harness_service().sitzungen(source)


@router.get("/harness/threads/{thread_id}")
async def thread(thread_id: str) -> dict:
    tasks = get_harness_service().sitzung(thread_id)
    if not tasks:
        raise HTTPException(404, "Sitzung nicht gefunden")
    return {"id": thread_id, "root": tasks[0]["root"], "title": tasks[0]["goal"][:200], "tasks": tasks}


@router.get("/harness/tasks/{task_id}")
async def task(task_id: str) -> dict:
    return task_or_404(task_id)


@router.post("/harness/tasks/{task_id}/cancel")
async def cancel(task_id: str) -> dict:
    task_or_404(task_id)
    return await get_harness_service().cancel(task_id)


@router.post("/harness/tasks/{task_id}/approve")
async def approve(task_id: str, payload: Approval) -> dict:
    task_or_404(task_id)
    try:
        return get_harness_service().approve(task_id, payload.approval_id, payload.allow)
    except PremiumNoetig:
        raise
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.get("/harness/tasks/{task_id}/events")
async def events(task_id: str, after: int = 0):
    task_or_404(task_id)

    async def stream():
        async for event in get_harness_service().stream(task_id, after):
            yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/harness/message")
async def message(payload: Message) -> dict:
    if payload.source not in {"app", "minijon"}:
        raise HTTPException(400, "Ungültiger Kanal")
    return await handle(payload.text, payload.source) or {"handled": False}


@router.get("/mini-jon/agent")
async def agent_state() -> dict:
    agent = get_mini_jon_agent()
    from app.services.mini_jon_screen import destination

    return {"config": dict(agent.config), "state": dict(agent.state), "destination": destination()}


@router.put("/mini-jon/agent")
async def agent_config(payload: dict) -> dict:
    try:
        return get_mini_jon_agent().configure(payload)
    except PremiumNoetig:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/mini-jon/agent/events")
async def agent_events():
    agent = get_mini_jon_agent()

    async def stream():
        while True:
            agent.changed.clear()
            yield f'data: {json.dumps(agent.state, ensure_ascii=False)}\n\n'
            try:
                await asyncio.wait_for(agent.changed.wait(), 20)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


class ProjectSelection(BaseModel):
    root: str
    source: str = Field(default="minijon", pattern="^(app|minijon)$")


@router.get("/harness/project")
async def selected_project(source: str = "minijon") -> dict:
    if source not in {"app", "minijon"}:
        raise HTTPException(400, "Ungültiger Kanal")
    return {"root": selection(source)}


@router.post("/harness/project")
async def select_project(payload: ProjectSelection) -> dict:
    from app.services.project_service import get_project_service

    project = get_project_service().find_by_root(payload.root)
    if not project:
        raise HTTPException(400, "Bitte das Projekt zuerst in Jon speichern.")
    selection(payload.source, project["root"])
    return {"root": project["root"]}


class ScreenQuestion(BaseModel):
    question: str = Field(default="Was ist zu sehen und welche Hilfe ist sinnvoll?", max_length=4000)


@router.post("/mini-jon/screen")
async def screen(payload: ScreenQuestion) -> dict:
    from app.services.mini_jon_screen import analyze

    try:
        return await analyze(get_mini_jon_agent(), payload.question)
    except PremiumNoetig:
        raise
    except (ValueError, OSError, TimeoutError) as exc:
        raise HTTPException(400, str(exc) or "Bildschirmanalyse hat zu lange gedauert.")
    except PremiumNoetig:
        raise
    except Exception:
        raise HTTPException(502, "Das Vision-Modell ist nicht erreichbar oder unterstützt keine Bilder. Prüfe Anbieter und Vision-Modell.")


class PreviewRequest(BaseModel):
    root: str = Field(min_length=1, max_length=4000)


def preview_root(root: str) -> Path:
    from app.services.premium import get_premium
    from app.services.project_service import get_project_service

    if not get_premium().premium():
        from app.services.premium import PremiumNoetig

        raise PremiumNoetig("harness", "Die Projektvorschau im Harness gibt es mit Jon Premium.")

    project = get_project_service().find_by_root(root)
    if not project:
        raise HTTPException(400, "Bitte das Projekt zuerst in Jon speichern.")
    pfad = Path(project["root"]).expanduser().resolve()
    if not pfad.is_dir():
        raise HTTPException(400, "Der Projektordner existiert nicht mehr.")
    return pfad


@router.get("/harness/preview")
async def preview_state(root: str) -> dict:
    return get_vorschau().zustand(preview_root(root))


@router.post("/harness/preview")
async def preview_start(payload: PreviewRequest) -> dict:
    try:
        return await get_vorschau().starten(preview_root(payload.root))
    except PremiumNoetig:
        raise
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc))


@router.post("/harness/preview/stop")
async def preview_stop(payload: PreviewRequest) -> dict:
    return await get_vorschau().stoppen(preview_root(payload.root))
