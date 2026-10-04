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
    assert "exp" not in inhalt
    for datei in server.ordner.iterdir():
        assert ADMIN not in datei.read_text(encoding="utf-8")
    assert client.get("/codes/status").json() == {"ok": True, "oeffentlich": server.oeffentlich(), "admin": True, "kostenlos": True}


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
    server.uhr.wert += 5000 * 86400
    erneuert = client.post("/codes/erneuern", json={"token": token, "geraet": ANDERES}).json()["token"]
    assert "exp" not in server.lesen(erneuert) and server.lesen(erneuert)["iat"] == int(server.uhr())
    assert client.post("/codes/liste", json={"token": admin, "geraet": GERAET}).status_code == 200
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
        assert jon.premium() and status["gueltig_bis"] == 0 and jon.braucht_erneuerung()
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


def test_unbekannte_stufen_vom_codeserver_werden_abgelehnt(jon, server):
    falsch = server.signieren({"stufe": "superadmin", "geraete": [jon.geraet()], "quelle": "codes"})
    with pytest.raises(ValueError, match="keine gültige Stufe"):
        jon.speichern(falsch)


def test_codes_gelten_fuer_immer_auch_wenn_der_pi_nicht_erreichbar_ist(jon, server):
    jon.speichern(server.entwickler_token({"id": "abcdefabcdef", "name": "Offline"}, jon.geraet()))

    async def nicht_erreichbar(name, daten):
        raise ConnectionError("Der FelWorks-Codeserver ist nicht erreichbar.")

    jon.codeserver = nicht_erreichbar
    with pytest.raises(ConnectionError):
        asyncio.run(jon.erneuern())
    assert jon.stufe() == "entwickler" and jon.status()["gueltig_bis"] == 0 and not jon.status()["hinweis"]


def _admin(client):
    return client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).json()["token"]


def _code(client, admin, **werte):
    return client.post("/codes/erstellen", json={"token": admin, "geraet": GERAET, **werte}).json()


def _einloesen(client, code, geraet):
    return client.post("/codes/einloesen", json={"code": code, "geraet": geraet}).json()


DRITTES = "c" * 20


def test_premium_codes_mit_laufzeit_und_fuer_immer(server, client):
    admin = _admin(client)
    monat = _code(client, admin, name="Gewinnspiel", art="premium", tage=30)
    assert monat["code"].startswith("PRE-") and monat["codes"][0]["art"] == "premium" and monat["codes"][0]["tage"] == 30
    eingeloest = _einloesen(client, monat["code"], ANDERES)
    inhalt = server.lesen(eingeloest["token"])
    assert eingeloest["stufe"] == "premium" and inhalt["stufe"] == "premium" and inhalt["exp"] == int(server.uhr()) + 30 * 86400
    immer = _code(client, admin, art="premium")
    assert "exp" not in server.lesen(_einloesen(client, immer["code"], ANDERES)["token"])
    server.uhr.wert += 31 * 86400
    abgelaufen = client.post("/codes/erneuern", json={"token": eingeloest["token"], "geraet": ANDERES})
    assert abgelaufen.status_code == 403 and "abgelaufen" in abgelaufen.json()["detail"]
    assert client.post("/codes/team/liste", json={"token": eingeloest["token"], "geraet": ANDERES}).status_code == 403


def test_admin_codes_geben_volle_rechte_und_lassen_sich_sperren(server, client):
    admin = _admin(client)
    neu = _code(client, admin, name="Zweiter Admin", art="admin")
    assert neu["code"].startswith("ADM-")
    zweiter = _einloesen(client, neu["code"], ANDERES)
    assert zweiter["stufe"] == "admin" and "pk" not in server.lesen(zweiter["token"])
    erzeugt = client.post("/codes/erstellen", json={"token": zweiter["token"], "geraet": ANDERES, "art": "entwickler"})
    assert erzeugt.status_code == 200 and len(erzeugt.json()["codes"]) == 2
    kennung = neu["codes"][0]["id"]
    bearbeitet = client.post("/codes/bearbeiten", json={"token": admin, "geraet": GERAET, "id": kennung, "name": "Co-Admin", "max_geraete": 5}).json()["codes"]
    assert next(c for c in bearbeitet if c["id"] == kennung)["name"] == "Co-Admin"
    client.post("/codes/sperren", json={"token": admin, "geraet": GERAET, "id": kennung})
    assert client.post("/codes/liste", json={"token": zweiter["token"], "geraet": ANDERES}).status_code == 403
    client.post("/codes/sperren", json={"token": admin, "geraet": GERAET, "id": kennung, "gesperrt": False})
    frei = client.post("/codes/geraet-entfernen", json={"token": admin, "geraet": GERAET, "id": kennung, "entfernen": ANDERES}).json()["codes"]
    assert next(c for c in frei if c["id"] == kennung)["geraete"] == 0
    assert client.post("/codes/liste", json={"token": zweiter["token"], "geraet": ANDERES}).status_code == 403


