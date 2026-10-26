from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.services import telegram_service as ts
from app.services import weltzeit
from app.services.chat_service import heute_block

MITTAG = datetime(2026, 10, 26, 16, 0, tzinfo=timezone.utc)


def test_uhrzeit_in_anderen_staedten():
    tokio = weltzeit.antwort("Wie spät ist es gerade in Tokio?", MITTAG)
    assert tokio.startswith("In Tokio ist es jetzt 01:00 Uhr, schon Dienstag der 27.10.")
    assert weltzeit.antwort("wie spät ist es in New York", MITTAG).startswith("In New York ist es jetzt 12:00 Uhr")
    assert weltzeit.antwort("Wie spät ist es auf Hawaii?", MITTAG).startswith("Auf Hawaii ist es jetzt 06:00 Uhr")
    assert "21:30" in weltzeit.antwort("Wie viel Uhr ist es eigentlich in Neu-Delhi?", MITTAG)
    assert weltzeit.antwort("Wie spät ist es?", MITTAG).startswith("Es ist ")


def test_keine_falschen_treffer():
    for text in (
        "Wie spät ist es in Tokio, wenn es hier 18 Uhr ist?",
        "Wie spät war es gestern in Tokio?",
        "Wie spät ist es in Hogwarts?",
        "Erklär mir Zeitzonen",
        "Ich komme heute spät nach Hause",
    ):
        assert weltzeit.antwort(text, MITTAG) is None, text


def test_telegram_beantwortet_uhrzeit_ohne_modell(monkeypatch):
    dienst = ts.TelegramService()

    def kein_modell(*_a, **_k):
        raise AssertionError("Fuer die Uhrzeit darf kein Modell gefragt werden")

    monkeypatch.setattr(ts.TelegramService, "_answer", kein_modell, raising=False)
    antwort = asyncio.run(dienst._schnellweg("Wie spät ist es in Tokio?", None))
    assert antwort.startswith("In Tokio ist es jetzt")


def test_systemprompt_kennt_die_weltzeit():
    block = heute_block()
    assert "Weltzeit jetzt:" in block and "Tokio" in block and "keine Suche" in block


def test_hoeflichkeit_und_kurz_am_ende():
    assert weltzeit.antwort("Wie spät ist es gerade in Tokio? Antworte kurz.", MITTAG).startswith("In Tokio ist es jetzt 01:00 Uhr")
    assert weltzeit.antwort("Wie spät ist es in London bitte?", MITTAG).startswith("In London ist es jetzt 16:00 Uhr")
    assert weltzeit.antwort("Wie spät ist es in Tokio und erklär mir den Kaiserpalast", MITTAG) is None
