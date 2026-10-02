from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from app.services.harness.service import HarnessService
from app.services.harness.workspace import Workspace
from app.services.mini_jon_agent import MiniJonAgent


def scripted(actions):
    iterator = iter(actions)

    async def complete(*args, **kwargs):
        return json.dumps(next(iterator))

    return complete


async def finish(service, task):
    await asyncio.wait_for(service.running[task["id"]], 10)
    return service.get(task["id"])


@pytest.mark.parametrize("source,slot", [("minijon", "emil"), ("app", "jon")])
def test_harness_and_specialist_use_channel_credentials(tmp_path, monkeypatch, source, slot):
    from app.services import mini_jon_agent

    agent = MiniJonAgent(tmp_path / "agent.json")
    monkeypatch.setattr(mini_jon_agent, "get_mini_jon_agent", lambda: agent)
    calls = []
    answers = iter([
        json.dumps({"tool": "delegate", "args": {"role": "Prüfung", "question": "Prüfe die Aufgabe.", "files": []}}),
        "Keine Dateien vorhanden.",
        json.dumps({"tool": "finish", "args": {"summary": "Geprüft."}}),
    ])

    async def model(*args, **kwargs):
        calls.append(kwargs["slot"])
        return next(answers)

    async def run():
        service = HarnessService(tmp_path / "tasks", model)
        task = service.start("Projekt prüfen", str(tmp_path), source=source)
        if source == "minijon":
            assert agent.state["task_id"] == task["id"]
        result = await finish(service, task)
        assert result["status"] == "done"
        assert result["specialists"][0]["status"] == "done"
        assert not agent.state["task_id"]

    asyncio.run(run())
    assert calls == [slot, slot, slot]


