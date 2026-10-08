from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

VERBOTEN = {"harness_task", "oberflaeche", "set_mood", "journal", "write_skill"}
SHELL = {"run_powershell", "run_cmd"}
ZEITLIMIT = 900
ERGEBNIS_MAX = 14000
_namen: set[str] | None = None


def verfuegbar() -> set[str]:
    global _namen
    if _namen is None:
        from app.services.tools import werkzeugnamen

        _namen = werkzeugnamen() - VERBOTEN
    return _namen


def katalog(grenze: int = 400) -> str:
    from app.services.tools import ToolBox

    zeilen = []
    for eintrag in ToolBox()._eigene_tools():
        funktion = eintrag["function"]
        if funktion["name"] in VERBOTEN:
            continue
        beschreibung = " ".join(str(funktion.get("description", "")).split())[:110]
        felder = ",".join(list((funktion.get("parameters") or {}).get("properties", {}))[:8])
        zeilen.append(f'{funktion["name"]}({felder}): {beschreibung}')
        if len(zeilen) >= grenze:
            break
    return "\n".join(zeilen)


def standardisieren(roh: str) -> dict:
    from app.services.tool_result import succeeded

    try:
        daten = json.loads(roh)
    except (TypeError, ValueError):
        daten = {"text": str(roh)}
    if not isinstance(daten, dict):
        daten = {"wert": daten}
    ok = succeeded(daten)
    text = json.dumps(daten, ensure_ascii=False)
    if len(text) > ERGEBNIS_MAX:
        daten = {"gekuerzt": True, "auszug": text[:ERGEBNIS_MAX]}
    return {"ok": ok, **daten}


async def ausfuehren(
    task: dict,
    name: str,
    args: dict,
    freigabe: Callable[[dict, str, dict, bool], Awaitable[bool]],
    quelle: str = "harness",
) -> dict:
    from app.services.risiko import HOCH, NIEDRIG, bewerten
    from app.services.tools import ToolBox, describe_tool

    name = str(name or "").strip()
    if not name:
        raise ValueError("name fehlt. Gib das Jon-Werkzeug an, z. B. web_search.")
    if name in VERBOTEN:
        raise ValueError(f"{name} ist im Harness nicht verfügbar.")
    if name not in verfuegbar():
        raise ValueError(f"Das Werkzeug {name} gibt es nicht. Nutze jon_tools, um die Liste zu sehen.")
    if not isinstance(args, dict):
        raise ValueError("args des Jon-Werkzeugs muss ein Objekt sein.")
    stufe = bewerten(name, args)
    if stufe.risiko != NIEDRIG:
        shell = name in SHELL
        befehl = str(args.get("command", "")) if shell else describe_tool(name, args)
        if not await freigabe(task, "jon:" + name, {"command": befehl, "werkzeug": name, "args": {k: str(v)[:300] for k, v in args.items()}}, stufe.risiko == HOCH and not shell):
            return {"ok": False, "error": "Freigabe abgelehnt oder abgelaufen. Nicht umgehen."}
    box = ToolBox(source=quelle, root=task.get("root") if task.get("modus") == "code" else None)
    from app.services.tools import runde_beginnen

    runde_beginnen()
    try:
        roh = await asyncio.wait_for(box.execute(name, args, source=quelle), ZEITLIMIT)
    except asyncio.TimeoutError:
        return {"ok": False, "error": f"{name} hat nach {ZEITLIMIT // 60} Minuten nicht geantwortet."}
    return standardisieren(roh)
