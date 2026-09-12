from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.services.abnahme_service import get_abnahme_service
from app.services.approval_service import (
    laeuft_unbeaufsichtigt,
    unbeaufsichtigt,
    zuruecksetzen,
)
from app.services.aufgaben_service import (
    BRAUCHT_FREIGABE,
    FERTIG,
    GESCHEITERT,
    LAEUFT,
    WARTET,
    get_aufgaben_service,
)
from app.services.hypothese_service import BESTAETIGT, WIDERLEGT, get_hypothese_service
from app.services.vorwaerts_service import get_vorwaerts_service


@pytest.fixture()
def dienst():
    d = get_aufgaben_service()
    for aufgabe in d.liste(limit=200):
        d._setzen(aufgabe["id"], zustand="abgeraeumt")
    d._laeuft = ""
    return d


def test_aufgabe_landet_in_der_schlange(dienst):
    aufgabe = dienst.anlegen("Raeum den Downloads-Ordner auf", budget_minuten=5)
    assert aufgabe["zustand"] == WARTET
    assert aufgabe["budget_minuten"] == 5
    assert aufgabe["protokoll"][0]["text"] == "Aufgabe angenommen."
    assert dienst.naechste()["id"] == aufgabe["id"]


def test_zu_kurze_aufgabe_wird_abgelehnt(dienst):
    assert dienst.anlegen("hm").get("error")


def test_prioritaet_entscheidet_die_reihenfolge(dienst):
    dienst.anlegen("Unwichtiges erledigen", prioritaet=9)
    dringend = dienst.anlegen("Dringend erledigen", prioritaet=1)
    assert dienst.naechste()["id"] == dringend["id"]


def test_protokoll_waechst_mit(dienst):
    aufgabe = dienst.anlegen("Etwas tun")
    dienst.protokollieren(aufgabe["id"], "Erster Schritt", "schritt")
    dienst.protokollieren(aufgabe["id"], "Zweiter Schritt", "schritt")
    stand = dienst.holen(aufgabe["id"])
    assert [z["text"] for z in stand["protokoll"][-2:]] == [
        "Erster Schritt",
        "Zweiter Schritt",
    ]


def test_pausieren_und_fortsetzen(dienst):
    aufgabe = dienst.anlegen("Etwas Laengeres tun")
    assert dienst.pausieren(aufgabe["id"])["zustand"] == "pausiert"
    assert dienst.naechste() is None
    assert dienst.fortsetzen(aufgabe["id"])["zustand"] == WARTET
    assert dienst.naechste()["id"] == aufgabe["id"]


def test_neustart_nimmt_laufende_aufgaben_wieder_auf(dienst):
    aufgabe = dienst.anlegen("Wird unterbrochen")
    dienst._setzen(aufgabe["id"], zustand=LAEUFT)
    assert dienst.unterbrochene_aufnehmen() >= 1
    assert dienst.holen(aufgabe["id"])["zustand"] == WARTET


def test_unbeaufsichtigt_ist_ein_eigener_kontext():
    assert laeuft_unbeaufsichtigt() is False
    marke = unbeaufsichtigt(True)
    assert laeuft_unbeaufsichtigt() is True
    zuruecksetzen(marke)
    assert laeuft_unbeaufsichtigt() is False


def test_aufgabe_parkt_statt_zu_blockieren(dienst, monkeypatch):
    aufgabe = dienst.anlegen("Loesch den alten Kram")

    async def _entwerfen(auftrag, ziel="", kontext="", quelle="app"):
        return {"id": "p1", "schritte": [{"titel": "Loeschen"}], "zustand": "entworfen"}

    async def _ausfuehren(kennung, bestaetigt=False, quelle="app"):
        yield {
            "art": "freigabe",
            "text": "Riskant",
            "schritte": ["Alles loeschen"],
            "werkzeuge": ["delete_path"],
        }

    from app.services import planer_service

    planer = planer_service.get_planer_service()
    monkeypatch.setattr(planer, "entwerfen", _entwerfen)
    monkeypatch.setattr(planer, "ausfuehren", _ausfuehren)
    monkeypatch.setattr(planer, "holen", lambda k: None)

    ergebnis = asyncio.run(dienst.lauf(aufgabe["id"]))
    assert ergebnis["freigabe"] is True
    stand = dienst.holen(aufgabe["id"])
    assert stand["zustand"] == BRAUCHT_FREIGABE
    assert stand["offene_freigabe"]["werkzeuge"] == ["delete_path"]
    assert any("Freigabe" in z["text"] for z in stand["protokoll"])


