from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.services import ausloeser_service as modul
from app.services.ausloeser_service import AusloeserFehler, AusloeserService

WURZEL = Path(__file__).resolve().parents[2]
SPIEL = WURZEL / "backend" / "app" / "static" / "katzenhof.html"
MANIFEST = WURZEL / "spiele" / "KATZENHOF" / "jon-spiele.json"
ZEITKARTE = WURZEL / "frontend" / "src" / "components" / "ZeitCard.tsx"
EINSTELLUNGEN = WURZEL / "frontend" / "src" / "components" / "SettingsMenu.tsx"


@pytest.fixture()
def dienst(tmp_path, monkeypatch):
    monkeypatch.setattr(modul, "STORE", tmp_path / "ausloeser.json")
    return AusloeserService()


def test_taeglicher_ausloeser_wird_faellig(dienst):
    jetzt = datetime.now()
    vorhin = (jetzt - timedelta(minutes=5)).strftime("%H:%M")
    dienst.anlegen("taeglich", "Mach mir eine Wetterzusammenfassung", zeit=vorhin)
    faellig = dienst.faellige()
    assert len(faellig) == 1
    assert "Wetter" in faellig[0][1]


def test_taeglicher_ausloeser_wartet_auf_seine_zeit(dienst):
    spaeter = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
    dienst.anlegen("taeglich", "Abendrunde drehen", zeit=spaeter)
    assert dienst.faellige() == []


def test_taeglicher_ausloeser_nur_an_seinen_tagen(dienst):
    mittwoch = datetime(2026, 9, 16, 9, 0)
    am_tag = {"zeit": "08:30", "tage": [2], "zuletzt": 0.0}
    am_anderen = {"zeit": "08:30", "tage": [3], "zuletzt": 0.0}
    assert dienst._faellig_taeglich(am_tag, mittwoch) is True
    assert dienst._faellig_taeglich(am_anderen, mittwoch) is False


def test_taeglicher_ausloeser_wird_nach_mitternacht_nachgeholt(dienst):
    kurz_nach_zwoelf = datetime(2026, 9, 16, 0, 20)
    regel = {"zeit": "23:50", "tage": [], "zuletzt": 0.0}
    assert dienst._faellig_taeglich(regel, kurz_nach_zwoelf) is True
    regel["zuletzt"] = datetime(2026, 9, 15, 23, 51).timestamp()
    assert dienst._faellig_taeglich(regel, kurz_nach_zwoelf) is False


def test_verpasster_ausloeser_verfaellt_nach_sechs_stunden(dienst):
    spaet = datetime(2026, 9, 16, 18, 0)
    regel = {"zeit": "07:00", "tage": [], "zuletzt": 0.0}
    assert dienst._faellig_taeglich(regel, spaet) is False


def test_zeit_muss_stimmen(dienst):
    with pytest.raises(AusloeserFehler):
        dienst.anlegen("taeglich", "Kaputt", zeit="25:70")
    with pytest.raises(AusloeserFehler):
        dienst.anlegen("taeglich", "Ohne Zeit")


def test_intervall_braucht_mindestens_fuenf_minuten(dienst):
    with pytest.raises(AusloeserFehler):
        dienst.anlegen("intervall", "Zu oft", minuten=1)
    regel = dienst.anlegen("intervall", "Alle zehn Minuten", minuten=10)
    assert "10 Minuten" in regel["beschreibung"]


def test_intervall_feuert_erst_nach_ablauf(dienst):
    dienst.anlegen("intervall", "Postfach ansehen", minuten=5)
    assert len(dienst.faellige()) == 1
    dienst._regeln[0]["zuletzt"] = time.time()
    assert dienst.faellige() == []


def test_ordner_meldet_nur_neue_dateien(dienst, tmp_path):
    ordner = tmp_path / "eingang"
    ordner.mkdir()
    (ordner / "alt.pdf").write_text("alt", encoding="utf-8")
    dienst.anlegen(
        "ordner", "Sortier das ein", ordner=str(ordner), muster="*.pdf"
    )
    assert dienst.faellige() == []

    (ordner / "neu.pdf").write_text("neu", encoding="utf-8")
    (ordner / "egal.txt").write_text("egal", encoding="utf-8")
    faellig = dienst.faellige()
    assert len(faellig) == 1
    assert "neu.pdf" in faellig[0][1]
    assert dienst.faellige() == []


def test_ordner_muss_es_geben(dienst, tmp_path):
    with pytest.raises(AusloeserFehler):
        dienst.anlegen("ordner", "Nichts da", ordner=str(tmp_path / "fehlt"))


def test_start_ausloeser_nur_beim_start(dienst):
    dienst.anlegen("start", "Sag guten Morgen")
    assert dienst.faellige() == []
    assert len(dienst.faellige(start=True)) == 1


def test_wochentage_aus_worten():
    assert modul.tage_lesen("werktags") == [0, 1, 2, 3, 4]
    assert modul.tage_lesen("mo,mi,fr") == [0, 2, 4]
    assert modul.tage_lesen("Sonntag") == [6]
    assert modul.tage_lesen("") == []


