from __future__ import annotations

import asyncio
import mimetypes

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.testumgebung import Fehler, get_testumgebung

router = APIRouter(prefix="/api/testumgebung")
vorschau_router = APIRouter()

SANDBOX = "sandbox allow-scripts allow-forms allow-modals allow-popups allow-pointer-lock allow-downloads"


class Neu(BaseModel):
    name: str = Field(default="", max_length=60)
    maschine: bool | None = None


class Befehl(BaseModel):
    befehl: str = Field(min_length=1, max_length=8000)
    zeit: float = Field(default=60, ge=1, le=600)


class Datei(BaseModel):
    pfad: str = Field(min_length=1, max_length=400)
    inhalt: str = Field(default="", max_length=2_000_000)


class Code(BaseModel):
    sprache: str = Field(min_length=1, max_length=20)
    code: str = Field(max_length=2_000_000)
    dateiname: str = Field(default="", max_length=120)


def _kennung(kennung: str) -> str:
    dienst = get_testumgebung()
    return dienst.standard() if kennung in ("", "standard") else kennung


async def _tun(funktion, *argumente):
    try:
        return await asyncio.to_thread(funktion, *argumente)
    except Fehler as fehler:
        raise HTTPException(400, str(fehler)) from fehler


@router.get("")
async def liste() -> dict:
    return await _tun(get_testumgebung().liste)


@router.post("")
async def neu(daten: Neu) -> dict:
    return await _tun(get_testumgebung().erstellen, daten.name, daten.maschine)


@router.post("/docker/starten")
async def docker_starten() -> dict:
    return await _tun(get_testumgebung().docker_starten)


@router.delete("/{kennung}")
async def loeschen(kennung: str) -> dict:
    return await _tun(get_testumgebung().loeschen, kennung)


@router.post("/{kennung}/zuruecksetzen")
async def zuruecksetzen(kennung: str) -> dict:
    return await _tun(get_testumgebung().zuruecksetzen, await asyncio.to_thread(_kennung, kennung))


@router.get("/{kennung}")
async def beschreiben(kennung: str) -> dict:
    return await _tun(get_testumgebung().beschreiben, await asyncio.to_thread(_kennung, kennung))


@router.get("/{kennung}/dateien")
async def dateien(kennung: str) -> dict:
    return await _tun(get_testumgebung().dateien, await asyncio.to_thread(_kennung, kennung))


@router.get("/{kennung}/datei")
async def lesen(kennung: str, pfad: str) -> dict:
    return await _tun(get_testumgebung().lesen, await asyncio.to_thread(_kennung, kennung), pfad)


@router.put("/{kennung}/datei")
async def schreiben(kennung: str, daten: Datei) -> dict:
    return await _tun(get_testumgebung().schreiben, await asyncio.to_thread(_kennung, kennung), daten.pfad, daten.inhalt)


@router.post("/{kennung}/ausfuehren")
async def ausfuehren(kennung: str, daten: Befehl) -> dict:
    return await _tun(get_testumgebung().ausfuehren, await asyncio.to_thread(_kennung, kennung), daten.befehl, daten.zeit)


@router.post("/{kennung}/code")
async def code(kennung: str, daten: Code) -> dict:
    return await _tun(get_testumgebung().code, await asyncio.to_thread(_kennung, kennung), daten.sprache, daten.code, daten.dateiname)


@vorschau_router.get("/testumgebung-vorschau/{kennung}/{pfad:path}")
async def vorschau(kennung: str, pfad: str = "") -> FileResponse:
    try:
        datei = await asyncio.to_thread(get_testumgebung().datei_fuer_vorschau, kennung, pfad)
    except Fehler as fehler:
        raise HTTPException(404, str(fehler)) from fehler
    art = mimetypes.guess_type(datei.name)[0] or "application/octet-stream"
    return FileResponse(datei, media_type=art, headers={"Content-Security-Policy": SANDBOX, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
