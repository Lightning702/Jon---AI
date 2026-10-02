from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx
import pytest
from fastapi import FastAPI

from app.api.harness_routes import router
from app.core.auth import TokenMiddleware
from app.services.harness.service import HarnessService
from app.services.harness.workspace import Workspace


def test_api_requires_token_and_tracks_real_changes(monkeypatch, tmp_path):
    from app.services.harness import service as module

    root = tmp_path / "project"
    root.mkdir()
    actions = iter([
        {"tool": "plan", "args": {"steps": ["Erstellen"]}},
        {"tool": "create", "args": {"path": "hello.py", "content": "print('Hallo')\n"}},
        {"tool": "finish", "args": {"summary": "Datei erstellt", "incomplete": True}},
    ])

    async def model(*args, **kwargs):
        await asyncio.sleep(0)
        return json.dumps(next(actions))

    service = HarnessService(tmp_path / "tasks", model)
    monkeypatch.setattr(module, "_service", service)
    app = FastAPI()
    app.add_middleware(TokenMiddleware)
    app.include_router(router)

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            assert (await client.get("/api/harness/tasks")).status_code == 401
            client.headers["X-Jon-Token"] = os.environ["JON_TOKEN"]
            response = await client.post("/api/harness/tasks", json={"goal": "Datei erstellen", "root": str(root)})
            assert response.status_code == 200
            task_id = response.json()["id"]
            runner = service.running.get(task_id)
            if runner:
                await runner
            task = (await client.get(f"/api/harness/tasks/{task_id}")).json()
            assert task["status"] == "needs_review"
            assert (root / "hello.py").read_text() == "print('Hallo')\n"
            assert task["changes"][0]["path"] == "hello.py"
            assert (await client.post(f"/api/harness/tasks/{task_id}/approve", json={"approval_id": "stale", "allow": True})).status_code == 409
            assert (await client.get("/api/harness/tasks/missing")).status_code == 404
            response = await client.get(f"/api/harness/tasks/{task_id}/events")
            events = [json.loads(line[5:]) for line in response.text.splitlines() if line.startswith("data:")]
            assert events[0]["type"] == "snapshot"
            assert not any(e["type"] == "approval_required" for e in events)

    asyncio.run(run())


def test_telegram_cannot_control_another_channel(monkeypatch, tmp_path):
    from app.services.harness import service as module
    from app.services.harness.messages import handle

    service = HarnessService(tmp_path / "tasks")
    service.tasks["owned"] = {"id": "owned", "source": "telegram:1"}
    monkeypatch.setattr(module, "_service", service)

    async def run():
        for command in ("/hstatus owned", "/hstop owned", "/diff owned", "/erlauben owned token"):
            response = await handle(command, "telegram:2")
            assert "anderen Kanal" in response["text"]

    asyncio.run(run())


def test_telegram_project_must_be_registered(monkeypatch, tmp_path):
    from app.services.harness import messages

    class Projects:
        def list(self):
            return [{"id": "one", "name": "Demo", "root": str(tmp_path)}]

        def find_by_root(self, root):
            return None

    monkeypatch.setattr(messages, "get_project_service", lambda: Projects())
    monkeypatch.setattr(messages, "SELECTION_FILE", tmp_path / "selected.json")

    async def run():
        assert "Projekt gewählt" in (await messages.handle("/projekt one", "telegram:1"))["text"]
        assert "Zuerst" in (await messages.handle("/harness ändere etwas", "telegram:1"))["text"]
        assert "eindeutiges" in (await messages.handle("/projekt C:/Windows", "telegram:1"))["text"]

    asyncio.run(run())


def test_workspace_lease_across_service_instances(tmp_path):
    async def model(*args, **kwargs):
        await asyncio.sleep(20)

    first = HarnessService(tmp_path / "tasks", model)

    async def run():
        task = first.start("First", str(tmp_path))
        second = HarnessService(tmp_path / "tasks", model)
        with pytest.raises(ValueError, match="anderer Jon-Prozess"):
            second.start("Second", str(tmp_path))
        assert json.loads((tmp_path / "tasks" / f'{task["id"]}.json').read_text())["status"] != "interrupted"
        await first.cancel(task["id"])
        second_task = second.start("Second", str(tmp_path))
        await second.cancel(second_task["id"])

    asyncio.run(run())


def test_cancel_kills_descendants(tmp_path):
    from app.services.harness.process import run_command

    child = tmp_path / "child.py"
    child.write_text("import subprocess,sys,time\nfrom pathlib import Path\nsubprocess.Popen([sys.executable,'-c',\"import time; from pathlib import Path; time.sleep(2); Path('orphan.txt').write_text('bad')\"])\nPath('ready.txt').write_text('ready')\ntime.sleep(30)\n", encoding="utf-8")
    command = f"& '{sys.executable}' child.py" if os.name == "nt" else f"'{sys.executable}' child.py"

    async def run():
        task = asyncio.create_task(run_command(command, str(tmp_path)))
        try:
            async with asyncio.timeout(10):
                while not (tmp_path / "ready.txt").exists():
                    await asyncio.sleep(.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await asyncio.sleep(2.3)
            assert not (tmp_path / "orphan.txt").exists()
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    asyncio.run(run())


def test_failed_check_cannot_be_overridden_by_model(tmp_path):
    actions = iter([
        {"tool": "plan", "args": {"steps": ["Ändern", "Testen"]}},
        {"tool": "create", "args": {"path": "a.txt", "content": "x"}},
        {"tool": "verify", "args": {"command": "exit 4"}},
        {"tool": "finish", "args": {"summary": "Alles perfekt"}},
    ])

    async def model(*args, **kwargs):
        return json.dumps(next(actions))

    service = HarnessService(tmp_path / "tasks", model)

    async def run():
        task = service.start("Test", str(tmp_path))
        async for event in service.stream(task["id"]):
            if event["type"] == "approval_required":
                service.approve(task["id"], event["pending"]["id"], True)
        result = service.get(task["id"])
        assert result["status"] == "needs_review"
        assert result["checks"][0]["exit_code"] == 4

    asyncio.run(run())
