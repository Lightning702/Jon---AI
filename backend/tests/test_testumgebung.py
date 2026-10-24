from __future__ import annotations

import asyncio
import json
import sys

import pytest

from app.services import testumgebung as modul


@pytest.fixture
def dienst(tmp_path, monkeypatch):
    monkeypatch.setenv("JON_TESTUMGEBUNG_DIR", str(tmp_path / "Testumgebung"))
    neu = modul.Testumgebung()
    monkeypatch.setattr(neu, "docker", lambda frisch=False: {"installiert": False, "laeuft": False})
    monkeypatch.setattr(modul, "_dienst", neu)
    return neu


def test_anlegen_schreiben_lesen_und_loeschen(dienst):
    umgebung = dienst.erstellen("Mein Test", False)
    assert umgebung["modus"] == "ordner" and umgebung["id"] == "mein-test"
    zweite = dienst.erstellen("Mein Test", False)
    assert zweite["id"] == "mein-test-2"
    dienst.schreiben("mein-test", "src/app.py", "print('hi')")
    assert dienst.lesen("mein-test", "src/app.py")["inhalt"] == "print('hi')"
    assert [d["pfad"] for d in dienst.dateien("mein-test")["dateien"]] == ["src/app.py"]
    with pytest.raises(modul.Fehler):
        dienst.schreiben("mein-test", "../draussen.txt", "x")
    with pytest.raises(modul.Fehler):
        dienst.lesen("mein-test", modul.META)
    assert len(dienst.liste()["umgebungen"]) == 2
    dienst.loeschen("mein-test")
    assert [u["id"] for u in dienst.liste()["umgebungen"]] == ["mein-test-2"]


def test_python_code_laeuft_und_liefert_ausgabe(dienst):
    kennung = dienst.standard()
    ergebnis = dienst.code(kennung, "python", "import sys\nprint('Summe', sum(range(5)))\nsys.exit(3)")
    assert ergebnis["exit"] == 3
    assert "Summe 10" in ergebnis["ausgabe"]
    assert ergebnis["datei"] == "main.py"


def test_html_bekommt_eine_vorschau(dienst):
    kennung = dienst.standard()
    ergebnis = dienst.code(kennung, "html", "<!doctype html><h1>Hallo</h1>", "spiel.html")
    assert ergebnis["vorschau"] == "/testumgebung-vorschau/standard/spiel.html"
    assert dienst.datei_fuer_vorschau("standard", "spiel.html").read_text(encoding="utf-8").endswith("</h1>")


def test_befehl_mit_zeitlimit(dienst):
    kennung = dienst.standard()
    befehl = "Start-Sleep -Seconds 20" if sys.platform == "win32" else "sleep 20"
    ergebnis = dienst.ausfuehren(kennung, befehl, 2)
    assert ergebnis["abgebrochen"] is True
    assert ergebnis["dauer"] < 15


def test_zuruecksetzen_leert_die_umgebung(dienst):
    kennung = dienst.standard()
    dienst.schreiben(kennung, "alt.txt", "weg")
    neu = dienst.zuruecksetzen(kennung)
    assert neu["id"] == "standard" and neu["dateien"] == 0


def test_fehlende_sprache_wird_erklaert(dienst, monkeypatch):
    monkeypatch.setattr(modul.shutil, "which", lambda name: None)
    with pytest.raises(modul.Fehler) as fehler:
        dienst.code(dienst.standard(), "php", "<?php echo 1;")
    assert "nicht installiert" in str(fehler.value)


def test_risiko_und_werkzeug(dienst):
    from app.services.risiko import NIEDRIG, MITTEL, HOCH, bewerten
    from app.services.werkzeug_register import finden_async, laden

    dienst.standard()
    assert bewerten("testumgebung", {"aktion": "dateien"}).risiko == NIEDRIG
    assert bewerten("testumgebung", {"aktion": "code", "sprache": "python"}).risiko == MITTEL
    assert bewerten("testumgebung", {"aktion": "ausfuehren", "befehl": "Remove-Item -Recurse -Force C:\\"}).risiko == HOCH
    laden()
    antwort = json.loads(asyncio.run(finden_async("testumgebung")(None, {"aktion": "code", "sprache": "python", "code": "print(6*7)"}, "testumgebung")))
    assert "42" in antwort["ausgabe"]


def test_vorschau_route_ist_abgeschottet(dienst):
    from fastapi.testclient import TestClient

    from app.main import app

    dienst.code(dienst.standard(), "html", "<h1>Vorschau</h1>")
    with TestClient(app) as client:
        antwort = client.get("/testumgebung-vorschau/standard/index.html")
        assert antwort.status_code == 200
        assert "sandbox" in antwort.headers["content-security-policy"]
        assert "Vorschau" in antwort.text
        assert client.get("/testumgebung-vorschau/standard/../../geheim.txt").status_code == 404


def test_gepacktes_jon_startet_echtes_python(dienst, monkeypatch):
    monkeypatch.setattr(modul.sys, "frozen", True, raising=False)
    monkeypatch.setattr(modul.shutil, "which", lambda name: {"python": None, "py": r"C:\Windows\py.exe"}.get(name))
    assert modul._programm("python") == r"C:\Windows\py.exe"
    monkeypatch.setattr(modul.shutil, "which", lambda name: None)
    with pytest.raises(modul.Fehler) as fehler:
        dienst.code(dienst.standard(), "python", "print(1)")
    assert "python ist auf diesem PC nicht installiert" in str(fehler.value)


def test_gepacktes_backend_startet_keinen_zweiten_server(monkeypatch):
    import run_backend

    monkeypatch.setattr(run_backend.sys, "frozen", True, raising=False)
    for argumente in (["jon-backend.exe", "main.py"], ["jon-backend.exe", "-m", "playwright", "install"], ["jon-backend.exe", "-X", "utf8", "x.py"]):
        monkeypatch.setattr(run_backend.sys, "argv", argumente)
        with pytest.raises(SystemExit) as ende:
            run_backend.main()
        assert ende.value.code == 2


def test_docker_desktop_wird_auch_in_der_benutzerinstallation_gefunden(dienst, monkeypatch, tmp_path):
    from app.services import testumgebung as modul

    programm = tmp_path / "Programs" / "DockerDesktop" / "Docker Desktop.exe"
    programm.parent.mkdir(parents=True)
    programm.write_bytes(b"")
    gestartet = []
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "keine"))
    monkeypatch.setattr(modul.shutil, "which", lambda name: None)
    monkeypatch.setattr(dienst, "docker", lambda frisch=False: {"installiert": True, "laeuft": False})
    monkeypatch.setattr(modul.subprocess, "Popen", lambda befehl, **k: gestartet.append(befehl))
    assert dienst.docker_starten()["ok"] is True
    assert gestartet == [[str(programm)]]
