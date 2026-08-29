from __future__ import annotations

import json
import os
import threading

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.store import atomic_write_json, atomic_write_text, read_json
from app.main import app

TOKEN = os.environ["JON_TOKEN"]

client = TestClient(app)
offen = TestClient(app, headers={})


def test_gesundheit_bleibt_ohne_token_erreichbar():
    antwort = offen.get("/api/health")
    assert antwort.status_code == 200


def test_powershell_ohne_token_wird_abgewiesen():
    antwort = offen.post("/api/system/powershell", json={"command": "echo hallo"})
    assert antwort.status_code == 401
    assert "Schlüssel" in antwort.json()["detail"]


def test_einstellungen_ohne_token_werden_abgewiesen():
    assert offen.get("/api/settings").status_code == 401


def test_falsches_token_wird_abgewiesen():
    falsch = TestClient(app, headers={"X-Jon-Token": "nicht-das-richtige"})
    assert falsch.get("/api/settings").status_code == 401


def test_token_im_header_wird_akzeptiert():
    assert client.get("/api/settings").status_code == 200


def test_token_als_query_wird_akzeptiert():
    antwort = offen.get(f"/api/settings?token={TOKEN}")
    assert antwort.status_code == 200


def test_token_als_cookie_wird_akzeptiert():
    mit_cookie = TestClient(app, headers={})
    mit_cookie.cookies.set(auth.COOKIE_NAME, TOKEN)
    assert mit_cookie.get("/api/settings").status_code == 200


def test_spiele_ports_bleiben_fuer_mitspieler_offen():
    assert auth.is_open_path("/api/mp/info")
    assert not auth.is_open_path("/api/system/powershell")


def test_statische_seiten_brauchen_kein_token():
    assert auth.is_open_path("/blockwelt")
    assert auth.is_open_path("/app/index.html")


def test_token_vergleich_ist_streng():
    assert auth.token_matches(TOKEN)
    assert not auth.token_matches(TOKEN + "x")
    assert not auth.token_matches("")
    assert not auth.token_matches(None)


def test_cors_erlaubt_keinen_platzhalter_mehr():
    from app.core.config import Settings

    einstellungen = Settings(cors_origins="")
    assert "*" not in einstellungen.origins()
    assert "null" in einstellungen.origins()


def test_kopplungsadresse_enthaelt_token():
    url = auth.pair_url(8756, False)
    assert "token=" in url
    assert auth.get_token() in url


def test_atomares_schreiben_laesst_keine_reste(tmp_path):
    ziel = tmp_path / "daten.json"
    atomic_write_json(ziel, {"a": 1})
    assert read_json(ziel) == {"a": 1}
    atomic_write_json(ziel, {"a": 2})
    assert read_json(ziel) == {"a": 2}
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomares_schreiben_ueberlebt_parallele_zugriffe(tmp_path):
    ziel = tmp_path / "parallel.json"
    atomic_write_json(ziel, {"start": True})
    fehler: list[Exception] = []

    def schreiben(nummer: int) -> None:
        try:
            for _ in range(40):
                atomic_write_json(ziel, {"wer": nummer, "werte": list(range(200))})
                json.loads(ziel.read_text(encoding="utf-8"))
        except Exception as exc:
            fehler.append(exc)

    faeden = [threading.Thread(target=schreiben, args=(i,)) for i in range(6)]
    for faden in faeden:
        faden.start()
    for faden in faeden:
        faden.join()

    assert fehler == []
    assert isinstance(read_json(ziel), dict)
    assert list(tmp_path.glob("*.tmp")) == []


def test_read_json_verkraftet_kaputte_datei(tmp_path):
    ziel = tmp_path / "kaputt.json"
    atomic_write_text(ziel, "{ das ist kein json")
    assert read_json(ziel, default={"leer": True}) == {"leer": True}


def test_alte_datei_bleibt_wenn_neue_daten_nicht_serialisierbar_sind(tmp_path):
    ziel = tmp_path / "bestand.json"
    atomic_write_json(ziel, {"wichtig": "bleibt"})
    with pytest.raises(TypeError):
        atomic_write_json(ziel, {"kaputt": object()})
    assert read_json(ziel) == {"wichtig": "bleibt"}
