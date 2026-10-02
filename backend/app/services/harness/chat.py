from __future__ import annotations

from app.services.harness.messages import describe, selection
from app.services.harness.service import get_harness_service
from app.services.project_service import get_project_service


async def execute(args: dict, source: str, root: str | None) -> dict:
    if source.startswith("telegram"):
        return {"error": "Nutze /projekte, /projekt und /harness im privaten, verbundenen Telegram-Chat."}
    source = "minijon" if source in {"mini-jon", "emil", "minijon"} else source
    action = args.get("action")
    service = get_harness_service()
    projects = get_project_service()
    if action == "projects":
        return {"projects": projects.list(), "current_root": root or selection(source)}
    if action == "list":
        return {"tasks": [describe(task) for task in service.list()[:10]]}
    if action == "start":
        chosen = args.get("project")
        if chosen:
            matches = [p for p in projects.list() if p["id"] == chosen or p["name"].casefold() == str(chosen).casefold()]
            if len(matches) != 1:
                return {"error": "Bitte ein eindeutiges gespeichertes Projekt wählen."}
            target = matches[0]["root"]
            if root and target != root:
                return {"error": "Das gewählte Projekt entspricht nicht dem geöffneten Arbeitsordner."}
        else:
            target = root or selection(source)
        if not target:
            return {"error": "Noch kein Projekt gewählt. Zeige projects und frage nach dem gewünschten Projekt."}
        task = service.start(str(args.get("goal", "")), target, source=source)
        return {"task_id": task["id"], "status": task["status"], "text": describe(task), "next": f'/hstatus {task["id"]} zeigt Fortschritt und Freigaben.'}
    if action in {"status", "stop"}:
        task = service.get(str(args.get("id", "")))
        if action == "stop":
            task = await service.cancel(task["id"])
        return {"text": describe(task), "status": task["status"]}
    return {"error": "Unbekannte Harness-Aktion."}
