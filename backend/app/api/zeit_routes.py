from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.zeit_service import ZeitFehler, get_zeit_service

router = APIRouter(prefix="/api/zeit")


@router.get("")
async def stand() -> dict:
    return get_zeit_service().stand()


@router.post("")
async def starten(payload: dict) -> dict:
    try:
        return get_zeit_service().starten(
            str(payload.get("art", "stoppuhr")),
            int(payload.get("sekunden", 0) or 0),
            str(payload.get("titel", "")),
        )
    except ZeitFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Ungueltige Dauer.")


@router.post("/{uhr_id}/pause")
async def pausieren(uhr_id: str) -> dict:
    try:
        return get_zeit_service().pausieren(uhr_id)
    except ZeitFehler as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{uhr_id}/weiter")
async def weiter(uhr_id: str) -> dict:
    try:
        return get_zeit_service().weiter(uhr_id)
    except ZeitFehler as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{uhr_id}")
async def stoppen(uhr_id: str) -> dict:
    try:
        return get_zeit_service().stoppen(uhr_id)
    except ZeitFehler as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("")
async def alle_stoppen() -> dict:
    return get_zeit_service().stoppen()
