import asyncio

from app.api import mobile_routes
from app.api.routes import app_befehl


def test_video_wunsch():
    assert mobile_routes._video_wunsch([]) == (15, "maus")
    assert mobile_routes._video_wunsch(["2"]) == (15, "2")
    assert mobile_routes._video_wunsch(["2", "30s"]) == (30, "2")
    assert mobile_routes._video_wunsch(["alle", "20"]) == (20, "alle")
    assert mobile_routes._video_wunsch(["90"]) == (60, "maus")


def test_harness_befehle_gehen_auch_in_der_app():
    antwort = asyncio.run(app_befehl({"text": "/hhelp"}))
    assert "Jon Harness" in antwort["text"]


def test_telegram_befehl(monkeypatch):
    import app.services.telegram_plan as plan

    async def senden(text):
        return {"ok": True, "text": text}

    monkeypatch.setattr(plan, "senden", senden)
    assert asyncio.run(app_befehl({"text": "/telegram Hallo"}))["text"] == "Auf Telegram geschickt."
    assert "Was soll ich" in asyncio.run(app_befehl({"text": "/telegram"}))["text"]


def test_stopp_ohne_laufende_auftraege():
    assert asyncio.run(app_befehl({"text": "/stopp"}))["text"] == "Gerade läuft nichts, alles ruhig."


def test_hilfe_listet_neue_befehle():
    antwort = asyncio.run(app_befehl({"text": "/hilfe"}))
    namen = [b["name"] for b in antwort["befehle"]]
    for name in ("/bildschirme", "/telegram", "/harness", "/erlauben", "/video", "/live"):
        assert name in namen
