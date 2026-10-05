import asyncio
import json
import os

import httpx
import pytest
from fastapi import FastAPI

from app.api.agenten_routes import router
from app.core.auth import TokenMiddleware
from app.services.agenten_service import AgentenService


def model_for(calls, failure=""):
    async def model(system, user, **kwargs):
        data = json.loads(user)
        calls.append((data, kwargs))
        if "profile" in data:
            if failure == "plan":
                return "kein JSON"
            return json.dumps({"teile": [
                {"titel": "Formen", "auftrag": "Prüfe puellam", "rolle": "latin", "werkzeug": "web_search"},
                {"titel": "Übersetzung", "auftrag": "Übersetze legere", "rolle": "latin", "werkzeug": "browser_task"},
            ]})
        if "teilauftrag" in data:
            if failure == "part" and "legere" in data["teilauftrag"]:
                raise RuntimeError("Modell nicht erreichbar")
            await asyncio.sleep(.01)
            return "puellam ist der Subjektsakkusativ des AcI. legere heißt lesen."
        if "mini" in data:
            if failure == "summary":
                raise RuntimeError("Koordinator ausgefallen")
            return "Marcus sagt, dass das Mädchen liest."
        if failure == "review":
            return '{"ok":"true"}'
        return json.dumps({"ok": failure != "contradiction", "probleme": ["Widerspruch"] if failure == "contradiction" else [], "korrektur": ""})
    return model


def test_team_uses_original_context_minijon_slot_and_persists(tmp_path, monkeypatch):
    from app.services.tools import ToolBox
    async def blocked(*args, **kwargs):
        pytest.fail("Recherche ohne Freigabe")
    monkeypatch.setattr(ToolBox, "execute", blocked)
    calls = []
    service = AgentenService(tmp_path, model_for(calls))
    async def run():
        result = await service.bearbeiten("Marcus dicit puellam legere.", 2, slot="emil", source="minijon")
        assert result["status"] == "done"
        assert result["vollstaendig"]
        assert len(result["teile"]) == 2
        assert all(item["werkzeug"] == "keins" for item in result["teile"])
        assert all(kwargs["slot"] == "emil" for _, kwargs in calls)
        assert all(data["urspruenglicher_auftrag"] == result["aufgabe"] for data, _ in calls if "teilauftrag" in data)
        assert AgentenService(tmp_path).get(result["id"])["antwort"] == result["antwort"]
    asyncio.run(run())


@pytest.mark.parametrize("failure", ["part", "summary", "review", "contradiction"])
def test_partial_errors_never_report_completion(tmp_path, failure):
    service = AgentenService(tmp_path, model_for([], failure))
    result = asyncio.run(service.bearbeiten("Prüfe diesen Satz"))
    assert result["status"] == "needs_review"
    assert not result["vollstaendig"]
    assert result["ok"]
    assert result["antwort"]
    if failure == "summary":
        assert "Koordinator" in result["fehler"]
        assert "Subjektsakkusativ" in result["antwort"]


def test_bad_plan_falls_back_to_original_task(tmp_path):
    result = asyncio.run(AgentenService(tmp_path, model_for([], "plan")).bearbeiten("Prüfe den Originalsatz", roles=["latin"]))
    assert result["status"] == "done"
    assert len(result["teile"]) == 1
    assert result["teile"][0]["auftrag"] == "Prüfe den Originalsatz"
    assert result["hinweis"]


def test_cancel_stops_children_and_keeps_finished_parts(tmp_path):
    cancelled = []
    async def model(system, user, **kwargs):
        data = json.loads(user)
        if "profile" in data:
            return '{"teile":[{"auftrag":"schnell"},{"auftrag":"langsam"}]}'
        if data.get("teilauftrag") == "schnell":
            return "Bereits vorhandenes Ergebnis"
        try:
            await asyncio.sleep(100)
        finally:
            cancelled.append(True)
    service = AgentenService(tmp_path, model)
    async def run():
        task = service.start("Prüfe zwei Dinge")
        async with asyncio.timeout(5):
            while not any(p["status"] == "done" for p in service.get(task["id"])["teile"]):
                await asyncio.sleep(.01)
        result = await service.cancel(task["id"])
        assert result["status"] == "cancelled"
        assert result["teile"][0]["ergebnis"] == "Bereits vorhandenes Ergebnis"
        assert result["teile"][1]["status"] == "cancelled"
        assert cancelled == [True]
    asyncio.run(run())


