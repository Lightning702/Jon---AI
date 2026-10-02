from __future__ import annotations

import re
import time
from typing import Any

from app.services.connectors.basis import Connector, Werkzeug

STIMMEN = {"a": "de-DE-ConradNeural", "b": "de-DE-KatjaNeural"}
TEILE_MAX = 80
TEXT_MAX = 1100


def _dateiname(titel: str) -> str:
    sauber = re.sub(r"[^\wÄÖÜäöüß\- ]", "", titel).strip().replace(" ", "-")
    return (sauber or "Podcast")[:60]


def teile_lesen(args: dict[str, Any]) -> list[tuple[str, str]]:
    teile: list[tuple[str, str]] = []
    roh = args.get("teile")
    if isinstance(roh, list):
        for eintrag in roh:
            if not isinstance(eintrag, dict):
                continue
            text = " ".join(str(eintrag.get("text", "")).split())
            if not text:
                continue
            sprecher = "b" if str(eintrag.get("sprecher", "a")).strip().lower() in ("b", "gast", "2", "zwei") else "a"
            teile.append((sprecher, text))
    if not teile and args.get("skript"):
        for zeile in str(args.get("skript")).splitlines():
            treffer = re.match(r"^\s*(A|B|Jon|Gast|Sprecher\s*[12])\s*:\s*(.+)$", zeile, re.I)
            if treffer:
                wer = treffer.group(1).lower()
                teile.append(("b" if wer in ("b", "gast") or wer.endswith("2") else "a", treffer.group(2).strip()))
            elif zeile.strip() and teile:
                sprecher, text = teile[-1]
                teile[-1] = (sprecher, f"{text} {zeile.strip()}")
            elif zeile.strip():
                teile.append(("a", zeile.strip()))
    zerlegt: list[tuple[str, str]] = []
    for sprecher, text in teile:
        while len(text) > TEXT_MAX:
            schnitt = text.rfind(". ", 0, TEXT_MAX)
            schnitt = schnitt + 1 if schnitt > 200 else TEXT_MAX
            zerlegt.append((sprecher, text[:schnitt].strip()))
            text = text[schnitt:].strip()
        if text:
            zerlegt.append((sprecher, text))
    return zerlegt[:TEILE_MAX]


class StudioConnector(Connector):
    id = "studio"
    name = "Studio"
    woerter = ("podcast", "hörspiel", "hoerspiel", "hörbuch", "hoerbuch", "als audio", "audiodatei", "mp3 erstellen", "vertonen", "vertone")

    def werkzeuge(self) -> list[Werkzeug]:
        return [
            Werkzeug(
                name="podcast_erstellen",
                beschreibung=(
                    "Erstellt einen Podcast oder ein Hörstück als MP3 mit zwei Stimmen (a = Jon, männlich; "
                    "b = Gast, weiblich). Schreib zuerst ein lebendiges Skript und übergib es als teile "
                    "(Liste aus sprecher und text) oder als skript mit Zeilen wie 'A: ...' und 'B: ...'."
                ),
                eigenschaften={
                    "titel": {"type": "string"},
                    "teile": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"sprecher": {"type": "string", "enum": ["a", "b"]}, "text": {"type": "string"}}},
                    },
                    "skript": {"type": "string", "description": "Alternativ: Zeilen 'A: ...' und 'B: ...'."},
                },
                pflicht=["titel"],
                stufe="standard",
                kurz="Nimmt einen Podcast auf.",
            )
        ]

    async def ausfuehren(self, name: str, args: dict[str, Any]) -> dict:
        if name != "podcast_erstellen":
            return {"error": f"Das Studio kennt {name} nicht."}
        from app.services.dateiindex_service import get_dateiindex_service
        from app.services.dateiraum_service import get_dateiraum_service
        from app.services.voice_service import synthesize_speech

        teile = teile_lesen(args)
        if not teile:
            return {"error": "Für den Podcast fehlt das Skript."}
        titel = " ".join(str(args.get("titel") or "Podcast").split())[:80]
        audio = bytearray()
        try:
            for sprecher, text in teile:
                audio.extend(await synthesize_speech(text, voice=STIMMEN[sprecher], volume="+0%", rate="+2%"))
        except Exception as exc:
            return {"error": f"Die Sprachausgabe ist gerade nicht erreichbar: {exc}"}
        if not audio:
            return {"error": "Die Sprachausgabe hat nichts geliefert."}
        ziel = get_dateiraum_service().ordner("Audio") / f"{_dateiname(titel)}-{time.strftime('%Y%m%d-%H%M%S')}.mp3"
        ziel.write_bytes(bytes(audio))
        karte = get_dateiindex_service().karte_und_merken(ziel, titel=titel, beschreibung="Podcast von Jon", quelle="studio")
        return {"ok": True, "datei": karte, "teile": len(teile), "sekunden_ca": round(len(audio) / 6000)}
