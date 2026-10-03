from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.providers.base import ChatMessage, ChatRequest, ProviderError
from app.providers.openai_compatible import STREAM_PAUSE_S, OpenAICompatibleProvider, fehlertext


class Strom:
    def __init__(self, fehler):
        self.fehler = fehler
        self.teile = [SimpleNamespace(usage=None, choices=[SimpleNamespace(delta=SimpleNamespace(reasoning_content="Ich denke nach", content=None, tool_calls=None))])]

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.teile:
            return self.teile.pop(0)
        raise self.fehler


class Client:
    def __init__(self, fehler):
        self.optionen = []
        self.fehler = fehler
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, **kwargs):
        self.optionen.append(kwargs)
        return self

    async def create(self, **payload):
        return Strom(self.fehler)


@pytest.mark.parametrize("fehler, wort", [(httpx.ReadTimeout(""), "abgerissen"), (httpx.RemoteProtocolError(""), "getrennt")])
def test_abbruch_mitten_im_strom_hat_klare_meldung(monkeypatch, fehler, wort):
    anbieter = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
    anbieter.name = "nvidia"
    anbieter._no_tool_models = set()
    client = Client(fehler)
    monkeypatch.setattr(anbieter, "_client", lambda slot="jon": client, raising=False)
    anfrage = ChatRequest(messages=[ChatMessage(role="user", content="Hallo")], model="nvidia/nemotron-3-ultra-550b", temperature=0.2, top_p=1.0, max_tokens=100, tools=[], slot="jon")

    async def lauf():
        teile = []
        async for teil in anbieter.stream(anfrage, None):
            teile.append(teil)
        return teile

    with pytest.raises(ProviderError) as info:
        asyncio.run(lauf())
    meldung = str(info.value)
    assert meldung.startswith("nvidia: ") and wort in meldung
    assert len(meldung) > 30
    zeit = client.optionen[0]["timeout"]
    assert zeit.read >= STREAM_PAUSE_S and zeit.connect < 60


def test_fehlertext_ist_nie_leer():
    assert fehlertext(ValueError("")) == "ValueError ohne Fehlermeldung"
    assert fehlertext(RuntimeError("kaputt")) == "kaputt"
