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

from app.api.multiplayer_routes import MP_TCP_PORT, MP_WS_PORT, create_coop_app
from app.api.multiplayer_routes import router as multiplayer_router
from app.api.p2p_routes import create_chat_app
from app.api.p2p_routes import router as p2p_router
from app.api.maps_routes import router as maps_router
from app.api.phone_routes import router as phone_router
from app.api.research_routes import router as research_router
from app.api.routes import accounts, providers, router
from app.api.studio_routes import router as studio_router
from app.api.system_routes import router as system_router
from app.core.auth import TokenMiddleware, get_token
from app.core.config import ROOT_DIR, get_settings, web_app_dir
from app.core.logbook import logger as logbook_logger
from app.core.logbook import note_error, note_ok, setup_logging
from app.db.database import init_db

_log = logbook_logger("main")


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
        except Exception as exc:
            note_error("dream_watcher", exc)
            continue


async def _friend_location_watcher() -> None:
    from app.services.friend_location_service import get_friend_location_service

    service = get_friend_location_service()
    while True:
        await asyncio.sleep(120)
        try:
            if not service.sharing().get("aktiv"):
                continue
            await service.broadcast()
        except Exception as exc:
            note_error("friend_location_watcher", exc)
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
        except Exception as exc:
            note_error("clipboard_watcher", exc)
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
        except Exception as exc:
            note_error("task_watcher", exc)
            continue


async def _telegram_watcher() -> None:
    from app.services.telegram_service import get_telegram_service

    service = get_telegram_service()
    while True:
        try:
            await service.poll_once()
        except Exception as exc:
            note_error("telegram_watcher", exc)
            await asyncio.sleep(10)


async def _group_bots_watcher() -> None:
    from app.services.telegram_group_service import get_group_bots

    bots = get_group_bots()
    while True:
        try:
            await asyncio.gather(*(bot.poll_once() for bot in bots))
        except Exception as exc:
            note_error("group_bots_watcher", exc)
            await asyncio.sleep(10)


async def _morning_watcher() -> None:
    from app.services.telegram_service import get_telegram_service

    service = get_telegram_service()
    while True:
        await asyncio.sleep(60)
        try:
            await service.morning_tick()
        except Exception as exc:
            note_error("morning_watcher", exc)
            continue


async def _phone_watcher() -> None:
    from app.services.phone_service import get_phone_service

    service = get_phone_service()
    try:
        await service.start()
    except Exception as exc:
        note_error("phone_watcher", exc)
        pass
    while True:
        await asyncio.sleep(15)
        try:
            if service.enabled() and not service.status()["running"]:
                await service.start()
            await service.run_due()
        except Exception as exc:
            note_error("phone_watcher", exc)
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
        except Exception as exc:
            note_error("companion_watcher", exc)
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
        except Exception as exc:
            note_error("routine_timeline_watcher", exc)
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
        except Exception as exc:
            note_error("file_watcher", exc)
            continue


async def _autofile_watcher() -> None:
    from app.services.autofile_service import get_autofile_service

    while True:
        await asyncio.sleep(20)
        try:
            await asyncio.to_thread(get_autofile_service().tick)
        except Exception as exc:
            note_error("autofile_watcher", exc)
            continue


async def _appusage_watcher() -> None:
    from app.services.settings_service import get_settings_service
    from app.services.appusage_service import get_appusage_service

    interval = 15
    while True:
        await asyncio.sleep(interval)
        try:
            if not get_settings_service().get().get("app_usage_enabled", False):
                continue
            await asyncio.to_thread(get_appusage_service().tick, interval)
        except Exception as exc:
            note_error("appusage_watcher", exc)
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
    except asyncio.CancelledError:
        raise
    except (SystemExit, Exception) as exc:
        note_error("chat_server", exc)
        _log.info(f"Chat-Port {CHAT_PORT} belegt - P2P-Chat bleibt aus")
        return


async def _multiplayer_server() -> None:
    from app.services.multiplayer_service import get_multiplayer_service

    service = get_multiplayer_service()
    try:
        await service.start()
        await service.serve_stream("0.0.0.0", MP_TCP_PORT)
    except asyncio.CancelledError:
        raise
    except (SystemExit, Exception) as exc:
        note_error("multiplayer_server", exc)
        _log.info(f"Koop-Port {MP_TCP_PORT} belegt - Spiele-Server bleibt aus")
        return


async def _coop_beacon() -> None:
    from app.services.coop_lan_service import DISCOVERY_PORT, get_coop_beacon
    from app.services.multiplayer_service import get_multiplayer_service

    beacon = get_coop_beacon()
    beacon.bind(get_multiplayer_service(), MP_TCP_PORT, MP_WS_PORT)
    try:
        await beacon.serve(MP_TCP_PORT, MP_WS_PORT)
    except asyncio.CancelledError:
        raise
    except (SystemExit, Exception) as exc:
        note_error("coop_beacon", exc)
        _log.info(f"Koop-Suche auf {DISCOVERY_PORT} nicht moeglich")
        return


