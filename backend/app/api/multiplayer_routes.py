from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.coop_lan_service import (
    DISCOVERY_PORT,
    ensure_firewall,
    firewall_state,
    interfaces,
    invite_host,
    local_addresses,
)
from app.services.multiplayer_service import (
    GAMES,
    PROTOCOL_VERSION,
    WebSocketTransport,
    get_multiplayer_service,
)

router = APIRouter(prefix="/api/mp", tags=["multiplayer"])

MP_TCP_PORT = 8759
MP_WS_PORT = 8760
MP_UDP_PORT = DISCOVERY_PORT
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


@router.get("/status")
async def mp_status() -> dict:
    settings = get_settings()
    service = get_multiplayer_service()
    return {
        **service.status(),
        "version": settings.app_version,
        "tcp_port": MP_TCP_PORT,
        "ws_port": MP_WS_PORT,
        "udp_port": MP_UDP_PORT,
        "http_port": settings.port,
        "lan": settings.jon_lan,
        "addresses": local_addresses(),
        "invite_host": invite_host(),
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
        "udp_port": MP_UDP_PORT,
        "addresses": local_addresses(),
        "invite_host": invite_host(),
        "firewall": await asyncio.to_thread(firewall_state),
        "hint": (
            "Im gleichen Netzwerk reicht der Freundschaftscode: Jon sucht den "
            "Gastgeber selbst und verbindet dorthin. Von aussen geht "
            f"CODE@adresse — Browser ueber Port {MP_WS_PORT}, ECHO und AETHERIA "
            f"ueber {MP_TCP_PORT}. Ueber das Internet braucht der Gastgeber eine "
            "Portfreigabe fuer diese zwei Ports."
        ),
    }


@router.get("/network")
async def mp_network(refresh: bool = False) -> dict:
    from app.services.coop_lan_service import get_coop_beacon

    settings = get_settings()
    beacon = get_coop_beacon()
    return {
        "addresses": local_addresses(),
        "invite_host": invite_host(),
        "interfaces": interfaces(),
        "discovery": beacon.online,
        "findable": beacon.findable,
        "tcp_port": MP_TCP_PORT,
        "ws_port": MP_WS_PORT,
        "udp_port": MP_UDP_PORT,
        "http_port": settings.port,
        "firewall": await asyncio.to_thread(firewall_state, refresh),
    }


@router.post("/firewall")
async def mp_firewall() -> dict:
    result = await asyncio.to_thread(
        ensure_firewall, [MP_TCP_PORT, MP_WS_PORT], [MP_UDP_PORT]
    )
    state = await asyncio.to_thread(firewall_state, True)
    return {**result, "firewall": state}


@router.get("/find/{code}")
async def mp_find(code: str) -> dict:
    service = get_multiplayer_service()
    wanted = str(code or "").strip().upper()
    if service.knows_code(wanted):
        return {
            "where": "local",
            "code": wanted,
            "lobby": service.lobby_info(wanted),
            **service.invite_info(wanted),
        }
    remote = await service.find_remote(wanted)
    if remote is None:
        raise HTTPException(status_code=404, detail="Code nicht gefunden")
    return {"where": "remote", "code": wanted, **remote}


@router.get("/scan")
async def mp_scan() -> dict:
    service = get_multiplayer_service()
    found = await service.scan_remote()
    local = [
        {
            **entry,
            "host": "127.0.0.1",
            "tcp_port": MP_TCP_PORT,
            "ws_port": MP_WS_PORT,
            "origin": "",
            "local": True,
        }
        for entry in service.beacon_list()
    ]
    return {"lobbies": local + found}


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
    if not service.knows_code(payload.code):
        remote = await service.find_remote(payload.code)
        if remote is not None:
            return {"redirect": remote}
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
