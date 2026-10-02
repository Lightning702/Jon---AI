from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.sicherung_service import SicherungFehler, get_sicherung_service

router = APIRouter(prefix="/api/handy/sicherung", tags=["handy-sicherung"])


def _geraet(angegeben: str = "") -> str:
    from app.services.geraete_funktionen import HANDY_KONTEXT

    gebunden = HANDY_KONTEXT.get()
    if gebunden:
        return gebunden
    if angegeben:
        return angegeben
    raise HTTPException(status_code=400, detail="Welches Gerät?")


def _fehler(aufruf):
    try:
        return aufruf()
    except SicherungFehler as fehler:
        raise HTTPException(status_code=400, detail=str(fehler))


@router.post("/start")
async def starten(payload: dict) -> dict:
    return _fehler(lambda: get_sicherung_service().starten(_geraet(), int(payload.get("groesse") or 0)))


@router.post("/teil")
async def teil_senden(payload: dict) -> dict:
    return _fehler(lambda: get_sicherung_service().anhaengen(_geraet(), str(payload.get("marke", "")), str(payload.get("data", ""))))


@router.post("/ende")
async def abschliessen(payload: dict) -> dict:
    return _fehler(lambda: get_sicherung_service().abschliessen(_geraet(), str(payload.get("marke", ""))))


@router.get("/liste")
async def liste(geraet: str = "") -> dict:
    return {"sicherungen": _fehler(lambda: get_sicherung_service().liste(_geraet(geraet)))}


@router.get("/datei")
async def datei(name: str, offset: int = 0, geraet: str = "") -> dict:
    return _fehler(lambda: get_sicherung_service().teil(_geraet(geraet), name, offset))
