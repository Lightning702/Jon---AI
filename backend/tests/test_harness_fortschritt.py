from __future__ import annotations

import asyncio
import json

import pytest

from app.services.harness import kontext as kontext_verwaltung
from app.services.harness import service as harness_service
from app.services.harness.service import HarnessService, kontext_bauen
from app.services.harness.workspace import Workspace


async def _ende(service, task, zeit=20):
    await asyncio.wait_for(service.running[task["id"]], zeit)
    return service.get(task["id"])


def _projekt(tmp_path, anzahl=450):
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    zeilen = [f'<div class="karte" data-nr="{n}">Abschnitt {n} mit "Anführungszeichen" und Inhalt</div>' for n in range(anzahl)]
    (projekt / "seite.html").write_text("\n".join(zeilen), encoding="utf-8")
    return projekt


def test_endloses_lesen_wird_gewarnt_gesperrt_und_angehalten(tmp_path):
    projekt = _projekt(tmp_path)
    kontexte = []

    async def modell(system, user, **kwargs):
        if system == kontext_verwaltung.SYSTEM:
            return json.dumps({"tool": "read", "args": {"path": "seite.html"}})
        kontexte.append(json.loads(user))
        if len(kontexte) == 1:
            return json.dumps({"tool": "plan", "args": {"steps": ["Lesen", "Neu gestalten"]}})
        return json.dumps({"note": "Ich lese die Seite vollständig.", "tool": "read", "args": {"path": "seite.html", "start": 1, "count": 500}})

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        return await _ende(service, service.start("Gestalte seite.html moderner", str(projekt)))

    ergebnis = asyncio.run(lauf())
    assert ergebnis["status"] == "needs_review"
    assert len(kontexte) <= harness_service.OHNE_FORTSCHRITT_ENDE + 1
    assert any("mehrfach gelesen" in k.get("warnung", "") for k in kontexte)
    assert any("nichts umgesetzt" in k.get("warnung", "") for k in kontexte)
    assert any(harness_service.GESPERRT in e["message"] for e in ergebnis["log"] if e["type"] == "action_error")
    assert any("seite.html: Zeilen 1-450 von 450" in " ".join(k.get("already_read", [])) for k in kontexte)
    assert not ergebnis["kompakt"].lstrip().startswith("{")


def test_umsetzen_setzt_den_waechter_zurueck_und_ueberschreibt_nach_dem_lesen(tmp_path):
    projekt = _projekt(tmp_path)
    schritte = [{"tool": "plan", "args": {"steps": ["Lesen", "Neu schreiben"]}}]
    schritte += [{"tool": "search", "args": {"text": "karte"}}] * 12
    schritte += [{"tool": "read", "args": {"path": "seite.html"}}]
    schritte += [{"tool": "create", "args": {"path": "seite.html", "content": "<main>Neu</main>", "overwrite": True}}]
    schritte += [{"tool": "search", "args": {"text": "Neu"}}] * 3
    schritte += [{"tool": "finish", "args": {"summary": "Neu geschrieben", "incomplete": True}}]
    folge = iter(schritte)
    kontexte = []

    async def modell(system, user, **kwargs):
        if system == kontext_verwaltung.SYSTEM:
            return "Bisher wurde seite.html gesucht und gelesen, als Nächstes wird sie neu geschrieben."
        kontexte.append(json.loads(user))
        return json.dumps(next(folge))

    async def lauf():
        service = HarnessService(tmp_path / "harness", modell)
        return await _ende(service, service.start("Gestalte seite.html neu", str(projekt)))

    ergebnis = asyncio.run(lauf())
    assert ergebnis["status"] == "needs_review"
    assert ergebnis["summary"].startswith("Neu geschrieben")
    assert (projekt / "seite.html").read_text(encoding="utf-8") == "<main>Neu</main>"
    assert ergebnis["ohne_fortschritt"] == 3
    assert "nichts umgesetzt" not in kontexte[-1].get("warnung", "")


def test_ueberschreiben_nur_nach_dem_lesen(tmp_path):
    (tmp_path / "a.html").write_text("alt", encoding="utf-8")
    workspace = Workspace(str(tmp_path))
    with pytest.raises(ValueError):
        workspace.create("a.html", "neu", overwrite=True)
    with pytest.raises(FileExistsError):
        workspace.create("a.html", "neu")
    workspace.read("a.html")
    ergebnis = workspace.create("a.html", "neu", overwrite=True)
    assert ergebnis["overwritten"] and (tmp_path / "a.html").read_text(encoding="utf-8") == "neu"


def test_ganze_datei_bleibt_im_kontext_sichtbar(tmp_path):
    projekt = _projekt(tmp_path, 260)
    inhalt = Workspace(str(projekt)).read("seite.html", 1, 500)
    assert len(inhalt["content"]) > 16000
    verlauf = [{"tool": "read", "args": {"path": "seite.html", "start": 1, "count": 500}, "result": harness_service.ergebnis_text("read", inhalt)}]
    verlauf += [{"tool": "search", "args": {"text": "x"}, "result": "{}"}]
    task = {"goal": "x", "root": ".", "steps": [], "changes": []}
    daten = json.loads(kontext_bauen(task, [], [], verlauf, 90000))
    gelesen = daten["recent_actions"][0]["result"]
    assert "gekürzt" not in gelesen and gelesen.endswith(inhalt["content"][-60:])


def test_unbrauchbare_verdichtung_wird_durch_gesicherten_stand_ersetzt():
    task = {"goal": "Seite neu gestalten", "steps": ["Lesen", "Schreiben"], "changes": [], "decisions": [], "kompakt": "", "kompaktierungen": 0}
    harness_service.zustand.gelesen(task, "seite.html", 1, 450, 450)
    verlauf = [{"tool": "read", "args": {"path": "seite.html"}, "result": "x"}] * 8

    async def fragen(system, user):
        return '{"note":"Ich lese.","tool":"read","args":{"path":"seite.html"}}'

    asyncio.run(kontext_verwaltung.kompaktieren(task, verlauf, fragen))
    assert "Bereits gelesen: seite.html: Zeilen 1-450 von 450" in task["kompakt"]
    assert not task["kompakt"].startswith("{")
    assert len(verlauf) == kontext_verwaltung.BEHALTEN
