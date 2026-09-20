from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services import live_service
from app.services.handy_service import (
    _entschluesseln,
    _verschluesseln,
    code_erzeugen,
    get_handy_service,
    schluessel_fuer_code,
    thema_fuer,
)
from app.services.verbund_service import VerbundFehler, VerbundService

client = TestClient(app)


def _bildschirm_da() -> bool:
    try:
        live_service.bild("alle", 320, 40)
        return True
    except Exception:
        return False


def test_monitorliste_hat_immer_einen_eintrag():
    liste = live_service.monitore()
    assert liste
    assert all(m["id"] and m["name"] for m in liste)


def test_mehrere_monitore_bekommen_einen_alle_eintrag(monkeypatch):
    monkeypatch.setattr(
        live_service,
        "_monitore_windows",
        lambda: [
            {"links": 0, "oben": 0, "rechts": 1920, "unten": 1080},
            {"links": 1920, "oben": 0, "rechts": 3840, "unten": 1080},
        ],
    )
    monkeypatch.setattr(live_service.os, "name", "nt")
    liste = live_service.monitore()
    assert liste[0]["id"] == "alle"
    assert [m["id"] for m in liste[1:]] == ["1", "2"]
    assert liste[1]["breite"] == 1920


def test_stand_nennt_monitore_ohne_geheime_felder():
    stand = live_service.get_live_service().stand()
    assert "monitore" in stand
    assert all("feld" not in m for m in stand["monitore"])


@pytest.mark.skipif(not _bildschirm_da(), reason="Kein Bildschirm zum Aufnehmen")
def test_bild_kommt_als_jpeg():
    daten = live_service.bild("alle", 480, 40)
    assert daten[:2] == b"\xff\xd8"


@pytest.mark.skipif(not _bildschirm_da(), reason="Kein Bildschirm zum Aufnehmen")
def test_bild64_liefert_dasselbe_bild_als_text():
    antwort = client.get("/api/live/bild64", params={"breite": 480, "qualitaet": 40})
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["ok"] is True
    import base64

    assert base64.b64decode(daten["bild"])[:2] == b"\xff\xd8"


@pytest.mark.skipif(not _bildschirm_da(), reason="Kein Bildschirm zum Aufnehmen")
def test_start_und_stopp_merken_sich_den_zustand():
    dienst = live_service.get_live_service()
    stand = dienst.starten("alle", 3.0, 640, 40)
    assert stand["laeuft"] is True
    assert stand["takt"] == 3.0
    dienst.telegram_ziel("4711", 12)
    assert dienst.telegram_ziele()["4711"]["nachricht"] == 12
    aus = dienst.stoppen()
    assert aus["laeuft"] is False
    assert aus["telegram"] == []


def test_live_api_ist_ohne_schluessel_zu():
    ohne = TestClient(app, headers={})
    antwort = ohne.get("/api/live", headers={"X-Jon-Token": "falsch"})
    assert antwort.status_code == 401


def test_verbund_liste_ist_anfangs_leer():
    antwort = client.get("/api/verbund")
    assert antwort.status_code == 200
    assert isinstance(antwort.json()["geraete"], list)


def test_umschlag_des_verbundes_passt_zum_handy_protokoll():
    code = code_erzeugen()
    schluessel = schluessel_fuer_code(code)
    kennung = thema_fuer(code)
    zusatz = f"pair:{kennung}".encode("utf-8")
    dienst = get_handy_service()
    dienst.kopplung_starten()
    with dienst._lock:
        dienst._sitzung["code"] = code
        dienst._sitzung["thema"] = kennung
        dienst._sitzung["schluessel"] = schluessel
    umschlag = {
        "v": 2,
        "k": "pair",
        "i": kennung,
        "r": "abc123",
        **_verschluesseln(
            schluessel, zusatz, {"op": "pair", "rid": "1", "name": "Pi", "plattform": "Pi"}
        ),
    }
    antwort = asyncio.run(dienst.umschlag(umschlag))
    inhalt = _entschluesseln(schluessel, zusatz, antwort)
    assert inhalt["ok"] is True
    assert inhalt["status"] == "wartet"
    dienst.kopplung_abbrechen()


def test_kurzer_code_wird_abgelehnt():
    dienst = VerbundService()
    with pytest.raises(VerbundFehler):
        dienst.koppeln("ABC")


def test_unbekanntes_geraet_meldet_sich_deutlich():
    dienst = VerbundService()
    with pytest.raises(VerbundFehler):
        dienst.finden("gibtesnicht")


def test_geraet_wird_ueber_namensteil_gefunden():
    dienst = VerbundService()
    dienst._daten = {
        "geraete": [
            {
                "id": "a1",
                "name": "raspberrypi",
                "pc_id": "x",
                "geraete_id": "g",
                "schluessel": "",
                "token": "",
                "adressen": [],
                "broker": {"host": "h", "port": 1883},
                "erstellt": 0.0,
                "gesehen": 0.0,
                "weg": "",
                "version": "",
                "plattform": "Raspberry Pi",
            }
        ]
    }
    assert dienst.finden("pi")["id"] == "a1"
    assert dienst.finden("RASPBERRYPI")["id"] == "a1"


def test_direkter_weg_wird_vor_dem_relais_versucht(monkeypatch):
    dienst = VerbundService()
    eintrag = {
        "id": "b2",
        "name": "Pi",
        "pc_id": "x",
        "geraete_id": "g",
        "schluessel": "",
        "token": "tok",
        "adressen": ["http://127.0.0.1:1"],
        "broker": {"host": "h", "port": 1883},
        "erstellt": 0.0,
        "gesehen": 0.0,
        "weg": "",
        "version": "",
        "plattform": "",
    }
    dienst._daten = {"geraete": [eintrag]}
    monkeypatch.setattr(dienst, "_sichern", lambda: None)

    async def direkt(*_args, **_kwargs):
        return {"ok": True, "code": 200, "text": json.dumps({"version": "9.9.9"})}

    monkeypatch.setattr(dienst, "_direkt", direkt)

    def relais(*_args, **_kwargs):
        raise AssertionError("Das Relais haette nicht laufen duerfen.")

    monkeypatch.setattr(dienst, "_ueber_relais", relais)
    antwort = asyncio.run(dienst.rufen("b2"))
    assert antwort["ok"] is True
    assert eintrag["weg"] == "heimnetz"


def test_ohne_direkte_adresse_geht_es_ueber_das_relais(monkeypatch):
    dienst = VerbundService()
    eintrag = {
        "id": "c3",
        "name": "Pi",
        "pc_id": "x",
        "geraete_id": "g",
        "schluessel": "",
        "token": "tok",
        "adressen": [],
        "broker": {"host": "h", "port": 1883},
        "erstellt": 0.0,
        "gesehen": 0.0,
        "weg": "",
        "version": "",
        "plattform": "",
    }
    dienst._daten = {"geraete": [eintrag]}
    monkeypatch.setattr(dienst, "_sichern", lambda: None)
    monkeypatch.setattr(
        dienst,
        "_ueber_relais",
        lambda *_a, **_k: {"ok": True, "code": 200, "text": "{}"},
    )
    antwort = asyncio.run(dienst.rufen("c3"))
    assert antwort["ok"] is True
    assert eintrag["weg"] == "internet"