def test_freigabe_setzt_die_aufgabe_fort(dienst):
    aufgabe = dienst.anlegen("Wartet auf Freigabe")
    dienst._setzen(aufgabe["id"], zustand=BRAUCHT_FREIGABE)
    weiter = dienst.freigeben(aufgabe["id"], True)
    assert weiter["zustand"] == WARTET
    assert weiter["unbeaufsichtigt"] is False


def test_verweigerte_freigabe_beendet_die_aufgabe(dienst):
    aufgabe = dienst.anlegen("Wartet auf Freigabe")
    dienst._setzen(aufgabe["id"], zustand=BRAUCHT_FREIGABE)
    aus = dienst.freigeben(aufgabe["id"], False)
    assert aus["zustand"] == GESCHEITERT
    assert "verweigert" in aus["fehler"]


def test_aufgabe_laeuft_durch_und_wird_abgenommen(dienst, monkeypatch):
    aufgabe = dienst.anlegen("Schreib eine Notiz")

    async def _entwerfen(auftrag, ziel="", kontext="", quelle="app"):
        return {
            "id": "p2",
            "schritte": [{"titel": "Notiz schreiben", "zustand": "offen"}],
            "zustand": "entworfen",
            "fortschritt": 0.0,
        }

    async def _ausfuehren(kennung, bestaetigt=False, quelle="app"):
        yield {"art": "schritt", "titel": "Notiz schreiben", "status": "fertig"}
        yield {"art": "ende", "ok": True, "text": "Notiz liegt bereit."}

    async def _abnahme(auftrag, plan="", ergebnis="", seit=0.0):
        return {"fertig": True, "note": 5, "fehlt": "", "quelle": "test"}

    from app.services import planer_service

    planer = planer_service.get_planer_service()
    monkeypatch.setattr(planer, "entwerfen", _entwerfen)
    monkeypatch.setattr(planer, "ausfuehren", _ausfuehren)
    monkeypatch.setattr(planer, "holen", lambda k: {"fortschritt": 1.0, "zustand": "fertig"})
    monkeypatch.setattr(get_abnahme_service(), "pruefen", _abnahme)

    ergebnis = asyncio.run(dienst.lauf(aufgabe["id"]))
    assert ergebnis["ok"] is True
    stand = dienst.holen(aufgabe["id"])
    assert stand["zustand"] == FERTIG
    assert stand["ergebnis"] == "Notiz liegt bereit."
    assert stand["abnahme"]["note"] == 5


def test_abnahme_kann_fertig_verhindern(dienst, monkeypatch):
    aufgabe = dienst.anlegen("Halbe Sache abliefern")

    async def _entwerfen(auftrag, ziel="", kontext="", quelle="app"):
        return {"id": "p3", "schritte": [], "zustand": "entworfen", "fortschritt": 0.0}

    async def _ausfuehren(kennung, bestaetigt=False, quelle="app"):
        yield {"art": "ende", "ok": True, "text": "Angeblich fertig."}

    async def _abnahme(auftrag, plan="", ergebnis="", seit=0.0):
        return {"fertig": False, "fehlt": "Die Datei ist leer.", "note": 2}

    from app.services import planer_service

    planer = planer_service.get_planer_service()
    monkeypatch.setattr(planer, "entwerfen", _entwerfen)
    monkeypatch.setattr(planer, "ausfuehren", _ausfuehren)
    monkeypatch.setattr(planer, "holen", lambda k: None)
    monkeypatch.setattr(get_abnahme_service(), "pruefen", _abnahme)

    ergebnis = asyncio.run(dienst.lauf(aufgabe["id"]))
    assert ergebnis["ok"] is False
    stand = dienst.holen(aufgabe["id"])
    assert "leer" in stand["fehler"]
    assert stand["zustand"] == WARTET


