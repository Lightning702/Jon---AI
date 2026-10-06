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


def test_zwischenmeldungen_planschritt_und_aktionsdetails_landen_im_verlauf(tmp_path):
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    (projekt / "index.html").write_text("<h1>Alt</h1>\n", encoding="utf-8")
    kontexte = []
    antworten = [
        {"note": "Ich plane zuerst die Arbeit.", "step": 1, "tool": "plan", "args": {"steps": ["Datei lesen", "Titel ändern"]}},
        {"note": "Ich lese die Startseite.", "step": 1, "tool": "read", "args": {"path": "index.html"}},
        {"note": "Ich passe den Titel an.", "step": 2, "tool": "edit", "args": {"path": "index.html", "old": "Alt", "new": "Neu"}},
        {"note": "Ich passe den Titel an.", "step": 9, "tool": "finish", "args": {"summary": "Titel geändert", "incomplete": True}},
    ]

    async def ablauf():
        service = HarnessService(tmp_path / "tasks", modell(antworten, kontexte))
        return await fertig(service, service.start("Ändere den Titel", str(projekt)))

    ergebnis = asyncio.run(ablauf())
    notizen = [e["message"] for e in ergebnis["log"] if e["type"] == "notiz"]
    assert notizen == ["Ich plane zuerst die Arbeit.", "Ich lese die Startseite.", "Ich passe den Titel an."]
    gelesen = next(e for e in ergebnis["log"] if e["type"] == "action" and e["tool"] == "read")
    geaendert = next(e for e in ergebnis["log"] if e["type"] == "action" and e["tool"] == "edit")
    assert gelesen["pfad"] == "index.html"
    assert (geaendert["pfad"], geaendert["plus"], geaendert["minus"]) == ("index.html", 1, 1)
    assert ergebnis["plan_schritt"] == 2
    reihenfolge = [e["type"] for e in ergebnis["log"]]
    assert reihenfolge.index("notiz") < reihenfolge.index("action")


def test_befehlsdetails_zeigen_ergebnis_und_letzte_ausgabezeilen():
    from app.services.harness.service import aktion_details

    ok = aktion_details("verify", {"command": "npm test"}, {"ok": True, "output": "a\n\nb\nc\nd\n18 tests passed\n"})
    assert ok == {"message": "npm test", "ok": True, "ausgabe": "b\nc\nd\n18 tests passed"}
    abgelehnt = aktion_details("command", {"command": "rm -rf x"}, {"error": "Freigabe abgelehnt"})
    assert abgelehnt["ok"] is False and "abgelehnt" in abgelehnt["ausgabe"]
    assert aktion_details("plan", {}, {"steps": ["a", "b"]}) == {"message": "2 Schritte"}


def test_rate_limit_unterbricht_und_fahre_fort_macht_mit_gedaechtnis_weiter(tmp_path):
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    kontexte = []
    folge = iter([
        {"tool": "plan", "args": {"steps": ["Seite anlegen", "Stil ergänzen"]}, "step": 1},
        {"tool": "create", "args": {"path": "index.html", "content": "<h1>Hallo</h1>"}, "step": 1},
        RuntimeError("Fehler 429: rate limit exceeded"),
        {"tool": "create", "args": {"path": "stil.css", "content": "h1{color:red}"}, "step": 2},
        {"tool": "finish", "args": {"summary": "Seite und Stil fertig", "incomplete": True}},
    ])

    async def complete(system, user, **kwargs):
        kontexte.append(json.loads(user))
        naechstes = next(folge)
        if isinstance(naechstes, Exception):
            raise naechstes
        return json.dumps(naechstes)

    async def ablauf():
        service = HarnessService(tmp_path / "tasks", complete)
        erster = await fertig(service, service.start("Baue eine Startseite mit Stil", str(projekt)))
        assert erster["status"] == "interrupted" and "fahre fort" in erster["summary"]
        assert [e["tool"] for e in erster["verlauf"]] == ["plan", "create"]
        neu = HarnessService(tmp_path / "tasks", complete)
        assert neu.get(erster["id"])["verlauf"][1]["args"]["path"] == "index.html"
        zweiter = await fertig(neu, neu.start("fahre fort", str(projekt), thread=erster["thread"]))
        assert zweiter["status"] == "needs_review" and zweiter["fortsetzung"]["original_goal"] == "Baue eine Startseite mit Stil"
        assert zweiter["steps"] == ["Seite anlegen", "Stil ergänzen"]
        dritter = neu.start("Erstelle noch eine Kontaktseite", str(projekt), thread=erster["thread"])
        assert "fortsetzung" not in dritter
        await neu.cancel(dritter["id"])

    asyncio.run(ablauf())
    weiter = kontexte[3]
    assert weiter["continue"]["original_goal"] == "Baue eine Startseite mit Stil"
    assert [e["tool"] for e in weiter["recent_actions"]][:2] == ["plan", "create"]
    vorher = weiter["earlier_tasks"][0]
    assert vorher["status"] == "interrupted" and vorher["plan"] == ["Seite anlegen", "Stil ergänzen"]
    assert [e["tool"] for e in vorher["done_actions"]] == ["plan", "create"]
    assert (projekt / "index.html").is_file() and (projekt / "stil.css").is_file()


