from __future__ import annotations

import json
import socket

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.multiplayer_service import (
    GAMES,
    PROTOCOL_VERSION,
    WebSocketTransport,
    get_multiplayer_service,
)

router = APIRouter(prefix="/api/mp", tags=["multiplayer"])

MP_TCP_PORT = 8759


class CreateIn(BaseModel):
    game: str = "blockwelt"
    name: str = "Spieler"
    model: str = "default"
    seed: int | None = None
    max_players: int = Field(default=2, ge=2, le=8)
    spawn: dict | None = None


class JoinIn(BaseModel):
    code: str
    name: str = "Spieler"
    model: str = "default"


def _local_addresses() -> list[str]:
    hosts: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            address = info[4][0]
            if address not in hosts and not address.startswith("127."):
                hosts.append(address)
    except Exception:
        pass
    return hosts


@router.get("/status")
async def mp_status() -> dict:
    settings = get_settings()
    service = get_multiplayer_service()
    return {
        **service.status(),
        "version": settings.app_version,
        "tcp_port": MP_TCP_PORT,
        "http_port": settings.port,
        "lan": settings.jon_lan,
        "addresses": _local_addresses(),
    }


@router.get("/info")
async def mp_info() -> dict:
    settings = get_settings()
    return {
        "protocol": PROTOCOL_VERSION,
        "games": sorted(GAMES),
        "http_port": settings.port,
        "tcp_port": MP_TCP_PORT,
        "addresses": _local_addresses(),
        "hint": (
            "Weltweit spielen: Beide Spieler verbinden sich mit derselben "
            "Jon-Adresse. Entweder Portfreigabe fuer Port "
            f"{settings.port} (Browser) und {MP_TCP_PORT} (ECHO/AETHERIA), "
            "oder ein oeffentlich erreichbarer Jon-Server. Im Beitrittsfeld "
            "sind CODE und CODE@host:port erlaubt."
        ),
    }


@router.post("/create")
async def mp_create(payload: CreateIn) -> dict:
    service = get_multiplayer_service()
    try:
        lobby, member = service.create_lobby(
            payload.game,
            payload.name,
            payload.model,
            seed=payload.seed,
            max_players=payload.max_players,
            spawn=payload.spawn,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"code": lobby.code, "token": member.token, "lobby": lobby.summary()}


@router.post("/join")
async def mp_join(payload: JoinIn) -> dict:
    service = get_multiplayer_service()
    try:
        lobby, member = service.join_lobby(payload.code, payload.name, payload.model)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"code": lobby.code, "token": member.token, "lobby": lobby.summary()}


@router.get("/lobby/{code}")
async def mp_lobby(code: str) -> dict:
    info = get_multiplayer_service().lobby_info(code)
    if info is None:
        raise HTTPException(status_code=404, detail="Code nicht gefunden")
    return info


@router.websocket("/ws")
async def mp_socket(socket: WebSocket) -> None:
    await socket.accept()
    service = get_multiplayer_service()
    await service.start()
    transport = WebSocketTransport(socket)
    lobby = None
    member = None
    try:
        while True:
            raw = await socket.receive_text()
            try:
                message = json.loads(raw)
            except Exception:
                continue
            if not isinstance(message, dict):
                continue
            if lobby is None or member is None:
                pair = await service.handshake(message, transport)
                if pair is None:
                    await transport.send(
                        {"t": "error", "code": "handshake", "msg": "Anmeldung fehlgeschlagen"}
                    )
                    continue
                lobby, member = pair
                continue
            await service.handle(lobby, member, message)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if lobby is not None and member is not None and member.transport is transport:
            await service.detach(lobby, member)