def test_team_nachrichten_ideen_und_rundschreiben(server, client, monkeypatch):
    gemeldet = []
    monkeypatch.setattr(server, "_melden_im_hintergrund", gemeldet.append)
    admin = _admin(client)
    anna_code = _code(client, admin, name="Anna")
    anna = _einloesen(client, anna_code["code"], ANDERES)["token"]
    ben = _einloesen(client, _code(client, admin, name="Ben")["code"], DRITTES)["token"]
    privat = client.post("/codes/team/senden", json={"token": anna, "geraet": ANDERES, "art": "idee", "text": "Dunkelmodus für MiniJon"}).json()
    idee = privat["nachrichten"][-1]
    assert idee["art"] == "idee" and idee["status"] == "neu" and idee["von"]["name"] == "Anna"
    assert any("Dunkelmodus" in g for g in gemeldet)
    assert client.post("/codes/team/liste", json={"token": ben, "geraet": DRITTES}).json()["nachrichten"] == []
    client.post("/codes/team/senden", json={"token": anna, "geraet": ANDERES, "art": "nachricht", "text": "Hallo Team", "an": "team"})
    assert [n["text"] for n in client.post("/codes/team/liste", json={"token": ben, "geraet": DRITTES}).json()["nachrichten"]] == ["Hallo Team"]
    assert client.post("/codes/team/senden", json={"token": ben, "geraet": DRITTES, "art": "rundschreiben", "text": "x"}).status_code == 403
    adminsicht = client.post("/codes/team/liste", json={"token": admin, "geraet": GERAET}).json()
    assert adminsicht["ungelesen"] == 2 and {m["name"] for m in adminsicht["mitglieder"]} == {"Anna", "Ben"}
    client.post("/codes/team/senden", json={"token": admin, "geraet": GERAET, "art": "rundschreiben", "text": "Bitte 4.61 testen"})
    client.post("/codes/team/senden", json={"token": admin, "geraet": GERAET, "art": "nachricht", "text": "Danke Anna", "an": anna_code["codes"][0]["id"], "antwort_auf": idee["id"]})
    bensicht = client.post("/codes/team/liste", json={"token": ben, "geraet": DRITTES}).json()
    assert [n["text"] for n in bensicht["nachrichten"]] == ["Hallo Team", "Bitte 4.61 testen"] and bensicht["ungelesen"] == 2
    annasicht = client.post("/codes/team/liste", json={"token": anna, "geraet": ANDERES}).json()
    assert "Danke Anna" in [n["text"] for n in annasicht["nachrichten"]]
    gestimmt = client.post("/codes/team/stimme", json={"token": anna, "geraet": ANDERES, "id": idee["id"]}).json()
    assert next(n for n in gestimmt["nachrichten"] if n["id"] == idee["id"])["stimmen"] == 1
    assert client.post("/codes/team/status", json={"token": anna, "geraet": ANDERES, "id": idee["id"], "status": "geplant"}).status_code == 403
    geplant = client.post("/codes/team/status", json={"token": admin, "geraet": GERAET, "id": idee["id"], "status": "geplant"}).json()
    assert next(n for n in geplant["nachrichten"] if n["id"] == idee["id"])["status"] == "geplant"
    assert client.post("/codes/team/gelesen", json={"token": admin, "geraet": GERAET}).json() == {"ungelesen": 0}
    assert client.post("/codes/team/ungelesen", json={"token": admin, "geraet": GERAET}).json()["ungelesen"] == 0


