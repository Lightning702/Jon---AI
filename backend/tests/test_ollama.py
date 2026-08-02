from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app
from app.providers.base import ChatMessage, ChatRequest, ProviderError
from app.providers.ollama_provider import OllamaProvider
from app.services import ollama_service as os_mod
from app.services.ollama_service import OllamaConfigError, OllamaService

client = TestClient(app)


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(os_mod, "OLLAMA_FILE", tmp_path / "ollama.json")
    made = OllamaService()
    monkeypatch.setattr(os_mod, "_service", made)
    return made


def test_standardwerte_und_url(service):
    config = service.config()
    assert config["enabled"] is True
    assert config["port"] == 11434
    assert config["url"].endswith(":11434")
    assert config["api_base"].endswith("/v1")
    assert config["keep_alive"] == "5m"


def test_einstellungen_bleiben_dauerhaft(service, tmp_path, monkeypatch):
    service.update(
        {
            "host": "192.168.1.50",
            "port": 12345,
            "model": "llama3.2",
            "temperature": 0.2,
            "top_k": 12,
            "context_length": 8192,
            "keep_alive": "30m",
            "system_prompt": "Sei kurz.",
            "stream": False,
        }
    )
    monkeypatch.setattr(os_mod, "OLLAMA_FILE", tmp_path / "ollama.json")
    wieder = OllamaService().config()
    assert wieder["host"] == "192.168.1.50"
    assert wieder["port"] == 12345
    assert wieder["model"] == "llama3.2"
    assert wieder["temperature"] == 0.2
    assert wieder["top_k"] == 12
    assert wieder["context_length"] == 8192
    assert wieder["keep_alive"] == "30m"
    assert wieder["system_prompt"] == "Sei kurz."
    assert wieder["stream"] is False
    assert wieder["url"] == "http://192.168.1.50:12345"


def test_server_url_wird_zerlegt(service):
    config = service.update({"url": "https://ollama.example.com:8443"})
    assert config["scheme"] == "https"
    assert config["host"] == "ollama.example.com"
    assert config["port"] == 8443


def test_tailscale_und_lan_adressen_erlaubt(service):
    assert service.update({"host": "100.101.102.103"})["host"] == "100.101.102.103"
    assert service.update({"host": "192.168.178.42"})["host"] == "192.168.178.42"
    assert service.update({"host": "localhost"})["host"] == "localhost"


@pytest.mark.parametrize(
    "values",
    [
        {"port": 0},
        {"port": 99999},
        {"host": ""},
        {"host": "kein host"},
        {"temperature": 5},
        {"top_p": 2},
        {"context_length": 10},
        {"max_tokens": 0},
        {"max_tokens": -5},
        {"timeout": 0},
        {"keep_alive": "fuenf minuten"},
        {"scheme": "ftp"},
    ],
)
def test_falsche_eingaben_werden_abgelehnt(service, values):
    with pytest.raises(OllamaConfigError):
        service.update(values)


def test_falsche_eingabe_aendert_nichts(service):
    vorher = service.config()
    with pytest.raises(OllamaConfigError):
        service.update({"host": "10.0.0.5", "port": -1})
    assert service.config()["host"] == vorher["host"]


def test_chat_optionen_folgen_den_einstellungen(service):
    service.update(
        {
            "temperature": 0.3,
            "top_p": 0.5,
            "top_k": 7,
            "max_tokens": 512,
            "context_length": 16384,
            "seed": 99,
        }
    )
    options = service.chat_options()
    assert options["temperature"] == 0.3
    assert options["top_p"] == 0.5
    assert options["top_k"] == 7
    assert options["num_predict"] == 512
    assert options["num_ctx"] == 16384
    assert options["seed"] == 99
    service.update({"seed": -1})
    assert "seed" not in service.chat_options()


def test_max_tokens_minus_eins_heisst_unbegrenzt(service):
    assert service.config()["max_tokens"] == 32768
    assert service.update({"max_tokens": -1})["max_tokens"] == -1
    assert service.chat_options()["num_predict"] == -1


def test_status_bei_totem_server(service):
    service.update({"host": "127.0.0.1", "port": 1})
    status = asyncio.run(service.status(force=True))
    assert status["state"] == "offline"
    assert status["error"]
    assert status["models"] == []


def test_status_wenn_ausgeschaltet(service):
    service.update({"enabled": False})
    status = asyncio.run(service.status(force=True))
    assert status["state"] == "disabled"
    assert "ausgeschaltet" in status["error"].lower()


def _transport(handler):
    return httpx.MockTransport(handler)


def _patch_client(monkeypatch, handler):
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = _transport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def _ndjson(lines: list[dict]) -> bytes:
    return "".join(json.dumps(line) + "\n" for line in lines).encode("utf-8")


def _collect(provider, request, executor=None):
    async def run():
        return [chunk async for chunk in provider.stream(request, executor)]

    return asyncio.run(run())


