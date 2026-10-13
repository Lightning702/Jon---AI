from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.handy_service import HandyFehler, get_handy_service
from app.services.oekosystem_service import OekoFehler, get_oekosystem

router = APIRouter(prefix="/api/oekosystem")


class BesitzerIn(BaseModel):
    besitzer: str = Field(default="", max_length=60)


class TypIn(BaseModel):
    typ: str = Field(default="handy", max_length=12)


class KlingelnIn(BaseModel):
    ziel: str = Field(default="", max_length=80)
    sekunden: int = Field(default=30, ge=5, le=120)


class FrageIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    verlauf: list = Field(default_factory=list)
    gespraech: str = Field(default="", max_length=64)
    persona: str = Field(default="junior", pattern="^(papa|junior|funke)$")


class GedaechtnisIn(BaseModel):
    eintraege: list = Field(default_factory=list)
    seit: str = Field(default="", max_length=64)


def _geraet_im_kontext() -> str:
    from app.services.geraete_funktionen import HANDY_KONTEXT

    return str(HANDY_KONTEXT.get() or "")


def _fehler(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("")
async def uebersicht(pruefen: bool = False) -> dict:
    return await get_oekosystem().uebersicht(verbund_pruefen=pruefen)


@router.get("/aktiv")
async def aktiv() -> dict:
    return get_oekosystem().aktiv()


@router.get("/standorte")
async def standorte(lokal: bool = False) -> dict:
    return await get_oekosystem().standorte(nur_lokal=lokal)


@router.get("/geraete/{geraete_id}/spur")
async def spur(geraete_id: str) -> dict:
    return {"spur": get_oekosystem().spur(geraete_id)}


@router.post("/geraete/{geraete_id}/standort")
async def standort_anfragen(geraete_id: str) -> dict:
    try:
        return {"ok": True, "standort": await get_oekosystem().standort_anfragen(geraete_id, _fragender())}
    except OekoFehler as exc:
        raise _fehler(exc)


@router.post("/geraete/{geraete_id}/besitzer")
async def besitzer(geraete_id: str, eingabe: BesitzerIn) -> dict:
    try:
        return get_handy_service().besitzer_setzen(geraete_id, eingabe.besitzer)
    except HandyFehler as exc:
        raise _fehler(exc)


@router.post("/geraete/{geraete_id}/typ")
async def typ(geraete_id: str, eingabe: TypIn) -> dict:
    try:
        return get_handy_service().typ_setzen(geraete_id, eingabe.typ)
    except HandyFehler as exc:
        raise _fehler(exc)


def _fragender() -> str:
    kennung = _geraet_im_kontext()
    if kennung:
        eintrag = get_handy_service()._geraet(kennung) or {}
        return str(eintrag.get("besitzer") or eintrag.get("name") or "ein Jon-Gerät")
    return get_oekosystem().eigener_name()


@router.get("/wo-ist")
async def wo_ist(person: str, fragender: str = "", weiter: bool = True) -> dict:
    try:
        return await get_oekosystem().wo_ist(person, fragender or _fragender(), weiterfragen=weiter)
    except OekoFehler as exc:
        return {"ok": False, "fehler": str(exc)}


@router.post("/klingeln")
async def klingeln(eingabe: KlingelnIn) -> dict:
    try:
        return await get_oekosystem().klingeln(_geraet_im_kontext(), eingabe.ziel, eingabe.sekunden)
    except OekoFehler as exc:
        raise _fehler(exc)


@router.post("/uhr-koppeln")
async def uhr_koppeln() -> dict:
    kennung = _geraet_im_kontext()
    if not kennung:
        raise HTTPException(status_code=400, detail="Eine Uhr wird über das gekoppelte Handy verbunden.")
    try:
        return await get_oekosystem().uhr_koppeln(kennung)
    except OekoFehler as exc:
        raise _fehler(exc)


@router.post("/frage")
async def frage(eingabe: FrageIn) -> dict:
    from app.api.routes import _chat_service
    from app.schemas import ChatIn, MessageIn

    kennung = _geraet_im_kontext()
    get_oekosystem().aktiv_merken(kennung or "pc")
    nachrichten = []
    for eintrag in list(eingabe.verlauf)[-8:]:
        if isinstance(eintrag, dict) and eintrag.get("role") in ("user", "assistant") and str(eintrag.get("content") or "").strip():
            nachrichten.append(MessageIn(role=eintrag["role"], content=str(eintrag["content"])[:4000]))
    nachrichten.append(MessageIn(role="user", content=eingabe.text.strip()))
    nutzlast = ChatIn(
        messages=nachrichten,
        conversation_id=eingabe.gespraech or None,
        persist=True,
        source="uhr",
        tool_mode="allow",
        werkzeuge="klein",
        persona=eingabe.persona,
    )
    antwort = ""
    gespraech = eingabe.gespraech
    fehler = ""
    werkzeuge: list[str] = []
    async for ereignis in _chat_service.stream(nutzlast):
        art = str(ereignis.get("type", ""))
        if art == "content":
            antwort += str(ereignis.get("delta", ""))
        elif art == "meta" and ereignis.get("conversation_id"):
            gespraech = str(ereignis["conversation_id"])
        elif art == "error":
            fehler = str(ereignis.get("message") or "Jon konnte nicht antworten.")
        elif art == "tool" and ereignis.get("name") and str(ereignis["name"]) not in werkzeuge:
            werkzeuge.append(str(ereignis["name"]))
    return {"antwort": antwort.strip()[:6000], "gespraech": gespraech, "fehler": fehler if not antwort.strip() else "", "werkzeuge": werkzeuge[:12]}


@router.get("/gedaechtnis")
async def gedaechtnis_holen(seit: str = "") -> dict:
    import asyncio

    kennung = _geraet_im_kontext()
    ohne = f"geraet:{kennung}"[:32] if kennung else ""
    return await asyncio.to_thread(get_oekosystem().gedaechtnis_export, seit, ohne)


@router.post("/gedaechtnis")
async def gedaechtnis_tauschen(eingabe: GedaechtnisIn) -> dict:
    return await get_oekosystem().gedaechtnis_tauschen(_geraet_im_kontext(), eingabe.eintraege, eingabe.seit)


@router.post("/gedaechtnis/abgleichen")
async def gedaechtnis_abgleichen() -> dict:
    return await get_oekosystem().gedaechtnis_abgleichen()
