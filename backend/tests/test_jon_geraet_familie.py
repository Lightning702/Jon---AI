from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.services.geraete_funktionen import HANDY_KONTEXT
from app.services.handy_service import RECHTE_VORGABE, HandyFehler, HandyService, sos_text


def _dienst(monkeypatch, tmp_path, faehigkeiten=("status", "apps", "durchsage", "klingeln", "regeln")):
    import app.services.handy_service as modul

    monkeypatch.setattr(modul, "STORE", tmp_path / "handy.json")
    dienst = HandyService()
    dienst._data["geraete"].append({
        "id": "geraet-1", "name": "Jon Gerät", "token": "t", "schluessel": "", "rechte": dict(RECHTE_VORGABE),
        "faehigkeiten": list(faehigkeiten), "zustand": {}, "gesehen": 0,
    })
    return dienst


def test_neue_rechte_sind_standardmaessig_an():
    for recht in ("durchsage", "klingeln", "regeln"):
        assert RECHTE_VORGABE[recht] is True


def test_zustand_behaelt_bildschirmzeit(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    stand = {"limits": {"tiktok": 60}, "genutzt": {"tiktok": 12}}
    dienst.zustand_melden("geraet-1", {"zustand": {"akku": 80, "bildschirmzeit": stand, "wecker": "morgen 06:30", "geheim": "x"}})
    zustand = dienst.zustand("geraet-1")["zustand"]
    assert zustand["bildschirmzeit"] == stand
    assert zustand["wecker"] == "morgen 06:30"
    assert "geheim" not in zustand


def test_sos_landet_in_meldungen_und_telegram(monkeypatch, tmp_path):
    import app.services.handy_service as modul

    dienst = _dienst(monkeypatch, tmp_path)
    gesendet = []

    async def telegram(text, daten=None):
        gesendet.append(text)

    monkeypatch.setattr(modul, "_telegram_melden", telegram)

    async def ablauf():
        antwort = await dienst.meldung_annehmen("geraet-1", {"art": "sos", "daten": {"akku": 17, "laedt": False, "zeit": 1_700_000_000_000, "lat": 48.2082, "lon": 16.3738, "genau": 12, "unsinn": {"x": 1}}})
        await asyncio.sleep(0)
        return antwort

    antwort = asyncio.run(ablauf())
    assert antwort["ok"]
    neu = dienst.meldungen_neu()
    assert len(neu) == 1 and neu[0]["art"] == "sos" and neu[0]["name"] == "Jon Gerät"
    assert "unsinn" not in neu[0]["daten"]
    assert dienst.meldungen_neu() == []
    assert gesendet and "SOS von Jon Gerät" in gesendet[0] and "17 %" in gesendet[0]
    assert "openstreetmap.org/?mlat=48.20820&mlon=16.37380" in gesendet[0] and "± 12 m" in gesendet[0]
    sicht = dienst.geraete()[0]
    assert sicht["meldungen"][0]["quittiert"] is False
    assert dienst.meldung_quittieren("geraet-1", sicht["meldungen"][0]["id"])
    assert dienst.geraete()[0]["meldungen"][0]["quittiert"] is True


def test_unbekannte_meldung_wird_abgelehnt(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    antwort = asyncio.run(dienst.meldung_annehmen("geraet-1", {"art": "hack", "daten": {}}))
    assert not antwort["ok"]


def test_durchsage_mit_lesebestaetigung(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    auftraege = []

    async def auftrag(geraete_id, op, daten=None, wartezeit=45.0):
        auftraege.append((geraete_id, op, daten))
        return {"ok": True, "daten": {"angezeigt": True}}

    monkeypatch.setattr(dienst, "auftrag", auftrag)
    ergebnis = asyncio.run(dienst.durchsage("geraet-1", "  Essen   ist fertig  ", True, "Mama"))
    assert ergebnis["angezeigt"]
    op = auftraege[0]
    assert op[1] == "durchsage" and op[2]["text"] == "Essen ist fertig" and op[2]["von"] == "Mama"
    kennung = ergebnis["kennung"]
    asyncio.run(dienst.meldung_annehmen("geraet-1", {"art": "gelesen", "daten": {"kennung": kennung}}))
    assert dienst.geraete()[0]["durchsagen"][0]["gelesen"]


def test_regeln_werden_gefiltert_und_gespeichert(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    gesendet = {}

    async def auftrag(geraete_id, op, daten=None, wartezeit=45.0):
        gesendet.update(daten or {})
        return {"ok": True, "daten": {"limits": {"tiktok": 30}, "pause_aktiv": False}}

    monkeypatch.setattr(dienst, "auftrag", auftrag)
    stand = asyncio.run(dienst.regeln_setzen("geraet-1", {"limits": {"tiktok": 30, "chrome": 999}, "nacht": {"an": True, "von": "21:00", "boese": 1}}))
    assert gesendet["limits"] == {"tiktok": 30}
    assert gesendet["nacht"] == {"an": True, "von": "21:00"}
    assert stand["limits"]["tiktok"] == 30
    assert dienst.zustand("geraet-1")["zustand"]["bildschirmzeit"]["limits"]["tiktok"] == 30
    with pytest.raises(HandyFehler):
        asyncio.run(dienst.regeln_setzen("geraet-1", {"unbekannt": 1}))


def test_freie_apps_aus_dem_zustand(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    gesendet = {}

    async def auftrag(geraete_id, op, daten=None, wartezeit=45.0):
        gesendet.update(daten or {})
        return {"ok": True, "daten": {"limits": {}, "pause_aktiv": False}}

    monkeypatch.setattr(dienst, "auftrag", auftrag)
    with dienst._lock:
        dienst._data["geraete"][0]["zustand"] = {"apps": [{"id": "com.google.android.youtube", "name": "YouTube"}]}
    asyncio.run(dienst.regeln_setzen("geraet-1", {
        "limits": {"com.google.android.youtube": 45, "chrome": 10},
        "nacht": {"apps": ["com.google.android.youtube", "chrome"]},
        "extra": {"com.google.android.youtube": 20, "fremd.app": 30},
    }))
    assert gesendet["limits"] == {"com.google.android.youtube": 45}
    assert gesendet["nacht"]["apps"] == ["com.google.android.youtube"]
    assert list(gesendet["ausnahmen"]) == ["com.google.android.youtube"]
    assert gesendet["ausnahmen"]["com.google.android.youtube"] > 0


def test_geraet_meldet_sich_selbst_ab(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    antwort = asyncio.run(dienst._bearbeiten({"op": "abmelden", "rid": "r1"}, dienst._data["geraete"][0]))
    assert antwort == {"rid": "r1", "ok": True}
    assert dienst.geraete() == []


def test_alte_app_kann_nicht_klingeln(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path, faehigkeiten=("status", "dateien"))
    with pytest.raises(HandyFehler, match="aktualisieren"):
        asyncio.run(dienst.klingeln("geraet-1", 30))


def test_ausgeschaltetes_recht_blockiert(monkeypatch, tmp_path):
    dienst = _dienst(monkeypatch, tmp_path)
    dienst.rechte_setzen("geraet-1", "klingeln", False)
    with pytest.raises(HandyFehler, match="ausgeschaltet"):
        asyncio.run(dienst.klingeln("geraet-1", 30))


def test_sos_text_ohne_zeit():
    text = sos_text("Handy", {"akku": 5, "laedt": True, "text": "Hilfe"})
    assert "5 % (lädt)" in text and "Hilfe" in text


def test_eltern_routen_nicht_vom_geraet(monkeypatch):
    from app.api import handy_routes

    marke = HANDY_KONTEXT.set("geraet-1")
    try:
        for aufruf in (
            handy_routes.device_rules("geraet-1", {"pause_minuten": 0}),
            handy_routes.device_announce("geraet-1", {"text": "x"}),
            handy_routes.device_ring("geraet-1", {}),
            handy_routes.alerts_new(),
        ):
            with pytest.raises(HTTPException) as fehler:
                asyncio.run(aufruf)
            assert fehler.value.status_code == 403
    finally:
        HANDY_KONTEXT.reset(marke)


def test_eltern_routen_vom_pc(monkeypatch):
    from app.api import handy_routes

    class Dienst:
        async def regeln_setzen(self, geraete_id, regeln):
            return {"pause_aktiv": True, "id": geraete_id, "regeln": regeln}

        def meldungen_neu(self):
            return [{"art": "sos"}]

    monkeypatch.setattr(handy_routes, "get_handy_service", lambda: Dienst())
    antwort = asyncio.run(handy_routes.device_rules("geraet-1", {"pause_minuten": 30}))
    assert antwort["bildschirmzeit"]["pause_aktiv"]
    assert asyncio.run(handy_routes.alerts_new())["meldungen"][0]["art"] == "sos"


def test_ki_werkzeuge_nicht_aus_dem_geraet(monkeypatch):
    from app.services.connectors.android import AndroidConnector

    connector = AndroidConnector()
    marke = HANDY_KONTEXT.set("geraet-1")
    try:
        ergebnis = asyncio.run(connector.ausfuehren("android_screen_time", {"action": "pause", "minutes": 600}))
    finally:
        HANDY_KONTEXT.reset(marke)
    assert "error" in ergebnis and "nicht vom Gerät" in ergebnis["error"]


def test_ki_durchsage_vom_pc(monkeypatch):
    from app.services.connectors.android import AndroidConnector

    connector = AndroidConnector()
    aufrufe = []

    class Dienst:
        async def durchsage(self, geraete_id, text, vorlesen=True, von=""):
            aufrufe.append((geraete_id, text, vorlesen))
            return {"angezeigt": True, "kennung": "k"}

    monkeypatch.setattr(connector, "_dienst", lambda: Dienst())
    monkeypatch.setattr(connector, "_waehlen", lambda args, recht: {"id": "geraet-1", "name": "Jon Gerät"})
    ergebnis = asyncio.run(connector.ausfuehren("android_announce", {"text": "Essen!", "speak": False}))
    assert ergebnis["angezeigt"] and ergebnis["geraet"] == "Jon Gerät"
    assert aufrufe == [("geraet-1", "Essen!", False)]
