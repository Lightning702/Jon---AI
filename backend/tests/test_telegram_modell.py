import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import (
    NVIDIA_EMIL_MODELL,
    NVIDIA_JON_MODELL,
    Settings,
    get_settings,
    lebendes_modell,
)
from app.providers.base import ChatMessage, ChatRequest, ProviderError
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.services import chat_service as cs
from app.services import telegram_service as ts
from app.services.settings_service import get_settings_service


@pytest.fixture(autouse=True)
def _telegram_wahl_zuruecksetzen():
    einstellungen = get_settings_service()
    einstellungen.update({"telegram_provider": "", "telegram_model": ""})
    yield
    einstellungen.update(
        {"telegram_provider": "", "telegram_model": "", "auto_failover": True}
    )


def test_abgeschaltete_nvidia_modelle_werden_ersetzt():
    assert lebendes_modell("openai/gpt-oss-120b") == NVIDIA_JON_MODELL
    assert lebendes_modell("openai/gpt-oss-20b") == NVIDIA_EMIL_MODELL
    assert lebendes_modell("openai/gpt-oss-120b", "openrouter") == "openai/gpt-oss-120b"
    assert lebendes_modell("meta/muse-glimmer-30b") == "meta/muse-glimmer-30b"
    alt = Settings(
        default_jon_model="openai/gpt-oss-120b",
        default_emil_model="openai/gpt-oss-20b",
    )
    assert alt.jon_model == NVIDIA_JON_MODELL
    assert alt.emil_model == NVIDIA_EMIL_MODELL


def test_chat_ersetzt_ein_totes_modell_aus_den_einstellungen():
    from app.schemas import ChatIn, MessageIn

    service = cs.ChatService()
    payload = ChatIn(
        messages=[MessageIn(role="user", content="hi")],
        provider="nvidia",
        model="openai/gpt-oss-120b",
    )
    assert service.resolve(payload) == ("nvidia", NVIDIA_JON_MODELL)


def test_ersatzmodell_ist_nie_das_gewaehlte_modell():
    service = cs.ChatService()
    cs.mark_fast("nvidia", NVIDIA_JON_MODELL)
    cs.mark_fast("nvidia", NVIDIA_EMIL_MODELL)
    plan = asyncio.run(service.attempt_plan("nvidia", ["nvidia"], NVIDIA_JON_MODELL))
    assert plan == [("nvidia", NVIDIA_JON_MODELL), ("nvidia", NVIDIA_EMIL_MODELL)]
    plan = asyncio.run(service.attempt_plan("nvidia", ["nvidia"], NVIDIA_EMIL_MODELL))
    assert plan == [("nvidia", NVIDIA_EMIL_MODELL), ("nvidia", NVIDIA_JON_MODELL)]


def test_ollama_springt_vor_die_lahmen_wege():
    lahm = ("nvidia", "lahmes/modell")
    schnell = ("nvidia", "schnelles/modell")
    ersatz = ("ollama", "gemma4:e2b")
    cs.mark_fast(*schnell)
    cs.mark_fast(*ersatz)
    cs.mark_slow(*lahm)
    try:
        plan = cs.mit_ollama_ersatz([schnell, lahm], ersatz)
        assert plan == [schnell, ersatz, lahm]
        assert cs.mit_ollama_ersatz([schnell], None) == [schnell]
        assert cs.mit_ollama_ersatz([schnell, ersatz], ersatz) == [schnell, ersatz]
    finally:
        cs.mark_fast(*lahm)


class _FakeOllama:
    def __init__(self, modelle, da=True):
        self._modelle = modelle
        self._da = da

    def available(self):
        return self._da

    async def list_models(self):
        return list(self._modelle)


class _FakeNvidia:
    def available(self):
        return True

    async def list_models(self):
        return [NVIDIA_JON_MODELL, NVIDIA_EMIL_MODELL]


class _FakeRegistry:
    def __init__(self, ollama):
        self._anbieter = {"ollama": ollama, "nvidia": _FakeNvidia()}

    def all(self):
        return dict(self._anbieter)

    def get(self, name):
        if name not in self._anbieter:
            raise ProviderError(f"Unknown provider: {name}")
        return self._anbieter[name]