def _request(**kwargs):
    base = dict(
        messages=[ChatMessage(role="user", content="Hallo")],
        model="llama3.2",
        temperature=0.4,
        top_p=0.8,
    )
    base.update(kwargs)
    return ChatRequest(**base)


def test_stream_sendet_offizielle_ollama_optionen(service, monkeypatch):
    service.update(
        {
            "top_k": 11,
            "context_length": 12288,
            "keep_alive": "42m",
            "system_prompt": "Antworte knapp.",
        }
    )
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            content=_ndjson(
                [
                    {"message": {"content": "Hallo Welt"}, "done": False},
                    {
                        "message": {"content": ""},
                        "done": True,
                        "prompt_eval_count": 7,
                        "eval_count": 3,
                    },
                ]
            ),
        )

    _patch_client(monkeypatch, handler)
    chunks = _collect(OllamaProvider(), _request(max_tokens=321))
    assert seen["path"] == "/api/chat"
    assert seen["model"] == "llama3.2"
    assert seen["keep_alive"] == "42m"
    assert seen["options"]["top_k"] == 11
    assert seen["options"]["num_ctx"] == 12288
    assert seen["options"]["num_predict"] == 321
    assert seen["options"]["temperature"] == 0.4
    assert seen["options"]["top_p"] == 0.8
    assert seen["messages"][0] == {"role": "system", "content": "Antworte knapp."}
    text = "".join(c.delta for c in chunks if c.kind == "content")
    assert text == "Hallo Welt"
    usage = [c for c in chunks if c.kind == "usage"]
    assert usage and usage[0].prompt_tokens == 7 and usage[0].completion_tokens == 3


def test_streaming_kann_abgeschaltet_werden(service, monkeypatch):
    service.update({"stream": False})
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"message": {"content": "Fertig"}, "done": True, "eval_count": 2},
        )

    _patch_client(monkeypatch, handler)
    chunks = _collect(OllamaProvider(), _request())
    assert seen["stream"] is False
    assert "".join(c.delta for c in chunks if c.kind == "content") == "Fertig"


def test_werkzeuge_werden_ausgefuehrt(service, monkeypatch):
    runden: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        runden.append(payload)
        if len(runden) == 1:
            return httpx.Response(
                200,
                content=_ndjson(
                    [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "get_weather",
                                            "arguments": {"city": "Berlin"},
                                        }
                                    }
                                ],
                            },
                            "done": True,
                        }
                    ]
                ),
            )
        return httpx.Response(
            200,
            content=_ndjson(
                [{"message": {"content": "In Berlin sind es 18 Grad."}, "done": True}]
            ),
        )

    _patch_client(monkeypatch, handler)
    aufrufe: list[tuple[str, dict]] = []

    async def executor(name: str, args: dict) -> str:
        aufrufe.append((name, args))
        return "18 Grad"

    tools = [{"type": "function", "function": {"name": "get_weather"}}]
    chunks = _collect(OllamaProvider(), _request(tools=tools), executor)
    assert aufrufe == [("get_weather", {"city": "Berlin"})]
    assert [c.kind for c in chunks if c.kind in ("tool", "tool_result")] == [
        "tool",
        "tool_result",
    ]
    assert "18 Grad" in "".join(c.delta for c in chunks if c.kind == "content")
    assert runden[1]["messages"][-1]["role"] == "tool"
    assert runden[1]["messages"][-1]["content"] == "18 Grad"


def test_modell_ohne_werkzeuge_antwortet_trotzdem(service, monkeypatch):
    versuche: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        versuche.append(payload)
        if "tools" in payload:
            return httpx.Response(
                400, json={"error": "modell does not support tools"}
            )
        return httpx.Response(
            200, content=_ndjson([{"message": {"content": "Klappt"}, "done": True}])
        )

    _patch_client(monkeypatch, handler)

    async def executor(name: str, args: dict) -> str:
        return ""

    tools = [{"type": "function", "function": {"name": "x"}}]
    chunks = _collect(OllamaProvider(), _request(tools=tools), executor)
    assert len(versuche) == 2
    assert "tools" not in versuche[1]
    assert "".join(c.delta for c in chunks if c.kind == "content") == "Klappt"


def test_fehler_mitten_im_stream_bricht_sauber_ab(service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_ndjson(
                [
                    {"message": {"content": "Teil"}, "done": False},
                    {"error": "unerwarteter Serverfehler"},
                ]
            ),
        )

    _patch_client(monkeypatch, handler)
    with pytest.raises(ProviderError) as info:
        _collect(OllamaProvider(), _request())
    assert "unerwarteter Serverfehler" in str(info.value)


