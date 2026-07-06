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