def test_aufgabe_gibt_nach_drei_laeufen_auf(dienst, monkeypatch):
    aufgabe = dienst.anlegen("Geht nie")

    async def _entwerfen(auftrag, ziel="", kontext="", quelle="app"):
        return {"error": "Kein Plan moeglich."}

    from app.services import planer_service

    monkeypatch.setattr(planer_service.get_planer_service(), "entwerfen", _entwerfen)
    for _ in range(3):
        dienst._laeuft = ""
        asyncio.run(dienst.lauf(aufgabe["id"]))
        if dienst.holen(aufgabe["id"])["zustand"] == GESCHEITERT:
            break
        dienst._setzen(aufgabe["id"], zustand=WARTET)
    stand = dienst.holen(aufgabe["id"])
    assert stand["laeufe"] >= 1
    assert stand["fehler"]


def test_abnahme_erkennt_offene_schritte_ohne_modell(monkeypatch):
    dienst = get_abnahme_service()
    monkeypatch.setattr(
        dienst, "_schritte", lambda plan: (["Schritt eins"], ["Schritt zwei"], "laeuft")
    )
    monkeypatch.setattr(dienst, "_dateien", lambda seit: [])
    ergebnis = asyncio.run(dienst.pruefen("Auftrag", "p1", "irgendwas"))
    assert ergebnis["fertig"] is False
    assert "Schritt zwei" in ergebnis["fehlt"]
    assert ergebnis["quelle"] == "pruefung"


def test_abnahme_erkennt_leere_dateien(monkeypatch):
    dienst = get_abnahme_service()
    monkeypatch.setattr(dienst, "_schritte", lambda plan: (["fertig"], [], "fertig"))
    monkeypatch.setattr(
        dienst,
        "_dateien",
        lambda seit: [{"name": "leer.pdf", "art": "dokument", "groesse": 0, "leer": True}],
    )
    ergebnis = asyncio.run(dienst.pruefen("Mach eine PDF", "p1", ""))
    assert ergebnis["fertig"] is False
    assert "leer.pdf" in ergebnis["fehlt"]


def test_vorwaerts_sagt_voraus_was_entsteht(tmp_path):
    dienst = get_vorwaerts_service()
    ziel = tmp_path / "neu.txt"
    sicht = dienst.vorhersagen("write_file", {"path": str(ziel)})
    assert sicht["veraendert"] is True
    assert str(ziel) in sicht["entsteht"]
    assert sicht["pruefbar"] is True


def test_vorwaerts_merkt_wenn_nichts_entstand(tmp_path):
    dienst = get_vorwaerts_service()
    ziel = tmp_path / "fehlt.txt"
    sicht = dienst.vorhersagen("write_file", {"path": str(ziel)})
    abgleich = dienst.abgleichen(sicht, '{"ok": true}')
    assert abgleich["getroffen"] is False
    assert "fehlt.txt" in abgleich["abweichungen"][0]

    ziel.write_text("da", encoding="utf-8")
    assert dienst.abgleichen(sicht, "")["getroffen"] is True


def test_vorwaerts_kennt_lesende_werkzeuge():
    sicht = get_vorwaerts_service().vorhersagen("list_dir", {"path": "C:/"})
    assert sicht["veraendert"] is False
    assert sicht["pruefbar"] is False


def test_vorwaerts_findet_den_widerspruch_in_einer_folge(tmp_path):
    datei = tmp_path / "a.txt"
    datei.write_text("x", encoding="utf-8")
    schritte = [
        {"werkzeug": "delete_path", "args": {"path": str(datei)}},
        {"werkzeug": "read_file", "args": {"path": str(datei)}},
    ]
    ergebnis = get_vorwaerts_service().durchspielen(schritte)
    assert ergebnis["probleme"], ergebnis
    assert "entfernt" in ergebnis["probleme"][0]


