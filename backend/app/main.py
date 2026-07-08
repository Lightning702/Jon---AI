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

from app.api.routes import accounts, providers, router
from app.api.system_routes import router as system_router
from app.core.config import get_settings
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
            model = data.get("model") or settings.default_model
            await dreams.run_pending(provider, model)
        except Exception:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    warmup = asyncio.create_task(_warm_caches())
    dream_task = asyncio.create_task(_dream_watcher())
    yield
    warmup.cancel()
    dream_task.cancel()


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
    _free_port(settings.host, settings.port)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
