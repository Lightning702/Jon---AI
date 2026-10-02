from __future__ import annotations

import base64
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

import app.services.sicherung_service as modul
from app.main import app
from app.services.sicherung_service import SicherungFehler, SicherungService


def _zip(mit_meta: bool = True) -> bytes:
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as archiv:
        if mit_meta:
            archiv.writestr("jon-sicherung.json", "{}")
        archiv.writestr("dateien/fitness.json", '{"schritte": 1}')
    return puffer.getvalue()


@pytest.fixture
def dienst(monkeypatch, tmp_path):
    monkeypatch.setattr(modul, "ORDNER", tmp_path / "sicherungen")
    monkeypatch.setattr(modul, "TEIL", 16)
    frisch = SicherungService()
    monkeypatch.setattr(modul, "_dienst", frisch)
    return frisch


def test_sicherung_hochladen_und_wieder_holen(dienst):
    inhalt = _zip()
    marke = dienst.starten("geraet-1", len(inhalt))["marke"]
    for i in range(0, len(inhalt), 50):
        dienst.anhaengen("geraet-1", marke, base64.b64encode(inhalt[i:i + 50]).decode())
    eintrag = dienst.abschliessen("geraet-1", marke)
    assert eintrag["groesse"] == len(inhalt)
    assert [s["name"] for s in dienst.liste("geraet-1")] == [eintrag["name"]]
    geladen = b""
    offset = 0
    while True:
        teil = dienst.teil("geraet-1", eintrag["name"], offset)
        geladen += base64.b64decode(teil["data"])
        if teil["offset"] >= teil["size"]:
            break
        offset = teil["offset"]
    assert geladen == inhalt


def test_fremde_daten_werden_abgelehnt(dienst):
    inhalt = _zip(mit_meta=False)
    marke = dienst.starten("geraet-1", len(inhalt))["marke"]
    dienst.anhaengen("geraet-1", marke, base64.b64encode(inhalt).decode())
    with pytest.raises(SicherungFehler, match="keine Jon-Sicherung"):
        dienst.abschliessen("geraet-1", marke)
    with pytest.raises(SicherungFehler):
        dienst.starten("../boese", 10)
    with pytest.raises(SicherungFehler):
        dienst.teil("geraet-1", "../../geheim.zip", 0)
    marke = dienst.starten("geraet-1", 5)["marke"]
    with pytest.raises(SicherungFehler, match="Mehr Daten"):
        dienst.anhaengen("geraet-1", marke, base64.b64encode(b"123456").decode())
    with pytest.raises(SicherungFehler, match="abgelaufen"):
        dienst.anhaengen("geraet-2", marke, base64.b64encode(b"1").decode())


def test_nur_die_neuesten_bleiben(dienst, monkeypatch):
    monkeypatch.setattr(modul, "BEHALTEN", 2)
    zeiten = iter(["20260101-000001", "20260101-000002", "20260101-000003"])
    monkeypatch.setattr(modul.time, "strftime", lambda format, *rest: next(zeiten) + ".zip")
    for _ in range(3):
        inhalt = _zip()
        marke = dienst.starten("geraet-1", len(inhalt))["marke"]
        dienst.anhaengen("geraet-1", marke, base64.b64encode(inhalt).decode())
        dienst.abschliessen("geraet-1", marke)
    assert [s["name"] for s in dienst.liste("geraet-1")] == ["20260101-000003.zip", "20260101-000002.zip"]


def test_ohne_geraet_fragt_die_api(dienst):
    antwort = TestClient(app).get("/api/handy/sicherung/liste")
    assert antwort.status_code == 400
    assert TestClient(app).get("/api/handy/sicherung/liste?geraet=geraet-1").json() == {"sicherungen": []}
