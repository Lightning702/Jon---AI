from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import httpx

from app.core.fehler import leise

KOPF = {"User-Agent": "Jon/4 (https://getjon.info; Praesentationsbilder)"}
MAX_BILD = 25_000_000
URL = re.compile(r"^https?://", re.I)


def _ablage() -> Path:
    from app.services.dateiraum_service import get_dateiraum_service

    ziel = get_dateiraum_service().ordner("Images") / "Praesentationen"
    ziel.mkdir(parents=True, exist_ok=True)
    return ziel


def _speichern(daten: bytes, schluessel: str) -> str:
    from PIL import Image

    with Image.open(io.BytesIO(daten)) as bild:
        bild.load()
        if bild.width < 40 or bild.height < 40:
            raise ValueError("Bild ist zu klein.")
        name = hashlib.sha1(schluessel.encode("utf-8")).hexdigest()[:16]
        if bild.format in ("JPEG", "PNG") and len(daten) < 6_000_000:
            ziel = _ablage() / f"{name}.{'jpg' if bild.format == 'JPEG' else 'png'}"
            ziel.write_bytes(daten)
            return str(ziel)
        bild.thumbnail((2400, 2400))
        ziel = _ablage() / f"{name}.png"
        if bild.mode in ("RGBA", "LA", "P"):
            bild.convert("RGBA").save(ziel, format="PNG", optimize=True)
        else:
            ziel = ziel.with_suffix(".jpg")
            bild.convert("RGB").save(ziel, format="JPEG", quality=88)
        return str(ziel)


WIKI_THUMB = re.compile(r"^(https://upload\.wikimedia\.org/wikipedia/[^/]+)/thumb/(.+?)/(\d+)px-[^/]+$")
WIKI_BREITEN = (960, 1280, 640, 1920, 500)


def ersatzadressen(url: str) -> list[str]:
    treffer = WIKI_THUMB.match(url)
    if not treffer:
        return [url]
    basis, datei, _ = treffer.groups()
    name = datei.rsplit("/", 1)[-1]
    endung = ".png" if name.lower().endswith(".svg") else ""
    adressen = [url] + [f"{basis}/thumb/{datei}/{breite}px-{name}{endung}" for breite in WIKI_BREITEN]
    if not endung:
        adressen.append(f"{basis}/{datei}")
    return list(dict.fromkeys(adressen))


async def herunterladen(url: str) -> str:
    from app.services.offline import MELDUNG, aktiv

    if aktiv():
        raise ValueError(MELDUNG)
    letzter: Exception | None = None
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=KOPF) as client:
        for adresse in ersatzadressen(url):
            try:
                antwort = await client.get(adresse)
                antwort.raise_for_status()
                if len(antwort.content) > MAX_BILD:
                    raise ValueError("Bild ist größer als 25 MB.")
                return _speichern(antwort.content, adresse)
            except Exception as fehler:
                letzter = fehler
    raise letzter or ValueError("Bild nicht erreichbar.")


async def _commons(suche: str) -> list[str]:
    parameter = {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": "6",
        "gsrsearch": suche, "gsrlimit": "15", "prop": "imageinfo",
        "iiprop": "url|size|mime", "iiurlwidth": "1920",
    }
    async with httpx.AsyncClient(timeout=20, headers=KOPF) as client:
        antwort = await client.get("https://commons.wikimedia.org/w/api.php", params=parameter)
        antwort.raise_for_status()
        seiten = list((antwort.json().get("query") or {}).get("pages", {}).values())
    seiten.sort(key=lambda s: s.get("index", 99))
    treffer = []
    for seite in seiten:
        info = (seite.get("imageinfo") or [{}])[0]
        art = info.get("mime")
        if art not in ("image/jpeg", "image/png", "image/svg+xml"):
            continue
        if art != "image/svg+xml" and int(info.get("width", 0)) < 600:
            continue
        adresse = info.get("thumburl") or (info.get("url") if art != "image/svg+xml" else "")
        if adresse:
            treffer.append((adresse, str(seite.get("title", "")).removeprefix("File:")))
    return treffer


