from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.media_service import get_media_service
from app.services.premium import PremiumNoetig

router = APIRouter(prefix="/api/media")


class MediaTask(BaseModel):
    kind: str = Field(pattern="^(transcribe|youtube|speech)$")
    upload_id: str = ""
    url: str = Field(default="", max_length=2000)
    text: str = Field(default="", max_length=80000)
    voice: str = "de-DE-ConradNeural"
    summarize: bool = False


@router.post("/uploads")
async def upload(request: Request, name: str = "audio.mp3") -> dict:
    try:
        return await get_media_service().upload(name, request.stream())
    except PremiumNoetig:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/jobs")
async def start(payload: MediaTask) -> dict:
    try:
        return get_media_service().start(**payload.model_dump())
    except PremiumNoetig:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/jobs")
async def jobs() -> list[dict]:
    service = get_media_service()
    return [{key: value[key] for key in ("id", "title", "kind", "status", "progress", "created_at")} for value in sorted(service.jobs.values(), key=lambda x: x["created_at"], reverse=True)[:50]]


@router.get("/jobs/{key}")
async def job(key: str) -> dict:
    try:
        return get_media_service().get(key)
    except KeyError:
        raise HTTPException(404, "Medienauftrag nicht gefunden.")


@router.post("/jobs/{key}/cancel")
async def cancel(key: str) -> dict:
    try:
        return await get_media_service().cancel(key)
    except KeyError:
        raise HTTPException(404, "Medienauftrag nicht gefunden.")


@router.get("/jobs/{key}/files/{name}")
async def file(key: str, name: str):
    try:
        path = get_media_service().file(key, name)
    except (KeyError, ValueError):
        raise HTTPException(404, "Datei nicht gefunden.")
    return FileResponse(path, filename=name, media_type="audio/mpeg" if name.endswith(".mp3") else "text/plain; charset=utf-8")
