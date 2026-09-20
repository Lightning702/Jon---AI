from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from app.services.live_service import LiveFehler, get_live_service

router = APIRouter(prefix="/api/live")

GRENZE = "jonlive"


@router.get("")
async def stand() -> dict:
    return get_live_service().stand()


@router.post("/start")
async def start(payload: dict) -> dict:
    try:
        return get_live_service().starten(
            str(payload.get("welcher", "alle") or "alle"),
            float(payload.get("takt", 2.0) or 2.0),
            int(payload.get("breite", 1280) or 1280),
            int(payload.get("qualitaet", 60) or 60),
        )
    except LiveFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stop")
async def stop() -> dict:
    return get_live_service().stoppen()


@router.get("/bild")
async def einzelbild(welcher: str = "", breite: int = 0, qualitaet: int = 0) -> Response:
    dienst = get_live_service()
    try:
        if welcher or breite or qualitaet:
            from app.services.live_service import bild

            daten = await asyncio.to_thread(
                bild,
                welcher or "alle",
                breite or 1280,
                qualitaet or 60,
            )
        else:
            daten = await asyncio.to_thread(dienst.aktuell)
    except LiveFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=daten,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/bild64")
async def bild_base64(welcher: str = "alle", breite: int = 0, qualitaet: int = 0) -> dict:
    import base64

    from app.services.live_service import bild

    try:
        daten = await asyncio.to_thread(
            bild, welcher or "alle", breite or 1100, qualitaet or 55
        )
    except LiveFehler as exc:
        return {"ok": False, "fehler": str(exc)}
    return {
        "ok": True,
        "typ": "image/jpeg",
        "bild": base64.b64encode(daten).decode("ascii"),
    }


@router.get("/strom")
async def strom() -> StreamingResponse:
    dienst = get_live_service()

    async def bilder():
        dienst.zuschauer_an()
        try:
            while True:
                try:
                    daten = await asyncio.to_thread(dienst.aktuell)
                except LiveFehler:
                    return
                yield (
                    f"--{GRENZE}\r\nContent-Type: image/jpeg\r\n"
                    f"Content-Length: {len(daten)}\r\n\r\n"
                ).encode("ascii") + daten + b"\r\n"
                await asyncio.sleep(max(0.2, dienst.takt()))
        finally:
            dienst.zuschauer_ab()

    return StreamingResponse(
        bilder(),
        media_type=f"multipart/x-mixed-replace; boundary={GRENZE}",
        headers={"Cache-Control": "no-store"},
    )
