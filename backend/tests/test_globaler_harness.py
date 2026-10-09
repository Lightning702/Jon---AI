from __future__ import annotations

import asyncio
import json

import pytest

from app.services.harness import kontext as kontext_verwaltung
from app.services.harness.service import HarnessService


async def _ende(service, task, zeit=20):
    await asyncio.wait_for(service.running[task["id"]], zeit)
    return service.get(task["id"])


@pytest.fixture
def jon_ordner(tmp_path, monkeypatch):
    from app.services.dateiraum_service import get_dateiraum_service

    ordner = tmp_path / "Jon"
    monkeypatch.setattr(type(get_dateiraum_service()), "wurzel", lambda self: ordner)
    return ordner


def test_allgemeiner_auftrag_nutzt_jon_werkzeuge_ohne_projekt(tmp_path, jon_ordner, monkeypatch):
    async def suche(frage, anzahl=6, read=False):
        return {"treffer": [{"title": "Wien", "url": "https://example.org/wien", "snippet": "Hauptstadt"}], "mager": False}

    monkeypatch.setattr("app.services.websearch_service.search_web", suche)
    antworten = iter([
        {"note": "Ich plane.", "tool": "plan", "args": {"steps": ["Recherchieren", "Bericht schreiben"]}},
        {"note": "Ich suche.", "step": 1, "tool": "jon", "args": {"name": "web_search", "args": {"query": "Hauptstadt Österreich"}}},
        {"note": "Fertig.", "step": 2, "tool": "finish", "args": {"summary": "Wien ist die Hauptstadt."}},
    ])
    systeme = []

    async def modell(system, user, **kwargs):
        systeme.append(system)
        return json.dumps(next(antworten))

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        task = service.start("Finde die Hauptstadt von Österreich und berichte", "", modus="allgemein")
        assert task["modus"] == "allgemein"
        assert str(jon_ordner / "Workspace" / "Auftraege") in task["root"]
        return await _ende(service, task)

    ergebnis = asyncio.run(lauf())
    assert ergebnis["status"] == "done"
    assert any(e["werkzeug"] == "jon:web_search" and e["ok"] for e in ergebnis["tool_results"])
    assert ergebnis["modellaufrufe"] == 3
    assert [s["zustand"] for s in ergebnis["fortschritt"]] == ["erledigt", "erledigt"]
    assert any(d["text"] == "Ich suche." for d in ergebnis["decisions"])
    assert "autonomer Agent" in systeme[0]


def test_unbekanntes_jon_werkzeug_wird_als_fehler_gemerkt(tmp_path, jon_ordner):
    antworten = iter([
        {"tool": "jon", "args": {"name": "gibt_es_nicht", "args": {}}},
        {"tool": "finish", "args": {"summary": "Abgebrochen.", "incomplete": True}},
    ])

    async def modell(system, user, **kwargs):
        return json.dumps(next(antworten))

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        return await _ende(service, service.start("Teste Fehler", "", modus="allgemein"))

    ergebnis = asyncio.run(lauf())
    assert ergebnis["errors"] and "gibt es nicht" in ergebnis["errors"][0]["meldung"]
    assert ergebnis["status"] == "needs_review"


def test_kontext_wird_verdichtet_und_arbeit_geht_weiter(tmp_path, jon_ordner, monkeypatch):
    monkeypatch.setattr(kontext_verwaltung, "MAX_EINTRAEGE", 6)
    monkeypatch.setattr(kontext_verwaltung, "BEHALTEN", 2)
    (tmp_path / "projekt").mkdir()
    for nummer in range(12):
        (tmp_path / "projekt" / f"datei{nummer}.txt").write_text(f"Inhalt {nummer}", encoding="utf-8")
    schritte = [{"tool": "plan", "args": {"steps": ["Alles lesen", "Zusammenfassen"]}}]
    schritte += [{"step": 1, "tool": "read", "args": {"path": f"datei{n}.txt"}} for n in range(12)]
    schritte += [{"step": 2, "tool": "finish", "args": {"summary": "Alle Dateien gelesen."}}]
    antworten = iter(schritte)
    verdichtungen = []
    kontexte = []

    async def modell(system, user, **kwargs):
        if system == kontext_verwaltung.SYSTEM:
            verdichtungen.append(user)
            return "VERDICHTET: zwölf Dateien wurden teilweise gelesen."
        kontexte.append(user)
        return json.dumps(next(antworten))

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        return await _ende(service, service.start("Lies alle Dateien", str(tmp_path / "projekt")))

    ergebnis = asyncio.run(lauf())
    assert ergebnis["status"] == "done"
    assert ergebnis["kompaktierungen"] >= 1 and verdichtungen
    assert ergebnis["kompakt"].startswith("VERDICHTET")
    assert any("earlier_work_summary" in k for k in kontexte[-3:])
    assert any(e["type"] == "compacted" for e in ergebnis["log"])