def test_fehlendes_modell_gibt_klare_meldung(service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": 'model "llama3.2" not found'})

    _patch_client(monkeypatch, handler)
    with pytest.raises(ProviderError) as info:
        _collect(OllamaProvider(), _request())
    assert "ollama pull llama3.2" in str(info.value)


def test_server_nicht_erreichbar_gibt_hilfe(service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nicht erreichbar", request=request)

    _patch_client(monkeypatch, handler)
    service.update({"auto_reconnect": False})
    with pytest.raises(ProviderError) as info:
        _collect(OllamaProvider(), _request())
    text = str(info.value)
    assert "Keine Verbindung" in text
    assert service.base_url() in text


def test_auto_reconnect_versucht_es_erneut(service, monkeypatch):
    versuche: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        versuche.append(1)
        if len(versuche) < 3:
            raise httpx.ConnectError("weg", request=request)
        return httpx.Response(
            200, content=_ndjson([{"message": {"content": "Da"}, "done": True}])
        )

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("app.providers.ollama_provider.RECONNECT_DELAY", 0.0)
    service.update({"auto_reconnect": True})
    chunks = _collect(OllamaProvider(), _request())
    assert len(versuche) == 3
    assert "".join(c.delta for c in chunks if c.kind == "content") == "Da"


def test_ohne_modell_klare_meldung(service):
    provider = OllamaProvider()
    with pytest.raises(ProviderError) as info:
        _collect(provider, _request(model=""))
    assert "kein Modell" in str(info.value).lower() or "Modell" in str(info.value)


def test_ausgeschaltet_blockt_anfragen(service):
    service.update({"enabled": False})
    provider = OllamaProvider()
    assert provider.available() is False
    with pytest.raises(ProviderError):
        _collect(provider, _request())


def test_modelle_kommen_von_der_offiziellen_api(service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2"}]},
        )

    _patch_client(monkeypatch, handler)
    assert asyncio.run(service.models(refresh=True)) == ["llama3.2", "qwen2.5:7b"]
    assert service.last_success()


def test_status_meldet_version_und_anzahl(service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.12.0"})
        return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})

    _patch_client(monkeypatch, handler)
    service.update({"model": "llama3.2"})
    status = asyncio.run(service.status(force=True))
    assert status["state"] == "online"
    assert status["version"] == "0.12.0"
    assert status["model_count"] == 1
    assert status["models"] == ["llama3.2"]
    assert status["last_success"]
    assert status["error"] == ""


def test_status_warnt_bei_fehlendem_modell(service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.12.0"})
        return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})

    _patch_client(monkeypatch, handler)
    service.update({"model": "mistral"})
    status = asyncio.run(service.status(force=True))
    assert status["state"] == "online"
    assert "ollama pull mistral" in status["error"]


def test_api_endpunkte(service):
    assert client.get("/api/ollama/config").status_code == 200
    res = client.put("/api/ollama/config", json={"host": "10.0.0.7", "port": 11434})
    assert res.status_code == 200
    assert res.json()["url"] == "http://10.0.0.7:11434"
    kaputt = client.put("/api/ollama/config", json={"port": 0})
    assert kaputt.status_code == 400
    assert "Port" in kaputt.json()["detail"] or "port" in kaputt.json()["detail"]
    assert client.get("/api/ollama/status").status_code == 200
    assert client.get("/api/ollama/models").status_code == 200
    hosts = client.get("/api/ollama/hosts")
    assert hosts.status_code == 200
    assert hosts.json()["hosts"][0]["host"] == "127.0.0.1"
    assert client.post("/api/ollama/reset").json()["port"] == 11434


def test_ausgeschaltet_verschwindet_aus_der_anbieterliste(service):
    from app.core.keys import KeyManager

    service.update({"enabled": False})
    assert KeyManager().key_for("ollama") is None
    eintrag = next(
        p for p in client.get("/api/providers").json() if p["provider"] == "ollama"
    )
    assert eintrag["configured"] is False
    service.update({"enabled": True})
    assert KeyManager().key_for("ollama") == "ollama"


def test_modellwahl_bleibt_zwischen_app_und_ollama_gleich(service):
    from app.services.settings_service import get_settings_service

    get_settings_service().update({"provider": "ollama", "model": "llama3.2"})
    client.put("/api/ollama/config", json={"model": "qwen2.5:7b"})
    assert get_settings_service().selection()[1] == "qwen2.5:7b"
    client.put("/api/settings", json={"model": "mistral"})
    assert service.config()["model"] == "mistral"


def test_registry_hat_weiterhin_genau_einen_ollama_eintrag():
    from app.providers.registry import ProviderRegistry

    registry = ProviderRegistry()
    namen = list(registry.all())
    assert namen.count("ollama") == 1
    assert type(registry.get("ollama")).__name__ == "OllamaProvider"
    assert set(namen) == {
        "nvidia",
        "openai",
        "deepseek",
        "mistral",
        "glm",
        "qwen",
        "ollama",
        "lmstudio",
        "openrouter",
        "groq",
        "together",
        "xai",
        "anthropic",
        "gemini",
    }
