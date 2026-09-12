from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import plattform
from app.services.blender_service import get_blender_service
from app.services.dateiindex_service import get_dateiindex_service, karte
from app.services.dateiraum_service import get_dateiraum_service
from app.services.dokument_service import get_dokument_service
from app.services.umgebung_service import get_umgebung_service

router = APIRouter(prefix="/api/dateien")


def _geprueft(pfad: str) -> Path:
    ziel = Path(unquote(str(pfad or ""))).expanduser()
    erlaubt, grund = get_dateiraum_service().frei(ziel)
    if not erlaubt:
        raise HTTPException(status_code=403, detail=grund)
    return ziel


@router.get("/raum")
async def raum() -> dict:
    return get_dateiraum_service().stand()


@router.get("/liste")
async def liste(art: str = "", projekt: str = "", limit: int = 50) -> dict:
    return {"dateien": get_dateiindex_service().liste(art, projekt, limit)}


@router.get("/suche")
async def suche(frage: str = "", limit: int = 12) -> dict:
    treffer = get_dateiindex_service().suchen(frage, limit)
    return {
        "treffer": treffer,
        "dateien": [
            karte(e["pfad"], e.get("projekt", ""), e.get("titel", ""))
            for e in treffer
            if e.get("vorhanden", True)
        ],
    }


@router.get("/stand")
async def stand() -> dict:
    return get_dateiindex_service().stand()


@router.get("/karte")
async def datei_karte(pfad: str) -> dict:
    ziel = _geprueft(pfad)
    if not ziel.exists():
        raise HTTPException(status_code=404, detail="Diese Datei gibt es nicht mehr.")
    return karte(ziel)


@router.get("/inhalt")
async def inhalt(pfad: str):
    ziel = _geprueft(pfad)
    if not ziel.is_file():
        raise HTTPException(status_code=404, detail="Diese Datei gibt es nicht mehr.")
    return FileResponse(str(ziel), filename=ziel.name)


@router.post("/oeffnen")
async def oeffnen(payload: dict) -> dict:
    ziel = _geprueft(str(payload.get("pfad", "")))
    if payload.get("ordner"):
        ergebnis = plattform.ordner_oeffnen(ziel)
    else:
        ergebnis = plattform.datei_oeffnen(ziel)
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.post("/ordner")
async def ordner_anlegen(payload: dict) -> dict:
    name = str(payload.get("name", "")).strip()
    ort = str(payload.get("ort", "")).strip()
    ziel = f"{ort}/{name}" if ort and name else (ort or name)
    ergebnis = get_dateiraum_service().zielordner(ziel)
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.post("/erstellen")
async def erstellen(payload: dict) -> dict:
    ergebnis = await asyncio.to_thread(
        get_dokument_service().erstellen,
        str(payload.get("art", "txt")),
        str(payload.get("titel", "")),
        payload.get("inhalt", ""),
        str(payload.get("ort", "")),
        str(payload.get("dateiname", "")),
        str(payload.get("projekt", "")),
        "",
        "app",
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.delete("/index/{kennung}")
async def index_vergessen(kennung: str) -> dict:
    return {"vergessen": get_dateiindex_service().vergessen(kennung)}


@router.get("/umgebung")
async def umgebung(neu: bool = False) -> dict:
    return await asyncio.to_thread(get_umgebung_service().pruefen, neu)


@router.get("/blender")
async def blender(neu: bool = False) -> dict:
    return await asyncio.to_thread(get_blender_service().gefunden, neu)


@router.post("/blender/szene")
async def blender_szene(payload: dict) -> dict:
    ergebnis = await get_blender_service().szene(
        str(payload.get("auftrag", "")),
        str(payload.get("projekt", "")),
        str(payload.get("ort", "")),
        bool(payload.get("rendern", True)),
        str(payload.get("export", "")),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.post("/blender/render")
async def blender_render(payload: dict) -> dict:
    ergebnis = await asyncio.to_thread(
        get_blender_service().rendern,
        str(payload.get("datei", "")),
        int(payload.get("breite", 1280) or 1280),
        int(payload.get("hoehe", 720) or 720),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.post("/blender/export")
async def blender_export(payload: dict) -> dict:
    ergebnis = await asyncio.to_thread(
        get_blender_service().exportieren,
        str(payload.get("datei", "")),
        str(payload.get("format", "glb")),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis
