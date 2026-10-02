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
        assert result["id"] not in service.runs
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
