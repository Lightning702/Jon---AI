from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.services import netlify_service as nsvc
from app.services.settings_service import get_settings_service

client = TestClient(app)


class _Resp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data
        self.text = json.dumps(data)

    def json(self):
        return self._data


class _FakeClient:
    user_status = 200
    deploy_state = "ready"

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None):
        if url.endswith("/user"):
            return _Resp(
                _FakeClient.user_status,
                {"email": "felix@test.de", "full_name": "Felix"},
            )
        if "/sites" in url:
            return _Resp(
                200,
                [
                    {"id": "site-1", "name": "jon-ki", "ssl_url": "https://jon-ki.netlify.app"},
                    {"id": "site-2", "name": "andere", "url": "http://andere.netlify.app"},
                ],
            )
        if "/deploys/" in url:
            return _Resp(
                200,
                {
                    "id": "dep-1",
                    "state": _FakeClient.deploy_state,
                    "ssl_url": "https://jon-ki.netlify.app",
                },
            )
        return _Resp(404, {})

    async def post(self, url, headers=None, content=None):
        _FakeClient.last_content = content
        return _Resp(
            200,
            {
                "id": "dep-1",
                "state": _FakeClient.deploy_state,
                "ssl_url": "https://jon-ki.netlify.app",
                "deploy_ssl_url": "https://dep-1--jon-ki.netlify.app",
            },
        )


def _reset():
    get_settings_service().update(
        {
            "netlify_token": "",
            "netlify_site_id": "",
            "netlify_site_name": "",
            "netlify_site_url": "",
        }
    )


def test_veroeffentlichen_seite_wird_ausgeliefert():
    for pfad in ("/veroeffentlichen", "/publish"):
        res = client.get(pfad)
        assert res.status_code == 200
        assert "Jon-Ordner" in res.text
        assert "/api/netlify/" in res.text


def test_netlify_routen_registriert():
    paths = set(app.openapi()["paths"])
    for p in (
        "/api/netlify/status",
        "/api/netlify/token",
        "/api/netlify/sites",
        "/api/netlify/site",
        "/api/netlify/deploy",
    ):
        assert p in paths


def test_status_ohne_token(monkeypatch):
    _reset()
    res = client.get("/api/netlify/status")
    assert res.status_code == 200
    data = res.json()
    assert data["token_set"] is False
    assert data["site_id"] == ""


def test_token_setzen_und_trennen(monkeypatch):
    _reset()
    monkeypatch.setattr(nsvc.httpx, "AsyncClient", _FakeClient)
    res = client.post("/api/netlify/token", json={"token": "tok-123"})
    assert res.status_code == 200
    assert res.json()["token_set"] is True
    assert res.json()["email"] == "felix@test.de"
    assert client.get("/api/netlify/status").json()["token_set"] is True
    res = client.post("/api/netlify/token", json={"token": ""})
    assert res.json()["token_set"] is False
    assert client.get("/api/netlify/status").json()["token_set"] is False


def test_ungueltiger_token(monkeypatch):
    _reset()
    monkeypatch.setattr(nsvc.httpx, "AsyncClient", _FakeClient)
    _FakeClient.user_status = 401
    res = client.post("/api/netlify/token", json={"token": "kaputt"})
    _FakeClient.user_status = 200
    assert res.status_code == 400
    assert client.get("/api/netlify/status").json()["token_set"] is False


def test_sites_und_auswahl(monkeypatch):
    _reset()
    monkeypatch.setattr(nsvc.httpx, "AsyncClient", _FakeClient)
    client.post("/api/netlify/token", json={"token": "tok-123"})
    res = client.get("/api/netlify/sites")
    assert res.status_code == 200
    sites = res.json()
    assert sites[0]["id"] == "site-1"
    assert sites[0]["url"] == "https://jon-ki.netlify.app"
    res = client.post(
        "/api/netlify/site",
        json={"site_id": "site-1", "name": "jon-ki", "url": "https://jon-ki.netlify.app"},
    )
    assert res.status_code == 200
    assert res.json()["site_id"] == "site-1"


def test_deploy(monkeypatch):
    _reset()
    monkeypatch.setattr(nsvc.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(nsvc, "_jon_zip_bauen", lambda: 7)
    monkeypatch.setattr(nsvc, "_website_zip", lambda: b"PK-fake-zip")
    client.post("/api/netlify/token", json={"token": "tok-123"})
    client.post("/api/netlify/site", json={"site_id": "site-1", "name": "jon-ki"})
    res = client.post("/api/netlify/deploy")
    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "ready"
    assert data["url"] == "https://jon-ki.netlify.app"
    assert data["jon_zip_dateien"] == 7
    assert _FakeClient.last_content == b"PK-fake-zip"


def test_deploy_ohne_setup():
    _reset()
    res = client.post("/api/netlify/deploy")
    assert res.status_code == 400
