from __future__ import annotations

import asyncio
import re

AUFGABEN = ("text", "code", "bild", "sehen")
BILD = re.compile(r"(image|flux|sdxl|stable[-_ ]?diffusion|z[-_ ]?image|kolors|hidream|qwen[-_]?image|playground|dall|imagen|sana|omnigen)", re.I)
SEHEN = re.compile(r"(vl\b|-vl|vision|llava|minicpm-?v|gemma-?3|pixtral|moondream|qwen2\.5-?vl|qwen3-?vl|internvl)", re.I)
CODE = re.compile(r"(coder|code|devstral|starcoder|codestral|deepseek-coder)", re.I)
NICHT_TEXT = re.compile(r"(embed|rerank|whisper|tts|bge|nomic)", re.I)
GROESSE = re.compile(r"(\d+(?:\.\d+)?)\s*b\b", re.I)
WOLKE = re.compile(r"[:-]cloud\b", re.I)
BILD_ANBIETER = {"lokalserver"}


def _einstellungen() -> dict:
    from app.services.settings_service import get_settings_service

    return get_settings_service().get()


def aktiv() -> bool:
    return bool(_einstellungen().get("modell_je_aufgabe", True))


def zuordnung() -> dict[str, dict]:
    roh = _einstellungen().get("aufgabenmodelle") or {}
    if not isinstance(roh, dict):
        return {}
    ergebnis = {}
    for aufgabe in AUFGABEN:
        eintrag = roh.get(aufgabe)
        if isinstance(eintrag, dict) and eintrag.get("provider"):
            ergebnis[aufgabe] = {"provider": str(eintrag["provider"]), "model": str(eintrag.get("model", ""))}
    return ergebnis


def speichern(werte: dict) -> dict:
    from app.services.settings_service import get_settings_service

    neu = {}
    for aufgabe in AUFGABEN:
        eintrag = (werte or {}).get(aufgabe)
        if isinstance(eintrag, dict) and str(eintrag.get("provider", "")).strip():
            neu[aufgabe] = {"provider": str(eintrag["provider"]).strip(), "model": str(eintrag.get("model", "")).strip()}
    get_settings_service().update({"aufgabenmodelle": neu})
    return neu


def fuer(aufgabe: str) -> tuple[str, str] | None:
    if not aktiv():
        return None
    eintrag = zuordnung().get(aufgabe)
    if not eintrag:
        return None
    from app.services.offline import aktiv as offline, lokal

    if aufgabe != "bild" and offline() and not lokal(eintrag["provider"], eintrag["model"]):
        return None
    return eintrag["provider"], eintrag["model"]


def sehen_wahl(provider: str, model: str) -> tuple[str, str]:
    gewaehlt = fuer("sehen")
    if gewaehlt and gewaehlt[1]:
        return gewaehlt
    return provider, model


def fuer_chat(aufgabe: str, provider: str, model: str) -> tuple[str, str]:
    gewaehlt = fuer(aufgabe) or (fuer("text") if aufgabe == "code" else None)
    if not gewaehlt or not gewaehlt[1]:
        return provider, model
    return gewaehlt


def _groesse(name: str) -> float:
    treffer = GROESSE.findall(name)
    return max((float(t) for t in treffer), default=0.0)


def einordnen(modelle: list[tuple[str, str]]) -> dict[str, dict]:
    vorschlag: dict[str, dict] = {}
    modelle = [m for m in modelle if not WOLKE.search(m[1])]
    bild = [m for m in modelle if BILD.search(m[1]) and m[0] in BILD_ANBIETER]
    sehen = [m for m in modelle if SEHEN.search(m[1]) and not BILD.search(m[1])]
    code = [m for m in modelle if CODE.search(m[1]) and not BILD.search(m[1])]
    text = [m for m in modelle if not BILD.search(m[1]) and not NICHT_TEXT.search(m[1])]
    if bild:
        vorschlag["bild"] = {"provider": bild[0][0], "model": bild[0][1]}
    if sehen:
        vorschlag["sehen"] = {"provider": sehen[0][0], "model": max(sehen, key=lambda m: _groesse(m[1]))[1]}
    if text:
        groesstes = max(text, key=lambda m: (_groesse(m[1]), not CODE.search(m[1])))
        vorschlag["text"] = {"provider": groesstes[0], "model": groesstes[1]}
    if code:
        bestes = max(code, key=lambda m: _groesse(m[1]))
        vorschlag["code"] = {"provider": bestes[0], "model": bestes[1]}
    elif "text" in vorschlag:
        vorschlag["code"] = dict(vorschlag["text"])
    return vorschlag


async def erkennen() -> dict:
    from app.providers.registry import get_registry

    registry = get_registry().all()
    gefunden: list[tuple[str, str]] = []
    quellen = {}
    for name in ("lokalserver", "ollama", "lmstudio"):
        anbieter = registry.get(name)
        if anbieter is None:
            continue
        try:
            if not anbieter.available():
                continue
            liste = await asyncio.wait_for(anbieter.list_models(), 8)
        except Exception:
            continue
        quellen[name] = list(liste)
        gefunden.extend((name, m) for m in liste)
    try:
        from app.services.studio_service import get_studio_service

        studio = await asyncio.wait_for(get_studio_service().lokale_bildmodelle(), 8)
        for modell in studio:
            gefunden.insert(0, ("lokalserver", modell))
    except Exception:
        pass
    return {"modelle": quellen, "vorschlag": einordnen(gefunden)}
