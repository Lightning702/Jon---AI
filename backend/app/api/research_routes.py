from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import ResearchControlIn, ResearchStartIn
from app.services.research import get_research_service

router = APIRouter(prefix="/api/research")


@router.get("/tasks")
async def research_tasks() -> dict:
    service = get_research_service()
    return {"aufgaben": service.list(), "aktiv": service.active()}


@router.post("/start")
async def research_start(payload: ResearchStartIn) -> dict:
    try:
        return await get_research_service().start(
            payload.topic,
            payload.minutes,
            payload.provider,
            payload.model,
            payload.depth,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/tasks/{task_id}")
async def research_task(task_id: str) -> dict:
    try:
        return get_research_service().get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Research-Auftrag nicht gefunden")


@router.post("/tasks/{task_id}/control")
async def research_control(task_id: str, payload: ResearchControlIn) -> dict:
    service = get_research_service()
    try:
        if payload.action == "pause":
            return service.pause(task_id)
        if payload.action == "resume":
            return service.resume(task_id)
        if payload.action == "resume_task":
            return await service.resume_task(task_id)
        return service.stop(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Research-Auftrag läuft nicht mehr")


@router.delete("/tasks/{task_id}")
async def research_delete(task_id: str) -> dict:
    return {"deleted": get_research_service().delete(task_id)}


@router.get("/tasks/{task_id}/files")
async def research_files(task_id: str) -> dict:
    try:
        return {"dateien": get_research_service().files(task_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Research-Auftrag nicht gefunden")


@router.get("/tasks/{task_id}/files/{name}")
async def research_file(task_id: str, name: str) -> dict:
    try:
        return {"name": name, "inhalt": get_research_service().read_file(task_id, name)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Research-Auftrag nicht gefunden")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")


@router.get("/tasks/{task_id}/stream")
async def research_stream(task_id: str) -> StreamingResponse:
    service = get_research_service()
    try:
        service.get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Research-Auftrag nicht gefunden")

    async def event_stream():
        try:
            async for snapshot in service.stream(task_id):
                yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
