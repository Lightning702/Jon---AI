from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.handy_service import (
    _entschluesseln,
    _verschluesseln,
    geraete_typ,
    get_handy_service,
    schluessel_fuer_code,
    standort_saeubern,
    thema_fuer,
)
from app.services.oekosystem_service import OekoFehler, get_oekosystem, name_passt

client = TestClient(app)


class _KeineKarte:
    async def reverse(self, lat, lon):
        return None

    async def home_details(self):
        return {"lat": 47.75, "lon": 16.23, "name": "Zuhause", "quelle": "nutzer"}


@pytest.fixture(autouse=True)
def _ohne_netz(monkeypatch):
    from app.services.maps import service as karten

    monkeypatch.setattr(karten, "get_maps_service", lambda: _KeineKarte())


def _koppeln(name: str, plattform: str, auto: dict | None = None, besitzer: str = "") -> str:
    dienst = get_handy_service()
    dienst.kopplung_abbrechen()
    dienst.kopplung_starten(False, auto)
    stand = dienst._pair_anmelden({"name": name, "plattform": plattform, "besitzer": besitzer})
    if not auto:
        assert stand["status"] == "wartet"
        dienst.kopplung_beantworten(True)
    else:
        assert stand["status"] == "verbunden"
    ergebnis = dienst._pair_stand()
    dienst.kopplung_abbrechen()
    return ergebnis["geraet"]


def _aufraeumen(*kennungen: str) -> None:
    for kennung in kennungen:
        get_handy_service().geraet_entfernen(kennung)


def test_namen_werden_tolerant_verglichen():
    assert name_passt("Felix", "Felix") == 3
    assert name_passt("felix", "Felix Heinisch") == 2
    assert name_passt("Félix", "felix") == 3
    assert name_passt("Mama", "Felix") == 0
    assert name_passt("Feli", "Felix Heinisch") == 1


def test_geraetetyp_wird_erkannt():
    assert geraete_typ("", "Wear OS 5 · Jon Uhr") == "uhr"
    assert geraete_typ("", "Android 15 · Jon Gerät") == "handy"
    assert geraete_typ("", "Raspberry Pi") == "pc"
    assert geraete_typ("tablet", "Android") == "tablet"


def test_standort_wird_geprueft():
    assert standort_saeubern({"lat": 200, "lon": 0}) is None
    assert standort_saeubern({"lat": True, "lon": 1}) is None
    ort = standort_saeubern({"lat": 47.1, "lon": 16.2, "genau": 12, "zeit": int(time.time() * 1000)})
    assert ort["lat"] == 47.1 and ort["genau"] == 12.0
    assert ort["zeit"] <= time.time()


def test_uhr_koppelt_ueber_das_handy_ohne_bestaetigung():
    handy = _koppeln("Galaxy A54", "Android 15 · Jon Gerät", besitzer="Felix")
    try:
        dienst = get_handy_service()
        dienst.besitzer_setzen(handy, "Felix")
        daten = asyncio.run(get_oekosystem().uhr_koppeln(handy))
        assert len(daten["code"]) == 12 and daten["besitzer"] == "Felix"
        uhr_schluessel = schluessel_fuer_code(daten["code"])
        thema = thema_fuer(daten["code"])
        zusatz = f"pair:{thema}".encode()
        umschlag = {"v": 2, "k": "pair", "i": thema, **_verschluesseln(uhr_schluessel, zusatz, {"op": "pair", "rid": "a", "name": "Galaxy Watch7", "plattform": "Wear OS 5 · Jon Uhr", "typ": "uhr"})}
        antwort = asyncio.run(dienst.umschlag(umschlag))
        assert _entschluesseln(uhr_schluessel, zusatz, antwort)["status"] == "verbunden"
        umschlag = {"v": 2, "k": "pair", "i": thema, **_verschluesseln(uhr_schluessel, zusatz, {"op": "pair-status", "rid": "b"})}
        ergebnis = _entschluesseln(uhr_schluessel, zusatz, asyncio.run(dienst.umschlag(umschlag)))
        uhr = ergebnis["geraet"]
        eintrag = next(g for g in dienst.geraete() if g["id"] == uhr)
        assert eintrag["typ"] == "uhr" and eintrag["besitzer"] == "Felix" and eintrag["ueber"] == handy
    finally:
        dienst.kopplung_abbrechen()
        _aufraeumen(handy, locals().get("uhr", ""))


def test_wo_ist_braucht_freigabe_und_nutzt_gespeicherten_standort():
    handy = _koppeln("Pixel 9", "Android 16 · Jon Gerät")
    try:
        dienst = get_handy_service()
        dienst.besitzer_setzen(handy, "Lena")
        with pytest.raises(OekoFehler, match="nicht freigegeben"):
            asyncio.run(get_oekosystem().wo_ist("Lena", "Mama"))
        dienst.rechte_setzen(handy, "standort", True)
        assert dienst.standort_merken(handy, {"lat": 47.7501, "lon": 16.2302, "genau": 15}) is not None
        ergebnis = asyncio.run(get_oekosystem().wo_ist("lena", "Mama"))
        assert ergebnis["ok"] and ergebnis["person"] == "lena"
        assert ergebnis["zuhause"] is True
        assert ergebnis["live"] is False
        assert "openstreetmap" in ergebnis["karte"]
        orte = asyncio.run(get_oekosystem().standorte(nur_lokal=True))["orte"]
        assert any(o["id"] == handy and o["zuhause"] for o in orte)
    finally:
        _aufraeumen(handy)


