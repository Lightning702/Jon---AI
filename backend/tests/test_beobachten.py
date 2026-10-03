from __future__ import annotations

import asyncio
import json

import pytest

from app.services.beobachten import Beobachten, json_lesen

TREFFER = {"treffer": [{"title": "Tiiny AI Pocket Lab ist ab heute erhältlich", "url": "https://news.example/pocket-lab", "snippet": "Der Verkauf hat begonnen.", "text": "Ab heute im Handel."}, {"title": "Gerücht", "url": "https://blog.example/geruecht", "snippet": "Vielleicht bald."}]}


class Uhr:
    def __init__(self):
        self.zeit = 1_800_000_000.0

    def __call__(self):
        return self.zeit


def dienst(tmp_path, urteile, suche=None, senden=None):
    uhr = Uhr()
    aufrufe = {"suche": 0, "modell": [], "gesendet": []}

    async def suchen(frage):
        aufrufe["suche"] += 1
        if suche:
            return await suche(frage)
        return TREFFER

    async def fragen(system, user):
        aufrufe["modell"].append(json.loads(user))
        wert = urteile.pop(0)
        if isinstance(wert, Exception):
            raise wert
        return wert

    async def telegram(text):
        if senden:
            return await senden(text)
        aufrufe["gesendet"].append(text)
        return True

    return Beobachten(tmp_path, suchen, fragen, telegram, uhr), uhr, aufrufe


def test_anlegen_mit_standardwerten_und_ohne_doppelte(tmp_path):
    d, _, _ = dienst(tmp_path, [])
    eintrag = d.anlegen("Tiiny AI Pocket Lab Release")
    assert eintrag["status"] == "aktiv" and eintrag["intervall_stunden"] == 24 and eintrag["bedingung"] == "Tiiny AI Pocket Lab Release"
    assert eintrag["letzter_check"] == 0 and eintrag["treffer"] is None
    assert d.anlegen("tiiny ai pocket lab release")["id"] == eintrag["id"]
    gespeichert = json.loads((tmp_path / "beobachtungen.json").read_text(encoding="utf-8"))
    assert {"id", "frage", "bedingung", "intervall_stunden", "letzter_check", "status", "treffer"} <= set(gespeichert[0])
    with pytest.raises(ValueError):
        d.anlegen("x")


def test_nicht_erfuellt_bleibt_aktiv_und_wartet_bis_zum_naechsten_intervall(tmp_path):
    d, uhr, aufrufe = dienst(tmp_path, ['{"erfuellt": false, "beweis": "", "quelle": ""}'])
    eintrag = d.anlegen("Tiiny AI Pocket Lab Release", "Das Gerät ist offiziell erschienen")
    assert asyncio.run(d.runde()) == 1
    stand = d.holen(eintrag["id"])
    assert stand["status"] == "aktiv" and stand["letzter_check"] == uhr.zeit and not aufrufe["gesendet"]
    assert aufrufe["modell"][0]["bedingung"] == "Das Gerät ist offiziell erschienen"
    uhr.zeit += 23 * 3600
    assert asyncio.run(d.runde()) == 0


def test_erfuellt_meldet_genau_einmal_in_app_und_telegram(tmp_path):
    d, uhr, aufrufe = dienst(tmp_path, ['Hier mein Ergebnis: {"erfuellt": true, "beweis": "Der Verkauf hat heute begonnen.", "quelle": "https://news.example/pocket-lab"}'])
    eintrag = d.anlegen("Tiiny AI Pocket Lab Release")
    asyncio.run(d.runde())
    stand = d.holen(eintrag["id"])
    assert stand["status"] == "erfuellt"
    assert stand["treffer"]["quelle"] == "https://news.example/pocket-lab" and "Verkauf" in stand["treffer"]["beweis"]
    assert len(aufrufe["gesendet"]) == 1 and "https://news.example/pocket-lab" in aufrufe["gesendet"][0]
    assert [m["id"] for m in d.meldungen()] == [eintrag["id"]]
    assert d.meldungen() == []
    uhr.zeit += 48 * 3600
    assert asyncio.run(d.runde()) == 0
    asyncio.run(d.pruefen(eintrag["id"]))
    assert len(aufrufe["gesendet"]) == 1 and aufrufe["suche"] == 1