def test_fehlerbericht_mit_bild_und_schalter(server, client, monkeypatch):
    monkeypatch.setattr(server, "_melden_im_hintergrund", lambda text: None)
    admin = _admin(client)
    tester = _einloesen(client, _code(client, admin, name="Tester")["code"], ANDERES)["token"]
    bild = "data:image/jpeg;base64," + "A" * 100
    antwort = client.post("/codes/team/senden", json={"token": tester, "geraet": ANDERES, "art": "fehler", "text": "Absturz", "anhang": {"system": "Jon 4.60", "log": "Zeile", "bild": bild}}).json()
    nachricht = antwort["nachrichten"][-1]
    assert nachricht["anhang"] == {"system": "Jon 4.60", "log": "Zeile", "bild": True}
    assert client.post("/codes/team/anhang", json={"token": admin, "geraet": GERAET, "id": nachricht["id"]}).json()["bild"] == bild
    client.post("/codes/flags/setzen", json={"token": admin, "geraet": GERAET, "schluessel": "fehlerbericht", "an": False})
    gesperrt = client.post("/codes/team/senden", json={"token": tester, "geraet": ANDERES, "art": "fehler", "text": "x", "anhang": {"log": "y"}})
    assert gesperrt.status_code == 403 and "ausgeschaltet" in gesperrt.json()["detail"]
    zu_gross = client.post("/codes/team/senden", json={"token": admin, "geraet": GERAET, "art": "fehler", "text": "x", "anhang": {"bild": "data:image/png;base64," + "A" * 1_300_000}})
    assert zu_gross.status_code == 413


def test_beta_schalter_fuer_alle_oder_auswahl(server, client):
    admin = _admin(client)
    anna_code = _code(client, admin, name="Anna")
    anna = _einloesen(client, anna_code["code"], ANDERES)["token"]
    ben = _einloesen(client, _code(client, admin, name="Ben")["code"], DRITTES)["token"]
    assert client.post("/codes/erneuern", json={"token": anna, "geraet": ANDERES}).json()["flags"]["skills"] is True
    client.post("/codes/flags/setzen", json={"token": admin, "geraet": GERAET, "schluessel": "skills", "fuer": "auswahl", "codes": [anna_code["codes"][0]["id"]]})
    assert client.post("/codes/skills/liste", json={"token": anna, "geraet": ANDERES}).status_code == 200
    assert client.post("/codes/skills/liste", json={"token": ben, "geraet": DRITTES}).status_code == 403
    eigen = client.post("/codes/flags/setzen", json={"token": admin, "geraet": GERAET, "schluessel": "neues_menue", "name": "Neues Menü", "an": True}).json()["flags"]
    assert eigen["neues_menue"]["eigen"] and eigen["neues_menue"]["name"] == "Neues Menü"
    assert client.post("/codes/erneuern", json={"token": ben, "geraet": DRITTES}).json()["flags"] == {"neues_menue": True, "beta": True, "inspektor": True, "modell": True, "skills": False, "fehlerbericht": True}
    assert client.post("/codes/flags/setzen", json={"token": admin, "geraet": GERAET, "schluessel": "beta", "loeschen": True}).status_code == 400
    assert client.post("/codes/flags/setzen", json={"token": ben, "geraet": DRITTES, "schluessel": "beta", "an": False}).status_code == 403


def test_statistik_aus_berichten(server, client):
    admin = _admin(client)
    anna = _einloesen(client, _code(client, admin, name="Anna")["code"], ANDERES)["token"]
    bericht = {"version": "4.60.1", "system": "Windows 11", "nutzung": {"anfragen": 12, "tokens": 3400, "fehler": 1, "modelle": {"nvidia/nemotron": 12}, "werkzeuge": {"web_search": 4}, "anbieter": {"nvidia": 12}}}
    client.post("/codes/erneuern", json={"token": anna, "geraet": ANDERES, "bericht": bericht})
    client.post("/codes/erneuern", json={"token": admin, "geraet": GERAET, "bericht": {**bericht, "nutzung": {"anfragen": 3}}})
    statistik = client.post("/codes/statistik", json={"token": admin, "geraet": GERAET}).json()
    assert statistik["summe"]["anfragen"] == 15 and statistik["summe"]["werkzeuge"] == [["web_search", 4]]
    anna_geraet = next(g for g in statistik["geraete"] if g["geraet"] == ANDERES)
    assert anna_geraet["name"] == "Anna" and anna_geraet["version"] == "4.60.1" and anna_geraet["system"] == "Windows 11"
    liste = client.post("/codes/liste", json={"token": admin, "geraet": GERAET}).json()["codes"]
    assert liste[0]["geraete_liste"][0]["version"] == "4.60.1"
    assert client.post("/codes/statistik", json={"token": anna, "geraet": ANDERES}).status_code == 403


