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
async def pairing_start(direct_only: bool = False) -> dict:
    from app.services.handy_relay import get_handy_relay

    daten = await asyncio.to_thread(get_handy_service().kopplung_starten, direct_only)
    if not direct_only:
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
    if len(text) > 4096:
        return None
    groesse = max(128, min(1024, groesse))
    try:
        import io
        import qrcode
        bild = qrcode.make(text)
        puffer = io.BytesIO()
        bild.save(puffer, format="PNG")
        return puffer.getvalue()
    except ImportError:
        pass
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


def _nur_eltern() -> None:
    from app.services.geraete_funktionen import HANDY_KONTEXT

    if HANDY_KONTEXT.get():
        raise HTTPException(status_code=403, detail="Das geht nur in Jon am PC oder Pi.")


@router.post("/devices/{device_id}/durchsage")
async def device_announce(device_id: str, payload: dict) -> dict:
    from app.services.premium import get_premium

    get_premium().pruefen("familie")

    _nur_eltern()
    try:
        return await get_handy_service().durchsage(
            device_id,
            str(payload.get("text", "")),
            bool(payload.get("vorlesen", True)),
            str(payload.get("von", "")),
        )
    except HandyFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/devices/{device_id}/klingeln")
async def device_ring(device_id: str, payload: dict | None = None) -> dict:
    _nur_eltern()
    try:
        return await get_handy_service().klingeln(device_id, (payload or {}).get("sekunden", 30))
    except HandyFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/devices/{device_id}/regeln")
async def device_rules(device_id: str, payload: dict) -> dict:
    from app.services.premium import get_premium

    get_premium().pruefen("familie")

    _nur_eltern()
    try:
        return {"bildschirmzeit": await get_handy_service().regeln_setzen(device_id, payload)}
    except HandyFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/meldungen/neu")
async def alerts_new() -> dict:
    _nur_eltern()
    return {"meldungen": get_handy_service().meldungen_neu()}


@router.post("/devices/{device_id}/meldungen/{meldung_id}/quittieren")
async def alert_ack(device_id: str, meldung_id: str) -> dict:
    _nur_eltern()
    return {"ok": get_handy_service().meldung_quittieren(device_id, meldung_id)}


@router.get("/devices/{device_id}/bericht")
def wochenbericht(device_id: str, bis: str = "") -> dict:
    _nur_eltern()
    try:
        return get_handy_service().wochenbericht(device_id, bis)
    except HandyFehler as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/mein-bericht")
def mein_wochenbericht() -> dict:
    from app.services.geraete_funktionen import HANDY_KONTEXT

    geraet = HANDY_KONTEXT.get()
    if not geraet:
        raise HTTPException(status_code=404, detail="Nur für gekoppelte Handys.")
    try:
        return get_handy_service().wochenbericht(geraet)
    except HandyFehler as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/devices/{device_id}/zeitanfragen/{meldung_id}")
async def zeitanfrage_beantworten(device_id: str, meldung_id: str, payload: dict) -> dict:
    _nur_eltern()
    minuten = payload.get("minuten")
    try:
        return await get_handy_service().zeitanfrage_beantworten(
            device_id,
            meldung_id,
            bool(payload.get("erlaubt")),
            int(minuten) if isinstance(minuten, (int, float)) else None,
        )
    except HandyFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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


@router.get("/vpn")
async def vpn_status() -> dict:
    from app.services.geraete_vpn import tailscale_status
    return await asyncio.to_thread(tailscale_status)
