from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

URSPRUENGE = [u.strip() for u in os.environ.get("JON_DEMO_ORIGINS", "https://getjon.info,https://www.getjon.info,https://getjon.netlify.app").split(",") if u.strip()]
PRO_IP = int(os.environ.get("JON_DEMO_PRO_IP", "20"))
PRO_TAG = int(os.environ.get("JON_DEMO_PRO_TAG", "600"))
MAX_AUDIO = 4 * 1024 * 1024
PERSONAS = {
    "jon": "Du bist Jon, der KI-Assistent von FelWorks aus Österreich, hier in der öffentlichen Website-Demo. Antworte freundlich, klar und auf Deutsch, wenn der Nutzer nichts anderes schreibt. "
    "In der Demo hast du keinen Zugriff auf einen Computer, keine Dateien, kein Gedächtnis und keine Werkzeuge. Behaupte nie, etwas auf einem Gerät getan zu haben. "
    "Wenn jemand fragt, was du sonst kannst: In der Vollversion steuert Jon den PC, arbeitet mit Projekten, hat ein Fachteam, Funke am Handy und mehr; Download auf getjon.info. "
    "Gib keine Anleitungen für Schaden, Hass oder Illegales. Halte Antworten eher kurz.",
    "minijon": "Du bist MiniJon, Jons kleiner, verspielter Begleiter, hier in der öffentlichen Website-Demo. Antworte kurz, warm und mit trockenem Humor, gern mit einem passenden Emoji, auf Deutsch, wenn der Nutzer nichts anderes schreibt. "
    "Du hast in der Demo keinen Zugriff auf Geräte, Dateien oder ein Gedächtnis und tust auch nicht so. Gib keine Anleitungen für Schaden, Hass oder Illegales.",
}


class Begrenzer:
    def __init__(self, pro_ip: int = PRO_IP, pro_tag: int = PRO_TAG, fenster: float = 600, uhr=time.time) -> None:
        self.pro_ip, self.pro_tag, self.fenster, self.uhr = pro_ip, pro_tag, fenster, uhr
        self.ips: dict[str, deque] = {}
        self.tag: deque = deque()

    def pruefen(self, ip: str) -> None:
        jetzt = self.uhr()
        while self.tag and jetzt - self.tag[0] > 86400:
            self.tag.popleft()
        if len(self.tag) >= self.pro_tag:
            raise HTTPException(429, "Die Demo ist für heute ausgelastet. Lade dir Jon kostenlos herunter und probier ihn ohne Grenzen aus.")
        verlauf = self.ips.setdefault(ip, deque())
        while verlauf and jetzt - verlauf[0] > self.fenster:
            verlauf.popleft()
        if len(verlauf) >= self.pro_ip:
            raise HTTPException(429, "Kurze Pause bitte: In der Demo gibt es ein paar Nachrichten pro zehn Minuten.")
        verlauf.append(jetzt)
        self.tag.append(jetzt)
        if len(self.ips) > 5000:
            self.ips = {k: v for k, v in self.ips.items() if v and jetzt - v[-1] < self.fenster}


class Nachricht(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=1500)


class Chat(BaseModel):
    persona: str = Field(default="jon", pattern="^(jon|minijon)$")
    nachrichten: list[Nachricht] = Field(min_length=1, max_length=12)


class Route(BaseModel):
    von: str = Field(min_length=2, max_length=200)
    nach: str = Field(min_length=2, max_length=200)
    modus: str = Field(default="auto", pattern="^(auto|fahrrad|fuss|oepnv)$")


def adresse(request: Request) -> str:
    weitergeleitet = request.headers.get("x-forwarded-for", "")
    return (weitergeleitet.split(",")[0].strip() or (request.client.host if request.client else "")) or "unbekannt"


def auswahl() -> tuple[str, str]:
    from app.core.config import get_settings, lebendes_modell
    from app.services.settings_service import get_settings_service

    provider = os.environ.get("JON_DEMO_PROVIDER", "")
    model = os.environ.get("JON_DEMO_MODEL", "")
    if not provider:
        provider, eingestellt = get_settings_service().selection()
        provider = provider or get_settings().default_provider
        model = model or eingestellt or get_settings().jon_model
    return provider, lebendes_modell(model or get_settings().jon_model, provider)