def test_parallele_fachagenten(tmp_path, jon_ordner):
    antworten = {"haupt": iter([
        {"tool": "delegate", "args": {"fragen": [{"role": "research", "question": "A?"}, {"role": "writing", "question": "B?"}]}},
        {"tool": "finish", "args": {"summary": "Beides beantwortet."}},
    ])}

    async def modell(system, user, **kwargs):
        if "lesender Teilagent" in system:
            await asyncio.sleep(0.05)
            return "Antwort " + json.loads(user)["question"]
        return json.dumps(next(antworten["haupt"]))

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        return await _ende(service, service.start("Zwei Fragen klären", "", modus="allgemein"))

    ergebnis = asyncio.run(lauf())
    assert ergebnis["status"] == "done"
    assert sorted(s["result"] for s in ergebnis["specialists"]) == ["Antwort A?", "Antwort B?"]


def test_lauf_ohne_schrittgrenze_laesst_sich_stoppen(tmp_path, jon_ordner):
    zaehler = {"n": 0}

    async def modell(system, user, **kwargs):
        zaehler["n"] += 1
        await asyncio.sleep(0.005)
        return json.dumps({"tool": "create", "args": {"path": f"teil{zaehler['n']}.txt", "content": "x"}})

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        task = service.start("Endlos arbeiten", "", modus="allgemein")
        for _ in range(600):
            if zaehler["n"] > 85:
                break
            await asyncio.sleep(0.05)
        await service.cancel(task["id"])
        await asyncio.sleep(0.05)
        return service.get(task["id"])

    ergebnis = asyncio.run(lauf())
    assert zaehler["n"] > 80
    assert ergebnis["status"] == "cancelled"


def test_model_router_haengt_ollama_als_lokalen_ersatz_an(monkeypatch):
    from app.services import chat_service
    from app.services.modell_router import ModelRouter

    async def anbieter(provider, model):
        return [provider]

    async def ersatz(registry, primary):
        return ("ollama", "qwen2.5-coder:7b")

    monkeypatch.setattr(chat_service, "ollama_ersatz", ersatz)

    async def planen(provider, namen, model):
        return [(provider, model)]

    route = asyncio.run(ModelRouter(registry=object()).plan("nvidia", "gross", anbieter=anbieter, planen=planen))
    assert route[0] == ("nvidia", "gross")
    assert ("ollama", "qwen2.5-coder:7b") in route


def test_harness_route_laeuft_ueber_den_router(monkeypatch):
    from app.services.harness import modell

    gesehen = {}

    class Router:
        async def plan(self, provider, model, **werte):
            gesehen.update(provider=provider, model=model, **werte)
            return [(provider, model), ("ollama", "lokal")]

    monkeypatch.setattr("app.services.modell_router.get_model_router", lambda: Router())
    route = asyncio.run(modell.route_bauen(modell.Zugang("nvidia", "gross")))
    assert route[-1] == ("ollama", "lokal") and gesehen["provider"] == "nvidia"


@pytest.mark.standard
def test_standard_behaelt_schrittgrenze(tmp_path, jon_ordner):
    zaehler = {"n": 0}

    async def modell(system, user, **kwargs):
        zaehler["n"] += 1
        return json.dumps({"tool": "create", "args": {"path": f"teil{zaehler['n']}.txt", "content": "x"}})

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        return await _ende(service, service.start("Endlos", "", modus="allgemein"), 60)

    ergebnis = asyncio.run(lauf())
    assert ergebnis["status"] == "needs_review" and "Schrittlimit (80)" in ergebnis["summary"]


def test_schleifen_werden_erkannt_und_als_warnung_mitgegeben():
    from app.services.harness.service import kontext_bauen, schleife_erkennen

    verlauf = [{"tool": "jon", "args": {"name": "web_search"}, "result": "{}"} for _ in range(5)]
    assert "5-mal" in schleife_erkennen(verlauf)
    assert schleife_erkennen(verlauf[:4]) == ""
    assert schleife_erkennen([{"tool": "read", "args": {}}] * 6) == ""
    task = {"goal": "x", "root": ".", "steps": [], "changes": []}
    assert "warnung" in json.loads(kontext_bauen(task, [], [], verlauf, 90000))


def test_plan_nimmt_lange_und_strukturierte_plaene_an():
    from app.services.harness.service import MAX_PLAN, plan_schritte

    assert plan_schritte({"steps": [{"schritt": "Vorlage lesen"}, "2. Recherche", {"titel": "Folien bauen", "details": "x"}]}) == ["Vorlage lesen", "Recherche", "Folien bauen"]
    assert plan_schritte({"steps": "1. eins\n2. zwei"}) == ["eins", "zwei"]
    assert plan_schritte({"steps": []}) == []
    assert MAX_PLAN >= 20