async def _openverse(suche: str) -> list[str]:
    async with httpx.AsyncClient(timeout=20, headers=KOPF) as client:
        antwort = await client.get("https://api.openverse.org/v1/images/", params={"q": suche, "page_size": "12", "size": "large"})
        antwort.raise_for_status()
        return [(e.get("url"), str(e.get("title", ""))) for e in antwort.json().get("results", []) if e.get("url")]


FUELLWOERTER = {"a", "an", "the", "of", "with", "and", "on", "in", "for", "background", "photo", "image", "picture", "professional", "high", "quality", "realistic"}


def varianten(suche: str) -> list[str]:
    woerter = [w for w in re.split(r"[\s,;]+", str(suche or "")) if w]
    kern = [w for w in woerter if w.lower() not in FUELLWOERTER]
    ergebnis = [" ".join(woerter)]
    for anzahl in (5, 4, 3, 2):
        if len(kern) > anzahl:
            ergebnis.append(" ".join(kern[:anzahl]))
    if kern:
        ergebnis.append(" ".join(kern))
    return list(dict.fromkeys(v for v in ergebnis if v.strip()))


def passt(titel: str, suche: str) -> bool:
    woerter = [w.lower() for w in re.split(r"[\W_]+", suche) if len(w) >= 3 and w.lower() not in FUELLWOERTER]
    if not woerter:
        return True
    text = re.sub(r"[\W_]+", " ", titel.lower())
    treffer = sum(1 for w in woerter if w[:5] in text)
    return treffer >= min(3, len(woerter))


async def suchen(suche: str) -> str:
    begriff = str(suche or "").strip()[:200]
    from app.services.offline import aktiv

    if not begriff or aktiv():
        return ""
    for variante in varianten(begriff):
        for quelle in (_commons, _openverse):
            try:
                ergebnisse = await quelle(variante)
            except Exception as fehler:
                leise(fehler, "services/bildquelle")
                continue
            adressen = [adresse for adresse, titel in ergebnisse if passt(titel, variante)]
            for adresse in adressen[:5]:
                try:
                    return await herunterladen(adresse)
                except Exception as fehler:
                    leise(fehler, "services/bildquelle")
    return ""


def name_aus_url(url: str) -> str:
    teil = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    teil = re.sub(r"^\d+px-", "", teil)
    teil = re.sub(r"(\.(svg|png|jpe?g|gif|webp))+$", "", teil, flags=re.I)
    from urllib.parse import unquote

    return re.sub(r"[_\-]+", " ", unquote(teil)).strip()


async def besorgen(eintrag: dict, breit: bool = True) -> str:
    bild = str(eintrag.get("image") or eintrag.get("bild") or "").strip()
    if bild and URL.match(bild):
        try:
            return await herunterladen(bild)
        except Exception as fehler:
            leise(fehler, "services/bildquelle")
            ersatz = await suchen(name_aus_url(bild))
            if ersatz:
                return ersatz
            bild = ""
    if bild and Path(bild).expanduser().is_file():
        return str(Path(bild).expanduser())
    for feld in ("image_url", "bild_url"):
        adresse = str(eintrag.get(feld) or "").strip()
        if adresse and URL.match(adresse):
            try:
                return await herunterladen(adresse)
            except Exception as fehler:
                leise(fehler, "services/bildquelle")
    suche = str(eintrag.get("bild_suche") or eintrag.get("image_search") or "").strip()
    if suche:
        gefunden = await suchen(suche)
        if gefunden:
            return gefunden
    wunsch = str(eintrag.get("bild_prompt") or eintrag.get("image_prompt") or "").strip()
    if wunsch:
        from app.services.pptx_inhalte import bild_besorgen

        return await bild_besorgen(wunsch, breit)
    return ""
