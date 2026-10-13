import asyncio
import json
from datetime import datetime

from app.services import telegram_plan
from app.services.reminder_service import get_reminder_service
from app.services.werkzeug_register import finden_async, laden


def test_zeit_lesen():
    jetzt = datetime(2026, 10, 12, 14, 5)
    assert telegram_plan.zeit_lesen("20:00", "", jetzt) == ("20:00", "2026-10-12")
    assert telegram_plan.zeit_lesen("20 Uhr", "", jetzt) == ("20:00", "2026-10-12")
    assert telegram_plan.zeit_lesen("um 9", "", jetzt) == ("09:00", "2026-10-13")
    assert telegram_plan.zeit_lesen("in 10 Minuten", "", jetzt) == ("14:15", "2026-10-12")
    assert telegram_plan.zeit_lesen("morgen 8 Uhr", "", jetzt) == ("08:00", "2026-10-13")
    assert telegram_plan.zeit_lesen("Freitag 18:30", "", jetzt) == ("18:30", "2026-10-16")
    assert telegram_plan.zeit_lesen("halb 8 abends", "", jetzt) == ("19:30", "2026-10-12")
    assert telegram_plan.zeit_lesen("2026-10-20T09:15", "", jetzt) == ("09:15", "2026-10-20")
    assert telegram_plan.zeit_lesen("21:00", "2026-11-01", jetzt) == ("21:00", "2026-11-01")
    assert telegram_plan.zeit_lesen("irgendwann", "", jetzt) is None


def test_telegram_erinnerungen_bleiben_getrennt():
    dienst = get_reminder_service()
    normal = dienst.add("Trinken", "00:00", "once")
    tg = dienst.add("Muell", "00:00", "once", "", "telegram", "2000-01-01")
    spaeter = dienst.add("Zukunft", "00:00", "once", "", "telegram", "2999-01-01")
    try:
        app_faellig = [r["id"] for r in dienst.due()]
        tg_faellig = [r["id"] for r in dienst.due("telegram")]
        assert normal["id"] in app_faellig and tg["id"] not in app_faellig
        assert tg["id"] in tg_faellig and spaeter["id"] not in tg_faellig
        assert dienst.due("telegram") == []
    finally:
        for eintrag in (normal, tg, spaeter):
            dienst.delete(eintrag["id"])


def test_werkzeug_plant_listet_und_loescht(monkeypatch):
    laden()
    werkzeug = finden_async("telegram_senden")
    geplant = json.loads(asyncio.run(werkzeug(None, {"text": "Erinnerung: Muell", "zeit": "morgen 20 Uhr"}, "telegram_senden")))
    assert geplant["geplant"] and geplant["zeit"] == "20:00"
    liste = json.loads(asyncio.run(werkzeug(None, {"aktion": "liste"}, "telegram_senden")))["geplant"]
    assert any(g["id"] == geplant["id"] for g in liste)
    weg = json.loads(asyncio.run(werkzeug(None, {"aktion": "loeschen", "text": "muell"}, "telegram_senden")))
    assert weg["ok"] and weg["geloescht"] >= 1
    assert not any(g["id"] == geplant["id"] for g in telegram_plan.geplante())


def test_sofort_senden(monkeypatch):
    gesendet = []

    class Bot:
        async def send(self, chat, text):
            gesendet.append((chat, text))

    monkeypatch.setattr(telegram_plan, "bereit", lambda: (True, ""))
    monkeypatch.setattr(telegram_plan, "chat", lambda: "4711")
    import app.services.telegram_service as modul

    monkeypatch.setattr(modul, "get_telegram_service", lambda: Bot())
    laden()
    ergebnis = json.loads(asyncio.run(finden_async("telegram_senden")(None, {"text": "Hallo"}, "telegram_senden")))
    assert ergebnis["gesendet"] and gesendet == [("4711", "Hallo")]


def test_ohne_einrichtung_klarer_fehler(monkeypatch):
    monkeypatch.setattr(telegram_plan, "bereit", lambda: (False, "Telegram ist noch nicht eingerichtet."))
    ergebnis = asyncio.run(telegram_plan.senden("x"))
    assert "eingerichtet" in ergebnis["error"]
