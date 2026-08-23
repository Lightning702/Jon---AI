from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.research import stages
from app.services.research.models import (
    STATUS_DONE,
    STATUS_INTERRUPTED,
    STATUS_RUNNING,
    ResearchTask,
    slugify,
)
from app.services.research.service import parse_minutes
from app.services.research.store import ResearchStore
from app.services.research.web import UnsafeUrl, check_url, domain_of, extract_text


def test_slug_macht_dateinamen_sicher():
    assert slugify("Quantenmechanik") == "quantenmechanik"
    assert slugify("Neuronale Netze & Deep Learning") == "neuronale-netze-deep-learning"
    assert slugify("Größe / Übung") == "groesse-uebung"
    assert slugify("") == "thema"
    assert slugify("123") == "123"
    assert len(slugify("x" * 200)) <= 48


def test_zeitbudget_aus_sprache():
    assert parse_minutes("Du hast zwei Stunden") == 120
    assert parse_minutes("du hast 90 Minuten Zeit") == 90
    assert parse_minutes("eine Stunde") == 60
    assert parse_minutes("1,5 Stunden") == 90
    assert parse_minutes("lerne alles über Physik") == 0
    assert parse_minutes("lerne alles über Physik", 45) == 45


def test_sicherer_webzugriff_blockt_gefaehrliches():
    assert check_url("https://de.wikipedia.org/wiki/Physik").startswith("https://")
    for gesperrt in (
        "ftp://example.com/x",
        "https://shop.de/checkout",
        "https://x.de/login",
        "https://x.de/warenkorb",
        "https://x.de/setup.exe",
        "https://x.de/archiv.zip",
        "http://127.0.0.1/admin",
        "http://192.168.0.5/",
        "http://localhost:8756/api",
    ):
        with pytest.raises(UnsafeUrl):
            check_url(gesperrt)


def test_domain_erkennung():
    assert domain_of("https://www.arxiv.org/abs/1") == "arxiv.org"
    assert domain_of("https://de.wikipedia.org/wiki/X") == "de.wikipedia.org"


def test_textextraktion_wirft_navigation_weg():
    html = (
        "<html><head><title>Testseite</title></head><body>"
        "<nav><a href='#'>Start</a><a href='#'>Login</a></nav>"
        "<main><h2>Kapitel eins</h2>"
        "<p>Dies ist ein ausreichend langer Absatz mit echtem Inhalt, "
        "der die Mindestlaenge klar ueberschreitet.</p>"
        "<script>var x = 1;</script>"
        "<p>Kurz</p></main>"
        "<footer>Impressum</footer></body></html>"
    )
    titel, text = extract_text(html)
    assert titel == "Testseite"
    assert "## Kapitel eins" in text
    assert "ausreichend langer Absatz" in text
    assert "var x" not in text
    assert "Impressum" not in text
    assert "Kurz" not in text


def test_json_parser_ist_tolerant():
    assert stages.parse_json('{"a": 1}') == {"a": 1}
    assert stages.parse_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert stages.parse_json('Hier bitte: {"a": 3} — fertig') == {"a": 3}
    assert stages.parse_json("[1, 2, 3]") == [1, 2, 3]
    assert stages.parse_json("gar kein json", {"fallback": True}) == {"fallback": True}


def test_task_zeitrechnung_und_fortschritt():
    task = ResearchTask.create("Quantenmechanik", 60, "nvidia", "modell", "normal")
    assert task.slug == "quantenmechanik"
    assert task.budget_s == 3600
    task.status = STATUS_RUNNING
    task.started_at = time.time() - 600
    assert 590 < task.elapsed_s() < 620
    assert 2980 < task.remaining_s() < 3010
    daten = task.to_dict()
    assert daten["minuten"] == 60
    assert daten["ordner"] == "skills/quantenmechanik"
    assert 0 <= daten["fortschritt"] <= 1


