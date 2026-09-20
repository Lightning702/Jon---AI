from __future__ import annotations

import base64
import json
import re
import threading
import time
from pathlib import Path

import pytest

from app.services.browser import privatbruecke
from app.services.browser.manager import BrowserFehler

WURZEL = Path(__file__).resolve().parents[2]
SEITE = WURZEL / "frontend" / "electron" / "private-browser.html"
PRELOAD = WURZEL / "frontend" / "electron" / "privatePreload.cjs"
MAIN = WURZEL / "frontend" / "electron" / "main.cjs"


@pytest.fixture(autouse=True)
def sauber():
    privatbruecke.zuruecksetzen()
    yield
    privatbruecke.zuruecksetzen()


def _im_hintergrund(op, args, ablage, wartezeit=5.0):
    def lauf():
        try:
            ablage["ergebnis"] = privatbruecke.aufrufen(op, args, wartezeit=wartezeit)
        except Exception as exc:
            ablage["fehler"] = exc

    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    return faden


def _warten_auf_auftrag(grenze=3.0):
    ende = time.time() + grenze
    while time.time() < ende:
        auftrag = privatbruecke.abholen()
        if auftrag is not None:
            return auftrag
        time.sleep(0.02)
    return None


def test_auftrag_geht_hin_und_ergebnis_zurueck():
    ablage: dict = {}
    faden = _im_hintergrund("goto", {"url": "https://example.com"}, ablage)
    auftrag = _warten_auf_auftrag()
    assert auftrag is not None
    assert auftrag["op"] == "goto"
    assert auftrag["args"]["url"] == "https://example.com"
    assert privatbruecke.antworten(auftrag["id"], True, {"url": "https://example.com"})
    faden.join(timeout=3)
    assert ablage["ergebnis"]["url"] == "https://example.com"


def test_fehler_vom_browser_wird_zum_browserfehler():
    ablage: dict = {}
    faden = _im_hintergrund("click", {"element": "e9"}, ablage)
    auftrag = _warten_auf_auftrag()
    privatbruecke.antworten(auftrag["id"], False, {}, "Element weg")
    faden.join(timeout=3)
    assert isinstance(ablage["fehler"], BrowserFehler)
    assert "Element weg" in str(ablage["fehler"])


def test_ohne_antwort_laeuft_der_auftrag_in_den_timeout():
    ablage: dict = {}
    faden = _im_hintergrund("read", {}, ablage, wartezeit=0.3)
    faden.join(timeout=3)
    assert isinstance(ablage["fehler"], BrowserFehler)
    assert "nicht geantwortet" in str(ablage["fehler"])


def test_unbekannte_aktion_wird_abgelehnt():
    with pytest.raises(BrowserFehler) as info:
        privatbruecke.aufrufen("tanzen", {})
    assert "tanzen" in str(info.value)


def test_verbindung_laeuft_ab():
    assert privatbruecke.verbunden() is False
    privatbruecke.melden(True)
    assert privatbruecke.verbunden() is True
    assert privatbruecke.fenster_offen() is True


def test_die_verbindung_haelt_laenger_als_eine_abfragerunde():
    assert privatbruecke.FRISCH > 30.0


def test_motor_laesst_sich_auf_playwright_stellen(monkeypatch):
    from app.services.settings_service import get_settings_service

    privatbruecke.melden(True)
    dienst = get_settings_service()
    dienst.update({"browser_motor": "playwright"})
    assert privatbruecke.aktiv() is False
    dienst.update({"browser_motor": "privat"})
    assert privatbruecke.aktiv() is True


def test_get_manager_nimmt_den_privaten_browser(monkeypatch):
    from app.services.browser import manager as manager_modul

    monkeypatch.setattr(privatbruecke, "aktiv", lambda: True)
    gewaehlt = manager_modul.get_manager("probe")
    assert isinstance(gewaehlt, privatbruecke.PrivatManager)
    monkeypatch.setattr(privatbruecke, "aktiv", lambda: False)
    assert isinstance(manager_modul.get_manager("probe"), manager_modul.BrowserManager)


def test_manager_liefert_das_gewohnte_format():
    manager = privatbruecke.manager("probe")
    ablage: dict = {}

    def lauf():
        ablage["ergebnis"] = manager.aufrufen("read", {})

    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    auftrag = _warten_auf_auftrag()
    privatbruecke.antworten(auftrag["id"], True, {"url": "https://x.de", "titel": "X"})
    faden.join(timeout=3)
    assert ablage["ergebnis"]["ok"] is True
    assert ablage["ergebnis"]["titel"] == "X"


def test_manager_meldet_fehler_statt_zu_werfen():
    manager = privatbruecke.manager("probe")
    ablage: dict = {}

    def lauf():
        ablage["ergebnis"] = manager.aufrufen("upload", {"pfad": "x"})

    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    faden.join(timeout=3)
    assert ablage["ergebnis"]["ok"] is False
    assert "upload" in ablage["ergebnis"]["fehler"]


def test_status_sagt_ob_das_fenster_offen_ist():
    privatbruecke.melden(True)
    manager = privatbruecke.manager("probe")
    ablage: dict = {}

    def lauf():
        ablage["ergebnis"] = manager.aufrufen("status", {})

    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    auftrag = _warten_auf_auftrag()
    privatbruecke.antworten(auftrag["id"], True, {"url": "https://x.de", "tabs": []})
    faden.join(timeout=3)
    assert ablage["ergebnis"]["aktiv"] is True


