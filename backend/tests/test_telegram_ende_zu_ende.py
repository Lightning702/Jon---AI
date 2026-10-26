from __future__ import annotations

import asyncio
import time

import pytest

from app.services import bildschirm_agent, pc_strom
from app.services import telegram_service as ts
from app.services.settings_service import get_settings_service

CHAT = 4242


class Antwort:
    def __init__(self, daten: dict):
        self._daten = daten
        self.status_code = 200
        self.content = b""

    def json(self) -> dict:
        return self._daten


class Telegram:
    def __init__(self, texte: list[str]):
        self.updates = [{"update_id": i + 1, "message": {"message_id": i + 1, "chat": {"id": CHAT, "type": "private"}, "from": {"id": CHAT}, "date": int(time.time()), "text": t}} for i, t in enumerate(texte)]
        self.gesendet: list[tuple[float, str]] = []

    def klasse(self, besitzer):
        class Client:
            is_closed = False

            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def aclose(self):
                return None

            async def get(self, url, params=None, **kwargs):
                if url.endswith("/getUpdates"):
                    neu, besitzer.updates = besitzer.updates, []
                    return Antwort({"ok": True, "result": neu})
                return Antwort({"ok": True, "result": {}})

            async def post(self, url, json=None, data=None, files=None, **kwargs):
                if url.endswith("/sendMessage") and json:
                    besitzer.gesendet.append((time.perf_counter(), str(json.get("text", ""))))
                return Antwort({"ok": True, "result": {"message_id": len(besitzer.gesendet)}})

        return Client


@pytest.fixture
def telegram(monkeypatch):
    einstellungen = get_settings_service()
    alt = {k: einstellungen.get().get(k) for k in ("telegram_bot_token", "telegram_chat_id", "telegram_aktionsvideo")}
    einstellungen.update({"telegram_bot_token": "123456:test", "telegram_chat_id": str(CHAT), "telegram_aktionsvideo": False})

    def bauen(texte: list[str]):
        attrappe = Telegram(texte)
        monkeypatch.setattr(ts.httpx, "AsyncClient", attrappe.klasse(attrappe))
        dienst = ts.TelegramService()
        return dienst, attrappe

    yield bauen
    einstellungen.update({k: v for k, v in alt.items() if v is not None})
    if alt.get("telegram_bot_token") is None:
        einstellungen.update({"telegram_bot_token": ""})


async def _abarbeiten(dienst: ts.TelegramService) -> None:
    await dienst.poll_once()
    for _ in range(50):
        laufend = [t for liste in dienst._running.values() for t in liste if not t.done()]
        if not laufend:
            break
        await asyncio.gather(*laufend, return_exceptions=True)


def test_herunterfahren_ueber_telegram_ohne_modell_und_sofort(telegram, monkeypatch):
    befehle: list[tuple] = []
    monkeypatch.setattr(pc_strom, "_shutdown", lambda *a: befehle.append(a))
    monkeypatch.setattr(pc_strom.subprocess, "run", lambda *a, **k: befehle.append(("verboten", a)))

    def kein_modell(*_a, **_k):
        raise AssertionError("Fuer Herunterfahren darf kein Modell gefragt werden")

    monkeypatch.setattr(ts.TelegramService, "_answer", kein_modell, raising=False)
    dienst, attrappe = telegram(["Fahr den PC herunter"])
    beginn = time.perf_counter()
    asyncio.run(_abarbeiten(dienst))
    assert befehle and befehle[0][:3] == ("/s", "/t", "30")
    antworten = [t for _, t in attrappe.gesendet]
    assert any("30" in t and ("herunter" in t.lower() or "aus" in t.lower()) for t in antworten), antworten
    assert attrappe.gesendet[-1][0] - beginn < 2.0


