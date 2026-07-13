from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    from app.core.config import get_settings

    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["default_provider"] == "nvidia"
    assert body["default_model"] == get_settings().jon_model
    assert body["default_model"] == "meta/llama-3.1-70b-instruct"


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
        if account["auth"] == "api_key":
            assert account["plan"] == "Über die offizielle API nicht verfügbar"


def test_approve_unknown():
    res = client.post("/api/chat/approve", json={"id": "nope", "approved": True})
    assert res.status_code == 200
    assert res.json()["status"] == "unknown"


def test_settings_roundtrip():
    res = client.put(
        "/api/settings", json={"custom_prompt": "Sei knapp.", "prompt_mode": "append"}
    )
    assert res.status_code == 200
    assert res.json()["custom_prompt"] == "Sei knapp."
    client.put("/api/settings", json={"custom_prompt": ""})


def test_reminders_flow():
    created = client.post(
        "/api/reminders", json={"text": "Trinken", "time": "13:00", "repeat": "daily"}
    ).json()
    assert created["id"]
    assert any(r["id"] == created["id"] for r in client.get("/api/reminders").json())
    assert client.delete(f"/api/reminders/{created['id']}").json()["deleted"] is True


def test_accounts_include_local_and_new():
    providers = {a["provider"]: a for a in client.get("/api/accounts").json()}
    assert {"openrouter", "groq", "together", "xai", "ollama", "lmstudio"} <= set(providers)
    assert providers["ollama"]["auth"] == "local"


def test_game_skill_present():
    res = client.get("/api/skills/game-design")
    assert res.status_code == 200
    assert "requestAnimationFrame" in res.json()["content"]


def test_edit_and_game_tools_registered():
    from app.services.tools import ToolBox

    names = {t["function"]["name"] for t in ToolBox().schema()}
    assert {"edit_file", "set_reminder", "list_reminders"} <= names
