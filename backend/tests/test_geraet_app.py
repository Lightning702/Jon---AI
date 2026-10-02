from __future__ import annotations

import base64
import sys

from fastapi.testclient import TestClient

import app.services.geraet_app_service as modul
from app.main import app
from app.services.geraet_app_service import GeraetAppService


def _dienst(monkeypatch, tmp_path) -> GeraetAppService:
    monkeypatch.setattr(modul, "ORDNER", tmp_path / "geraet-app")
    monkeypatch.setattr(modul, "TEIL", 10)
    dienst = GeraetAppService()
    monkeypatch.setattr(modul, "_dienst", dienst)
    return dienst


def test_ohne_app_nichts_verfuegbar(monkeypatch, tmp_path):
    _dienst(monkeypatch, tmp_path)
    client = TestClient(app)
    assert client.get("/api/handy/app").json() == {"verfuegbar": False}
    assert client.get("/geraet.apk").status_code == 404
    assert client.get("/api/handy/app/teil").status_code == 404
    assert "noch keine App" in client.get("/geraet").text


def test_app_ablegen_und_in_teilen_laden(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    quelle = tmp_path / "neu.apk"
    inhalt = b"PK" + bytes(range(40))
    quelle.write_bytes(inhalt)
    info = dienst.ablegen(quelle, "1.4.1", 5)
    assert info["verfuegbar"] and info["version"] == "1.4.1" and info["code"] == 5 and info["groesse"] == len(inhalt)
    assert len(info["sha256"]) == 64
    client = TestClient(app)
    geladen = b""
    offset = 0
    while True:
        teil = client.get(f"/api/handy/app/teil?offset={offset}").json()
        geladen += base64.b64decode(teil["data"])
        if teil["offset"] >= teil["size"]:
            break
        offset = teil["offset"]
    assert geladen == inhalt
    antwort = client.get("/geraet.apk")
    assert antwort.status_code == 200 and antwort.content == inhalt
    assert "1.4.1 laden" in client.get("/geraet").text


def test_alte_versionen_werden_ersetzt(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    quelle = tmp_path / "a.apk"
    quelle.write_bytes(b"alt")
    dienst.ablegen(quelle, "1.4.1", 5)
    quelle.write_bytes(b"neu")
    dienst.ablegen(quelle, "1.4.2", 6)
    namen = sorted(p.name for p in (tmp_path / "geraet-app").glob("*.apk"))
    assert namen == ["Jon-Geraet-1.4.2.apk"]


def test_heimnetz_schalter(monkeypatch, tmp_path):
    _dienst(monkeypatch, tmp_path)
    from app.core import heimnetz
    from app.services.settings_service import get_settings_service

    client = TestClient(app)
    vorher = get_settings_service().get().get("heimnetz")
    try:
        antwort = client.post("/api/system/heimnetz", json={"an": True}).json()
        assert antwort["an"] is True and antwort["neustart"] is True
        assert heimnetz.lan_aktiv() is True
        adressen = client.get("/api/handy/app/adressen").json()
        assert adressen["heimnetz"] is True
        assert all(url.endswith("/geraet") for url in adressen["urls"])
    finally:
        get_settings_service().update({"heimnetz": bool(vorher)})


def test_pi_update_nur_auf_dem_pi(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")
    moeglich, grund = dienst.pi_update_moeglich()
    assert not moeglich and "Raspberry Pi" in grund
    antwort = TestClient(app).post("/api/system/pi-update")
    assert antwort.status_code == 400