def test_workspace_requires_read_and_rejects_concurrent_edit(tmp_path):
    file = tmp_path / "app.py"
    file.write_text("a = 1\n", encoding="utf-8")
    workspace = Workspace(str(tmp_path))
    with pytest.raises(ValueError, match="lesen"):
        workspace.edit("app.py", "1", "2")
    workspace.read("app.py")
    file.write_text("a = 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="verändert"):
        workspace.edit("app.py", "3", "2")
    assert file.read_text() == "a = 3\n"


@pytest.mark.parametrize("path", ["../outside.py", ".git/config", ".env", "sub/.env.local", ".ssh/id_rsa", "cert.pem"])
def test_workspace_blocks_escape_and_secrets(tmp_path, path):
    with pytest.raises(PermissionError):
        Workspace(str(tmp_path)).path(path)


def test_workspace_does_not_follow_hardlinks(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("private", encoding="utf-8")
    os.link(target, tmp_path / "b.txt")
    with pytest.raises(PermissionError):
        Workspace(str(tmp_path)).read("b.txt")


def test_new_file_never_overwrites_existing(tmp_path):
    workspace = Workspace(str(tmp_path))
    workspace.create("src/a.py", "original")
    with pytest.raises(FileExistsError):
        workspace.create("src/a.py", "replacement")
    assert (tmp_path / "src/a.py").read_text() == "original"


def test_search_excludes_dependencies_and_secrets(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules/x.py").write_text("needle")
    (tmp_path / ".env").write_text("needle")
    (tmp_path / "main.py").write_text("needle")
    assert Workspace(str(tmp_path)).search("needle")["matches"] == [{"path": "main.py", "line": 1, "text": "needle"}]


def test_changes_cannot_claim_verified_success(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    service = HarnessService(tmp_path / "tasks", scripted([
        {"tool": "plan", "args": {"steps": ["Datei erstellen", "Prüfen"]}},
        {"tool": "create", "args": {"path": "result.txt", "content": "done"}},
        {"tool": "finish", "args": {"summary": "Fertig"}},
    ]))

    async def run():
        return await finish(service, service.start("Datei erstellen", str(root)))

    result = asyncio.run(run())
    assert result["status"] == "needs_review"
    assert (root / "result.txt").read_text() == "done"
    assert result["changes"][0]["diff"]


def test_approved_real_verification_and_stale_approval(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    service = HarnessService(tmp_path / "tasks", scripted([
        {"tool": "plan", "args": {"steps": ["Erstellen", "Testen"]}},
        {"tool": "create", "args": {"path": "result.txt", "content": "okay"}},
        {"tool": "verify", "args": {"command": "Write-Output geprüft" if os.name == "nt" else "printf geprüft"}},
        {"tool": "finish", "args": {"summary": "Erstellt und geprüft"}},
    ]))

    async def run():
        task = service.start("Erstellen", str(root))
        async for event in service.stream(task["id"]):
            if event["type"] == "approval_required":
                pending = event["pending"]
                with pytest.raises(ValueError):
                    service.approve(task["id"], "stale", True)
                service.approve(task["id"], pending["id"], True)
                with pytest.raises(ValueError):
                    service.approve(task["id"], pending["id"], True)
        return service.get(task["id"])

    result = asyncio.run(run())
    assert result["status"] == "done"
    assert result["checks"][0]["exit_code"] == 0


def test_declined_command_never_runs(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    command = "Set-Content marker.txt bad" if os.name == "nt" else "echo bad > marker.txt"
    service = HarnessService(tmp_path / "tasks", scripted([
        {"tool": "command", "args": {"command": command}},
        {"tool": "finish", "args": {"summary": "Abgelehnt", "incomplete": True}},
    ]))

    async def run():
        task = service.start("Test", str(root))
        async for event in service.stream(task["id"]):
            if event["type"] == "approval_required":
                service.approve(task["id"], event["pending"]["id"], False)
        return service.get(task["id"])

    result = asyncio.run(run())
    assert result["status"] == "needs_review"
    assert not (root / "marker.txt").exists()


def test_cancel_pending_approval_is_terminal(tmp_path):
    service = HarnessService(tmp_path / "tasks", scripted([{"tool": "command", "args": {"command": "echo hello"}}]))

    async def run():
        task = service.start("Test", str(tmp_path))
        async for event in service.stream(task["id"]):
            if event["type"] == "approval_required":
                await service.cancel(task["id"])
        result = service.get(task["id"])
        assert result["pending"] is None
        assert not service.approvals
        return result

    assert asyncio.run(run())["status"] == "cancelled"


def test_second_task_in_same_workspace_is_rejected(tmp_path):
    service = HarnessService(tmp_path / "tasks", scripted([]))

    async def run():
        task = service.start("A", str(tmp_path))
        with pytest.raises(ValueError, match="bereits"):
            service.start("B", str(tmp_path))
        await service.cancel(task["id"])

    asyncio.run(run())


def test_restart_retains_interrupted_history(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"id": "a", "status": "working", "pending": {"id": "x"}}))
    task = HarnessService(tmp_path).get("a")
    assert task["status"] == "interrupted"
    assert task["pending"] is None


def test_context_is_opt_in_and_private(tmp_path):
    agent = MiniJonAgent(tmp_path / "config.json")
    context = {"process": "Code.exe", "title": "secret.tsx", "idle_seconds": 15}
    assert agent.observe(context)["context"] == {}
    agent.configure({"enabled": True})
    assert agent.observe(context)["context"]["title"] == "secret.tsx"
    agent.configure({"privacy": True})
    assert agent.observe(context)["context"] == {}
    assert agent.state["suggestion"] == ""


def test_context_hysteresis_and_blacklist(tmp_path):
    now = [0.0]
    agent = MiniJonAgent(tmp_path / "config.json", clock=lambda: now[0])
    agent.configure({"enabled": True})
    context = {"process": "Code.exe", "title": "file.tsx", "idle_seconds": 15}
    assert agent.observe(context)["activity"] == "idle"
    now[0] = 9
    assert agent.observe(context)["activity"] == "coding"
    assert agent.state["suggestion"]
    agent.reject()
    now[0] = 700
    assert not agent.observe(context)["suggestion"]
    assert agent.observe({"title": "Bitwarden"})["context"] == {}


def test_personality_is_distinct_and_truthful():
    from app.services.persona_service import PersonaService

    service = PersonaService()
    for variant in ("papa", "junior"):
        text = service.persona_block(False, variant)
        assert "VERANTWORTUNGSKOMPASS" in text
        assert "Behaupte weder Bewusstsein" in text
        assert "MUSST du von Lena" not in text
    assert "Mini Jon" in service.persona_block(False, "junior")
    assert "trockenem Humor" in service.persona_block(False, "papa")


def test_harness_aliases_use_current_directory(monkeypatch):
    from app.services import terminal_service as terminal

    monkeypatch.setattr(terminal, "_gebuendelt", lambda: None)
    monkeypatch.setattr(terminal, "starter", lambda: ("python", "backend"))
    for windows in (True, False):
        monkeypatch.setattr(terminal, "_windows", lambda: windows)
        text = terminal._harness_inhalt()
        assert "-m app.cli harness" in text
        assert "cd " not in text


def test_commands_and_failures_are_real(tmp_path):
    from app.services.harness.process import run_command

    async def run():
        okay = await run_command("Write-Output okay" if os.name == "nt" else "printf okay", str(tmp_path))
        assert okay["ok"] and "okay" in okay["output"]
        bad = await run_command("exit 7", str(tmp_path))
        assert not bad["ok"] and bad["exit_code"] == 7
        timeout = await run_command("Start-Sleep 20" if os.name == "nt" else "sleep 20", str(tmp_path), 1)
        assert timeout["timed_out"] and not timeout["ok"]

    asyncio.run(run())
