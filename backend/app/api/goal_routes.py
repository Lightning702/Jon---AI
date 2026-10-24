from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.ziel_modus import get_ziel_modus

router = APIRouter(prefix="/api/goal")


class Ziel(BaseModel):
    ziel: str = Field(min_length=1, max_length=4000)
    root: str = Field(default="", max_length=1000)
    modus: str = Field(default="", max_length=20)
    source: str = Field(default="app", max_length=60)


def _ziel(kennung: str) -> dict:
    try:
        return get_ziel_modus().get(kennung)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler)) from fehler


@router.get("")
async def liste(source: str = "") -> dict:
    return {"ziele": get_ziel_modus().liste(source)}


@router.post("")
async def starten(daten: Ziel) -> dict:
    try:
        return get_ziel_modus().starten(daten.ziel, daten.source, daten.root, daten.modus)
    except ValueError as fehler:
        raise HTTPException(409, str(fehler)) from fehler


@router.get("/{kennung}")
async def stand(kennung: str) -> dict:
    return _ziel(kennung)


@router.post("/{kennung}/stopp")
async def stoppen(kennung: str) -> dict:
    _ziel(kennung)
    return await get_ziel_modus().stoppen(kennung)


@router.get("/{kennung}/ereignisse")
async def ereignisse(kennung: str, nach: int = 0):
    _ziel(kennung)

    async def strom():
        async for ereignis in get_ziel_modus().verfolgen(kennung, nach):
            yield f"data: {json.dumps(ereignis, ensure_ascii=False)}\n\n"

    return StreamingResponse(strom(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
