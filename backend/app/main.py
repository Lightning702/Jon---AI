from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import time
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.p2p_routes import create_chat_app
from app.api.p2p_routes import router as p2p_router
from app.api.routes import accounts, providers, router
from app.api.system_routes import router as system_router
from app.core.config import ROOT_DIR, get_settings
from app.db.database import init_db


async def _warm_caches() -> None:
    with suppress(Exception):
        await providers()
    with suppress(Exception):
        await accounts()


async def _dream_watcher() -> None:
    from app.services.dream_service import get_dream_service
    from app.services.settings_service import get_settings_service
    from app.services.system_service import SystemService

    syssvc = SystemService()
    while True:
        await asyncio.sleep(60)
        try:
            data = get_settings_service().get()
            if not data.get("dream_auto", True):
                continue
            idle_minutes = float(data.get("dream_idle_minutes", 5) or 5)
            idle = await asyncio.to_thread(syssvc.idle_seconds)
            if idle < idle_minutes * 60:
                continue
            dreams = get_dream_service()
            if not any(t["status"] == "pending" for t in dreams.list()):
                continue
            settings = get_settings()
            provider = data.get("provider") or settings.default_provider
            model = data.get("model") or settings.jon_model
            await dreams.run_pending(provider, model)
        except Exception:
            continue


async def _clipboard_watcher() -> None:
    from app.services.clipboard_service import get_clipboard_service
    from app.services.settings_service import get_settings_service

    svc = get_clipboard_service()
    while True:
        await asyncio.sleep(2)
        try:
            if not get_settings_service().get().get("clipboard_history", True):
                continue
            await asyncio.to_thread(svc.capture)
        except Exception:
            continue


async def _task_watcher() -> None:
    from app.services.settings_service import get_settings_service
    from app.services.task_service import get_task_service

    while True:
        await asyncio.sleep(30)
        try:
            tasks = get_task_service()
            if not tasks._due():
                continue
            data = get_settings_service().get()
            settings = get_settings()
            provider = data.get("provider") or settings.default_provider
            model = data.get("model") or settings.jon_model
            await tasks.run_due(provider, model)
        except Exception:
            continue


async def _telegram_watcher() -> None:
    from app.services.telegram_service import get_telegram_service

    service = get_telegram_service()
    while True:
        try:
            await service.poll_once()
        except Exception:
            await asyncio.sleep(10)


async def _morning_watcher() -> None:
    from app.services.telegram_service import get_telegram_service

    service = get_telegram_service()
    while True:
        await asyncio.sleep(60)
        try:
            await service.morning_tick()
        except Exception:
            continue


async def _companion_watcher() -> None:
    from app.services.cowork_service import get_cowork_service
    from app.services.focus_service import get_focus_service
    from app.services.pomodoro_service import get_pomodoro_service

    focus = get_focus_service()
    cowork = get_cowork_service()
    pomodoro = get_pomodoro_service()
    while True:
        await asyncio.sleep(5)
        try:
            await asyncio.to_thread(focus.tick)
            await asyncio.to_thread(pomodoro.tick)
            await cowork.tick()
        except Exception:
            continue


async def _routine_timeline_watcher() -> None:
    from app.services.routine_service import get_routine_service
    from app.services.settings_service import get_settings_service
    from app.services.timeline_service import get_timeline_service

    routine = get_routine_service()
    timeline = get_timeline_service()
    while True:
        await asyncio.sleep(30)
        try:
            data = get_settings_service().get()
            if data.get("routine_enabled", True):
                await asyncio.to_thread(routine.tick)
            if data.get("timeline_enabled", False):
                await asyncio.to_thread(timeline.capture)
        except Exception:
            continue


async def _file_watcher() -> None:
    from app.services.settings_service import get_settings_service
    from app.services.watcher_service import get_watcher_service

    while True:
        await asyncio.sleep(12)
        try:
            data = get_settings_service().get()
            settings = get_settings()
            provider = data.get("provider") or settings.default_provider
            model = data.get("model") or settings.jon_model
            await get_watcher_service().tick(provider, model)
        except Exception:
            continue


async def _chat_server() -> None:
    from app.services.p2p_service import CHAT_PORT

    config = uvicorn.Config(
        create_chat_app(),
        host="0.0.0.0",
        port=CHAT_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except Exception:
        return


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.services.p2p_service import get_p2p_service

    p2p = get_p2p_service()
    warmup = asyncio.create_task(_warm_caches())
    dream_task = asyncio.create_task(_dream_watcher())
    clipboard_task = asyncio.create_task(_clipboard_watcher())
    automation_task = asyncio.create_task(_task_watcher())
    telegram_task = asyncio.create_task(_telegram_watcher())
    morning_task = asyncio.create_task(_morning_watcher())
    companion_task = asyncio.create_task(_companion_watcher())
    routine_task = asyncio.create_task(_routine_timeline_watcher())
    files_task = asyncio.create_task(_file_watcher())
    chat_task = asyncio.create_task(_chat_server())
    announce_task = asyncio.create_task(p2p.announce_loop())
    listen_task = asyncio.create_task(p2p.listen_loop())

    try:
        from app.services.quickwrite_service import get_quickwrite_service

        get_quickwrite_service().start_mouse_listener()
    except Exception:
        pass

    from app.services.relay_service import get_relay_service

    relay_task = asyncio.create_task(get_relay_service().start())
    outbox_task = asyncio.create_task(p2p.outbox_loop())
    yield
    relay_task.cancel()
    outbox_task.cancel()
    warmup.cancel()
    dream_task.cancel()
    clipboard_task.cancel()
    automation_task.cancel()
    telegram_task.cancel()
    morning_task.cancel()
    companion_task.cancel()
    routine_task.cancel()
    files_task.cancel()
    chat_task.cancel()
    announce_task.cancel()
    listen_task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(system_router)
    app.include_router(p2p_router)

    from pathlib import Path

    from fastapi.responses import FileResponse

    game_file = Path(__file__).resolve().parent / "static" / "blockwelt.html"

    @app.get("/blockwelt")
    async def blockwelt():
        return FileResponse(game_file, media_type="text/html")

    dist = ROOT_DIR / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/app", StaticFiles(directory=str(dist), html=True), name="app")
    return app


app = create_app()


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1.0)
        return probe.connect_ex((host, port)) == 0


def _free_port(host: str, port: int) -> None:
    if not _port_in_use(host, port):
        return
    if os.name == "nt":
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"Get-NetTCPConnection -LocalPort {port} -State Listen "
                "-ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty OwningProcess -Unique | "
                f"Where-Object {{ $_ -ne {os.getpid()} }} | "
                "ForEach-Object { Stop-Process -Id $_ -Force "
                "-ErrorAction SilentlyContinue }",
            ],
            capture_output=True,
            timeout=20,
        )
    else:
        subprocess.run(
            ["sh", "-c", f"lsof -ti tcp:{port} | xargs -r kill -9"],
            capture_output=True,
            timeout=20,
        )
    for _ in range(20):
        if not _port_in_use(host, port):
            return
        time.sleep(0.25)


def main() -> None:
    settings = get_settings()
    host = "0.0.0.0" if settings.jon_lan else settings.host
    _free_port(settings.host, settings.port)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