def test_skills_teilen_holen_und_entfernen(server, client, monkeypatch):
    monkeypatch.setattr(server, "_melden_im_hintergrund", lambda text: None)
    admin = _admin(client)
    anna = _einloesen(client, _code(client, admin, name="Anna")["code"], ANDERES)["token"]
    ben = _einloesen(client, _code(client, admin, name="Ben")["code"], DRITTES)["token"]
    geteilt = client.post("/codes/skills/teilen", json={"token": anna, "geraet": ANDERES, "name": "rezepte", "titel": "Rezepte", "inhalt": "# Rezepte\nKoche gut."}).json()["skills"]
    assert geteilt[0]["name"] == "rezepte" and "inhalt" not in geteilt[0] and geteilt[0]["autor"]["name"] == "Anna"
    assert client.post("/codes/skills/teilen", json={"token": ben, "geraet": DRITTES, "name": "rezepte", "inhalt": "x"}).status_code == 409
    geholt = client.post("/codes/skills/holen", json={"token": ben, "geraet": DRITTES, "id": geteilt[0]["id"]}).json()
    assert geholt["inhalt"].startswith("# Rezepte") and geholt["downloads"] == 1
    assert client.post("/codes/skills/teilen", json={"token": anna, "geraet": ANDERES, "name": "Böse Name", "inhalt": "x"}).status_code == 400
    assert client.post("/codes/skills/entfernen", json={"token": ben, "geraet": DRITTES, "id": geteilt[0]["id"]}).status_code == 404
    assert client.post("/codes/skills/entfernen", json={"token": anna, "geraet": ANDERES, "id": geteilt[0]["id"]}).json()["skills"] == []


def test_felworks_modellzugang_mit_kontingent(server, client):
    import httpx

    gesehen = []

    def nvidia(anfrage: httpx.Request) -> httpx.Response:
        gesehen.append((str(anfrage.url), anfrage.headers.get("authorization")))
        if anfrage.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "nvidia/nemotron-3-ultra-550b-a55b"}]})
        if json.loads(anfrage.content).get("stream"):
            return httpx.Response(200, content=b'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\ndata: [DONE]\n\n', headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "Hallo"}}]})

    server.llm_transport = httpx.MockTransport(nvidia)
    server.llm_schluessel, server.llm_basis = "nvapi-geheim", "https://nvidia.example/v1"
    admin = _admin(client)
    anna = _einloesen(client, _code(client, admin, name="Anna")["code"], ANDERES)["token"]
    kopf = {"Authorization": f"Bearer {anna}"}
    assert client.get("/codes/llm/v1/models").status_code == 401
    assert client.get("/codes/llm/v1/models", headers=kopf).json()["data"][0]["id"] == "nvidia/nemotron-3-ultra-550b-a55b"
    antwort = client.post("/codes/llm/v1/chat/completions", headers=kopf, json={"model": "nvidia/nemotron-3-ultra-550b-a55b", "messages": [{"role": "user", "content": "Hi"}]})
    assert antwort.json()["choices"][0]["message"]["content"] == "Hallo"
    assert gesehen[-1] == ("https://nvidia.example/v1/chat/completions", "Bearer nvapi-geheim")
    strom = client.post("/codes/llm/v1/chat/completions", headers=kopf, json={"model": "x", "stream": True, "messages": [{"role": "user", "content": "Hi"}]})
    assert "Hi" in strom.text and "[DONE]" in strom.text
    client.post("/codes/llm/kontingent", json={"token": admin, "geraet": GERAET, "wert": 2})
    voll = client.post("/codes/llm/v1/chat/completions", headers=kopf, json={"model": "x", "messages": [{"role": "user", "content": "Hi"}]})
    assert voll.status_code == 429 and "Tageskontingent" in voll.json()["detail"]
    for _ in range(3):
        assert client.post("/codes/llm/v1/chat/completions", headers={"Authorization": f"Bearer {admin}"}, json={"model": "x", "messages": [{"role": "user", "content": "Hi"}]}).status_code == 200
    assert client.post("/codes/statistik", json={"token": admin, "geraet": GERAET}).json()["felworks"] == {"kontingent": 2, "heute": 5, "gesamt": 5}
    client.post("/codes/flags/setzen", json={"token": admin, "geraet": GERAET, "schluessel": "modell", "an": False})
    assert client.get("/codes/llm/v1/models", headers=kopf).status_code == 403


