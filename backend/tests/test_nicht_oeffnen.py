from __future__ import annotations

import asyncio
import json

import pytest

from app.services import browserwahl, websearch_service, websuche_browser
from app.services.tools import OEFFNEN, ToolBox, runde_beginnen


@pytest.fixture(autouse=True)
def _wunsch_zuruecksetzen():
    yield
    runde_beginnen()


@pytest.fixture()
def geoeffnet(monkeypatch):
    aufrufe = []

    def oeffnen(adresse, browser=""):
        aufrufe.append((adresse, browser))
        return {"ok": True, "url": adresse}

    monkeypatch.setattr(browserwahl, "oeffnen", oeffnen)
    return aufrufe


def ausfuehren(name, args):
    return json.loads(asyncio.run(ToolBox().execute(name, args)))


def test_nachschauen_oeffnet_kein_fenster(geoeffnet):
    runde_beginnen("Schau mal nach, wie das Wetter morgen in Wien wird")
    ergebnis = ausfuehren("open_url", {"url": "https://wetter.orf.at"})
    assert ergebnis["nicht_geoeffnet"] and "web_search" in ergebnis["error"]
    assert ausfuehren("browser_goto", {"url": "https://wetter.orf.at"})["nicht_geoeffnet"]
    assert geoeffnet == []


def test_ausdruecklich_oeffnen_bleibt_erlaubt(geoeffnet):
    runde_beginnen("Öffne mir bitte YouTube")
    ergebnis = ausfuehren("open_url", {"url": "https://www.youtube.com"})
    assert ergebnis["ok"] and geoeffnet == [("https://www.youtube.com", "")]
    runde_beginnen()
    assert ausfuehren("open_url", {"url": "https://orf.at"})["ok"]


def test_websuche_bleibt_im_hintergrund(monkeypatch, geoeffnet):
    async def direkt(frage, anzahl, tief):
        return {"treffer": [], "mager": True, "fehler": "zu wenig"}

    def sichtbar(*args, **kwargs):
        pytest.fail("Die Suche hat den sichtbaren Browser benutzt")

    monkeypatch.setattr(websearch_service, "search_web", direkt)
    monkeypatch.setattr(websuche_browser, "suchen", sichtbar)
    runde_beginnen("Was kostet das neue iPhone?")
    ausfuehren("web_search", {"query": "iPhone Preis", "browser": "edge"})
    assert geoeffnet == []


def test_absicht_zum_oeffnen():
    for text in ["Öffne mir YouTube", "mach mal die Seite von Spiegel auf", "geh auf github.com", "spiel mir das Lied von Queen ab", "zeig mir die Website von Apple", "mach das in Edge", "was steht auf dieser Seite", "Ruf bitte orf.at auf"]:
        assert OEFFNEN.search(text), text
    for text in ["Wie wird das Wetter morgen in Wien?", "Schau mal nach, was das iPhone 17 kostet", "Was ist das neueste Video auf YouTube von MrBeast?", "Recherchiere die Öffnungszeiten vom Billa", "Erstelle eine Tabelle mit Preisen", "prüf mal ob die Seite erreichbar ist", "Geh die Liste durch und sag mir was fehlt"]:
        assert not OEFFNEN.search(text), text
