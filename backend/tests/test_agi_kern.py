from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.benchmark_service import get_benchmark_service
from app.services.ereignis_service import get_ereignis_service
from app.services.erfahrung_service import KLAPPT_NICHT, bereich_fuer, get_erfahrung_service
from app.services.handlungsraum_service import get_handlungsraum_service
from app.services.kern import HANDLUNG, WAHRNEHMUNG, Signal, get_kern, verdrahten
from app.services.memory_service import MemoryService
from app.services.notizblock_service import get_notizblock_service
from app.services.selbst_service import get_selbst_service
from app.services.semantik import aehnlichkeit, vektor
from app.services.weltmodell_service import get_weltmodell_service
from app.services.zeitraum import verstehen
from app.services.ziel_service import get_ziel_service


def test_benchmark_bleibt_gruen():
    ergebnis = get_benchmark_service().lauf()
    assert ergebnis["gesamt"] >= 50
    assert ergebnis["quote"] >= 0.95, ergebnis["durchgefallen"]


def test_zeitraum_versteht_deutsche_angaben():
    assert verstehen("gestern").beschreibung == "gestern"
    assert verstehen("morgen").zukunft is True
    assert verstehen("vor 3 tagen").beschreibung == "vor 3 Tagen"
    heute = verstehen("")
    assert heute.beschreibung == "heute"
    assert heute.von.date() == heute.bis.date()


def test_ereignisgedaechtnis_beantwortet_was_war():
    dienst = get_ereignis_service()
    dienst.notieren("werkzeug", "write_file", "Schreibt die Datei notiz.txt", bedeutung=0.5)
    dienst.notieren("fehler", "delete_path", "Systempfad blockiert", gelungen=False)
    bild = dienst.tagesbild("heute")
    assert bild["anzahl"] >= 2
    assert "delete_path" in bild["fehler"]
    treffer = dienst.suchen("datei geschrieben")
    assert any(t["titel"] == "write_file" for t in treffer)


def test_ziele_leben_ueber_tage():
    dienst = get_ziel_service()
    ziel = dienst.anlegen(
        "Regal aufbauen", frist="morgen", naechster_schritt="Werkzeug suchen"
    )
    assert ziel["frist"]
    assert ziel["tage_bis_frist"] in (0, 1)
    offen = [z["titel"] for z in dienst.liste()]
    assert "Regal aufbauen" in offen
    dienst.aktualisieren(ziel["id"], zustand="erledigt", fortschritt=1.0)
    assert "Regal aufbauen" not in [z["titel"] for z in dienst.liste()]
    assert dienst.prompt_block() is not None


def test_weltmodell_kennt_dinge_und_beziehungen():
    dienst = get_weltmodell_service()
    dienst.merken("Rex", "sache", "Der Hund des Nutzers")
    dienst.merken("Werkstatt", "projekt", "Umbau im Keller")
    dienst.verbinden("Rex", "Werkstatt", "kommt_vor_in")
    umfeld = dienst.umfeld("Rex")
    assert umfeld["gefunden"] is True
    assert any(b.get("zu") == "Werkstatt" for b in umfeld["beziehungen"])
    block = dienst.prompt_block("Wie heisst der Hund?")
    assert "Rex" in block


def test_notizblock_ueberlebt_den_turn():
    dienst = get_notizblock_service()
    dienst.schreiben("Preis liegt bei 8 EUR", "buch")
    dienst.ergaenzen("Versand kostet 3 EUR", "buch")
    inhalt = dienst.lesen("buch")
    assert "8 EUR" in inhalt and "Versand" in inhalt
    assert dienst.lesen("anderes") == ""


def test_erfahrung_merkt_sich_was_nicht_klappt():
    dienst = get_erfahrung_service()
    bereich = bereich_fuer("browser_goto", {"url": "https://thalia.de/suche"})
    assert bereich == "web:thalia.de"
    dienst.notieren(bereich, "Suchfeld liegt oben rechts")
    dienst.notieren(bereich, "Cookie-Banner verdeckt alles", KLAPPT_NICHT, 0.8)
    block = dienst.prompt_block(bereich)
    assert "Suchfeld" in block and "Achtung" in block


def test_selbstbild_kennt_grenzen_und_zutrauen():
    dienst = get_selbst_service()
    bild = dienst.selbstbild()
    assert bild["werkzeuge"] > 50
    assert any("Passwoerter" in g for g in bild["grenzen"])
    einschaetzung = dienst.kann_ich("eine Datei im Downloads-Ordner suchen")
    assert einschaetzung["zutrauen"] in ("hoch", "mittel", "niedrig")
    assert dienst.sicherheit_schaetzen("Das ist vermutlich vielleicht so") < 0.7