def test_task_speichern_und_wiederherstellen(tmp_path, monkeypatch):
    import app.services.research.store as store_module

    monkeypatch.setattr(store_module, "RESEARCH_DIR", tmp_path)
    store = ResearchStore()
    task = ResearchTask.create("Photosynthese", 30, "nvidia", "modell")
    task.status = STATUS_RUNNING
    task.files = ["lichtreaktion.md"]
    store.save(task)

    zurueck = store.load(task.id)
    assert zurueck is not None
    assert zurueck.topic == "Photosynthese"
    assert zurueck.files == ["lichtreaktion.md"]

    betroffen = store.mark_interrupted()
    assert task.id in betroffen
    assert store.load(task.id).status == STATUS_INTERRUPTED

    assert len(store.all()) == 1
    assert store.delete(task.id) is True
    assert store.load(task.id) is None


def test_markdown_ablage_und_skillordner(tmp_path, monkeypatch):
    import app.services.research.storage as storage
    import app.services.skill_service as skill_service

    monkeypatch.setattr(storage, "SKILLS_DIR", tmp_path)
    monkeypatch.setattr(skill_service, "SKILLS_DIR", tmp_path)

    task = ResearchTask.create("Quantenmechanik", 30, "nvidia", "modell")
    task.status = STATUS_DONE
    name = storage.write_file(task.slug, slugify("Quantenverschränkung"), "# Test\n\nInhalt")
    assert name == "quantenverschraenkung.md"
    readme = storage.write_index(task, "# Quantenmechanik\n\nÜbersicht")
    assert readme == "README.md"
    task.files = [name, readme]
    quellen = storage.write_sources(task)
    assert quellen == "sources.md"
    storage.write_file(task.slug, "skill", "# Quantenmechanik\n\nSkill")

    assert "Inhalt" in storage.read_file(task.slug, name)
    dateien = {eintrag["name"] for eintrag in storage.list_files(task.slug)}
    assert dateien == {"quantenverschraenkung.md", "README.md", "sources.md", "skill.md"}

    dienst = skill_service.SkillService()
    eintraege = dienst.list()
    assert any(
        eintrag["name"] == "quantenmechanik" and eintrag["kind"] == "wissen"
        for eintrag in eintraege
    )
    gelesen = dienst.read("quantenmechanik")
    assert gelesen["kind"] == "wissen"
    assert len(gelesen["files"]) == 4
    datei = dienst.read_file("quantenmechanik", "quantenverschraenkung")
    assert "Inhalt" in datei["content"]
    assert "Wissensordner" in dienst.catalog()

    (tmp_path / "geheim.md").write_text("streng geheim", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        dienst.read_file("quantenmechanik", "../geheim")
    with pytest.raises(ValueError):
        dienst.read_file("quantenmechanik", "böse datei!")
    with pytest.raises(ValueError):
        dienst.read_file("../../etc", "passwd")


def test_flache_skills_bleiben_erhalten(tmp_path, monkeypatch):
    import app.services.skill_service as skill_service

    monkeypatch.setattr(skill_service, "SKILLS_DIR", tmp_path)
    dienst = skill_service.SkillService()
    dienst.write("recherche", "# Recherche\n\nAnleitung")
    eintraege = dienst.list()
    assert eintraege[0]["name"] == "recherche"
    assert eintraege[0]["kind"] == "datei"
    assert dienst.read("recherche")["title"] == "Recherche"
    assert dienst.delete("recherche") is True
    assert dienst.list() == []


def test_deep_learning_tool_startet_und_stoppt(monkeypatch):
    from app.services.research import service as service_module

    class FakeService:
        def __init__(self):
            self.gestoppt = []

        async def start(self, topic, minutes=0, provider=None, model=None, depth="normal"):
            return {
                "id": "task1",
                "thema": topic,
                "minuten": minutes or 45,
                "status": "laeuft",
                "ordner": f"skills/{slugify(topic)}",
            }

        def active(self):
            return [{"id": "task1"}]

        def list(self):
            return []

        def stop(self, task_id):
            self.gestoppt.append(task_id)
            return {"id": task_id, "status": "abgebrochen"}

    fake = FakeService()
    monkeypatch.setattr(service_module, "_service", fake)
    from app.services.tools import ToolBox

    box = ToolBox()
    gestartet = json.loads(
        asyncio.run(
            box.execute("deep_learning", {"action": "start", "topic": "Quantenmechanik", "minutes": 120})
        )
    )
    assert gestartet["gestartet"] is True
    assert gestartet["id"] == "task1"
    assert gestartet["task"]["minuten"] == 120

    ohne_thema = json.loads(
        asyncio.run(box.execute("deep_learning", {"action": "start"}))
    )
    assert "error" in ohne_thema

    gestoppt = json.loads(asyncio.run(box.execute("deep_learning", {"action": "stop"})))
    assert gestoppt["status"] == "abgebrochen"
    assert fake.gestoppt == ["task1"]


def test_resume_holt_uebersprungene_unterthemen_zurueck(tmp_path, monkeypatch):
    import app.services.research.service as service_module
    import app.services.research.store as store_module

    monkeypatch.setattr(store_module, "RESEARCH_DIR", tmp_path)
    dienst = service_module.ResearchService()

    task = ResearchTask.create("Photosynthese", 20, "nvidia", "modell")
    task.status = "abgebrochen"
    task.consumed_s = 60.0
    from app.services.research.models import Subtopic

    task.subtopics = [
        Subtopic(id="a", title="Fertig", question="?", status="fertig"),
        Subtopic(id="b", title="Abgebrochen", question="?", status="laeuft"),
        Subtopic(id="c", title="Uebersprungen", question="?", status="uebersprungen"),
        Subtopic(id="d", title="Leer", question="?", status="leer"),
    ]
    dienst._store.save(task)

    gestartet: list[str] = []

    async def fake_launch(aufgabe):
        gestartet.append(aufgabe.id)

    monkeypatch.setattr(dienst, "_launch", fake_launch)
    ergebnis = asyncio.run(dienst.resume_task(task.id))

    assert gestartet == [task.id]
    assert ergebnis["status"] == "laeuft"
    stati = {s["title"]: s["status"] for s in ergebnis["unterthemen"]}
    assert stati["Fertig"] == "fertig"
    assert stati["Abgebrochen"] == "offen"
    assert stati["Uebersprungen"] == "offen"
    assert stati["Leer"] == "offen"

    gespeichert = dienst._store.load(task.id)
    assert gespeichert.status == "laeuft"
    assert sum(1 for s in gespeichert.subtopics if s.status == "offen") == 3


def test_resume_verlaengert_aufgebrauchtes_zeitbudget(tmp_path, monkeypatch):
    import app.services.research.service as service_module
    import app.services.research.store as store_module

    monkeypatch.setattr(store_module, "RESEARCH_DIR", tmp_path)
    dienst = service_module.ResearchService()

    from app.services.research.models import Subtopic

    task = ResearchTask.create("Photosynthese", 5, "nvidia", "modell")
    task.status = "unterbrochen"
    task.consumed_s = 5 * 60
    task.subtopics = [Subtopic(id="a", title="Offen", question="?", status="offen")]
    dienst._store.save(task)

    async def fake_launch(aufgabe):
        return None

    monkeypatch.setattr(dienst, "_launch", fake_launch)
    ergebnis = asyncio.run(dienst.resume_task(task.id))
    assert ergebnis["verbleibend_s"] >= service_module.MIN_RESUME_S
    assert ergebnis["minuten"] > 5


def test_resume_ignoriert_fertige_recherche(tmp_path, monkeypatch):
    import app.services.research.service as service_module
    import app.services.research.store as store_module

    monkeypatch.setattr(store_module, "RESEARCH_DIR", tmp_path)
    dienst = service_module.ResearchService()
    task = ResearchTask.create("Fertig", 10, "nvidia", "modell")
    task.status = STATUS_DONE
    dienst._store.save(task)

    gestartet: list[str] = []

    async def fake_launch(aufgabe):
        gestartet.append(aufgabe.id)

    monkeypatch.setattr(dienst, "_launch", fake_launch)
    ergebnis = asyncio.run(dienst.resume_task(task.id))
    assert ergebnis["status"] == STATUS_DONE
    assert gestartet == []