def test_limit_cancel_before_start_and_private_run(tmp_path):
    service = AgentenService(tmp_path, model_for([]))
    async def run():
        first = service.start("Eins")
        second = service.start("Zwei")
        with pytest.raises(ValueError, match="bereits"):
            service.start("Drei")
        await service.cancel(first["id"])
        await service.cancel(second["id"])
        assert service.get(first["id"])["status"] == "cancelled"
        result = await service.bearbeiten("Privat", persist=False)
        assert result["status"] == "done"
        assert not (tmp_path / (result["id"] + ".json")).exists()
        assert result["id"] not in [item["id"] for item in service.list()]
        assert service.get(result["id"])["status"] == "done"
    asyncio.run(run())


def test_preassigned_run_id_and_live_view(tmp_path):
    service = AgentenService(tmp_path, model_for([]))
    key = "b" * 32
    async def run():
        started = service.start("Latein prüfen", run_id=key)
        assert started["id"] == key
        assert any(item["id"] == key for item in service.live())
        await service.running[key]
        assert service.get(key)["teile"][0]["rolle_name"] == "Latein"
        assert service.start("Noch einmal", run_id=key)["id"] != key
        assert service.start("Ungültig", run_id="../etc")["id"] != "../etc"
    asyncio.run(run())


def test_restart_marks_unfinished_and_does_not_resume(tmp_path):
    key = "a" * 32
    (tmp_path / (key + ".json")).write_text(json.dumps({"id": key, "status": "working", "teile": [{"status": "working"}]}))
    service = AgentenService(tmp_path)
    assert service.get(key)["status"] == "interrupted"
    assert not service.running


def test_timeout_finishes_and_is_not_success(tmp_path, monkeypatch):
    from app.services import agenten_service
    monkeypatch.setattr(agenten_service, "GESAMT_TIMEOUT_S", .02)
    async def model(*args, **kwargs):
        await asyncio.sleep(100)
    result = asyncio.run(AgentenService(tmp_path, model).bearbeiten("Zeitlimit"))
    assert result["status"] == "failed"
    assert not result["vollstaendig"]
    assert result["fehler"] == "Zeitlimit erreicht."


def test_api_auth_validation_and_results(tmp_path, monkeypatch):
    from app.services import agenten_service
    service = AgentenService(tmp_path, model_for([]))
    monkeypatch.setattr(agenten_service, "_service", service)
    app = FastAPI()
    app.add_middleware(TokenMiddleware)
    app.include_router(router)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            assert (await client.get("/api/agents/runs")).status_code == 401
            client.headers["X-Jon-Token"] = os.environ["JON_TOKEN"]
            assert (await client.post("/api/agents/runs", json={"aufgabe": "Prüfen", "roles": ["invented"]})).status_code == 400
            response = await client.post("/api/agents/runs", json={"aufgabe": "Latein prüfen", "source": "minijon"})
            assert response.status_code == 200
            key = response.json()["id"]
            if key in service.running:
                await service.running[key]
            result = (await client.get("/api/agents/runs/" + key)).json()
            assert result["slot"] == "emil"
            assert result["status"] == "done"
            assert len((await client.get("/api/agents/runs?brief=true")).json()) == 1
            assert (await client.delete("/api/agents/runs/" + key)).status_code == 200
            assert (await client.get("/api/agents/runs/" + key)).status_code == 404
    asyncio.run(run())


