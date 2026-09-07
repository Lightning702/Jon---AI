from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services.calendar_service import get_calendar_service
from app.services.knowledge_service import get_knowledge_service
from app.services.memory_service import MemoryService
from app.services.notes_service import get_notes_service
from app.services.project_service import get_project_service
from app.services.search_service import universal_search

client = TestClient(app)


@pytest.fixture()
def login_projekt(tmp_path: Path):
    root = tmp_path / "LoginManager"
    (root / "auth").mkdir(parents=True)
    (root / "auth" / "login.ts").write_text(
        "export function login(user: string) { return user; }", encoding="utf-8"
    )
    (root / "README.md").write_text("Wetterkarte fuer Segelflieger", encoding="utf-8")
    service = get_project_service()
    entry = service.add(str(root), name="LoginManager", note="Google Login fehlt noch")
    yield entry
    service.delete(entry["id"])


def _groups(query: str) -> dict[str, list]:
    return {g["kind"]: g["items"] for g in universal_search(query)["groups"]}


def test_kurze_anfrage_liefert_nichts():
    assert universal_search("a") == {"groups": []}


def test_projekt_und_dateien_werden_gefunden(login_projekt):
    groups = _groups("login")
    assert any(item["title"] == "LoginManager" for item in groups.get("projekt", []))
    treffer = groups.get("datei", [])
    assert any("login.ts" in item["title"] for item in treffer)
    assert all(item.get("path") for item in treffer)


def test_dateiinhalt_wird_durchsucht(login_projekt):
    groups = _groups("Segelflieger")
    assert any("README.md" in item["title"] for item in groups.get("datei", []))


def test_nur_freigegebene_ordner_werden_durchsucht(tmp_path: Path, login_projekt):
    privat = tmp_path / "privat"
    privat.mkdir()
    (privat / "geheim.txt").write_text("login geheimnis", encoding="utf-8")
    treffer = _groups("geheimnis").get("datei", [])
    assert not any("geheim.txt" in item["title"] for item in treffer)


def test_notizen_termine_und_wissen_werden_gefunden():
    notiz = get_notes_service().add("Login Ideen fuer Jon")
    tag = (date.today() + timedelta(days=2)).isoformat()
    termin = get_calendar_service().add("Login-Review", tag, "09:00")
    MemoryService().add("Der Nutzer nennt sein Login-System Echo")
    get_knowledge_service().learn_text("Login erfolgt ueber OAuth", "Login Doku")
    try:
        groups = _groups("login")
        assert any("Login Ideen" in item["title"] for item in groups.get("notiz", []))
        assert any(item["title"] == "Login-Review" for item in groups.get("termin", []))
        assert groups.get("memory")
        assert groups.get("knowledge")
    finally:
        get_notes_service().delete(notiz["id"])
        get_calendar_service().delete(termin["id"])


def test_api_liefert_gruppen(login_projekt):
    antwort = client.post("/api/search", json={"query": "login"})
    assert antwort.status_code == 200
    kinds = {g["kind"] for g in antwort.json()["groups"]}
    assert "projekt" in kinds
    assert "datei" in kinds
