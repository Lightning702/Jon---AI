from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.services.design_service import get_design_service, typ

router = APIRouter(prefix="/api/design")


@router.get("/hintergruende")
async def liste() -> dict:
    return {"eintraege": get_design_service().liste()}


@router.post("/hintergruende")
async def hochladen(request: Request, name: str = "") -> dict:
    try:
        return await get_design_service().hochladen(name, request.stream())
    except ValueError as fehler:
        raise HTTPException(status_code=400, detail=str(fehler))


@router.get("/hintergruende/{name}")
async def datei(name: str) -> FileResponse:
    pfad = get_design_service().finden(name)
    if pfad is None:
        raise HTTPException(status_code=404, detail="Diesen Hintergrund gibt es nicht mehr.")
    return FileResponse(pfad, media_type=typ(pfad), headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.delete("/hintergruende/{name}")
async def loeschen(name: str) -> dict:
    if not get_design_service().loeschen(name):
        raise HTTPException(status_code=404, detail="Diesen Hintergrund gibt es nicht mehr.")
    return {"geloescht": True}
