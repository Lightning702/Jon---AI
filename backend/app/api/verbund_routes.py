from __future__ import annotations

import asyncio
import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.verbund_service import VerbundFehler, get_verbund_service

router = APIRouter(prefix="/api/verbund")


@router.get("")
async def liste() -> dict:
    return {"geraete": get_verbund_service().geraete()}


@router.get("/stand")
async def stand() -> dict:
    return await get_verbund_service().stand()


@router.post("/koppeln")
async def koppeln(payload: dict) -> dict:
    dienst = get_verbund_service()
    makler = payload.get("broker") if isinstance(payload.get("broker"), dict) else None
    try:
        return await asyncio.to_thread(
            dienst.koppeln, str(payload.get("code", "")), makler
        )
    except VerbundFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{geraet_id}")
async def entfernen(geraet_id: str) -> dict:
    return {"ok": get_verbund_service().entfernen(geraet_id)}


@router.get("/{geraet_id}/pruefen")
async def pruefen(geraet_id: str) -> dict:
    try:
        return await get_verbund_service().pruefen(geraet_id)
    except VerbundFehler as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{geraet_id}/fragen")
async def fragen(geraet_id: str, payload: dict) -> dict:
    try:
        antwort = await get_verbund_service().fragen(
            geraet_id, str(payload.get("frage", ""))
        )
    except VerbundFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"antwort": antwort}


@router.post("/{geraet_id}/rufen")
async def rufen(geraet_id: str, payload: dict) -> dict:
    try:
        return await get_verbund_service().rufen(
            geraet_id,
            str(payload.get("methode", "GET")),
            str(payload.get("pfad", "/api/health")),
            payload.get("rumpf") if isinstance(payload.get("rumpf"), dict) else None,
            payload.get("query") if isinstance(payload.get("query"), dict) else None,
        )
    except VerbundFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{geraet_id}/bild")
async def bild(geraet_id: str, welcher: str = "alle") -> Response:
    try:
        daten = await get_verbund_service().bildschirm(geraet_id, welcher or "alle")
    except VerbundFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=daten,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{geraet_id}/bild64")
async def bild64(geraet_id: str, welcher: str = "alle") -> dict:
    try:
        daten = await get_verbund_service().bildschirm(geraet_id, welcher or "alle")
    except VerbundFehler as exc:
        return {"ok": False, "fehler": str(exc)}
    return {"ok": True, "bild": base64.b64encode(daten).decode("ascii")}