async def antworten(persona: str, nachrichten: list[Nachricht]):
    from app.providers.base import ChatMessage, ChatRequest
    from app.providers.registry import get_registry

    provider, model = auswahl()
    anfrage = ChatRequest(messages=[ChatMessage(role="system", content=PERSONAS[persona])] + [ChatMessage(role=n.role, content=n.content) for n in nachrichten], model=model, temperature=0.6, top_p=1.0, max_tokens=900, tools=[], slot="jon", first_token_timeout=60)
    async for teil in get_registry().get(provider).stream(anfrage, None):
        if teil.kind == "content" and teil.delta:
            yield teil.delta


def erstellen(begrenzer: Begrenzer | None = None) -> FastAPI:
    app = FastAPI(title="Jon Demo", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=URSPRUENGE, allow_methods=["GET", "POST"], allow_headers=["Content-Type"], max_age=600)
    grenze = begrenzer or Begrenzer()

    @app.get("/demo/status")
    async def status() -> dict:
        return {"ok": True, "funktionen": ["jon", "minijon", "maps", "transkript"], "grenze_pro_10_min": grenze.pro_ip}

    @app.post("/demo/chat")
    async def chat(daten: Chat, request: Request):
        grenze.pruefen(adresse(request))
        if daten.nachrichten[-1].role != "user":
            raise HTTPException(400, "Die letzte Nachricht muss vom Nutzer sein.")

        async def strom():
            try:
                async for stueck in antworten(daten.persona, daten.nachrichten):
                    yield "data: " + json.dumps({"delta": stueck}, ensure_ascii=False) + "\n\n"
                yield 'data: {"fertig": true}\n\n'
            except Exception:
                yield "data: " + json.dumps({"fehler": "Jon ist gerade nicht erreichbar. Versuch es gleich noch einmal."}, ensure_ascii=False) + "\n\n"

        return StreamingResponse(strom(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.get("/demo/orte")
    async def orte(q: str, request: Request) -> dict:
        from app.services.maps.service import get_maps_service

        if not 2 <= len(q.strip()) <= 200:
            raise HTTPException(400, "Bitte einen Ort eingeben.")
        grenze.pruefen(adresse(request))
        try:
            treffer = await get_maps_service().search(q.strip(), None, 6)
        except Exception:
            raise HTTPException(502, "Die Kartensuche ist gerade nicht erreichbar.")
        return {"treffer": [t.to_dict() for t in treffer]}

    @app.post("/demo/route")
    async def route(daten: Route, request: Request) -> dict:
        from app.services.maps.service import get_maps_service

        grenze.pruefen(adresse(request))
        dienst = get_maps_service()
        try:
            von, nach = await asyncio.gather(dienst.search(daten.von, None, 1), dienst.search(daten.nach, None, 1))
            if not von or not nach:
                raise HTTPException(404, "Mindestens einen der Orte habe ich nicht gefunden.")
            routen = await dienst.route([(von[0].lat, von[0].lon), (nach[0].lat, nach[0].lon)], daten.modus, False)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(502, "Die Route ist gerade nicht berechenbar.")
        if not routen:
            raise HTTPException(404, "Keine Route gefunden.")
        ort = lambda p: {"name": p.name, "label": p.label, "lat": p.lat, "lon": p.lon}
        weg = routen[0].to_dict()
        return {"von": ort(von[0]), "nach": ort(nach[0]), "route": {k: weg.get(k) for k in ("mode", "distance_m", "duration_s", "summary")}}

    @app.post("/demo/transkript")
    async def transkript(request: Request) -> dict:
        grenze.pruefen(adresse(request))
        daten = await request.body()
        if not daten or len(daten) > MAX_AUDIO or daten[:4] != b"RIFF":
            raise HTTPException(400, "Bitte eine kurze WAV-Aufnahme bis 4 MB schicken.")
        try:
            from app.services.voice_service import VoiceService

            text = await asyncio.to_thread(VoiceService().transcribe_wav, daten)
        except Exception:
            raise HTTPException(503, "Die Spracherkennung ist auf diesem Jon gerade nicht verfügbar.")
        return {"text": text}

    return app


app = erstellen()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=os.environ.get("JON_DEMO_HOST", "127.0.0.1"), port=int(os.environ.get("JON_DEMO_PORT", "8790")), log_level="warning", proxy_headers=False)


if __name__ == "__main__":
    main()
