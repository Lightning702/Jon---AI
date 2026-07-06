from __future__ import annotations

import asyncio
import json
from typing import Any

from app.services.automation_service import AutomationService
from app.services.memory_service import MemoryService
from app.services.system_service import SystemService

_STR = {"type": "string"}
_NUM = {"type": "number"}
_INT = {"type": "integer"}
_BOOL = {"type": "boolean"}

SAFE_TOOLS = {"get_screen_info", "list_windows", "wait", "recall"}


def _shorten(value: Any, limit: int = 120) -> str:
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def describe_tool(name: str, args: dict[str, Any]) -> str:
    if name == "run_powershell":
        return "Führt einen PowerShell-Befehl auf deinem PC aus."
    if name == "run_cmd":
        return "Führt einen CMD-Befehl auf deinem PC aus."
    if name == "open_url":
        return f"Öffnet {_shorten(args.get('url', 'eine URL'))} im Browser."
    if name == "start_program":
        return f"Startet das Programm {_shorten(args.get('path', ''))}."
    if name == "kill_program":
        return f"Beendet das Programm {_shorten(args.get('name', ''))}."
    if name == "open_explorer":
        return f"Öffnet den Ordner {_shorten(args.get('path', ''))} im Explorer."
    if name == "list_dir":
        return f"Listet den Inhalt von {_shorten(args.get('path', ''))} auf."
    if name == "read_file":
        return f"Liest die Datei {_shorten(args.get('path', ''))}."
    if name == "write_file":
        return f"Schreibt in die Datei {_shorten(args.get('path', ''))}."
    if name == "move_path":
        return (
            f"Verschiebt {_shorten(args.get('source', ''))} nach "
            f"{_shorten(args.get('destination', ''))}."
        )
    if name == "delete_path":
        return f"Löscht {_shorten(args.get('path', ''))}."
    if name == "open_in_vscode":
        return f"Öffnet {_shorten(args.get('path', ''))} in VS Code."
    if name == "get_screen_info":
        return "Fragt Bildschirmgröße und Mausposition ab."
    if name == "mouse_move":
        return f"Bewegt die Maus zu x={args.get('x')}, y={args.get('y')}."
    if name == "mouse_click":
        return "Klickt mit der Maus."
    if name == "mouse_scroll":
        return f"Scrollt um {args.get('amount')}."
    if name == "keyboard_type":
        return f"Tippt den Text: {_shorten(args.get('text', ''))}"
    if name == "keyboard_press":
        return f"Drückt die Taste {_shorten(args.get('key', ''))}."
    if name == "keyboard_hotkey":
        keys = "+".join(str(k) for k in args.get("keys") or [])
        return f"Drückt die Tastenkombination {keys}."
    if name == "list_windows":
        return "Listet alle offenen Fenster auf."
    if name == "focus_window":
        return f"Holt das Fenster „{_shorten(args.get('title', ''))}“ in den Vordergrund."
    if name == "wait":
        return f"Wartet {args.get('seconds')} Sekunden."
    if name == "remember":
        return f"Merkt sich: {_shorten(args.get('content', ''))}"
    if name == "recall":
        return "Ruft gespeicherte Erinnerungen ab."
    if name == "forget":
        return f"Löscht Erinnerungen zu: {_shorten(args.get('query', ''))}"
    return f"Führt das Tool {name} aus."


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class ToolBox:
    def __init__(
        self,
        service: SystemService | None = None,
        automation: AutomationService | None = None,
        memory: MemoryService | None = None,
    ) -> None:
        self._service = service or SystemService()
        self._automation = automation or AutomationService()
        self._memory = memory or MemoryService()

    def schema(self) -> list[dict]:
        return [
            _tool(
                "run_powershell",
                "Fuehrt einen Windows-PowerShell-Befehl auf dem PC des Nutzers aus und "
                "liefert exit_code, stdout und stderr. Damit kannst du praktisch alles auf "
                "dem Computer steuern: Systeminfos, Prozesse, Netzwerk, Dateien, Apps.",
                {"command": {"type": "string", "description": "Der PowerShell-Befehl"}},
                ["command"],
            ),
            _tool(
                "run_cmd",
                "Fuehrt einen Windows-CMD-Befehl aus.",
                {"command": _STR},
                ["command"],
            ),
            _tool(
                "open_url",
                "Oeffnet eine URL im Standardbrowser.",
                {"url": _STR},
                ["url"],
            ),
            _tool(
                "start_program",
                "Startet ein Programm oder eine .exe.",
                {
                    "path": _STR,
                    "args": {"type": "array", "items": {"type": "string"}},
                },
                ["path"],
            ),
            _tool(
                "kill_program",
                "Beendet ein laufendes Programm anhand des Namens (z.B. notepad).",
                {"name": _STR},
                ["name"],
            ),
            _tool(
                "open_explorer",
                "Oeffnet einen Ordner im Windows Explorer.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "list_dir",
                "Listet den Inhalt eines Ordners auf.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "read_file",
                "Liest den Inhalt einer Textdatei.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "write_file",
                "Schreibt Text in eine Datei und ueberschreibt vorhandenen Inhalt.",
                {"path": _STR, "content": _STR},
                ["path", "content"],
            ),
            _tool(
                "move_path",
                "Verschiebt oder benennt eine Datei oder einen Ordner um.",
                {"source": _STR, "destination": _STR},
                ["source", "destination"],
            ),
            _tool(
                "delete_path",
                "Loescht eine Datei oder einen Ordner.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "open_in_vscode",
                "Oeffnet einen Pfad in VS Code.",
                {"path": _STR},
                ["path"],
            ),
            _tool(
                "get_screen_info",
                "Liefert Groesse des Hauptmonitors, Grenzen des gesamten virtuellen "
                "Desktops (alle Monitore) und die aktuelle Mausposition. Rufe das "
                "auf, bevor du die Maus bewegst oder klickst.",
                {},
                [],
            ),
            _tool(
                "mouse_move",
                "Bewegt die Maus zu einer Position. x/y sind Pixel (auch auf "
                "Zweitmonitoren) oder Bruchteile zwischen 0 und 1 bezogen auf den "
                "Hauptmonitor (z.B. x=0.5, y=0.4 = Mitte leicht oben).",
                {"x": _NUM, "y": _NUM, "duration": _NUM},
                ["x", "y"],
            ),
            _tool(
                "mouse_click",
                "Klickt mit der Maus. Mit x/y (Pixel oder Bruchteile 0-1) wird vorher "
                "dorthin bewegt, ohne x/y wird an der aktuellen Position geklickt. "
                "button: left/right/middle, clicks: 1-3 (2 = Doppelklick).",
                {"x": _NUM, "y": _NUM, "button": _STR, "clicks": _INT},
                [],
            ),
            _tool(
                "mouse_scroll",
                "Scrollt das Mausrad. Positiver Wert = nach oben, negativer = nach "
                "unten (z.B. -500 scrollt eine Seite runter).",
                {"amount": _INT},
                ["amount"],
            ),
            _tool(
                "keyboard_type",
                "Tippt Text ueber die Tastatur in das aktuell fokussierte Feld oder "
                "Fenster. press_enter=true drueckt danach Enter.",
                {"text": _STR, "press_enter": _BOOL},
                ["text"],
            ),
            _tool(
                "keyboard_press",
                "Drueckt eine einzelne Taste, optional mehrfach. Beispiele: enter, "
                "tab, esc, space, backspace, delete, up, down, left, right, home, "
                "end, pageup, pagedown, f5, win.",
                {"key": _STR, "presses": _INT},
                ["key"],
            ),
            _tool(
                "keyboard_hotkey",
                "Drueckt eine Tastenkombination gleichzeitig, z.B. "
                '["ctrl","l"] fuer die Browser-Adressleiste, ["ctrl","v"], '
                '["alt","tab"], ["win","d"].',
                {"keys": {"type": "array", "items": _STR}},
                ["keys"],
            ),
            _tool(
                "list_windows",
                "Listet alle offenen Fenster mit Titel und ob sie aktiv/minimiert "
                "sind.",
                {},
                [],
            ),
            _tool(
                "focus_window",
                "Holt ein Fenster in den Vordergrund. title ist ein Teil des "
                "Fenstertitels, z.B. 'WhatsApp' oder 'YouTube'.",
                {"title": _STR},
                ["title"],
            ),
            _tool(
                "wait",
                "Wartet die angegebene Zeit in Sekunden (max 15), z.B. bis eine "
                "Seite oder App geladen ist.",
                {"seconds": _NUM},
                ["seconds"],
            ),
            _tool(
                "remember",
                "Speichert dauerhaft eine wichtige Information ueber den Nutzer oder "
                "eine Vorliebe/Regel, an die du dich in allen kuenftigen Gespraechen "
                "erinnern sollst (z.B. Name, Kontakte, Vorlieben, wiederkehrende "
                "Aufgaben). Nutze das automatisch, wenn der Nutzer etwas Merkenswertes "
                "sagt oder dich bittet, dir etwas zu merken.",
                {"content": _STR},
                ["content"],
            ),
            _tool(
                "recall",
                "Ruft gespeicherte Erinnerungen ab. Ohne query alle, mit query nur "
                "passende. Nutze das, wenn du frueheres Wissen ueber den Nutzer "
                "brauchst.",
                {"query": _STR},
                [],
            ),
            _tool(
                "forget",
                "Loescht gespeicherte Erinnerungen, die zum Suchbegriff passen.",
                {"query": _STR},
                ["query"],
            ),
        ]

    async def execute(self, name: str, args: dict[str, Any]) -> str:
        return await asyncio.to_thread(self._execute, name, args)

    def _execute(self, name: str, args: dict[str, Any]) -> str:
        svc = self._service
        if name == "run_powershell":
            r = svc.run_powershell(str(args.get("command", "")))
            return json.dumps(
                {
                    "exit_code": r.exit_code,
                    "stdout": r.stdout[:6000],
                    "stderr": r.stderr[:2000],
                },
                ensure_ascii=False,
            )
        if name == "run_cmd":
            r = svc.run_cmd(str(args.get("command", "")))
            return json.dumps(
                {
                    "exit_code": r.exit_code,
                    "stdout": r.stdout[:6000],
                    "stderr": r.stderr[:2000],
                },
                ensure_ascii=False,
            )
        if name == "open_url":
            return json.dumps({"opened": svc.open_url(str(args.get("url", "")))})
        if name == "start_program":
            pid = svc.start_program(str(args.get("path", "")), args.get("args") or [])
            return json.dumps({"pid": pid})
        if name == "kill_program":
            r = svc.kill_program(str(args.get("name", "")))
            return json.dumps(
                {"exit_code": r.exit_code, "stdout": r.stdout, "stderr": r.stderr},
                ensure_ascii=False,
            )
        if name == "open_explorer":
            svc.open_explorer(str(args.get("path", "")))
            return json.dumps({"opened": True})
        if name == "list_dir":
            return json.dumps(
                svc.list_dir(str(args.get("path", "")))[:200], ensure_ascii=False
            )
        if name == "read_file":
            return json.dumps(
                {"content": svc.read_file(str(args.get("path", "")))[:6000]},
                ensure_ascii=False,
            )
        if name == "write_file":
            svc.write_file(str(args.get("path", "")), str(args.get("content", "")))
            return json.dumps({"written": True})
        if name == "move_path":
            dest = svc.move_path(
                str(args.get("source", "")), str(args.get("destination", ""))
            )
            return json.dumps({"moved_to": dest})
        if name == "delete_path":
            svc.delete_path(str(args.get("path", "")))
            return json.dumps({"deleted": True})
        if name == "open_in_vscode":
            return json.dumps({"pid": svc.open_in_vscode(str(args.get("path", "")))})
        auto = self._automation
        if name == "get_screen_info":
            return json.dumps(auto.screen_info())
        if name == "mouse_move":
            return json.dumps(
                auto.mouse_move(
                    float(args.get("x", 0)),
                    float(args.get("y", 0)),
                    float(args.get("duration", 0.3)),
                )
            )
        if name == "mouse_click":
            x = args.get("x")
            y = args.get("y")
            return json.dumps(
                auto.mouse_click(
                    float(x) if x is not None else None,
                    float(y) if y is not None else None,
                    str(args.get("button", "left")),
                    int(args.get("clicks", 1)),
                )
            )
        if name == "mouse_scroll":
            return json.dumps(auto.mouse_scroll(int(args.get("amount", 0))))
        if name == "keyboard_type":
            return json.dumps(
                auto.keyboard_type(
                    str(args.get("text", "")),
                    bool(args.get("press_enter", False)),
                ),
                ensure_ascii=False,
            )
        if name == "keyboard_press":
            return json.dumps(
                auto.keyboard_press(
                    str(args.get("key", "")), int(args.get("presses", 1))
                ),
                ensure_ascii=False,
            )
        if name == "keyboard_hotkey":
            return json.dumps(
                auto.keyboard_hotkey([str(k) for k in args.get("keys") or []]),
                ensure_ascii=False,
            )
        if name == "list_windows":
            return json.dumps(auto.list_windows()[:80], ensure_ascii=False)
        if name == "focus_window":
            return json.dumps(
                auto.focus_window(str(args.get("title", ""))), ensure_ascii=False
            )
        if name == "wait":
            return json.dumps(auto.wait(float(args.get("seconds", 1.0))))
        mem = self._memory
        if name == "remember":
            return json.dumps(
                mem.add(str(args.get("content", "")), source="chat"),
                ensure_ascii=False,
            )
        if name == "recall":
            query = str(args.get("query", "")).strip()
            items = mem.search(query) if query else mem.list()
            return json.dumps(items, ensure_ascii=False)
        if name == "forget":
            return json.dumps(
                {"removed": mem.forget(str(args.get("query", "")))},
                ensure_ascii=False,
            )
        return json.dumps({"error": f"unbekanntes Tool: {name}"})