def test_fortsetzen_erkennt_nur_echte_weiter_befehle():
    from app.services.harness.service import WEITER

    for text in ["fahre fort", "Fahr fort!", "mach bitte weiter", "weiter", "fahre fort danke", "ok mach weiter", "continue"]:
        assert WEITER.fullmatch(text), text
    for text in ["Fahre fort und baue Tests", "weiterleiten der Mail", "Erstelle eine Website", ""]:
        assert not WEITER.fullmatch(text), text


def test_alle_befehle_erlauben_laeuft_ohne_freigabe_ausser_bei_zerstoerenden(tmp_path):
    from app.services.settings_service import get_settings_service

    projekt = tmp_path / "projekt"
    projekt.mkdir()
    harmlos = "Write-Output frei" if os.name == "nt" else "printf frei"
    folge = iter([
        {"tool": "command", "args": {"command": harmlos}},
        {"tool": "command", "args": {"command": "rm -rf ./ordner"}},
        {"tool": "finish", "args": {"summary": "fertig"}},
    ])

    async def complete(system, user, **kwargs):
        return json.dumps(next(folge))

    async def ablauf():
        service = HarnessService(tmp_path / "tasks", complete)
        task = service.start("Baue alles", str(projekt))
        for _ in range(400):
            await asyncio.sleep(0.02)
            pending = service.tasks[task["id"]].get("pending")
            if pending:
                assert "rm -rf" in pending["args"]["command"]
                service.approve(task["id"], pending["id"], False)
                break
        await asyncio.wait_for(service.running[task["id"]], 20)
        return service.get(task["id"])

    get_settings_service().update({"harness_alles_erlauben": True})
    try:
        ergebnis = asyncio.run(ablauf())
    finally:
        get_settings_service().update({"harness_alles_erlauben": False})
    meldungen = [e["message"] for e in ergebnis["log"] if e["type"] == "hinweis"]
    assert any(m.startswith("Automatisch erlaubt") and "frei" in m for m in meldungen)
    assert any("braucht trotz" in m for m in meldungen)
    assert sum(1 for e in ergebnis["log"] if e["type"] == "approval_required") == 1


def test_freigabe_einstellung_ueber_die_schnittstelle(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.harness_routes import router
    from app.services.settings_service import get_settings_service

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    try:
        assert client.get("/api/harness/freigabe").json() == {"alles": False}
        assert client.post("/api/harness/freigabe", json={"alles": True}).json() == {"alles": True}
        assert get_settings_service().get()["harness_alles_erlauben"] is True
        assert client.post("/api/harness/freigabe", json={"alles": False}).json() == {"alles": False}
    finally:
        get_settings_service().update({"harness_alles_erlauben": False})


def test_harness_hat_standardmaessig_kein_schrittlimit(tmp_path):
    from itertools import islice

    from app.providers.openai_compatible import runden

    projekt = tmp_path / "projekt"
    projekt.mkdir()
    (projekt / "a.txt").write_text("a", encoding="utf-8")
    zaehler = {"n": 0}

    async def complete(system, user, **kwargs):
        zaehler["n"] += 1
        if zaehler["n"] > 230:
            return json.dumps({"tool": "finish", "args": {"summary": "nach 230 Schritten fertig"}})
        return json.dumps({"tool": "list", "args": {"path": "."}})

    async def starten(service, **werte):
        task = service.start("Schau dir alles sehr gründlich an", str(projekt), **werte)
        await asyncio.wait_for(service.running[task["id"]], 60)
        return service.get(task["id"])

    ergebnis = asyncio.run(starten(HarnessService(tmp_path / "tasks", complete)))
    assert ergebnis["status"] == "done" and ergebnis["step"] == 231 and "230 Schritten" in ergebnis["summary"]
    assert len(list(islice(runden(True), 5000))) == 5000 and list(runden(False)) == [0]
    zaehler["n"] = 0
    kurz = asyncio.run(starten(HarnessService(tmp_path / "tasks2", complete), max_steps=3))
    assert kurz["status"] == "needs_review" and "Schrittlimit (3)" in kurz["summary"]
