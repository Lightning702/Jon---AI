from __future__ import annotations

import asyncio
import json
import os
import stat
import sys
import time

import pytest
from fastapi.testclient import TestClient

from app import codeserver
from app.codeserver import Codeserver, admin_daten, erstellen, normalisieren
from app.services import premium as modul
from app.services.premium import Abgelehnt, Premium, lesen

pytestmark = pytest.mark.standard
ADMIN = "ein-sehr-langer-admin-code"
GERAET = "a" * 20
ANDERES = "b" * 20


class Uhr:
    def __init__(self) -> None:
        self.wert = 1_800_000_000.0

    def __call__(self) -> float:
        return self.wert


@pytest.fixture()
def server(tmp_path):
    dienst = Codeserver(tmp_path / "codes", Uhr())
    dienst.admin_setzen(admin_daten(ADMIN))
    return dienst


@pytest.fixture()
def client(server):
    return TestClient(erstellen(server, pause=0), headers={})


def test_admin_code_liefert_signierte_admin_lizenz_ohne_klartext_auf_der_platte(server, client):
    antwort = client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET})
    assert antwort.status_code == 200 and antwort.json()["stufe"] == "admin"
    inhalt = server.lesen(antwort.json()["token"])
    assert inhalt["stufe"] == "admin" and inhalt["geraete"] == [GERAET] and inhalt["quelle"] == "codes"
    assert inhalt["exp"] - server.uhr() == 90 * 86400
    for datei in server.ordner.iterdir():
        assert ADMIN not in datei.read_text(encoding="utf-8")
    assert client.get("/codes/status").json() == {"ok": True, "oeffentlich": server.oeffentlich(), "admin": True}


def test_admin_erzeugt_entwickler_codes_die_nur_als_hash_gespeichert_werden(server, client):
    admin = client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).json()["token"]
    neu = client.post("/codes/erstellen", json={"token": admin, "geraet": GERAET, "name": "Anna", "geraete": 2}).json()
    code = neu["code"]
    assert code.startswith("ENT-") and len(code) == 28 and normalisieren(code)
    gespeichert = (server.ordner / "codes.json").read_text(encoding="utf-8")
    assert normalisieren(code) not in gespeichert and "Anna" in gespeichert
    assert neu["codes"][0]["name"] == "Anna" and neu["codes"][0]["geraete"] == 0
    entwickler = client.post("/codes/einloesen", json={"code": code.lower().replace("-", " "), "geraet": ANDERES})
    assert entwickler.status_code == 200 and entwickler.json()["stufe"] == "entwickler"
    inhalt = server.lesen(entwickler.json()["token"])
    assert inhalt["stufe"] == "entwickler" and inhalt["name"] == "Anna" and inhalt["code"] == neu["codes"][0]["id"]
    assert client.post("/codes/liste", json={"token": admin, "geraet": GERAET}).json()["codes"][0]["geraete"] == 1


def test_entwickler_darf_keine_codes_erzeugen(server, client):
    admin = client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).json()["token"]
    code = client.post("/codes/erstellen", json={"token": admin, "geraet": GERAET}).json()["code"]
    entwickler = client.post("/codes/einloesen", json={"code": code, "geraet": ANDERES}).json()["token"]
    for pfad in ("/codes/erstellen", "/codes/liste"):
        antwort = client.post(pfad, json={"token": entwickler, "geraet": ANDERES})
        assert antwort.status_code == 403 and "Admin" in antwort.json()["detail"]
    assert client.post("/codes/liste", json={"token": admin, "geraet": ANDERES}).status_code == 403


def test_geraetegrenze_sperren_und_erneuern(server, client):
    admin = client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).json()["token"]
    neu = client.post("/codes/erstellen", json={"token": admin, "geraet": GERAET, "geraete": 1}).json()
    code, kennung = neu["code"], neu["codes"][0]["id"]
    token = client.post("/codes/einloesen", json={"code": code, "geraet": ANDERES}).json()["token"]
    assert client.post("/codes/einloesen", json={"code": code, "geraet": ANDERES}).status_code == 200
    voll = client.post("/codes/einloesen", json={"code": code, "geraet": "c" * 20})
    assert voll.status_code == 403 and "1 Geräten" in voll.json()["detail"]
    server.uhr.wert += 5 * 86400
    erneuert = client.post("/codes/erneuern", json={"token": token, "geraet": ANDERES}).json()["token"]
    assert server.lesen(erneuert)["exp"] == server.uhr() + 14 * 86400
    assert client.post("/codes/erneuern", json={"token": token, "geraet": GERAET}).status_code == 403
    assert client.post("/codes/sperren", json={"token": admin, "geraet": GERAET, "id": kennung}).json()["codes"][0]["gesperrt"]
    gesperrt = client.post("/codes/erneuern", json={"token": token, "geraet": ANDERES})
    assert gesperrt.status_code == 403 and "gesperrt" in gesperrt.json()["detail"]
    assert "gesperrt" in client.post("/codes/einloesen", json={"code": code, "geraet": ANDERES}).json()["detail"]
    client.post("/codes/sperren", json={"token": admin, "geraet": GERAET, "id": kennung, "gesperrt": False})
    assert client.post("/codes/erneuern", json={"token": token, "geraet": ANDERES}).status_code == 200


