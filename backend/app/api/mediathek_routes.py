from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.services.mediathek_service import get_mediathek_service

router = APIRouter(prefix="/api/mediathek")
BROCKEN = 512 * 1024


def _typ(pfad: Path) -> str:
    geraten, _ = mimetypes.guess_type(pfad.name)
    if geraten:
        return geraten
    return "audio/mpeg" if pfad.suffix.lower() == ".mp3" else "video/mp4"


def _bereich(kopf: str, groesse: int) -> tuple[int, int] | None:
    if not kopf.startswith("bytes="):
        return None
    roh = kopf[6:].split(",")[0].strip()
    anfang, _, ende = roh.partition("-")
    try:
        if anfang:
            von = int(anfang)
            bis = int(ende) if ende else groesse - 1
        else:
            laenge = int(ende or 0)
            if laenge <= 0:
                return None
            von = max(0, groesse - laenge)
            bis = groesse - 1
    except ValueError:
        return None
    if von >= groesse or von > bis:
        return None
    return von, min(bis, groesse - 1)


@router.get("")
async def liste() -> dict:
    return get_mediathek_service().liste()


@router.get("/datei/{kennung}")
async def datei(kennung: str, request: Request):
    gefunden = get_mediathek_service().finden(kennung)
    if gefunden is None:
        raise HTTPException(status_code=404, detail="Diese Aufnahme gibt es nicht mehr.")
    pfad, eintrag = gefunden
    groesse = pfad.stat().st_size
    typ = _typ(pfad)
    bereich = _bereich(request.headers.get("range", ""), groesse)
    von, bis = bereich if bereich else (0, groesse - 1)

    def lesen():
        offen = pfad.open("rb")
        try:
            offen.seek(von)
            rest = bis - von + 1
            while rest > 0:
                stueck = offen.read(min(BROCKEN, rest))
                if not stueck:
                    break
                rest -= len(stueck)
                yield stueck
        finally:
            offen.close()

    kopf = {
        "Content-Length": str(bis - von + 1),
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Disposition": f'inline; filename="{eintrag["id"]}{pfad.suffix}"',
    }
    if bereich:
        kopf["Content-Range"] = f"bytes {von}-{bis}/{groesse}"
    return StreamingResponse(
        lesen(),
        status_code=206 if bereich else 200,
        media_type=typ,
        headers=kopf,
    )


@router.get("/bild/{kennung}")
async def bild(kennung: str):
    pfad = get_mediathek_service().bild(kennung)
    if pfad is None:
        raise HTTPException(status_code=404, detail="Kein Bild vorhanden.")
    return FileResponse(pfad, media_type="image/jpeg")


@router.delete("/{kennung}")
async def loeschen(kennung: str) -> dict:
    if not get_mediathek_service().loeschen(kennung):
        raise HTTPException(status_code=404, detail="Diese Aufnahme gibt es nicht mehr.")
    return {"geloescht": True}