async def _coop_web_server() -> None:
    config = uvicorn.Config(
        create_coop_app(),
        host="0.0.0.0",
        port=MP_WS_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except asyncio.CancelledError:
        raise
    except (SystemExit, Exception) as exc:
        note_error("coop_web_server", exc)
        _log.info(f"Koop-Port {MP_WS_PORT} belegt - Browser-Koop nur lokal")
        return


def _parent_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000, False, pid)
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) != 0
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


async def _parent_watchdog() -> None:
    raw = os.environ.get("JON_PARENT_PID", "").strip()
    if not raw.isdigit():
        return
    pid = int(raw)
    if pid <= 0 or pid == os.getpid():
        return
    while True:
        await asyncio.sleep(2)
        if await asyncio.to_thread(_parent_alive, pid):
            continue
        _log.info("Jon-App beendet - Backend faehrt herunter")
        os._exit(0)


async def _share_beacon() -> None:
    from app.services.ollama_share_service import DISCOVERY_PORT, get_share_service

    try:
        await get_share_service().serve_discovery()
    except asyncio.CancelledError:
        raise
    except (SystemExit, Exception) as exc:
        note_error("share_beacon", exc)
        _log.info(f"Ollama-Freigabe-Suche auf {DISCOVERY_PORT} nicht moeglich")
        return


_tasks: dict[str, asyncio.Task] = {}


EINMALIG = {"warmup", "parent_watchdog"}


def _spawn(name: str, coro) -> asyncio.Task:
    task = asyncio.create_task(coro, name=name)
    _tasks[name] = task
    note_ok(name)
    task.add_done_callback(lambda done: _finished(name, done))
    return task


def _finished(name: str, task: asyncio.Task) -> None:
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        note_error(name, error)
    elif name not in EINMALIG:
        _log.warning("Hintergrunddienst %s hat sich beendet", name)


def _stop_all() -> None:
    for task in _tasks.values():
        task.cancel()
    _tasks.clear()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log.info("STEP init_db")
    init_db()
    _log.info("STEP init_db ok")
    from app.services.trash_service import get_trash_service

    with suppress(Exception):
        get_trash_service().cleanup()
    from app.services.research import get_research_service

    with suppress(Exception):
        get_research_service().boot()
    from app.services.p2p_service import get_p2p_service

    p2p = get_p2p_service()
    _log.info("STEP p2p service ok")
    _spawn("warmup", _warm_caches())
    _spawn("dream_watcher", _dream_watcher())
    _spawn("clipboard_watcher", _clipboard_watcher())
    _spawn("friend_location_watcher", _friend_location_watcher())
    _spawn("task_watcher", _task_watcher())
    _spawn("telegram_watcher", _telegram_watcher())
    _spawn("group_bots_watcher", _group_bots_watcher())
    _spawn("morning_watcher", _morning_watcher())
    _spawn("companion_watcher", _companion_watcher())
    _spawn("phone_watcher", _phone_watcher())
    _spawn("routine_timeline_watcher", _routine_timeline_watcher())
    _spawn("file_watcher", _file_watcher())
    _spawn("autofile_watcher", _autofile_watcher())
    _spawn("appusage_watcher", _appusage_watcher())
    _spawn("chat_server", _chat_server())
    _spawn("multiplayer_server", _multiplayer_server())
    _spawn("coop_web_server", _coop_web_server())
    _spawn("coop_beacon", _coop_beacon())
    _spawn("share_beacon", _share_beacon())
    _spawn("parent_watchdog", _parent_watchdog())
    _spawn("p2p_announce", p2p.announce_loop())
    _spawn("p2p_listen", p2p.listen_loop())

    try:
        from app.services.quickwrite_service import get_quickwrite_service

        get_quickwrite_service().start_mouse_listener()
    except Exception as exc:
        note_error("quickwrite", exc)

    from app.services.relay_service import get_relay_service

    _log.info("STEP tasks ok")
    _spawn("relay", get_relay_service().start())
    _spawn("p2p_outbox", p2p.outbox_loop())
    _log.info("STEP vor yield")
    yield
    _stop_all()
    with suppress(Exception):
        from app.services.phone_service import get_phone_service

        await get_phone_service().stop()


def create_app() -> FastAPI:
    setup_logging()
    get_token()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(TokenMiddleware)
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
    app.include_router(multiplayer_router)
    app.include_router(phone_router)
    app.include_router(maps_router)
    app.include_router(research_router)
    app.include_router(studio_router)

    from pathlib import Path

    from fastapi.responses import FileResponse

    game_file = Path(__file__).resolve().parent / "static" / "blockwelt.html"

    @app.get("/blockwelt")
    async def blockwelt():
        return FileResponse(game_file, media_type="text/html")

    private_file = Path(__file__).resolve().parent / "static" / "privat.html"

    @app.get("/privat")
    async def privat():
        return FileResponse(
            private_file,
            media_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    dist = web_app_dir()
    if dist is not None:
        app.mount("/app", StaticFiles(directory=str(dist), html=True), name="app")
    else:
        _log.warning("Web-Oberflaeche nicht gefunden - /app bleibt aus")
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
