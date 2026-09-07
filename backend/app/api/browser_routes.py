from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas import BrowserConfirmIn
from app.services.browser.protokoll import verlauf
from app.services.browser.sicherheit import get_guard
from app.services.browser.werkzeuge import ausfuehren
from app.services.browser.zustand import get_zustand

router = APIRouter(prefix="/api/browser")


@router.get("/status")
async def status(sitzung: str = "") -> dict:
    from app.services.browser.sitzung import letzte

    schluessel = sitzung or letzte()
    zustand = get_zustand(schluessel).lesen()
    offen = get_guard(schluessel).offen()
    return {
        "sitzung": schluessel,
        "zustand": zustand.als_dict(),
        "bestaetigung": offen.als_dict() if offen is not None else None,
        "protokoll": verlauf(30),
    }


@router.post("/confirm")
async def bestaetigen(payload: BrowserConfirmIn, sitzung: str = "") -> dict:
    from app.services.browser.sitzung import letzte

    erlaubt = get_guard(sitzung or letzte()).entscheiden(
        payload.token, payload.approved
    )
    if not erlaubt:
        raise HTTPException(
            status_code=400,
            detail="Diese Bestaetigung ist unbekannt, abgelaufen oder verbraucht.",
        )
    return {"status": "ok", "bestaetigt": payload.approved}


@router.post("/stop")
async def stoppen() -> dict:
    ergebnis = await asyncio.to_thread(ausfuehren, "close", {})
    get_guard().leeren()
    return ergebnis