@pytest.mark.parametrize("ankuendigung_zuerst", [True, False])
def test_chat_shows_live_card_with_the_run_id_the_team_uses(monkeypatch, ankuendigung_zuerst):
    from app.providers.base import StreamChunk
    from app.providers.registry import get_registry
    from app.schemas import ChatIn, MessageIn
    from app.services.chat_service import ChatService
    from app.services.tools import ToolBox

    genutzt = []

    async def ausfuehren(self, name, args, source=None):
        genutzt.append(args.get("_lauf"))
        return json.dumps({"id": args.get("_lauf"), "status": "done", "antwort": "Fertig"})

    class Anbieter:
        name = "openai"

        def available(self):
            return True

        async def list_models(self):
            return ["modell"]

        async def stream(self, request, tool_executor=None):
            args = {"aufgabe": "Prüfe den Satz aus zwei Perspektiven"}
            if ankuendigung_zuerst:
                yield StreamChunk(kind="tool", name="team", args=args)
                ergebnis = await tool_executor("team", args)
            else:
                ergebnis = await tool_executor("team", args)
                yield StreamChunk(kind="tool", name="team", args=args)
            yield StreamChunk(kind="tool_result", name="team", ok=True, result=ergebnis)
            yield StreamChunk(delta="Das Fachteam ist fertig.", kind="content")

    registry = get_registry()
    monkeypatch.setattr(registry, "get", lambda name: Anbieter(), raising=False)
    monkeypatch.setattr("app.services.chat_service.get_registry", lambda: registry, raising=False)
    monkeypatch.setattr(ToolBox, "execute", ausfuehren)

    async def sammeln():
        payload = ChatIn(messages=[MessageIn(role="user", content="Lass dein Fachteam den Satz prüfen")], persist=False, provider="openai", model="modell", tool_mode="ask")
        return [event async for event in ChatService().stream(payload)]

    events = asyncio.run(sammeln())
    karten = [e["card"] for e in events if e.get("type") == "tool" and e.get("card")]
    assert len(karten) == 1
    assert karten[0]["kind"] == "agenten"
    assert genutzt == [karten[0]["data"]["id"]]
    assert not any(e.get("approval_id") for e in events if e.get("type") == "tool")


def vokabel_modell(calls, teile=1):
    liste = "\n".join(f"{i}. vocabulum{i} – Wort {i}" for i in range(1, 801))

    async def model(system, user, **kwargs):
        data = json.loads(user)
        calls.append((system, data, kwargs))
        if "profile" in data:
            return json.dumps({"teile": [{"titel": f"Vokabeln {n}", "auftrag": "Schreib alle Vokabeln aus dem Material heraus", "rolle": "latin", "werkzeug": "keins"} for n in range(teile)]})
        if "teilauftrag" in data:
            return liste if "vocabulum" in data["material"] else "Kein Material bekommen."
        if "mini" in data:
            return "kurz zusammengefasst"
        return json.dumps({"ok": True, "probleme": [], "korrektur": ""})

    return model, liste


def test_agenten_bekommen_das_material_und_liefern_lange_listen_vollstaendig(tmp_path):
    calls = []
    model, liste = vokabel_modell(calls)
    service = AgentenService(tmp_path, model)
    material = "Nutzer:\nHier mein Text: " + " ".join(f"vocabulum{i}" for i in range(1, 801))
    result = asyncio.run(service.bearbeiten("Schreib mir alle Vokabeln raus", 3, material=material))
    assert result["status"] == "done" and result["vollstaendig"]
    assert result["antwort"] == liste and len(result["antwort"]) > 14000
    teil = next((s, d, k) for s, d, k in calls if "teilauftrag" in d)
    assert "vocabulum800" in teil[1]["material"] and teil[2]["max_tokens"] >= 8000 and "vollständige Liste" in teil[0]
    assert not any("mini" in d for _, d, _ in calls)
    datei = tmp_path / "ergebnisse" / os.path.basename(result["datei"])
    assert datei.is_file() and "800. vocabulum800" in datei.read_text(encoding="utf-8")
    assert datei.name.endswith("Schreib mir alle Vokabeln raus.md")


