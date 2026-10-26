from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import bildschirm_agent as ba
from app.services import pc_strom
from app.services import telegram_service as ts
from app.services.approval_service import get_approval_service
from app.services.risiko import bewerten as risiko_bewerten


def _el(name, art="Button", x=100, y=100, w=80, h=30, quelle="fenster", wert=""):
    return ba.Element(name=name, art=art, x=x, y=y, w=w, h=h, quelle=quelle, wert=wert)


def test_herunterfahren_wird_erkannt():
    assert pc_strom.erkennen("Fahr den PC herunter") == "herunterfahren"
    assert pc_strom.erkennen("fahre bitte meinen pc runter") == "herunterfahren"
    assert pc_strom.erkennen("PC aus") == "herunterfahren"
    assert pc_strom.erkennen("kannst du den Computer herunterfahren?") == "herunterfahren"
    assert pc_strom.erkennen("Starte den PC neu") == "neustarten"
    assert pc_strom.erkennen("Sperr den PC") == "sperren"
    assert pc_strom.erkennen("doch nicht herunterfahren") == "abbrechen"
    assert pc_strom.erkennen("Energiesparmodus") == "energiesparen"


def test_herunterfahren_nicht_bei_fragen_oder_bedingungen():
    assert pc_strom.erkennen("wie kann ich den PC herunterfahren?") is None
    assert pc_strom.erkennen("wenn der Download fertig ist, fahr den PC runter") is None
    assert pc_strom.erkennen("Fahr mal runter zum Baecker") is None
    assert pc_strom.erkennen("Schalte das Licht aus") is None


def test_vorlauf_aus_text():
    assert pc_strom.vorlauf("fahr den pc in 10 minuten herunter") == 600
    assert pc_strom.vorlauf("fahr den pc in einer stunde runter") == 3600
    assert pc_strom.vorlauf("PC in 45 sekunden aus") == 45
    assert pc_strom.vorlauf("PC aus") == 30
    assert 10 <= pc_strom.vorlauf("fahr den pc um 23:30 uhr herunter") <= 86400


def test_strom_risiko():
    assert risiko_bewerten("pc_strom", {"aktion": "abbrechen"}).risiko == "niedrig"
    assert risiko_bewerten("pc_strom", {"aktion": "herunterfahren", "sekunden": 30}).risiko == "mittel"
    assert risiko_bewerten("pc_strom", {"aktion": "herunterfahren", "sekunden": 0}).risiko == "hoch"
    assert risiko_bewerten("bildschirm_lesen", {}).risiko == "niedrig"


def test_strom_text():
    assert "30 Sekunden" in pc_strom.text({"ok": True, "aktion": "Herunterfahren", "in_sekunden": 30})
    assert "10 Minuten" in pc_strom.text({"ok": True, "aktion": "Neustart", "in_sekunden": 600})
    assert "bleibt an" in pc_strom.text({"ok": True, "aktion": "Abgebrochen"})


def test_exakter_knopf_gewinnt():
    elemente = [
        _el("Registerkarten suchen"),
        _el("Suchen", art="Button", x=400),
        _el("gmail - Suchen", art="TabItem", x=700),
    ]
    liste = ba.kandidaten("Suchen", elemente)
    treffer = ba.eindeutig(liste)
    assert treffer is not None and treffer.name == "Suchen" and treffer.x == 400


def test_fuellwoerter_und_umlaute():
    elemente = [_el("Schließen", x=10), _el("Start", x=300, quelle="taskleiste"), _el("Weiter", x=600)]
    assert ba.eindeutig(ba.kandidaten("den Start Button", elemente)).name == "Start"
    assert ba.eindeutig(ba.kandidaten("schliessen", elemente)).name == "Schließen"
    assert ba.eindeutig(ba.kandidaten("auf weiter", elemente)).name == "Weiter"


def test_feld_bevorzugt_eingabe():
    elemente = [_el("Suche", art="Text", x=10), _el("Suche", art="Edit", x=400, w=300)]
    treffer = ba.eindeutig(ba.kandidaten("Suchfeld Suche", elemente))
    assert treffer is not None and treffer.art == "Edit"


def test_mehrdeutig_bleibt_offen():
    elemente = [_el("Aktualisieren", x=10), _el("Aktualisieren", x=900)]
    assert ba.eindeutig(ba.kandidaten("Aktualisieren", elemente)) is None


def test_ocr_woerter_als_ziel():
    zeile = ba.Element(
        name="Jetzt Start drücken",
        art="Text",
        x=100,
        y=50,
        w=300,
        h=20,
        quelle="text",
        extra={"woerter": [{"n": "Jetzt", "x": 100, "y": 50, "w": 60, "h": 20}, {"n": "Start", "x": 170, "y": 50, "w": 60, "h": 20}, {"n": "drücken", "x": 240, "y": 50, "w": 80, "h": 20}]},
    )
    liste = ba.kandidaten("Start", [], [zeile])
    assert liste and liste[0].name == "Start" and liste[0].mitte == (200, 60)