def test_screenshot_wird_zur_datei(tmp_path, monkeypatch):
    punkt = base64.b64encode(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
            "IQAAAABJRU5ErkJggg=="
        )
    ).decode()
    monkeypatch.setattr("app.core.config.DATA_DIR", tmp_path)
    manager = privatbruecke.manager("probe")
    ablage: dict = {}

    def lauf():
        ablage["ergebnis"] = manager.aufrufen("screenshot", {})

    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    auftrag = _warten_auf_auftrag()
    privatbruecke.antworten(
        auftrag["id"], True, {"bild": f"data:image/png;base64,{punkt}"}
    )
    faden.join(timeout=3)
    datei = Path(ablage["ergebnis"]["datei"])
    assert datei.is_file()
    assert datei.read_bytes().startswith(b"\x89PNG")


def test_trennen_weckt_wartende_auftraege():
    ablage: dict = {}
    faden = _im_hintergrund("read", {}, ablage, wartezeit=5.0)
    _warten_auf_auftrag()
    privatbruecke.zuruecksetzen()
    faden.join(timeout=3)
    assert isinstance(ablage["fehler"], BrowserFehler)
    assert "getrennt" in str(ablage["fehler"])


def test_skripte_enthalten_die_leselogik():
    daten = privatbruecke.skripte()
    for schluessel in ("elemente", "seite", "beschreibung", "zustimmung"):
        assert daten[schluessel].strip().startswith("(")
    assert daten["max_elemente"] > 0


def test_route_reicht_auftrag_und_ergebnis_durch():
    from fastapi.testclient import TestClient

    from app.main import create_app

    ablage: dict = {}
    with TestClient(create_app()) as client:
        antwort = client.get("/api/browser/privat/auftrag?warten=0&fenster=1")
        assert antwort.status_code == 200
        assert antwort.json()["auftrag"] is None
        assert privatbruecke.verbunden() is True

        faden = _im_hintergrund("goto", {"url": "https://jon.test"}, ablage, 8.0)
        geholt = client.get("/api/browser/privat/auftrag?warten=5&fenster=1").json()
        auftrag = geholt["auftrag"]
        assert auftrag["op"] == "goto"
        assert auftrag["skripte"]["elemente"].strip().startswith("(")

        client.post(
            "/api/browser/privat/ergebnis",
            json={
                "id": auftrag["id"],
                "ok": True,
                "daten": {"url": "https://jon.test", "titel": "Jon"},
                "fenster": True,
            },
        )
        faden.join(timeout=5)
        assert ablage["ergebnis"]["titel"] == "Jon"

        stand = client.get("/api/browser/privat/stand").json()
        assert stand["verbunden"] is True
        assert stand["fenster"] is True


def test_browser_werkzeug_laeuft_ueber_den_privaten_browser(monkeypatch):
    from app.services.browser.werkzeuge import ausfuehren

    monkeypatch.setattr(privatbruecke, "aktiv", lambda: True)
    privatbruecke.melden(True)
    ablage: dict = {}

    def lauf():
        ablage["ergebnis"] = ausfuehren("goto", {"url": "https://beispiel.de"})

    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    auftrag = _warten_auf_auftrag()
    assert auftrag is not None and auftrag["op"] == "goto"
    privatbruecke.antworten(
        auftrag["id"],
        True,
        {
            "url": "https://beispiel.de",
            "titel": "Beispiel",
            "seitentext": "Hallo Welt",
            "interaktive_elemente": [],
            "tabs": [],
            "tab": "t1",
        },
    )
    faden.join(timeout=5)
    assert ablage["ergebnis"]["ok"] is True
    assert ablage["ergebnis"]["titel"] == "Beispiel"


def test_browserwahl_oeffnet_im_privaten_browser(monkeypatch):
    from app.services import browserwahl

    monkeypatch.setattr(privatbruecke, "aktiv", lambda: True)
    monkeypatch.setattr(browserwahl, "wahl", lambda: browserwahl.JON)
    privatbruecke.melden(True)
    ablage: dict = {}

    def lauf():
        ablage["ergebnis"] = browserwahl.oeffnen("youtube.com")

    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    auftrag = _warten_auf_auftrag()
    assert auftrag["op"] == "goto"
    assert auftrag["args"]["url"] == "https://youtube.com"
    privatbruecke.antworten(
        auftrag["id"], True, {"url": "https://youtube.com", "titel": "YouTube"}
    )
    faden.join(timeout=5)
    assert ablage["ergebnis"]["ok"] is True


def test_die_browserseite_fuehrt_auftraege_aus():
    text = SEITE.read_text(encoding="utf-8")
    assert "window.jonPrivat.onAuftrag" in text
    assert "jonAuftragAusfuehren" in text
    assert "jonSchnappschuss" in text
    for op in ("goto", "read", "click", "fill", "press", "select", "scroll", "tab_new"):
        assert f"op === '{op}'" in text, op
    assert "capturePage" in text


def test_preload_reicht_auftraege_durch():
    text = PRELOAD.read_text(encoding="utf-8")
    assert "private:auftrag" in text
    assert "private:ergebnis" in text


def test_electron_holt_auftraege_vom_backend():
    text = MAIN.read_text(encoding="utf-8")
    assert "/browser/privat/auftrag" in text
    assert "/browser/privat/ergebnis" in text
    assert "privatSchleife" in text
    assert 'ipcMain.handle("private:ergebnis"' in text


def test_die_browserseite_bleibt_gueltiges_javascript():
    text = SEITE.read_text(encoding="utf-8")
    bloecke = re.findall(r"<script>(.*?)</script>", text, re.S)
    assert bloecke
    offen = bloecke[-1].count("{") - bloecke[-1].count("}")
    assert offen == 0
    assert json.dumps(bloecke[-1][:10])
