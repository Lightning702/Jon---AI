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


@router.post("/oeffnen")
async def adresse_oeffnen(payload: dict) -> dict:
    from app.services.browserwahl import oeffnen as browser_oeffnen

    adresse = str(payload.get("url", "")).strip()
    if not adresse:
        raise HTTPException(status_code=400, detail="Keine Adresse angegeben.")
    ergebnis = await asyncio.to_thread(
        browser_oeffnen, adresse, str(payload.get("browser", ""))
    )
    if not ergebnis.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=ergebnis.get("fehler")
            or ergebnis.get("error")
            or "Die Seite liess sich nicht oeffnen.",
        )
    return ergebnis


@router.get("/wahl")
async def browser_wahl() -> dict:
    from app.services.browserwahl import name, verfuegbare, wahl

    return {"browser": wahl(), "name": name(), "verfuegbar": verfuegbare()}


@router.get("/privat/auftrag")
async def privat_auftrag(warten: float = 25.0, fenster: bool = False) -> dict:
    from app.services.browser import privatbruecke

    privatbruecke.melden(fenster)
    grenze = max(0.0, min(float(warten or 0.0), 50.0))
    ende = asyncio.get_event_loop().time() + grenze
    while True:
        auftrag = privatbruecke.abholen()
        if auftrag is not None:
            auftrag["skripte"] = privatbruecke.skripte()
            return {"auftrag": auftrag}
        if asyncio.get_event_loop().time() >= ende:
            return {"auftrag": None}
        await asyncio.sleep(0.12)


@router.post("/privat/ergebnis")
async def privat_ergebnis(payload: dict) -> dict:
    from app.services.browser import privatbruecke

    privatbruecke.melden(bool(payload.get("fenster", True)), payload.get("seite"))
    angekommen = privatbruecke.antworten(
        str(payload.get("id", "")),
        bool(payload.get("ok", False)),
        payload.get("daten") if isinstance(payload.get("daten"), dict) else {},
        str(payload.get("fehler", "")),
    )
    return {"ok": True, "angekommen": angekommen}


@router.get("/privat/stand")
async def privat_stand() -> dict:
    from app.services.browser import privatbruecke

    return privatbruecke.stand()


@router.get("/privat/skripte")
async def privat_skripte() -> dict:
    from app.services.browser import privatbruecke

    return privatbruecke.skripte()


@router.post("/privat/trennen")
async def privat_trennen() -> dict:
    from app.services.browser import privatbruecke

    privatbruecke.zuruecksetzen()
    return {"ok": True}