def test_durchspielen_sammelt_den_endzustand(tmp_path):
    schritte = [
        {"werkzeug": "write_file", "args": {"path": str(tmp_path / "eins.txt")}},
        {"werkzeug": "write_file", "args": {"path": str(tmp_path / "zwei.txt")}},
    ]
    ergebnis = get_vorwaerts_service().durchspielen(schritte)
    assert len(ergebnis["am_ende_da"]) == 2
    assert not ergebnis["probleme"]


def test_hypothese_wird_erst_nach_zwei_belegen_bestaetigt():
    dienst = get_hypothese_service()
    h = dienst.anlegen("Der Ordner ist schreibgeschuetzt", "list_dir probieren", "list_dir")
    assert h["zustand"] == "offen"
    nach_einem = dienst.verbuchen(h["id"], True)
    assert nach_einem["zustand"] == "offen"
    nach_zwei = dienst.verbuchen(h["id"], True)
    assert nach_zwei["zustand"] == BESTAETIGT
    assert nach_zwei["belege_dafuer"] == 2


def test_hypothese_wird_widerlegt():
    dienst = get_hypothese_service()
    h = dienst.anlegen("Das Netz ist schuld an allem", "netz_status", "netz_status")
    dienst.verbuchen(h["id"], False)
    assert dienst.verbuchen(h["id"], False)["zustand"] == WIDERLEGT


def test_hypothese_lehnt_riskante_tests_ab():
    dienst = get_hypothese_service()
    h = dienst.anlegen(
        "Loeschen hilft", "einfach loeschen", "delete_path", {"path": "C:/Windows"}
    )
    ergebnis = asyncio.run(dienst.pruefen(h["id"]))
    assert ergebnis.get("error")
    assert "riskant" in ergebnis["error"]


def test_hypothese_ohne_test_wird_abgelehnt():
    dienst = get_hypothese_service()
    h = dienst.anlegen("Reine Vermutung ohne Test", "", "keins")
    assert "keinen ausfuehrbaren Test" in asyncio.run(dienst.pruefen(h["id"]))["error"]


def test_bestaetigte_hypothese_kommt_in_den_prompt():
    dienst = get_hypothese_service()
    h = dienst.anlegen("Der Pfad muss absolut sein", "probieren", "netz_status")
    dienst.verbuchen(h["id"], True)
    dienst.verbuchen(h["id"], True)
    block = dienst.prompt_block()
    assert "nachgeprueft" in block
    assert "absolut" in block


def test_aufgaben_kommen_ins_arbeitsgedaechtnis(dienst):
    dienst.anlegen("Eine sichtbare Aufgabe")
    block = dienst.prompt_block()
    assert "sichtbare Aufgabe" in block
    from app.services.aufmerksamkeit_service import get_aufmerksamkeit_service

    gewaehlt = get_aufmerksamkeit_service().waehlen("woran arbeitest du", budget=4000)
    assert any(e["name"] == "aufgaben" for e in gewaehlt["gewaehlt"])


@pytest.mark.parametrize(
    "werkzeug", ["aufgabe", "aufgabe_starten", "durchspielen", "hypothese"]
)
def test_neue_werkzeuge_sind_angemeldet(werkzeug):
    from app.services.tools import describe_tool, werkzeugnamen
    from app.services.werkzeug_register import finden, finden_async

    assert werkzeug in werkzeugnamen()
    assert finden(werkzeug) or finden_async(werkzeug)
    assert describe_tool(werkzeug, {}) != werkzeug


def test_auswahl_findet_die_aufgabenliste():
    from app.services.tools import select_tools

    for satz in (
        "kuemmere dich um die praesentation waehrend ich weg bin",
        "woran arbeitest du gerade",
        "wie weit bist du mit meinem projekt",
    ):
        auswahl = select_tools(satz)
        assert auswahl is None or "aufgabe" in auswahl, satz


def test_systemprompt_kennt_das_alleinarbeiten():
    from app.services.chat_service import SYSTEM_PROMPT

    assert "ALLEINE ARBEITEN" in SYSTEM_PROMPT
    assert "NACHPRUEFEN STATT RATEN" in SYSTEM_PROMPT
    assert "durchspielen" in SYSTEM_PROMPT
