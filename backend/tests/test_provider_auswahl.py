import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.openai_compatible import OpenAICompatibleProvider
from app.services import settings_service as ss


def _service(tmp_path, monkeypatch, data):
    monkeypatch.setattr(ss, "SETTINGS_FILE", tmp_path / "settings.json")
    service = ss.SettingsService()
    service.update(data)
    return service


def test_eigener_pet_anbieter_gewinnt_trotz_ollama(tmp_path, monkeypatch):
    service = _service(
        tmp_path,
        monkeypatch,
        {
            "provider": "ollama",
            "model": "gemma3:270m",
            "pet_provider": "nvidia",
            "pet_model": "openai/gpt-oss-20b",
        },
    )
    assert service.pet_selection() == ("nvidia", "openai/gpt-oss-20b")
    assert service.selection() == ("ollama", "gemma3:270m")


def test_ohne_eigene_wahl_folgt_mini_jon_weiter_jon(tmp_path, monkeypatch):
    service = _service(
        tmp_path, monkeypatch, {"provider": "ollama", "model": "gemma3:270m"}
    )
    assert service.pet_selection() == ("ollama", "gemma3:270m")
    assert service.telegram_selection() == ("ollama", "gemma3:270m")


def test_bei_nvidia_gelten_eigene_companion_modelle(tmp_path, monkeypatch):
    service = _service(
        tmp_path,
        monkeypatch,
        {
            "provider": "nvidia",
            "model": "z-ai/glm-5.2",
            "pet_model": "openai/gpt-oss-20b",
        },
    )
    assert service.pet_selection() == ("nvidia", "openai/gpt-oss-20b")


class _ToolsError(Exception):
    def __init__(self):
        super().__init__(
            "Error code: 400 - {'error': {'message': "
            "'registry.ollama.ai/library/gemma3:270m does not support tools', "
            "'type': 'invalid_request_error'}}"
        )
        self.status_code = 400


def test_modell_ohne_tool_unterstuetzung_antwortet_ohne_tools():
    provider = OpenAICompatibleProvider(
        "ollama", "http://127.0.0.1:11434/v1", api_key="ollama"
    )
    calls = []

    async def create(**payload):
        calls.append(dict(payload))
        if payload.get("tools"):
            raise _ToolsError()
        return "ok"

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    payload = {
        "model": "gemma3:270m",
        "messages": [],
        "tools": [{"type": "function"}],
        "tool_choice": "auto",
    }
    result = asyncio.run(provider._create_with_retry(client, payload))
    assert result == "ok"
    assert len(calls) == 2
    assert "tools" not in calls[1]
    assert "tool_choice" not in calls[1]
    assert "gemma3:270m" in provider._no_tool_models