def test_pi_steuerzentrale_nur_fuer_admins(server, client, monkeypatch):
    befehle = []

    def befehl(argumente, zeit=30):
        befehle.append(argumente)
        if argumente[:2] == ["systemctl", "show"]:
            return 0, "4242"
        if "is-active" in argumente:
            return 0, "active"
        return 0, "ok"

    server.befehl = befehl
    getoetet = []
    monkeypatch.setattr(codeserver.os, "kill", lambda pid, sig: getoetet.append(pid))
    admin = _admin(client)
    anna = _einloesen(client, _code(client, admin, name="Anna")["code"], ANDERES)["token"]
    assert client.post("/codes/pi/status", json={"token": anna, "geraet": ANDERES}).status_code == 403
    stand = client.post("/codes/pi/status", json={"token": admin, "geraet": GERAET}).json()
    assert stand["dienste"] == {"jon": "active", "jon-codes": "active", "jon-demo": "active"} and stand["version"]
    assert client.post("/codes/pi/neustart", json={"token": admin, "geraet": GERAET, "dienst": "jon-demo"}).json()["ok"]
    assert ["systemctl", "--user", "restart", "jon-demo"] in befehle
    assert client.post("/codes/pi/neustart", json={"token": admin, "geraet": GERAET, "dienst": "jon"}).json()["ok"] and getoetet == [4242]
    assert client.post("/codes/pi/neustart", json={"token": admin, "geraet": GERAET, "dienst": "rm -rf"}).status_code == 422
    assert client.post("/codes/pi/aktualisieren", json={"token": admin, "geraet": GERAET}).json()["ok"]
    assert any(a[:1] == ["git"] and "pull" in a for a in befehle)
    assert "log" in client.post("/codes/pi/log", json={"token": admin, "geraet": GERAET, "dienst": "jon-demo"}).json()


def test_jon_team_zentrale_flags_beta_fehlerbericht_und_skills(jon, server, client, monkeypatch):
    monkeypatch.setattr(server, "_melden_im_hintergrund", lambda text: None)

    async def codeserver_rufen(name, daten):
        antwort = client.post("/codes/" + name, json=daten)
        if antwort.status_code >= 400:
            raise (Abgelehnt if antwort.status_code in {401, 403} else ValueError)(antwort.json()["detail"])
        return antwort.json()

    jon.codeserver = codeserver_rufen
    import app.core.logbook as logbuch
    from app.services import skill_service

    monkeypatch.setattr(logbuch, "export_text", lambda: "start\nNVIDIA_API_KEY=nvapi-abcdefghijklmnop\nAuthorization: Bearer xyz\nende")
    monkeypatch.setattr(jon, "systembericht", lambda: "Jon 4.60.1 · Entwickler")
    geschrieben = {}
    monkeypatch.setattr(skill_service.SkillService, "__init__", lambda self: None)
    monkeypatch.setattr(skill_service.SkillService, "write", lambda self, name, inhalt: geschrieben.update({name: inhalt}) or {"name": name, "title": "Notizen", "chars": len(inhalt)})

    async def ablauf():
        assert jon.felworks_schluessel() is None and jon.flags() == {} and not jon.status()["team"]
        with pytest.raises(ValueError, match="Entwickler und Admins"):
            await jon.team("team/liste")
        await jon.admin(ADMIN)
        assert jon.status()["team"] and jon.status()["haupt"] and jon.flag("modell")
        neu = await jon.team("erstellen", {"name": "Lena", "art": "entwickler"})
        with pytest.raises(ValueError, match="Unbekannte Aktion"):
            await jon.team("pi/boese")
        jon.abmelden()
        await jon.eingeben(neu["code"])
        await jon.erneuern()
        status = jon.status()
        assert status["stufe"] == "entwickler" and status["team"] and not status["haupt"] and status["flags"]["inspektor"]
        assert jon.felworks_schluessel() == jon.token()
        assert not jon.beta_aktiv()
        jon.beta_setzen(True)
        assert jon.beta_aktiv() and jon.status()["beta"]
        gesendet = await jon.fehlerbericht("Absturz beim Speichern")
        bericht = gesendet["nachrichten"][-1]
        assert bericht["art"] == "fehler" and "nvapi-" not in bericht["anhang"]["log"] and "xyz" not in bericht["anhang"]["log"] and "[entfernt]" in bericht["anhang"]["log"]
        await jon.team("skills/teilen", {"name": "notizen", "titel": "Notizen", "inhalt": "# Notizen"})
        skills = (await jon.team("skills/liste"))["skills"]
        installiert = await jon.skill_installieren(skills[0]["id"])
        assert installiert["titel"] == "Notizen" and geschrieben == {"notizen": "# Notizen"}

    asyncio.run(ablauf())


