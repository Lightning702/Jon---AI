from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import automation_service
from app.services import bildschirm_agent as ba
from app.services import telegram_service as ts


def _el(name, art="Button", x=100, y=100, w=80, h=30, quelle="fenster"):
    return ba.Element(name=name, art=art, x=x, y=y, w=w, h=h, quelle=quelle)


@pytest.fixture(autouse=True)
def frisch():
    ba._letzte.update(zeit=0.0, elemente=[], titel="", auswahl_zeit=0.0, auswahl_art="links")
    yield
    ba._letzte.update(zeit=0.0, elemente=[], titel="", auswahl_zeit=0.0, auswahl_art="links")


@pytest.fixture
def bildschirm(monkeypatch):
    geklickt: list[tuple] = []
    stand = {"elemente": [], "fenster": {"x": 0, "y": 0, "w": 1600, "h": 900}}
    monkeypatch.setattr(ba, "ui_elemente", lambda: {"titel": "Testseite", "fenster": stand["fenster"], "elemente": list(stand["elemente"])})
    monkeypatch.setattr(ba, "texte", lambda bereich: [])
    monkeypatch.setattr(ba, "_fensterbereich", lambda fenster: (0, 0, 1600, 900))
    monkeypatch.setattr(ba, "fenster_an", lambda x, y: "Testseite")
    monkeypatch.setattr(ba, "fenster_rechteck", lambda x, y: (0, 0, 1600, 900))
    monkeypatch.setattr(ba, "_vordergrund_titel", lambda: "Testseite")

    async def nichts(*a, **k):
        return None

    async def kurz(*a, **k):
        return None

    monkeypatch.setattr(ba, "per_markierung", nichts)
    monkeypatch.setattr(ba, "per_raster", nichts)
    monkeypatch.setattr(ba.asyncio, "sleep", lambda *a, **k: kurz())
    monkeypatch.setattr(automation_service.AutomationService, "mouse_click", lambda self, x, y, knopf="left", anzahl=1: geklickt.append((x, y, knopf, anzahl)) or {"clicked_at": [x, y]})
    stand["geklickt"] = geklickt
    return stand


def test_lagewoerter_werden_abgetrennt():
    assert ba.lage_lesen("Start oben rechts") == ("start", {"senkrecht": "oben", "waagrecht": "rechts"})
    assert ba.lage_lesen("den zweiten Anmelden Button") == ("den anmelden button", {"nr": 2})
    assert ba.lage_lesen("den Start Button ganz unten") == ("den start button", {"senkrecht": "unten"})
    assert ba.lage_lesen("Links") == ("Links", {})
    assert ba.lage_lesen("Start") == ("Start", {})


def test_nach_lage_waehlt_die_richtige_ecke():
    links_oben = _el("Start", x=10, y=10)
    rechts_oben = _el("Start", x=1400, y=10)
    unten = _el("Start", x=700, y=800)
    liste = ba.kandidaten("Start", [links_oben, rechts_oben, unten])
    assert ba.nach_lage(liste, {"senkrecht": "oben", "waagrecht": "rechts"}) is rechts_oben
    assert ba.nach_lage(liste, {"senkrecht": "oben", "waagrecht": "links"}) is links_oben
    assert ba.nach_lage(liste, {"senkrecht": "unten"}) is unten
    assert ba.nach_lage(liste, {"nr": 2}) is rechts_oben
    assert ba.nach_lage(liste, {"nr": -1}) is unten
    assert ba.nach_lage(liste, {"nr": 5}) is None


def test_gleiche_namen_sind_gleichauf_doppelte_quellen_nicht():
    knopf = _el("Aktualisieren", x=10)
    text_im_knopf = _el("Aktualisieren", art="Text", quelle="text", x=20, y=105, w=50, h=20)
    assert ba.gleichauf(ba.kandidaten("Aktualisieren", [knopf, text_im_knopf])) == []
    zweiter = _el("Aktualisieren", x=900)
    assert len(ba.gleichauf(ba.kandidaten("Aktualisieren", [knopf, zweiter]))) == 2


def test_doppelter_name_fragt_statt_zu_raten(bildschirm):
    bildschirm["elemente"] = [_el("Anmelden", art="Hyperlink", x=1400, y=20), _el("Anmelden", x=700, y=500)]
    ergebnis = asyncio.run(ba.klicken("Anmelden"))
    assert ergebnis.get("mehrdeutig") and not bildschirm["geklickt"]
    assert "2-mal" in ergebnis["error"]
    assert "1. Anmelden (Link, oben rechts im Fenster „Testseite“)" in ergebnis["error"]
    assert "2. Anmelden (Knopf, Mitte im Fenster „Testseite“)" in ergebnis["error"]


def test_antwort_mit_nummer_klickt_das_gewaehlte(bildschirm):
    bildschirm["elemente"] = [_el("Anmelden", art="Hyperlink", x=1400, y=20), _el("Anmelden", x=700, y=500)]
    asyncio.run(ba.klicken("Anmelden"))
    for antwort in ("2", "die zweite", "Nummer 2"):
        assert ba.befehl_erkennen(antwort) == {"aktion": "klicken", "ziel": "2", "art": "links"}
    ergebnis = asyncio.run(ba.klicken("2"))
    assert ergebnis["erkannt_per"] == "liste"
    assert bildschirm["geklickt"] == [(740, 515, "left", 1)]
    assert ba.befehl_erkennen("2") is None