def test_befehle_aus_text():
    assert ba.befehl_erkennen("Klick auf den Start Button") == {"aktion": "klicken", "ziel": "den Start Button", "art": "links"}
    assert ba.befehl_erkennen("kannst du auf Anmelden klicken")["ziel"] == "Anmelden"
    assert ba.befehl_erkennen("doppelklick auf Papierkorb")["art"] == "doppel"
    assert ba.befehl_erkennen("schreib hallo welt in das Suchfeld") == {"aktion": "eingeben", "ziel": "Suchfeld", "text": "hallo welt"}
    assert ba.befehl_erkennen("klick") is None
    assert ba.befehl_erkennen("schreib eine Mail an Oma") is None


def test_nummer_aus_liste(monkeypatch):
    element = _el("OK", x=50)
    element.nummer = 3
    ba._merken("Fenster", [element])
    gefunden, weg, _ = asyncio.run(ba.finden("3"))
    assert gefunden is element and weg == "liste"


class _FakeTelegram(ts.TelegramService):
    def __init__(self):
        super().__init__()
        self.gesendet: list[dict] = []
        self.geaendert: list[dict] = []
        self.api: list[tuple[str, dict]] = []

    async def _api_antwort(self, method, payload):
        self.api.append((method, payload))
        if method == "sendMessage":
            self.gesendet.append(payload)
            return {"ok": True, "result": {"message_id": len(self.gesendet)}}
        if method == "editMessageText":
            self.geaendert.append(payload)
            return {"ok": True}
        return {"ok": True}


def test_freigabe_mit_knopf_und_rueckfrage(monkeypatch):
    dienst = _FakeTelegram()
    monkeypatch.setattr(ts, "get_settings_service", lambda: type("S", (), {"get": lambda self: {"telegram_chat_id": "42"}})())

    async def ablauf():
        freigaben = get_approval_service()
        kennung = freigaben.create()
        await dienst._freigabe_fragen("42", {"approval_id": kennung, "summary": "Fuehrt einen Befehl aus.", "risiko": "hoch", "args": {"command": "Stop-Computer"}})
        nachricht = dienst.gesendet[-1]
        knopf = nachricht["reply_markup"]["inline_keyboard"][0][0]
        assert knopf["callback_data"] == f"jf:{kennung}:1"
        assert "Stop-Computer" in nachricht["text"]
        assert dienst._offene_freigaben("42")
        warten = asyncio.ensure_future(freigaben.wait(kennung, timeout=5))
        await asyncio.sleep(0)
        await dienst._rueckfrage({"id": "cb1", "data": knopf["callback_data"], "message": {"chat": {"id": 42}}})
        assert await warten is True
        assert dienst.geaendert and "Erlaubt" in dienst.geaendert[-1]["text"]
        assert not dienst._offene_freigaben("42")

    asyncio.run(ablauf())


def test_fremder_chat_darf_nicht_freigeben(monkeypatch):
    dienst = _FakeTelegram()
    monkeypatch.setattr(ts, "get_settings_service", lambda: type("S", (), {"get": lambda self: {"telegram_chat_id": "42"}})())

    async def ablauf():
        freigaben = get_approval_service()
        kennung = freigaben.create()
        await dienst._rueckfrage({"id": "cb2", "data": f"jf:{kennung}:1", "message": {"chat": {"id": 99}}})
        assert kennung in freigaben.offen()
        freigaben.resolve(kennung, False)

    asyncio.run(ablauf())


def test_schnellweg_herunterfahren(monkeypatch):
    dienst = _FakeTelegram()
    aufrufe = []
    monkeypatch.setattr(pc_strom, "ausfuehren", lambda aktion, sekunden=30: aufrufe.append((aktion, sekunden)) or {"ok": True, "aktion": "Herunterfahren", "in_sekunden": sekunden})
    antwort = asyncio.run(dienst._schnellweg("Fahr den PC in 5 Minuten herunter", None))
    assert aufrufe == [("herunterfahren", 300)]
    assert "5 Minuten" in antwort and "/abbrechen" in antwort


def test_schnellweg_klick(monkeypatch):
    dienst = _FakeTelegram()

    async def klicken(ziel, art="links", fenster=""):
        return {"geklickt": "Start (Button)", "position": [10, 10], "erkannt_per": "bedienelement", "fenster": "Spiel", "fenster_gewechselt": True}

    monkeypatch.setattr(ba, "klicken", klicken)
    antwort = asyncio.run(dienst._schnellweg("klick auf den Start Button", None))
    assert "Start (Button)" in antwort and "Spiel" in antwort


def test_schnellweg_klick_nicht_gefunden_geht_ans_modell(monkeypatch):
    dienst = _FakeTelegram()

    async def klicken(ziel, art="links", fenster=""):
        return {"error": "nicht gefunden"}

    monkeypatch.setattr(ba, "klicken", klicken)
    assert asyncio.run(dienst._schnellweg("klick auf Zauberknopf", None)) is None


def test_werkzeuge_im_schema():
    from app.services.tools import ToolBox

    namen = {t["function"]["name"] for t in ToolBox().schema("klick auf start")}
    assert {"bildschirm_lesen", "bildschirm_klicken", "bildschirm_eingeben", "pc_strom"} <= namen


