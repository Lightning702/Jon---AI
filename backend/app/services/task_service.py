from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime

from app.core.config import DATA_DIR, get_settings
from app.providers.base import ChatMessage, ChatRequest
from app.providers.registry import get_registry

TASKS_FILE = DATA_DIR / "tasks.json"

WEEKDAY_KEYS = ["mo", "di", "mi", "do", "fr", "sa", "so"]

AUTOMATION_SYSTEM = (
    "Du bist Jon und fuehrst jetzt eine vom Nutzer geplante Automation aus. "
    "Der Nutzer hat diese Aufgabe selbst eingerichtet, du darfst deine Tools "
    "direkt verwenden. Arbeite sorgfaeltig und sicher: loesche oder "
    "ueberschreibe nichts Wichtiges, ausser die Aufgabe verlangt es "
    "ausdruecklich. Fasse am Ende in 2-4 kurzen Saetzen auf Deutsch zusammen, "
    "was du getan hast und was dabei herausgekommen ist."
)


def _normalize_repeat(repeat: str) -> str:
    value = (repeat or "daily").strip().lower()
    if value in {"daily", "taeglich", "täglich", "jeden tag"}:
        return "daily"
    if value in {"once", "einmal", "einmalig"}:
        return "once"
    for key in WEEKDAY_KEYS:
        if value.startswith(key):
            return key
    return "daily"


class TaskService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        base = {"tasks": [], "running": False}
        if TASKS_FILE.exists():
            try:
                base.update(json.loads(TASKS_FILE.read_text(encoding="utf-8")))
            except Exception:
                pass
        base["running"] = False
        return base

    def _save(self) -> None:
        try:
            TASKS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def add(self, task: str, time_str: str, repeat: str = "daily") -> dict:
        task = task.strip()
        time_str = time_str.strip()
        if not task:
            return {"error": "Aufgabe angeben"}
        try:
            hour, minute = [int(x) for x in time_str.split(":")[:2]]
            time_str = f"{hour:02d}:{minute:02d}"
        except Exception:
            return {"error": "time muss das Format HH:MM haben"}
        now = datetime.now()
        item = {
            "id": uuid.uuid4().hex[:10],
            "task": task,
            "time": time_str,
            "repeat": _normalize_repeat(repeat),
            "active": True,
            "last_run": now.strftime("%Y-%m-%d") if now.strftime("%H:%M") >= time_str else "",
            "last_run_at": None,
            "last_result": None,
            "seen": True,
            "created_at": now.isoformat(timespec="seconds"),
        }
        with self._lock:
            self._data["tasks"].insert(0, item)
            self._save()
        return item

    def list(self) -> list[dict]:
        with self._lock:
            return [dict(t) for t in self._data["tasks"]]

    def delete(self, task_id: str) -> bool:
        with self._lock:
            before = len(self._data["tasks"])
            self._data["tasks"] = [
                t for t in self._data["tasks"] if t["id"] != task_id
            ]
            self._save()
            return len(self._data["tasks"]) < before

    def unseen_reports(self) -> list[dict]:
        with self._lock:
            reports = [
                dict(t)
                for t in self._data["tasks"]
                if t.get("last_result") and not t.get("seen")
            ]
            for t in self._data["tasks"]:
                if t.get("last_result"):
                    t["seen"] = True
            if reports:
                self._save()
            return reports

    def _due(self) -> list[dict]:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current = now.strftime("%H:%M")
        due: list[dict] = []
        with self._lock:
            for t in self._data["tasks"]:
                if not t.get("active", True):
                    continue
                if t.get("last_run") == today:
                    continue
                if current < t.get("time", "23:59"):
                    continue
                repeat = t.get("repeat", "daily")
                if repeat in WEEKDAY_KEYS and WEEKDAY_KEYS[now.weekday()] != repeat:
                    continue
                due.append(t)
        return due

    async def _run_task(
        self, task: str, provider_name: str, model: str
    ) -> str:
        from app.services.chat_service import TOOL_PROVIDERS
        from app.services.tools import ToolBox

        provider = get_registry().get(provider_name)
        toolbox = ToolBox()
        use_tools = provider_name in TOOL_PROVIDERS
        request = ChatRequest(
            messages=[
                ChatMessage(role="system", content=AUTOMATION_SYSTEM),
                ChatMessage(role="user", content=task),
            ],
            model=model,
            temperature=0.7,
            top_p=1.0,
            max_tokens=4096,
            tools=toolbox.schema(task) if use_tools else [],
        )
        parts: list[str] = []
        tools_used: list[str] = []
        async for chunk in provider.stream(
            request, toolbox.execute if use_tools else None
        ):
            if chunk.kind == "content":
                parts.append(chunk.delta)
            elif chunk.kind == "tool_result" and chunk.ok and chunk.name:
                tools_used.append(chunk.name)
        result = "".join(parts).strip()
        if not result and tools_used:
            result = "Erledigt ✅ (" + ", ".join(dict.fromkeys(tools_used)) + ")"
        return result or "Erledigt, aber ohne Bericht."

    async def run_due(
        self, provider: str | None = None, model: str | None = None
    ) -> dict:
        settings = get_settings()
        provider = provider or settings.default_provider
        model = model or settings.default_model
        with self._lock:
            if self._data.get("running"):
                return {"started": False, "reason": "laeuft bereits"}
            self._data["running"] = True
        due = self._due()
        completed = 0
        try:
            for t in due:
                now = datetime.now()
                try:
                    result = await self._run_task(t["task"], provider, model)
                except Exception as exc:
                    result = f"Automation fehlgeschlagen: {exc}"
                with self._lock:
                    t["last_run"] = now.strftime("%Y-%m-%d")
                    t["last_run_at"] = now.isoformat(timespec="seconds")
                    t["last_result"] = result
                    t["seen"] = False
                    if t.get("repeat") == "once":
                        t["active"] = False
                    self._save()
                completed += 1
        finally:
            with self._lock:
                self._data["running"] = False
                self._save()
        return {"started": bool(due), "completed": completed}

    async def run_now(
        self, task_id: str, provider: str | None = None, model: str | None = None
    ) -> dict:
        settings = get_settings()
        provider = provider or settings.default_provider
        model = model or settings.default_model
        with self._lock:
            item = next(
                (t for t in self._data["tasks"] if t["id"] == task_id), None
            )
        if item is None:
            return {"error": "Automation nicht gefunden"}
        now = datetime.now()
        try:
            result = await self._run_task(item["task"], provider, model)
        except Exception as exc:
            result = f"Automation fehlgeschlagen: {exc}"
        with self._lock:
            item["last_run"] = now.strftime("%Y-%m-%d")
            item["last_run_at"] = now.isoformat(timespec="seconds")
            item["last_result"] = result
            item["seen"] = True
            if item.get("repeat") == "once":
                item["active"] = False
            self._save()
        return {"id": item["id"], "task": item["task"], "result": result}


_service: TaskService | None = None


def get_task_service() -> TaskService:
    global _service
    if _service is None:
        _service = TaskService()
    return _service
