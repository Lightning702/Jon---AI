from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ollama_usb import UsbFehler, durchsuchen, get_usb_ollama, laufwerke

router = APIRouter(prefix="/api/ollama/usb", tags=["ollama-usb"])


class PfadIn(BaseModel):
    pfad: str = ""
    programme: list[str] = []


class EinbindenIn(BaseModel):
    datei: str
    name: str = ""


@router.get("")
async def usb_stand() -> dict:
    dienst = get_usb_ollama()
    stand, liste = await asyncio.gather(asyncio.to_thread(dienst.stand), asyncio.to_thread(laufwerke))
    return {**stand, "laufwerke": liste}


@router.get("/laufwerke")
async def usb_laufwerke() -> dict:
    return {"laufwerke": await asyncio.to_thread(laufwerke)}


@router.post("/suchen")
async def usb_suchen(eingabe: PfadIn) -> dict:
    try:
        return await asyncio.to_thread(durchsuchen, eingabe.pfad)
    except UsbFehler as fehler:
        raise HTTPException(status_code=400, detail=str(fehler))


@router.post("/verbinden")
async def usb_verbinden(eingabe: PfadIn) -> dict:
    try:
        return await asyncio.to_thread(get_usb_ollama().verbinden, eingabe.pfad, eingabe.programme)
    except UsbFehler as fehler:
        raise HTTPException(status_code=400, detail=str(fehler))


@router.post("/trennen")
async def usb_trennen() -> dict:
    return await asyncio.to_thread(get_usb_ollama().trennen)


@router.post("/einbinden")
async def usb_einbinden(eingabe: EinbindenIn) -> dict:
    try:
        return await asyncio.to_thread(get_usb_ollama().einbinden, eingabe.datei, eingabe.name)
    except UsbFehler as fehler:
        raise HTTPException(status_code=400, detail=str(fehler))
