from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.agent_profiles import PROFILES
from app.services.agenten_service import get_agenten_service

router = APIRouter(prefix="/api/agents")


class StartTeam(BaseModel):
    aufgabe: str = Field(min_length=1, max_length=12000)
    max_agenten: int = Field(default=3, ge=1, le=4)
    source: str = Field(default="app", pattern="^(app|minijon)$")
    research: bool = False
    roles: list[str] = Field(default_factory=list, max_length=8)
    kinder: int | None = Field(default=None, ge=3, le=17)


def find(run_id: str) -> dict:
    try:
        run = get_agenten_service().get(run_id)
        if not run.get("persist", True):
            raise KeyError(run_id)
        return run
    except KeyError:
        raise HTTPException(404, "Fachauftrag nicht gefunden.")


@router.get("/profiles")
async def profiles() -> list[dict]:
    return [{"id": key, **value} for key, value in PROFILES.items()]


@router.get("/runs")
async def runs(brief: bool = False) -> list[dict]:
    return get_agenten_service().list(brief)


@router.post("/runs")
async def start(payload: StartTeam) -> dict:
    try:
        return get_agenten_service().start(**payload.model_dump(), slot="emil" if payload.source == "minijon" else "jon")
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/runs/{run_id}")
async def run(run_id: str) -> dict:
    return find(run_id)


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str) -> dict:
    find(run_id)
    return await get_agenten_service().cancel(run_id)


@router.delete("/runs/{run_id}")
async def delete(run_id: str) -> dict:
    find(run_id)
    try:
        get_agenten_service().delete(run_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    return {"ok": True}
