from __future__ import annotations

import os
import time

import pytest

from app.services import jon_dateien


@pytest.fixture
def jon_ordner(tmp_path, monkeypatch):
    from app.services.dateiraum_service import get_dateiraum_service

    ordner = tmp_path / "Jon"
    monkeypatch.setattr(type(get_dateiraum_service()), "wurzel", lambda self: ordner)
    monkeypatch.setattr(jon_dateien, "_datei", lambda: tmp_path / "jon_dateien.json")
    return ordner


FOLIEN = [{"layout": "title", "title": "Datensicherung"}, {"layout": "bullets", "title": "Warum?", "bullets": ["Defekte", "Ransomware"]}]


def test_grundname_ignoriert_versionszusaetze():
    assert jon_dateien.grundname("Datensicherung_Final.pptx") == "datensicherung"
    assert jon_dateien.grundname("Datensicherung neu v2.pptx") == "datensicherung"
    assert jon_dateien.grundname("Datensicherung (3).pptx") == "datensicherung"
    assert jon_dateien.grundname("Teil-1.pptx") != jon_dateien.grundname("Teil-2.pptx")


def test_powerpoint_wird_aktualisiert_statt_kopiert(jon_ordner):
    from app.services.pptx_service import get_pptx_service

    dienst = get_pptx_service()
    erste = dienst.create("Datensicherung", FOLIEN, None, "hell", "", False)
    zweite = dienst.create("Datensicherung", FOLIEN + [{"layout": "closing", "title": "Danke"}], None, "hell", "", False)
    dritte = dienst.create("Datensicherung", FOLIEN, "Datensicherung_Final.pptx", "hell", "", False)
    assert erste["path"] == zweite["path"] == dritte["path"]
    assert zweite.get("aktualisiert") and dritte.get("aktualisiert")
    assert len(list((jon_ordner / "Documents").glob("*.pptx"))) == 1
    kopie = dienst.create("Datensicherung", FOLIEN, None, "hell", "", False, True)
    assert kopie["path"] != erste["path"]


def test_fremde_oder_vom_nutzer_geaenderte_dateien_bleiben(jon_ordner):
    from app.services.pptx_service import get_pptx_service

    dienst = get_pptx_service()
    erste = dienst.create("Referat", FOLIEN, None, "hell", "", False)
    pfad = erste["path"]
    with open(pfad, "ab") as datei:
        datei.write(b"\0")
    spaeter = time.time() + 5
    os.utime(pfad, (spaeter, spaeter))
    zweite = dienst.create("Referat", FOLIEN, None, "hell", "", False)
    assert zweite["path"] != pfad
    assert not zweite.get("aktualisiert")


def test_word_dokument_wird_aktualisiert(jon_ordner):
    from app.services.dokument_service import get_dokument_service

    dienst = get_dokument_service()
    erste = dienst.erstellen("docx", "Brief an die Schule", "# Brief\nText")
    zweite = dienst.erstellen("docx", "Brief an die Schule", "# Brief\nNeuer Text")
    assert erste["datei"]["path"] == zweite["datei"]["path"]
    assert zweite.get("aktualisiert")


def test_bearbeiten_haelt_die_datei_als_jons_datei(jon_ordner):
    from app.services.pptx_bearbeiten import bearbeiten
    from app.services.pptx_service import get_pptx_service
    import asyncio

    dienst = get_pptx_service()
    erste = dienst.create("Vortrag", FOLIEN, None, "hell", "", False)
    asyncio.run(bearbeiten(erste["path"], [{"aktion": "ersetzen", "suchen": "Ransomware", "ersetzen": "Erpressersoftware"}]))
    zweite = dienst.create("Vortrag", FOLIEN, None, "hell", "", False)
    assert zweite["path"] == erste["path"]
