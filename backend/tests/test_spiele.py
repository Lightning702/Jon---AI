from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.services import arcade_service as arc

client = TestClient(app)

MANIFEST = {
    "sammlung": "Testsammlung",
    "herausgeber": "FelWorks",
    "version": "2.0",
    "bauen": "build.bat",
    "spiele": [
        {
            "id": "testspiel",
            "titel": "Testspiel",
            "genre": "Test",
            "icon": "🎯",
            "kurz": "kurz",
            "beschreibung": "lang",
            "steuerung": "WASD",
            "exe": "bin/test.exe",
            "args": ["-play", "0"],
            "vorschau": "vorschau/test.jpg",
        },
        {
            "id": "testweb",
            "titel": "Testweb",
            "typ": "web",
            "pfad": "/testweb",
            "vorschau": "vorschau/test.jpg",
        },
        {"titel": "Ohne Id"},
        "kaputt",
    ],
}


@pytest.fixture()
def wurzel(tmp_path, monkeypatch):
    spielordner = tmp_path / "Testspiel"
    (spielordner / "bin").mkdir(parents=True)
    (spielordner / "vorschau").mkdir()
    (spielordner / "jon-spiele.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    (spielordner / "build.bat").write_text("@echo off", encoding="utf-8")
    (spielordner / "vorschau" / "test.jpg").write_bytes(b"bild")
    monkeypatch.setattr(arc, "ROOT_DIR", tmp_path)
    return spielordner


def test_manifest_wird_gefunden_und_geputzt(wurzel):
    spiele = arc.ArcadeService().spiele()
    testspiel = next(s for s in spiele if s["id"] == "testspiel")
    assert testspiel["titel"] == "Testspiel"
    assert testspiel["version"] == "2.0"
    assert testspiel["herausgeber"] == "FelWorks"
    assert testspiel["sammlung"] == "Testsammlung"
    assert testspiel["vorschau"] is True
    assert [s["id"] for s in spiele].count("testspiel") == 1
    assert all(s["titel"] for s in spiele)


def test_web_spiel_wird_gelesen(wurzel):
    spiele = arc.ArcadeService().spiele()
    web = next(s for s in spiele if s["id"] == "testweb")
    assert web["typ"] == "web"
    assert web["status"] == "bereit"
    assert web["vorschau"] is True


def test_status_ohne_exe_ist_nicht_gebaut(wurzel):
    testspiel = next(s for s in arc.ArcadeService().spiele() if s["id"] == "testspiel")
    assert testspiel["status"] in ("nicht_gebaut", "fehlt")
    assert testspiel["baubar"] is (testspiel["status"] == "nicht_gebaut")


def test_status_mit_exe_ist_bereit(wurzel):
    (wurzel / "bin" / "test.exe").write_bytes(b"MZ")
    testspiel = next(s for s in arc.ArcadeService().spiele() if s["id"] == "testspiel")
    assert testspiel["status"] in ("bereit", "nicht_verfuegbar")
    assert testspiel["gebaut_am"]


def test_start_ohne_exe_meldet_verstaendlichen_fehler(wurzel):
    with pytest.raises(arc.SpielFehler) as fehler:
        arc.ArcadeService().starten("testspiel")
    assert "Testspiel" in str(fehler.value)


def test_unbekanntes_spiel_wirft_fehler(wurzel):
    with pytest.raises(arc.SpielFehler):
        arc.ArcadeService().starten("gibtsnicht")


def test_web_spiel_startet_ohne_prozess(wurzel, monkeypatch):
    def kein_start(*args, **kwargs):
        raise AssertionError("Ein Web-Spiel darf keinen Prozess starten")

    monkeypatch.setattr(arc.subprocess, "Popen", kein_start)
    ergebnis = arc.ArcadeService().starten("testweb")
    assert ergebnis == {"id": "testweb", "typ": "web", "pfad": "/testweb", "status": "bereit"}


def test_stoppen_ohne_lauf_ist_harmlos(wurzel):
    assert arc.ArcadeService().stoppen("testspiel")["status"] == "bereit"


def test_vorschau_datei(wurzel):
    assert arc.ArcadeService().vorschau("testspiel").read_bytes() == b"bild"
    with pytest.raises(arc.SpielFehler):
        arc.ArcadeService().vorschau("gibtsnicht")


def test_keine_eingebauten_webspiele_mehr(wurzel):
    assert arc.EINGEBAUTE_SPIELE == []
    assert all(s["typ"] == "nativ" for s in arc.ArcadeService().spiele() if s["id"] == "blockwelt")


def test_api_liefert_spiele():
    res = client.get("/api/games")
    assert res.status_code == 200
    spiele = res.json()["spiele"]
    assert isinstance(spiele, list)
    assert all(s["titel"] for s in spiele)


def test_api_unbekanntes_spiel_gibt_400():
    res = client.post("/api/games/gibtsnicht/start")
    assert res.status_code == 400
    assert "gibtsnicht" in res.json()["detail"]


def test_echte_spielesammlung_ist_eingetragen():
    manifest = Path(__file__).resolve().parents[2] / "ECHO" / "jon-spiele.json"
    if not manifest.exists():
        pytest.skip("ECHO-Ordner nicht vorhanden")
    daten = json.loads(manifest.read_text(encoding="utf-8"))
    assert daten["herausgeber"] == "FelWorks"
    assert {s["id"] for s in daten["spiele"]} == {"echo", "aetheria"}


@pytest.mark.parametrize(
    "ordner, spiel_id, exe",
    [
        ("HARMONIE", "harmonie", "bin/HARMONIE.exe"),
        ("BLOCKWELT", "blockwelt", "bin/BLOCKWELT.exe"),
        ("STARFALL", "starfall", "bin/STARFALL.exe"),
    ],
)
def test_native_spiele_haben_manifest(ordner, spiel_id, exe):
    manifest = Path(__file__).resolve().parents[2] / "spiele" / ordner / "jon-spiele.json"
    if not manifest.exists():
        pytest.skip(f"{ordner} nicht vorhanden")
    daten = json.loads(manifest.read_text(encoding="utf-8"))
    assert daten["herausgeber"] == "FelWorks"
    eintrag = next(s for s in daten["spiele"] if s["id"] == spiel_id)
    assert eintrag["exe"] == exe
    assert eintrag.get("typ", "nativ") == "nativ"
    assert (manifest.parent / eintrag["vorschau"]).exists()
    assert (manifest.parent / daten["bauen"]).exists()
