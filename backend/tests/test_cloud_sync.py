from __future__ import annotations

import asyncio
import base64
import json

import pytest

from app.services import cloud_sync
from app.services.memory_service import MemoryService


def test_verschluesselung_haelt_inhalt_geheim_und_prueft_das_passwort():
    text = cloud_sync.verschluesseln({"geheim": "Mein Hund heißt Bello"}, "langes-passwort")
    assert "Bello" not in base64.b64decode(text).decode()
    assert cloud_sync.entschluesseln(text, "langes-passwort") == {"geheim": "Mein Hund heißt Bello"}
    with pytest.raises(ValueError, match="Falsches"):
        cloud_sync.entschluesseln(text, "anderes-passwort")
    with pytest.raises(ValueError, match="8 Zeichen"):
        cloud_sync.verschluesseln({}, "kurz")


def test_paket_ohne_geheimnisse_und_einspielen_ohne_doppelte_erinnerungen(tmp_path, monkeypatch):
    (tmp_path / "user_settings.json").write_text(json.dumps({"telegram_bot_token": "geheim", "theme": "dunkel", "telegram_chat_id": "1"}), encoding="utf-8")
    (tmp_path / "persona.json").write_text('{"name": "Felix"}', encoding="utf-8")
    MemoryService().add("Felix programmiert gern Spiele")
    daten = cloud_sync.paket(tmp_path)
    assert "telegram_bot_token" not in daten["einstellungen"] and "telegram_chat_id" not in daten["einstellungen"]
    assert daten["einstellungen"]["theme"] == "dunkel" and daten["dateien"]["persona.json"] == '{"name": "Felix"}'
    assert any("Spiele" in e["content"] for e in daten["erinnerungen"])
    ziel = tmp_path / "ziel"
    ziel.mkdir()
    daten["erinnerungen"].append({"content": "Felix wohnt in Österreich", "source": "chat", "wichtigkeit": 0.7})
    ergebnis = cloud_sync.einspielen(daten, ziel)
    assert ergebnis["erinnerungen"] == 1
    assert (ziel / "persona.json").read_text(encoding="utf-8") == '{"name": "Felix"}'
    assert cloud_sync.einspielen(daten, ziel)["erinnerungen"] == 0


def test_hochladen_schickt_nur_verschluesselte_daten(monkeypatch):
    gesendet = {}

    async def rufen(name, daten):
        gesendet.update(daten)
        return {"zeit": 1}

    premium = cloud_sync.get_premium()
    monkeypatch.setattr(premium, "rufen", rufen)
    monkeypatch.setattr(premium, "token", lambda: "JON1.x.y")
    MemoryService().add("Mein Lieblingsessen ist Pizza")
    asyncio.run(cloud_sync.hochladen("langes-passwort"))
    assert gesendet["aktion"] == "hochladen" and "Pizza" not in base64.b64decode(gesendet["daten"]).decode()
