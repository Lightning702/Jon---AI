from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas import InboxActionIn, InboxAnalyzeIn, InboxSeenIn
from app.services.inbox_service import get_inbox_service

router = APIRouter(prefix="/api/inbox")


@router.get("")
async def inbox_feed(limit: int = 12, days: int = 7) -> dict:
    return await asyncio.to_thread(get_inbox_service().feed, limit, days)


@router.post("/analyze")
async def inbox_analyze(payload: InboxAnalyzeIn) -> dict:
    service = get_inbox_service()
    text = payload.text
    subject = payload.betreff
    sender = payload.von
    key = payload.id
    if key.startswith("mail:") and not text:
        from app.services.mail_service import get_mail_service

        try:
            mail = await asyncio.to_thread(
                get_mail_service().read_mail, key.split(":", 1)[1]
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        if "error" in mail:
            raise HTTPException(status_code=404, detail=mail["error"])
        text = mail.get("text", "")
        subject = subject or mail.get("betreff", "")
        sender = sender or mail.get("von", "")
    if not key:
        raise HTTPException(status_code=400, detail="Kein Eintrag angegeben.")
    try:
        return await service.analyze(
            key,
            text,
            subject,
            sender,
            payload.provider,
            payload.model,
            payload.force,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/action")
async def inbox_action(payload: InboxActionIn) -> dict:
    if not payload.bestaetigt:
        raise HTTPException(
            status_code=403,
            detail="Diese Aktion braucht deine Bestaetigung.",
        )
    try:
        return await asyncio.to_thread(
            get_inbox_service().apply,
            payload.typ,
            payload.payload,
            payload.quelle or "inbox",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/seen")
async def inbox_seen(payload: InboxSeenIn) -> dict:
    get_inbox_service().mark_seen(payload.id)
    return {"gesehen": payload.id}