def test_erfundene_quelle_oder_beleg_ohne_quelle_zaehlt_nicht(tmp_path):
    d, _, aufrufe = dienst(tmp_path, ['{"erfuellt": true, "beweis": "Ist erschienen", "quelle": "https://erfunden.example"}', '{"erfuellt": true, "beweis": "", "quelle": "https://news.example/pocket-lab"}'])
    eintrag = d.anlegen("Tiiny AI Pocket Lab Release", intervall_stunden=1)
    asyncio.run(d.pruefen(eintrag["id"]))
    d._aendern(eintrag["id"], letzter_check=0)
    asyncio.run(d.pruefen(eintrag["id"]))
    assert d.holen(eintrag["id"])["status"] == "aktiv" and not aufrufe["gesendet"]


def test_fehler_in_suche_und_modell_stoppen_den_dienst_nicht(tmp_path):
    zaehler = {"n": 0}

    async def kaputte_suche(frage):
        zaehler["n"] += 1
        if zaehler["n"] == 1:
            raise ConnectionError("kein Netz")
        return TREFFER

    d, uhr, aufrufe = dienst(tmp_path, [RuntimeError("Modell überlastet"), '{"erfuellt": true, "beweis": "Verkauf gestartet", "quelle": "https://news.example/pocket-lab"}'], suche=kaputte_suche)
    a = d.anlegen("Tiiny AI Pocket Lab Release")
    b = d.anlegen("Zweite Beobachtung zum Testen")
    assert asyncio.run(d.runde()) == 2
    assert "kein Netz" in d.holen(a["id"])["letzter_fehler"] and "überlastet" in d.holen(b["id"])["letzter_fehler"]
    assert d.holen(a["id"])["status"] == "aktiv" and d.holen(a["id"])["letzter_check"] == uhr.zeit
    uhr.zeit += 25 * 3600
    d._aendern(b["id"], status="gestoppt")
    asyncio.run(d.runde())
    assert d.holen(a["id"])["status"] == "erfuellt" and len(aufrufe["gesendet"]) == 1


def test_telegram_fehler_verhindert_die_app_meldung_nicht(tmp_path):
    async def kaputt(text):
        raise RuntimeError("Telegram nicht verbunden")

    d, _, _ = dienst(tmp_path, ['{"erfuellt": true, "beweis": "Verkauf gestartet", "quelle": "https://news.example/pocket-lab"}'], senden=kaputt)
    eintrag = d.anlegen("Tiiny AI Pocket Lab Release")
    asyncio.run(d.runde())
    assert d.holen(eintrag["id"])["status"] == "erfuellt" and len(d.meldungen()) == 1


def test_stoppen_und_json_lesen(tmp_path):
    d, _, _ = dienst(tmp_path, [])
    eintrag = d.anlegen("Etwas beobachten")
    assert d.stoppen(eintrag["id"])["status"] == "gestoppt"
    assert not d.faellig(d.holen(eintrag["id"]))
    assert json_lesen('```json\n{"erfuellt": false}\n```') == {"erfuellt": False}
    with pytest.raises(ValueError):
        json_lesen("kein json")


def test_chat_werkzeug_und_api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.services import beobachten as modul
    from app.services.risiko import LESE_TOOLS
    from app.services.tools import CORE_TOOLS, ToolBox

    d, _, _ = dienst(tmp_path, [])
    monkeypatch.setattr(modul, "_dienst", d)
    assert "beobachten" in LESE_TOOLS and "beobachten" in CORE_TOOLS
    box = ToolBox()
    angelegt = json.loads(asyncio.run(box.execute("beobachten", {"aktion": "anlegen", "frage": "Tiiny AI Pocket Lab Release", "bedingung": "offiziell erschienen"})))
    assert angelegt["ok"] and "solange er" in angelegt["hinweis"]
    liste = json.loads(asyncio.run(box.execute("beobachten", {"aktion": "liste"})))
    assert liste["beobachtungen"][0]["frage"] == "Tiiny AI Pocket Lab Release"
    client = TestClient(create_app())
    assert client.get("/api/beobachten").json()[0]["status"] == "aktiv"
    neu = client.post("/api/beobachten", json={"frage": "Neues iPhone vorgestellt"}).json()
    assert neu["intervall_stunden"] == 24
    assert client.delete(f"/api/beobachten/{neu['id']}").json() == {"geloescht": True}
    assert client.delete(f"/api/beobachten/{neu['id']}").status_code == 404
    gestoppt = json.loads(asyncio.run(box.execute("beobachten", {"aktion": "stoppen", "id": angelegt["beobachtung"]["id"]})))
    assert gestoppt["beobachtung"]["status"] == "gestoppt"
