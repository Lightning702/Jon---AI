from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.services import telegram_group_service as tgs
from app.services import telegram_service as ts
from app.services.mini_jon_service import (
    SLEEP_GIF,
    MiniJonService,
    get_mini_jon_service,
)

client = TestClient(app)


def test_gruppen_routen_registriert():
    paths = set(app.openapi()["paths"])
    assert "/api/mini-jon/status" in paths


def test_group_memory_dedup_und_verlauf():
    memory = tgs.GroupMemory()
    assert memory.record("-901", "Anna", "Hi zusammen", message_id=11)
    assert not memory.record("-901", "Anna", "Hi zusammen", message_id=11)
    assert memory.record("-901", "Ben", "Moin", message_id=12)
    transcript = memory.transcript("-901")
    assert "Anna: Hi zusammen" in transcript
    assert "Ben: Moin" in transcript
    for i in range(tgs.GROUP_KEEP + 10):
        memory.record("-902", "Anna", f"Nachricht {i}", message_id=100 + i)
    assert len(memory._data["-902"]) == tgs.GROUP_KEEP


def test_mention_erkennung():
    entities = [{"type": "mention", "offset": 0, "length": 11}]
    assert tgs.is_mentioned("@MiniJonBot wie gehts?", entities, "minijonbot")
    assert tgs.is_mentioned("hey @MiniJonBot!", None, "MiniJonBot")
    assert not tgs.is_mentioned("hey Leute", None, "MiniJonBot")
    assert not tgs.is_mentioned("@JonBot mach was", None, "MiniJonBot")
    assert not tgs.is_mentioned("@MiniJonBot hi", None, "")


def test_strip_mention():
    assert (
        tgs.strip_mention("@MiniJonBot wie spät ist es?", "MiniJonBot")
        == "wie spät ist es?"
    )
    assert tgs.strip_mention("sag mal @minijonbot, alles klar?", "MiniJonBot") == (
        "sag mal alles klar?"
    )


def test_mini_jon_status_wechsel():
    service = get_mini_jon_service()
    assert service.set_status("schläft")["status"] == "schlaeft"
    assert service.is_sleeping()
    assert MiniJonService().is_sleeping()
    assert "error" in service.set_status("quatsch")
    assert service.set_status("wach")["status"] == "wach"
    assert not service.is_sleeping()


def test_schlaf_animation_gif():
    SLEEP_GIF.unlink(missing_ok=True)
    path = get_mini_jon_service().sleep_animation()
    assert path is not None and path.exists()
    raw = path.read_bytes()
    assert raw[:6] in (b"GIF87a", b"GIF89a")
    from PIL import Image

    with Image.open(path) as img:
        assert getattr(img, "n_frames", 1) > 1


def _bot_mit_fakes(monkeypatch, sent, calls):
    async def fake_username(self):
        return "MiniJonBot"

    async def fake_api(self, method, payload=None, data=None, files=None):
        return {"ok": True}

    async def fake_send(self, chat_id, text):
        sent.append(text)

    async def fake_answer(variant, username, sender, question, **kwargs):
        calls.append((variant, sender, question))
        return f"Antwort für {sender}"

    monkeypatch.setattr(tgs.GroupBot, "username", fake_username)
    monkeypatch.setattr(tgs.GroupBot, "_api", fake_api)
    monkeypatch.setattr(tgs.GroupBot, "send", fake_send)
    monkeypatch.setattr(tgs, "group_answer", fake_answer)
    return tgs.MiniJonBot()


def test_bot_liest_mit_und_antwortet_nur_bei_mention(monkeypatch):
    sent: list[str] = []
    calls: list[tuple] = []
    bot = _bot_mit_fakes(monkeypatch, sent, calls)
    get_mini_jon_service().set_status("wach")
    asyncio.run(
        bot.handle_message(
            {
                "chat": {"id": -910, "type": "group"},
                "from": {"first_name": "Anna"},
                "message_id": 1,
                "text": "Hallo zusammen, wie war euer Tag?",
            }
        )
    )
    assert sent == [] and calls == []
    assert "Anna: Hallo zusammen" in tgs.get_group_memory().transcript("-910")
    asyncio.run(
        bot.handle_message(
            {
                "chat": {"id": -910, "type": "group"},
                "from": {"first_name": "Anna"},
                "message_id": 2,
                "text": "@MiniJonBot was meinst du dazu?",
            }
        )
    )
    assert len(sent) == 1 and "Antwort für Anna" in sent[0]
    assert calls and calls[0][0] == "junior"
    assert calls[0][2] == "was meinst du dazu?"
    assert "Mini Jon: Antwort für Anna" in tgs.get_group_memory().transcript("-910")


