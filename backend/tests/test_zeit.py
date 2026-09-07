from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.tools import ToolBox
from app.services.zeit_service import get_zeit_service, lesbar

client = TestClient(app)


@pytest.fixture(autouse=True)
def leer():
    get_zeit_service().stoppen()
    yield
    get_zeit_service().stoppen()


def test_stoppuhr_laeuft_und_pausiert():
    uhr = client.post("/api/zeit", json={"art": "stoppuhr", "titel": "Lernen"}).json()
    assert uhr["art"] == "stoppuhr"
    assert uhr["laeuft"] is True
    assert uhr["titel"] == "Lernen"

    pausiert = client.post(f"/api/zeit/{uhr['id']}/pause").json()
    assert pausiert["laeuft"] is False
    stand_a = pausiert["verstrichen"]
    time.sleep(0.4)
    stand_b = client.get("/api/zeit").json()["uhren"][0]["verstrichen"]
    assert stand_b == pytest.approx(stand_a, abs=0.15)

    weiter = client.post(f"/api/zeit/{uhr['id']}/weiter").json()
    assert weiter["laeuft"] is True


def test_timer_zaehlt_runter_und_wird_fertig():
    uhr = client.post("/api/zeit", json={"art": "timer", "sekunden": 1}).json()
    assert uhr["rest"] == pytest.approx(1.0, abs=0.2)
    assert uhr["fertig"] is False
    time.sleep(1.2)
    jetzt = client.get("/api/zeit").json()["uhren"][0]
    assert jetzt["fertig"] is True
    assert jetzt["rest"] == 0.0


def test_timer_ohne_dauer_wird_abgelehnt():
    antwort = client.post("/api/zeit", json={"art": "timer", "sekunden": 0})
    assert antwort.status_code == 400


def test_stoppen_liefert_gemessene_zeit():
    uhr = client.post("/api/zeit", json={"art": "stoppuhr"}).json()
    time.sleep(0.3)
    ergebnis = client.delete(f"/api/zeit/{uhr['id']}").json()
    assert len(ergebnis["gestoppt"]) == 1
    assert ergebnis["gestoppt"][0]["verstrichen"] >= 0.25
    assert client.get("/api/zeit").json()["uhren"] == []


def test_jon_kann_zeit_stoppen():
    runner = ToolBox()
    gestartet = json.loads(runner._zeit("start_stopwatch", {"label": "Kochen"}))
    assert gestartet["gestartet"]["titel"] == "Kochen"

    laufend = json.loads(runner._zeit("list_timers", {}))
    assert len(laufend["uhren"]) == 1

    time.sleep(0.3)
    gestoppt = json.loads(runner._zeit("stop_timer", {}))
    assert "Kochen" in gestoppt["text"]
    assert json.loads(runner._zeit("list_timers", {}))["uhren"] == []


def test_timer_ueber_werkzeug():
    runner = ToolBox()
    ergebnis = json.loads(runner._zeit("start_timer", {"minutes": 2, "seconds": 30}))
    assert ergebnis["gestartet"]["dauer"] == 150.0
    assert "2:30" in ergebnis["text"]


def test_lesbar_formatiert():
    assert lesbar(0) == "0:00"
    assert lesbar(65) == "1:05"
    assert lesbar(3725) == "1:02:05"
