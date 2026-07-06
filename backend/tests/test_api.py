from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["default_provider"] == "nvidia"
    assert body["default_model"] == "openai/gpt-oss-120b"


def test_providers():
    res = client.get("/api/providers")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_conversations_list():
    res = client.get("/api/conversations")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_transcribe_empty():
    res = client.post("/api/system/transcribe", content=b"")
    assert res.status_code == 400


def test_skills_roundtrip():
    res = client.put("/api/skills/test-skill", json={"content": "# Test\nHallo"})
    assert res.status_code == 200
    listing = client.get("/api/skills").json()
    assert any(s["name"] == "test-skill" for s in listing)
    read = client.get("/api/skills/test-skill").json()
    assert "Hallo" in read["content"]
    assert client.delete("/api/skills/test-skill").json()["deleted"] is True


def test_web_design_skill_present():
    res = client.get("/api/skills/web-design")
    assert res.status_code == 200
    assert "Design-Tokens" in res.json()["content"]


def test_usage_shape():
    res = client.get("/api/usage")
    assert res.status_code == 200
    assert "usage" in res.json()


def test_accounts_list():
    res = client.get("/api/accounts")
    assert res.status_code == 200
    body = res.json()
    providers = {a["provider"] for a in body}
    assert {"openai", "anthropic"} <= providers
    for account in body:
        assert account["plan"] == "Über die offizielle API nicht verfügbar"


def test_approve_unknown():
    res = client.post("/api/chat/approve", json={"id": "nope", "approved": True})
    assert res.status_code == 200
    assert res.json()["status"] == "unknown"