def test_handlungsraum_fasst_alles_zusammen():
    zustand = get_handlungsraum_service().zustand()
    for feld in ("browser", "bildschirm", "auftraege", "ziele", "netz"):
        assert feld in zustand


def test_kern_verteilt_signale():
    verdrahten()
    kern = get_kern()
    gesehen: list[Signal] = []
    kern.hoeren("test", lambda signal: gesehen.append(signal))
    kern.melden("test", "probe", {"wert": 1})
    assert gesehen and gesehen[0].name == "probe"
    vorher = get_ereignis_service().tagesbild("heute")["anzahl"]
    kern.melden(HANDLUNG, "probe_handlung", {"detail": "test", "gelungen": True})
    assert get_ereignis_service().tagesbild("heute")["anzahl"] > vorher
    kern.melden(WAHRNEHMUNG, "bildschirm", {"titel": "Editor"})
    assert "signale" in kern.stand()


def test_gedaechtnis_findet_relevantes_statt_neuestes():
    speicher = MemoryService()
    speicher.add("Der Nutzer faehrt ein blaues Fahrrad.")
    speicher.add("Der Lieblingskaffee ist Espresso.")
    for nummer in range(12):
        speicher.add(f"Belangloser Merkposten Nummer {nummer}.")
    treffer = speicher.relevante("Was fuer ein Fahrrad habe ich?", limit=5)
    assert any("Fahrrad" in e["content"] for e in treffer)


def test_semantik_trennt_nah_und_fern():
    assert aehnlichkeit(vektor("Termin beim Zahnarzt"), vektor("Zahnarzttermin")) > 0.3
    assert aehnlichkeit(vektor("Zahnarzt"), vektor("Festplatte formatieren")) < 0.2


def test_lernen_findet_muster_und_antimuster():
    from app.services.lernen_service import get_lernen_service

    ereignisse = get_ereignis_service()
    for _ in range(3):
        ereignisse.notieren("werkzeug", "browser_goto", "Seite geoeffnet")
        ereignisse.notieren("werkzeug", "browser_read", "Seite gelesen")
        ereignisse.notieren("werkzeug", "browser_click", "Geklickt")
    for _ in range(2):
        ereignisse.notieren("fehler", "download_file", "Netzfehler", gelungen=False)
    dienst = get_lernen_service()
    muster = dienst.muster(tage=1, mindest=2)
    assert any(len(m["schritte"]) == 3 for m in muster)
    antimuster = dienst.antimuster(tage=1, mindest=2)
    assert any(a["werkzeug"] == "download_file" for a in antimuster)


def test_trainingsdaten_werden_exportiert():
    from app.services.lernen_service import get_lernen_service

    ergebnis = get_lernen_service().trainingsdaten(grenze=10)
    assert ergebnis["ok"] is True
    assert Path(ergebnis["datei"]).exists()


def test_auftrag_ueberlebt_absturz():
    from app.services.auftrag_service import get_auftrag_service

    dienst = get_auftrag_service()
    kennung = dienst.anlegen("Langer Lauf", {"auftrag": "test"})
    dienst.melden(kennung, schritte=10, schritt=4)
    assert dienst.holen(kennung)["fortschritt"] == 0.4
    assert dienst.unterbrochene_markieren() >= 1
    assert any(a["zustand"] == "unterbrochen" for a in dienst.offene())


def test_cache_spart_wiederholte_abfragen():
    from app.services.cache_service import get_cache_service

    cache = get_cache_service()
    cache.leeren()
    cache.merken("web_search", {"query": "wetter"}, '{"treffer": []}')
    assert cache.holen("web_search", {"query": "wetter"}) is not None
    assert cache.holen("web_search", {"query": "anderes"}) is None
    assert cache.holen("delete_path", {"path": "x"}) is None


def test_rueckgaengig_stellt_datei_wieder_her(tmp_path):
    from app.services.rueckgaengig_service import get_rueckgaengig_service

    datei = tmp_path / "notiz.txt"
    datei.write_text("alt", encoding="utf-8")
    dienst = get_rueckgaengig_service()
    dienst.vormerken("write_file", {"path": str(datei)})
    datei.write_text("neu", encoding="utf-8")
    ergebnis = dienst.rueckgaengig()
    assert ergebnis["ok"] is True
    assert datei.read_text(encoding="utf-8") == "alt"


def test_werkzeuge_laufen_ueber_die_registry():
    from app.services.tools import ToolBox

    box = ToolBox()
    ergebnis = json.loads(asyncio.run(box.execute("weltzustand", {})))
    assert "browser" in ergebnis
    ziel = json.loads(
        asyncio.run(box.execute("ziel", {"aktion": "anlegen", "titel": "Testziel"}))
    )
    assert ziel["titel"] == "Testziel"
