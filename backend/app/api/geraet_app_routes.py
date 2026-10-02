from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.services.geraet_app_service import get_geraet_app_service

router = APIRouter(tags=["geraet-app"])


@router.get("/api/handy/app")
async def app_info() -> dict:
    return get_geraet_app_service().info()


@router.get("/api/handy/app/teil")
async def app_teil(offset: int = 0) -> dict:
    try:
        return get_geraet_app_service().teil(offset)
    except FileNotFoundError as fehler:
        raise HTTPException(status_code=404, detail=str(fehler))


@router.post("/api/handy/app/holen")
async def app_holen() -> dict:
    try:
        return await get_geraet_app_service().von_github_holen()
    except Exception as fehler:
        raise HTTPException(status_code=502, detail=f"GitHub ist gerade nicht erreichbar: {fehler}")


@router.get("/geraet.apk")
async def app_download():
    pfad = get_geraet_app_service().datei()
    if pfad is None:
        raise HTTPException(status_code=404, detail="Auf diesem Jon liegt noch keine App.")
    return FileResponse(str(pfad), media_type="application/vnd.android.package-archive", filename=pfad.name)


@router.get("/geraet", response_class=HTMLResponse)
async def app_seite() -> str:
    info = get_geraet_app_service().info()
    if not info.get("verfuegbar"):
        knopf = "<p>Auf diesem Jon liegt noch keine App.</p>"
    else:
        megabyte = round(info["groesse"] / 1_048_576)
        knopf = f'<a class="k" href="/geraet.apk">Jon Gerät {info["version"]} laden</a><p class="m">{megabyte} MB · Android</p>'
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Jon Gerät</title>
<style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#05070e;color:#fff;font-family:system-ui,sans-serif;text-align:center}}
main{{padding:32px;max-width:380px}}h1{{font-size:28px;margin:0 0 8px}}p{{color:#aab;line-height:1.5}}.k{{display:block;margin:24px 0 8px;padding:16px 20px;border-radius:30px;background:#d4af37;color:#111;font-weight:700;text-decoration:none}}.m{{font-size:13px}}</style></head>
<body><main><h1>Jon Gerät</h1><p>Lade die App, erlaube das Installieren aus dieser Quelle und scanne danach in Jon am PC den Kopplungscode.</p>{knopf}</main></body></html>"""


@router.get("/api/handy/app/adressen")
async def app_adressen() -> dict:
    from app.core.auth import lan_adressen
    from app.core.config import get_settings
    from app.core.heimnetz import lan_aktiv

    port = get_settings().port
    aktiv = lan_aktiv()
    return {
        **get_geraet_app_service().info(),
        "heimnetz": aktiv,
        "urls": [f"http://{adresse}:{port}/geraet" for adresse in lan_adressen()] if aktiv else [],
    }


@router.post("/api/system/heimnetz")
async def heimnetz(payload: dict) -> dict:
    from app.core.heimnetz import lan_aktiv
    from app.services.settings_service import get_settings_service

    get_settings_service().update({"heimnetz": bool(payload.get("an"))})
    return {"an": bool(payload.get("an")), "aktiv": lan_aktiv(), "neustart": True}


@router.get("/api/system/pi-update")
async def pi_update_stand() -> dict:
    return get_geraet_app_service().pi_update_stand()


@router.post("/api/system/pi-update")
async def pi_update() -> dict:
    try:
        return get_geraet_app_service().pi_update_starten()
    except ValueError as fehler:
        raise HTTPException(status_code=400, detail=str(fehler))