def test_mini_jon_schlaf_kommandos_und_gruppenschlaf(monkeypatch):
    sent: list[str] = []
    calls: list[tuple] = []
    bot = _bot_mit_fakes(monkeypatch, sent, calls)
    monkeypatch.setattr(MiniJonService, "sleep_animation", lambda self: None)
    asyncio.run(
        bot.handle_message(
            {
                "chat": {"id": -911, "type": "group"},
                "from": {"first_name": "Anna"},
                "message_id": 1,
                "text": "/schlafen@MiniJonBot",
            }
        )
    )
    assert get_mini_jon_service().is_sleeping()
    assert sent and "eingeschlafen" in sent[-1]
    asyncio.run(
        bot.handle_message(
            {
                "chat": {"id": -911, "type": "group"},
                "from": {"first_name": "Ben"},
                "message_id": 2,
                "text": "@MiniJonBot bist du da?",
            }
        )
    )
    assert "aufwachen" in sent[-1].lower()
    assert calls == []
    asyncio.run(
        bot.handle_message(
            {
                "chat": {"id": -911, "type": "group"},
                "from": {"first_name": "Ben"},
                "message_id": 3,
                "text": "/aufwachen@MiniJonBot",
            }
        )
    )
    assert not get_mini_jon_service().is_sleeping()
    assert "wach" in sent[-1].lower()


def test_fremdes_kommando_wird_ignoriert(monkeypatch):
    sent: list[str] = []
    calls: list[tuple] = []
    bot = _bot_mit_fakes(monkeypatch, sent, calls)
    get_mini_jon_service().set_status("wach")
    asyncio.run(
        bot.handle_message(
            {
                "chat": {"id": -912, "type": "group"},
                "from": {"first_name": "Anna"},
                "message_id": 1,
                "text": "/schlafen@JonBot",
            }
        )
    )
    assert sent == []
    assert not get_mini_jon_service().is_sleeping()


def test_jon_bot_gruppe_mention_und_bindung(monkeypatch):
    from app.services.settings_service import get_settings_service

    service = ts.TelegramService()
    sent: list[str] = []

    async def fake_username(self):
        return "JonBot"

    async def fake_api(self, method, payload):
        if method == "sendMessage":
            sent.append(payload["text"])

    async def fake_answer(variant, username, sender, question, **kwargs):
        return f"[{variant}] Jon antwortet {sender}"

    monkeypatch.setattr(ts.TelegramService, "bot_username", fake_username)
    monkeypatch.setattr(ts.TelegramService, "_api", fake_api)
    monkeypatch.setattr(tgs, "group_answer", fake_answer)
    bound_before = get_settings_service().get().get("telegram_chat_id", "")
    asyncio.run(
        service._handle_group_message(
            {
                "chat": {"id": -920, "type": "supergroup"},
                "from": {"first_name": "Ben"},
                "message_id": 5,
                "text": "einfach nur Gruppengespräch",
            }
        )
    )
    assert sent == []
    asyncio.run(
        service._handle_group_message(
            {
                "chat": {"id": -920, "type": "supergroup"},
                "from": {"first_name": "Ben"},
                "message_id": 6,
                "text": "@jonbot was geht?",
                "entities": [{"type": "mention", "offset": 0, "length": 7}],
            }
        )
    )
    assert sent and "[papa] Jon antwortet Ben" in sent[0]
    assert get_settings_service().get().get("telegram_chat_id", "") == bound_before
    transcript = tgs.get_group_memory().transcript("-920")
    assert "Ben: einfach nur Gruppengespräch" in transcript
    assert "Jon: [papa] Jon antwortet Ben" in transcript


def test_mini_jon_endpoints():
    res = client.get("/api/mini-jon/status").json()
    assert res["status"] in ("wach", "schlaeft")
    res = client.post("/api/mini-jon/status", json={"status": "schläft"}).json()
    assert res["status"] == "schlaeft"
    assert (
        client.post("/api/mini-jon/status", json={"status": "quatsch"}).status_code
        == 400
    )
    res = client.post("/api/mini-jon/status", json={"status": "wach"}).json()
    assert res["status"] == "wach"
