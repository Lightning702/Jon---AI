from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.anmeldung_service import AnmeldeFehler, get_anmeldung_service

router = APIRouter(prefix="/api/anmeldung")


class ZugangIn(BaseModel):
    benutzername: str = ""
    passwort: str = ""


class AenderungIn(ZugangIn):
    neuer_benutzername: str = ""
    neues_passwort: str = ""


def _fehler(fehler: AnmeldeFehler) -> JSONResponse:
    inhalt = {"detail": str(fehler)}
    inhalt.update(fehler.extra)
    return JSONResponse(status_code=fehler.status, content=inhalt)


@router.get("")
async def stand() -> dict:
    return get_anmeldung_service().stand()


@router.post("/einrichten")
async def einrichten(payload: ZugangIn):
    try:
        return await asyncio.to_thread(
            get_anmeldung_service().einrichten, payload.benutzername, payload.passwort
        )
    except AnmeldeFehler as fehler:
        return _fehler(fehler)


@router.post("/pruefen")
async def pruefen(payload: ZugangIn):
    try:
        return await asyncio.to_thread(
            get_anmeldung_service().pruefen, payload.benutzername, payload.passwort
        )
    except AnmeldeFehler as fehler:
        return _fehler(fehler)


@router.post("/aendern")
async def aendern(payload: AenderungIn):
    try:
        return await asyncio.to_thread(
            get_anmeldung_service().aendern,
            payload.benutzername,
            payload.passwort,
            payload.neuer_benutzername,
            payload.neues_passwort,
        )
    except AnmeldeFehler as fehler:
        return _fehler(fehler)
