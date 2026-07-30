from __future__ import annotations

import json
import socket
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
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
MP_WS_PORT = 8760
GAME_PAGE = Path(__file__).resolve().parents[1] / "static" / "blockwelt.html"


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


def _invite_host() -> str:
    addresses = _local_addresses()
    return addresses[0] if addresses else "127.0.0.1"


@router.get("/status")
async def mp_status() -> dict:
    settings = get_settings()
    service = get_multiplayer_service()
    return {
        **service.status(),
        "version": settings.app_version,
        "tcp_port": MP_TCP_PORT,
        "ws_port": MP_WS_PORT,
        "http_port": settings.port,
        "lan": settings.jon_lan,
        "addresses": _local_addresses(),
        "invite_host": _invite_host(),
    }


@router.get("/info")
async def mp_info() -> dict:
    settings = get_settings()
    return {
        "protocol": PROTOCOL_VERSION,
        "games": sorted(GAMES),
        "http_port": settings.port,
        "tcp_port": MP_TCP_PORT,
        "ws_port": MP_WS_PORT,
        "addresses": _local_addresses(),
        "invite_host": _invite_host(),
        "hint": (
            "Weltweit spielen: Der Gastgeber gibt CODE@adresse weiter. Der "
            f"Koop-Port {MP_WS_PORT} (Browser) und {MP_TCP_PORT} "
            "(ECHO/AETHERIA) sind im Netzwerk erreichbar, ohne dass der Rest "
            "von Jon offen ist. Ueber das Internet braucht der Gastgeber eine "
            "Portfreigabe fuer diese zwei Ports. Im Beitrittsfeld sind CODE "
            "und CODE@host:port erlaubt."
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


def create_coop_app() -> FastAPI:
    app = FastAPI(title="Jon Koop", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/")
    async def coop_root() -> RedirectResponse:
        return RedirectResponse("/blockwelt")

    @app.get("/blockwelt")
    async def coop_blockwelt() -> FileResponse:
        return FileResponse(GAME_PAGE, media_type="text/html")

    return app
