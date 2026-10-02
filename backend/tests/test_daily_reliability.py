from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services.tool_result import succeeded


@pytest.mark.parametrize("result", [
    {"ok": False}, {"success": False}, {"exit_code": 9}, {"returncode": "1"},
    {"timed_out": True}, {"status": "failed"},
    {"output": "a" * 500, "error": "late failure"},
])
def test_failed_results_never_count_as_success(result):
    assert not succeeded(json.dumps(result))


def test_successful_output_may_mention_error():
    assert succeeded(json.dumps({"ok": True, "output": "error handler repaired", "exit_code": 0}))
    assert succeeded(json.dumps({"error": None, "ok": True}))


def test_failed_response_is_not_cached(monkeypatch, tmp_path):
    from app.services import cache_service

    monkeypatch.setattr(cache_service, "DATEI", tmp_path / "cache.json")
    cache = cache_service.CacheService()
    cache.merken("web_search", {"query": "hello"}, json.dumps({"ok": False}))
    assert cache.holen("web_search", {"query": "hello"}) is None


def test_no_provider_replay_after_an_executed_tool():
    from app.services.chat_service import ChatService

    calls = []

    class Provider:
        async def stream(self, request, executor):
            await executor("create_file", {})
            raise ConnectionError("stream disconnected after action")
            yield

    async def executor(name, args):
        calls.append(name)
        return "created"

    async def run():
        service = object.__new__(ChatService)
        service._registry = SimpleNamespace(get=lambda name: Provider())
        with pytest.raises(ConnectionError):
            async for _ in service._stream_route([("first", "one"), ("second", "two")], SimpleNamespace(model=""), executor, {}):
                pass
        assert calls == ["create_file"]

    asyncio.run(run())


def test_invalid_context_settings_are_atomic(tmp_path):
    from app.services.mini_jon_agent import MiniJonAgent

    agent = MiniJonAgent(tmp_path / "agent.json")
    with pytest.raises(ValueError):
        agent.configure({"enabled": True, "blacklist": 12})
    assert not agent.config["enabled"]
    assert not agent.path.exists()


def test_privacy_check_runs_before_a_cache_hit(monkeypatch):
    from app.services import cache_service, datenschutz_service
    from app.services.tools import ToolBox

    monkeypatch.setattr(cache_service, "get_cache_service", lambda: SimpleNamespace(holen=lambda *args: '{"secret":"old cached data"}'))
    monkeypatch.setattr(datenschutz_service, "darf_raus", lambda *args: (False, "blocked", {}))
    box = object.__new__(ToolBox)
    box._source, box._root = "app", None
    result = asyncio.run(box.execute("web_search", {"query": "blocked"}))
    assert "blocked" in result and "secret" not in result


def test_chat_cannot_approve_shell_commands():
    from app.services.harness.chat import execute

    result = asyncio.run(execute({"action": "approve"}, "app", None))
    assert "error" in result


def test_telegram_tool_cannot_lose_channel_ownership():
    from app.services.harness.chat import execute

    result = asyncio.run(execute({"action": "start", "goal": "write a file"}, "telegram", None))
    assert "error" in result


def test_harness_setup_failure_is_terminal(monkeypatch, tmp_path):
    from app.services.harness.service import HarnessService
    from app.services import settings_service

    monkeypatch.setattr(settings_service, "get_settings_service", lambda: (_ for _ in ()).throw(ValueError("bad configuration")))

    async def run():
        service = HarnessService(tmp_path / "tasks")
        task = service.start("Check project", str(tmp_path))
        await service.running[task["id"]]
        assert service.get(task["id"])["status"] == "failed"
        await service.close()

    asyncio.run(run())
