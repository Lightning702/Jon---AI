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
    code: str = ""


class MediaIn(BaseModel):
    name: str
    mime: str
    data: str


class SendIn(BaseModel):
    peer_id: str
    text: str = ""
    media: MediaIn | None = None
    group_id: str = ""
    reply_to: str = ""


class TypingIn(BaseModel):
    peer_id: str


class GroupIn(BaseModel):
    name: str
    members: list[str]


class ReactIn(BaseModel):
    emoji: str


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
    from app.services.relay_service import get_relay_service

    service = get_p2p_service()
    return {
        "ip": service.local_ip(),
        "unread": service.total_unread(),
        "requests": len(service.requests()) + len(service.group_invites()),
        "queued": service.pending_outbox(),
        "relay": get_relay_service().status(),
    }


@router.get("/peers")
async def peers() -> list[dict]:
    return get_p2p_service().peers()


@router.post("/peers")
async def add_peer(payload: PeerIn) -> dict:
    service = get_p2p_service()
    if payload.code.strip():
        result = await service.add_peer_by_code(payload.code)
    elif payload.name.strip():
        result = await service.add_peer_by_name(payload.name)
    elif payload.ip.strip():
        result = await service.add_peer_by_ip(payload.ip)
    else:
        raise HTTPException(status_code=400, detail="Namen oder Code angeben")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/peers/{peer_id}")
async def delete_peer(peer_id: str) -> dict:
    return {"deleted": get_p2p_service().forget_peer(peer_id)}


@router.get("/requests")
async def requests() -> list[dict]:
    return get_p2p_service().requests()


@router.post("/requests/{peer_id}/accept")
async def accept_request(peer_id: str) -> dict:
    result = get_p2p_service().accept_request(peer_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/requests/{peer_id}/reject")
async def reject_request(peer_id: str) -> dict:
    return get_p2p_service().reject_request(peer_id)


@router.post("/requests/{peer_id}/block")
async def block_peer(peer_id: str) -> dict:
    return get_p2p_service().block_peer(peer_id)


@router.get("/blocked")
async def blocked() -> list[dict]:
    return get_p2p_service().blocked()


@router.post("/blocked/{peer_id}/unblock")
async def unblock(peer_id: str) -> dict:
    return get_p2p_service().unblock_peer(peer_id)


@router.get("/groups")
async def groups() -> list[dict]:
    return get_p2p_service().groups()


@router.post("/groups")
async def create_group(payload: GroupIn) -> dict:
    result = await get_p2p_service().create_group(payload.name, payload.members)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/groups/invites")
async def group_invites() -> list[dict]:
    return get_p2p_service().group_invites()


@router.post("/groups/{group_id}/accept")
async def accept_group(group_id: str) -> dict:
    result = get_p2p_service().accept_group(group_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/groups/{group_id}/reject")
async def reject_group(group_id: str) -> dict:
    return get_p2p_service().reject_group(group_id)


@router.post("/groups/{group_id}/leave")
async def leave_group(group_id: str) -> dict:
    result = await get_p2p_service().leave_group(group_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str) -> dict:
    return {"deleted": get_p2p_service().delete_group(group_id)}


@router.get("/search")
async def search(q: str = "") -> list[dict]:
    return await asyncio.to_thread(get_p2p_service().search, q)


@router.post("/messages/{message_id}/react")
async def react(message_id: str, payload: ReactIn) -> dict:
    result = await get_p2p_service().react(message_id, payload.emoji)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, for_all: bool = False) -> dict:
    result = await get_p2p_service().delete_message(message_id, for_all)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/chats/{chat_id}")
async def clear_chat(chat_id: str) -> dict:
    return {"cleared": await asyncio.to_thread(get_p2p_service().clear_chat, chat_id)}


@router.get("/notifications")
async def notifications(channel: str = "app") -> list[dict]:
    return get_p2p_service().pending_notifications(channel)


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


@router.post("/messages/{message_id}/transcribe")
async def transcribe(message_id: str) -> dict:
    result = await asyncio.to_thread(get_p2p_service().transcribe, message_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/send")
async def send(payload: SendIn) -> dict:
    media = payload.media.model_dump() if payload.media else None
    result = await get_p2p_service().send(
        payload.peer_id, payload.text, media, payload.group_id, payload.reply_to
    )
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
            "public_key": me["public_key"],
        }

    @app.post("/request")
    async def friend_request(request: Request) -> dict:
        service = get_p2p_service()
        if not service.identity()["enabled"]:
            raise HTTPException(status_code=403, detail="Chat ist deaktiviert")
        payload = await request.json()
        sender_ip = request.client.host if request.client else ""
        result = service.receive_request(payload, sender_ip)
        if result.get("error"):
            raise HTTPException(status_code=403, detail=result["error"])
        return result

    @app.post("/typing")
    async def peer_typing(request: Request) -> dict:
        service = get_p2p_service()
        payload = await request.json()
        peer_id = str(payload.get("from_id", "")).strip()
        if peer_id:
            service.note_typing(peer_id)
        return {"ok": True}

    @app.post("/event")
    async def event(request: Request) -> dict:
        service = get_p2p_service()
        if not service.identity()["enabled"]:
            raise HTTPException(status_code=403, detail="Chat ist deaktiviert")
        payload = await request.json()
        sender_ip = request.client.host if request.client else ""
        result = await asyncio.to_thread(service.receive_event, payload, sender_ip)
        if result.get("error") in ("pending", "blocked"):
            raise HTTPException(status_code=403, detail=result["error"])
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

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
        if result.get("error") in ("pending", "blocked"):
            raise HTTPException(status_code=403, detail=result["error"])
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    return app