def test_unbekannte_person_liefert_hilfreichen_hinweis():
    with pytest.raises(OekoFehler, match="Besitzer"):
        asyncio.run(get_oekosystem().wo_ist("Niemand Bekanntes", "Mama", weiterfragen=False))


def test_standort_ohne_freigabe_wird_nicht_gespeichert():
    handy = _koppeln("Moto G", "Android 14 · Jon Gerät")
    try:
        assert get_handy_service().standort_merken(handy, {"lat": 1.0, "lon": 2.0}) is None
        assert get_oekosystem().lokale_standorte() == [] or all(o["id"] != handy for o in get_oekosystem().lokale_standorte())
    finally:
        _aufraeumen(handy)


def test_auftrag_an_offline_uhr_geht_ueber_das_handy():
    handy = _koppeln("Galaxy S25", "Android 16 · Jon Gerät")
    uhr = _koppeln("Galaxy Watch", "Wear OS · Jon Uhr", auto={"typ": "uhr", "besitzer": "Felix", "ueber": handy})
    dienst = get_handy_service()

    async def ablauf():
        abholer = asyncio.create_task(dienst.abholen(handy, {"warten": 5}))
        await asyncio.sleep(0.05)
        auftrag = asyncio.create_task(dienst.auftrag(uhr, "klingeln", {"sekunden": 10}, wartezeit=5))
        ereignisse = (await abholer)["ereignisse"]
        assert ereignisse and ereignisse[0]["daten"]["op"] == "uhr"
        daten = ereignisse[0]["daten"]
        assert daten["uhr_op"] == "klingeln" and daten["uhr"] == uhr and daten["uhr_daten"]["sekunden"] == 10
        dienst.antwort_annehmen(handy, {"auftrag": daten["auftrag"], "ok": True, "daten": {"klingelt": True}})
        return await auftrag

    try:
        ergebnis = asyncio.run(ablauf())
        assert ergebnis["ok"] and ergebnis["ueber"] == handy and ergebnis["geraet"] == uhr
    finally:
        _aufraeumen(handy, uhr)


def test_uhr_laesst_nur_eigenes_handy_klingeln(monkeypatch):
    handy = _koppeln("Galaxy A54", "Android 15 · Jon Gerät")
    fremd = _koppeln("Mamas Handy", "Android 14 · Jon Gerät")
    uhr = _koppeln("Galaxy Watch", "Wear OS · Jon Uhr", auto={"typ": "uhr", "besitzer": "Felix", "ueber": handy})
    dienst = get_handy_service()
    dienst.besitzer_setzen(handy, "Felix")
    dienst.besitzer_setzen(fremd, "Anita")
    geklingelt: list[str] = []

    async def klingeln(geraete_id, sekunden=30):
        geklingelt.append(geraete_id)
        return {"klingelt": True}

    monkeypatch.setattr(dienst, "klingeln", klingeln)
    try:
        ergebnis = asyncio.run(get_oekosystem().klingeln(uhr))
        assert ergebnis["ok"] and geklingelt == [handy]
        with pytest.raises(OekoFehler, match="eigenen"):
            asyncio.run(get_oekosystem().klingeln(uhr, fremd))
    finally:
        _aufraeumen(handy, fremd, uhr)


def test_aktives_geraet_lenkt_erinnerungen_um():
    handy = _koppeln("Galaxy A54", "Android 15 · Jon Gerät")
    oeko = get_oekosystem()
    try:
        oeko.aktiv_merken(handy)
        assert oeko.unterwegs()["id"] == handy
        assert client.get("/api/reminders/due").json() == []
        oeko.aktiv_merken("pc")
        assert oeko.unterwegs() is None
    finally:
        oeko.aktiv_merken("pc")
        _aufraeumen(handy)


def test_gedaechtnis_wird_getauscht_ohne_echo():
    oeko = get_oekosystem()
    vorher = oeko.gedaechtnis_export()["stand"]
    ergebnis = asyncio.run(oeko.gedaechtnis_tauschen("abc123", [{"content": "Felix trinkt gern Kakao mit Zimt."}], vorher))
    assert ergebnis["neu"] == 1
    assert all("Kakao mit Zimt" not in e["content"] for e in ergebnis["eintraege"])
    fremd = oeko.gedaechtnis_export(vorher, "geraet:anderes")
    assert any("Kakao mit Zimt" in e["content"] for e in fremd["eintraege"])
    doppelt = asyncio.run(oeko.gedaechtnis_tauschen("abc123", [{"content": "Felix trinkt gern Kakao mit Zimt."}], vorher))
    assert doppelt["neu"] == 0


def test_routen_liefern_uebersicht_und_standorte():
    stand = client.get("/api/oekosystem").json()
    assert stand["ich"]["typ"] == "pc" and isinstance(stand["geraete"], list)
    assert "orte" in client.get("/api/oekosystem/standorte?lokal=true").json()
    antwort = client.get("/api/oekosystem/wo-ist", params={"person": "Unbekannt", "weiter": "false"}).json()
    assert antwort["ok"] is False and antwort["fehler"]
    assert client.post("/api/oekosystem/uhr-koppeln").status_code == 400


def test_wo_ist_karte_wird_gebaut():
    from app.services.chat_service import card_payload

    karte = card_payload("wo_ist", json.dumps({"ok": True, "person": "Felix", "lat": 47.7, "lon": 16.2, "adresse": "Grazerstraße 11", "wann": "gerade eben", "zuhause": True}))
    assert karte["kind"] == "maps"
    assert karte["data"]["karte"]["marker"][0]["name"] == "Felix"
    assert card_payload("wo_ist", json.dumps({"ok": False, "error": "x"})) is None
