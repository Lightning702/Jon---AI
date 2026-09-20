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


def test_wecker_kennt_seine_uhrzeit():
    uhr = client.post(
        "/api/zeit", json={"art": "wecker", "uhrzeit": "07:30", "titel": "Aufstehen"}
    ).json()
    assert uhr["art"] == "wecker"
    assert uhr["klingelt_um"][11:16] == "07:30"
    assert uhr["rest"] > 0
    assert uhr["fertig"] is False


def test_wecker_ohne_uhrzeit_wird_abgelehnt():
    antwort = client.post("/api/zeit", json={"art": "wecker"})
    assert antwort.status_code == 400


def test_timer_laesst_sich_verlaengern_und_verkuerzen():
    uhr = client.post("/api/zeit", json={"art": "timer", "sekunden": 180}).json()
    laenger = client.post(
        f"/api/zeit/{uhr['id']}/anpassen", json={"sekunden": 420}
    ).json()
    assert laenger["dauer"] == 600.0
    assert laenger["rest"] == pytest.approx(600.0, abs=1.0)

    kuerzer = client.post(
        f"/api/zeit/{uhr['id']}/anpassen", json={"sekunden": -120}
    ).json()
    assert kuerzer["dauer"] == 480.0


def test_stoppuhr_laesst_sich_nicht_anpassen():
    uhr = client.post("/api/zeit", json={"art": "stoppuhr"}).json()
    antwort = client.post(f"/api/zeit/{uhr['id']}/anpassen", json={"sekunden": 60})
    assert antwort.status_code == 400


def test_neustart_setzt_den_timer_zurueck():
    uhr = client.post("/api/zeit", json={"art": "timer", "sekunden": 5}).json()
    time.sleep(0.5)
    neu = client.post(f"/api/zeit/{uhr['id']}/neustart").json()
    assert neu["verstrichen"] == pytest.approx(0.0, abs=0.2)
    assert neu["rest"] == pytest.approx(5.0, abs=0.2)


def test_jon_erhoeht_und_verkuerzt_auf_zuruf():
    runner = ToolBox()
    json.loads(runner._zeit("start_timer", {"minutes": 3, "label": "Tee"}))

    laenger = json.loads(runner._zeit("adjust_timer", {"minutes": 7}))
    assert laenger["uhr"]["dauer"] == 600.0
    assert "laenger" in laenger["text"]

    kuerzer = json.loads(runner._zeit("adjust_timer", {"minutes": -2}))
    assert kuerzer["uhr"]["dauer"] == 480.0
    assert "kuerzer" in kuerzer["text"]


def test_jon_ohne_versatz_fragt_nach():
    runner = ToolBox()
    json.loads(runner._zeit("start_timer", {"minutes": 3}))
    assert "error" in json.loads(runner._zeit("adjust_timer", {}))


def test_jon_steuert_pause_neustart_und_stopp():
    runner = ToolBox()
    json.loads(runner._zeit("start_timer", {"minutes": 4, "label": "Nudeln"}))

    pause = json.loads(runner._zeit("control_timer", {"action": "pause"}))
    assert pause["uhr"]["laeuft"] is False

    weiter = json.loads(runner._zeit("control_timer", {"action": "resume"}))
    assert weiter["uhr"]["laeuft"] is True

    neu = json.loads(runner._zeit("control_timer", {"action": "restart"}))
    assert neu["uhr"]["rest"] == pytest.approx(240.0, abs=1.0)

    gestoppt = json.loads(runner._zeit("control_timer", {"action": "stop"}))
    assert "Nudeln" in gestoppt["text"]
    assert client.get("/api/zeit").json()["uhren"] == []


def test_jon_waehlt_die_richtige_uhr():
    runner = ToolBox()
    json.loads(runner._zeit("start_timer", {"minutes": 5, "label": "Pizza"}))
    json.loads(runner._zeit("start_stopwatch", {"label": "Lernen"}))

    getroffen = json.loads(runner._zeit("adjust_timer", {"minutes": 1, "kind": "timer"}))
    assert getroffen["uhr"]["titel"] == "Pizza"

    ueber_namen = json.loads(runner._zeit("control_timer", {"action": "pause", "id": "lernen"}))
    assert ueber_namen["uhr"]["titel"] == "Lernen"


def test_jon_stellt_und_verschiebt_den_wecker():
    runner = ToolBox()
    gestellt = json.loads(
        runner._zeit("set_alarm", {"label": "Schule", "time": "06:15"})
    )
    assert gestellt["rings_at"][11:16] == "06:15"

    liste = json.loads(runner._zeit("list_alarms", {}))
    assert len(liste["alarms"]) == 1
    assert liste["alarms"][0]["label"] == "Schule"

    verschoben = json.loads(runner._zeit("adjust_timer", {"minutes": 30, "kind": "wecker"}))
    assert verschoben["uhr"]["klingelt_um"][11:16] == "06:45"

    geloescht = json.loads(runner._zeit("delete_alarm", {}))
    assert geloescht["deleted"] is True
    assert json.loads(runner._zeit("list_alarms", {}))["alarms"] == []


def test_stoppen_ohne_angabe_laesst_den_wecker_stehen():
    runner = ToolBox()
    json.loads(runner._zeit("set_alarm", {"label": "Frueh", "time": "05:00"}))
    json.loads(runner._zeit("start_timer", {"minutes": 2}))

    json.loads(runner._zeit("delete_alarm", {"name": "frueh"}))
    uebrig = client.get("/api/zeit").json()["uhren"]
    assert [u["art"] for u in uebrig] == ["timer"]


def test_uhr_aus_telegram_wird_einmal_gemeldet():
    fern = ToolBox(source="telegram")
    json.loads(fern._zeit("start_timer", {"minutes": 6, "label": "Unterwegs"}))

    erste = client.get("/api/zeit/neu").json()["uhren"]
    assert [u["titel"] for u in erste] == ["Unterwegs"]
    assert erste[0]["quelle"] == "telegram"
    assert client.get("/api/zeit/neu").json()["uhren"] == []


def test_uhr_aus_der_app_wird_nicht_gemeldet():
    runner = ToolBox()
    json.loads(runner._zeit("start_timer", {"minutes": 6}))
    assert client.get("/api/zeit/neu").json()["uhren"] == []


def test_karte_zeigt_alle_uhren():
    from app.services.chat_service import card_payload

    runner = ToolBox()
    ergebnis = runner._zeit("set_alarm", {"label": "Zug", "time": "08:00"})
    karte = card_payload("set_alarm", ergebnis)
    assert karte is not None
    assert karte["kind"] == "zeit"
    assert [u["art"] for u in karte["data"]["uhren"]] == ["wecker"]


def test_abgelaufene_uhren_klingeln_beim_start_nicht_nach():
    from app.services.zeit_service import STORE, ZeitService
    from app.core.store import atomic_write_json

    atomic_write_json(
        STORE,
        [
            {
                "id": "altbekannt",
                "art": "timer",
                "titel": "Von gestern",
                "gestartet": time.time() - 900,
                "dauer": 180.0,
            }
        ],
    )
    dienst = ZeitService()
    uhr = dienst.stand()["uhren"][0]
    assert uhr["fertig"] is True
    assert uhr["klingelt"] is False
    dienst.stoppen()


def test_ton_bleibt_in_den_tests_still():
    from app.services.zeit_service import stumm, ton_an

    assert stumm() is True
    assert ton_an() is False