def test_premium_code_schaltet_in_jon_premium_frei_aber_kein_team(jon, server, client):
    admin = client.post("/codes/einloesen", json={"code": ADMIN, "geraet": GERAET}).json()["token"]
    code = client.post("/codes/erstellen", json={"token": admin, "geraet": GERAET, "art": "premium", "tage": 7}).json()["code"]
    token = client.post("/codes/einloesen", json={"code": code, "geraet": jon.geraet()}).json()["token"]
    status = jon.speichern(token)
    assert status["stufe"] == "premium" and status["gueltig_bis"] > 0 and not status["team"] and not status["abo"]
    assert jon.premium() and not jon.flag("inspektor") and jon.felworks_schluessel() is None


def test_inspektor_misst_anfragen_und_werkzeuge():
    from app.providers.base import ChatMessage, ChatRequest, StreamChunk
    from app.services.inspektor import Inspektor

    inspektor = Inspektor()

    async def strom(anfrage, ausfuehren=None):
        yield StreamChunk(delta="denke", kind="reasoning")
        yield StreamChunk(kind="tool", name="web_search", args={})
        yield StreamChunk(kind="tool_result", name="web_search", ok=True, result="x")
        yield StreamChunk(delta="Antwort", kind="content")
        yield StreamChunk(kind="usage", prompt_tokens=120, completion_tokens=30)

    gemessen = inspektor.umhuellen("nvidia", strom)

    async def ablauf():
        teile = [t async for t in gemessen(ChatRequest(messages=[ChatMessage(role="user", content="Wetter?")], model="m1", tools=[{}, {}]))]
        assert len(teile) == 5

    asyncio.run(ablauf())
    eintrag = inspektor.liste()[0]
    assert eintrag["anbieter"] == "nvidia" and eintrag["modell"] == "m1" and eintrag["frage"] == "Wetter?" and eintrag["antwort"] == "Antwort"
    assert eintrag["werkzeuge"] == [{"name": "web_search", "ok": True}] and eintrag["prompt_tokens"] == 120 and eintrag["werkzeuge_angeboten"] == 2 and not eintrag["laeuft"]
    nutzung = inspektor.nutzung()
    assert nutzung["anfragen"] == 1 and nutzung["tokens"] == 150 and nutzung["werkzeuge"] == {"web_search": 1}


def test_beta_kanal_nimmt_die_hoechste_version_mit_vorabversionen(monkeypatch):
    from app.services import update_service

    liste = [{"tag_name": "v4.60.1", "prerelease": False, "draft": False, "assets": []}, {"tag_name": "v4.61.1", "prerelease": True, "draft": False, "assets": [{"name": "Jon-Setup.exe", "browser_download_url": "https://x/setup.exe", "size": 5}]}, {"tag_name": "v4.62.1", "prerelease": True, "draft": True, "assets": []}]
    monkeypatch.setattr(update_service, "_fetch", lambda url, timeout=10.0: json.dumps(liste if "per_page" in url else liste[0]).encode())
    monkeypatch.setattr(update_service, "_beta", lambda: True)
    assert update_service._release()["version"] == "4.61.1" and update_service._release()["beta"] is True
    monkeypatch.setattr(update_service, "_beta", lambda: False)
    assert update_service._release()["version"] == "4.60.1"


