from __future__ import annotations

import platform
import time

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter(prefix="/api")
ARTEN = {"problem": "Problem", "fehler": "Fehler melden", "vorschlag": "Vorschlag", "standard": "Neue Standard-Funktion", "premium": "Neue Premium-Funktion", "frage": "Frage"}
SUPPORT_EMAIL = "felix.heinisch12@gmail.com"
_gesendet: list[float] = []


class Nachricht(BaseModel):
    art: str = Field(default="problem", pattern="^(problem|fehler|vorschlag|standard|premium|frage)$")
    betreff: str = Field(min_length=3, max_length=160)
    nachricht: str = Field(min_length=10, max_length=8000)
    email: str = Field(default="", max_length=200, pattern=r"^$|^[^@\s]+@[^@\s]+\.[^@\s]+$")
    infos: bool = True


def systeminfo() -> dict:
    from app.services.premium import get_premium

    settings = get_settings()
    return {"version": settings.app_version, "stufe": get_premium().status()["name"], "system": f"{platform.system()} {platform.release()} · Python {platform.python_version()}"}


@router.get("/support")
async def support_info() -> dict:
    return {"email": SUPPORT_EMAIL, "arten": ARTEN, **systeminfo()}


@router.post("/support")
async def support_senden(daten: Nachricht) -> dict:
    jetzt = time.time()
    _gesendet[:] = [t for t in _gesendet if jetzt - t < 3600]
    if len(_gesendet) >= 5:
        raise HTTPException(429, "Du hast in der letzten Stunde schon fünf Nachrichten geschickt. Bitte versuch es später noch einmal.")
    felder = {"form-name": "support", "art": ARTEN[daten.art], "betreff": daten.betreff.strip(), "nachricht": daten.nachricht.strip(), "email": daten.email.strip(), "bot-feld": ""}
    if daten.infos:
        felder.update(systeminfo())
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
            antwort = await client.post(get_settings().jon_support_url, data=felder, headers={"Accept": "text/html"})
    except httpx.HTTPError:
        raise HTTPException(503, f"Die Nachricht konnte gerade nicht gesendet werden. Schreib direkt an {SUPPORT_EMAIL}.")
    if antwort.status_code >= 400:
        raise HTTPException(502, f"Der Support-Server hat die Nachricht abgelehnt (Fehler {antwort.status_code}). Schreib direkt an {SUPPORT_EMAIL}.")
    _gesendet.append(jetzt)
    return {"ok": True, "email": SUPPORT_EMAIL}
