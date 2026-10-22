from __future__ import annotations

import asyncio
import json

import pytest

from app.services import btw_service
from app.services.harness.service import HarnessService


@pytest.fixture
def jon_ordner(tmp_path, monkeypatch):
    from app.services.dateiraum_service import get_dateiraum_service

    ordner = tmp_path / "Jon"
    monkeypatch.setattr(type(get_dateiraum_service()), "wurzel", lambda self: ordner)
    return ordner


def test_nachauftrag_wird_erkannt():
    assert btw_service.ist_nachauftrag("/btw danach: schick mir die Datei per Mail")
    assert btw_service.ist_nachauftrag("Anschließend erstelle noch ein Word-Dokument")
    assert btw_service.ist_nachauftrag("mach bitte eine Zusammenfassung, wenn du fertig bist")
    assert not btw_service.ist_nachauftrag("/btw wie weit bist du?")
    assert not btw_service.ist_nachauftrag("Was ist eine inkrementelle Sicherung?")
    assert btw_service.auftrag_text("/btw danach: schick mir die Datei") == "schick mir die Datei"
    assert btw_service.ohne_befehl("/btw   Wie spät ist es") == "Wie spät ist es"


def test_zwischenfrage_nutzt_verlauf_ohne_denken(monkeypatch):
    gesehen = {}

    async def complete(system, user, **kwargs):
        gesehen.update(kwargs, user=user, system=system)
        return "Die 3-2-1-Regel heißt: drei Kopien, zwei Medien, eine außer Haus."

    monkeypatch.setattr("app.services.llm.complete", complete)
    ergebnis = asyncio.run(btw_service.antworten("/btw was war nochmal die 3-2-1-Regel?", [{"role": "user", "content": "Erklär mir Backups"}], nebenbei="Präsentation über Datensicherung"))
    assert ergebnis["art"] == "frage"
    assert "drei Kopien" in ergebnis["antwort"]
    assert gesehen["denken"] is False
    assert "Erklär mir Backups" in gesehen["user"]
    assert "Präsentation über Datensicherung" in gesehen["user"]
    assert "ZWISCHENFRAGE: was war nochmal die 3-2-1-Regel?" in gesehen["user"]


def test_leere_zwischenfrage():
    assert asyncio.run(btw_service.antworten("/btw"))["art"] == "leer"


def test_nachauftrag_im_chat_kommt_zurueck():
    ergebnis = asyncio.run(btw_service.antworten("/btw danach übersetz das ins Englische"))
    assert ergebnis["art"] == "nachauftrag"
    assert ergebnis["auftrag"] == "übersetz das ins Englische"


def test_harness_startet_nachauftrag_nach_dem_ende(tmp_path, jon_ordner, monkeypatch):
    monkeypatch.setattr(HarnessService, "alles_erlaubt", staticmethod(lambda: True))
    tor = {"auf": None}
    ziele = []

    async def modell(system, user, **kwargs):
        if "Nachauftrag-Ziel" in user:
            ziele.append("nach")
            return json.dumps({"note": "Erledigt.", "tool": "finish", "args": {"summary": "Nachauftrag erledigt."}})
        await tor["auf"].wait()
        return json.dumps({"note": "Fertig.", "tool": "finish", "args": {"summary": "Erster Auftrag erledigt."}})

    async def lauf():
        tor["auf"] = asyncio.Event()
        service = HarnessService(tmp_path / "harness", modell)
        monkeypatch.setattr("app.services.harness.get_harness_service", lambda: service)
        erster = service.start("Schreib einen kurzen Text", "", modus="allgemein")
        await asyncio.sleep(0.05)
        ergebnis = await btw_service.antworten("/btw danach: Nachauftrag-Ziel bitte erledigen", task_id=erster["id"])
        assert ergebnis["art"] == "nachauftrag"
        assert service.get(erster["id"])["nachauftraege"] == ["Nachauftrag-Ziel bitte erledigen"]
        tor["auf"].set()
        await asyncio.wait_for(service.running[erster["id"]], 20)
        for _ in range(200):
            neue = [t for t in service.tasks.values() if t["id"] != erster["id"]]
            if neue and neue[0]["status"] in ("done", "needs_review"):
                return service, erster, neue[0]
            await asyncio.sleep(0.05)
        raise AssertionError("Nachauftrag wurde nicht gestartet")

    service, erster, neu = asyncio.run(lauf())
    assert neu["goal"] == "Nachauftrag-Ziel bitte erledigen"
    assert service.sitzung_von(neu) == service.sitzung_von(erster)
    assert "nachauftraege" not in service.get(erster["id"])
    assert ziele == ["nach"]


def test_btw_route(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    async def complete(system, user, **kwargs):
        return "Kurz gesagt: ja."

    monkeypatch.setattr("app.services.llm.complete", complete)
    with TestClient(app) as client:
        antwort = client.post("/api/btw", json={"frage": "/btw geht das?"})
    assert antwort.status_code == 200
    assert antwort.json() == {"art": "frage", "antwort": "Kurz gesagt: ja."}


def test_telegram_btw_antwortet_sofort_und_merkt_nachauftrag_vor(monkeypatch):
    from app.services.telegram_service import TelegramService

    dienst = TelegramService()
    gesendet = []
    erledigt = []
    tor = {}

    async def senden(chat_id, text, *args, **kwargs):
        gesendet.append(text)

    async def bearbeiten(chat_id, text, voice=False):
        if text == "Lange Aufgabe":
            await tor["auf"].wait()
        erledigt.append(text)

    async def complete(system, user, **kwargs):
        assert "Lange Aufgabe" in user
        return "Ich arbeite noch an deiner langen Aufgabe."

    monkeypatch.setattr(dienst, "send", senden)
    monkeypatch.setattr(dienst, "_handle", bearbeiten)
    monkeypatch.setattr("app.services.llm.complete", complete)

    async def lauf():
        tor["auf"] = asyncio.Event()
        dienst._launch("7", "Lange Aufgabe")
        await asyncio.sleep(0.05)
        await dienst._btw("7", "/btw wie weit bist du?")
        await dienst._btw("7", "/btw danach schick mir eine Zusammenfassung")
        assert erledigt == []
        tor["auf"].set()
        await asyncio.gather(*dienst._running["7"])

    asyncio.run(lauf())
    assert "Nebenbei: Ich arbeite noch an deiner langen Aufgabe." in gesendet
    assert any(t.startswith("Notiert.") and "schick mir eine Zusammenfassung" in t for t in gesendet)
    assert not any("vorige Nachricht" in t for t in gesendet)
    assert erledigt == ["Lange Aufgabe", "schick mir eine Zusammenfassung"]