def test_premium_kostenlos_fuer_alle_und_admin_kann_es_beenden(server, client):
    assert client.get("/codes/status").json()["kostenlos"] is True
    assert client.post("/codes/kostenlos/verfuegbar").json() == {"verfuegbar": True}
    antwort = client.post("/codes/kostenlos", json={"geraet": ANDERES}).json()
    inhalt = lesen(antwort["token"], server.oeffentlich())
    assert antwort["stufe"] == "premium" and inhalt["stufe"] == "premium" and inhalt["kostenlos"] and "exp" not in inhalt
    assert inhalt["geraete"] == [ANDERES] and inhalt["code"] == "frei-" + ANDERES[:12]
    neu = client.post("/codes/erneuern", json={"token": antwort["token"], "geraet": ANDERES}).json()
    assert lesen(neu["token"], server.oeffentlich())["kostenlos"] and "flags" not in neu
    assert client.post("/codes/kostenlos", json={"geraet": ANDERES}).status_code == 200
    assert client.post("/codes/erneuern", json={"token": antwort["token"], "geraet": GERAET}).status_code == 403
    admin = _admin(client)
    assert client.post("/codes/kostenlos/stand", json={"token": antwort["token"], "geraet": ANDERES}).status_code == 403
    assert client.post("/codes/kostenlos/setzen", json={"token": antwort["token"], "geraet": ANDERES, "aktiv": False}).status_code == 403
    stand = client.post("/codes/kostenlos/stand", json={"token": admin, "geraet": GERAET}).json()
    assert stand["aktiv"] and stand["geraete"] == 1 and stand["aktiv_7_tage"] == 1 and stand["neu_7_tage"] == 1
    stand = client.post("/codes/kostenlos/setzen", json={"token": admin, "geraet": GERAET, "aktiv": False}).json()
    assert not stand["aktiv"] and stand["ausgeschaltet"]
    abgelehnt = client.post("/codes/erneuern", json={"token": antwort["token"], "geraet": ANDERES})
    assert abgelehnt.status_code == 403 and "beendet" in abgelehnt.json()["detail"]
    assert client.post("/codes/kostenlos", json={"geraet": DRITTES}).status_code == 403
    assert client.get("/codes/status").json()["kostenlos"] is False
    assert client.post("/codes/kostenlos/setzen", json={"token": admin, "geraet": GERAET, "aktiv": True}).json()["aktiv"]
    assert client.post("/codes/erneuern", json={"token": antwort["token"], "geraet": ANDERES}).status_code == 200
    assert client.post("/codes/erneuern", json={"token": admin, "geraet": GERAET}).status_code == 200


def test_premium_kostenlos_wird_pro_adresse_gebremst(server, client):
    for i in range(codeserver.KOSTENLOS_PRO_IP):
        assert client.post("/codes/kostenlos", json={"geraet": f"{i:020x}"}).status_code == 200
    assert client.post("/codes/kostenlos", json={"geraet": "f" * 20}).status_code == 429
    assert client.post("/codes/kostenlos", json={"geraet": f"{0:020x}"}).status_code == 200
    server.uhr.wert += 3601
    assert client.post("/codes/kostenlos", json={"geraet": "f" * 20}).status_code == 200
    assert server.kostenlos_stand()["geraete"] == codeserver.KOSTENLOS_PRO_IP + 1


def test_jon_holt_premium_kostenlos_und_faellt_nach_dem_ende_auf_standard(jon, server, client):
    async def codeserver_rufen(name, daten):
        antwort = client.post("/codes/" + name, json=daten)
        if antwort.status_code >= 400:
            raise (Abgelehnt if antwort.status_code in {401, 403} else ValueError)(antwort.json()["detail"])
        return antwort.json()

    jon.codeserver = codeserver_rufen

    async def ablauf():
        assert await jon.kostenlos_verfuegbar()
        status = await jon.kostenlos_holen()
        assert status["stufe"] == "premium" and status["kostenlos"] and status["gueltig_bis"] == 0 and not status["team"]
        assert all(f["frei"] for f in status["features"]) and jon.braucht_erneuerung()
        assert not await jon.kostenlos_verfuegbar()
        assert (await jon.erneuern())["kostenlos"]
        admin = _admin(client)
        client.post("/codes/kostenlos/setzen", json={"token": admin, "geraet": GERAET, "aktiv": False})
        with pytest.raises(Abgelehnt, match="beendet"):
            await jon.erneuern()
        assert jon.stufe() == "standard" and not jon.token()
        jon._kostenlos = (time.time(), True)
        with pytest.raises(Abgelehnt):
            await jon.kostenlos_holen()
        assert not await jon.kostenlos_verfuegbar()

    asyncio.run(ablauf())


def test_jon_meldet_kein_kostenloses_premium_wenn_der_pi_fehlt(jon):
    async def nicht_erreichbar(name, daten):
        raise ConnectionError("Der FelWorks-Codeserver ist nicht erreichbar.")

    jon.codeserver = nicht_erreichbar
    assert asyncio.run(jon.kostenlos_verfuegbar()) is False
