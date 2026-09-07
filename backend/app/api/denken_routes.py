from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.services.auftrag_service import get_auftrag_service
from app.services.benchmark_service import get_benchmark_service
from app.services.budget_service import get_budget_service
from app.services.ereignis_service import get_ereignis_service
from app.services.handlungsraum_service import get_handlungsraum_service
from app.services.initiative_service import get_initiative_service
from app.services.konsolidierung_service import get_konsolidierung_service
from app.services.selbst_service import get_selbst_service
from app.services.weltmodell_service import get_weltmodell_service
from app.services.ziel_service import get_ziel_service

router = APIRouter(prefix="/api/denken")


@router.get("/zustand")
async def zustand() -> dict:
    return get_handlungsraum_service().zustand()


@router.get("/ziele")
async def ziele() -> dict:
    dienst = get_ziel_service()
    return {"offen": dienst.liste(), "faellig": dienst.faellig(3)}


@router.post("/ziele")
async def ziel_anlegen(payload: dict) -> dict:
    ergebnis = get_ziel_service().anlegen(
        str(payload.get("titel", "")),
        str(payload.get("beschreibung", "")),
        str(payload.get("frist", "")),
        str(payload.get("naechster_schritt", "")),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.patch("/ziele/{kennung}")
async def ziel_aendern(kennung: str, payload: dict) -> dict:
    ergebnis = get_ziel_service().aktualisieren(
        kennung,
        str(payload.get("zustand", "")),
        str(payload.get("naechster_schritt", "")),
        payload.get("fortschritt"),
        str(payload.get("frist", "")),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=404, detail=ergebnis["error"])
    return ergebnis


@router.delete("/ziele/{kennung}")
async def ziel_loeschen(kennung: str) -> dict:
    return {"geloescht": get_ziel_service().loeschen(kennung)}


@router.get("/verlauf")
async def verlauf(zeitraum: str = "heute", thema: str = "") -> dict:
    dienst = get_ereignis_service()
    bild = dienst.tagesbild(zeitraum)
    if thema:
        bild["treffer"] = dienst.suchen(thema, limit=15)
    return bild


@router.get("/initiative")
async def initiative() -> dict:
    dienst = get_initiative_service()
    return {"vorschlaege": dienst.alle(), "offen": dienst.offene()}


@router.post("/initiative/lauf")
async def initiative_lauf() -> dict:
    return await get_initiative_service().lauf(erzwingen=True)


@router.post("/initiative/{kennung}")
async def initiative_entscheiden(kennung: str, payload: dict) -> dict:
    dienst = get_initiative_service()
    if payload.get("ausfuehren"):
        return await dienst.ausfuehren(kennung)
    ergebnis = dienst.entscheiden(kennung, bool(payload.get("angenommen", True)))
    if ergebnis.get("error"):
        raise HTTPException(status_code=404, detail=ergebnis["error"])
    return ergebnis


@router.get("/selbstbild")
async def selbstbild(aufgabe: str = "") -> dict:
    dienst = get_selbst_service()
    return dienst.kann_ich(aufgabe) if aufgabe else dienst.selbstbild()


@router.get("/weltmodell")
async def weltmodell(art: str = "", name: str = "") -> dict:
    dienst = get_weltmodell_service()
    if name:
        return dienst.umfeld(name)
    return {"entitaeten": dienst.alle(art, 200)}


@router.get("/auftraege")
async def auftraege() -> dict:
    dienst = get_auftrag_service()
    return {"offen": dienst.offene(), "alle": dienst.liste(limit=25)}


@router.get("/budget")
async def budget() -> dict:
    return get_budget_service().stand()


@router.post("/konsolidieren")
async def konsolidieren(payload: dict | None = None) -> dict:
    tag = str((payload or {}).get("tag", "gestern"))
    return await get_konsolidierung_service().lauf(tag)


@router.get("/benchmark")
async def benchmark(bereich: str = "") -> dict:
    return await asyncio.to_thread(get_benchmark_service().lauf, bereich)