OLLAMA_MODELLE = [
    "x/z-image-turbo:latest",
    "gemini-3-flash-preview:cloud",
    "gemma3:270m",
    "gemma4:e2b",
]


def test_ollama_ersatz_nimmt_ein_chatfaehiges_modell(monkeypatch):
    from app.services.ollama_service import get_ollama_service

    monkeypatch.setattr(get_ollama_service(), "selected_model", lambda: "")
    registry = _FakeRegistry(_FakeOllama(OLLAMA_MODELLE))
    assert asyncio.run(cs.ollama_ersatz(registry, "nvidia")) == ("ollama", "gemma3:270m")
    monkeypatch.setattr(get_ollama_service(), "selected_model", lambda: "gemma4:e2b")
    assert asyncio.run(cs.ollama_ersatz(registry, "nvidia")) == ("ollama", "gemma4:e2b")
    assert asyncio.run(cs.ollama_ersatz(registry, "ollama")) is None
    aus = _FakeRegistry(_FakeOllama(OLLAMA_MODELLE, da=False))
    assert asyncio.run(cs.ollama_ersatz(aus, "nvidia")) is None
    get_settings_service().update({"auto_failover": False})
    assert asyncio.run(cs.ollama_ersatz(registry, "nvidia")) is None


class _LangsamerStrom:
    def __init__(self, pause):
        self._pause = pause
        self._fertig = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._fertig:
            raise StopAsyncIteration
        self._fertig = True
        await asyncio.sleep(self._pause)
        delta = SimpleNamespace(
            content="Hallo, ich bin da und beantworte deine Frage jetzt.",
            reasoning_content=None,
            tool_calls=None,
        )
        return SimpleNamespace(usage=None, choices=[SimpleNamespace(delta=delta)])


def _langsamer_anbieter(pause):
    async def create(**_payload):
        return _LangsamerStrom(pause)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    client.with_options = lambda **_kwargs: client
    anbieter = OpenAICompatibleProvider(name="nvidia", base_url="http://x", api_key="k")
    anbieter._client = lambda slot="jon": client
    return anbieter


async def _sammeln(anbieter, request):
    teile = []
    async for chunk in anbieter.stream(request):
        if chunk.kind == "content":
            teile.append(chunk.delta)
    return "".join(teile)


def test_telegram_wartet_laenger_auf_das_erste_wort(monkeypatch):
    monkeypatch.setattr(get_settings(), "first_token_timeout", 0.05)
    anbieter = _langsamer_anbieter(0.3)

    def anfrage(geduld):
        return ChatRequest(
            messages=[ChatMessage(role="user", content="Hallo")],
            model="m",
            first_token_timeout=geduld,
        )

    with pytest.raises(ProviderError):
        asyncio.run(_sammeln(anbieter, anfrage(0.0)))
    assert "beantworte" in asyncio.run(_sammeln(anbieter, anfrage(2.0)))
    assert cs.GEDULD_QUELLEN["telegram"] > Settings().first_token_timeout * 2


def _dienst_mit_fakes(monkeypatch, ablauf, gesendet):
    async def fake_handle(self, chat_id, text, voice=False):
        ablauf.append(("start", text))
        await asyncio.sleep(0.05)
        ablauf.append(("ende", text))

    async def fake_send(self, chat_id, text):
        gesendet.append(text)

    monkeypatch.setattr(ts.TelegramService, "_handle", fake_handle)
    monkeypatch.setattr(ts.TelegramService, "send", fake_send)
    return ts.TelegramService()


def test_neue_nachricht_bricht_die_laufende_antwort_nicht_ab(monkeypatch):
    ablauf: list = []
    gesendet: list = []
    dienst = _dienst_mit_fakes(monkeypatch, ablauf, gesendet)

    async def lauf():
        dienst._launch("1", "erste")
        dienst._launch("1", "zweite")
        await asyncio.gather(*dienst._running["1"])

    asyncio.run(lauf())
    assert ablauf == [
        ("start", "erste"),
        ("ende", "erste"),
        ("start", "zweite"),
        ("ende", "zweite"),
    ]
    assert any("vorige Nachricht" in text for text in gesendet)