def test_ausschalten_stoppt_den_ausloeser(dienst):
    vorhin = (datetime.now() - timedelta(minutes=2)).strftime("%H:%M")
    regel = dienst.anlegen("taeglich", "Etwas tun", zeit=vorhin)
    dienst.schalten(regel["id"], False)
    assert dienst.faellige() == []
    dienst.schalten(regel["id"], True)
    assert len(dienst.faellige()) == 1


def test_loeschen_entfernt_den_ausloeser(dienst):
    regel = dienst.anlegen("intervall", "Weg damit", minuten=30)
    dienst.loeschen(regel["id"])
    assert dienst.liste()["ausloeser"] == []
    with pytest.raises(AusloeserFehler):
        dienst.loeschen(regel["id"])


def test_pruefen_legt_eine_aufgabe_an(dienst, monkeypatch):
    angelegt: list[dict] = []

    class Fake:
        def anlegen(self, auftrag, **rest):
            angelegt.append({"auftrag": auftrag, **rest})
            return {"id": 7, "titel": rest.get("titel", "")}

    monkeypatch.setattr(
        "app.services.aufgaben_service.get_aufgaben_service", lambda: Fake()
    )
    vorhin = (datetime.now() - timedelta(minutes=1)).strftime("%H:%M")
    dienst.anlegen("taeglich", "Rechnungen sortieren", zeit=vorhin, budget=25)
    ergebnis = dienst.pruefen()
    assert ergebnis["anzahl"] == 1
    assert angelegt[0]["auftrag"] == "Rechnungen sortieren"
    assert angelegt[0]["budget_minuten"] == 25
    assert angelegt[0]["quelle"] == "ausloeser"
    assert dienst.pruefen()["anzahl"] == 0


def test_beim_start_laeuft_nur_einmal(dienst, monkeypatch):
    monkeypatch.setattr(
        "app.services.aufgaben_service.get_aufgaben_service",
        lambda: type("F", (), {"anlegen": lambda self, auftrag, **rest: {"id": 1}})(),
    )
    dienst.anlegen("start", "Zusammenfassung vom Vortag")
    assert dienst.beim_start()["anzahl"] == 1
    assert dienst.beim_start()["anzahl"] == 0


def test_ausloeser_ueberleben_den_neustart(dienst, tmp_path):
    dienst.anlegen("intervall", "Bleib erhalten", minuten=45)
    zweiter = AusloeserService()
    assert len(zweiter.liste()["ausloeser"]) == 1
    assert zweiter.liste()["ausloeser"][0]["auftrag"] == "Bleib erhalten"


def test_werkzeug_legt_an_und_listet(dienst, monkeypatch):
    from app.services.werkzeug_register import finden, laden

    laden()
    monkeypatch.setattr(modul, "get_ausloeser_service", lambda: dienst)
    funktion = finden("ausloeser")
    assert funktion is not None
    daten = json.loads(
        funktion(
            None,
            {
                "aktion": "anlegen",
                "art": "intervall",
                "auftrag": "Schau in den Kalender",
                "minuten": 30,
            },
            "ausloeser",
        )
    )
    assert daten["art"] == "intervall"
    liste = json.loads(funktion(None, {"aktion": "liste"}, "ausloeser"))
    assert len(liste["ausloeser"]) == 1


def test_werkzeug_meldet_fehler_verstaendlich(dienst, monkeypatch):
    from app.services.werkzeug_register import finden, laden

    laden()
    monkeypatch.setattr(modul, "get_ausloeser_service", lambda: dienst)
    daten = json.loads(
        finden("ausloeser")(
            None, {"aktion": "anlegen", "art": "taeglich", "auftrag": "Tu etwas Sinnvolles"}, "ausloeser"
        )
    )
    assert "zeit" in daten["error"].lower()


def test_ausloeser_und_bericht_sind_angemeldet():
    from app.services.tools import ToolBox, werkzeugnamen

    namen = werkzeugnamen()
    assert "ausloeser" in namen
    assert "bericht" in namen
    schema = {t["function"]["name"]: t for t in ToolBox()._eigene_tools()}
    felder = schema["ausloeser"]["function"]["parameters"]["properties"]
    for feld in ("art", "auftrag", "zeit", "minuten", "ordner"):
        assert feld in felder


def test_aufgabenschlange_ist_ab_werk_an():
    from app.services.settings_service import DEFAULTS

    assert DEFAULTS["aufgaben_enabled"] is True


def test_datei_erstellen_laesst_sich_zuruecknehmen():
    from app.services.rueckgaengig_service import UMKEHRBAR

    assert "datei_erstellen" in UMKEHRBAR


