from __future__ import annotations

import asyncio
import json

from app.services.chat_service import card_payload
from app.services.werkzeug_register import finden, finden_async, laden


def _rufen(name: str, args: dict) -> dict:
    laden()
    asynchron = finden_async(name)
    if asynchron is not None:
        return json.loads(asyncio.run(asynchron(None, args, name)))
    return json.loads(finden(name)(None, args, name))


def test_neues_handy_zeigt_qr_karte():
    from app.services.handy_service import get_handy_service

    try:
        ergebnis = _rufen("geraet_verbinden", {"art": "Smartphone"})
        assert ergebnis["ok"] and ergebnis["art"] == "handy"
        assert len(ergebnis["code"]) == 12
        nutzlast = json.loads(ergebnis["nutzlast"])
        assert nutzlast["direct_only"] is True and nutzlast["c"] == ergebnis["code"]
        karte = card_payload("geraet_verbinden", json.dumps(ergebnis))
        assert karte["kind"] == "kopplung" and karte["data"]["code_gruppiert"].count("-") == 2
        assert get_handy_service().kopplung_status()["status"] == "offen"
    finally:
        get_handy_service().kopplung_abbrechen()


def test_uhr_ohne_handy_bekommt_code():
    from app.services.handy_service import get_handy_service

    try:
        ergebnis = _rufen("geraet_verbinden", {"art": "meine Smartwatch"})
        assert ergebnis["art"] == "uhr" and len(ergebnis["code"]) == 12 and "Code eingeben" in ergebnis["anleitung"]
    finally:
        get_handy_service().kopplung_abbrechen()


def test_karteikarten_aus_eigenen_karten():
    ergebnis = _rufen("karteikarten", {"thema": "Photosynthese", "karten": [
        {"frage": "Wo findet die Photosynthese statt?", "antwort": "In den Chloroplasten."},
        {"frage": "Was entsteht neben Glucose?", "antwort": "Sauerstoff."},
        {"frage": "Nur Frage"},
    ]})
    assert ergebnis["ok"] and ergebnis["anzahl"] == 2 and ergebnis["aktion"] == "lernen"
    karte = card_payload("karteikarten", json.dumps(ergebnis))
    assert karte["kind"] == "karteikarten" and karte["data"]["deck"] == ergebnis["deck"]
    liste = _rufen("karteikarten", {"aktion": "liste"})
    assert any(d["id"] == ergebnis["deck"] for d in liste["decks"])
    wieder = _rufen("karteikarten", {"aktion": "lernen", "deck": "photosynth"})
    assert wieder["deck"] == ergebnis["deck"]
    assert _rufen("karteikarten", {"aktion": "loeschen", "deck": ergebnis["deck"]})["ok"]


def test_karteikarten_ohne_thema_fragen_nach():
    ergebnis = _rufen("karteikarten", {})
    assert ergebnis["ok"] is False and "Thema" in ergebnis["error"]
    assert card_payload("karteikarten", json.dumps(ergebnis)) is None


def test_haftnotiz_anlegen_und_abhaken():
    neu = _rufen("haftnotiz", {"text": "Kakao und Zimt kaufen", "farbe": "blau"})
    assert neu["ok"] and neu["notiz"]["color"] == "blau"
    assert any(n["id"] == neu["notiz"]["id"] for n in _rufen("haftnotiz", {"aktion": "liste"})["notizen"])
    fertig = _rufen("haftnotiz", {"aktion": "erledigt", "text": "zimt"})
    assert fertig["ok"] and fertig["erledigt"]["done"] is True
    assert _rufen("haftnotiz", {"aktion": "loeschen", "text": "kakao und zimt"})["ok"]


def test_rezept_und_text_brauchen_eingaben():
    assert _rufen("rezept", {})["ok"] is False
    assert _rufen("text_vermenschlichen", {"text": "kurz"})["ok"] is False


def test_bild_zeigen_baut_bildkarte(monkeypatch):
    from app.services import bildquelle

    async def finden(suche, anzahl=1):
        return [{"pfad": "C:/bilder/ton618.jpg", "titel": "TON 618 SDSS9.jpg", "quelle": "Wikimedia Commons", "seite": "https://commons.wikimedia.org/wiki/File:TON_618_SDSS9.jpg", "lizenz": "CC BY 4.0", "autor": "SDSS", "beschreibung": "", "url": "https://upload.wikimedia.org/x.jpg"}][:anzahl]

    monkeypatch.setattr(bildquelle, "finden", finden)
    ergebnis = _rufen("bild_zeigen", {"query": "TON 618 quasar", "anzahl": 2, "titel": "TON 618"})
    assert ergebnis["ok"] and ergebnis["bilder"][0]["lizenz"] == "CC BY 4.0"
    karte = card_payload("bild_zeigen", json.dumps(ergebnis))
    assert karte["kind"] == "webbild" and karte["data"]["titel"] == "TON 618"
    assert "url" not in karte["data"]["bilder"][0] and karte["data"]["bilder"][0]["pfad"].endswith("ton618.jpg")


def test_bild_zeigen_ohne_treffer_und_ohne_begriff(monkeypatch):
    from app.services import bildquelle

    async def nichts(suche, anzahl=1):
        return []

    monkeypatch.setattr(bildquelle, "finden", nichts)
    assert _rufen("bild_zeigen", {"query": "xyz"})["ok"] is False
    assert _rufen("bild_zeigen", {})["ok"] is False
    assert card_payload("bild_zeigen", json.dumps({"ok": False, "error": "x"})) is None


def test_visualise_laesst_alle_werkzeuge_offen():
    from app.services.chat_service import FORCED_PROMPTS, OFFEN_ERZWUNGEN, forced_tools
    from app.services.tools import CORE_TOOLS

    assert "bild_zeigen" in OFFEN_ERZWUNGEN and "bild_zeigen" in FORCED_PROMPTS
    assert "bild_zeigen" in CORE_TOOLS
    werkzeuge = [{"function": {"name": "web_search"}}, {"function": {"name": "bild_zeigen"}}]
    assert len(forced_tools(werkzeuge, "maps")) == 2