def test_klick_auf_zuruf_ueber_telegram(telegram, monkeypatch):
    geklickt: list[tuple] = []

    async def klicken(ziel, art="links", fenster=""):
        geklickt.append((ziel, art, fenster))
        return {"geklickt": "Start", "fenster": "Testseite"}

    monkeypatch.setattr(bildschirm_agent, "klicken", klicken)
    dienst, attrappe = telegram(["Klick auf den Start Button"])
    asyncio.run(_abarbeiten(dienst))
    assert geklickt and "start" in geklickt[0][0].lower()
    assert any("Geklickt: Start" in t for _, t in attrappe.gesendet), attrappe.gesendet


def test_abbrechen_ueber_telegram(telegram, monkeypatch):
    befehle: list[tuple] = []
    monkeypatch.setattr(pc_strom, "_shutdown", lambda *a: befehle.append(a))
    dienst, attrappe = telegram(["/abbrechen"])
    asyncio.run(_abarbeiten(dienst))
    assert ("/a",) in befehle


def test_telegram_denkt_nur_wenn_noetig():
    from app.services.chat_service import denken_noetig, schnell_denken

    assert schnell_denken(denken_noetig("Wie spät ist es in Tokio?", None, False), "emil") is False
    assert schnell_denken(denken_noetig("Code mir ein Snake-Spiel in Python", None, False), "emil") is True
    assert schnell_denken(denken_noetig("Wie spät ist es in Tokio?", None, False), "jon") is None


def test_telegram_nimmt_fuer_text_nicht_das_langsame_bildmodell():
    from app.core.config import NVIDIA_EMIL_MODELL, NVIDIA_SEHEN_MODELL

    einstellungen = get_settings_service()
    alt = {k: einstellungen.get().get(k) for k in ("telegram_provider", "telegram_model", "pet_provider", "pet_model")}
    try:
        einstellungen.update({"telegram_provider": "nvidia", "telegram_model": NVIDIA_SEHEN_MODELL, "pet_provider": "nvidia", "pet_model": NVIDIA_SEHEN_MODELL})
        assert ts.TelegramService.modellwahl() == ("nvidia", NVIDIA_EMIL_MODELL)
        assert einstellungen.pet_selection() == ("nvidia", NVIDIA_EMIL_MODELL)
        einstellungen.update({"telegram_model": "nvidia/nemotron-3-ultra-550b-a55b"})
        assert ts.TelegramService.modellwahl() == ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b")
    finally:
        einstellungen.update({k: v if v is not None else "" for k, v in alt.items()})


def test_unerreichbarer_anbieter_wird_beim_ausweichen_ausgelassen():
    import httpx

    from app.providers.openai_compatible import OpenAICompatibleProvider

    anbieter = OpenAICompatibleProvider(name="felworks", base_url="http://127.0.0.1:9/v1", api_key="x")
    assert not anbieter.unerreichbar()
    try:
        try:
            raise httpx.ConnectTimeout("weg")
        except httpx.ConnectTimeout as ursache:
            raise RuntimeError("felworks antwortet nicht") from ursache
    except RuntimeError as fehler:
        anbieter.ausfall_merken(fehler)
    assert anbieter.unerreichbar()
    anbieter.unerreichbar_seit = 0.0
    anbieter.ausfall_merken(RuntimeError("nur langsam"))
    assert not anbieter.unerreichbar()


def test_ausweichen_ueberspringt_ausgefallenen_anbieter(monkeypatch):
    import time as zeit
    from types import SimpleNamespace

    from app.services import chat_service as cs

    class Anbieter:
        def __init__(self, weg):
            self.unerreichbar_seit = zeit.monotonic() if weg else 0.0

        def available(self):
            return True

        async def list_models(self):
            return ["m"]

        def unerreichbar(self, sekunden=120.0):
            return bool(self.unerreichbar_seit)

    alle = {"nvidia": Anbieter(False), "felworks": Anbieter(True), "openai": Anbieter(False)}
    monkeypatch.setattr(cs, "ALTERNATIVE_PROVIDERS", ("felworks", "openai"))
    registry = SimpleNamespace(get=lambda name: alle[name])
    namen = asyncio.run(cs.route_providers(registry, "nvidia", "m"))
    assert "felworks" not in namen and "openai" in namen
