from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.premium import TEAM_AKTIONEN, Abgelehnt, PremiumNoetig, get_premium

router = APIRouter(prefix="/api")


class Kauf(BaseModel):
    plan: str = Field(default="monat", pattern="^(monat|jahr)$")


class Lizenz(BaseModel):
    token: str = Field(min_length=20, max_length=4000)


class Admin(BaseModel):
    passwort: str = Field(min_length=1, max_length=400)


class Code(BaseModel):
    code: str = Field(min_length=8, max_length=400)


class NeuerCode(BaseModel):
    name: str = Field(default="", max_length=60)
    geraete: int = Field(default=3, ge=1, le=50)
    art: str = Field(default="entwickler", pattern="^(entwickler|premium|admin)$")
    tage: int = Field(default=0, ge=0, le=3650)


class Fehlerbericht(BaseModel):
    text: str = Field(default="", max_length=8000)
    bild: bool = False


class Beta(BaseModel):
    an: bool


class SkillHolen(BaseModel):
    id: str = Field(pattern="^[a-f0-9]{12}$")


class Sperren(BaseModel):
    id: str = Field(pattern="^[a-f0-9]{12}$")
    gesperrt: bool = True


async def ausfuehren(aufruf):
    try:
        return await aufruf
    except PremiumNoetig:
        raise
    except ConnectionError as exc:
        raise HTTPException(503, str(exc))
    except Abgelehnt as exc:
        raise HTTPException(403, str(exc))
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc) or "Die Lizenz konnte nicht verarbeitet werden.")


@router.get("/premium")
async def status() -> dict:
    return get_premium().status()


@router.get("/premium/kostenlos")
async def kostenlos_verfuegbar() -> dict:
    return {"verfuegbar": await get_premium().kostenlos_verfuegbar()}


@router.post("/premium/kostenlos")
async def kostenlos_holen() -> dict:
    return await ausfuehren(get_premium().kostenlos_holen())


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


@router.post("/premium/code")
async def code(daten: Code) -> dict:
    return await ausfuehren(get_premium().einloesen(daten.code))


@router.get("/premium/codes")
async def codes() -> dict:
    return await ausfuehren(get_premium().codes())


@router.post("/premium/codes")
async def code_erstellen(daten: NeuerCode) -> dict:
    return await ausfuehren(get_premium().code_erstellen(daten.name, daten.geraete, daten.art, daten.tage))


@router.post("/premium/team/{aktion:path}")
async def team(aktion: str, daten: dict) -> dict:
    if aktion not in TEAM_AKTIONEN:
        raise HTTPException(404, "Unbekannte Aktion.")
    return await ausfuehren(get_premium().team(aktion, daten))


@router.post("/premium/fehlerbericht")
async def fehlerbericht(daten: Fehlerbericht) -> dict:
    return await ausfuehren(get_premium().fehlerbericht(daten.text, daten.bild))


@router.post("/premium/skill-installieren")
async def skill_installieren(daten: SkillHolen) -> dict:
    return await ausfuehren(get_premium().skill_installieren(daten.id))


@router.post("/premium/beta")
async def beta(daten: Beta) -> dict:
    try:
        return get_premium().beta_setzen(daten.an)
    except ValueError as exc:
        raise HTTPException(403, str(exc))


@router.get("/inspektor")
async def inspektor() -> dict:
    from app.services.inspektor import get_inspektor

    if not get_premium().flag("inspektor"):
        raise HTTPException(403, "Der Jon-Inspektor ist für Entwickler und Admins.")
    return {"eintraege": get_inspektor().liste(), "nutzung": get_inspektor().nutzung()}


@router.post("/inspektor/leeren")
async def inspektor_leeren() -> dict:
    from app.services.inspektor import get_inspektor

    if not get_premium().flag("inspektor"):
        raise HTTPException(403, "Der Jon-Inspektor ist für Entwickler und Admins.")
    get_inspektor().leeren()
    return {"eintraege": []}


@router.post("/premium/codes/sperren")
async def code_sperren(daten: Sperren) -> dict:
    return await ausfuehren(get_premium().code_sperren(daten.id, daten.gesperrt))


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