def test_neuer_admin_code_sperrt_alte_admin_lizenzen(server, client):
    admin = client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).json()["token"]
    server.admin_setzen(admin_daten("ein-ganz-anderer-admin-code"))
    assert client.post("/codes/erneuern", json={"token": admin, "geraet": GERAET}).status_code == 403
    assert client.post("/codes/liste", json={"token": admin, "geraet": GERAET}).status_code == 403
    assert client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).status_code == 403


def test_falsche_codes_werden_gebremst_und_fremde_lizenzen_abgelehnt(server, client):
    for _ in range(8):
        assert client.post("/codes/einloesen", json={"code": "ENT-AAAA-BBBB-CCCC-DDDD-EEEE", "geraet": GERAET}).status_code == 403
    gebremst = client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET})
    assert gebremst.status_code == 429
    server.uhr.wert += 901
    assert client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).status_code == 200
    fremd = Codeserver(server.ordner.parent / "fremd", Uhr())
    fremd.admin_setzen(admin_daten(ADMIN))
    assert client.post("/codes/liste", json={"token": fremd.admin_token(GERAET), "geraet": GERAET}).status_code == 403
    assert client.post("/codes/einloesen", json={"code": ADMIN, "geraet": "kein-geraet"}).status_code == 422
    assert client.post("/codes/einloesen", json={"code": "x" * 30, "geraet": GERAET}, headers={"x-forwarded-for": "1.2.3.4"}).status_code == 403


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Dateirechte nur unter Linux prüfbar")
def test_geheime_dateien_sind_nur_fuer_den_besitzer_lesbar(server):
    server.oeffentlich()
    server.erstellen("x", 1)
    assert stat.S_IMODE(os.stat(server.ordner).st_mode) == 0o700
    for name in ("schluessel.pem", "admin.json", "codes.json"):
        assert stat.S_IMODE(os.stat(server.ordner / name).st_mode) == 0o600


def test_kommandozeile_richtet_admin_ein_und_stellt_lizenz_aus(tmp_path, monkeypatch, capsys):
    import io

    monkeypatch.setenv("JON_CODES_DIR", str(tmp_path / "cli"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(admin_daten(ADMIN)) + "\n"))
    codeserver.main(["admin"])
    codeserver.main(["lizenz", GERAET])
    token = capsys.readouterr().out.strip().splitlines()[-1]
    dienst = Codeserver(tmp_path / "cli")
    assert dienst.lesen(token)["stufe"] == "admin"
    assert dienst.ist_admin_code(ADMIN) and not dienst.ist_admin_code(ADMIN + "x")


@pytest.fixture()
def jon(tmp_path, monkeypatch, server):
    monkeypatch.setattr(modul, "CODE_OEFFENTLICH", server.oeffentlich())
    monkeypatch.setattr(modul, "_maschine", lambda: "test-maschine")
    return Premium(tmp_path / "jon")


def test_jon_loest_codes_ein_zeigt_entwickler_und_verwaltet_codes_als_admin(jon, server, client):
    async def codeserver_rufen(name, daten):
        antwort = client.post("/codes/" + name, json=daten)
        if antwort.status_code >= 400:
            raise (Abgelehnt if antwort.status_code in {401, 403} else ValueError)(antwort.json()["detail"])
        return antwort.json()

    jon.codeserver = codeserver_rufen

    async def ablauf():
        with pytest.raises(ValueError, match="nur der Admin"):
            await jon.codes()
        status = await jon.admin(ADMIN)
        assert status["stufe"] == "admin" and status["name"] == "Admin" and status["codes"]
        neu = await jon.code_erstellen("Lena", 3)
        assert (await jon.codes())["codes"][0]["name"] == "Lena"
        jon.abmelden()
        status = await jon.eingeben(neu["code"])
        assert status["stufe"] == "entwickler" and status["name"] == "Entwickler" and status["inhaber"] == "Lena"
        assert not status["codes"] and all(f["frei"] for f in status["features"])
        assert jon.premium()
        jon.pruefen("studio")
        for _ in range(5):
            jon.verbrauchen("harness")
        with pytest.raises(ValueError, match="nur der Admin"):
            await jon.code_erstellen("Neu", 1)
        assert (await jon.erneuern())["stufe"] == "entwickler"
        server.sperren(lesen(jon.token())["code"], True)
        with pytest.raises(Abgelehnt, match="gesperrt"):
            await jon.erneuern()
        assert jon.stufe() == "standard" and not jon.token()

    asyncio.run(ablauf())


def test_premium_schluessel_vom_codeserver_wird_nicht_als_premium_akzeptiert(jon, server):
    falsch = server.signieren({"stufe": "premium", "geraete": [jon.geraet()], "exp": time.time() + 3600})
    with pytest.raises(ValueError, match="keine gültige Stufe"):
        jon.speichern(falsch)
