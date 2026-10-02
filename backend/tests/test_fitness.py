from __future__ import annotations

import asyncio
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.services import fitness_service as modul
from app.services.fitness_service import FitnessFehler, FitnessService, datum_lesen, uebungen_lesen


@pytest.fixture
def dienst(monkeypatch, tmp_path):
    monkeypatch.setattr(modul, "STORE", tmp_path / "fitness.json")
    monkeypatch.setattr(modul, "_dienst", None)
    return modul.get_fitness_service()


def test_freitext_uebungen():
    uebungen = uebungen_lesen("Bankdrücken 3x10 60kg, Kniebeugen 4x8 mit 80,5 kg; 20 Liegestütze und Klimmzüge 3x6")
    namen = [u["name"] for u in uebungen]
    assert namen == ["Bankdrücken", "Kniebeugen", "Liegestütze", "Klimmzüge"]
    assert uebungen[0]["saetze"] == [{"wdh": 10, "gewicht": 60.0}] * 3
    assert uebungen[1]["saetze"][0] == {"wdh": 8, "gewicht": 80.5} and len(uebungen[1]["saetze"]) == 4
    assert uebungen[2]["saetze"] == [{"wdh": 20, "gewicht": 0.0}]
    assert len(uebungen[3]["saetze"]) == 3


def test_gewicht_vor_saetzen():
    uebungen = uebungen_lesen("3x12 Rudern mit 40kg")
    assert uebungen == [{"name": "Rudern", "saetze": [{"wdh": 12, "gewicht": 40.0}] * 3}]


def test_datum():
    assert datum_lesen("heute") == date.today().isoformat()
    assert datum_lesen("gestern") == (date.today() - timedelta(days=1)).isoformat()
    assert datum_lesen("24.12.2025") == "2025-12-24"
    with pytest.raises(FitnessFehler):
        datum_lesen("irgendwann")


def test_training_und_rekorde(dienst: FitnessService):
    erstes = dienst.training_eintragen({"art": "gym", "text": "Bankdrücken 3x10 60kg", "dauer_min": 50})
    assert erstes["volumen"] == 1800.0
    assert erstes["rekorde"] == ["Bankdrücken: 60 kg"]
    zweites = dienst.training_eintragen({"art": "gym", "uebungen": [{"name": "Bankdrücken", "saetze": [{"wdh": 5, "gewicht": 65}]}]})
    assert zweites["rekorde"] == ["Bankdrücken: 65 kg"]
    drittes = dienst.training_eintragen({"art": "gym", "text": "Bankdrücken 1x5 50kg"})
    assert drittes["rekorde"] == []
    uebersicht = dienst.uebersicht()
    assert uebersicht["woche"]["trainings"] == 3
    assert uebersicht["rekorde"][0]["gewicht"] == 65
    assert uebersicht["serie"] == 1
    assert dienst.training_loeschen(drittes["id"])
    assert dienst.uebersicht()["woche"]["trainings"] == 2


def test_leeres_training(dienst: FitnessService):
    with pytest.raises(FitnessFehler):
        dienst.training_eintragen({"art": "gym"})


def test_laufen_mit_distanz(dienst: FitnessService):
    lauf = dienst.training_eintragen({"art": "laufen", "dauer_min": "31", "distanz_km": "5,2", "datum": "gestern"})
    assert lauf["distanz_km"] == 5.2 and lauf["datum"] == (date.today() - timedelta(days=1)).isoformat()


def test_schritte_nehmen_das_maximum(dienst: FitnessService):
    heute = date.today().isoformat()
    dienst.schritte_melden({heute: 4000, "kaputt": 3, "1999-01-01": 5})
    dienst.schritte_melden({heute: 3500})
    dienst.ziel_setzen(schritte=5000)
    uebersicht = dienst.uebersicht()
    assert uebersicht["heute"]["schritte"] == 4000
    assert uebersicht["heute"]["ziel"] == 5000
    assert uebersicht["heute"]["fortschritt"] == 0.8
    assert len(uebersicht["verlauf"]) == 7


def test_speichern_und_neu_laden(dienst: FitnessService):
    dienst.gewicht_eintragen("72,4")
    neu = FitnessService()
    assert neu.uebersicht()["gewicht"][-1]["kg"] == 72.4
    with pytest.raises(FitnessFehler):
        neu.gewicht_eintragen(3)


def test_werkzeuge_und_auswahl(dienst):
    from app.services.connectors.fitness import FitnessConnector
    from app.services.tools import select_tools

    connector = FitnessConnector()
    ergebnis = asyncio.run(connector.ausfuehren("fitness_training_eintragen", {"art": "gym", "text": "Kreuzheben 3x5 100kg"}))
    assert ergebnis["uebungen"][0]["name"] == "Kreuzheben"
    fehler = asyncio.run(connector.ausfuehren("fitness_training_eintragen", {"art": "gym"}))
    assert "error" in fehler
    assert "fitness_uebersicht" in select_tools("wie viele schritte habe ich heute gemacht")
    assert "fitness_training_eintragen" in select_tools("ich war heute im gym")
    assert "fitness_uebersicht" not in select_tools("wie wird das wetter")


def test_routen(dienst):
    from app.api import fitness_routes

    assert fitness_routes.add_workout({"art": "yoga", "dauer_min": 20})["art"] == "yoga"
    with pytest.raises(HTTPException):
        fitness_routes.add_workout({"art": "gym"})
    assert fitness_routes.report_steps({"tage": {date.today().isoformat(): 1234}})["gespeichert"] == 1
    assert fitness_routes.overview(7)["heute"]["schritte"] == 1234
    assert fitness_routes.set_goals({"trainings_pro_woche": 4})["trainings_pro_woche"] == 4
