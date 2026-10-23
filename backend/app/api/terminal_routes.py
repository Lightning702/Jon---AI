from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from app.core.config import get_settings, lebendes_modell
from app.core.fehler import leise
from app.providers.openai_compatible import OpenAICompatibleProvider, denk_extra
from app.providers.registry import get_registry
from app.services.settings_service import get_settings_service

router = APIRouter()

NICHT_DURCHREICHEN = {"lmstudio"}


def _basis(name: str, anbieter) -> str:
    if name == "ollama":
        try:
            return anbieter._service.openai_base_url().rstrip("/")
        except Exception:
            return ""
    return str(getattr(anbieter, "_base_url", "") or "").rstrip("/")


def _jon_wahl() -> tuple[str, str]:
    from app.services.chat_service import grundmodell

    gespeichert, modell = get_settings_service().selection()
    anbieter = gespeichert or get_settings().default_provider
    modell = modell or grundmodell(anbieter, "jon") or get_settings().jon_model
    return anbieter, lebendes_modell(modell, anbieter)


def _durchreichbar() -> dict[str, object]:
    ergebnis = {}
    for name, anbieter in get_registry().all().items():
        if name in NICHT_DURCHREICHEN:
            continue
        if not isinstance(anbieter, OpenAICompatibleProvider) and name != "ollama":
            continue
        try:
            if anbieter.available():
                ergebnis[name] = anbieter
        except Exception as fehler:
            leise(fehler, "terminal_routes")
    return ergebnis


def _ziel(modell: str) -> tuple[str, str, object]:
    anbieter = _durchreichbar()
    if not modell or modell in ("jon", "auto", "standard"):
        name, wahl = _jon_wahl()
        if name not in anbieter:
            if "felworks" in anbieter:
                name, wahl = "felworks", list(getattr(anbieter["felworks"], "_default_models", []) or [wahl])[0]
            elif anbieter:
                name = next(iter(anbieter))
                wahl = list(getattr(anbieter[name], "_default_models", []) or [wahl])[0]
            else:
                raise HTTPException(503, "In Jon ist noch kein Anbieter mit Schlüssel eingerichtet.")
        return name, wahl, anbieter[name]
    if "/" in modell:
        vorne, rest = modell.split("/", 1)
        if vorne in anbieter:
            return vorne, rest, anbieter[vorne]
    name, _ = _jon_wahl()
    if name in anbieter:
        return name, modell, anbieter[name]
    raise HTTPException(404, f"Das Modell {modell} kennt Jon nicht.")


@router.get("/api/terminal/hallo")
async def hallo() -> dict:
    from app.services.nutzer import nutzername

    anbieter, modell = _jon_wahl()
    try:
        wer = nutzername()
    except Exception:
        wer = ""
    return {"jon": True, "version": get_settings().app_version, "anbieter": anbieter, "modell": modell, "bereit": sorted(_durchreichbar()), "name": wer}


@router.get("/api/llm/v1/models")
async def modelle() -> dict:
    daten = [{"id": "jon", "object": "model", "owned_by": "jon"}]
    for name, anbieter in _durchreichbar().items():
        try:
            liste = await asyncio.wait_for(anbieter.list_models(), 6)
        except Exception:
            liste = list(getattr(anbieter, "_default_models", []) or [])
        for eintrag in liste[:80]:
            daten.append({"id": f"{name}/{eintrag}", "object": "model", "owned_by": name})
    return {"object": "list", "data": daten}


@router.post("/api/llm/v1/chat/completions")
async def vervollstaendigen(request: Request):
    from app.core.netzweg import async_client

    try:
        koerper = await request.json()
    except ValueError:
        raise HTTPException(400, "Ungültige Anfrage.")
    if not isinstance(koerper, dict) or not isinstance(koerper.get("messages"), list):
        raise HTTPException(400, "Ungültige Anfrage.")
    name, modell, anbieter = _ziel(str(koerper.get("model") or ""))
    koerper["model"] = modell
    wunsch = koerper.pop("jon_denken", None)
    if "chat_template_kwargs" not in koerper:
        koerper.update(denk_extra(modell, wunsch if isinstance(wunsch, bool) else None))
    basis = _basis(name, anbieter)
    if not basis:
        raise HTTPException(503, f"{name} ist gerade nicht erreichbar.")
    schluessel = ""
    try:
        schluessel = anbieter._key("jon") or ""
    except Exception as fehler:
        leise(fehler, "terminal_routes")
    kopf = {"Content-Type": "application/json", "X-Jon-Anbieter": name}
    if schluessel:
        kopf["Authorization"] = f"Bearer {schluessel}"
    if koerper.get("stream"):
        client = async_client(timeout=httpx.Timeout(300, connect=20))
        antwort = await client.send(client.build_request("POST", f"{basis}/chat/completions", json=koerper, headers={**kopf, "Accept": "text/event-stream"}), stream=True)
        if antwort.status_code >= 400:
            inhalt = await antwort.aread()
            await antwort.aclose()
            await client.aclose()
            return Response(content=inhalt, status_code=antwort.status_code, media_type="application/json")

        async def weiter():
            try:
                async for stueck in antwort.aiter_raw():
                    yield stueck
            finally:
                await antwort.aclose()
                await client.aclose()

        return StreamingResponse(weiter(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no", "X-Jon-Anbieter": name, "X-Jon-Modell": modell})
    async with async_client(timeout=300) as client:
        antwort = await client.post(f"{basis}/chat/completions", json=koerper, headers=kopf)
    return Response(content=antwort.content, status_code=antwort.status_code, media_type="application/json", headers={"X-Jon-Anbieter": name, "X-Jon-Modell": modell})
