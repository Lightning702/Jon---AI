from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import app.providers.openai_compatible as modul
from app.providers.base import ProviderError
from app.providers.openai_compatible import OpenAICompatibleProvider


class Gebremst(Exception):
    status_code = 429
    response = SimpleNamespace(headers={"retry-after": "1"})


def _anbieter() -> OpenAICompatibleProvider:
    anbieter = OpenAICompatibleProvider.__new__(OpenAICompatibleProvider)
    anbieter.name = "nvidia"
    return anbieter


def _client(fehlversuche: int, zaehler: dict):
    async def create(**kwargs):
        zaehler["n"] += 1
        if zaehler["n"] <= fehlversuche:
            raise Gebremst("Too Many Requests")
        return "antwort"

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.fixture(autouse=True)
def ohne_warten(monkeypatch):
    gewartet = []

    async def schlafen(sekunden):
        gewartet.append(sekunden)

    monkeypatch.setattr(modul.asyncio, "sleep", schlafen)
    return gewartet


def test_ratenbegrenzung_wird_abgewartet(ohne_warten):
    zaehler = {"n": 0}
    assert asyncio.run(_anbieter()._create_with_retry(_client(2, zaehler), {"model": "m"})) == "antwort"
    assert zaehler["n"] == 3
    assert ohne_warten == [2.0, 4.0]


def test_dauerhafte_ratenbegrenzung_meldet_einen_fehler(ohne_warten):
    zaehler = {"n": 0}
    with pytest.raises(ProviderError):
        asyncio.run(_anbieter()._create_with_retry(_client(99, zaehler), {"model": "m"}))
    assert zaehler["n"] == 1 + modul.RATE_RETRIES
