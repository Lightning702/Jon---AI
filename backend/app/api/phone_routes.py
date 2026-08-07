from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas import PhoneCallIn, PhoneUpdateIn
from app.services.phone_service import get_phone_service

router = APIRouter(prefix="/api/phone", tags=["phone"])


@router.get("/status")
async def status() -> dict:
    return get_phone_service().status()


@router.get("/diagnostics")
async def diagnostics() -> dict:
    return get_phone_service().diagnostics()


@router.post("/start")
async def start() -> dict:
    service = get_phone_service()
    await service.restart()
    return service.status()


@router.post("/stop")
async def stop() -> dict:
    service = get_phone_service()
    await service.stop()
    return service.status()


@router.get("/setup")
async def setup() -> dict:
    service = get_phone_service()
    data = service.ensure_credentials()
    return {
        "server": service.local_ip(),
        "port": int(data.get("phone_sip_port", 5060) or 5060),
        "username": data.get("phone_sip_user", ""),
        "password": data.get("phone_sip_password", ""),
        "realm": data.get("phone_sip_realm", "jon"),
        "transport": "UDP",
        "app": "Linphone",
        "app_url": "https://f-droid.org/packages/org.linphone/",
    }


@router.post("/credentials/new")
async def new_credentials() -> dict:
    import secrets

    from app.services.settings_service import get_settings_service

    get_settings_service().update(
        {"phone_sip_password": secrets.token_urlsafe(18)}
    )
    service = get_phone_service()
    await service.restart()
    return await setup()


@router.get("/calls")
async def calls(include_done: bool = False) -> dict:
    service = get_phone_service()
    return {"calls": service.list(include_done=include_done)}


@router.post("/calls")
async def create_call(payload: PhoneCallIn) -> dict:
    service = get_phone_service()
    try:
        return service.schedule(
            when=payload.when or "",
            message=payload.message or "",
            reason=payload.reason or "",
            recurrence=payload.recurrence or "",
            duration=payload.duration or 600,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/calls/{call_id}")
async def update_call(call_id: str, payload: PhoneUpdateIn) -> dict:
    service = get_phone_service()
    try:
        call = service.update(
            call_id,
            when=payload.when or "",
            message=payload.message or "",
            reason=payload.reason or "",
            recurrence=payload.recurrence or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if call is None:
        raise HTTPException(status_code=404, detail="Anruf nicht gefunden")
    return call


@router.delete("/calls/{call_id}")
async def delete_call(call_id: str) -> dict:
    if not get_phone_service().cancel(call_id):
        raise HTTPException(status_code=404, detail="Anruf nicht gefunden")
    return {"ok": True}


@router.post("/test")
async def test_call() -> dict:
    service = get_phone_service()
    try:
        return await service.place_call(test=True, duration=90)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/dial")
async def dial(payload: PhoneCallIn) -> dict:
    service = get_phone_service()
    try:
        return await service.place_call(
            message=payload.message or "",
            reason=payload.reason or "",
            duration=payload.duration or 600,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/hangup")
async def hangup() -> dict:
    service = get_phone_service()
    stack = getattr(service, "_stack", None)
    if stack is None:
        return {"ok": False}
    for call in stack.active_calls():
        await call.hangup("Vom Nutzer beendet")
    return {"ok": True}


@router.get("/history")
async def history(limit: int = 25) -> dict:
    return {"calls": get_phone_service().history(limit=limit)}


@router.delete("/history")
async def clear_history() -> dict:
    get_phone_service().clear_history()
    return {"ok": True}
