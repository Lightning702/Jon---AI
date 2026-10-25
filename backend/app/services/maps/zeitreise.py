from __future__ import annotations

import re
from typing import Any

import httpx

from .http import cached, get_json, store, user_agent
from .overpass import _MIRRORS

WAYBACK_CONFIG = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"
MAX_SPANNE = 0.05
WARTEZEIT = 75.0

_JAHR = re.compile(r"(?<!\d)(-?\d{3,4})(?!\d)")
_JAHRHUNDERT = re.compile(r"\bC\s?(\d{1,2})\b", re.I)


def jahr_aus(wert: str) -> int | None:
    text = str(wert or "").strip()
    if not text:
        return None
    jahrhundert = _JAHRHUNDERT.search(text)
    if jahrhundert and not _JAHR.search(text):
        return (int(jahrhundert.group(1)) - 1) * 100 + 50
    treffer = _JAHR.search(text.replace("~", " "))
    if not treffer:
        return None
    jahr = int(treffer.group(1))
    if jahr < -3000 or jahr > 2200:
        return None
    return jahr


def luftbild_liste(daten: Any) -> list[dict[str, Any]]:
    if not isinstance(daten, dict):
        return []
    bilder: list[dict[str, Any]] = []
    for release, eintrag in daten.items():
        if not isinstance(eintrag, dict):
            continue
        titel = str(eintrag.get("itemTitle", ""))
        datum = re.search(r"(\d{4})-(\d{2})-(\d{2})", titel)
        adresse = str(eintrag.get("itemURL", ""))
        if not datum or "{level}" not in adresse:
            continue
        bilder.append(
            {
                "release": int(release) if str(release).isdigit() else str(release),
                "datum": datum.group(0),
                "jahr": int(datum.group(1)),
                "url": adresse.replace("{level}", "{z}").replace("{row}", "{y}").replace("{col}", "{x}"),
            }
        )
    bilder.sort(key=lambda bild: bild["datum"])
    return bilder


async def luftbilder() -> list[dict[str, Any]]:
    try:
        daten = await get_json(WAYBACK_CONFIG, ttl=86400.0, bucket="wayback", min_interval=1.0)
    except Exception:
        return []
    return luftbild_liste(daten)


def baujahr_abfrage(sued: float, west: float, nord: float, ost: float) -> str:
    rahmen = f"({sued:.5f},{west:.5f},{nord:.5f},{ost:.5f})"
    teile = "".join(
        f'way["{schluessel}"]["{datum}"]{rahmen};'
        for schluessel in ("building", "building:part")
        for datum in ("start_date", "construction_date")
    )
    return f"[out:json][timeout:60];({teile});out tags;"


def baujahre_aus(daten: Any) -> list[list[int]]:
    elemente = daten.get("elements") if isinstance(daten, dict) else None
    if not isinstance(elemente, list):
        return []
    gesehen: dict[int, int] = {}
    for element in elemente:
        if not isinstance(element, dict) or element.get("type") != "way":
            continue
        tags = element.get("tags") or {}
        jahr = jahr_aus(tags.get("start_date", "")) or jahr_aus(tags.get("construction_date", ""))
        kennung = element.get("id")
        if jahr is None or not isinstance(kennung, int):
            continue
        gesehen[kennung] = jahr
    return [[kennung, jahr] for kennung, jahr in gesehen.items()]


async def baujahre(sued: float, west: float, nord: float, ost: float) -> dict[str, Any]:
    if nord < sued:
        sued, nord = nord, sued
    if ost < west:
        west, ost = ost, west
    mitte_lat = (sued + nord) / 2
    mitte_lon = (west + ost) / 2
    halb = MAX_SPANNE / 2
    sued, nord = max(-85.0, max(sued, mitte_lat - halb)), min(85.0, min(nord, mitte_lat + halb))
    west, ost = max(-180.0, max(west, mitte_lon - halb)), min(180.0, min(ost, mitte_lon + halb))
    rahmen = [sued, west, nord, ost]
    abfrage = baujahr_abfrage(sued, west, nord, ost)
    schluessel = f"zeitreise {abfrage}"
    treffer = await cached(schluessel, 86400.0)
    if treffer is not None:
        return {"gebaeude": treffer, "rahmen": rahmen}
    fehler = "Overpass hat nicht geantwortet"
    async with httpx.AsyncClient(timeout=httpx.Timeout(WARTEZEIT, connect=10.0), headers={"User-Agent": user_agent()}) as client:
        for adresse in _MIRRORS:
            try:
                antwort = await client.post(adresse, content=abfrage, headers={"Content-Type": "text/plain; charset=utf-8"})
                antwort.raise_for_status()
                daten = antwort.json()
            except Exception as exc:
                fehler = f"{type(exc).__name__}: {str(exc)[:160]}"
                continue
            if isinstance(daten, dict) and daten.get("remark") and not daten.get("elements"):
                fehler = str(daten.get("remark"))[:200]
                continue
            gebaeude = baujahre_aus(daten)
            await store(schluessel, gebaeude)
            return {"gebaeude": gebaeude, "rahmen": rahmen}
    return {"gebaeude": [], "fehler": fehler, "rahmen": rahmen}