def test_ohne_offene_frage_ist_eine_zahl_kein_klick():
    assert ba.befehl_erkennen("2") is None
    assert ba.befehl_erkennen("die zweite") is None


def test_lagewort_im_befehl_klickt_sofort(bildschirm):
    bildschirm["elemente"] = [_el("Start", x=10, y=10), _el("Start", x=1400, y=10), _el("Start", x=700, y=800)]
    befehl = ba.befehl_erkennen("Klick auf den Start Button oben rechts")
    assert befehl == {"aktion": "klicken", "ziel": "den Start Button oben rechts", "art": "links"}
    ergebnis = asyncio.run(ba.klicken(befehl["ziel"]))
    assert ergebnis["erkannt_per"] == "lage"
    assert bildschirm["geklickt"] == [(1440, 25, "left", 1)]


def test_oben_rechts_klicken_ist_kein_rechtsklick():
    befehl = ba.befehl_erkennen("kannst du auf den Start Button oben rechts klicken")
    assert befehl["art"] == "links" and befehl["ziel"].endswith("oben rechts")
    assert ba.befehl_erkennen("kannst du auf den Papierkorb rechts klicken")["art"] == "rechts"


def test_erster_link_nach_art(bildschirm):
    bildschirm["elemente"] = [
        _el("Suche", art="Edit", x=100, y=20, w=600),
        _el("Wikipedia - Photosynthese", art="Hyperlink", x=100, y=200, w=400),
        _el("Spektrum - Photosynthese", art="Hyperlink", x=100, y=300, w=400),
    ]
    ergebnis = asyncio.run(ba.klicken("den ersten Link"))
    assert ergebnis["geklickt"].startswith("Wikipedia")
    ergebnis = asyncio.run(ba.klicken("den zweiten Link"))
    assert ergebnis["geklickt"].startswith("Spektrum")


def test_nur_einer_im_vordergrundfenster_wird_genommen(bildschirm):
    bildschirm["fenster"] = {"x": 0, "y": 0, "w": 800, "h": 600}
    bildschirm["elemente"] = [_el("Speichern", x=100, y=100), _el("Speichern", x=1200, y=700)]
    ergebnis = asyncio.run(ba.klicken("Speichern"))
    assert ergebnis["erkannt_per"] == "fenster"
    assert bildschirm["geklickt"] == [(140, 115, "left", 1)]


def test_telegram_stellt_die_rueckfrage(monkeypatch):
    dienst = ts.TelegramService()

    async def klicken(ziel, art="links", fenster=""):
        return {"error": "\"Anmelden\" sehe ich 2-mal. Welches meinst du?\n1. Anmelden (Link, oben rechts)\n2. Anmelden (Knopf, Mitte)", "mehrdeutig": True}

    monkeypatch.setattr(ba, "klicken", klicken)
    monkeypatch.setattr(dienst, "_direkt_loggen", lambda *a, **k: None)
    antwort = asyncio.run(dienst._schnellweg("klick auf Anmelden", None))
    assert antwort.startswith("\"Anmelden\" sehe ich 2-mal")


def _zeile(text, x, y, wortbreite=60):
    woerter = [{"n": w, "x": x + i * (wortbreite + 8), "y": y, "w": wortbreite, "h": 20} for i, w in enumerate(text.split())]
    return ba.Element(name=text, art="Text", x=x, y=y, w=len(woerter) * (wortbreite + 8), h=20, quelle="text", extra={"woerter": woerter})


def test_fenster_im_hintergrund_wird_ueber_alle_bildschirme_gefunden(bildschirm, monkeypatch):
    bildschirm["fenster"] = {"x": 0, "y": 0, "w": 600, "h": 400}
    bildschirm["elemente"] = [_el("Start", x=200, y=1040, quelle="taskleiste")]
    aufrufe = []

    def texte(bereich):
        aufrufe.append(bereich)
        if bereich is None:
            return [_zeile("Abbrechen Start", 1500, 300), _zeile("Bitte klick auf den Start Button", 50, 100), _zeile("Das Spiel hat einen grossen Start und ein Ziel", 50, 200)]
        return []

    monkeypatch.setattr(ba, "texte", texte)
    ergebnis = asyncio.run(ba.klicken("den Start Button"))
    assert None in aufrufe
    assert ergebnis["erkannt_per"] == "bildschirm"
    x, y = bildschirm["geklickt"][0][:2]
    assert x > 1500 and 290 <= y <= 330


def test_befehlszeile_ist_kein_ziel():
    zeile = _zeile("Klick auf den Start Button", 50, 100)
    assert ba.kandidaten("den Start Button", [], [zeile]) == []
    assert ba.kandidaten("Hier klicken", [], [_zeile("Hier klicken", 50, 100)])


def test_vordergrund_pruefung_zerstoert_andere_fensterfunktionen_nicht():
    pygetwindow = pytest.importorskip("pygetwindow")
    from app.services.mini_jon_agent import foreground

    foreground()
    import ctypes

    assert ctypes.windll.user32.GetWindowRect.argtypes is None
    assert isinstance(pygetwindow.getAllTitles(), list)
