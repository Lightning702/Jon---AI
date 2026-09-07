from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.providers.base import StreamChunk
from app.providers.registry import get_registry
from app.services.calendar_service import get_calendar_service
from app.services.inbox_service import CATEGORIES, get_inbox_service

client = TestClient(app)


class FakeProvider:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    async def stream(self, request, executor=None):
        yield StreamChunk(kind="content", delta=self.answer)


@pytest.fixture()
def fake_llm(monkeypatch):
    def install(answer: str):
        monkeypatch.setattr(
            get_registry(), "get", lambda name: FakeProvider(answer), raising=False
        )

    return install


def _analyse(text: str, key: str, fake_llm, antwort: str) -> dict:
    fake_llm(antwort)
    service = get_inbox_service()
    return asyncio.run(service.analyze(key, text, "Betreff", "lehrer@schule.at", force=True))


def test_terminaenderung_wird_erkannt(fake_llm):
    antwort = (
        '{"typ": "terminaenderung", "titel": "Mathetest verschoben", '
        '"zusammenfassung": "Der Mathetest wurde auf Freitag verschoben.", '
        '"wichtigkeit": "hoch", "datum": "2026-09-04", "zeit": "", "deadline": "", '
        '"personen": ["Herr Huber"], "projekt": "", '
        '"aktionen": [{"typ": "kalender_aendern", "label": "Kalender aktualisieren", '
        '"payload": {"suche": "Mathetest", "date": "2026-09-04"}}]}'
    )
    data = _analyse(
        "Der Mathetest wurde auf Freitag verschoben.", "mail:1", fake_llm, antwort
    )
    assert data["typ"] == "terminaenderung"
    assert data["datum"] == "2026-09-04"
    assert data["aktionen"][0]["typ"] == "kalender_aendern"
    assert data["aktionen"][0]["freigabe"] is True


def test_aufgabe_mit_deadline_wird_erkannt(fake_llm):
    antwort = (
        '{"typ": "aufgabe", "titel": "Präsentation schicken", '
        '"zusammenfassung": "Die Präsentation soll bis Montag da sein.", '
        '"wichtigkeit": "mittel", "datum": "", "zeit": "", "deadline": "2026-09-07", '
        '"personen": ["Anna"], "projekt": "Vertrieb", '
        '"aktionen": ['
        '{"typ": "aufgabe_neu", "label": "Aufgabe erstellen", '
        '"payload": {"title": "Präsentation schicken", "date": "2026-09-07"}}, '
        '{"typ": "erinnerung_neu", "label": "Erinnerung erstellen", '
        '"payload": {"text": "Präsentation schicken", "time": "09:00"}}]}'
    )
    data = _analyse(
        "Kannst du mir die Präsentation bis Montag schicken?", "mail:2", fake_llm, antwort
    )
    assert data["typ"] == "aufgabe"
    assert data["deadline"] == "2026-09-07"
    assert [a["typ"] for a in data["aktionen"]] == ["aufgabe_neu", "erinnerung_neu"]
    assert all(a["freigabe"] is False for a in data["aktionen"])


def test_termin_wird_erkannt_und_gecacht(fake_llm):
    antwort = (
        '{"typ": "termin", "titel": "Meeting", "zusammenfassung": "Meeting morgen um 15 Uhr.", '
        '"wichtigkeit": "hoch", "datum": "2026-09-01", "zeit": "15:00", "deadline": "", '
        '"personen": [], "projekt": "", "aktionen": [{"typ": "kalender_neu", '
        '"label": "Kalendereintrag erstellen", "payload": {"title": "Meeting", '
        '"date": "2026-09-01", "time": "15:00"}}]}'
    )
    data = _analyse("Meeting morgen um 15 Uhr.", "mail:3", fake_llm, antwort)
    assert data["zeit"] == "15:00"
    assert get_inbox_service().analysis_for("mail:3")["titel"] == "Meeting"


def test_unbekannte_aktionen_werden_verworfen(fake_llm):
    antwort = (
        '{"typ": "info", "titel": "Newsletter", "zusammenfassung": "Nichts zu tun.", '
        '"wichtigkeit": "niedrig", "aktionen": [{"typ": "mail_senden", '
        '"label": "Antworten", "payload": {"an": "fremd@example.com"}}]}'
    )
    data = _analyse("Newsletter", "mail:4", fake_llm, antwort)
    assert data["aktionen"] == []


def test_aktion_ohne_bestaetigung_wird_abgelehnt():
    antwort = client.post(
        "/api/inbox/action",
        json={"typ": "kalender_neu", "payload": {"title": "Test", "date": "heute"}},
    )
    assert antwort.status_code == 403


def test_bestaetigte_aktion_legt_termin_an():
    tag = (date.today() + timedelta(days=3)).isoformat()
    antwort = client.post(
        "/api/inbox/action",
        json={
            "typ": "kalender_neu",
            "bestaetigt": True,
            "payload": {"title": "Mathetest", "date": tag, "time": "08:00"},
        },
    )
    assert antwort.status_code == 200
    assert antwort.json()["ergebnis"]["title"] == "Mathetest"
    assert any(e["title"] == "Mathetest" for e in get_calendar_service().search("Mathetest"))


def test_terminaenderung_verschiebt_bestehenden_termin():
    neu = (date.today() + timedelta(days=5)).isoformat()
    antwort = client.post(
        "/api/inbox/action",
        json={
            "typ": "kalender_aendern",
            "bestaetigt": True,
            "payload": {"suche": "Mathetest", "date": neu},
        },
    )
    assert antwort.status_code == 200
    assert antwort.json()["ergebnis"]["date"] == neu


def test_terminaenderung_ohne_treffer_meldet_fehler():
    antwort = client.post(
        "/api/inbox/action",
        json={
            "typ": "kalender_aendern",
            "bestaetigt": True,
            "payload": {"suche": "Gibt-es-nicht-xyz", "date": "morgen"},
        },
    )
    assert antwort.status_code == 400


def test_feed_fuehrt_quellen_zusammen():
    tag = (date.today() + timedelta(days=1)).isoformat()
    get_calendar_service().add("Zahnarzt", tag, "10:00")
    data = client.get("/api/inbox").json()
    assert [c["id"] for c in data["kategorien"]] == [c["id"] for c in CATEGORIES]
    assert data["zaehler"]["alle"] >= 1
    assert any(e["titel"] == "Zahnarzt" for e in data["eintraege"])
    assert all("kategorie" in e for e in data["eintraege"])


def test_feed_bleibt_ohne_mailkonto_nutzbar():
    data = client.get("/api/inbox").json()
    assert isinstance(data["eintraege"], list)
    assert isinstance(data["mail_fehler"], str)


def test_gesehen_wird_gemerkt():
    client.post("/api/inbox/seen", json={"id": "mail:3"})
    data = client.get("/api/inbox").json()
    assert isinstance(data["eintraege"], list)


def test_wiederkehrende_erinnerungen_stehen_nur_einmal():
    from app.services.reminder_service import get_reminder_service

    dienst = get_reminder_service()
    erinnerung = dienst.add("Softwareupdates pruefen", "23:00", "daily")
    try:
        eintraege = client.get("/api/inbox").json()["eintraege"]
        treffer = [e for e in eintraege if e["titel"] == "Softwareupdates pruefen"]
        assert len(treffer) == 1
    finally:
        dienst.delete(erinnerung["id"])
