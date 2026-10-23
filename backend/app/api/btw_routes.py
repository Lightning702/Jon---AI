from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter

from app.services.btw_service import antworten

router = APIRouter(prefix="/api")


class Zwischenfrage(BaseModel):
    frage: str = Field(min_length=1, max_length=4000)
    verlauf: list[dict] = Field(default_factory=list, max_length=40)
    task_id: str = Field(default="", max_length=40)
    nebenbei: str = Field(default="", max_length=6000)


@router.post("/btw")
async def zwischenfrage(daten: Zwischenfrage) -> dict:
    return await antworten(daten.frage, daten.verlauf, daten.task_id, daten.nebenbei)
