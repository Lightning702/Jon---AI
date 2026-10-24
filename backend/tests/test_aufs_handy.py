from __future__ import annotations

import asyncio
import json

import pytest

from app.services import telegram_plan
from app.services.werkzeug_register import finden_async, laden


class Bot:
    def __init__(self, annehmen: bool = True) -> None:
        self.texte: list[tuple[str, str]] = []
        self.dateien: list[tuple[str, dict]] = []
        self.annehmen = annehmen

    async def send(self, chat, text):
        self.texte.append((chat, text))

    async def send_datei(self, chat, datei):
        self.dateien.append((chat, datei))
        return self.annehmen


@pytest.fixture
def bot(monkeypatch, tmp_path):
    from app.services.dateiraum_service import DateiraumService

    neu = Bot()
    monkeypatch.setattr(telegram_plan, "bereit", lambda: (True, ""))
    monkeypatch.setattr(telegram_plan, "chat", lambda: "4711")
    monkeypatch.setattr("app.services.telegram_service.get_telegram_service", lambda: neu)
    monkeypatch.setattr(DateiraumService, "frei", lambda self, pfad: (str(pfad).startswith(str(tmp_path)), "Dieser Ort liegt ausserhalb der freigegebenen Bereiche."))
    return neu


def test_datei_und_text_kommen_aufs_handy(bot, tmp_path):
    folien = tmp_path / "Datensicherung.pptx"
    folien.write_bytes(b"x")
    foto = tmp_path / "foto.png"
    foto.write_bytes(b"x")
    ergebnis = asyncio.run(telegram_plan.zustellen("Hier deine Präsentation", [str(folien), str(foto)]))
    assert ergebnis["ok"] and ergebnis["dateien"] == ["Datensicherung.pptx", "foto.png"]
    assert bot.texte == [("4711", "Hier deine Präsentation")]
    assert [(d["path"], d["kind"]) for _, d in bot.dateien] == [(str(folien), "datei"), (str(foto), "bild")]


def test_fehlende_oder_gesperrte_datei_wird_nicht_geschickt(bot, tmp_path):
    assert "finde ich nicht" in asyncio.run(telegram_plan.zustellen("", [str(tmp_path / "fehlt.pdf")]))["error"]
    fremd = tmp_path.parent / "fremd.txt"
    fremd.write_text("geheim", encoding="utf-8")
    try:
        assert "ausserhalb" in asyncio.run(telegram_plan.zustellen("", [str(fremd)]))["error"]
    finally:
        fremd.unlink()
    assert bot.dateien == []


def test_bildschirmfoto_aufs_handy(bot, tmp_path, monkeypatch):
    bild = tmp_path / "screenshot-handy.png"
    bild.write_bytes(b"x")
    monkeypatch.setattr(telegram_plan, "_bildschirmfoto", lambda: bild)
    ergebnis = asyncio.run(telegram_plan.zustellen("", [], True))
    assert ergebnis["dateien"] == ["screenshot-handy.png"]
    assert bot.dateien[0][1]["kind"] == "bild"


def test_werkzeug_nimmt_dateien_und_ohne_alles_gibt_es_einen_hinweis(bot, tmp_path):
    pdf = tmp_path / "rechnung.pdf"
    pdf.write_bytes(b"x")
    laden()
    werkzeug = finden_async("telegram_senden")
    ergebnis = json.loads(asyncio.run(werkzeug(None, {"dateien": [str(pdf)]}, "telegram_senden")))
    assert ergebnis["dateien"] == ["rechnung.pdf"]
    leer = asyncio.run(telegram_plan.zustellen("", []))
    assert "Sag mir" in leer["error"]


def test_route_schickt_aufs_handy(bot, tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    datei = tmp_path / "liste.md"
    datei.write_text("- Brot", encoding="utf-8")
    antwort = TestClient(create_app()).post("/api/system/telegram/senden", json={"pfade": [str(datei)]})
    assert antwort.status_code == 200 and antwort.json()["dateien"] == ["liste.md"]
    fehler = TestClient(create_app()).post("/api/system/telegram/senden", json={"pfade": [str(tmp_path / "weg.md")]})
    assert fehler.status_code == 400


def test_dateien_als_json_text_werden_verstanden(bot, tmp_path):
    datei = tmp_path / "liste.md"
    datei.write_text("- Brot", encoding="utf-8")
    laden()
    werkzeug = finden_async("telegram_senden")
    ergebnis = json.loads(asyncio.run(werkzeug(None, {"dateien": json.dumps([str(datei)])}, "telegram_senden")))
    assert ergebnis["dateien"] == ["liste.md"]
