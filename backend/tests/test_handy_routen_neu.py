from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mein_bericht_nur_fuer_handys():
    antwort = client.get("/api/handy/mein-bericht")
    assert antwort.status_code == 404
    assert "gekoppelte Handys" in antwort.json()["detail"]


def test_bericht_fuer_unbekanntes_geraet():
    assert client.get("/api/handy/devices/gibt-es-nicht/bericht").status_code == 404


def test_zeitanfrage_fuer_unbekanntes_geraet():
    antwort = client.post("/api/handy/devices/gibt-es-nicht/zeitanfragen/abc", json={"erlaubt": True, "minuten": 30})
    assert antwort.status_code == 400
    assert "Unbekanntes" in antwort.json()["detail"]
