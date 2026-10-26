from __future__ import annotations

import asyncio
import base64
import io
import re
import threading
import time

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_json, read_json

DATEI = DATA_DIR / "modelltests.json"

HERSTELLER = {
    "meta": "Meta",
    "google": "Google",
    "nvidia": "NVIDIA",
    "nv-mistralai": "NVIDIA und Mistral AI",
    "mistralai": "Mistral AI",
    "microsoft": "Microsoft",
    "ibm": "IBM",
    "deepseek-ai": "DeepSeek",
    "moonshotai": "Moonshot AI",
    "z-ai": "Zhipu AI",
    "openai": "OpenAI",
    "minimaxai": "MiniMax",
    "writer": "Writer",
    "01-ai": "01.AI",
    "adept": "Adept",
    "ai21labs": "AI21 Labs",
    "aisingapore": "AI Singapore",
    "bigcode": "BigCode",
    "databricks": "Databricks",
    "snowflake": "Snowflake",
    "stepfun-ai": "StepFun",
    "poolside": "Poolside",
    "zyphra": "Zyphra",
    "qwen": "Alibaba Qwen",
    "anthropic": "Anthropic",
    "x-ai": "xAI",
}

FAEHIGKEIT_NAMEN = {
    "text": "Text zu Text",
    "code": "Code",
    "bild_zu_text": "Bild zu Text",
    "video_zu_text": "Video zu Text",
    "audio_zu_text": "Audio zu Text",
    "text_zu_bild": "Text zu Bild",
    "einbettung": "Einbettung (Suche)",
    "sicherheit": "Sicherheitsprüfung",
    "uebersetzung": "Übersetzung",
    "denken": "Denkt vor der Antwort",
    "werkzeuge": "Werkzeuge",
    "spezial": "Spezialmodell, kein Chat",
}

EINBETTUNG = re.compile(r"(embed|nvclip|retriever|rerank|arctic-embed|bge|nomic)", re.I)
SICHERHEIT = re.compile(r"(guard|safety|content-safety|reward|topic-control)", re.I)
SEHEN = re.compile(r"(vl\b|-vl|vlm|vision|llava|neva|vila|kosmos|fuyu|deplot|gemma-?[34]|diffusiongemma|glimmer|omni|pixtral|moondream|qwen\d?(\.\d)?-?vl|internvl|minicpm-?v|parse|cosmos)", re.I)
VIDEO = re.compile(r"(diffusiongemma|omni|cosmos|video|glimmer)", re.I)
AUDIO = re.compile(r"(omni|whisper|audio)", re.I)
CODE = re.compile(r"(code|coder|codestral|starcoder|devstral|laguna)", re.I)
BILD = re.compile(r"(flux|sdxl|stable[-_ ]?diffusion|dall|imagen|z[-_ ]?image|hidream|kolors|qwen[-_]?image)", re.I)
DENKEN = re.compile(r"(reason|thinking|r1\b|qwq|gpt-oss|nemotron-3|glm-5|kimi-k|deepseek-v4|step-5|minimax-m3)", re.I)
UEBERSETZUNG = re.compile(r"(translate|riva-translate)", re.I)

GESPERRT = re.compile(r"HTTP 40[34]|HTTP 410")


def _zahl(text: str) -> float:
    return float(text)


def parameter(modell: str) -> dict:
    name = modell.split("/")[-1].lower()
    gesamt = aktiv = 0.0
    treffer = re.search(r"(\d+)x(\d+(?:\.\d+)?)b", name)
    if treffer:
        gesamt = _zahl(treffer.group(1)) * _zahl(treffer.group(2))
    treffer = re.search(r"(\d+(?:\.\d+)?)b-a(\d+(?:\.\d+)?)(b|m)\b", name)
    if treffer:
        gesamt = _zahl(treffer.group(1))
        aktiv = _zahl(treffer.group(2)) / (1000 if treffer.group(3) == "m" else 1)
    if not gesamt:
        treffer = re.search(r"(?<![a-z])e(\d+(?:\.\d+)?)b\b", name)
        if treffer:
            aktiv = _zahl(treffer.group(1))
        treffer = re.search(r"(?<![\dx.])(\d+(?:\.\d+)?)b\b", name)
        if treffer:
            gesamt = _zahl(treffer.group(1))
    if gesamt and not aktiv:
        aktiv = gesamt
    return {"gesamt_mrd": round(gesamt, 2) if gesamt else None, "aktiv_mrd": round(aktiv, 2) if aktiv else None, "moe": bool(gesamt and aktiv and aktiv < gesamt)}