def test_katzenhof_liegt_bereit():
    text = SPIEL.read_text(encoding="utf-8")
    assert "Katzenhof" in text
    assert "requestAnimationFrame" in text
    for stueck in ("hofBauen", "katzeHolen", "schlafen", "bauen", "jonSkripte" if False else "SCHRITTE"):
        assert stueck in text
    daten = json.loads(MANIFEST.read_text(encoding="utf-8"))
    spiel = daten["spiele"][0]
    assert spiel["id"] == "katzenhof"
    assert spiel["typ"] == "web"
    assert spiel["pfad"] == "/katzenhof"


def test_das_alte_cozy_spiel_ist_nicht_mehr_in_der_sammlung():
    assert not (WURZEL / "spiele" / "HARMONIE" / "jon-spiele.json").exists()
    konfig = json.loads(
        (WURZEL / "frontend" / "installer.config.json").read_text(encoding="utf-8")
    )
    ziele = [e.get("to") for e in konfig.get("extraResources", [])]
    assert "KATZENHOF" in ziele
    assert "HARMONIE" not in ziele


def test_katzenhof_wird_ausgeliefert():
    text = (WURZEL / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert '"katzenhof.html"' in text
    assert '@app.get("/katzenhof")' in text


def test_zeitkarte_ist_eine_uhr_fuer_alle_drei_arten():
    text = ZEITKARTE.read_text(encoding="utf-8")
    for stueck in ("Timer", "Wecker", "Stoppuhr"):
        assert f'titel: "{stueck}"' in text
    assert "zeitPause" in text and "zeitStoppen" in text
    assert "zeitAnpassen" in text and "zeitNeustart" in text and "zeitRuhe" in text
    assert "ton_pc" in text


def test_zeitkarte_wird_im_chat_angezeigt():
    text = (WURZEL / "frontend" / "src" / "lib" / "karten.ts").read_text(
        encoding="utf-8"
    )
    assert '"zeit",' in text


def test_zeitwerkzeuge_erzeugen_eine_karte():
    from app.services.chat_service import CARD_TOOLS, card_payload
    from app.services.tools import ToolBox
    from app.services.zeit_service import get_zeit_service

    for name in ("start_timer", "start_stopwatch", "set_alarm", "list_alarms"):
        assert CARD_TOOLS[name] == "zeit"
    for name in ("adjust_timer", "control_timer"):
        assert CARD_TOOLS[name] == "zeit"
    get_zeit_service().stoppen()
    try:
        ergebnis = ToolBox()._zeit("set_alarm", {"label": "Aufstehen", "time": "07:30"})
        karte = card_payload("set_alarm", ergebnis)
        assert karte["kind"] == "zeit"
        uhr = karte["data"]["uhren"][0]
        assert uhr["art"] == "wecker"
        assert uhr["titel"] == "Aufstehen"
    finally:
        get_zeit_service().stoppen()


def test_zeitstand_nennt_den_messzeitpunkt():
    from app.services.zeit_service import ZeitService

    dienst = ZeitService()
    uhr = dienst.starten("timer", 60, "Probe")
    assert uhr["gemessen"] > 0
    assert uhr["rest"] <= 60
    dienst.stoppen(uhr["id"])


def test_einstellungen_haben_einen_einfachen_modus():
    text = EINSTELLUNGEN.read_text(encoding="utf-8")
    assert "EinfachContext" in text
    assert "jon_einstellungen_stufe" in text
    assert text.count("<Profi>") == text.count("</Profi>") == 2


def test_jon_laeuft_ueberall_im_terminal():
    from app.services.terminal_service import stand

    text = (WURZEL / "docs" / "CLI.md").read_text(encoding="utf-8")
    for ort in ("Windows CMD", "PowerShell", "macOS Terminal", "Linux", "VS Code"):
        assert ort in text
    assert "Du (code)>" in text
    assert stand()["befehl"].endswith("jon.cmd") or stand()["befehl"].endswith("jon")


def test_einstellungen_richten_das_terminal_ein():
    text = EINSTELLUNGEN.read_text(encoding="utf-8")
    assert "Jon im Terminal" in text
    assert "terminalEinrichten" in text and "terminalEntfernen" in text


def test_downloads_landen_im_player():
    dl = (WURZEL / "backend" / "app" / "services" / "downloader_service.py").read_text(
        encoding="utf-8"
    )
    assert "_in_die_mediathek" in dl
    assert dl.count("_in_die_mediathek(") >= 3
    spieler = (WURZEL / "frontend" / "src" / "components" / "Player.tsx").read_text(
        encoding="utf-8"
    )
    assert "mediathekDateiUrl" in spieler and "mediathekLoeschen" in spieler
    app_text = (WURZEL / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert 'label: "Player"' in app_text


def test_die_3d_modelle_schauen_dich_an():
    text = (WURZEL / "frontend" / "electron" / "pet3d.js").read_text(encoding="utf-8")
    assert "kopfGruppe" in text
    assert text.count("kopfGruppe(kopf") == 2
    assert "const auge = (dx, dy, dz)" in text
    assert text.count("scaling(0.042, 0.042 * glanz, 0.03)") == 1
