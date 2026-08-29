from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas import StudioConnectIn, StudioGenerateIn
from app.services.studio_service import StudioError, get_studio_service

router = APIRouter(prefix="/api/studio", tags=["studio"])


@router.get("/config")
async def studio_config() -> dict:
    return get_studio_service().config()


@router.post("/connect")
async def studio_connect(payload: StudioConnectIn) -> dict:
    try:
        return get_studio_service().connect(
            payload.provider,
            payload.api_key or "",
            payload.base_url or "",
            payload.model or "",
            payload.video_model or "",
            payload.size or "",
        )
    except StudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/connect/{provider}")
async def studio_disconnect(provider: str) -> dict:
    return get_studio_service().disconnect(provider)


@router.post("/generate")
async def studio_generate(payload: StudioGenerateIn) -> dict:
    try:
        return await get_studio_service().generate(
            payload.prompt,
            payload.kind,
            payload.model or "",
            payload.size or "",
            payload.negative or "",
            payload.provider or "",
            payload.image or "",
        )
    except StudioError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/gallery")
async def studio_gallery() -> dict:
    return {"galerie": get_studio_service().gallery()}


@router.delete("/gallery/{entry_id}")
async def studio_delete(entry_id: str) -> dict:
    try:
        return get_studio_service().delete(entry_id)
    except StudioError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/file/{name}")
async def studio_file(name: str) -> FileResponse:
    try:
        path = get_studio_service().file(name)
    except StudioError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})