def hersteller(anbieter: str, modell: str) -> str:
    if "/" in modell:
        vorne = modell.split("/")[0].lower()
        return HERSTELLER.get(vorne, vorne)
    return HERSTELLER.get(anbieter, anbieter)


def faehigkeiten(modell: str, messung: dict | None = None, ollama: list[str] | None = None) -> list[str]:
    messung = messung or {}
    if EINBETTUNG.search(modell):
        return ["einbettung"] + (["bild_zu_text"] if SEHEN.search(modell) else [])
    if SICHERHEIT.search(modell):
        return ["sicherheit"]
    if BILD.search(modell):
        return ["text_zu_bild"]
    liste = ["text"]
    code = messung.get("code") or {}
    if CODE.search(modell):
        liste.append("code")
    elif code:
        if not code.get("fehler") and re.search(r"def |```|return ", str(code.get("text") or "")):
            liste.append("code")
    elif not UEBERSETZUNG.search(modell):
        liste.append("code")
    bild = messung.get("bild") or {}
    video = messung.get("video") or {}
    if ollama:
        if "vision" in ollama:
            liste.append("bild_zu_text")
        if "thinking" in ollama:
            liste.append("denken")
        if "tools" in ollama:
            liste.append("werkzeuge")
    elif bild:
        if bild.get("richtig"):
            liste.append("bild_zu_text")
    elif SEHEN.search(modell):
        liste.append("bild_zu_text")
    if video.get("richtig") or (not video and "bild_zu_text" in liste and VIDEO.search(modell)):
        liste.append("video_zu_text")
    if AUDIO.search(modell) and "bild_zu_text" in liste:
        liste.append("audio_zu_text")
    if UEBERSETZUNG.search(modell):
        liste.append("uebersetzung")
    if "denken" not in liste and (DENKEN.search(modell) or (messung.get("hallo") or {}).get("denkt")):
        liste.append("denken")
    return liste


def _zustand(messung: dict | None) -> str:
    if not messung:
        return "ungetestet"
    if messung.get("art") == "kein_chat":
        return "kein_chat"
    hallo = messung.get("hallo") or {}
    fehler = str(hallo.get("fehler") or "")
    if GESPERRT.search(fehler):
        return "gesperrt"
    if fehler:
        return "haengt" if "Timeout" in fehler else "fehler"
    return "bereit"


def _sekunden(eintrag: dict | None) -> float | None:
    if not eintrag or eintrag.get("fehler"):
        return None
    wert = eintrag.get("s")
    return float(wert) if isinstance(wert, (int, float)) else None


def zusammenfassen(anbieter: str, modell: str, messung: dict | None = None, ollama: dict | None = None) -> dict:
    ollama = ollama or {}
    werte = parameter(modell)
    if ollama.get("parameter_size") and not werte["gesamt_mrd"]:
        treffer = re.search(r"(\d+(?:\.\d+)?)\s*([BM])", str(ollama["parameter_size"]), re.I)
        if treffer:
            zahl = float(treffer.group(1)) / (1000 if treffer.group(2).upper() == "M" else 1)
            werte = {"gesamt_mrd": zahl, "aktiv_mrd": zahl, "moe": False}
    faehig = faehigkeiten(modell, messung, ollama.get("capabilities"))
    if _zustand(messung) == "kein_chat" and "einbettung" not in faehig and "sicherheit" not in faehig:
        faehig = [f for f in faehig if f not in ("text", "code")] or ["spezial"]
    hallo = (messung or {}).get("hallo") or {}
    code = (messung or {}).get("code") or {}
    bild = (messung or {}).get("bild") or {}
    video = (messung or {}).get("video") or {}
    return {
        "id": modell,
        "anbieter": anbieter,
        "hersteller": hersteller(anbieter, modell),
        "parameter": werte,
        "faehigkeiten": faehig,
        "faehigkeit_namen": [FAEHIGKEIT_NAMEN[f] for f in faehig],
        "zustand": _zustand(messung),
        "kurz_s": _sekunden(hallo),
        "erstes_wort_s": hallo.get("erstes") if not hallo.get("fehler") else None,
        "lang_s": _sekunden(code),
        "bild_s": _sekunden(bild) if bild.get("richtig") else None,
        "video_s": _sekunden(video) if video.get("richtig") else None,
        "fehler": str(hallo.get("fehler") or ""),
        "getestet": (messung or {}).get("zeit"),
        "familie": ollama.get("family", ""),
        "quantisierung": ollama.get("quantization_level", ""),
        "lokal": anbieter in ("ollama", "lmstudio", "lokalserver"),
    }


