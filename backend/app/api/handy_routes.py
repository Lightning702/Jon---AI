from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.services.handy_service import HandyFehler, get_handy_service

router = APIRouter(prefix="/api/handy")


@router.post("/gate")
async def gate(request: Request) -> dict:
    umschlag = await request.json()
    if not isinstance(umschlag, dict):
        raise HTTPException(status_code=400, detail="Ungueltiger Umschlag.")
    try:
        return await get_handy_service().umschlag(umschlag)
    except HandyFehler as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/gate/stream")
async def gate_stream(request: Request) -> StreamingResponse:
    umschlag = await request.json()
    if not isinstance(umschlag, dict):
        raise HTTPException(status_code=400, detail="Ungueltiger Umschlag.")
    dienst = get_handy_service()

    async def strom():
        try:
            async for stueck in dienst.umschlag_strom(umschlag):
                yield f"data: {json.dumps(stueck, ensure_ascii=False)}\n\n"
        except HandyFehler as exc:
            yield f"data: {json.dumps({'fehler': str(exc)})}\n\n"

    return StreamingResponse(
        strom(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/pairing/start")
async def pairing_start() -> dict:
    from app.services.handy_relay import get_handy_relay

    daten = get_handy_service().kopplung_starten()
    daten["relay"] = await asyncio.to_thread(get_handy_relay().sofort)
    return daten


@router.get("/pairing/state")
async def pairing_state() -> dict:
    from app.services.handy_relay import get_handy_relay

    daten = get_handy_service().kopplung_status()
    daten["relay"] = get_handy_relay().status()
    return daten


@router.post("/pairing/answer")
async def pairing_answer(payload: dict) -> dict:
    try:
        return get_handy_service().kopplung_beantworten(bool(payload.get("angenommen")))
    except HandyFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/pairing/cancel")
async def pairing_cancel() -> dict:
    return get_handy_service().kopplung_abbrechen()


@router.get("/pairing/qr")
async def pairing_qr(text: str, groesse: int = 640) -> Response:
    bild = await asyncio.to_thread(_qr_png, text, groesse)
    if bild is None:
        raise HTTPException(status_code=500, detail="QR-Code nicht erzeugt.")
    return Response(content=bild, media_type="image/png")


def _qr_png(text: str, groesse: int) -> bytes | None:
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    try:
        kodierer = cv2.QRCodeEncoder_create()
        roh = kodierer.encode(text)
    except Exception:
        return None
    rand = 4
    gepolstert = np.pad(roh, rand, mode="constant", constant_values=255)
    kante = max(1, groesse // gepolstert.shape[0])
    gross = cv2.resize(
        gepolstert,
        (gepolstert.shape[1] * kante, gepolstert.shape[0] * kante),
        interpolation=cv2.INTER_NEAREST,
    )
    erfolg, puffer = cv2.imencode(".png", gross)
    if not erfolg:
        return None
    return puffer.tobytes()


@router.get("/devices")
async def devices() -> dict:
    dienst = get_handy_service()
    return {"geraete": dienst.geraete(), "pc": dienst.kennung()}


@router.delete("/devices/{device_id}")
async def device_remove(device_id: str) -> dict:
    return {"entfernt": get_handy_service().geraet_entfernen(device_id)}


@router.post("/devices/{device_id}/rights")
async def device_rights(device_id: str, payload: dict) -> dict:
    try:
        rechte = get_handy_service().rechte_setzen(
            device_id,
            str(payload.get("recht", "")),
            bool(payload.get("wert")),
        )
    except HandyFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"rechte": rechte}


@router.post("/devices/{device_id}/name")
async def device_rename(device_id: str, payload: dict) -> dict:
    try:
        geraet = get_handy_service().geraet_umbenennen(device_id, str(payload.get("name", "")))
        return {"geraet": geraet}
    except HandyFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/devices/{device_id}/state")
async def device_state(device_id: str) -> dict:
    from app.services.connectors import get_connector_manager

    connector = get_connector_manager().connector("android")
    if connector is None:
        raise HTTPException(status_code=503, detail="Android-Connector fehlt.")
    return await connector.ausfuehren("android_device_status", {"device": device_id})


@router.post("/devices/{device_id}/file")
async def device_file(device_id: str, payload: dict) -> dict:
    from app.services.connectors import get_connector_manager

    connector = get_connector_manager().connector("android")
    if connector is None:
        raise HTTPException(status_code=503, detail="Android-Connector fehlt.")
    ergebnis = await connector.ausfuehren(
        "android_files_send",
        {"device": device_id, "path": str(payload.get("pfad", ""))},
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=str(ergebnis["error"]))
    return ergebnis


@router.get("/connectors")
async def connectors() -> dict:
    from app.services.connectors import get_connector_manager

    return {"connectoren": get_connector_manager().uebersicht()}


@router.get("/status")
async def status() -> dict:
    from app.services.handy_relay import get_handy_relay

    dienst = get_handy_service()
    return {
        "pc": dienst.kennung(),
        "geraete": len(dienst.geraete()),
        "relay": get_handy_relay().status(),
        "kopplung": dienst.kopplung_status(),
    }


@router.get("/system")
async def system() -> dict:
    from app.services.geraet_service import uebersicht

    return await asyncio.to_thread(uebersicht)
