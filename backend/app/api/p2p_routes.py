from __future__ import annotations

import asyncio

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.p2p_service import get_p2p_service

router = APIRouter(prefix="/api/p2p")


class ProfileIn(BaseModel):
    name: str
    avatar: str = ""


class PeerIn(BaseModel):
    name: str = ""
    ip: str = ""


class MediaIn(BaseModel):
    name: str
    mime: str
    data: str


class SendIn(BaseModel):
    peer_id: str
    text: str = ""
    media: MediaIn | None = None


class TypingIn(BaseModel):
    peer_id: str


@router.get("/me")
async def me() -> dict:
    return get_p2p_service().identity()


@router.put("/me")
async def set_me(payload: ProfileIn) -> dict:
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    result = await get_p2p_service().set_profile_checked(payload.name, payload.avatar)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/info")
async def info() -> dict:
    service = get_p2p_service()
    return {"ip": service.local_ip(), "unread": service.unread_count()}


@router.get("/peers")
async def peers() -> list[dict]:
    return get_p2p_service().peers()


@router.post("/peers")
async def add_peer(payload: PeerIn) -> dict:
    service = get_p2p_service()
    if payload.name.strip():
        result = await service.add_peer_by_name(payload.name)
    elif payload.ip.strip():
        result = await service.add_peer_by_ip(payload.ip)
    else:
        raise HTTPException(status_code=400, detail="Namen angeben")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/peers/{peer_id}")
async def delete_peer(peer_id: str) -> dict:
    return {"deleted": get_p2p_service().forget_peer(peer_id)}


@router.get("/notifications")
async def notifications() -> list[dict]:
    return get_p2p_service().pending_notifications()


@router.post("/typing")
async def typing(payload: TypingIn) -> dict:
    await get_p2p_service().send_typing(payload.peer_id)
    return {"ok": True}


@router.get("/typing")
async def typing_status() -> dict:
    return {"typing": get_p2p_service().typing_peers()}


@router.get("/messages/{peer_id}")
async def messages(peer_id: str) -> list[dict]:
    service = get_p2p_service()
    result = service.messages(peer_id)
    service.mark_seen(peer_id)
    return result


@router.post("/send")
async def send(payload: SendIn) -> dict:
    media = payload.media.model_dump() if payload.media else None
    result = await get_p2p_service().send(payload.peer_id, payload.text, media)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/media/{message_id}")
async def media(message_id: str):
    found = get_p2p_service().media_path(message_id)
    if found is None or not found[0].exists():
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    path, mime = found
    return FileResponse(str(path), media_type=mime)


def create_chat_app() -> FastAPI:
    app = FastAPI(title="Jon Chat", docs_url=None, redoc_url=None)

    @app.get("/ping")
    async def ping() -> dict:
        from app.services.p2p_service import CHAT_PORT

        me = get_p2p_service().identity()
        return {
            "id": me["id"],
            "name": me["name"],
            "avatar": me["avatar"],
            "port": CHAT_PORT,
        }

    @app.post("/typing")
    async def peer_typing(request: Request) -> dict:
        service = get_p2p_service()
        if not service.identity()["enabled"]:
            raise HTTPException(status_code=403, detail="Chat ist deaktiviert")
        payload = await request.json()
        peer_id = str(payload.get("from_id", "")).strip()
        if peer_id:
            service.note_typing(peer_id)
        return {"ok": True}

    @app.post("/inbox")
    async def inbox(request: Request) -> dict:
        service = get_p2p_service()
        if not service.identity()["enabled"]:
            raise HTTPException(status_code=403, detail="Chat ist deaktiviert")
        payload = await request.json()
        sender_ip = request.client.host if request.client else ""
        try:
            result = await asyncio.to_thread(service.receive, payload, sender_ip)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    return app
