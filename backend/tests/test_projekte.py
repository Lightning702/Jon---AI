from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services import project_service
from app.services.project_service import (
    ProjectError,
    analyze,
    changes,
    context_block,
    get_project_service,
    git_status,
    snapshot,
)
from app.services.tools import CODING_TOOLS, ToolBox

client = TestClient(app)


@pytest.fixture()
def projekt(tmp_path: Path) -> Path:
    root = tmp_path / "ECHO"
    (root / "src").mkdir(parents=True)
    (root / "node_modules" / "krempel").mkdir(parents=True)
    (root / "node_modules" / "krempel" / "index.js").write_text("nein", encoding="utf-8")
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "echo",
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"vite": "^6.0.0"},
                "scripts": {"build": "vite build", "test": "vitest"},
            }
        ),
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("fastapi>=0.110\npydantic\n", encoding="utf-8")
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "src" / "App.tsx").write_text("export default function App() {}", encoding="utf-8")
    return root


def test_ordner_wird_als_ganzes_projekt_verstanden(projekt: Path):
    data = analyze(str(projekt))
    assert data["name"] == "ECHO"
    assert data["dateien"] == 4
    assert "package.json (Node/JS)" in data["projekttyp"]
    assert "React" in data["frameworks"]
    assert "Vite" in data["frameworks"]
    assert "FastAPI" in data["frameworks"]
    assert data["skripte"]["build"] == "vite build"
    assert "index.html" in data["schluesseldateien"]
    assert "src/App.tsx" in data["schluesseldateien"]
    assert any(s["name"] == "TypeScript React" for s in data["sprachen"])


def test_analyse_ignoriert_abhaengigkeitsordner(projekt: Path):
    data = analyze(str(projekt))
    assert data["ordner"] == 1


def test_analyse_meldet_fehlenden_ordner():
    with pytest.raises(ProjectError):
        analyze(str(Path("C:/gibt-es-nicht-12345")))


def test_kontextblock_beschreibt_projekt(projekt: Path):
    text = context_block(str(projekt))
    assert "Projektanalyse" in text
    assert "React" in text
    assert "vite build" in text


def test_aenderungen_werden_gezaehlt(projekt: Path):
    vorher = snapshot(str(projekt))
    (projekt / "src" / "neu.ts").write_text("export const a = 1;", encoding="utf-8")
    (projekt / "index.html").write_text("<html><body>hi</body></html>", encoding="utf-8")
    (projekt / "requirements.txt").unlink()
    ergebnis = changes(str(projekt), vorher)
    assert ergebnis["anzahl"]["erstellt"] == 1
    assert ergebnis["anzahl"]["geloescht"] == 1
    assert "index.html" in ergebnis["geaendert"]


def test_git_status_ohne_repository(projekt: Path):
    data = git_status(str(projekt))
    assert data["repo"] is False


def test_projekt_registrierung_und_gedaechtnis(projekt: Path):
    service = get_project_service()
    entry = service.add(str(projekt), note="Login-System fehlt noch")
    assert entry["root"] == str(projekt.resolve())
    zweimal = service.add(str(projekt))
    assert zweimal["id"] == entry["id"]
    service.remember(entry["id"], "Baut mit vite build")
    block = service.memory_block(entry["id"])
    assert "Baut mit vite build" in block
    assert service.find_by_root(str(projekt))["id"] == entry["id"]
    assert any(p["id"] == entry["id"] for p in service.search("ECHO"))
    assert service.delete(entry["id"]) is True


def test_projekt_api_legt_an_analysiert_und_loescht(projekt: Path):
    angelegt = client.post("/api/projects", json={"root": str(projekt)})
    assert angelegt.status_code == 200
    projekt_id = angelegt.json()["id"]

    liste = client.get("/api/projects")
    assert any(p["id"] == projekt_id for p in liste.json())

    analyse = client.get("/api/projects/analyze", params={"root": str(projekt)})
    assert analyse.status_code == 200
    assert analyse.json()["name"] == "ECHO"

    notiz = client.post(
        f"/api/projects/{projekt_id}/note", json={"note": "Tests laufen mit vitest"}
    )
    assert "Tests laufen mit vitest" in notiz.json()["notizen"]

    stand = client.post("/api/projects/snapshot", json={"root": str(projekt)})
    (projekt / "src" / "extra.ts").write_text("export const b = 2;", encoding="utf-8")
    diff = client.post(
        "/api/projects/changes",
        json={"root": str(projekt), "snapshot": stand.json()},
    )
    assert diff.json()["anzahl"]["erstellt"] == 1

    git = client.get("/api/projects/git", params={"root": str(projekt), "mode": "diff"})
    assert git.status_code == 200
    assert git.json()["repo"] is False

    assert client.delete(f"/api/projects/{projekt_id}").json()["geloescht"] is True


def test_api_lehnt_unbekannten_ordner_ab():
    antwort = client.get(
        "/api/projects/analyze", params={"root": "C:/gibt-es-nicht-98765"}
    )
    assert antwort.status_code == 400


def test_coding_agent_kennt_projektwerkzeuge(projekt: Path):
    assert {"project_overview", "git_status", "git_diff"} <= CODING_TOOLS
    box = ToolBox(root=str(projekt))
    namen = {tool["function"]["name"] for tool in box.schema(coding=True)}
    assert {"project_overview", "git_status", "git_diff"} <= namen
    ergebnis = json.loads(box._execute("project_overview", {}))
    assert ergebnis["name"] == "ECHO"


def test_projektwerkzeug_bleibt_im_ordner(projekt: Path, tmp_path: Path):
    fremd = tmp_path / "privat"
    fremd.mkdir()
    box = ToolBox(root=str(projekt))
    ergebnis = json.loads(box._execute("project_overview", {"root": str(fremd)}))
    assert "error" in ergebnis


def test_service_modul_bleibt_ohne_zweite_datenbank():
    assert project_service.PROJECTS_FILE.name == "projects.json"
