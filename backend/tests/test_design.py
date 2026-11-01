from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import design_service
from app.services.design_service import DesignService
from app.services.settings_service import get_settings_service

client = TestClient(app)


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    ziel = tmp_path / "design"
    monkeypatch.setattr(design_service, "ORDNER", ziel)
    monkeypatch.setattr(design_service, "_service", DesignService())
    return ziel


def test_bild_hochladen_zeigen_und_loeschen(ordner):
    antwort = client.post("/api/design/hintergruende?name=Strand.PNG", content=b"\x89PNG-bild")
    assert antwort.status_code == 200
    eintrag = antwort.json()
    assert eintrag["art"] == "bild"
    assert eintrag["groesse"] == 9
    assert eintrag["name"].endswith(".png")
    assert (ordner / eintrag["name"]).is_file()

    liste = client.get("/api/design/hintergruende").json()["eintraege"]
    assert [e["name"] for e in liste] == [eintrag["name"]]

    datei = client.get(f"/api/design/hintergruende/{eintrag['name']}")
    assert datei.status_code == 200
    assert datei.headers["content-type"] == "image/png"
    assert datei.content == b"\x89PNG-bild"

    assert client.delete(f"/api/design/hintergruende/{eintrag['name']}").json() == {"geloescht": True}
    assert client.get("/api/design/hintergruende").json()["eintraege"] == []


def test_video_wird_in_stuecken_geliefert(ordner):
    inhalt = bytes(range(256)) * 40
    eintrag = client.post("/api/design/hintergruende?name=meer.mp4", content=inhalt).json()
    assert eintrag["art"] == "video"
    teil = client.get(f"/api/design/hintergruende/{eintrag['name']}", headers={"Range": "bytes=100-199"})
    assert teil.status_code == 206
    assert teil.content == inhalt[100:200]


def test_fremde_und_leere_dateien_werden_abgelehnt(ordner):
    assert client.post("/api/design/hintergruende?name=virus.exe", content=b"MZ").status_code == 400
    assert client.post("/api/design/hintergruende?name=leer.jpg", content=b"").status_code == 400
    assert not ordner.exists() or list(ordner.iterdir()) == []


def test_kein_ausbruch_aus_dem_ordner(ordner, tmp_path):
    (tmp_path / "geheim.png").write_bytes(b"x")
    assert client.get("/api/design/hintergruende/..%2Fgeheim.png").status_code == 404
    assert client.get("/api/design/hintergruende/geheim.png").status_code == 404
    assert client.delete("/api/design/hintergruende/geheim.png").status_code == 404


def test_design_wird_in_den_einstellungen_gemerkt():
    design = {"akzent": "#3b82f6", "wallpaper": {"art": "live", "live": "aurora"}}
    antwort = client.put("/api/settings", json={"design": design})
    assert antwort.status_code == 200
    assert get_settings_service().get()["design"] == design
    assert client.get("/api/settings").json()["design"] == design
    get_settings_service().update({"design": {}})


def test_eigene_designs_bleiben_gespeichert():
    liste = [{"id": "d-abc12", "name": "Mein Rosa", "werte": {"akzent": "#ff4d8d", "herzen": True}, "zeit": 1}]
    assert client.put("/api/settings", json={"design_liste": liste}).status_code == 200
    assert client.get("/api/settings").json()["design_liste"] == liste
    assert client.put("/api/settings", json={"design_liste": "kaputt"}).status_code == 422
    assert client.get("/api/settings").json()["design_liste"] == liste
    get_settings_service().update({"design_liste": []})
