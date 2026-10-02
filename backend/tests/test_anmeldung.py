import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import anmeldung_service as an

client = TestClient(app)


@pytest.fixture(autouse=True)
def frischer_zugang(tmp_path, monkeypatch):
    monkeypatch.setattr(an, "DATEI", tmp_path / "anmeldung.json")
    monkeypatch.setattr(an, "ITERATIONEN", 1000)
    monkeypatch.setattr(an, "_service", None)
    from app.core import krypto

    monkeypatch.setattr(krypto, "ARGON_SPEICHER", 8 * 1024)
    monkeypatch.setattr(krypto, "ARGON_ZEIT", 1)
    yield tmp_path / "anmeldung.json"


def _einrichten(name="Felix", passwort="geheim123"):
    return client.post(
        "/api/anmeldung/einrichten", json={"benutzername": name, "passwort": passwort}
    )


def _pruefen(name, passwort):
    return client.post(
        "/api/anmeldung/pruefen", json={"benutzername": name, "passwort": passwort}
    )


def test_erst_einrichten_dann_anmelden(frischer_zugang):
    stand = client.get("/api/anmeldung").json()
    assert stand["eingerichtet"] is False
    assert stand["support"] == "https://felworks-impressum.netlify.app/support"
    assert _einrichten().json() == {"ok": True}
    assert client.get("/api/anmeldung").json()["eingerichtet"] is True
    assert _pruefen("Felix", "geheim123").json() == {"ok": True}
    assert _pruefen("  felix ", "geheim123").status_code == 200
    assert _einrichten("Anders", "passwort99").status_code == 409


def test_zugang_liegt_nur_als_hash_auf_der_platte(frischer_zugang):
    _einrichten("Felix", "geheim123")
    inhalt = frischer_zugang.read_text(encoding="utf-8")
    assert "geheim123" not in inhalt
    assert "felix" not in inhalt.lower().replace("felix-", "")
    daten = json.loads(inhalt)
    assert daten["verfahren"] == "argon2id"
    assert daten["passwort"].startswith("$argon2id$")
    assert daten["benutzer"].startswith("$argon2id$")


def test_falsche_daten_und_sperre_nach_fuenf_versuchen():
    _einrichten()
    antwort = _pruefen("Felix", "falsch")
    assert antwort.status_code == 401
    assert antwort.json()["versuche_uebrig"] == 4
    assert _pruefen("Jemand", "geheim123").status_code == 401
    for _ in range(2):
        _pruefen("Felix", "falsch")
    gesperrt = _pruefen("Felix", "falsch")
    assert gesperrt.status_code == 429
    assert gesperrt.json()["sekunden"] == 60
    assert _pruefen("Felix", "geheim123").status_code == 429
    assert client.get("/api/anmeldung").json()["gesperrt_sekunden"] > 0


def test_zu_kurze_zugangsdaten_werden_abgelehnt():
    assert _einrichten("F", "geheim123").status_code == 400
    antwort = _einrichten("Felix", "123")
    assert antwort.status_code == 400
    assert "mindestens" in antwort.json()["detail"]
    assert client.get("/api/anmeldung").json()["eingerichtet"] is False


def test_benutzername_und_passwort_aendern():
    _einrichten()
    falsch = client.post(
        "/api/anmeldung/aendern",
        json={"benutzername": "Felix", "passwort": "falsch", "neues_passwort": "neues123"},
    )
    assert falsch.status_code == 401
    leer = client.post(
        "/api/anmeldung/aendern", json={"benutzername": "Felix", "passwort": "geheim123"}
    )
    assert leer.status_code == 400
    ok = client.post(
        "/api/anmeldung/aendern",
        json={
            "benutzername": "Felix",
            "passwort": "geheim123",
            "neuer_benutzername": "Chef",
            "neues_passwort": "neues123",
        },
    )
    assert ok.json() == {"ok": True}
    assert _pruefen("Felix", "geheim123").status_code == 401
    assert _pruefen("Chef", "neues123").status_code == 200
    nur_passwort = client.post(
        "/api/anmeldung/aendern",
        json={"benutzername": "Chef", "passwort": "neues123", "neues_passwort": "anders99"},
    )
    assert nur_passwort.status_code == 200
    assert _pruefen("Chef", "anders99").status_code == 200


def test_anmeldung_braucht_den_geraete_schluessel():
    ohne = TestClient(app, headers={})
    assert ohne.get("/api/anmeldung").status_code == 401


def test_alter_pbkdf2_zugang_wird_beim_anmelden_auf_argon2id_umgestellt(frischer_zugang):
    from app.core.store import atomic_write_json

    atomic_write_json(frischer_zugang, an._alt_eintrag("Felix", "geheim123"))
    assert _pruefen("Felix", "falsch").status_code == 401
    assert json.loads(frischer_zugang.read_text(encoding="utf-8"))["verfahren"] == "pbkdf2-sha256"
    assert _pruefen("Felix", "geheim123").status_code == 200
    daten = json.loads(frischer_zugang.read_text(encoding="utf-8"))
    assert daten["verfahren"] == "argon2id"
    assert _pruefen("felix", "geheim123").status_code == 200