def test_lange_teilergebnisse_werden_nicht_weggefasst_und_private_laeufe_nicht_gespeichert(tmp_path):
    calls = []
    model, liste = vokabel_modell(calls, teile=2)
    service = AgentenService(tmp_path, model)
    result = asyncio.run(service.bearbeiten("Alle Vokabeln", 2, material="vocabulum1", persist=False))
    assert liste in result["antwort"] and result["antwort"].count("## Vokabeln") == 2
    assert not any("mini" in d for _, d, _ in calls)
    assert not result.get("datei") and not (tmp_path / "ergebnisse").exists()


def test_agenten_ordner_laesst_sich_einstellen_und_zuruecksetzen(tmp_path):
    from app.services.settings_service import get_settings_service

    calls = []
    model, _ = vokabel_modell(calls)
    service = AgentenService(tmp_path, model)
    try:
        assert service.ordner_stand()["pfad"] == str(tmp_path / "ergebnisse") and not service.ordner_stand()["eigener"]
        eigen = tmp_path / "Meine Agenten"
        stand = service.ordner_setzen(str(eigen))
        assert stand["eigener"] and stand["vorhanden"] and stand["pfad"] == str(eigen.resolve())
        result = asyncio.run(service.bearbeiten("Vokabeln", 1, material="vocabulum1"))
        assert result["datei"].startswith(str(eigen.resolve())) and os.path.isfile(result["datei"])
        with pytest.raises(ValueError, match="vollständigen"):
            service.ordner_setzen("relativ/ordner")
        assert not service.ordner_setzen("")["eigener"]
    finally:
        get_settings_service().update({"agenten_ordner": ""})


def test_team_werkzeug_gibt_jon_die_antwort_kompakt_und_mit_material_zurueck(monkeypatch):
    from app.services import agenten_service
    from app.services.werkzeuge_kern import _team

    erhalten = {}

    class Dienst:
        async def bearbeiten(self, aufgabe, agenten, **kwargs):
            erhalten.update(kwargs, aufgabe=aufgabe)
            return {"status": "done", "vollstaendig": True, "antwort": "x" * 20000, "datei": "C:/Agenten/a.md", "teile": [{"titel": "A", "status": "done", "ergebnis": "y" * 30000}], "pruefung": {"ok": True, "probleme": []}, "fehler": "", "hinweis": ""}

    monkeypatch.setattr(agenten_service, "get_agenten_service", lambda: Dienst())

    class Box:
        _source = "app"
        _slot = "jon"
        _persist = True
        _material = "Nutzer:\nvocabulum"

    daten = json.loads(asyncio.run(_team(Box(), {"aufgabe": "Alle Vokabeln"})))
    inhalt = daten.get("data", daten)
    assert erhalten["material"] == "Nutzer:\nvocabulum" and erhalten["aufgabe"] == "Alle Vokabeln"
    assert inhalt["antwort_zeichen"] == 20000 and len(inhalt["antwort"]) <= 6000
    assert inhalt["gespeichert_in"] == "C:/Agenten/a.md" and "Fachteam-Karte" in inhalt["anweisung"]
    assert "y" * 100 not in json.dumps(inhalt)


def test_material_aus_dem_chatverlauf():
    from app.schemas import MessageIn
    from app.services.chat_service import material_aus_verlauf

    nachrichten = [MessageIn(role="user", content="Alt"), MessageIn(role="assistant", content="Antwort"), MessageIn(role="user", content="Schreib alle Vokabeln raus\n\nDatei: liste.txt\n" + "a" * 70000)]
    text = material_aus_verlauf(nachrichten)
    assert text.startswith("Nutzer:\nSchreib alle Vokabeln raus") and len(text) <= 60020
    kurz = material_aus_verlauf(nachrichten[:2])
    assert kurz == "Nutzer:\nAlt\n\nJon:\nAntwort"
