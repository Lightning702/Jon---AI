from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.zeit_service import ZeitFehler, get_zeit_service

router = APIRouter(prefix="/api/zeit")


@router.get("")
async def stand() -> dict:
    return get_zeit_service().stand()


@router.get("/neu")
async def neu() -> dict:
    return get_zeit_service().neue()


@router.post("")
async def starten(payload: dict) -> dict:
    try:
        return get_zeit_service().starten(
            str(payload.get("art", "stoppuhr")),
            int(payload.get("sekunden", 0) or 0),
            str(payload.get("titel", "")),
            str(payload.get("quelle", "app")),
            str(payload.get("uhrzeit", "")),
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


@router.post("/{uhr_id}/anpassen")
async def anpassen(uhr_id: str, payload: dict) -> dict:
    try:
        return get_zeit_service().anpassen(
            uhr_id, float(payload.get("sekunden", 0) or 0)
        )
    except ZeitFehler as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Ungueltige Dauer.")


@router.post("/{uhr_id}/neustart")
async def neustart(uhr_id: str) -> dict:
    try:
        return get_zeit_service().neustarten(uhr_id)
    except ZeitFehler as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{uhr_id}/ruhe")
async def ruhe(uhr_id: str) -> dict:
    try:
        return get_zeit_service().ruhe(uhr_id)
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
