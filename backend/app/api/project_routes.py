from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas import (
    ProjectAddIn,
    ProjectChangesIn,
    ProjectNoteIn,
    ProjectPathIn,
    ProjectUpdateIn,
)
from app.services.project_service import (
    ProjectError,
    analyze,
    changes,
    get_project_service,
    git_diff,
    git_status,
    snapshot,
)

router = APIRouter(prefix="/api/projects")


@router.get("")
async def list_projects() -> list[dict]:
    return get_project_service().list()


@router.post("")
async def add_project(payload: ProjectAddIn) -> dict:
    try:
        return await asyncio.to_thread(
            get_project_service().add, payload.root, payload.name, payload.note
        )
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/analyze")
async def analyze_project(root: str) -> dict:
    try:
        return await asyncio.to_thread(analyze, root)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analyse fehlgeschlagen: {exc}")


@router.get("/git")
async def project_git(root: str, mode: str = "status", staged: bool = False) -> dict:
    try:
        if mode == "diff":
            return await asyncio.to_thread(git_diff, root, staged)
        return await asyncio.to_thread(git_status, root)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/snapshot")
async def project_snapshot(payload: ProjectPathIn) -> dict:
    try:
        return await asyncio.to_thread(snapshot, payload.root)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/changes")
async def project_changes(payload: ProjectChangesIn) -> dict:
    try:
        return await asyncio.to_thread(changes, payload.root, payload.snapshot)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict:
    entry = get_project_service().get(project_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return entry


@router.put("/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdateIn) -> dict:
    try:
        return get_project_service().update(
            project_id, payload.model_dump(exclude_none=True)
        )
    except ProjectError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{project_id}/note")
async def note_project(project_id: str, payload: ProjectNoteIn) -> dict:
    try:
        return get_project_service().remember(project_id, payload.note)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{project_id}/open")
async def open_project(project_id: str) -> dict:
    try:
        return get_project_service().touch(project_id)
    except ProjectError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{project_id}")
async def delete_project(project_id: str) -> dict:
    return {"geloescht": get_project_service().delete(project_id)}
