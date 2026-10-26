from __future__ import annotations

import asyncio
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


UNBRAUCHBAR = re.compile(r"glitch|\bcorrupt(?:ed)?\b|datamosh|databend|data loss of image|compression artifact|broken image|kaputt", re.I)

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


NEBENSACHE = re.compile(r"\b(system|analy[sz]\w*|measur\w*|messung\w*|device|apparat\w*|sensor\w*|logger|tripod|stativ|chamber|experiment\w*|setup|equipment|instrument\w*|sign|schild|plaque|label\w*|screenshot|poster|stamp|briefmarke|map|karte|logo|museum|exhibit\w*)\b", re.I)


def nebensache(titel: str, suche: str) -> bool:
    gesucht = {w.lower() for w in re.findall(r"\w+", suche or "")}
    return any(t.group(0).lower() not in gesucht for t in NEBENSACHE.finditer(str(titel or "")))


def passt(titel: str, suche: str) -> bool:
    if UNBRAUCHBAR.search(str(titel or "")):
        return False
    woerter = [w.lower() for w in re.split(r"[\W_]+", suche) if len(w) >= 3 and w.lower() not in FUELLWOERTER]
    if not woerter:
        return True
    text = re.sub(r"[\W_]+", " ", titel.lower())
    treffer = sum(1 for w in woerter if w[:5] in text)
    return treffer >= min(3, len(woerter))


PRUEF_MAX = 3
PRUEF_ZEIT = 8.0
PRUEF_BUDGET = 4
PRUEF_FRAGE = (
    "Passt dieses Foto als Bild auf eine Praesentationsfolie zum Thema \"{suche}\"? Es muss das Thema klar und "
    "erkennbar zeigen, ohne stoerende Dinge im Vordergrund (Stative, Stuehle, Werkzeug, Schilder), keine Collage, "
    "kein Screenshot, keine Textseite. Antworte nur mit JA oder NEIN."
)


def _klein(pfad: str) -> bytes:
    from PIL import Image

    with Image.open(pfad) as bild:
        bild = bild.convert("RGB")
        bild.thumbnail((512, 512))
        puffer = io.BytesIO()
        bild.save(puffer, "JPEG", quality=80)
        return puffer.getvalue()


async def bild_passt(pfad: str, suche: str) -> bool | None:
    from app.services import sehen

    try:
        daten = await asyncio.to_thread(_klein, pfad)
    except Exception as fehler:
        leise(fehler, "services/bildquelle")
        return None
    try:
        ergebnis = await asyncio.wait_for(sehen.beschreiben([daten], PRUEF_FRAGE.format(suche=suche), "pruefen", max_tokens=300, wartezeit=PRUEF_ZEIT), PRUEF_ZEIT + 2)
    except asyncio.TimeoutError:
        return None
    text = str(ergebnis.get("text") or "").upper()
    if re.search(r"\b(NEIN|NO)\b", text):
        return False
    if re.search(r"\b(JA|YES)\b", text):
        return True
    return None


async def _geladen(adresse: str) -> str:
    try:
        return await herunterladen(adresse)
    except Exception as fehler:
        leise(fehler, "services/bildquelle")
        return ""


async def bestes(adressen: list[str], suche: str, budget: list[int] | None = None) -> str:
    budget = budget if budget is not None else [PRUEF_BUDGET]
    pfade = [p for p in await asyncio.gather(*(_geladen(a) for a in adressen)) if p]
    for pfad in pfade:
        if budget[0] <= 0:
            return pfad
        budget[0] -= 1
        if await bild_passt(pfad, suche) is not False:
            return pfad
    return ""


async def suchen(suche: str) -> str:
    begriff = str(suche or "").strip()[:200]
    from app.services.offline import aktiv

    if not begriff or aktiv():
        return ""
    budget = [PRUEF_BUDGET]
    for variante in varianten(begriff):
        kandidaten: list[tuple[bool, str]] = []
        for quelle in (_commons, _openverse):
            if sum(1 for neben, _ in kandidaten if not neben) >= PRUEF_MAX:
                break
            try:
                ergebnisse = await quelle(variante)
            except Exception as fehler:
                leise(fehler, "services/bildquelle")
                continue
            for adresse, titel in ergebnisse:
                if all(adresse != a for _, a in kandidaten) and passt(titel, variante):
                    kandidaten.append((nebensache(titel, begriff), adresse))
        if not kandidaten:
            continue
        geordnet = [a for _, a in sorted(kandidaten, key=lambda k: k[0])]
        pfad = await bestes(geordnet[:PRUEF_MAX], begriff, budget)
        if pfad:
            return pfad
    return ""


