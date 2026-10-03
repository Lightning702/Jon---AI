from __future__ import annotations

import asyncio
import json

import pytest

from app.providers.base import ProviderError, StreamChunk
from app.services.harness import modell
from app.services.harness.service import HarnessService, PROMPT_KURZ, kontext_bauen

FERTIG = json.dumps({"tool": "finish", "args": {"summary": "Erledigt"}})


class Anbieter:
    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.anfragen = []

    def available(self):
        return True

    async def list_models(self):
        return []

    async def stream(self, request, tool_executor=None):
        self.anfragen.append(request)
        antwort = self.antworten.pop(0)
        if isinstance(antwort, Exception):
            raise antwort
        art, text = antwort
        yield StreamChunk(delta=text, kind=art)


@pytest.fixture()
def umgebung(monkeypatch, tmp_path):
    from app.providers import registry as registry_modul

    anbieter: dict[str, Anbieter] = {}
    registry = registry_modul.get_registry()
    monkeypatch.setattr(registry, "get", lambda name: anbieter[name], raising=False)
    monkeypatch.setattr(modell, "WARTEN", (0.0, 0.0, 0.0))
    projekt = tmp_path / "projekt"
    projekt.mkdir()

    def laufen(provider, model, route=None):
        async def plan(zugang):
            return route or [(provider, model)]

        monkeypatch.setattr(modell, "route_bauen", plan)

        async def ablauf():
            service = HarnessService(tmp_path / "tasks")
            task = service.start("Prüfe das Projekt", str(projekt), provider=provider, model=model)
            await asyncio.wait_for(service.running[task["id"]], 10)
            return service.get(task["id"])

        return asyncio.run(ablauf())

    return anbieter, laufen


def test_rate_limit_wird_wiederholt_und_denkblock_ignoriert(umgebung):
    anbieter, laufen = umgebung
    anbieter["nvidia"] = Anbieter([ProviderError("nvidia: Error code: 429 Too Many Requests"), ProviderError("nvidia: 503 Service Unavailable"), ("content", '<think>Vielleicht {"tool":"read","args":{"path":"x"}}</think>' + FERTIG)])
    ergebnis = laufen("nvidia", "gross")
    assert ergebnis["status"] == "done", ergebnis["summary"]
    assert len(anbieter["nvidia"].anfragen) == 3
    assert anbieter["nvidia"].anfragen[0].first_token_timeout >= 120
    assert sum(1 for e in ergebnis["log"] if e["type"] == "hinweis") == 2


def test_haengendes_modell_weicht_auf_ersatzmodell_aus(umgebung):
    anbieter, laufen = umgebung
    anbieter["nvidia"] = Anbieter([ProviderError("nvidia: gross antwortet nicht (Anbieter ueberlastet)")] * 4 + [("content", FERTIG)])
    ergebnis = laufen("nvidia", "gross", [("nvidia", "gross"), ("nvidia", "klein")])
    assert ergebnis["status"] == "done", ergebnis["summary"]
    assert anbieter["nvidia"].anfragen[-1].model == "klein"
    assert ergebnis["aktives_modell"] == "klein"
    assert any("Ausweichmodell klein" in e["message"] for e in ergebnis["log"])


def test_antwort_nur_im_reasoning_wird_gelesen(umgebung):
    anbieter, laufen = umgebung
    anbieter["nvidia"] = Anbieter([("reasoning", "Ich bin fertig. " + FERTIG)])
    assert laufen("nvidia", "denker")["status"] == "done"


def test_dauerhafter_fehler_meldet_klare_ursache(umgebung):
    anbieter, laufen = umgebung
    anbieter["nvidia"] = Anbieter([ProviderError("nvidia: 401 Unauthorized")])
    ergebnis = laufen("nvidia", "gross")
    assert ergebnis["status"] == "failed"
    assert "Kein Modell hat geantwortet" in ergebnis["summary"] and "401" in ergebnis["summary"]


def test_ollama_bekommt_grosses_fenster_und_faellt_bei_speichermangel_zurueck(umgebung, monkeypatch):
    anbieter, laufen = umgebung
    monkeypatch.setattr(modell.Zugang, "ollama_kontext", lambda self: 4096)
    anbieter["ollama"] = Anbieter([ProviderError("Ollama: model requires more system memory (12 GiB) than is available"), ("content", FERTIG)])
    ergebnis = laufen("ollama", "qwen2.5-coder:7b")
    assert ergebnis["status"] == "done", ergebnis["summary"]
    fenster = [a.context_window for a in anbieter["ollama"].anfragen]
    assert fenster == [modell.HARNESS_KONTEXT, 4096]
    assert PROMPT_KURZ in anbieter["ollama"].anfragen[1].messages[0].content
    assert len(anbieter["ollama"].anfragen[1].messages[1].content) <= modell.Zugang("ollama", "x", klein=True).zeichenbudget()


def test_kontext_passt_ins_budget_und_behaelt_die_letzte_aktion():
    task = {"goal": "Ziel", "root": "/p", "steps": ["a"], "changes": []}
    dateien = [f"src/datei_{i}.ts" for i in range(300)]
    verlauf = [{"tool": "read", "args": {"path": f"d{i}"}, "result": "x" * 16000} for i in range(12)]
    text = kontext_bauen(task, dateien, [], verlauf, 6000)
    assert len(text) <= 6000
    daten = json.loads(text)
    assert daten["recent_actions"][-1]["args"]["path"] == "d11"
    assert daten["files"][-1].startswith("… und")
    assert len(kontext_bauen(task, dateien[:5], [], verlauf[:1], 90000)) > 15000


def test_fachteam_wiederholt_bei_ueberlast(monkeypatch):
    from app.services import llm
    from app.services.agenten_service import AgentenService

    aufrufe = []

    async def complete(system, user, **kwargs):
        aufrufe.append(kwargs)
        if len(aufrufe) < 3:
            raise RuntimeError("nvidia: 429 Too Many Requests")
        return "<think>überlegen</think>puellam ist Akkusativ."

    monkeypatch.setattr(llm, "complete", complete)
    monkeypatch.setattr(modell, "WARTEN", (0.0, 0.0, 0.0))
    ergebnis = asyncio.run(AgentenService()._teil_ausfuehren({"titel": "Latein", "auftrag": "Prüfe puellam.", "werkzeug": "keins"}))
    assert not ergebnis.fehler and ergebnis.ergebnis == "puellam ist Akkusativ."
    assert len(aufrufe) == 3 and aufrufe[0]["first_token_timeout"] >= 120
