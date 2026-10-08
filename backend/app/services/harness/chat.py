from __future__ import annotations

from app.services.harness.messages import describe, selection
from app.services.harness.service import get_harness_service
from app.services.project_service import get_project_service


async def execute(args: dict, source: str, root: str | None) -> dict:
    action = args.get("action")
    allgemein = str(args.get("modus", "")).strip().lower() in {"allgemein", "general", "agent"}
    if source.startswith("telegram") and not (action == "start" and allgemein) and action not in {"status", "list", "stop"}:
        return {"error": "Nutze /projekte, /projekt und /harness im privaten, verbundenen Telegram-Chat oder starte einen allgemeinen Auftrag mit modus allgemein."}
    source = "minijon" if source in {"mini-jon", "emil", "minijon"} else source
    service = get_harness_service()
    if action == "start" and allgemein:
        task = service.start(str(args.get("goal", "")), "", source="telegram" if source.startswith("telegram") else source, modus="allgemein")
        return {"task_id": task["id"], "thread": task["thread"], "status": task["status"], "modus": "allgemein", "text": describe(task), "next": "Der Auftrag läuft im Hintergrund weiter, auch über viele Schritte. Fortschritt im Harness-Fenster oder mit status."}
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
        thread = "" if args.get("new_session") is True else service.fortsetzbar(target)
        task = service.start(str(args.get("goal", "")), target, source=source, thread=thread)
        return {"task_id": task["id"], "thread": task["thread"], "continued": bool(thread), "status": task["status"], "text": describe(task), "next": f'/hstatus {task["id"]} zeigt Fortschritt und Freigaben.'}
    if action in {"status", "stop"}:
        task = service.get(str(args.get("id", "")))
        if action == "stop":
            task = await service.cancel(task["id"])
        return {"text": describe(task), "status": task["status"]}
    return {"error": "Unbekannte Harness-Aktion."}