def _schlicht(text: object) -> str:
    return re.sub(r"<[^>]+>", "", str(text or "")).strip()[:120]


async def _commons_mit_herkunft(suche: str) -> list[dict]:
    parameter = {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": "6",
        "gsrsearch": suche, "gsrlimit": "15", "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "1600",
        "iiextmetadatafilter": "Artist|LicenseShortName|ImageDescription",
    }
    async with httpx.AsyncClient(timeout=20, headers=KOPF) as client:
        antwort = await client.get("https://commons.wikimedia.org/w/api.php", params=parameter)
        antwort.raise_for_status()
        seiten = list((antwort.json().get("query") or {}).get("pages", {}).values())
    seiten.sort(key=lambda s: s.get("index", 99))
    treffer = []
    for seite in seiten:
        info = (seite.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if int(info.get("width", 0)) < 500:
            continue
        adresse = info.get("thumburl") or info.get("url")
        if not adresse:
            continue
        meta = info.get("extmetadata") or {}
        titel = str(seite.get("title", "")).removeprefix("File:")
        treffer.append({
            "adresse": adresse,
            "titel": titel,
            "quelle": "Wikimedia Commons",
            "seite": "https://commons.wikimedia.org/wiki/File:" + titel.replace(" ", "_"),
            "lizenz": _schlicht((meta.get("LicenseShortName") or {}).get("value")),
            "autor": _schlicht((meta.get("Artist") or {}).get("value")),
            "beschreibung": _schlicht((meta.get("ImageDescription") or {}).get("value")),
        })
    return treffer


async def _openverse_mit_herkunft(suche: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=20, headers=KOPF) as client:
        antwort = await client.get("https://api.openverse.org/v1/images/", params={"q": suche, "page_size": "12", "size": "large"})
        antwort.raise_for_status()
        return [
            {
                "adresse": e.get("url"),
                "titel": str(e.get("title", "")),
                "quelle": "Openverse",
                "seite": str(e.get("foreign_landing_url") or ""),
                "lizenz": (str(e.get("license", "")).upper() + " " + str(e.get("license_version", ""))).strip(),
                "autor": str(e.get("creator") or ""),
                "beschreibung": "",
            }
            for e in antwort.json().get("results", [])
            if e.get("url")
        ]


async def finden(suche: str, anzahl: int = 1) -> list[dict]:
    begriff = str(suche or "").strip()[:200]
    from app.services.offline import aktiv

    if not begriff or aktiv():
        return []
    ziel = max(1, min(4, int(anzahl or 1)))
    budget = [PRUEF_BUDGET + ziel]
    gefunden: list[dict] = []
    gesehen: set[str] = set()
    for variante in varianten(begriff):
        sammlung: list[dict] = []
        for quelle in (_commons_mit_herkunft, _openverse_mit_herkunft):
            if len(sammlung) >= ziel + 2:
                break
            try:
                ergebnisse = await quelle(variante)
            except Exception as fehler:
                leise(fehler, "services/bildquelle")
                continue
            for eintrag in ergebnisse:
                if len(sammlung) >= ziel + 2:
                    break
                adresse = str(eintrag.get("adresse") or "")
                if not adresse or adresse in gesehen or not passt(eintrag.get("titel", ""), variante):
                    continue
                gesehen.add(adresse)
                pfad = await _geladen(adresse)
                if pfad:
                    sammlung.append({**{k: v for k, v in eintrag.items() if k != "adresse"}, "pfad": pfad, "url": adresse})
        if not sammlung:
            continue
        for eintrag in sammlung:
            if len(gefunden) >= ziel:
                break
            if budget[0] <= 0:
                gefunden.append(eintrag)
                continue
            budget[0] -= 1
            if await bild_passt(eintrag["pfad"], begriff) is not False:
                gefunden.append(eintrag)
        if gefunden:
            return gefunden
    return gefunden


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