def test_screenshot_liefert_keine_base64(monkeypatch):
    from app.services import tools

    class _Svc:
        def screenshot(self, path=None):
            return {"path": path, "width": 10, "height": 10}

    box = tools.ToolBox()
    monkeypatch.setattr(tools, "SystemService", lambda: _Svc(), raising=False)
    ergebnis = json.loads(asyncio.run(box.execute("screenshot", {})))
    assert "data_url" not in ergebnis


def test_klick_im_genannten_fenster_wird_erkannt():
    assert ba.befehl_erkennen('Klick im Fenster "Jon Klicktest" auf den Start-Knopf') == {"aktion": "klicken", "ziel": "den Start-Knopf", "art": "links", "fenster": "Jon Klicktest"}
    assert ba.befehl_erkennen("klick auf Anmelden im Fenster Chrome") == {"aktion": "klicken", "ziel": "Anmelden", "art": "links", "fenster": "Chrome"}
    assert ba.befehl_erkennen("Im Programm Steam auf Spielen klicken")["fenster"] == "Steam"


def test_blinder_klick_nur_ohne_ziel():
    verben = ("klick", "klick mal", "linksklick")
    assert ts.blind_klick("klick", verben)
    assert ts.blind_klick("klick mal hier", verben)
    assert not ts.blind_klick("klick im fenster spiel auf start", verben)
    assert not ts.blind_klick("klick auf start", verben)


def test_schnellweg_gibt_fenster_weiter(monkeypatch):
    dienst = _FakeTelegram()
    erhalten = {}

    async def klicken(ziel, art="links", fenster=""):
        erhalten.update(ziel=ziel, fenster=fenster)
        return {"geklickt": "Start (Button)", "position": [10, 10], "erkannt_per": "text", "fenster": "Spiel"}

    monkeypatch.setattr(ba, "klicken", klicken)
    antwort = asyncio.run(dienst._schnellweg("Klick im Fenster Spiel auf Start", None))
    assert erhalten == {"ziel": "Start", "fenster": "Spiel"}
    assert "Start (Button)" in antwort


def test_kein_klick_in_sicherheitsfenster(monkeypatch):
    geklickt = []
    monkeypatch.setattr(ba, "finden", lambda ziel, nur_fenster=False: asyncio.sleep(0, (_el("Zulassen", x=500, y=400), "bedienelement", {})))
    monkeypatch.setattr(ba, "fenster_an", lambda x, y: "Windows-Sicherheit")
    from app.services import automation_service

    monkeypatch.setattr(automation_service.AutomationService, "mouse_click", lambda self, *a, **k: geklickt.append(a) or {"clicked_at": [0, 0]})
    ergebnis = asyncio.run(ba.klicken("Zulassen"))
    assert ergebnis.get("sicherheit") and not geklickt
    assert ba.sicherheitsfenster("Benutzerkontensteuerung") and not ba.sicherheitsfenster("Jon Klicktest")


def test_sicherheitsfenster_meldet_sich_im_telegram(monkeypatch):
    dienst = _FakeTelegram()

    async def klicken(ziel, art="links", fenster=""):
        return {"error": "An dieser Stelle liegt das Sicherheitsfenster \"Windows-Sicherheit\". Dort klicke ich nicht selbst, das entscheidest du.", "sicherheit": True}

    monkeypatch.setattr(ba, "klicken", klicken)
    antwort = asyncio.run(dienst._schnellweg("klick auf Zulassen", None))
    assert "Sicherheitsfenster" in antwort


def test_genanntes_fenster_faellt_nie_auf_die_taskleiste_zurueck(monkeypatch):
    start = _el("Start", quelle="taskleiste", x=0, y=740)
    monkeypatch.setattr(ba, "ui_elemente", lambda: {"titel": "Spiel", "fenster": {"x": 0, "y": 0, "w": 400, "h": 300}, "elemente": [_el("Spiel", art="Window"), start]})
    monkeypatch.setattr(ba, "texte", lambda bereich: [])

    async def nichts(*a, **k):
        return None

    monkeypatch.setattr(ba, "per_markierung", nichts)
    monkeypatch.setattr(ba, "per_raster", nichts)
    gefunden, _, _ = asyncio.run(ba.finden("Start", True))
    assert gefunden is None


def test_texterkennung_gewinnt_wenn_bedienelemente_langsam_sind(monkeypatch):
    import threading
    import time

    frei = threading.Event()

    def langsam():
        frei.wait(5)
        return {"titel": "", "fenster": None, "elemente": []}

    monkeypatch.setattr(ba, "ui_elemente", langsam)
    monkeypatch.setattr(ba, "texte", lambda bereich: [_el("Start", art="Text", quelle="text", x=500, y=300)])

    async def ablauf():
        beginn = time.perf_counter()
        ergebnis = await ba.finden("den Start Button")
        dauer = time.perf_counter() - beginn
        frei.set()
        return ergebnis, dauer

    (gefunden, weg, _), dauer = asyncio.run(ablauf())
    assert weg == "text" and gefunden.name == "Start"
    assert dauer < 2.0