class ModellInfo:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._lauf: dict = {"laeuft": False, "fertig": 0, "gesamt": 0, "aktuell": "", "anbieter": ""}
        self._aufgabe: asyncio.Task | None = None

    def messungen(self, anbieter: str) -> dict[str, dict]:
        from app.services.modell_messungen import MESSUNGEN

        ergebnis = dict(MESSUNGEN.get(anbieter, {})) if anbieter == "nvidia" else {}
        eigene = read_json(DATEI, {}) or {}
        for modell, eintrag in (eigene.get(anbieter) or {}).items():
            if isinstance(eintrag, dict):
                ergebnis[modell] = eintrag
        return ergebnis

    def merken(self, anbieter: str, modell: str, eintrag: dict) -> None:
        with self._lock:
            daten = read_json(DATEI, {}) or {}
            daten.setdefault(anbieter, {})[modell] = eintrag
            atomic_write_json(DATEI, daten)

    async def _ollama_details(self) -> dict[str, dict]:
        from app.services.ollama_service import get_ollama_service

        dienst = get_ollama_service()
        if not dienst.enabled():
            return {}
        try:
            import httpx

            async with httpx.AsyncClient(timeout=4) as client:
                antwort = await client.get(dienst.base_url() + "/api/tags")
                antwort.raise_for_status()
                eintraege = antwort.json().get("models", [])
                details: dict[str, dict] = {}
                for eintrag in eintraege:
                    name = str(eintrag.get("name") or eintrag.get("model") or "")
                    if name:
                        details[name] = dict(eintrag.get("details") or {})

                async def zeigen(name: str) -> None:
                    try:
                        roh = await client.post(dienst.base_url() + "/api/show", json={"model": name})
                        if roh.status_code < 400:
                            details[name]["capabilities"] = list(roh.json().get("capabilities") or [])
                    except Exception as fehler:
                        leise(fehler, "modell_info")

                await asyncio.gather(*(zeigen(n) for n in list(details)[:40]))
                return details
        except Exception as fehler:
            leise(fehler, "modell_info")
            return {}

    async def liste(self, anbieter: str, modelle: list[str]) -> dict:
        messungen = self.messungen(anbieter)
        details = await self._ollama_details() if anbieter == "ollama" else {}
        return {
            "anbieter": anbieter,
            "modelle": {m: zusammenfassen(anbieter, m, messungen.get(m), details.get(m)) for m in modelle},
            "lauf": dict(self._lauf),
        }

    def lauf(self) -> dict:
        return dict(self._lauf)

    def starten(self, anbieter: str, modelle: list[str]) -> dict:
        if self._aufgabe and not self._aufgabe.done():
            return self.lauf()
        self._lauf = {"laeuft": True, "fertig": 0, "gesamt": len(modelle), "aktuell": "", "anbieter": anbieter}
        self._aufgabe = asyncio.create_task(self._alle(anbieter, modelle))
        return self.lauf()

    async def _alle(self, anbieter: str, modelle: list[str]) -> None:
        try:
            for modell in modelle:
                self._lauf["aktuell"] = modell
                try:
                    eintrag = await messen(anbieter, modell)
                    self.merken(anbieter, modell, eintrag)
                except Exception as fehler:
                    leise(fehler, "modell_info")
                self._lauf["fertig"] += 1
                await asyncio.sleep(1.0)
        finally:
            self._lauf["laeuft"] = False
            self._lauf["aktuell"] = ""


