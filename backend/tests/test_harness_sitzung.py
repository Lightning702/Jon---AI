from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

import pytest

from app.services.harness.service import HarnessService
from app.services.harness.vorschau import Vorschau, erkennen


def modell(antworten, kontexte):
    folge = iter(antworten)

    async def complete(system, user, **kwargs):
        kontexte.append(json.loads(user))
        return json.dumps(next(folge))

    return complete


async def fertig(service, task):
    await asyncio.wait_for(service.running[task["id"]], 10)
    return service.get(task["id"])


def test_folgeauftrag_bleibt_in_derselben_sitzung_und_kennt_den_vorgaenger(tmp_path):
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    kontexte = []
    antworten = [
        {"tool": "plan", "args": {"steps": ["Seite anlegen"]}},
        {"tool": "create", "args": {"path": "index.html", "content": "<h1>Hallo</h1>"}},
        {"tool": "finish", "args": {"summary": "index.html angelegt", "incomplete": True}},
        {"tool": "finish", "args": {"summary": "Titel angepasst", "incomplete": True}},
    ]

    async def ablauf():
        service = HarnessService(tmp_path / "tasks", modell(antworten, kontexte))
        erster = await fertig(service, service.start("Baue eine Startseite", str(projekt)))
        assert erster["thread"] == erster["id"]
        assert service.fortsetzbar(str(projekt)) == erster["thread"]
        zweiter = await fertig(service, service.start("Mach den Titel größer", str(projekt), thread=erster["thread"]))
        assert zweiter["thread"] == erster["thread"]
        sitzungen = service.sitzungen()
        assert len(sitzungen) == 1 and sitzungen[0]["tasks"] == 2 and sitzungen[0]["title"] == "Baue eine Startseite"
        assert [t["id"] for t in service.sitzung(erster["thread"])] == [erster["id"], zweiter["id"]]
        anderes = tmp_path / "anderes"
        anderes.mkdir()
        with pytest.raises(ValueError, match="anderen Projekt"):
            service.start("Fremd", str(anderes), thread=erster["thread"])
        with pytest.raises(ValueError, match="gibt es nicht"):
            service.start("Weg", str(projekt), thread="abc123")
        neu = HarnessService(tmp_path / "tasks")
        assert neu.sitzungen()[0]["tasks"] == 2

    asyncio.run(ablauf())
    frueher = kontexte[-1]["earlier_tasks"]
    assert frueher[0]["goal"] == "Baue eine Startseite"
    assert frueher[0]["changed_files"] == ["index.html"]
    assert "angelegt" in frueher[0]["summary"]
    assert kontexte[0]["earlier_tasks"] == []


def test_chat_werkzeug_setzt_die_letzte_sitzung_fort(tmp_path, monkeypatch):
    from app.services.harness import chat as harness_chat
    from app.services.harness import service as harness_service

    projekt = tmp_path / "projekt"
    projekt.mkdir()

    async def complete(system, user, **kwargs):
        return json.dumps({"tool": "finish", "args": {"summary": "ok"}})

    service = HarnessService(tmp_path / "tasks", complete)
    monkeypatch.setattr(harness_chat, "get_harness_service", lambda: service)
    monkeypatch.setattr(harness_service, "get_harness_service", lambda: service)

    async def ablauf():
        erster = await harness_chat.execute({"action": "start", "goal": "Eins"}, "app", str(projekt))
        await service.running[erster["task_id"]]
        zweiter = await harness_chat.execute({"action": "start", "goal": "Zwei"}, "app", str(projekt))
        await service.running[zweiter["task_id"]]
        dritter = await harness_chat.execute({"action": "start", "goal": "Drei", "new_session": True}, "app", str(projekt))
        await service.running[dritter["task_id"]]
        return erster, zweiter, dritter

    erster, zweiter, dritter = asyncio.run(ablauf())
    assert zweiter["continued"] and zweiter["thread"] == erster["thread"]
    assert not dritter["continued"] and dritter["thread"] != erster["thread"]


def test_vorschau_erkennt_projektarten(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "package.json").write_text(json.dumps({"scripts": {"build": "x", "dev": "vite"}}), encoding="utf-8")
    assert erkennen(tmp_path / "a") == {"art": "npm", "skript": "dev", "befehl": "npm install && npm run dev", "installieren": True}
    (tmp_path / "b" / "dist").mkdir(parents=True)
    (tmp_path / "b" / "dist" / "index.html").write_text("x", encoding="utf-8")
    assert erkennen(tmp_path / "b")["ordner"].endswith("dist")
    (tmp_path / "c" / "seiten").mkdir(parents=True)
    (tmp_path / "c" / "seiten" / "spiel.html").write_text("x", encoding="utf-8")
    assert erkennen(tmp_path / "c")["datei"] == "spiel.html"
    (tmp_path / "d").mkdir()
    assert erkennen(tmp_path / "d") == {"art": ""}


