from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx

from app.cli import _konsole_vorbereiten, kunst
from app.cli.kunst import FETT, GRAU, GRUEN, ROT, TUERKIS, Stift
from app.core.auth import get_token
from app.core.config import get_settings
from app.services.harness import HarnessService
from app.services.harness.messages import describe
from app.services.harness.service import TERMINAL


class HarnessTerminal:
    def __init__(self, root: Path, provider: str = "", model: str = "", max_steps: int = 80) -> None:
        self.root = root.resolve(strict=True)
        self.provider, self.model, self.max_steps = provider, model, max_steps
        self.stift = Stift()
        self.local: HarnessService | None = None
        self.client: httpx.AsyncClient | None = None
        self.task_id = ""

    async def connect(self) -> None:
        self.client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{get_settings().port}/api", headers={"X-Jon-Token": get_token()}, timeout=30, trust_env=False)
        try:
            response = await self.client.get("/harness/tasks", timeout=2)
            response.raise_for_status()
        except httpx.ConnectError:
            await self.client.aclose()
            self.client = None
            self.local = HarnessService()
            print(self.stift("Lokaler Harness · ohne Verbindung zur geöffneten App", GRAU))

    async def request(self, method: str, path: str, body: dict | None = None):
        response = await self.client.request(method, path, json=body)
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(str(detail))
        return response.json()

    async def stream(self):
        if self.local:
            async for event in self.local.stream(self.task_id):
                yield event
            return
        async with self.client.stream("GET", f"/harness/tasks/{self.task_id}/events", timeout=httpx.Timeout(30, read=45)) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    yield json.loads(line[5:])

    async def stop(self) -> None:
        if not self.task_id:
            return
        if self.local:
            await self.local.cancel(self.task_id)
        else:
            await self.request("POST", f"/harness/tasks/{self.task_id}/cancel")

    async def run(self, goal: str) -> dict:
        payload = {"goal": goal, "root": str(self.root), "source": "terminal", "provider": self.provider, "model": self.model, "max_steps": self.max_steps}
        task = self.local.start(**payload) if self.local else await self.request("POST", "/harness/tasks", payload)
        self.task_id = task["id"]
        print(self.stift(f'Jon Harness · {self.task_id} · {self.root}', TUERKIS, FETT))
        handled: set[str] = set()
        try:
            async for event in self.stream():
                if event["type"] == "snapshot":
                    task = event["task"]
                pending = event.get("pending") or (event.get("task") or {}).get("pending")
                if pending and pending["id"] not in handled:
                    handled.add(pending["id"])
                    print("\n" + pending["args"]["command"])
                    print(self.stift(f'Ordner: {pending["args"]["cwd"]}', GRAU))
                    print(pending["notice"])
                    answer = await asyncio.to_thread(input, "Diesen Befehl ausführen? [j/N] ")
                    allow = answer.strip().lower() in {"j", "ja", "y", "yes"}
                    if self.local:
                        self.local.approve(self.task_id, pending["id"], allow)
                    else:
                        await self.request("POST", f"/harness/tasks/{self.task_id}/approve", {"approval_id": pending["id"], "allow": allow})
                if event["type"] == "action":
                    result = event["result"]
                    print(self.stift(f'  {"✕" if result.get("error") or result.get("ok") is False else "✓"} {event["tool"]}', ROT if result.get("error") or result.get("ok") is False else GRUEN))
                    if result.get("diff"):
                        print(result["diff"])
                    if "exit_code" in result:
                        print(f'  Exit {result["exit_code"]}\n{result["output"][-4000:]}')
                if event["type"] == "action_error":
                    print(self.stift(event["message"], ROT))
            task = self.local.get(self.task_id) if self.local else await self.request("GET", f"/harness/tasks/{self.task_id}")
            print("\n" + describe(task))
            return task
        except BaseException:
            await self.stop()
            raise
        finally:
            self.task_id = ""

    async def session(self, goal: str = "") -> int:
        await self.connect()
        try:
            if goal:
                task = await self.run(goal)
                return 0 if task["status"] == "done" else 1
            name = os.environ.get("USERNAME") or os.environ.get("USER") or "du"
            print(kunst.kopf(self.stift, get_settings().app_version, name, kunst.breite() < 108))
            print(self.stift(f"Jon Code · {self.root}\nAuftrag eingeben · /ende beendet · Strg+C stoppt die laufende Aufgabe", GRAU))
            while True:
                try:
                    text = (await asyncio.to_thread(input, self.stift("Du (code)> ", TUERKIS, FETT))).strip()
                except EOFError:
                    return 0
                if text in {"/ende", "/exit", "ende", "exit"}:
                    return 0
                if text:
                    await self.run(text)
        finally:
            if self.local:
                await self.local.close()
            if self.client:
                await self.client.aclose()


def main(argv: list[str] | None = None) -> None:
    _konsole_vorbereiten()
    parser = argparse.ArgumentParser(prog="jon-code", description="Jon Coding Harness im aktuellen Projektordner")
    parser.add_argument("goal", nargs="*")
    parser.add_argument("-C", "--cwd", default=str(Path.cwd()))
    parser.add_argument("--provider", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--max-steps", type=int, choices=range(1, 201), default=80, metavar="1..200")
    args = parser.parse_args(argv)
    from app.db.database import init_db

    init_db()
    try:
        code = asyncio.run(HarnessTerminal(Path(args.cwd), args.provider, args.model, args.max_steps).session(" ".join(args.goal)))
    except KeyboardInterrupt:
        print("\nAuftrag abgebrochen.")
        code = 130
    except Exception as exc:
        print(f"Jon Harness: {exc}")
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