def test_stopp_bricht_alle_wartenden_nachrichten_ab(monkeypatch):
    ablauf: list = []
    dienst = _dienst_mit_fakes(monkeypatch, ablauf, [])

    async def lauf():
        dienst._launch("1", "a")
        dienst._launch("1", "b")
        await asyncio.sleep(0.01)
        assert await dienst._cancel_running("1")
        await asyncio.sleep(0.1)
        assert not await dienst._cancel_running("1")

    asyncio.run(lauf())
    assert ablauf == [("start", "a")]


def test_modell_befehl_waehlt_ollama_auch_wenn_jon_nvidia_nutzt(monkeypatch):
    from app.providers import registry as registry_modul

    get_settings_service().update({"provider": "nvidia", "model": NVIDIA_JON_MODELL})
    monkeypatch.setattr(
        registry_modul, "get_registry", lambda: _FakeRegistry(_FakeOllama(OLLAMA_MODELLE))
    )
    monkeypatch.setattr(cs, "grundmodell", lambda provider, slot="emil": "")
    dienst = ts.TelegramService()

    antwort = asyncio.run(dienst._modell_befehl("/modell ollama gemma4"))
    assert "gemma4:e2b" in antwort
    assert ts.TelegramService.modellwahl() == ("ollama", "gemma4:e2b")

    antwort = asyncio.run(dienst._modell_befehl("/modell ollama"))
    assert ts.TelegramService.modellwahl() == ("ollama", "gemma3:270m")

    antwort = asyncio.run(dienst._modell_befehl("/modell ollama llama9"))
    assert "gibt es bei ollama nicht" in antwort
    assert ts.TelegramService.modellwahl() == ("ollama", "gemma3:270m")

    stand = asyncio.run(dienst._modell_befehl("/modell"))
    assert "ollama · gemma3:270m" in stand
    assert "gemma4:e2b" in stand
    assert "z-image" not in stand

    antwort = asyncio.run(dienst._modell_befehl("/modell auto"))
    assert "wie Jon" in antwort or "folgt wieder Jon" in antwort
    assert get_settings_service().get()["telegram_provider"] == ""


def test_modell_befehl_meldet_fehlendes_ollama(monkeypatch):
    from app.providers import registry as registry_modul

    monkeypatch.setattr(
        registry_modul,
        "get_registry",
        lambda: _FakeRegistry(_FakeOllama([], da=False)),
    )
    antwort = asyncio.run(ts.TelegramService()._modell_befehl("/modell ollama"))
    assert "nicht eingerichtet" in antwort
    assert get_settings_service().get()["telegram_provider"] == ""


def test_telegram_nimmt_bei_ollama_ohne_modell_das_ollama_modell(monkeypatch):
    from app.services.ollama_service import get_ollama_service

    monkeypatch.setattr(get_ollama_service(), "selected_model", lambda: "gemma4:e2b")
    get_settings_service().update(
        {"provider": "nvidia", "telegram_provider": "ollama", "telegram_model": ""}
    )
    assert ts.TelegramService.modellwahl() == ("ollama", "gemma4:e2b")


def test_anbieter_befehl_zeigt_und_wechselt_den_anbieter(monkeypatch):
    from app.providers import registry as registry_modul

    get_settings_service().update({"provider": "nvidia", "model": NVIDIA_JON_MODELL})
    monkeypatch.setattr(
        registry_modul, "get_registry", lambda: _FakeRegistry(_FakeOllama(OLLAMA_MODELLE))
    )
    monkeypatch.setattr(cs, "grundmodell", lambda provider, slot="emil": "")
    dienst = ts.TelegramService()

    stand = asyncio.run(dienst._anbieter_befehl("/anbieter"))
    assert "• ollama" in stand
    assert "• nvidia ✓" in stand

    antwort = asyncio.run(dienst._anbieter_befehl("/anbieter ollama"))
    assert "ollama · gemma3:270m" in antwort
    assert ts.TelegramService.modellwahl()[0] == "ollama"

    asyncio.run(dienst._anbieter_befehl("/anbieter auto"))
    assert ts.TelegramService.modellwahl()[0] == "nvidia"