def test_statische_vorschau_liefert_seite_aber_keine_geheimnisse(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Vorschau</h1>", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "app.js").write_text("ok", encoding="utf-8")
    vorschau = Vorschau()

    async def ablauf():
        zustand = await vorschau.starten(tmp_path)
        assert zustand["status"] == "laeuft"
        url = zustand["url"]
        basis = url.rsplit("/", 1)[0]
        lesen = lambda adresse, **kopf: urllib.request.urlopen(urllib.request.Request(adresse, headers=kopf), timeout=5).read().decode()
        assert "Vorschau" in await asyncio.to_thread(lesen, url)
        assert await asyncio.to_thread(lesen, basis + "/build/app.js") == "ok"
        with pytest.raises(urllib.error.HTTPError) as fehler:
            await asyncio.to_thread(lesen, basis + "/.env")
        assert fehler.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as fehler:
            await asyncio.to_thread(lesen, url, Host="boese.example")
        assert fehler.value.code == 403
        assert (await vorschau.starten(tmp_path))["url"] == url
        gestoppt = await vorschau.stoppen(tmp_path)
        assert gestoppt["status"] == "gestoppt"
        with pytest.raises(OSError):
            await asyncio.to_thread(lesen, url)

    asyncio.run(ablauf())


@pytest.mark.skipif(os.name == "nt", reason="Prozessbefehl ist POSIX-spezifisch")
def test_server_vorschau_findet_adresse_und_stoppt_den_prozess(tmp_path, monkeypatch):
    from app.services.harness import vorschau as modul

    befehl = f'"{sys.executable}" -c "import time; print(\'  Local:   \\x1b[36mhttp://localhost:4321/\\x1b[0m\', flush=True); time.sleep(60)"'
    monkeypatch.setattr(modul, "erkennen", lambda root: {"art": "npm", "skript": "dev", "befehl": befehl, "installieren": False})
    vorschau = Vorschau()

    async def ablauf():
        await vorschau.starten(tmp_path)
        for _ in range(100):
            zustand = vorschau.zustand(tmp_path)
            if zustand["status"] == "laeuft":
                break
            await asyncio.sleep(0.05)
        assert zustand["url"] == "http://localhost:4321/"
        prozess = vorschau.laeufe[vorschau._schluessel(tmp_path)]["prozess"]
        await vorschau.close()
        assert prozess.returncode is not None

    asyncio.run(ablauf())


def test_aenderung_ohne_plan_bekommt_automatischen_plan(tmp_path):
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    (projekt / "index.html").write_text("<h1>Alt</h1>", encoding="utf-8")
    kontexte = []
    antworten = [
        {"tool": "read", "args": {"path": "index.html"}},
        {"tool": "edit", "args": {"path": "index.html", "old": "Alt", "new": "Neu"}},
        {"tool": "finish", "args": {"summary": "Titel geändert", "incomplete": True}},
    ]

    async def ablauf():
        service = HarnessService(tmp_path / "tasks", modell(antworten, kontexte))
        return await fertig(service, service.start("Ändere den Titel", str(projekt)))

    ergebnis = asyncio.run(ablauf())
    assert (projekt / "index.html").read_text(encoding="utf-8") == "<h1>Neu</h1>"
    assert ergebnis["steps"] == ["Ändere den Titel"]
    assert any(e["type"] == "hinweis" and "Plan" in e["message"] for e in ergebnis["log"])


def test_wiederholter_fehler_haelt_frueh_an(tmp_path):
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    kontexte = []
    antworten = [{"tool": "plan", "args": {"steps": ["x"]}}] + [{"tool": "read", "args": {"path": "fehlt.txt"}}] * 20

    async def ablauf():
        service = HarnessService(tmp_path / "tasks", modell(antworten, kontexte))
        return await fertig(service, service.start("Lies die Datei", str(projekt)))

    ergebnis = asyncio.run(ablauf())
    assert ergebnis["status"] == "needs_review"
    assert "4-mal denselben Fehler" in ergebnis["summary"]
    assert len(kontexte) == 5
    assert kontexte[-1]["recent_actions"][-1]["tool"] == "read"
