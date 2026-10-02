from __future__ import annotations

import json

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text
from app.services.harness.service import TERMINAL, get_harness_service
from app.services.project_service import get_project_service

SELECTION_FILE = DATA_DIR / "harness_projects.json"


def selection(source: str, root: str | None = None) -> str:
    try:
        values = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        values = {}
    if root is not None:
        values[source] = root
        atomic_write_text(SELECTION_FILE, json.dumps(values, ensure_ascii=False))
    return str(values.get(source, ""))


def describe(task: dict) -> str:
    states = {"planning": "Plant", "working": "Arbeitet", "verifying": "Prüft", "waiting_approval": "Wartet auf Freigabe", "done": "Fertig", "needs_review": "Prüfung offen", "failed": "Fehlgeschlagen", "cancelled": "Abgebrochen", "interrupted": "Unterbrochen", "cancelling": "Bricht ab"}
    lines = [f'Jon Harness · {task["id"]} · {states.get(task["status"], task["status"])}', task["goal"], f'Schritt {task["step"]} · {len(task["changes"])} Änderungen · {len(task["checks"])} Prüfungen']
    if task.get("pending"):
        pending = task["pending"]
        lines.extend([pending["args"]["command"], f'Ordner: {pending["args"]["cwd"]}', pending["notice"], f'/erlauben {task["id"]} {pending["id"]}', f'/ablehnen {task["id"]} {pending["id"]}'])
    if task.get("summary"):
        lines.append(task["summary"])
    return "\n".join(lines)


async def handle(text: str, source: str) -> dict | None:
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return None
    command = parts[0].lower().split("@")[0]
    rest = parts[1].strip() if len(parts) > 1 else ""
    known = {"/hhelp", "/harness", "/code", "/projekt", "/projekte", "/aufgaben", "/hstatus", "/hstop", "/erlauben", "/ablehnen", "/diff", "/kontext", "/privat", "/ruhe"}
    if command not in known:
        return None
    service = get_harness_service()
    remote = source.startswith("telegram:")

    def owned(task_id: str) -> dict:
        task = service.get(task_id)
        if remote and task["source"] != source:
            raise PermissionError("Dieser Auftrag gehört zu einem anderen Kanal.")
        return task

    try:
        if command == "/hhelp":
            return {"text": "Jon Harness: /projekte zeigt deine Projekte. /projekt <Name> wählt den Arbeitsordner. /harness <Auftrag> startet die Arbeit. /aufgaben zeigt Aufträge, /hstatus <ID> den Stand, /diff <ID> Änderungen, /hstop <ID> stoppt. Shellbefehle benötigen die angezeigte Einzelfreigabe. MiniJon: /kontext an aktiviert lokale App-Erkennung, /privat an pausiert sie, /ruhe reduziert Hinweise."}
        if command in {"/projekt", "/projekte"}:
            projects = get_project_service().list()
            if command == "/projekte" or not rest:
                return {"text": "Projekte:\n" + "\n".join(f'{p["id"]} · {p["name"]}' for p in projects) + "\n/projekt <ID oder eindeutiger Name>"}
            matches = [p for p in projects if p["id"] == rest or p["name"].casefold() == rest.casefold()]
            if len(matches) != 1:
                raise ValueError("Bitte ein eindeutiges, in Jon gespeichertes Projekt wählen. /projekte zeigt die Auswahl.")
            selection(source, matches[0]["root"])
            return {"text": f'Projekt gewählt: {matches[0]["name"]}'}
        if command in {"/harness", "/code"}:
            if not rest:
                return {"text": "/projekte · /projekt <ID> · /harness <Auftrag> · /hstatus <ID> · /hstop <ID> · /diff <ID>\nShellbefehle: /erlauben <Aufgabe> <Freigabe> oder /ablehnen <Aufgabe> <Freigabe>"}
            root = selection(source)
            if not root or not get_project_service().find_by_root(root):
                raise ValueError("Zuerst mit /projekt ein gespeichertes Projekt wählen.")
            task = service.start(rest, root, source=source)
            return {"text": describe(task), "task_id": task["id"]}
        if command == "/aufgaben":
            return {"text": "\n\n".join(describe(t) for t in service.list(source if remote else "")[:5]) or "Keine Harness-Aufträge."}
        if command in {"/hstatus", "/hstop", "/diff"}:
            task = owned(rest)
            if command == "/hstop":
                task = await service.cancel(task["id"])
            if command == "/diff":
                return {"text": "\n\n".join(c["diff"] for c in task["changes"])[-12000:] or "Noch keine Dateiänderungen."}
            return {"text": describe(task)}
        if command in {"/erlauben", "/ablehnen"}:
            task_id, approval_id = rest.split()
            owned(task_id)
            service.approve(task_id, approval_id, command == "/erlauben")
            return {"text": "Freigabe erteilt." if command == "/erlauben" else "Abgelehnt.", "task_id": task_id}
        from app.services.mini_jon_agent import get_mini_jon_agent

        agent = get_mini_jon_agent()
        if command == "/ruhe":
            agent.reject()
            return {"text": "Verstanden. Ich halte mich für diese Tätigkeit länger zurück."}
        if rest not in {"an", "aus", ""}:
            raise ValueError("Bitte an oder aus angeben.")
        if rest:
            agent.configure({"enabled" if command == "/kontext" else "privacy": rest == "an"})
        return {"text": f'MiniJon-Kontext: {"an" if agent.config["enabled"] else "aus"}. Privatsphäre: {"an" if agent.config["privacy"] else "aus"}. Keine Screenshots oder Zwischenablage. Beobachtete Apps stehen unter /api/mini-jon/agent.'}
    except (KeyError, ValueError, PermissionError, OSError) as exc:
        return {"text": str(exc).strip("'")}


async def watch(task_id: str, send) -> None:
    service = get_harness_service()
    last = ""
    async for event in service.stream(task_id):
        task = service.get(task_id)
        pending = task.get("pending")
        key = pending["id"] if pending else task["status"] if task["status"] in TERMINAL else ""
        if key and key != last:
            last = key
            await send(describe(task))
