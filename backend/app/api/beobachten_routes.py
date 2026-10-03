from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.beobachten import get_beobachten

router = APIRouter(prefix="/api")


class Neu(BaseModel):
    frage: str = Field(min_length=3, max_length=300)
    bedingung: str = Field(default="", max_length=500)
    intervall_stunden: float = Field(default=24, ge=1, le=720)


@router.get("/beobachten")
async def liste() -> list[dict]:
    return get_beobachten().liste()


@router.post("/beobachten")
async def anlegen(daten: Neu) -> dict:
    try:
        return get_beobachten().anlegen(daten.frage, daten.bedingung, daten.intervall_stunden)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/beobachten/meldungen")
async def meldungen() -> list[dict]:
    return get_beobachten().meldungen()


@router.post("/beobachten/{kennung}/pruefen")
async def pruefen(kennung: str) -> dict:
    try:
        return await get_beobachten().pruefen(kennung)
    except KeyError:
        raise HTTPException(404, "Diese Beobachtung gibt es nicht.")


@router.post("/beobachten/{kennung}/stoppen")
async def stoppen(kennung: str) -> dict:
    try:
        return get_beobachten().stoppen(kennung)
    except KeyError:
        raise HTTPException(404, "Diese Beobachtung gibt es nicht.")


@router.delete("/beobachten/{kennung}")
async def loeschen(kennung: str) -> dict:
    if not get_beobachten().loeschen(kennung):
        raise HTTPException(404, "Diese Beobachtung gibt es nicht.")
    return {"geloescht": True}
