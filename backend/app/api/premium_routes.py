from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.premium import PremiumNoetig, get_premium

router = APIRouter(prefix="/api")


class Kauf(BaseModel):
    plan: str = Field(default="monat", pattern="^(monat|jahr)$")


class Lizenz(BaseModel):
    token: str = Field(min_length=20, max_length=4000)


class Admin(BaseModel):
    passwort: str = Field(min_length=1, max_length=400)


async def ausfuehren(aufruf):
    try:
        return await aufruf
    except PremiumNoetig:
        raise
    except ConnectionError as exc:
        raise HTTPException(503, str(exc))
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc) or "Die Lizenz konnte nicht verarbeitet werden.")


@router.get("/premium")
async def status() -> dict:
    return get_premium().status()


@router.post("/premium/kaufen")
async def kaufen(daten: Kauf) -> dict:
    return await ausfuehren(get_premium().kaufen(daten.plan))


@router.post("/premium/abholen")
async def abholen() -> dict:
    return await ausfuehren(get_premium().abholen())


@router.post("/premium/lizenz")
async def lizenz(daten: Lizenz) -> dict:
    return await ausfuehren(get_premium().eingeben(daten.token))


@router.post("/premium/admin")
async def admin(daten: Admin) -> dict:
    return await ausfuehren(get_premium().admin(daten.passwort))


@router.post("/premium/erneuern")
async def erneuern() -> dict:
    return await ausfuehren(get_premium().erneuern())


@router.post("/premium/portal")
async def portal() -> dict:
    return await ausfuehren(get_premium().portal())


@router.post("/premium/abmelden")
async def abmelden() -> dict:
    get_premium().offen = {}
    return get_premium().abmelden()


class Sync(BaseModel):
    passwort: str = Field(min_length=8, max_length=400)


@router.get("/premium/sync")
async def sync_info() -> dict:
    from app.services import cloud_sync

    return await ausfuehren(cloud_sync.info())


@router.post("/premium/sync/hochladen")
async def sync_hochladen(daten: Sync) -> dict:
    from app.services import cloud_sync

    return await ausfuehren(cloud_sync.hochladen(daten.passwort))


@router.post("/premium/sync/holen")
async def sync_holen(daten: Sync) -> dict:
    from app.services import cloud_sync

    return await ausfuehren(cloud_sync.holen(daten.passwort))