def testbild(farbe: str, form: str, zahl: str) -> str:
    from PIL import Image, ImageDraw, ImageFont

    bild = Image.new("RGB", (512, 384), "white")
    zeichner = ImageDraw.Draw(bild)
    if form == "kreis":
        zeichner.ellipse((60, 80, 260, 280), fill=farbe)
    else:
        zeichner.rectangle((60, 80, 260, 280), fill=farbe)
    try:
        schrift = ImageFont.truetype("arial.ttf", 90)
    except OSError:
        try:
            schrift = ImageFont.load_default(90)
        except TypeError:
            schrift = ImageFont.load_default()
    zeichner.text((300, 130), zahl, fill="black", font=schrift)
    puffer = io.BytesIO()
    bild.save(puffer, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(puffer.getvalue()).decode("ascii")


async def _strom(anbieter: str, modell: str, inhalt, max_tokens: int, erstes_max: float, gesamt_max: float) -> dict:
    from app.providers.openai_compatible import OpenAICompatibleProvider
    from app.providers.registry import get_registry

    dienst = get_registry().all().get(anbieter)
    if not isinstance(dienst, OpenAICompatibleProvider) or not dienst.available():
        return {"fehler": "nicht eingerichtet", "s": 0.0}
    client = dienst._client()
    beginn = time.perf_counter()
    erstes = None
    teile: list[str] = []
    denkt = False
    try:
        strom = await asyncio.wait_for(
            client.with_options(timeout=gesamt_max, max_retries=0).chat.completions.create(
                model=modell,
                messages=[{"role": "user", "content": inhalt}],
                max_tokens=max_tokens,
                temperature=0.2,
                stream=True,
            ),
            erstes_max,
        )

        async def lesen() -> None:
            nonlocal erstes, denkt
            async for stueck in strom:
                for wahl in getattr(stueck, "choices", None) or []:
                    delta = wahl.delta
                    extra = getattr(delta, "model_extra", None) or {}
                    if getattr(delta, "reasoning_content", None) or extra.get("reasoning_content") or extra.get("reasoning"):
                        denkt = True
                        if erstes is None:
                            erstes = time.perf_counter() - beginn
                    if delta.content:
                        if erstes is None:
                            erstes = time.perf_counter() - beginn
                        teile.append(delta.content)

        await asyncio.wait_for(lesen(), max(gesamt_max - (time.perf_counter() - beginn), 1.0))
    except asyncio.TimeoutError:
        return {"fehler": "ReadTimeout", "s": round(time.perf_counter() - beginn, 2), "erstes": round(erstes, 2) if erstes else None}
    except Exception as fehler:
        status = getattr(fehler, "status_code", None)
        return {"fehler": f"HTTP {status}" if status else type(fehler).__name__, "s": round(time.perf_counter() - beginn, 2)}
    text = "".join(teile).strip()
    return {"erstes": round(erstes, 2) if erstes is not None else None, "s": round(time.perf_counter() - beginn, 2), "zeichen": len(text), "denkt": denkt, "text": text[:160]}


async def messen(anbieter: str, modell: str) -> dict:
    eintrag: dict = {"modell": modell, "zeit": int(time.time())}
    if EINBETTUNG.search(modell) or re.search(r"(reward|deplot|kosmos|parse|detector|calibration)", modell, re.I):
        eintrag["art"] = "kein_chat"
        return eintrag
    eintrag["hallo"] = await _strom(anbieter, modell, "Hallo!", 400, 40, 60)
    if eintrag["hallo"].get("fehler"):
        return eintrag
    eintrag["code"] = await _strom(anbieter, modell, "Code mir eine Python-Funktion, die prueft, ob eine Zahl eine Primzahl ist. Nur Code mit kurzer Erklaerung.", 900, 40, 90)
    bild = await _strom(
        anbieter,
        modell,
        [
            {"type": "text", "text": "Welche Farbe und Form hat das Objekt links, und welche Zahl steht rechts? Antworte kurz auf Deutsch."},
            {"type": "image_url", "image_url": {"url": testbild("red", "kreis", "47")}},
        ],
        400,
        40,
        60,
    )
    antwort = str(bild.get("text") or "").lower()
    bild["richtig"] = "47" in antwort and ("rot" in antwort or "red" in antwort)
    eintrag["bild"] = bild
    if bild["richtig"]:
        video = await _strom(
            anbieter,
            modell,
            [
                {"type": "text", "text": "Das sind drei Standbilder aus einem Video in zeitlicher Reihenfolge. Nenne kurz auf Deutsch fuer jedes Bild Farbe, Form und Zahl."},
                {"type": "image_url", "image_url": {"url": testbild("red", "kreis", "1")}},
                {"type": "image_url", "image_url": {"url": testbild("blue", "quadrat", "2")}},
                {"type": "image_url", "image_url": {"url": testbild("green", "kreis", "3")}},
            ],
            500,
            40,
            60,
        )
        antwort = str(video.get("text") or "").lower()
        video["richtig"] = ("blau" in antwort or "blue" in antwort) and "gr" in antwort and ("quadrat" in antwort or "square" in antwort)
        eintrag["video"] = video
    return eintrag


_dienst: ModellInfo | None = None


def get_modell_info() -> ModellInfo:
    global _dienst
    if _dienst is None:
        _dienst = ModellInfo()
    return _dienst
