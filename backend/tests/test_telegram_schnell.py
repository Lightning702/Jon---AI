from __future__ import annotations

import asyncio

from app.services import telegram_service as ts


def test_aufwaermen_ohne_bot_tut_nichts(monkeypatch):
    dienst = ts.TelegramService()
    monkeypatch.setattr(dienst, "_token", lambda: "")
    assert dienst.aufwaermen() is False
    assert asyncio.run(dienst.verbindung_aufwaermen()) is False
    assert dienst._chat_service is None


def test_aufwaermen_baut_chat_und_prompt_vorab(monkeypatch):
    aufrufe = []

    class Chat:
        def _system_prompt(self):
            aufrufe.append("prompt")
            return "Du bist Jon."

        def _denkaufwand(self, text, frei):
            aufrufe.append("denkaufwand")
            return ""

    monkeypatch.setattr("app.services.chat_service.ChatService", Chat)
    dienst = ts.TelegramService()
    monkeypatch.setattr(dienst, "_token", lambda: "1:x")
    assert dienst.aufwaermen() is True
    assert isinstance(dienst._chat_service, Chat)
    assert aufrufe == ["prompt", "denkaufwand"]


def test_verbindung_aufwaermen_schickt_ein_einziges_token(monkeypatch):
    anfragen = []

    class Anbieter:
        async def complete(self, anfrage):
            anfragen.append(anfrage)
            return "H"

    class Register:
        def get(self, name):
            assert name == "nvidia"
            return Anbieter()

    monkeypatch.setattr("app.providers.registry.get_registry", lambda: Register())
    dienst = ts.TelegramService()
    monkeypatch.setattr(dienst, "_token", lambda: "1:x")
    monkeypatch.setattr(ts.TelegramService, "modellwahl", staticmethod(lambda: ("nvidia", "nvidia/nemotron-3.5-lightning-30b-a3b")))
    assert asyncio.run(dienst.verbindung_aufwaermen()) is True
    assert len(anfragen) == 1
    assert anfragen[0].max_tokens == 1 and anfragen[0].slot == "emil" and anfragen[0].denken is False
