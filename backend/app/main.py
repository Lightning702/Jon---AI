from __future__ import annotations

import asyncio
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    warmup = asyncio.create_task(_warm_caches())
    yield
    warmup.cancel()


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


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
